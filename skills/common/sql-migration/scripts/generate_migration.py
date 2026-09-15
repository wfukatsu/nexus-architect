#!/usr/bin/env python3
"""Generate the migration module from the SQL migration manifest.

    python3 generate_migration.py --project-dir DIR --out generated/sql-migration/<target> --package com.example.migration

Reads reports/03_design/sql-migration/{sql-migration-manifest.json, sql-inventory.json, schema.json,
conversion.json} and work/version-decisions.json. Before writing anything it checks the gate:

  * the manifest passes tools/lib/sql_migration_manifest.py
  * every dependency version the module pins was resolved (@rules/dependency-versions.md)
  * the output directory is absent, empty, or an earlier output of this generator
  * every statement's source still yields the inventoried text
  * the converter, run again on that text, gives the verdict the manifest recorded

and refuses (GateFailure, exit 1) with every violation when one fails. On success it replaces the output
directory with a Gradle module:

  src/main/resources/schema.json            the Schema Loader JSON
  src/main/resources/sql/SQM-###.sql        route scalardb_sql: the converted statement, full text
  src/main/resources/plans/SQM-###.plan.json  route plan: the whole plan, run by MigrationPlans
  <package>/ScalarDbSqlStatements.java      constants for the scalardb_sql statements
  <package>/CoreApiStatements.java          route core_api: one method per statement to implement
  <package>/MigrationPlans.java             loads and runs plans through a Fetcher and H2
  <package>/appside/Sqm###Query|Write|IdGenerator.java   route app_side skeletons with their semantics
  src/test/java/<package>/appside/Sqm###QueryGoldenTest.java  disabled until golden results are captured
  com/scalar/migrate/**                     the vendored runtime and helpers
  migration-summary.json                    what was generated per statement and what still needs implementing
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import logging
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3] / "tools" / "lib"))

import inventory as inventory_module  # noqa: E402
from scalardb_migrate.converter import convert_script  # noqa: E402
from scalardb_migrate.decomposer import DEFAULT_ROW_LIMIT  # noqa: E402
from scalardb_migrate.schema import SchemaRegistry  # noqa: E402
from sql_migration_manifest import (INVENTORY_PATH, MANIFEST_PATH, SCHEMA_PATH,  # noqa: E402
                                    load_and_validate)

RUNTIME = HERE.parent / "runtime-java" / "src" / "main" / "java" / "com" / "scalar" / "migrate"
CONVERSION_PATH = Path("reports/03_design/sql-migration/conversion.json")
VERSIONS_PATH = Path("work/version-decisions.json")
MARKER = ".sql-migration-generated"
REQUIRED_VERSIONS = ("com.scalar-labs:scalardb", "com.h2database:h2", "com.google.code.gson:gson", "org.junit:junit-bom")
SEVERITY = {"OK": 0, "WARN": 1, "PLANNED": 2, "ERROR": 3}
WRITE_PATTERNS = {"rmw", "conditional_write", "app_clock"}
STATEMENT_SEPARATOR = ";\n"  # one SQM may convert to several statements (a table and its index)


class GateFailure(Exception):
    """The manifest no longer describes what the source and the converter say; nothing was written."""


def _java_string(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "") + '"'


def _javadoc(text: str) -> str:
    return html.escape(text, quote=False).replace("*/", "*&#47;")


def _class_stem(sid: str) -> str:
    return sid.replace("-", "").capitalize()


def _load_json(path: Path, label: str, failures: list):
    if not path.is_file():
        failures.append(f"{label}: {path} does not exist")
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _gate(project: Path, out: Path):
    failures = []
    manifest, errors = load_and_validate(str(project))
    if manifest is None and not errors:
        raise GateFailure(f"no manifest at {MANIFEST_PATH}; run /architect:design-sql-migration first")
    if errors:
        raise GateFailure("the manifest is not valid — fix it with design-sql-migration:\n  " + "\n  ".join(errors))
    inputs = manifest.get("inputs", {})
    inventory = _load_json(project / (inputs.get("inventory") or INVENTORY_PATH), "inventory", failures)
    schema = _load_json(project / (inputs.get("schema") or SCHEMA_PATH), "schema", failures)
    conversion = json.loads((project / CONVERSION_PATH).read_text(encoding="utf-8")) \
        if (project / CONVERSION_PATH).is_file() else {}
    versions = _load_json(project / VERSIONS_PATH, "dependency versions", failures) or {}
    chosen = {e.get("name"): e.get("chosen") for e in versions.get("entries", []) if isinstance(e, dict)}
    missing = [name for name in REQUIRED_VERSIONS if not chosen.get(name)]
    if missing:
        failures.append(f"dependency versions not resolved in {VERSIONS_PATH}: {', '.join(missing)}")
    if out.exists() and any(out.iterdir()) and not (out / MARKER).is_file():
        failures.append(f"{out} holds files this generator did not write; refusing to overwrite it")
    if failures or inventory is None or schema is None:
        raise GateFailure("\n".join(failures))
    return manifest, inventory, schema, conversion, chosen


def _reconvert(project, manifest, inventory, schema_path, conversion):
    """Convert every decided statement again; {id: (status, converted, plan)} or GateFailure."""
    logging.getLogger("sqlglot").setLevel(logging.ERROR)
    dialect = manifest["source"]["dialect"]
    storage = manifest["target"]["storage"]
    registry = SchemaRegistry.from_schema_loader_json(str(schema_path))
    expected = {t: (v["rows"], None) for t, v in (conversion.get("expected_rows") or {}).items()}
    isolation = conversion.get("isolation", "SERIALIZABLE")
    statements = {s["id"]: s for s in inventory["statements"]}
    # DDL is checked against a registry of its own: feeding it into the schema registry would redefine the
    # namespace-qualified tables of schema.json without their namespace, and every plan would fetch from none.
    ddl_registry = SchemaRegistry()
    failures, verdicts = [], {}
    for entry in sorted(manifest["statements"], key=lambda e: statements[e["id"]]["category"] != "ddl"):
        stmt = statements[entry["id"]]
        recorded = entry["converter"]["status"]
        if stmt["language"] == "jpql":
            verdicts[entry["id"]] = ("ERROR", [], None)
            continue
        try:
            text = inventory_module.statement_text(stmt, project_dir=project)
        except inventory_module.StaleEvidence:
            failures.append(f"{entry['id']}: source changed since the inventory; re-run design-sql-migration")
            continue
        plan_options = entry.get("plan") or {}
        is_ddl = stmt["category"] == "ddl"
        results, updated = convert_script(text, dialect, ddl_registry if is_ddl else registry, storage=storage,
                                           expected_rows=expected,
                                           isolation=isolation,
                                           row_limit=plan_options.get("row_limit") or conversion.get("row_limit") or DEFAULT_ROW_LIMIT,
                                           h2_indexes=bool(plan_options.get("h2_indexes")))
        status = max((r.status for r in results), key=SEVERITY.get) if results else "ERROR"
        if status != recorded:
            failures.append(f"{entry['id']}: the converter now says {status}, the manifest recorded {recorded}")
        if is_ddl:
            ddl_registry = updated
        plan = next((r.plan for r in results if r.plan), None)
        if entry["route"] == "plan" and plan:
            for fetch in plan.get("fetch", []):
                if not fetch.get("namespace"):
                    failures.append(f"{entry['id']}: the plan fetches {fetch.get('table')} without a namespace; "
                                    "schema.json must qualify every table")
        verdicts[entry["id"]] = (status, [c for r in results for c in r.converted], plan)
    if failures:
        raise GateFailure("\n".join(failures))
    return verdicts


def _build_gradle(versions, premium):
    sql_client = (f"    runtimeOnly 'com.scalar-labs:scalardb-sql-jdbc:{versions['com.scalar-labs:scalardb']}'\n"
                  f"    runtimeOnly 'com.scalar-labs:scalardb-cluster-java-client-sdk:{versions['com.scalar-labs:scalardb']}'\n"
                  if premium else "")
    return f"""plugins {{
    id 'java'
}}

