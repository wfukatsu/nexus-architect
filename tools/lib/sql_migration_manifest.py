"""Validation for the SQL migration manifest `/architect:design-sql-migration` emits.

`reports/03_design/sql-migration/sql-migration-manifest.json` is the canonical record of how each
inventoried statement moves to ScalarDB — the Markdown views are its projection — so the rules of
@rules/sql-migration.md are checked here rather than trusted to prose. Every rule below guards a
mistake that reads fine: a statement nobody decided, an ERROR statement routed to ScalarDB SQL,
ScalarDB SQL chosen for an edition without it, dynamic SQL routed on the converter's word for one
rendering, application-side work that drops the semantics the converter flagged, a key naming a
column the schema does not have, evidence that no longer exists, a statement called verified with
nothing to show for it.

Usage:  python3 tools/lib/sql_migration_manifest.py <project_dir>   (exit 1 on violations)
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manifest_common import duplicates, load_manifest, report  # noqa: E402,F401

BASE = os.path.join("reports", "03_design", "sql-migration")
MANIFEST_PATH = os.path.join(BASE, "sql-migration-manifest.json")
INVENTORY_PATH = os.path.join(BASE, "sql-inventory.json")
SCHEMA_PATH = os.path.join(BASE, "schema.json")
TRACEABILITY_PATH = os.path.join("work", "traceability.json")
LABEL = "sql migration manifest"

ROUTES = ("schema", "scalardb_sql", "core_api", "plan", "app_side", "redesign", "retire")
STATUSES = ("OK", "WARN", "PLANNED", "ERROR")
CONVERTED = {"schema", "scalardb_sql", "core_api", "app_side", "redesign", "retire"}
ALLOWED_ROUTES = {"OK": CONVERTED, "WARN": CONVERTED,
                  "PLANNED": {"plan", "app_side", "redesign", "retire"},
                  "ERROR": {"app_side", "redesign", "retire"}}
AUTOMATIC_ROUTES = {"schema", "scalardb_sql", "core_api", "plan"}
QUERY_ROUTES = {"scalardb_sql", "core_api", "plan"}
JPQL_ROUTES = {"app_side", "redesign", "retire"}
EDITIONS = ("community", "enterprise_standard", "enterprise_premium")
SQL_EDITION = "enterprise_premium"
STORAGES = ("jdbc", "cassandra")
APP_PATTERNS = ("read", "rmw", "conditional_write", "id_generation", "app_clock")
KEY_SOURCES = ("design-scalardb", "investigation", "user")
VERIFICATION_STATUSES = ("pending", "verified", "failed", "skipped")
VERIFICATION_METHODS = ("golden", "difftest", "plan_validate", "unit")


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _list(value):
    return value if isinstance(value, list) else []


def _schema_tables(schema):
    """{table name: set of columns} from Schema Loader JSON keyed by `namespace.table`."""
    tables = {}
    for qualified, spec in (schema or {}).items():
        if isinstance(qualified, str) and isinstance(spec, dict):
            columns = spec.get("columns")
            tables[qualified.rpartition(".")[2]] = set(columns) if isinstance(columns, dict) else set()
    return tables


def _validate_target(manifest, errors):
    target = manifest.get("target")
    if not isinstance(target, dict):
        errors.append("target: must be an object")
        return None
    edition = target.get("edition")
    if edition not in EDITIONS:
        errors.append("target.edition must be one of %s" % "/".join(EDITIONS))
        edition = None
    if target.get("storage") not in STORAGES:
        errors.append("target.storage must be one of %s" % "/".join(STORAGES))
    return edition


def _validate_route_payload(sid, entry, route, codes, errors):
    if route == "app_side":
        app = entry.get("app_side") if isinstance(entry.get("app_side"), dict) else {}
        if app.get("pattern") not in APP_PATTERNS:
            errors.append("%s: app_side.pattern must be one of %s" % (sid, "/".join(APP_PATTERNS)))
        if "APP_SEMANTICS" in codes:
            semantics = app.get("semantics")
            if not isinstance(semantics, list) or not semantics:
                errors.append("%s: APP_SEMANTICS findings need app_side.semantics — what the code keeps, and how" % sid)
            else:
                for j, item in enumerate(semantics):
                    if not isinstance(item, dict) or not _text(item.get("note")) or not _text(item.get("handling")):
                        errors.append("%s: app_side.semantics[%d] needs note and handling" % (sid, j))
    elif route == "redesign":
        redesign = entry.get("redesign")
        if not isinstance(redesign, dict) or not _text(redesign.get("proposal")):
            errors.append("%s: redesign.proposal is required" % sid)
    elif route == "retire":
        retire = entry.get("retire")
        if not isinstance(retire, dict) or not _text(retire.get("evidence")):
            errors.append("%s: retire.evidence is required — why the statement is not migrated" % sid)
    elif route == "plan":
        plan = entry.get("plan")
        limit = plan.get("row_limit") if isinstance(plan, dict) else None
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            errors.append("%s: plan.row_limit must be a positive integer" % sid)


def _validate_verification(sid, entry, errors):
    verification = entry.get("verification")
    if not isinstance(verification, dict):
        errors.append("%s: verification must be an object" % sid)
        return
    status = verification.get("status")
    if status not in VERIFICATION_STATUSES:
        errors.append("%s: verification.status must be one of %s" % (sid, "/".join(VERIFICATION_STATUSES)))
        return
    if status in ("verified", "failed"):
        if verification.get("method") not in VERIFICATION_METHODS:
            errors.append("%s: verification.method must be one of %s" % (sid, "/".join(VERIFICATION_METHODS)))
        if not _text(verification.get("evidence")):
            errors.append("%s: verification.evidence is required when status is %s" % (sid, status))
    if status == "skipped" and not _text(verification.get("reason")):
        errors.append("%s: verification.reason is required when status is skipped" % sid)


def _validate_keys(manifest, schema, errors):
    keys = manifest.get("keys", [])
    if not isinstance(keys, list):
        errors.append("keys: must be an array")
        return
    tables = _schema_tables(schema) if isinstance(schema, dict) else None
    for i, key in enumerate(keys):
        where = "keys[%d]" % i
        if not isinstance(key, dict):
            errors.append("%s: entry must be an object" % where)
            continue
        table = key.get("table")
        partition = key.get("partition_key")
        if not isinstance(partition, list) or not partition:
            errors.append("%s: partition_key must be a non-empty array" % where)
        if key.get("source") not in KEY_SOURCES:
            errors.append("%s: source must be one of %s" % (where, "/".join(KEY_SOURCES)))
        if not _text(key.get("rationale")):
            errors.append("%s: rationale is required" % where)
        if tables is None:
            continue
        if table not in tables:
            errors.append("%s: table %s is not in the schema" % (where, table))
            continue
        for column in _list(partition) + _list(key.get("clustering_key")) + _list(key.get("secondary_indexes")):
            if column not in tables[table]:
                errors.append("%s: %s is not a column of %s" % (where, column, table))


def _validate_evidence(project_dir, statements, errors):
    for stmt in statements:
        origin = stmt.get("origin") if isinstance(stmt, dict) else None
        if not isinstance(origin, dict) or not _text(origin.get("path")):
            continue
        sid = stmt.get("id")
        path = os.path.join(project_dir, origin["path"])
        if not os.path.isfile(path):
            errors.append("%s: source file %s does not exist" % (sid, origin["path"]))
            continue
        lines = origin.get("lines")
        if not (isinstance(lines, list) and len(lines) == 2 and all(isinstance(n, int) for n in lines)):
            errors.append("%s: origin.lines must be [first, last]" % sid)
            continue
        with open(path, "rb") as handle:
            count = handle.read().count(b"\n") + 1
        if lines[1] > count or lines[0] < 1:
            errors.append("%s: origin lines %d-%d are past the end of %s" % (sid, lines[0], lines[1], origin["path"]))


def validate_sql_migration_manifest(manifest, project_dir=None, inventory=None, schema=None, traceability=None):
    """Violations of @rules/sql-migration.md. `inventory` / `schema` / `traceability` are the parsed
    side files; a check that needs one is skipped when it is None."""
    if not isinstance(manifest, dict):
        return ["%s: must be an object" % LABEL]
    errors = []
    edition = _validate_target(manifest, errors)
    inventory_statements = [s for s in _list((inventory or {}).get("statements")) if isinstance(s, dict)] \
        if isinstance(inventory, dict) else None
    by_id = {s.get("id"): s for s in inventory_statements or []}
    nodes = {n.get("id") for n in _list(traceability.get("nodes")) if isinstance(n, dict)} \
        if isinstance(traceability, dict) else None

    statements = manifest.get("statements")
    if not isinstance(statements, list):
        errors.append("statements: must be an array")
        statements = []
    decided = {}
    for i, entry in enumerate(statements):
        if not isinstance(entry, dict):
            errors.append("statements[%d]: entry must be an object" % i)
            continue
        sid = entry.get("id") if _text(entry.get("id")) else "statements[%d]" % i
        decided[sid] = decided.get(sid, 0) + 1
        if decided[sid] == 2:
            errors.append("%s: decided more than once" % sid)
        if decided[sid] > 1:
            continue
        if inventory_statements is not None and sid not in by_id:
            errors.append("%s: decision for a statement not in the inventory" % sid)
        stmt = by_id.get(sid, {})

        converter = entry.get("converter")
        status, codes = None, []
        if not isinstance(converter, dict):
            errors.append("%s: converter must be an object" % sid)
        else:
            status = converter.get("status")
            codes = _list(converter.get("codes"))
            if status not in STATUSES:
                errors.append("%s: converter.status must be one of %s" % (sid, "/".join(STATUSES)))
                status = None
        if not _text(entry.get("rationale")):
            errors.append("%s: rationale is required" % sid)

        route = entry.get("route")
        if route not in ROUTES:
            errors.append("%s: route must be one of %s" % (sid, "/".join(ROUTES)))
        else:
            if status and route not in ALLOWED_ROUTES[status]:
                errors.append("%s: converter status %s cannot take route %s" % (sid, status, route))
            if route == "schema" and stmt and stmt.get("category") != "ddl":
                errors.append("%s: route schema is only for DDL" % sid)
            if stmt.get("category") == "ddl" and route in QUERY_ROUTES:
                errors.append("%s: DDL cannot take route %s" % (sid, route))
            if stmt.get("language") == "jpql" and route not in JPQL_ROUTES:
                errors.append("%s: JPQL cannot take route %s" % (sid, route))
            if route == "scalardb_sql" and edition and edition != SQL_EDITION:
                errors.append("%s: route scalardb_sql needs ScalarDB SQL (%s); use core_api or app_side under %s"
                              % (sid, SQL_EDITION, edition))
            if stmt.get("dynamic") and route in AUTOMATIC_ROUTES:
                confirmation = entry.get("confirmation")
                if not (isinstance(confirmation, dict) and confirmation.get("by") == "user"
                        and _text(confirmation.get("note"))):
                    errors.append("%s: dynamic statement on route %s needs confirmation by the user "
                                  "(which variants were expanded and converted)" % (sid, route))
            _validate_route_payload(sid, entry, route, codes, errors)

        upstream = entry.get("upstream", [])
        if not isinstance(upstream, list):
            errors.append("%s: upstream must be an array" % sid)
        elif nodes is not None:
            for node in upstream:
                if node not in nodes:
                    errors.append("%s: upstream %s is not a node in %s" % (sid, node, TRACEABILITY_PATH))
        _validate_verification(sid, entry, errors)

    if inventory_statements is not None:
        for stmt in inventory_statements:
            if stmt.get("id") not in decided:
                errors.append("%s: in the inventory but has no decision" % stmt.get("id"))
    _validate_keys(manifest, schema, errors)
    if project_dir is not None and inventory_statements is not None:
        _validate_evidence(project_dir, inventory_statements, errors)
    return errors


def _read_json(project_dir, relative, label, errors, required=True):
    path = os.path.join(project_dir, relative)
    if not os.path.isfile(path):
        if required:
            errors.append("%s: %s does not exist" % (label, relative))
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError) as exc:
        errors.append("%s: %s is unreadable — %s" % (label, relative, exc))
        return None


def _validate_project(manifest, project_dir):
    errors = []
    inputs = manifest.get("inputs") if isinstance(manifest, dict) and isinstance(manifest.get("inputs"), dict) else {}
    inventory = _read_json(project_dir, inputs.get("inventory") or INVENTORY_PATH, "inputs.inventory", errors)
    schema = _read_json(project_dir, inputs.get("schema") or SCHEMA_PATH, "inputs.schema", errors)
    traceability = _read_json(project_dir, TRACEABILITY_PATH, "traceability", errors, required=False)
    return errors + validate_sql_migration_manifest(manifest, project_dir, inventory, schema, traceability)


def load_and_validate(project_dir):
    return load_manifest(project_dir, MANIFEST_PATH, LABEL, _validate_project)


def main(argv):
    project_dir = argv[1] if len(argv) > 1 else "."
    manifest, errors = load_and_validate(project_dir)
    return report(manifest, errors, project_dir, LABEL, "statements")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
