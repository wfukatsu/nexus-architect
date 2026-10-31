#!/usr/bin/env python3
"""Executable check of the SQL migration contract.

`/architect:design-sql-migration` decides one route per inventoried statement (@rules/sql-migration.md).
Each case below is a manifest that reads plausibly and is wrong — a statement nobody decided, an ERROR
statement sent to ScalarDB SQL, ScalarDB SQL chosen for an edition that has none, a dynamic statement
routed automatically without asking, application-side work that drops the semantics it must keep —
and the suite fails if the validator would let it through.

    python3 tools/lib/sql_migration_manifest.test.py

Exit 0 = all checks pass, 1 = at least one failed (the repo-wide convention).
"""

import copy
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sql_migration_manifest import (INVENTORY_PATH, MANIFEST_PATH,  # noqa: E402
                                    SCHEMA_PATH, load_and_validate,
                                    validate_sql_migration_manifest)

FAILURES = 0
CHECKS = 0


def check(label, condition, detail=""):
    global FAILURES, CHECKS
    CHECKS += 1
    print("  [%s] %s%s" % ("ok" if condition else "FAIL", label,
                           " — " + str(detail) if detail and not condition else ""))
    if not condition:
        FAILURES += 1


def statement(sid, category, origin_kind="app_code", path="src/OrderMapper.xml", lines=(2, 3), **extra):
    return dict({"id": sid, "category": category, "language": "sql", "dynamic": False, "dynamic_reasons": [],
                 "sql": "SELECT ...", "origin": {"kind": origin_kind, "path": path, "lines": list(lines)}}, **extra)


INVENTORY = {
    "schema_version": 1,
    "source_dialect": "oracle",
    "statements": [
        statement("SQM-001", "ddl", "sql_file", "db/schema.sql", (1, 1)),
        statement("SQM-002", "query"),
        statement("SQM-003", "query", lines=(4, 5)),
        statement("SQM-004", "query", lines=(6, 7)),
        statement("SQM-005", "dml", lines=(8, 8), dynamic=True, dynamic_reasons=["mybatis_if"]),
        statement("SQM-006", "query", lines=(9, 9), language="jpql"),
        statement("SQM-007", "query", lines=(2, 2), sql="SELECT o.order_no, c.name FROM orders o JOIN customers c ON c.id = o.customer_id WHERE o.status = ?"),
    ],
}

SCHEMA = {"shop.orders": {"transaction": True, "partition-key": ["customer_id"], "clustering-key": ["order_no ASC"],
                          "columns": {"customer_id": "BIGINT", "order_no": "BIGINT", "status": "TEXT", "total": "BIGINT"},
                          "secondary-index": ["status"]}}