// Generated by /architect:implement-sql-migration. Versions come from work/version-decisions.json.
java {{
    toolchain {{ languageVersion = JavaLanguageVersion.of(17) }}
}}

repositories {{ mavenCentral() }}

dependencies {{
    implementation 'com.scalar-labs:scalardb:{versions['com.scalar-labs:scalardb']}'
    implementation 'com.h2database:h2:{versions['com.h2database:h2']}'
    implementation 'com.google.code.gson:gson:{versions['com.google.code.gson:gson']}'
{sql_client}
    testImplementation platform('org.junit:junit-bom:{versions['org.junit:junit-bom']}')
    testImplementation 'org.junit.jupiter:junit-jupiter'
    testRuntimeOnly 'org.junit.platform:junit-platform-launcher'
}}

test {{
    useJUnitPlatform()
    // Oracle-style TO_CHAR('DAY'/'MON') depends on the JVM locale; Oracle's default NLS_DATE_LANGUAGE is AMERICAN
    jvmArgs '-Duser.language=en', '-Duser.country=US'
}}
"""


def _origin(stmt):
    origin = stmt["origin"]
    where = f"{origin['path']}:{origin['lines'][0]}-{origin['lines'][1]}"
    return where + (f" ({origin['locator']})" if origin.get("locator") else "")


def _scalardb_sql_class(package, entries):
    lines = [f"package {package};", "",
             "/** ScalarDB SQL for the statements routed to scalardb_sql. Generated from sql-migration-manifest.json; do not edit. */",
             "public final class ScalarDbSqlStatements {", "  private ScalarDbSqlStatements() {}", ""]
    for stmt, converted in entries:
        lines += [f"  /** {stmt['id']} — {_javadoc(_origin(stmt))}. */",
                  f"  public static final String {stmt['id'].replace('-', '_')} = {_java_string(STATEMENT_SEPARATOR.join(converted))};", ""]
    lines.append("}")
    return "\n".join(lines) + "\n"


def _core_api_interface(package, entries):
    lines = [f"package {package};", "",
             "import com.scalar.db.api.DistributedTransaction;", "import com.scalar.db.api.Result;",
             "import java.util.List;", "import java.util.Map;", "",
             "/**",
             " * Statements routed to core_api: implement each with Get / Scan / Put / Delete inside the caller's transaction.",
             " * The converted ScalarDB SQL states the access each one needs. Generated from sql-migration-manifest.json.",
             " */",
             "public interface CoreApiStatements {"]
    for stmt, converted in entries:
        returns = "List<Result>" if stmt["category"] == "query" else "void"
        lines += ["", "  /**", f"   * {stmt['id']} — {_javadoc(_origin(stmt))}.",
                  f"   * <pre>{_javadoc('; '.join(converted))}</pre>", "   */",
                  f"  {returns} {stmt['id'].replace('-', '').lower()}(DistributedTransaction transaction, Map<String, Object> params)"
                  " throws Exception;"]
    lines.append("}")
    return "\n".join(lines) + "\n"


def _plans_class(package, ids):
    id_list = ", ".join(f'"{i}"' for i in ids)
    return f"""package {package};

