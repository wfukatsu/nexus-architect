#!/usr/bin/env python3
"""Verification: result comparison that tolerates only representation, a differential test that proves plan and
ScalarDB SQL routes against the source database, golden capture and check for application-side reads, the
refusal to touch a production database, and results written back to the manifest without overstating them."""
import copy
import datetime
import decimal
import json
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support  # noqa: E402

support.require_sqlglot()
import convert_inventory  # noqa: E402
import inventory  # noqa: E402
from verify import common, difftest, golden  # noqa: E402

sys.path.insert(0, str(support.ROOT.parents[2] / "tools" / "lib"))
from sql_migration_manifest import validate_sql_migration_manifest  # noqa: E402

SQL = textwrap.dedent("""\
    CREATE TABLE orders (customer_id NUMBER(18), order_no NUMBER(18), status VARCHAR2(10), total NUMBER(18),
      PRIMARY KEY (customer_id, order_no));
    SELECT total FROM orders WHERE customer_id = 1 AND order_no = 2;
    SELECT NVL(status, 'NONE') AS s FROM orders WHERE customer_id = 1 ORDER BY order_no;
    SELECT order_no, LEVEL FROM orders START WITH order_no = 1 CONNECT BY PRIOR order_no = customer_id;
    UPDATE orders SET total = total - 1 WHERE customer_id = 1 AND order_no = 2;
    SELECT NVL(total, 0) AS t FROM orders WHERE customer_id = :customer ORDER BY order_no;
    """)


class FakeSource:
    def __init__(self, answers):
        self.answers, self.queries = answers, []

    def rows(self, sql):
        self.queries.append(sql)
        for fragment, answer in self.answers.items():
            if fragment in sql:
                return answer
        raise AssertionError("unexpected query " + sql)


class FakeRunner:
    def __init__(self, plan_rows=None, sql_rows=None):
        self.plan_rows, self.sql_rows, self.calls = plan_rows, sql_rows, []

    def plan(self, path, fetcher):
        self.calls.append(("plan", Path(path).name, fetcher))
        return self.plan_rows

    def sql(self, text):
        self.calls.append(("sql", text))
        return self.sql_rows


class Project(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "db").mkdir()
        (self.root / "db/schema.sql").write_text(SQL)
        self.inventory = inventory.build(source="oracle", sql_files=[self.root / "db/schema.sql"], project_dir=self.root)
        out = convert_inventory.convert(self.inventory, project_dir=self.root, edition="enterprise_premium", storage="jdbc",
                                        namespace="shop")
        self.schema = out["schema"]
        self.manifest = copy.deepcopy(out["draft"])
        self.manifest.pop("status")
        self.manifest.pop("open")
        for entry in self.manifest["statements"]:
            entry["rationale"] = "decided"
            for note in entry.get("app_side", {}).get("semantics", []):
                note["handling"] = "Hierarchy.connectBy"
        self.id = {name: next(s["id"] for s in self.inventory["statements"] if s["sql"].startswith(prefix)) for name, prefix in
                   {"get": "SELECT total", "plan": "SELECT NVL", "tree": "SELECT order_no, LEVEL", "rmw": "UPDATE",
                    "table": "CREATE TABLE", "bound": "SELECT NVL(total"}.items()}
        self.generated = self.root / "generated/sql-migration/shop"
        (self.generated / "src/main/resources/plans").mkdir(parents=True)
        (self.generated / f"src/main/resources/plans/{self.id['plan']}.plan.json").write_text("{}")
        (self.generated / "src/main/resources/sql").mkdir(parents=True)
        (self.generated / f"src/main/resources/sql/{self.id['get']}.sql").write_text(
            "SELECT total FROM orders WHERE customer_id = 1 AND order_no = 2;\n")

    def tearDown(self):
        self.tmp.cleanup()

    def entry(self, manifest, name):
        return next(e for e in manifest["statements"] if e["id"] == self.id[name])


