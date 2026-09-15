#!/usr/bin/env python3
"""Application-side analysis (ported from sql-migration tests/test_appside.py): every construct that moves to
the application, plans H2 cannot run, date-literal pushdown, key feeds on Cassandra, semantics to keep, cost
estimates, and how the CLI reports them."""
import io
import logging
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support  # noqa: E402

support.require_sqlglot()
from scalardb_migrate import cli  # noqa: E402
from scalardb_migrate.appside import estimate_cost, parse_expected_rows  # noqa: E402
from scalardb_migrate.converter import convert_script  # noqa: E402

logging.getLogger("sqlglot").setLevel(logging.ERROR)

AREA_SQL = """
WITH area_hierarchy AS (
    SELECT node_id AS shop_or_area_id, parent_id, node_name,
           SYS_CONNECT_BY_PATH(node_name, ' > ') AS area_path, LEVEL AS hierarchy_level
    FROM organization_master
    START WITH parent_id IS NULL
    CONNECT BY PRIOR node_id = parent_id
),
monthly_sales AS (
    SELECT shop_id, TO_CHAR(sales_date, 'YYYY-MM') AS sales_month, SUM(amount) AS total_amount
    FROM sales_transactions
    WHERE sales_date >= DATE '2026-01-01' AND sales_date < DATE '2027-01-01'
    GROUP BY shop_id, TO_CHAR(sales_date, 'YYYY-MM')
)
SELECT h.area_path, s.sales_month, s.total_amount,
       ROUND((s.total_amount / LAG(s.total_amount, 1) OVER (PARTITION BY s.shop_id ORDER BY s.sales_month)) * 100, 2) AS mom,
       DENSE_RANK() OVER (PARTITION BY h.parent_id, s.sales_month ORDER BY s.total_amount DESC) AS rank_in_area
FROM area_hierarchy h
INNER JOIN monthly_sales s ON h.shop_or_area_id = s.shop_id
WHERE h.hierarchy_level = 3
ORDER BY h.area_path, s.sales_month;
"""
AREA_DDL = """
CREATE TABLE organization_master (node_id NUMBER(18) PRIMARY KEY, parent_id NUMBER(18), node_name VARCHAR2(200));
CREATE TABLE sales_transactions (shop_id NUMBER(18), sales_date TIMESTAMP, order_id NUMBER(18), amount NUMBER(18),
  PRIMARY KEY (shop_id, sales_date, order_id));
"""
PLANNABLE = ("WITH m AS (SELECT shop_id, SUM(amount) AS t FROM sales_transactions "
             "WHERE sales_date >= DATE '2026-01-01' AND sales_date < DATE '2027-01-01' GROUP BY shop_id) "
             "SELECT shop_id, t, RANK() OVER (ORDER BY t DESC) AS r FROM m;")
ORDERS_DDL = """
CREATE TABLE customers (customer_id BIGINT PRIMARY KEY, region VARCHAR(10), name VARCHAR(20));
CREATE INDEX ix_region ON customers (region);
CREATE TABLE orders (customer_id BIGINT, order_no BIGINT, amount BIGINT, PRIMARY KEY (customer_id, order_no));
"""


def last(sql, **kw):
    results, _ = convert_script(sql, "oracle", **kw)
    return results[-1]


def codes(r, severity=None):
    return [i.code for i in r.issues if severity is None or i.severity == severity]


def messages(r, code):
    return [i.message for i in r.issues if i.code == code]