import com.google.gson.Gson;
import com.scalar.migrate.runtime.Fetcher;
import com.scalar.migrate.runtime.Plan;
import com.scalar.migrate.runtime.Residual;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

/**
 * Statements routed to plan: every fetch runs in one read-only ScalarDB transaction, then the original SQL runs on the
 * fetched rows in a per-call H2 database that is discarded afterwards. Generated from sql-migration-manifest.json.
 */
public final class MigrationPlans {{
  public static final List<String> IDS = List.of({id_list});
  private static final Gson GSON = new Gson();

  private MigrationPlans() {{}}

  public static Plan load(String id) throws IOException {{
    try (InputStream in = MigrationPlans.class.getResourceAsStream("/plans/" + id + ".plan.json")) {{
      if (in == null) {{
        throw new IllegalArgumentException("no plan for " + id);
      }}
      return GSON.fromJson(new String(in.readAllBytes(), StandardCharsets.UTF_8), Plan.class);
    }}
  }}

  /** Runs a plan and returns {{"columns": [...], "rows": [[...]]}}. The fetcher decides Core API or ScalarDB SQL. */
  public static Map<String, Object> run(String id, Fetcher fetcher, Map<String, Object> params) throws Exception {{
    Plan plan = load(id);
    Plan.Residual residual = plan.residual.get("java");
    try (Residual h2 = new Residual(residual.mode, residual.build_indexes)) {{
      fetcher.begin();
      try {{
        for (Plan.Fetch fetch : plan.fetch) {{
          h2.load(fetch, fetcher.fetch(fetch, params));
        }}
        fetcher.commit();
      }} catch (Exception e) {{
        fetcher.rollback();
        throw e;
      }}
      return h2.query(residual.sql, params);
    }}
  }}
}}
"""


def _semantics_doc(entry):
    notes = entry.get("app_side", {}).get("semantics", [])
    if not notes:
        return []
    return [" * <p>Semantics to keep:", " * <ul>"] + \
        [f" *   <li>{_javadoc(n['note'])} — handled by {_javadoc(n['handling'])}</li>" for n in notes] + [" * </ul>"]


NEEDS_IDS = re.compile(r"\bNEXTVAL\b|\bnextval\s*\(", re.I)
NEEDS_CLOCK = re.compile(r"\b(SYSDATE|SYSTIMESTAMP|CURRENT_DATE|CURRENT_TIMESTAMP|LOCALTIMESTAMP)\b|\bNOW\s*\(", re.I)


SUBSTITUTION = re.compile(r"\$\{\s*([A-Za-z_]\w*)")


def query_params(stmt):
    """The parameter names a read's implementation receives: its binds (a positional one as p<n>), then ${...} substitutions."""
    names = []
    for index, bind in enumerate(stmt.get("binds") or [], start=1):
        name = f"p{index}" if bind == "?" else bind
        if name not in names:
            names.append(name)
    for name in SUBSTITUTION.findall(stmt.get("sql") or ""):
        if name not in names:
            names.append(name)
    return names