class ComparisonTests(unittest.TestCase):
    def test_representation_differences_are_equal(self):
        self.assertEqual(common.normalize(decimal.Decimal("2.50")), common.normalize(2.5))
        self.assertEqual(common.normalize(decimal.Decimal("3")), 3)
        self.assertEqual(common.normalize(datetime.datetime(2024, 6, 1)), "2024-06-01")
        self.assertEqual(common.normalize("2024-06-01T00:00:00"), "2024-06-01")
        self.assertEqual(common.normalize(True), 1)

    def test_order_matters_only_when_the_query_orders(self):
        self.assertTrue(common.same_rows([(1,), (2,)], [[2], [1]], ordered=False)[0])
        ok, detail = common.same_rows([(1,), (2,)], [[2], [1]], ordered=True)
        self.assertFalse(ok)
        self.assertEqual(detail, "row 0 differs (2 rows expected, 2 returned)")
        ok, detail = common.same_rows([("secret-value",)], [], ordered=False)
        self.assertEqual((ok, detail), (False, "1 rows expected, 0 returned"))

    def test_top_level_order_and_referenced_tables(self):
        self.assertTrue(common.is_ordered("SELECT a FROM t ORDER BY a", "oracle"))
        self.assertFalse(common.is_ordered("SELECT a FROM (SELECT a FROM t ORDER BY a) x", "oracle"))
        self.assertEqual(common.tables_of("WITH m AS (SELECT * FROM sales s JOIN shops p ON p.id = s.shop) SELECT * FROM m",
                                          "oracle"), ["sales", "shops"])


class ProfileTests(unittest.TestCase):
    ENV = {"V_HOST": "127.0.0.1", "V_PORT": "5432", "V_USER": "reader", "V_DB": "shop"}

    def profile(self, **kw):
        base = {"product": "postgresql", "environment": "test", "host_env": "V_HOST", "port_env": "V_PORT",
                "user_env": "V_USER", "database_env": "V_DB", "allow_local_plaintext": True}
        base.update(kw)
        return base

    def test_production_and_unstated_environments_are_refused(self):
        with mock.patch.dict(os.environ, self.ENV):
            self.assertEqual(common.source_config(self.profile())["environment"], "test")
            with self.assertRaisesRegex(ValueError, "never connects to a production database"):
                common.source_config(self.profile(environment="production"))
            with self.assertRaisesRegex(ValueError, "environment"):
                common.source_config({k: v for k, v in self.profile().items() if k != "environment"})

    def test_literal_secrets_are_refused_like_investigation_profiles(self):
        with mock.patch.dict(os.environ, self.ENV), self.assertRaises(ValueError):
            common.source_config(self.profile(password="literal"))


class DifftestTests(Project):
    def test_a_plan_matching_the_source_is_verified(self):
        source = FakeSource({"NVL": (["s"], [["A"], ["B"]])})
        runner = FakeRunner(plan_rows=[["A"], ["B"]])
        results = difftest.run(self.manifest, self.inventory, self.root, source, runner, "core", self.generated)
        by_id = {r["id"]: r for r in results}
        self.assertEqual(by_id[self.id["plan"]], {"id": self.id["plan"], "method": "difftest", "outcome": "pass"})
        self.assertIn(("plan", f"{self.id['plan']}.plan.json", "core"), runner.calls)
        self.assertIn("'NONE'", source.queries[0])  # the source runs the full original text

    def test_a_plan_that_disagrees_fails_without_copying_data(self):
        results = difftest.run(self.manifest, self.inventory, self.root, FakeSource({"NVL": (["s"], [["A"], ["B"]])}),
                               FakeRunner(plan_rows=[["B"], ["A"]]), "core", self.generated)
        failed = next(r for r in results if r["id"] == self.id["plan"])
        self.assertEqual((failed["outcome"], failed["reason"]), ("fail", "row 0 differs (2 rows expected, 2 returned)"))

    def test_scalardb_sql_needs_the_licensed_path_and_writes_are_out_of_scope(self):
        results = {r["id"]: r for r in difftest.run(self.manifest, self.inventory, self.root, FakeSource({"NVL": (["s"], [["A"]])}),
                                                     FakeRunner(plan_rows=[["A"]]), "core", self.generated)}
        self.assertEqual((results[self.id["get"]]["outcome"], results[self.id["get"]]["reason"]),
                         ("skipped", "ScalarDB SQL needs ScalarDB Cluster and a license (--fetcher jdbc)"))
        self.assertEqual(results[self.id["rmw"]]["outcome"], "skipped")
        self.assertNotIn(self.id["table"], results)  # schema statements are not result-set comparisons
        jdbc = {r["id"]: r for r in difftest.run(self.manifest, self.inventory, self.root,
                                                 FakeSource({"SELECT total": (["total"], [[7]]), "NVL": (["s"], [["A"]])}),
                                                 FakeRunner(plan_rows=[["A"]], sql_rows=[[7]]), "jdbc", self.generated)}
        self.assertEqual(jdbc[self.id["get"]]["outcome"], "pass")

    def test_a_statement_with_bind_parameters_is_skipped_with_its_reason(self):
        results = difftest.run(self.manifest, self.inventory, self.root, FakeSource({"NVL(status": (["s"], [["A"]])}),
                               FakeRunner(plan_rows=[["A"]]), "core", self.generated)
        bound = next(r for r in results if r["id"] == self.id["bound"])
        self.assertEqual((bound["outcome"], bound["reason"]),
                         ("skipped", "the statement takes bind parameters; prove it with golden or unit tests"))

    def test_a_changed_source_is_skipped_not_compared(self):
        (self.root / "db/schema.sql").write_text(SQL.replace("'NONE'", "'OTHER'"))
        results = difftest.run(self.manifest, self.inventory, self.root, FakeSource({}), FakeRunner(), "core", self.generated)
        self.assertEqual(next(r for r in results if r["id"] == self.id["plan"])["reason"], "source changed since the inventory")