WELL_FORMED = {
    "schema_version": 1,
    "source": {"dialect": "oracle"},
    "target": {"scalardb_version": "3.20", "edition": "enterprise_premium", "storage": "jdbc", "namespace": "shop",
               "native_jdbc": {"engine": "postgresql", "isolation_level": "SNAPSHOT", "database": "shopdb"}},
    "inputs": {"inventory": INVENTORY_PATH, "schema": SCHEMA_PATH,
               "db_runs": ["reports/01_analysis/database-investigation/shop/design/r1"]},
    "keys": [{"table": "orders", "partition_key": ["customer_id"], "clustering_key": ["order_no"],
              "secondary_indexes": ["status"], "source": "investigation", "rationale": "orders are read per customer"}],
    "statements": [
        {"id": "SQM-001", "converter": {"status": "WARN", "codes": ["TYPE"]}, "route": "schema",
         "rationale": "table maps to shop.orders; NUMBER(10,2) scaled to BIGINT cents", "upstream": [],
         "verification": {"status": "pending"}},
        {"id": "SQM-002", "converter": {"status": "OK", "codes": []}, "route": "scalardb_sql",
         "rationale": "GET by full primary key", "upstream": ["FR-001"],
         "verification": {"status": "verified", "method": "difftest", "evidence": "reports/09_verification/sql-migration/difftest.json"}},
        {"id": "SQM-003", "converter": {"status": "PLANNED", "codes": ["PROJECTION"], "pattern": "P1"}, "route": "plan",
         "rationale": "expression in the select list; ~2k rows per call", "plan": {"row_limit": 10000, "h2_indexes": False},
         "verification": {"status": "skipped", "reason": "no source database authorized yet"}},
        {"id": "SQM-004", "converter": {"status": "ERROR", "codes": ["WINDOW", "APP_SEMANTICS"]}, "route": "app_side",
         "rationale": "LAG over monthly totals; H2 cannot run the CONNECT BY it also uses",
         "app_side": {"pattern": "read", "semantics": [{"note": "LAG / LEAD skip months without rows", "handling": "Windows.lag"}]},
         "verification": {"status": "failed", "method": "golden", "evidence": "reports/09_verification/sql-migration/golden-SQM-004.json"}},
        {"id": "SQM-005", "converter": {"status": "WARN", "codes": ["CROSS_PARTITION"]}, "route": "scalardb_sql",
         "rationale": "both expansions of the <if> convert",
         "confirmation": {"by": "user", "note": "status filter present and absent; both variants converted"},
         "verification": {"status": "pending"}},
        {"id": "SQM-006", "converter": {"status": "ERROR", "codes": ["PARSE"]}, "route": "redesign",
         "rationale": "JPQL over a join ScalarDB cannot serve", "redesign": {"proposal": "summary table keyed by customer"},
         "verification": {"status": "pending"}},
        {"id": "SQM-007", "converter": {"status": "ERROR", "codes": ["JOIN"]}, "route": "native_jdbc",
         "rationale": "the reporting module keeps its native SQL on shopdb through ScalarDB Native JDBC",
         "verification": {"status": "pending"}},
    ],
}

TRACEABILITY = {"schema_version": 1, "nodes": [{"id": "FR-001", "type": "requirement", "upstream": []}]}


def entry(m, sid):
    return next(s for s in m["statements"] if s["id"] == sid)


def rejects(label, mutate, *, expect, edit_inventory=None):
    """Mutate the well-formed fixture and require the validator to name the defect."""
    manifest = mutate(copy.deepcopy(WELL_FORMED))
    inventory = copy.deepcopy(INVENTORY)
    if edit_inventory:
        edit_inventory(inventory)
    try:
        errors = validate_sql_migration_manifest(manifest, inventory=inventory, schema=SCHEMA, traceability=TRACEABILITY)
    except Exception as exc:  # a crash is the one answer a validator may never give
        check(label, False, "validator raised %r" % exc)
        return
    check(label, any(expect in error for error in errors), errors or "no violation reported")


def mutated(fn):
    def apply(m):
        fn(m)
        return m
    return apply


print("A well-formed manifest passes")
errors = validate_sql_migration_manifest(copy.deepcopy(WELL_FORMED), inventory=INVENTORY, schema=SCHEMA,
                                         traceability=TRACEABILITY)
check("no violation on the well-formed fixture", errors == [], errors)

print("Every inventoried statement is decided exactly once")
rejects("a statement without a decision", mutated(lambda m: m["statements"].pop()), expect="SQM-007: in the inventory but has no decision")
rejects("a decision for a statement the inventory lacks",
        mutated(lambda m: m["statements"].append(dict(copy.deepcopy(entry(m, "SQM-002")), id="SQM-099"))),
        expect="SQM-099: decision for a statement not in the inventory")
rejects("two decisions for one statement",
        mutated(lambda m: m["statements"].append(copy.deepcopy(entry(m, "SQM-002")))), expect="SQM-002: decided more than once")

print("The route follows the converter, the statement and the edition")
rejects("an unknown route", mutated(lambda m: entry(m, "SQM-002").update(route="rewrite")), expect="SQM-002: route must be one of")
rejects("an ERROR statement sent to ScalarDB SQL", mutated(lambda m: entry(m, "SQM-004").update(route="scalardb_sql")),
        expect="SQM-004: converter status ERROR cannot take route scalardb_sql")
rejects("a PLANNED statement sent to the Core API", mutated(lambda m: entry(m, "SQM-003").update(route="core_api")),
        expect="SQM-003: converter status PLANNED cannot take route core_api")