def _app_side_files(package, entry, stmt):
    stem, sid = _class_stem(entry["id"]), entry["id"]
    pattern = entry["app_side"]["pattern"]
    header = ["/**", f" * {sid} — reimplemented in the application (pattern: {pattern}).",
              f" * <p>Source: {_javadoc(_origin(stmt))}", f" * <pre>{_javadoc(stmt['sql'])}</pre>"] + _semantics_doc(entry)
    files = {}
    if pattern == "read":
        body = header + [" * <p>Helpers: com.scalar.migrate.appside (references/app-side-notes.md). Prove it with the golden",
                         " * check of /architect:verify-sql-migration.", " */"]
        tables = "Map<String, List<Map<String, Object>>> tables"
        names = query_params(stmt)
        if names:  # the golden check passes golden.json's "params" to the two-argument form
            run = ["  @Override", f"  public List<Map<String, Object>> run({tables}) {{", "    return run(tables, Map.of());",
                   "  }", "", f"  /** Parameters: {', '.join(names)}. */", "  @Override",
                   f"  public List<Map<String, Object>> run({tables}, Map<String, Object> params) {{"]
        else:
            run = ["  @Override", f"  public List<Map<String, Object>> run({tables}) {{"]
        files[f"appside/{stem}Query.java"] = "\n".join(
            [f"package {package}.appside;", "", "import com.scalar.migrate.appside.AppSideQuery;", "import java.util.List;",
             "import java.util.Map;", ""] + body + [f"public final class {stem}Query implements AppSideQuery {{"] + run +
            [f'    throw new UnsupportedOperationException("{sid}: not implemented yet");', "  }", "}"]) + "\n"
        files[f"test:appside/{stem}QueryGoldenTest.java"] = "\n".join(
            [f"package {package}.appside;", "", "import static org.junit.jupiter.api.Assertions.assertTrue;", "",
             "import java.nio.file.Files;", "import java.nio.file.Path;", "import org.junit.jupiter.api.Disabled;",
             "import org.junit.jupiter.api.Test;", "",
             f"/** Golden frame for {sid}: capture the source database's result with /architect:verify-sql-migration, then enable. */",
             f'@Disabled("{sid}: golden results not captured yet")',
             f"class {stem}QueryGoldenTest {{", "  @Test", "  void matchesTheSourceDatabase() {",
             f'    Path golden = Path.of("src/test/resources/golden/{sid}/golden.json");',
             f'    assertTrue(Files.isRegularFile(golden), "capture " + golden + " first");',
             "    // verify-sql-migration runs the comparison: scripts/verify/golden.py check", "  }", "}"]) + "\n"
    elif pattern == "id_generation" and stmt["category"] == "ddl":
        body = header + [" * <p>ScalarDB has no sequences or identity columns; the application supplies these IDs.", " */"]
        files[f"appside/{stem}IdGenerator.java"] = "\n".join(
            [f"package {package}.appside;", ""] + body +
            [f"public interface {stem}IdGenerator {{", "  long next() throws Exception;", "}"]) + "\n"
    else:  # a write: rmw, conditional_write, app_clock, or id_generation on DML
        ids = pattern == "id_generation" or bool(NEEDS_IDS.search(stmt["sql"]))
        clock = pattern == "app_clock" or bool(NEEDS_CLOCK.search(stmt["sql"]))
        fields = ["  private final DistributedTransactionManager manager;"]
        params, assigns = ["DistributedTransactionManager manager"], ["    this.manager = manager;"]
        if ids:
            fields.append("  private final LongSupplier ids;  // the values the source took from a sequence or identity")
            params.append("LongSupplier ids")
            assigns.append("    this.ids = ids;")
        if clock:
            fields.append("  private final Clock clock;  // the time the source took from the database server")
            params.append("Clock clock")
            assigns.append("    this.clock = clock;")
        body = header + [" * <p>Read, compute and write in one ScalarDB transaction. On UnknownTransactionStatusException the",
                         " * outcome is unknown: do not roll back or retry blindly (rules/scalardb-exception-handling.md).", " */"]
        imports = ["import com.scalar.db.api.DistributedTransaction;", "import com.scalar.db.api.DistributedTransactionManager;",
                   "import com.scalar.db.exception.transaction.UnknownTransactionStatusException;"]
        imports += (["import java.time.Clock;"] if clock else []) + ["import java.util.Map;"] + \
            (["import java.util.function.LongSupplier;"] if ids else [])
        files[f"appside/{stem}Write.java"] = "\n".join(
            [f"package {package}.appside;", ""] + imports + [""] + body +
            [f"public final class {stem}Write {{"] + fields + ["",
             f"  public {stem}Write({', '.join(params)}) {{"] + assigns + ["  }", "",
             "  public void execute(Map<String, Object> params) throws Exception {",
             "    DistributedTransaction transaction = manager.start();", "    try {", "      apply(transaction, params);",
             "      transaction.commit();", "    } catch (UnknownTransactionStatusException e) {", "      throw e;",
             "    } catch (Exception e) {", "      transaction.rollback();", "      throw e;", "    }", "  }", "",
             "  void apply(DistributedTransaction transaction, Map<String, Object> params) throws Exception {",
             f'    throw new UnsupportedOperationException("{sid}: not implemented yet");', "  }", "}"]) + "\n"
    return files