def run_cli(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.main(argv)
    return code, out.getvalue(), err.getvalue()


class AppSideTests(unittest.TestCase):
    def test_inventory_lists_every_construct_not_only_the_first(self):
        r = last(AREA_SQL, decompose=False)
        assert r.status == "ERROR"
        assert {"CTE", "HIERARCHICAL", "WINDOW", "PROJECTION", "GROUP"} <= set(codes(r, "ERROR"))
        text = " ".join(i.message for i in r.issues)
        assert "area_hierarchy" in text and "CTE monthly_sales" in text and "LAG" in text and "DENSE_RANK" in text
        assert "TO_CHAR(sales_date, 'YYYY-MM')" in text  # rendered in the source dialect, not as CAST(... AS TEXT)

    def test_plan_is_rejected_when_h2_cannot_run_connect_by(self):
        r = last(AREA_SQL)
        assert r.status == "ERROR" and r.plan is None
        assert any("CONNECT BY" in m for m in messages(r, "RESIDUAL_H2"))

    def test_other_constructs_h2_lacks_are_not_planned(self):
        for sql, construct in [
            ("SELECT deptno, SUM(sal) AS s FROM emp GROUP BY ROLLUP (deptno)", "ROLLUP"),
            ("SELECT * FROM (SELECT deptno, job, sal FROM emp) PIVOT (SUM(sal) FOR job IN ('A' AS a))", "PIVOT"),
            ("SELECT deptno, MAX(sal) KEEP (DENSE_RANK FIRST ORDER BY hiredate) AS s FROM emp GROUP BY deptno", "KEEP"),
        ]:
            with self.subTest(construct=construct):
                r = last(sql)
                assert r.status == "ERROR" and any(construct in m for m in messages(r, "RESIDUAL_H2")), r.issues

    def test_date_literals_in_a_cte_are_pushed_into_the_fetch(self):
        r = last(AREA_DDL + PLANNABLE)
        assert r.status == "PLANNED", r.issues
        assert r.plan["fetch"][0]["scalardb_sql"].endswith(
            "WHERE sales_date >= '2026-01-01 00:00:00' AND sales_date < '2027-01-01 00:00:00'")
        assert r.plan["transaction"] == {"read_only": True}
        assert r.plan["recommended_config"]["scalar.db.scan_fetch_size"] == 1000
        assert "APP_SEMANTICS" not in codes(r)  # H2 runs the original SQL and keeps the semantics itself

    def test_plan_lists_indexes_for_the_residual_joins(self):
        q = ("SELECT c.name, COUNT(*) AS n FROM customers c JOIN orders o ON o.customer_id = c.customer_id "
             "WHERE c.region = 'X' AND NOT EXISTS (SELECT 1 FROM orders x WHERE x.order_no = o.order_no) GROUP BY c.name")
        r = last(ORDERS_DDL + q)
        assert r.status == "PLANNED", r.issues
        ix = {f["table"]: f["index_columns"] for f in r.plan["fetch"]}
        assert ix["customers"] == [["customer_id"]]                     # primary key, also the join column
        assert ix["orders"] == [["customer_id", "order_no"], ["order_no"]]  # key (leads with the join column) + correlation
        assert r.plan["residual"]["java"]["build_indexes"] is False     # listed, but only built when asked for
        assert last(ORDERS_DDL + q, h2_indexes=True).plan["residual"]["java"]["build_indexes"] is True

    def test_cassandra_full_scan_suggests_fetching_by_joined_keys(self):
        q = ("SELECT c.name, SUM(o.amount) * 2 AS s FROM customers c JOIN orders o ON o.customer_id = c.customer_id "
             "WHERE c.region = 'X' GROUP BY c.name")
        full = messages(last(ORDERS_DDL + q, storage="cassandra"), "FULL_SCAN")
        assert len(full) == 1
        assert "read customers first, then orders with one partition scan per customers.customer_id value" in full[0]

    def test_cassandra_key_feed_is_not_circular_and_every_table_is_reported(self):
        full = messages(last(AREA_DDL + AREA_SQL, storage="cassandra"), "FULL_SCAN")
        assert len(full) == 2
        assert all("cannot be fetched by key either" in m and "fetch by key instead" not in m for m in full)

    def test_semantics_to_keep_are_listed_for_app_side_statements(self):
        notes = " ".join(messages(last(AREA_SQL, decompose=False), "APP_SEMANTICS"))
        for expected in ("LAG / LEAD", "ORA-01476", "half away from zero", "NULLs sort last for ASC", "NLS_SORT",
                         "ORA-30004", "ignore NULLs"):
            assert expected in notes, expected

    def test_design_advice_names_summary_and_hierarchy_tables(self):
        advice = " ".join(messages(last(AREA_SQL, decompose=False), "DESIGN"))
        assert "summary table keyed by (shop_id, sales_month)" in advice
        assert "precompute the hierarchy" in advice
        assert "table definitions unknown" in advice

    def test_cost_estimates_and_guardrails(self):
        assert parse_expected_rows(["orders=5_000_000:50"]) == {"orders": (5_000_000, 50)}
        out = estimate_cost([("sales", "CROSS_PARTITION")], parse_expected_rows(["sales=3000000"]), "SERIALIZABLE", 10_000)
        assert {"ROW_LIMIT", "COST_DEADLINE"} <= {c for _, c, _ in out}  # 3M x 25 us x 2 = 150 s > 60 s
        snapshot = estimate_cost([("sales", "CROSS_PARTITION")], parse_expected_rows(["sales=1000000"]), "SNAPSHOT", None)
        assert any("~25.0 s" in m for _, _, m in snapshot)
        per_key = estimate_cost([("orders", "PARTITION_SCAN")], parse_expected_rows(["orders=5000000:40"]), "SNAPSHOT", None)
        assert any("~40 rows -> ~6 ms" in m for _, _, m in per_key)

    def test_converted_cross_partition_select_gets_cost_and_settings(self):
        r = last(ORDERS_DDL + "SELECT * FROM orders WHERE amount > 10", expected_rows=parse_expected_rows(["orders=100000"]))
        assert r.status == "WARN" and {"COST", "CONFIG"} <= set(codes(r))

    def test_cli_accepts_source_and_reports_application_side_work(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "area.sql"
            src.write_text(AREA_SQL, encoding="utf-8")
            code, _, err = run_cli([str(src), "--source", "oracle", "--out-dir", str(Path(d) / "out")])
            assert code == 1
            md = (Path(d) / "out" / "area.report.md").read_text(encoding="utf-8")
            assert "## Application-side work" in md and "**Semantics the application must keep**" in md
            assert "not supported for expression" not in err

    def test_cli_plan_dir_writes_plans_and_marks_them_in_the_converted_sql(self):
        # replaces upstream's test of the sql-transpile skill entry point, which is not vendored
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            src = tmp / "q.sql"
            src.write_text(AREA_DDL + PLANNABLE + AREA_SQL, encoding="utf-8")
            code, out, _ = run_cli([str(src), "--source", "oracle", "--out-dir", str(tmp / "out"),
                                    "--plan-dir", str(tmp / "plans"), "--expected-rows", "sales_transactions=1000000"])
            assert code == 1
            assert "PLANNED=1" in out and (tmp / "plans" / "q.3.plan.json").is_file()
            md = (tmp / "out" / "q.report.md").read_text(encoding="utf-8")
            assert "## Application-side work" in md and "ROW_LIMIT" in md
            assert "[APP-SIDE PLAN #3]" in (tmp / "out" / "q.scalardb.sql").read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