rejects("an unknown converter status", mutated(lambda m: entry(m, "SQM-002")["converter"].update(status="MAYBE")),
        expect="SQM-002: converter.status must be one of")
rejects("a query sent to the schema route", mutated(lambda m: entry(m, "SQM-002").update(route="schema")),
        expect="SQM-002: route schema is only for DDL")
rejects("JPQL sent to ScalarDB SQL",
        mutated(lambda m: entry(m, "SQM-006").update(route="scalardb_sql", converter={"status": "OK", "codes": []})),
        expect="SQM-006: JPQL cannot take route scalardb_sql")
rejects("ScalarDB SQL without Enterprise Premium", mutated(lambda m: m["target"].update(edition="enterprise_standard")),
        expect="SQM-002: route scalardb_sql needs ScalarDB SQL (enterprise_premium)")
rejects("an unknown edition", mutated(lambda m: m["target"].update(edition="premium")), expect="target.edition must be one of")
rejects("an unknown storage", mutated(lambda m: m["target"].update(storage="dynamo")), expect="target.storage must be one of")

print("Dynamic SQL is never routed automatically on the tool's word")
rejects("a dynamic statement on an automatic route without confirmation",
        mutated(lambda m: entry(m, "SQM-005").pop("confirmation")),
        expect="SQM-005: dynamic statement on route scalardb_sql needs confirmation by the user")
rejects("a confirmation that is not the user's",
        mutated(lambda m: entry(m, "SQM-005").update(confirmation={"by": "converter", "note": "looked fine"})),
        expect="SQM-005: dynamic statement on route scalardb_sql needs confirmation by the user")

print("Each route carries what acting on it needs")
rejects("a decision without a rationale", mutated(lambda m: entry(m, "SQM-002").update(rationale=" ")), expect="SQM-002: rationale is required")
rejects("application-side work without a pattern", mutated(lambda m: entry(m, "SQM-004")["app_side"].pop("pattern")),
        expect="SQM-004: app_side.pattern must be one of")
rejects("semantics findings the application-side plan ignores",
        mutated(lambda m: entry(m, "SQM-004")["app_side"].update(semantics=[])),
        expect="SQM-004: APP_SEMANTICS findings need app_side.semantics")
rejects("a semantics entry without its handling",
        mutated(lambda m: entry(m, "SQM-004")["app_side"]["semantics"][0].pop("handling")),
        expect="SQM-004: app_side.semantics[0] needs note and handling")
rejects("a redesign without a proposal", mutated(lambda m: entry(m, "SQM-006").update(redesign={})),
        expect="SQM-006: redesign.proposal is required")
rejects("a retirement without evidence", mutated(lambda m: entry(m, "SQM-006").update(route="retire", redesign=None)),
        expect="SQM-006: retire.evidence is required")
rejects("a plan without its row limit", mutated(lambda m: entry(m, "SQM-003").update(plan={})),
        expect="SQM-003: plan.row_limit must be a positive integer")

print("Native JDBC keeps a statement native only where the driver accepts it")


def native_sql(sql):
    def edit(inv):
        next(s for s in inv["statements"] if s["id"] == "SQM-007")["sql"] = sql
    return edit


def accepts(label, mutate=None, *, edit_inventory=None):
    manifest = mutate(copy.deepcopy(WELL_FORMED)) if mutate else copy.deepcopy(WELL_FORMED)
    inventory = copy.deepcopy(INVENTORY)
    if edit_inventory:
        edit_inventory(inventory)
    errors = validate_sql_migration_manifest(manifest, inventory=inventory, schema=SCHEMA, traceability=TRACEABILITY)
    check(label, errors == [], errors)


accepts("JPQL may stay native — the driver wraps the vendor driver the ORM talks to",
        mutated(lambda m: entry(m, "SQM-006").update(route="native_jdbc", redesign=None)))
accepts("an ERROR verdict does not bar the native route — the converter is not in the path",
        mutated(lambda m: entry(m, "SQM-004").update(route="native_jdbc", app_side=None)))