class GoldenTests(Project):
    def test_capture_dumps_the_referenced_tables_and_the_expected_result(self):
        source = FakeSource({"SELECT * FROM orders": (["customer_id", "total"], [[1, decimal.Decimal("9.50")]]),
                             "LEVEL": (["order_no", "level"], [[1, 1]])})
        path = golden.capture(self.entry(self.manifest, "tree"), self.inventory, self.root, source, self.generated, "oracle")
        data = json.loads(path.read_text())
        self.assertEqual(path, self.generated / f"src/test/resources/golden/{self.id['tree']}/golden.json")
        self.assertEqual(data["tables"]["orders"], [{"customer_id": 1, "total": {"$dec": "9.50"}}])
        self.assertEqual(data["expected"], {"columns": ["order_no", "level"], "rows": [[1, 1]]})
        self.assertFalse(data["ordered"])

    def test_capture_refuses_a_table_over_the_row_bound(self):
        source = FakeSource({"SELECT * FROM orders": (["customer_id"], [[n] for n in range(6)])})
        with self.assertRaisesRegex(ValueError, "orders has more than 5 rows"):
            golden.capture(self.entry(self.manifest, "tree"), self.inventory, self.root, source, self.generated, "oracle",
                           max_rows=5)

    def test_check_runs_golden_check_on_the_generated_class(self):
        calls = []
        outcome = golden.check(self.id["tree"], self.generated, "com.example.shop.migration",
                               java=lambda cmd: calls.append(cmd) or 1)
        self.assertEqual((outcome["outcome"], outcome["method"]), ("fail", "golden"))
        self.assertIn("com.example.shop.migration.appside.Sqm004Query".replace("Sqm004", self.id["tree"].replace("-", "").capitalize()),
                      calls[0])
        self.assertIn("com.scalar.migrate.appside.golden.GoldenCheck", calls[0])
        self.assertEqual(golden.check(self.id["tree"], self.generated, "com.example.shop.migration", java=lambda cmd: 0)["outcome"], "pass")
        self.assertEqual(golden.check(self.id["tree"], self.generated, "com.example.shop.migration", java=lambda cmd: 2)["outcome"], "error")


class RecordTests(Project):
    def test_results_become_verification_states_the_validator_accepts(self):
        results = [{"id": self.id["plan"], "method": "difftest", "outcome": "pass"},
                   {"id": self.id["tree"], "method": "golden", "outcome": "fail"},
                   {"id": self.id["get"], "method": "difftest", "outcome": "skipped", "reason": "no license"}]
        recorded = common.record(self.manifest, results, "reports/09_verification/sql-migration/run-1.json")
        self.assertEqual(self.entry(recorded, "plan")["verification"],
                         {"status": "verified", "method": "difftest", "evidence": "reports/09_verification/sql-migration/run-1.json"})
        self.assertEqual(self.entry(recorded, "tree")["verification"]["status"], "failed")
        self.assertEqual(self.entry(recorded, "get")["verification"], {"status": "skipped", "reason": "no license"})
        self.assertEqual(self.entry(self.manifest, "plan")["verification"], {"status": "pending"})  # input untouched
        self.assertEqual(validate_sql_migration_manifest(recorded, inventory=self.inventory, schema=self.schema), [])

    def test_a_skip_never_erases_an_earlier_proof_and_an_error_is_not_a_verdict(self):
        proven = common.record(self.manifest, [{"id": self.id["plan"], "method": "golden", "outcome": "pass"}], "e1.json")
        again = common.record(proven, [{"id": self.id["plan"], "method": "difftest", "outcome": "skipped", "reason": "x"},
                                       {"id": self.id["tree"], "method": "golden", "outcome": "error", "reason": "no JVM"}], "e2.json")
        self.assertEqual(self.entry(again, "plan")["verification"]["status"], "verified")
        self.assertEqual(self.entry(again, "tree")["verification"], {"status": "pending"})


if __name__ == "__main__":
    unittest.main()
