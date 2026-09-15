#!/usr/bin/env python3
"""Generating code from the migration manifest: one artifact per route, the full statement text recovered from
the source, and a refusal whenever the manifest no longer describes what the converter and the source say."""
import copy
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support  # noqa: E402

support.require_sqlglot()
import convert_inventory  # noqa: E402
import generate_migration  # noqa: E402
import inventory  # noqa: E402

sys.path.insert(0, str(support.ROOT.parents[2] / "tools" / "lib"))
from sql_migration_manifest import validate_sql_migration_manifest  # noqa: E402

SCRIPT = support.ROOT / "scripts/generate_migration.py"
BASE = Path("reports/03_design/sql-migration")

SQL = textwrap.dedent("""\
    CREATE TABLE orders (customer_id NUMBER(18), order_no NUMBER(18), status VARCHAR2(10), total NUMBER(18),
      PRIMARY KEY (customer_id, order_no));
    CREATE INDEX ix_status ON orders (status);
    CREATE SEQUENCE order_seq START WITH 1;
    SELECT total FROM orders WHERE customer_id = 1 AND order_no = 2 AND status = 'PAID-LITERAL';
    SELECT order_no FROM orders WHERE total > 100;
    SELECT NVL(status, 'SECRET-LITERAL') AS s FROM orders WHERE customer_id = 1;
    SELECT order_no, LEVEL FROM orders START WITH order_no = 1 CONNECT BY PRIOR order_no = customer_id;
    UPDATE orders SET total = total - 1 WHERE customer_id = 1 AND order_no = 2;
    SELECT order_no FROM orders WHERE status = 'X' ORDER BY total;
    INSERT INTO orders (customer_id, order_no, status, total) VALUES (1, order_seq.NEXTVAL, TO_CHAR(SYSDATE, 'YYYY'), 0);
    """)

VERSIONS = {"schema_version": 1, "checked_at": "2026-09-15T00:00:00Z", "confirmed_by_user": True, "entries": [
    {"name": "com.scalar-labs:scalardb", "chosen": "3.19.1"},
    {"name": "com.h2database:h2", "chosen": "2.5.250"},
    {"name": "com.google.code.gson:gson", "chosen": "2.14.0"},
    {"name": "org.junit:junit-bom", "chosen": "5.14.4"},
]}


def by_prefix(inv, prefix):
    return next(s["id"] for s in inv["statements"] if s["sql"].startswith(prefix))


class GenerateMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "db").mkdir()
        (self.root / "db/schema.sql").write_text(SQL)
        inv = inventory.build(source="oracle", sql_files=[self.root / "db/schema.sql"], project_dir=self.root)
        out = convert_inventory.convert(inv, project_dir=self.root, edition="enterprise_premium", storage="jdbc",
                                        namespace="shop")
        manifest = copy.deepcopy(out["draft"])
        manifest.pop("status")
        manifest.pop("open")
        self.ids = {name: by_prefix(inv, prefix) for name, prefix in {
            "get": "SELECT total", "scan": "SELECT order_no FROM orders WHERE total", "plan": "SELECT NVL",
            "tree": "SELECT order_no, LEVEL", "rmw": "UPDATE orders", "seq": "CREATE SEQUENCE",
            "redesign": "SELECT order_no FROM orders WHERE status", "table": "CREATE TABLE",
            "insert": "INSERT INTO orders"}.items()}
        for entry in manifest["statements"]:
            entry["rationale"] = "decided with the user"
            if entry["id"] == self.ids["scan"]:
                entry["route"] = "core_api"
            if entry["id"] == self.ids["redesign"]:
                entry.update(route="redesign", redesign={"proposal": "index total or keep a summary table"})
            for note in entry.get("app_side", {}).get("semantics", []):
                note["handling"] = "Hierarchy.connectBy"
        self.manifest = manifest
        for rel, data in ((BASE / "sql-inventory.json", inv), (BASE / "schema.json", out["schema"]),
                          (BASE / "sql-migration-manifest.json", manifest), (Path("work/version-decisions.json"), VERSIONS)):
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text(json.dumps(data))
        self.assertEqual(validate_sql_migration_manifest(manifest, inventory=inv, schema=out["schema"]), [])
        self.out = self.root / "generated/sql-migration/shop"

    def tearDown(self):
        self.tmp.cleanup()

    def generate(self, **kw):
        options = dict(project_dir=self.root, out_dir=self.out, package="com.example.shop.migration")
        options.update(kw)
        return generate_migration.generate(**options)

    def rewrite(self, rel, mutate):
        path = self.root / rel
        data = json.loads(path.read_text())
        mutate(data)
        path.write_text(json.dumps(data))

    def java(self, rel):
        return (self.out / "src/main/java/com/example/shop/migration" / rel).read_text()

    def test_scalardb_sql_statements_carry_the_full_converted_text(self):
        self.generate()
        sid = self.ids["get"]
        sql = (self.out / f"src/main/resources/sql/{sid}.sql").read_text()
        self.assertIn("'PAID-LITERAL'", sql)
        constants = self.java("ScalarDbSqlStatements.java")
        self.assertIn(sid.replace("-", "_") + " =", constants)
        self.assertIn("PAID-LITERAL", constants)

    def test_plans_are_written_whole_and_run_through_one_executor(self):
        self.generate()
        plan = json.loads((self.out / f"src/main/resources/plans/{self.ids['plan']}.plan.json").read_text())
        self.assertIn("'SECRET-LITERAL'", plan["residual"]["java"]["sql"])
        executor = self.java("MigrationPlans.java")
        self.assertIn(f'"{self.ids["plan"]}"', executor)
        self.assertIn("fetcher.begin()", executor)

    def test_plans_and_statements_keep_the_target_namespace(self):
        self.generate()
        plan = json.loads((self.out / f"src/main/resources/plans/{self.ids['plan']}.plan.json").read_text())
        self.assertEqual({f["namespace"] for f in plan["fetch"]}, {"shop"})

    def test_a_plan_without_a_namespace_refuses_generation(self):
        self.rewrite(BASE / "schema.json", lambda s: s.update({"orders": s.pop("shop.orders")}))
        with self.assertRaises(generate_migration.GateFailure) as refused:
            self.generate()
        self.assertIn(f"{self.ids['plan']}: the plan fetches orders without a namespace", str(refused.exception))

    def test_a_write_that_needs_ids_and_the_clock_gets_a_write_skeleton_with_both(self):
        self.generate()
        stem = self.ids["insert"].replace("-", "").capitalize()
        write = self.java(f"appside/{stem}Write.java")
        self.assertIn("LongSupplier", write)
        self.assertIn("Clock", write)
        self.assertFalse((self.out / f"src/main/java/com/example/shop/migration/appside/{stem}IdGenerator.java").exists())
        self.assertTrue((self.out / "src/main/java/com/example/shop/migration/appside"
                         / f"{self.ids['seq'].replace('-', '').capitalize()}IdGenerator.java").is_file())

    def test_core_api_statements_become_an_interface_to_implement(self):
        self.generate()
        interface = self.java("CoreApiStatements.java")
        self.assertIn("interface CoreApiStatements", interface)
        self.assertIn(self.ids["scan"].replace("-", "").lower() + "(", interface)

    def test_application_side_work_is_a_skeleton_with_its_semantics_and_a_golden_frame(self):
        self.generate()
        tree = self.ids["tree"].replace("-", "").capitalize()
        query = self.java(f"appside/{tree}Query.java")
        self.assertIn("implements AppSideQuery", query)
        self.assertIn("UnsupportedOperationException", query)
        self.assertIn("Hierarchy.connectBy", query)
        golden = (self.out / f"src/test/java/com/example/shop/migration/appside/{tree}QueryGoldenTest.java").read_text()
        self.assertIn("@Disabled", golden)
        rmw = self.java(f"appside/{self.ids['rmw'].replace('-', '').capitalize()}Write.java")
        self.assertIn("DistributedTransactionManager", rmw)
        self.assertIn("commit", rmw)
        self.assertTrue((self.out / "src/main/java/com/example/shop/migration/appside"
                         / f"{self.ids['seq'].replace('-', '').capitalize()}IdGenerator.java").is_file())

    def test_the_module_builds_on_its_own(self):
        self.generate()
        self.assertTrue((self.out / "src/main/java/com/scalar/migrate/runtime/Residual.java").is_file())
        gradle = (self.out / "build.gradle").read_text()
        for version in ("3.19.1", "2.5.250", "2.14.0", "5.14.4"):
            self.assertIn(version, gradle)
        self.assertEqual(json.loads((self.out / "src/main/resources/schema.json").read_text()), json.loads(
            (self.root / BASE / "schema.json").read_text()))

    def test_the_summary_lists_every_statement_and_what_is_left_to_do(self):
        summary = self.generate()
        by_id = {s["id"]: s for s in summary["statements"]}
        self.assertEqual(set(by_id), {s["id"] for s in self.manifest["statements"]})
        self.assertEqual(by_id[self.ids["redesign"]]["generated"], [])
        self.assertIn(self.ids["tree"], summary["requires_implementation"])
        self.assertIn(self.ids["scan"], summary["requires_implementation"])
        self.assertNotIn("SECRET-LITERAL", json.dumps(summary))
        self.assertEqual(json.loads((self.out / "migration-summary.json").read_text()), summary)

    def test_a_verdict_the_converter_no_longer_gives_refuses_generation(self):
        self.rewrite(BASE / "sql-migration-manifest.json", lambda m: next(
            e for e in m["statements"] if e["id"] == self.ids["get"])["converter"].update(status="WARN"))
        with self.assertRaises(generate_migration.GateFailure) as refused:
            self.generate()
        self.assertIn(f"{self.ids['get']}: the converter now says OK, the manifest recorded WARN", str(refused.exception))
        self.assertFalse(self.out.exists())

    def test_a_changed_source_refuses_generation(self):
        (self.root / "db/schema.sql").write_text(SQL.replace("SECRET-LITERAL", "CHANGED"))
        with self.assertRaises(generate_migration.GateFailure) as refused:
            self.generate()
        self.assertIn(f"{self.ids['plan']}: source changed", str(refused.exception))

    def test_an_invalid_manifest_refuses_generation(self):
        self.rewrite(BASE / "sql-migration-manifest.json", lambda m: m["statements"].pop())
        with self.assertRaises(generate_migration.GateFailure) as refused:
            self.generate()
        self.assertIn("manifest is not valid", str(refused.exception))

    def test_an_unresolved_dependency_version_refuses_generation(self):
        self.rewrite(Path("work/version-decisions.json"), lambda v: v["entries"].pop(1))
        with self.assertRaises(generate_migration.GateFailure) as refused:
            self.generate()
        self.assertIn("com.h2database:h2", str(refused.exception))

    def test_a_directory_the_generator_does_not_own_is_never_overwritten(self):
        self.out.mkdir(parents=True)
        (self.out / "handwritten.txt").write_text("keep me")
        with self.assertRaises(generate_migration.GateFailure):
            self.generate()
        self.assertEqual((self.out / "handwritten.txt").read_text(), "keep me")
        self.out.joinpath("handwritten.txt").unlink()
        self.generate()
        (self.out / "src/main/resources/sql/stale.sql").write_text("-- left over")
        self.generate()  # its own earlier output is replaced, not merged
        self.assertFalse((self.out / "src/main/resources/sql/stale.sql").exists())

    def test_cli_exit_codes(self):
        args = [sys.executable, str(SCRIPT), "--project-dir", str(self.root), "--out", str(self.out),
                "--package", "com.example.shop.migration"]
        ok = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.rewrite(BASE / "sql-migration-manifest.json", lambda m: m["statements"].pop())
        refused = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(refused.returncode, 1)
        self.assertIn("manifest is not valid", refused.stderr)


if __name__ == "__main__":
    unittest.main()