accepts("a community edition may keep statements native (no ScalarDB SQL involved)",
        mutated(lambda m: (m["target"].update(edition="community"),
                           entry(m, "SQM-002").update(route="native_jdbc"),
                           entry(m, "SQM-005").update(route="native_jdbc"))))
accepts("a plain INSERT ... VALUES with a scalar subquery in a value is not INSERT ... SELECT",
        edit_inventory=native_sql("INSERT INTO orders (customer_id, order_no, total) VALUES (?, ?, (SELECT MAX(total) FROM orders))"))
rejects("DDL kept native", mutated(lambda m: entry(m, "SQM-001").update(route="native_jdbc")),
        expect="SQM-001: DDL cannot take route native_jdbc")
rejects("the native route without the shared connection facts", mutated(lambda m: m["target"].pop("native_jdbc")),
        expect="target.native_jdbc is required when a statement takes route native_jdbc")
rejects("the native route on a Cassandra backend", mutated(lambda m: m["target"].update(storage="cassandra")),
        expect="route native_jdbc needs target.storage jdbc")
rejects("an unknown engine", mutated(lambda m: m["target"]["native_jdbc"].update(engine="db2")),
        expect="target.native_jdbc.engine must be one of")
rejects("an unknown isolation level", mutated(lambda m: m["target"]["native_jdbc"].update(isolation_level="REPEATABLE_READ")),
        expect="target.native_jdbc.isolation_level must be one of")
rejects("SERIALIZABLE on Oracle", mutated(lambda m: m["target"]["native_jdbc"].update(engine="oracle", isolation_level="SERIALIZABLE")),
        expect="SERIALIZABLE is refused on oracle (0AN01)")
rejects("no database named", mutated(lambda m: m["target"]["native_jdbc"].update(database="")),
        expect="target.native_jdbc.database is required")
rejects("a dynamic statement kept native without the user's confirmation",
        mutated(lambda m: entry(m, "SQM-005").update(route="native_jdbc", confirmation=None)),
        expect="SQM-005: dynamic statement on route native_jdbc needs confirmation by the user")
for label, sql in (
        ("INSERT ... SELECT", "INSERT INTO orders_archive (customer_id, order_no) SELECT customer_id, order_no FROM orders WHERE status = ?"),
        ("INSERT IGNORE", "INSERT IGNORE INTO orders (customer_id, order_no) VALUES (?, ?)"),
        ("MERGE", "MERGE INTO orders o USING staging s ON (o.order_no = s.order_no) WHEN MATCHED THEN UPDATE SET o.total = s.total"),
        ("ON CONFLICT", "INSERT INTO orders (customer_id, order_no) VALUES (?, ?) ON CONFLICT (customer_id, order_no) DO UPDATE SET total = ?"),
        ("ON DUPLICATE KEY UPDATE", "INSERT INTO orders (customer_id, order_no) VALUES (?, ?) ON DUPLICATE KEY UPDATE total = ?"),
        ("UPDATE reading another table", "UPDATE orders o SET total = (SELECT SUM(amount) FROM order_lines l WHERE l.order_no = o.order_no) WHERE o.customer_id = ?"),
        ("UPDATE reading another table", "UPDATE orders SET status = ? FROM customers WHERE customers.id = orders.customer_id"),
        ("DELETE reading another table", "DELETE FROM orders USING customers WHERE customers.id = orders.customer_id AND customers.closed = ?"),
        ("RETURNING on UPDATE / DELETE", "UPDATE orders SET status = ? WHERE order_no = ? RETURNING total"),
        ("SELECT ... INTO", "SELECT customer_id, order_no INTO orders_backup FROM orders WHERE status = ?"),
        ("CREATE TABLE AS SELECT", "CREATE TABLE orders_copy AS SELECT * FROM orders"),
        ("CALL / EXEC", "CALL recompute_totals(?)"),
        ("TRUNCATE", "TRUNCATE TABLE orders")):
    rejects("a native statement shaped as %s" % label, lambda m: m, edit_inventory=native_sql(sql),
            expect="SQM-007: statement shape the native driver refuses (0AN01): %s" % label)

print("Keys name tables and columns the schema declares")
rejects("a key for a table the schema lacks", mutated(lambda m: m["keys"][0].update(table="invoices")),
        expect="keys[0]: table invoices is not in the schema")
