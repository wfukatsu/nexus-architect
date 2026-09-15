#!/usr/bin/env python3
"""Converting an inventory: the analysis results become converter inputs, every statement gets the converter's
verdict without a stored literal, and a draft manifest proposes the route the rule assigns."""
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
import inventory  # noqa: E402

sys.path.insert(0, str(support.ROOT.parents[2] / "tools" / "lib"))
from sql_migration_manifest import validate_sql_migration_manifest  # noqa: E402

SCRIPT = support.ROOT / "scripts/convert_inventory.py"

SQL = textwrap.dedent("""\
    CREATE TABLE orders (customer_id NUMBER(18), order_no NUMBER(18), status VARCHAR2(10), total NUMBER(18),
      PRIMARY KEY (customer_id, order_no));
    CREATE INDEX ix_status ON orders (status);
    CREATE SEQUENCE order_seq START WITH 1;
    SELECT status FROM orders WHERE customer_id = 1 AND order_no = 2;
    SELECT order_no FROM orders WHERE total > 100;
    SELECT NVL(status, 'SECRET-LITERAL') AS s FROM orders WHERE customer_id = 1;
    UPDATE orders SET total = total - 1 WHERE customer_id = 1 AND order_no = 2;
    """)

MAPPER = textwrap.dedent("""\
    <mapper namespace="com.shop.OrderMapper">
      <select id="search">SELECT order_no FROM orders <where><if test="s != null">status = #{s}</if></where></select>
    </mapper>
    """)

REPO = textwrap.dedent('''\
    interface OrderRepository {
      @Query("SELECT o FROM Order o WHERE o.total > :min")
      List<Order> big(BigDecimal min);
    }
    ''')


class ConvertInventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "db").mkdir()
        (self.root / "db/schema.sql").write_text(SQL)
        self.inventory = inventory.build(source="oracle", sql_files=[self.root / "db/schema.sql"], project_dir=self.root)
        self.ids = {s["sql"].split(" (")[0].split(" WHERE")[0]: s["id"] for s in self.inventory["statements"]}

    def tearDown(self):
        self.tmp.cleanup()

    def run_convert(self, **kw):
        options = dict(project_dir=self.root, edition="enterprise_premium", storage="jdbc", namespace="shop")
        options.update(kw)
        return convert_inventory.convert(self.inventory, **options)

    def result(self, out, prefix):
        sid = next(s["id"] for s in self.inventory["statements"] if s["sql"].startswith(prefix))
        return next(r for r in out["conversion"]["results"] if r["id"] == sid), \
            next(e for e in out["draft"]["statements"] if e["id"] == sid)

    def test_statuses_come_from_the_converter_with_the_ddl_as_schema(self):
        out = self.run_convert()
        self.assertEqual(self.result(out, "SELECT status FROM orders")[0]["status"], "OK")
        self.assertEqual(self.result(out, "SELECT order_no FROM orders WHERE total")[0]["status"], "WARN")
        self.assertEqual(self.result(out, "SELECT NVL")[0]["status"], "PLANNED")
        rmw, _ = self.result(out, "UPDATE orders")
        self.assertEqual((rmw["status"], "RMW" in rmw["codes"]), ("ERROR", True))
        orders = out["schema"]["shop.orders"]
        self.assertEqual((orders["partition-key"], orders["clustering-key"], orders["secondary-index"]),
                         (["customer_id"], ["order_no ASC"], ["status"]))

    def test_draft_routes_follow_the_rule(self):
        out = self.run_convert()
        routes = {prefix: self.result(out, prefix)[1] for prefix in
                  ("CREATE TABLE", "CREATE SEQUENCE", "SELECT status", "SELECT NVL", "UPDATE orders")}
        self.assertEqual(routes["CREATE TABLE"]["route"], "schema")
        self.assertEqual((routes["CREATE SEQUENCE"]["route"], routes["CREATE SEQUENCE"]["app_side"]["pattern"]),
                         ("app_side", "id_generation"))
        self.assertEqual(routes["SELECT status"]["route"], "scalardb_sql")
        self.assertEqual((routes["SELECT NVL"]["route"], routes["SELECT NVL"]["plan"]["row_limit"]), ("plan", 10000))
        self.assertEqual((routes["UPDATE orders"]["route"], routes["UPDATE orders"]["app_side"]["pattern"]), ("app_side", "rmw"))
        self.assertTrue(all(e["verification"] == {"status": "pending"} for e in out["draft"]["statements"]))

    def test_the_edition_decides_between_scalardb_sql_and_the_core_api(self):
        out = self.run_convert(edition="enterprise_standard")
        self.assertEqual(self.result(out, "SELECT status")[1]["route"], "core_api")
        self.assertEqual(out["draft"]["target"]["edition"], "enterprise_standard")

    def test_the_draft_is_a_manifest_the_validator_accepts(self):
        out = self.run_convert()
        errors = validate_sql_migration_manifest(out["draft"], inventory=self.inventory, schema=out["schema"])
        self.assertEqual(errors, [])

    def test_key_hints_override_the_primary_key_split(self):
        out = self.run_convert(key_hints={"orders": (["customer_id", "order_no"], [])})
        self.assertEqual(out["schema"]["shop.orders"]["partition-key"], ["customer_id", "order_no"])
        self.assertEqual(out["draft"]["keys"][0]["partition_key"], ["customer_id", "order_no"])
        self.assertEqual(out["draft"]["keys"][0]["source"], "user")

    def test_live_row_estimates_feed_the_cost_estimate(self):
        run = self.root / "live"
        run.mkdir()
        (run / "inventory.json").write_text(json.dumps({"mode": "live", "statistics": [
            {"name": "ORDERS", "metric": "rows", "value": 3000000, "semantics": "estimate", "unit": "rows"}]}))
        out = self.run_convert(live_runs=[run])
        self.assertIn("COST", self.result(out, "SELECT order_no FROM orders WHERE total")[0]["codes"])
        self.assertEqual(out["conversion"]["expected_rows"], {"orders": {"rows": 3000000, "semantics": "estimate"}})

    def test_no_literal_is_stored_in_the_conversion_or_the_draft(self):
        out = self.run_convert()
        self.assertNotIn("SECRET-LITERAL", json.dumps(out["conversion"]) + json.dumps(out["draft"]))
        self.assertIn("'?'", self.result(out, "SELECT NVL")[0]["source_masked"])

    def test_dynamic_sql_and_jpql_are_proposed_but_never_decided_by_the_tool(self):
        app = self.root / "app"
        (app / "mapper").mkdir(parents=True)
        (app / "mapper/OrderMapper.xml").write_text(MAPPER)
        (app / "OrderRepository.java").write_text(REPO)
        self.inventory = inventory.build(source="oracle", sql_files=[self.root / "db/schema.sql"], app_roots=[app],
                                         project_dir=self.root)
        out = self.run_convert()
        search = next(e for e in out["draft"]["statements"] if e["id"] == next(
            s["id"] for s in self.inventory["statements"] if s["origin"].get("locator", "").endswith("#search")))
        self.assertNotIn("confirmation", search)
        jpql_id = next(s["id"] for s in self.inventory["statements"] if s["language"] == "jpql")
        jpql, = [r for r in out["conversion"]["results"] if r["id"] == jpql_id]
        self.assertEqual((jpql["status"], jpql["codes"]), ("ERROR", ["JPQL"]))
        self.assertEqual({o["id"]: o["question"] for o in out["draft"]["open"]}.keys(), {search["id"], jpql_id})

    def test_a_statement_whose_source_changed_is_skipped_not_guessed(self):
        (self.root / "db/schema.sql").write_text(SQL.replace("SECRET-LITERAL", "CHANGED"))
        out = self.run_convert()
        sid = next(s["id"] for s in self.inventory["statements"] if s["sql"].startswith("SELECT NVL"))
        self.assertEqual(out["conversion"]["skipped"], [{"id": sid, "reason": "stale_evidence"}])
        self.assertNotIn(sid, {r["id"] for r in out["conversion"]["results"]})

    def test_cli_writes_the_three_files(self):
        inv_path = self.root / "reports/03_design/sql-migration/sql-inventory.json"
        inv_path.parent.mkdir(parents=True)
        inv_path.write_text(json.dumps(self.inventory))
        r = subprocess.run([sys.executable, str(SCRIPT), "--inventory", str(inv_path), "--edition", "enterprise_premium",
                            "--storage", "jdbc", "--namespace", "shop", "--out-dir", str(inv_path.parent)],
                           capture_output=True, text=True, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        for name in ("schema.json", "conversion.json", "sql-migration-manifest.draft.json"):
            self.assertTrue((inv_path.parent / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
