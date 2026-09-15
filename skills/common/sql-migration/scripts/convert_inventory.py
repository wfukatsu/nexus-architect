#!/usr/bin/env python3
"""Run the converter over an SQL inventory and draft the migration manifest.

    python3 convert_inventory.py --inventory reports/03_design/sql-migration/sql-inventory.json \
        --edition community|enterprise_standard|enterprise_premium --storage jdbc|cassandra --namespace NS \
        --out-dir reports/03_design/sql-migration [--schema existing-schema.json] [--keys t=p1,p2/c1]... \
        [--live-run DIR]... [--isolation SERIALIZABLE|SNAPSHOT|READ_COMMITTED] [--row-limit N] [--h2-indexes] \
        [--scalardb-version X.Y] [--project-dir DIR]

The analysis results become converter inputs: the inventory's DDL (plus --schema and --keys) is the schema the
access paths are judged against, a live investigation run's row estimates feed the cost estimates, and the edition
decides whether a convertible statement is proposed for ScalarDB SQL or the Core API. Each statement's full text is
re-extracted from its source (a changed source is skipped, never guessed) and converted on its own.

Writes, into --out-dir:
  schema.json                         Schema Loader JSON, namespace-qualified
  conversion.json                     the converter's verdict per statement, literals masked, no plan bodies
  sql-migration-manifest.draft.json   one proposed route per statement (@rules/sql-migration.md) and the
                                      questions the tool may not answer (dynamic SQL, JPQL, semantics to keep)

Exit 0: written; 2: written, with statements skipped because their source changed; 1: fatal.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import inventory as inventory_module  # noqa: E402
from scalardb_migrate.converter import convert_script  # noqa: E402
from scalardb_migrate.decomposer import DEFAULT_ROW_LIMIT  # noqa: E402
from scalardb_migrate.schema import SchemaRegistry  # noqa: E402

EDITIONS = ("community", "enterprise_standard", "enterprise_premium")
STORAGES = ("jdbc", "cassandra")
ISOLATIONS = ("SERIALIZABLE", "SNAPSHOT", "READ_COMMITTED")
DEFAULT_INVENTORY = "reports/03_design/sql-migration/sql-inventory.json"
DEFAULT_SCHEMA = "reports/03_design/sql-migration/schema.json"
SEVERITY_ORDER = {"OK": 0, "WARN": 1, "PLANNED": 2, "ERROR": 3}

ID_GENERATION = {"SEQUENCE", "AUTO_INC"}
APP_CLOCK = {"NOW"}
CONDITIONAL_WRITE = {"DO_NOTHING", "INSERT_IGNORE", "MERGE"}
NO_KEY_PATH = {"FULL_SCAN", "NO_CROSS_PARTITION"}


def _parse_keys(items):
    out = {}
    for item in items or []:
        table, _, spec = item.partition("=")
        partition, _, clustering = spec.partition("/")
        out[table.strip().lower()] = ([c.strip() for c in partition.split(",") if c.strip()],
                                      [c.strip() for c in clustering.split(",") if c.strip()])
    return out


def rows_from_live_runs(runs):
    """{table: (rows, None)} and its provenance from the `rows` statistics of investigate-db-live runs."""
    rows, provenance = {}, {}
    for run in map(Path, runs or ()):
        inv = json.loads((run / "inventory.json").read_text(encoding="utf-8"))
        for stat in inv.get("statistics", []):
            value = stat.get("value")
            if stat.get("metric") == "rows" and isinstance(value, (int, float)) and not isinstance(value, bool):
                table = str(stat.get("name", "")).lower()
                rows[table] = (int(value), None)
                provenance[table] = {"rows": int(value), "semantics": stat.get("semantics")}
    return rows, provenance


def mask_message(message, literals):
    """Mask the statement's own literals in a converter message, and keep the identifiers the converter quotes.

    A literal of three characters or more is also masked where it appears inside another quoted string (a date
    literal the converter rewrote with a time); a shorter one only when it is the whole quoted string.
    """
    def replace(match):
        inner = match.group()[1:-1]
        if any(inner == lit or (len(lit) >= 3 and lit in inner) for lit in literals):
            return "'?'"
        return match.group()
    return inventory_module.STRING_LITERAL.sub(replace, message)


def _merge(results, text=""):
    """One verdict for a statement whose text the converter split into several (a PL/SQL body, say)."""
    literals = {lit[1:-1].replace("''", "'") for lit in inventory_module.STRING_LITERAL.findall(text)} - {""}
    status = max((r.status for r in results), key=SEVERITY_ORDER.get)
    codes, findings = [], []
    for r in results:
        for issue in r.issues:
            if issue.code not in codes:
                codes.append(issue.code)
            findings.append({"severity": issue.severity, "code": issue.code,
                             "message": mask_message(issue.message, literals)})
    plans = [r.plan for r in results if r.plan]
    plan = None
    if plans:
        p = plans[0]
        plan = {"pattern": p.get("pattern"),
                "fetch": [{"table": f.get("table"), "access_path": f.get("access_path")} for f in p.get("fetch", [])],
                "requires_cross_partition_scan": bool((p.get("guardrails") or {}).get("requires_cross_partition_scan"))}
    converted = [inventory_module.mask(c) for r in results for c in r.converted]
    return status, codes, findings, plan, converted


def propose(stmt, result, edition, row_limit, h2_indexes):
    """(route, payload, reason) as @rules/sql-migration.md §2 assigns it."""
    status, codes, category = result["status"], set(result["codes"]), stmt["category"]
    if stmt["language"] == "jpql":
        return "app_side", {"app_side": {"pattern": "read"}}, "JPQL is not SQL the converter reads"
    if category == "ddl":
        if status in ("OK", "WARN"):
            return "schema", {}, "the definition becomes part of the ScalarDB schema"
        if codes & ID_GENERATION or re.match(r"CREATE\s+SEQUENCE\b", stmt["sql"], re.I):
            return "app_side", {"app_side": {"pattern": "id_generation"}}, \
                "ScalarDB has no sequences or identity columns; the application generates IDs"
        return "redesign", {"redesign": {"proposal": "replace the object the converter rejected with an application or schema design"}}, \
            "ScalarDB has no equivalent object"
    if category in ("view", "routine", "trigger"):
        return "redesign", {"redesign": {"proposal": f"re-express the {category} as application code or as queries; ScalarDB has no {category}s"}}, \
            f"ScalarDB has no {category}s"
    if category == "transaction":
        return "retire", {"retire": {"evidence": "transaction control moves to the ScalarDB transaction API in the generated code"}}, \
            "transaction control is not a statement in ScalarDB code"
    if status in ("OK", "WARN"):
        if edition == "enterprise_premium":
            return "scalardb_sql", {}, "the converted statement is valid ScalarDB SQL"
        return "core_api", {}, f"convertible, but {edition} has no ScalarDB SQL; the same access through the Core API"
    if status == "PLANNED":
        return "plan", {"plan": {"row_limit": row_limit, "h2_indexes": h2_indexes}}, \
            "read-only; fetch through ScalarDB and run the original SQL in H2"
    if codes & NO_KEY_PATH:
        return "redesign", {"redesign": {"proposal": "add a key or an index the statement can read by, or a summary table"}}, \
            "no key or index the storage can read it by"
    if category == "query":
        return "app_side", {"app_side": {"pattern": "read"}}, "a read neither ScalarDB SQL nor H2 can run"
    if codes & ID_GENERATION:
        pattern = "id_generation"
    elif codes & APP_CLOCK:
        pattern = "app_clock"
    elif codes & CONDITIONAL_WRITE:
        pattern = "conditional_write"
    else:
        pattern = "rmw"
    return "app_side", {"app_side": {"pattern": pattern}}, "a write ScalarDB SQL cannot express; read, compute and write in one transaction"


def convert(inventory, project_dir, edition, storage, namespace, schema_file=None, key_hints=None, live_runs=(),
            isolation="SERIALIZABLE", row_limit=None, h2_indexes=False, scalardb_version=None,
            inventory_path=DEFAULT_INVENTORY, schema_path=DEFAULT_SCHEMA):
    if edition not in EDITIONS or storage not in STORAGES or isolation not in ISOLATIONS:
        raise ValueError("edition, storage or isolation outside the supported values")
    logging.getLogger("sqlglot").setLevel(logging.ERROR)
    dialect = inventory["source_dialect"]
    row_limit = row_limit or DEFAULT_ROW_LIMIT
    hints = {k.lower(): v for k, v in (key_hints or {}).items()}
    expected_rows, provenance = rows_from_live_runs(live_runs)
    registry = SchemaRegistry.from_schema_loader_json(str(schema_file)) if schema_file else SchemaRegistry()
    from_schema_file = {t.name.lower() for t in registry.tables()}
    options = dict(key_hints=hints, storage=storage, expected_rows=expected_rows, isolation=isolation,
                   row_limit=row_limit, h2_indexes=h2_indexes)

    statements = inventory.get("statements", [])
    results, skipped, texts, key_origin = [], [], {}, {}
    for stmt in statements:
        try:
            texts[stmt["id"]] = inventory_module.statement_text(stmt, project_dir=project_dir)
        except inventory_module.StaleEvidence:
            skipped.append({"id": stmt["id"], "reason": "stale_evidence"})
    # DDL first, so every query is judged against the whole schema
    ordered = sorted((s for s in statements if s["id"] in texts), key=lambda s: s["category"] != "ddl")
    for stmt in ordered:
        entry = {"id": stmt["id"], "source_masked": stmt["sql"]}
        if stmt["language"] == "jpql":
            entry.update(status="ERROR", codes=["JPQL"], pattern=None, plan=None, converted_masked=[],
                         findings=[{"severity": "ERROR", "code": "JPQL", "message": "JPQL is not SQL; the converter does not read it"}])
        else:
            before = {t.name.lower() for t in registry.tables()}
            converted, registry = convert_script(texts[stmt["id"]], dialect, registry, **options)
            for table in {t.name.lower() for t in registry.tables()} - before:
                key_origin[table] = "investigation" if stmt["origin"]["kind"] == "db_design_run" else "source_ddl"
            if not converted:
                continue
            status, codes, findings, plan, masked = _merge(converted, texts[stmt["id"]])
            entry.update(status=status, codes=codes, pattern=(plan or {}).get("pattern"), plan=plan,
                         converted_masked=masked, findings=findings)
        results.append(entry)
    order = {s["id"]: n for n, s in enumerate(statements)}
    results.sort(key=lambda r: order[r["id"]])

    schema = {f"{namespace}.{t.name}": t.to_schema_loader() for t in registry.tables()}
    keys = []
    for table in registry.tables():
        name = table.name.lower()
        source = "user" if name in hints else "design-scalardb" if name in from_schema_file \
            else key_origin.get(name, "source_ddl")
        keys.append({"table": table.name, "partition_key": list(table.partition_key),
                     "clustering_key": list(table.clustering_key), "secondary_indexes": list(table.secondary_indexes),
                     "source": source,
                     "rationale": {"user": "key split given by the user",
                                   "design-scalardb": "taken from the existing ScalarDB schema",
                                   "investigation": "investigated primary key: first column partitions, the rest cluster",
                                   "source_ddl": "source DDL primary key: first column partitions, the rest cluster"}[source]})

    by_id = {s["id"]: s for s in statements}
    draft_statements, open_items = [], []
    for result in results:
        stmt = by_id[result["id"]]
        route, payload, reason = propose(stmt, result, edition, row_limit, h2_indexes)
        converter = {"status": result["status"], "codes": result["codes"]}
        if result["pattern"]:
            converter["pattern"] = result["pattern"]
        entry = {"id": result["id"], "converter": converter, "route": route, "rationale": "proposed: " + reason}
        entry.update(payload)
        semantics = [f["message"] for f in result["findings"] if f["code"] == "APP_SEMANTICS"]
        if route == "app_side" and semantics:
            entry["app_side"]["semantics"] = [{"note": note, "handling": ""} for note in semantics]
            open_items.append({"id": result["id"], "question": "how the application code keeps each semantics note"})
        # object IDs of an investigation run are not traceability nodes; the skill adds FR- / AGG- upstreams
        entry["upstream"] = []
        entry["verification"] = {"status": "pending"}
        if stmt["dynamic"]:
            open_items.append({"id": result["id"], "question": "which renderings of this dynamic statement exist, and does "
                                                               "each convert (confirm before any automatic route)"})
        if stmt["language"] == "jpql":
            open_items.append({"id": result["id"], "question": "rewrite the JPQL as SQL and convert it, reimplement it, "
                                                               "or redesign the use case"})
        draft_statements.append(entry)
    for item in skipped:
        open_items.append({"id": item["id"], "question": "the source changed since the inventory; re-run the inventory"})

    target = {"edition": edition, "storage": storage, "namespace": namespace}
    if scalardb_version:
        target["scalardb_version"] = scalardb_version
    draft = {"schema_version": 1, "status": "draft", "source": {"dialect": dialect}, "target": target,
             "inputs": {"inventory": inventory_path, "schema": schema_path,
                        "db_runs": [s["path"] for s in inventory.get("sources", []) if s.get("kind") == "db_run"],
                        "live_runs": [str(r) for r in live_runs or ()]},
             "keys": keys, "statements": draft_statements, "open": open_items}
    conversion = {"schema_version": 1, "dialect": dialect, "edition": edition, "storage": storage,
                  "namespace": namespace, "isolation": isolation, "row_limit": row_limit, "expected_rows": provenance,
                  "results": results, "skipped": skipped}
    return {"schema": schema, "conversion": conversion, "draft": draft}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Convert an SQL inventory and draft the migration manifest.")
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--edition", required=True, choices=EDITIONS)
    ap.add_argument("--storage", required=True, choices=STORAGES)
    ap.add_argument("--namespace", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--schema", help="existing Schema Loader JSON (for example from design-scalardb)")
    ap.add_argument("--keys", action="append", help="table=partition1,partition2/clustering1 (repeatable)")
    ap.add_argument("--live-run", action="append", default=[], help="investigate-db-live run for row estimates")
    ap.add_argument("--isolation", default="SERIALIZABLE", choices=ISOLATIONS)
    ap.add_argument("--row-limit", type=int, default=DEFAULT_ROW_LIMIT)
    ap.add_argument("--h2-indexes", action="store_true")
    ap.add_argument("--scalardb-version")
    ap.add_argument("--project-dir", default=".")
    args = ap.parse_args(argv)
    project = Path(args.project_dir)
    out_dir = Path(args.out_dir)

    def rel(path):
        return inventory_module._rel(project, Path(path))
    try:
        inv = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
        out = convert(inv, project, args.edition, args.storage, args.namespace, args.schema, _parse_keys(args.keys),
                      args.live_run, args.isolation, args.row_limit, args.h2_indexes, args.scalardb_version,
                      rel(args.inventory), rel(out_dir / "schema.json"))
    except (OSError, ValueError, KeyError) as exc:
        print(f"convert_inventory failed: {exc}", file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, key in (("schema.json", "schema"), ("conversion.json", "conversion"),
                      ("sql-migration-manifest.draft.json", "draft")):
        (out_dir / name).write_text(json.dumps(out[key], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    counts = {}
    for r in out["conversion"]["results"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"{len(out['conversion']['results'])} converted {counts}, {len(out['conversion']['skipped'])} skipped, "
          f"{len(out['draft']['open'])} open questions -> {out_dir}")
    return 2 if out["conversion"]["skipped"] else 0


if __name__ == "__main__":
    sys.exit(main())