rejects("a key column the table lacks", mutated(lambda m: m["keys"][0].update(clustering_key=["order_date"])),
        expect="keys[0]: order_date is not a column of orders")
rejects("an empty partition key", mutated(lambda m: m["keys"][0].update(partition_key=[])),
        expect="keys[0]: partition_key must be a non-empty array")

print("Verification states what was proven, and how")
rejects("an unknown verification status", mutated(lambda m: entry(m, "SQM-002")["verification"].update(status="done")),
        expect="SQM-002: verification.status must be one of")
rejects("a verified statement without evidence", mutated(lambda m: entry(m, "SQM-002")["verification"].pop("evidence")),
        expect="SQM-002: verification.evidence is required when status is verified")
rejects("a skipped verification without a reason", mutated(lambda m: entry(m, "SQM-003")["verification"].pop("reason")),
        expect="SQM-003: verification.reason is required when status is skipped")
rejects("an unknown verification method", mutated(lambda m: entry(m, "SQM-004")["verification"].update(method="eyeball")),
        expect="SQM-004: verification.method must be one of")

print("Upstream IDs resolve in the traceability graph")
rejects("a dangling upstream ID", mutated(lambda m: entry(m, "SQM-002").update(upstream=["FR-404"])),
        expect="SQM-002: upstream FR-404 is not a node in work/traceability.json")

print("Hostile shapes are reported, not crashed on")
rejects("statements that are not an array", mutated(lambda m: m.update(statements={"SQM-001": {}})),
        expect="statements: must be an array")
rejects("an entry that is not an object", mutated(lambda m: m["statements"].append("SQM-008")),
        expect="statements[7]: entry must be an object")
rejects("a converter block that is not an object", mutated(lambda m: entry(m, "SQM-002").update(converter="OK")),
        expect="SQM-002: converter must be an object")
try:
    check("a manifest that is not an object is reported", any("must be an object" in e for e in validate_sql_migration_manifest(
        ["not", "a", "manifest"], inventory=INVENTORY, schema=SCHEMA, traceability=TRACEABILITY)))
except Exception as exc:
    check("a manifest that is not an object is reported", False, "validator raised %r" % exc)

print("From a project directory: inputs are read, and evidence lines must exist")
project = tempfile.mkdtemp()
try:
    def write(rel, content):
        path = os.path.join(project, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content if isinstance(content, str) else json.dumps(content))

    write("db/schema.sql", "CREATE TABLE orders (customer_id NUMBER(18), order_no NUMBER(18));\n")
    write("src/OrderMapper.xml", "\n".join("line %d" % n for n in range(1, 10)) + "\n")
    write(INVENTORY_PATH, INVENTORY)
    write(SCHEMA_PATH, SCHEMA)
    write(MANIFEST_PATH, WELL_FORMED)
    write("work/traceability.json", TRACEABILITY)
    _, errors = load_and_validate(project)
    check("a well-formed project passes", errors == [], errors)

    write("src/OrderMapper.xml", "line 1\nline 2\nline 3\n")
    _, errors = load_and_validate(project)
    check("an evidence line past the end of its file is reported",
          any("SQM-003: origin lines 4-5 are past the end of src/OrderMapper.xml" in e for e in errors), errors)

    os.remove(os.path.join(project, "db/schema.sql"))
    _, errors = load_and_validate(project)
    check("a missing source file is reported", any("SQM-001: source file db/schema.sql does not exist" in e for e in errors), errors)

    os.remove(os.path.join(project, INVENTORY_PATH))
    _, errors = load_and_validate(project)
    check("a manifest whose inventory is missing is reported", any("inputs.inventory" in e for e in errors), errors)

    os.remove(os.path.join(project, MANIFEST_PATH))
    manifest, errors = load_and_validate(project)
    check("a project that never ran the skill has nothing to check", manifest is None and errors == [], errors)
finally:
    shutil.rmtree(project)

print("\n%d/%d checks passed" % (CHECKS - FAILURES, CHECKS))
sys.exit(1 if FAILURES else 0)