def generate(project_dir, out_dir, package):
    if not re.fullmatch(r"[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)*", package):
        raise GateFailure(f"package {package!r} is not a Java package name")
    project, out = Path(project_dir), Path(out_dir)
    manifest, inventory, schema, conversion, versions = _gate(project, out)
    schema_path = project / (manifest["inputs"].get("schema") or SCHEMA_PATH)
    verdicts = _reconvert(project, manifest, inventory, schema_path, conversion)
    statements = {s["id"]: s for s in inventory["statements"]}

    main_java = Path("src/main/java") / Path(*package.split("."))
    test_java = Path("src/test/java") / Path(*package.split("."))
    files: dict[Path, str] = {}
    generated: dict[str, list[str]] = {e["id"]: [] for e in manifest["statements"]}
    sql_entries, core_entries, plan_ids = [], [], []
    for entry in manifest["statements"]:
        sid, route, stmt = entry["id"], entry["route"], statements[entry["id"]]
        _, converted, plan = verdicts[sid]
        if route == "schema":
            generated[sid].append("src/main/resources/schema.json")
        elif route == "scalardb_sql":
            path = Path(f"src/main/resources/sql/{sid}.sql")
            files[path] = ";\n".join(converted) + ";\n"
            generated[sid] += [path.as_posix(), (main_java / "ScalarDbSqlStatements.java").as_posix()]
            sql_entries.append((stmt, converted))
        elif route == "core_api":
            generated[sid].append((main_java / "CoreApiStatements.java").as_posix())
            core_entries.append((stmt, converted))
        elif route == "plan":
            path = Path(f"src/main/resources/plans/{sid}.plan.json")
            files[path] = json.dumps(plan, indent=2, ensure_ascii=False) + "\n"
            generated[sid] += [path.as_posix(), (main_java / "MigrationPlans.java").as_posix()]
            plan_ids.append(sid)
        elif route == "app_side":
            for rel, content in _app_side_files(package, entry, stmt).items():
                path = test_java / rel[5:] if rel.startswith("test:") else main_java / rel
                files[path] = content
                generated[sid].append(path.as_posix())

    if sql_entries:
        files[main_java / "ScalarDbSqlStatements.java"] = _scalardb_sql_class(package, sql_entries)
    if core_entries:
        files[main_java / "CoreApiStatements.java"] = _core_api_interface(package, core_entries)
    if plan_ids:
        files[main_java / "MigrationPlans.java"] = _plans_class(package, plan_ids)
    files[Path("src/main/resources/schema.json")] = json.dumps(schema, indent=2, ensure_ascii=False) + "\n"
    files[Path("build.gradle")] = _build_gradle(versions, manifest["target"]["edition"] == "enterprise_premium")
    files[Path("settings.gradle")] = f"rootProject.name = '{out.name}'\n"
    files[Path(".gitignore")] = "build/\n.gradle/\n"

    manifest_bytes = (project / MANIFEST_PATH).read_bytes()
    routes = {}
    for entry in manifest["statements"]:
        routes[entry["route"]] = routes.get(entry["route"], 0) + 1
    summary = {
        "schema_version": 1,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "package": package,
        "routes": routes,
        "statements": [{"id": e["id"], "route": e["route"], "generated": generated[e["id"]]} for e in manifest["statements"]],
        "requires_implementation": [e["id"] for e in manifest["statements"] if e["route"] in ("core_api", "app_side")],
        "not_generated": [e["id"] for e in manifest["statements"] if e["route"] in ("redesign", "retire")],
    }

    if out.exists():
        shutil.rmtree(out)  # the gate proved it is absent, empty or this generator's own output
    out.mkdir(parents=True)
    shutil.copytree(RUNTIME, out / "src/main/java/com/scalar/migrate")
    for rel, content in files.items():
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_text(content, encoding="utf-8")
    (out / "migration-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (out / MARKER).write_text(json.dumps({"generator": "implement-sql-migration",
                                          "manifest_sha256": summary["manifest_sha256"]}) + "\n", encoding="utf-8")
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate the migration module from the SQL migration manifest.")
    ap.add_argument("--project-dir", default=".")
    ap.add_argument("--out", required=True, help="output directory, normally generated/sql-migration/<target>")
    ap.add_argument("--package", required=True, help="Java package of the generated classes")
    args = ap.parse_args(argv)
    try:
        summary = generate(args.project_dir, args.out, args.package)
    except GateFailure as refused:
        print(f"generation refused:\n{refused}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"generation failed: {exc}", file=sys.stderr)
        return 1
    print(f"{len(summary['statements'])} statements {summary['routes']}; "
          f"{len(summary['requires_implementation'])} to implement -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
