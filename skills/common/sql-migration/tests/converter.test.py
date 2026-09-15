#!/usr/bin/env python3
"""Rule-level tests for the ScalarDB converter (ported from sql-migration tests/test_converter.py)."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support  # noqa: E402

support.require_sqlglot()
from scalardb_migrate.converter import convert_script  # noqa: E402

SCHEMA_DDL = {
    "mysql": "CREATE TABLE orders (customer_id INT, order_no BIGINT, status VARCHAR(20), amount DOUBLE, "
             "PRIMARY KEY (customer_id, order_no)); CREATE INDEX ix ON orders (status);",
}


def run(sql, dialect="mysql", with_schema=True):
    text = (SCHEMA_DDL.get(dialect, "") if with_schema else "") + sql
    results, reg = convert_script(text, dialect, decompose=False)
    return results[-1]


def run_on(sql, storage):
    results, _ = convert_script(SCHEMA_DDL["mysql"] + sql, "mysql", decompose=False, storage=storage)
    return results[-1]


def codes(r):
    return {i.code for i in r.issues}


class DdlTests(unittest.TestCase):
    def test_create_table_composite_pk_and_types(self):
        r = run("CREATE TABLE t (a INT, b BIGINT, c VARCHAR(10) NOT NULL, d DECIMAL(10,2), e DATETIME, PRIMARY KEY (a, b))",
                with_schema=False)
        assert r.status == "WARN"
        out = r.converted[0]
        assert "a INT" in out and "c TEXT" in out and "d DOUBLE" in out and "e TIMESTAMP" in out
        assert "PRIMARY KEY (a, b)" in out
        assert "NOT NULL" not in out and "TYPE" in codes(r)

    def test_create_table_multi_partition_key_hint(self):
        results, reg = convert_script("CREATE TABLE t (a INT, b INT, c INT, PRIMARY KEY (a, b, c))", "postgres",
                                      key_hints={"t": (["a", "b"], ["c"])})
        assert "PRIMARY KEY ((a, b), c)" in results[0].converted[0]
        meta = reg.get("t")
        assert meta.partition_key == ["a", "b"] and meta.clustering_key == ["c"]

    def test_auto_increment_is_error(self):
        r = run("CREATE TABLE t (id INT AUTO_INCREMENT PRIMARY KEY, v TEXT)", with_schema=False)
        assert r.status == "ERROR" and "AUTO_INC" in codes(r)

    def test_serial_is_error(self):
        assert run("CREATE TABLE t (id SERIAL PRIMARY KEY, v TEXT)", "postgres", with_schema=False).status == "ERROR"

    def test_no_primary_key_is_error(self):
        assert "PK" in codes(run("CREATE TABLE t (id INT, v TEXT)", with_schema=False))

    def test_inline_index_becomes_create_index(self):
        r = run("CREATE TABLE t (id INT PRIMARY KEY, name VARCHAR(10), INDEX ix (name))", with_schema=False)
        assert r.converted[1] == "CREATE INDEX ON t (name)"

    def test_composite_index_is_error(self):
        r = run("CREATE INDEX ix ON t (a, b)", "postgres", with_schema=False)
        assert r.status == "ERROR" and "INDEX" in codes(r)

    def test_alter_add_column(self):
        assert run("ALTER TABLE t ADD COLUMN x VARCHAR(10)", with_schema=False).converted == ["ALTER TABLE t ADD COLUMN x TEXT"]

    def test_sequence_and_view_unsupported(self):
        assert run("CREATE SEQUENCE s", "oracle", with_schema=False).status == "ERROR"
        assert run("CREATE VIEW v AS SELECT 1 FROM dual", "oracle", with_schema=False).status == "ERROR"

    def test_schema_loader_json_is_emitted(self):
        results, reg = convert_script(SCHEMA_DDL["mysql"], "mysql")
        j = json.loads(reg.to_schema_loader_json())
        assert j["orders"]["partition-key"] == ["customer_id"]
        assert j["orders"]["clustering-key"] == ["order_no ASC"]
        assert j["orders"]["secondary-index"] == ["status"]
        assert j["orders"]["columns"]["status"] == "TEXT"


class SelectTests(unittest.TestCase):
    def test_get_by_full_pk(self):
        r = run("SELECT status FROM orders WHERE customer_id = 1 AND order_no = 2")
        assert r.status == "OK"
        assert any("GET" in i.message for i in r.issues)

    def test_partition_scan_with_clustering_order(self):
        r = run("SELECT order_no FROM orders WHERE customer_id = 1 AND order_no > 10 ORDER BY order_no DESC LIMIT 5")
        assert r.status == "OK" and any("partition SCAN" in i.message for i in r.issues)

    def test_cross_partition_warning(self):
        r = run("SELECT order_no FROM orders WHERE amount > 10")
        assert r.status == "WARN" and "CROSS_PARTITION" in codes(r)

    def test_in_list_expanded_to_or(self):
        r = run("SELECT * FROM orders WHERE customer_id = 1 AND status IN ('A', 'B')")
        assert r.converted[0] == "SELECT * FROM orders WHERE customer_id = 1 AND (status = 'A' OR status = 'B')"

    def test_not_in_expanded_to_and(self):
        assert "status <> 'A' AND status <> 'B'" in run("SELECT * FROM orders WHERE customer_id = 1 AND status NOT IN ('A', 'B')").converted[0]

    def test_not_pushdown_and_dnf(self):
        r = run("SELECT * FROM orders WHERE NOT (customer_id = 1) OR (status = 'A' AND amount > 1)")
        assert r.converted[0].endswith("WHERE customer_id <> 1 OR (status = 'A' AND amount > 1)")

    def test_is_not_null_and_not_like(self):
        r = run("SELECT * FROM orders WHERE status IS NOT NULL AND status NOT LIKE 'X%' AND customer_id = 1")
        assert "status IS NOT NULL" in r.converted[0] and "status NOT LIKE 'X%'" in r.converted[0]

    def test_literal_on_left_is_flipped(self):
        assert "amount > 10" in run("SELECT * FROM orders WHERE 10 < amount AND customer_id = 1").converted[0]

    def test_column_to_column_predicate_is_error(self):
        assert "COL_COL" in codes(run("SELECT * FROM orders WHERE customer_id = order_no"))

    def test_expression_projection_is_error(self):
        assert "PROJECTION" in codes(run("SELECT amount * 2 FROM orders WHERE customer_id = 1"))

    def test_aggregates_ok_and_distinct_count_error(self):
        ok = run("SELECT status, COUNT(*), SUM(amount) FROM orders GROUP BY status HAVING COUNT(*) > 1")
        assert ok.converted[0] == "SELECT status, COUNT(*), SUM(amount) FROM orders GROUP BY status HAVING COUNT(*) > 1"
        assert "AGG_DISTINCT" in codes(run("SELECT COUNT(DISTINCT status) FROM orders"))

    def test_unsupported_select_features(self):
        for sql, code in [
            ("SELECT DISTINCT status FROM orders", "DISTINCT"),
            ("SELECT * FROM orders LIMIT 5 OFFSET 10", "OFFSET"),
            ("SELECT * FROM orders LIMIT 5, 10", "OFFSET"),
            ("WITH x AS (SELECT 1 AS a) SELECT a FROM x", "CTE"),
            ("SELECT * FROM orders WHERE customer_id IN (SELECT id FROM c)", "SUBQUERY"),
            ("SELECT * FROM orders UNION SELECT * FROM orders", "SET_OP"),
            ("SELECT * FROM orders WHERE customer_id = 1 AND UPPER(status) = 'A'", "PRED"),
        ]:
            with self.subTest(sql=sql):
                r = run(sql)
                assert r.status == "ERROR" and code in codes(r), r.issues

    def test_oracle_rownum_and_fetch(self):
        r = run("SELECT ename FROM emp WHERE deptno = 1 AND ROWNUM <= 5", "oracle", with_schema=False)
        assert r.converted[0] == "SELECT ename FROM emp WHERE deptno = 1 LIMIT 5"
        r = run("SELECT ename FROM emp ORDER BY sal FETCH FIRST 3 ROWS ONLY", "oracle", with_schema=False)
        assert r.converted[0] == "SELECT ename FROM emp ORDER BY sal LIMIT 3"

    def test_oracle_join_mark_becomes_left_join(self):
        r = run("SELECT e.ename, d.dname FROM emp e, dept d WHERE e.deptno = d.deptno(+)", "oracle", with_schema=False)
        assert r.status == "WARN" and "ORACLE_JOIN_MARK" in codes(r)
        assert r.converted[0] == "SELECT e.ename, d.dname FROM emp AS e LEFT JOIN dept AS d ON e.deptno = d.deptno"

    def test_comma_join_rewritten(self):
        r = run("SELECT e.ename, d.dname FROM emp e, dept d WHERE e.deptno = d.deptno AND e.sal > 1", "oracle",
                with_schema=False)
        assert r.converted[0] == "SELECT e.ename, d.dname FROM emp AS e INNER JOIN dept AS d ON e.deptno = d.deptno WHERE e.sal > 1"

    def test_join_using_rewritten_and_key_coverage_checked(self):
        r = run("SELECT c.name FROM customers c JOIN orders o USING (customer_id)")
        assert "ON c.customer_id = o.customer_id" in r.converted[0]
        assert "JOIN_KEY" in codes(r)  # orders PK is (customer_id, order_no): not covered

    def test_to_date_literal(self):
        r = run("SELECT ename FROM emp WHERE hiredate > TO_DATE('2020-01-01', 'YYYY-MM-DD')", "oracle", with_schema=False)
        assert r.converted[0].endswith("WHERE hiredate > '2020-01-01'")

    def test_ansi_date_literal(self):
        # Oracle ANSI date literals; SQLGlot represents them as DateStrToDate / TimeStrToTime
        for literal, value in [("DATE '2020-01-01'", "'2020-01-01'"),
                               ("TIMESTAMP '2020-01-01 10:00:00'", "'2020-01-01 10:00:00'")]:
            with self.subTest(literal=literal):
                r = run(f"SELECT ename FROM emp WHERE hiredate > {literal}", "oracle", with_schema=False)
                assert r.status != "ERROR" and r.converted[0].endswith(f"WHERE hiredate > {value}")

    def test_bind_markers(self):
        assert run("SELECT * FROM emp WHERE empno = :id", "oracle", with_schema=False).converted[0].endswith("= :id")
        assert run("SELECT * FROM emp WHERE empno = $1", "postgres", with_schema=False).converted[0].endswith("= ?")
        assert run("SELECT * FROM emp WHERE empno = ?", "mysql", with_schema=False).converted[0].endswith("= ?")

    def test_rollup_grouping_sets_and_rowid_are_errors(self):
        assert "GROUP" in codes(run("SELECT deptno, SUM(amount) FROM orders GROUP BY ROLLUP (deptno)", "oracle", with_schema=False))
        assert "GROUP" in codes(run("SELECT deptno FROM orders GROUP BY GROUPING SETS ((deptno), (status))", "oracle", with_schema=False))
        assert "ROWID" in codes(run("SELECT status FROM orders WHERE ROWID IS NOT NULL", "oracle", with_schema=False))

    def test_using_column_is_qualified_with_from_table(self):
        r = run("SELECT name FROM customers c JOIN orders o USING (customer_id) WHERE customer_id = 1")
        assert "WHERE c.customer_id = 1" in r.converted[0]

    def test_timestamp_literal_against_date_column_is_trimmed(self):
        ddl = "CREATE TABLE emp (empno INT PRIMARY KEY, hiredate DATE);"
        results, _ = convert_script(ddl + "SELECT empno FROM emp WHERE hiredate > TO_TIMESTAMP('1981-06-01 00:00:00', 'YYYY-MM-DD HH24:MI:SS')",
                                    "oracle", decompose=False)
        assert results[-1].converted[0].endswith("WHERE hiredate > '1981-06-01'")
        results, _ = convert_script(ddl + "SELECT empno FROM emp WHERE hiredate < TIMESTAMP '1982-06-01 00:00:00'", "oracle", decompose=False)
        assert results[-1].converted[0].endswith("WHERE hiredate < '1982-06-01'")


class DmlTests(unittest.TestCase):
    def test_insert_missing_pk_is_error(self):
        assert "PK" in codes(run("INSERT INTO orders (customer_id, status) VALUES (1, 'A')"))

    def test_insert_with_function_value_is_error(self):
        r = run("INSERT INTO orders (customer_id, order_no, status) VALUES (1, 2, NOW())")
        assert r.status == "ERROR" and "NOW" in codes(r)

    def test_on_duplicate_key_to_upsert(self):
        r = run("INSERT INTO orders (customer_id, order_no, status) VALUES (1, 2, 'A') ON DUPLICATE KEY UPDATE status = VALUES(status)")
        assert r.converted[0] == "UPSERT INTO orders (customer_id, order_no, status) VALUES (1, 2, 'A')"
        assert r.status == "OK"

    def test_on_conflict_to_upsert_and_do_nothing_error(self):
        r = run("INSERT INTO t (id, v) VALUES (1, 'a') ON CONFLICT (id) DO UPDATE SET v = EXCLUDED.v", "postgres", with_schema=False)
        assert r.converted[0].startswith("UPSERT INTO t (id, v)")
        r = run("INSERT INTO t (id, v) VALUES (1, 'a') ON CONFLICT (id) DO NOTHING", "postgres", with_schema=False)
        assert "DO_NOTHING" in codes(r)

    def test_on_conflict_with_expression_is_error(self):
        r = run("INSERT INTO t (id, n) VALUES (1, 1) ON CONFLICT (id) DO UPDATE SET n = t.n + 1", "postgres", with_schema=False)
        assert r.status == "ERROR"

    def test_replace_into_to_upsert(self):
        r = run("REPLACE INTO orders (customer_id, order_no, status) VALUES (1, 2, 'A')")
        assert r.converted[0].startswith("UPSERT INTO orders") and "REPLACE" in codes(r)

    def test_merge_constant_source_to_upsert(self):
        sql = ("MERGE INTO emp t USING (SELECT 1 AS empno, 'X' AS ename FROM dual) s ON (t.empno = s.empno) "
               "WHEN MATCHED THEN UPDATE SET t.ename = s.ename WHEN NOT MATCHED THEN INSERT (empno, ename) VALUES (s.empno, s.ename)")
        assert run(sql, "oracle", with_schema=False).converted[0] == "UPSERT INTO emp (empno, ename) VALUES (1, 'X')"

    def test_update_rmw_is_error_and_literal_ok(self):
        assert "RMW" in codes(run("UPDATE orders SET amount = amount + 1 WHERE customer_id = 1 AND order_no = 2"))
        r = run("UPDATE orders SET status = 'B', amount = NULL WHERE customer_id = 1 AND order_no = 2")
        assert r.converted[0] == "UPDATE orders SET status = 'B', amount = NULL WHERE customer_id = 1 AND order_no = 2"

    def test_update_join_and_delete_using_are_errors(self):
        assert "UPDATE_JOIN" in codes(run("UPDATE orders o JOIN c ON o.customer_id = c.id SET o.status = 'X'"))
        assert "DELETE_JOIN" in codes(run("DELETE FROM orders USING c WHERE orders.customer_id = c.id", "postgres", with_schema=False))

    def test_delete_without_where_warns(self):
        r = run("DELETE FROM orders")
        assert r.status == "WARN" and "NO_WHERE" in codes(r)

    def test_transactions(self):
        assert run("START TRANSACTION").converted == ["BEGIN"]
        assert run("BEGIN", "postgres", with_schema=False).converted == ["BEGIN"]
        assert run("ROLLBACK").converted == ["ROLLBACK"]


class StorageAwareTests(unittest.TestCase):
    """Non-JDBC storage (Cassandra) cannot push down cross-partition scans or orderings."""

    def test_cross_partition_order_by_is_pushed_down_on_jdbc_only(self):
        sql = "SELECT order_no FROM orders WHERE status = 'X' ORDER BY amount"
        assert run_on(sql, "jdbc").status == "WARN"
        r = run_on(sql, "cassandra")
        assert r.status == "ERROR" and "ORDER_STORAGE" in codes(r)
        assert "ORDER_STORAGE" in codes(run_on("SELECT order_no FROM orders ORDER BY amount LIMIT 10", "cassandra"))

    def test_partition_scan_in_clustering_order_is_kept_on_cassandra(self):
        for order in ("order_no", "order_no DESC"):
            r = run_on(f"SELECT order_no FROM orders WHERE customer_id = 1 ORDER BY {order} LIMIT 10", "cassandra")
            assert r.status == "OK", codes(r)
        assert "ORDER_STORAGE" in codes(run_on("SELECT order_no FROM orders WHERE customer_id = 1 ORDER BY amount", "cassandra"))

    def test_mixed_directions_against_the_clustering_order_fail_on_cassandra(self):
        ddl = "CREATE TABLE ev (dev INT, ts INT, seq INT, v INT, PRIMARY KEY (dev, ts, seq));"
        results, _ = convert_script(ddl + "SELECT v FROM ev WHERE dev = 1 ORDER BY ts DESC, seq", "mysql",
                                    decompose=False, storage="cassandra")
        assert "ORDER_STORAGE" in codes(results[-1])
        results, _ = convert_script(ddl + "SELECT v FROM ev WHERE dev = 1 ORDER BY ts DESC, seq DESC", "mysql",
                                    decompose=False, storage="cassandra")
        assert results[-1].status == "OK"

    def test_grouped_order_by_is_sorted_by_the_sql_layer(self):
        r = run_on("SELECT status, COUNT(*) FROM orders WHERE customer_id = 1 GROUP BY status ORDER BY status", "cassandra")
        assert r.status == "OK", codes(r)
        assert run_on("SELECT status, COUNT(*) FROM orders GROUP BY status ORDER BY status", "jdbc").status == "WARN"

    def test_no_cross_partition_scan_on_cassandra(self):
        for sql in ("SELECT status, COUNT(*) FROM orders GROUP BY status",
                    "SELECT order_no FROM orders WHERE amount > 10",
                    "SELECT order_no FROM orders WHERE amount = 1 OR amount = 2"):
            assert run_on(sql, "jdbc").status == "WARN"
            r = run_on(sql, "cassandra")
            assert r.status == "ERROR" and "NO_CROSS_PARTITION" in codes(r), (sql, codes(r))
        for sql in ("UPDATE orders SET amount = 0 WHERE amount > 1", "DELETE FROM orders WHERE amount > 10"):
            r = run_on(sql, "cassandra")
            assert r.status == "ERROR" and "NO_CROSS_PARTITION" in codes(r), (sql, codes(r))
        # a key or index condition plus a non-key filter is served without a cross-partition scan
        for sql in ("UPDATE orders SET amount = 0 WHERE customer_id = 1 AND order_no = 2",
                    "UPDATE orders SET amount = 0 WHERE status = 'X' AND amount > 1",
                    "SELECT order_no FROM orders WHERE customer_id = 1 AND amount > 1"):
            assert run_on(sql, "cassandra").status == "OK", sql

    def test_key_in_list_is_split_only_on_cassandra_selects(self):
        sql = "SELECT order_no FROM orders WHERE customer_id IN (1, 2, 3)"
        assert run_on(sql, "jdbc").status == "WARN"
        assert "OR_KEYS" in codes(run_on(sql, "cassandra"))
        assert "OR_KEYS" in codes(run_on("SELECT order_no FROM orders WHERE status IN ('A', 'B') AND amount > 1", "cassandra"))
        r = run_on("UPDATE orders SET amount = 0 WHERE customer_id IN (1, 2)", "cassandra")  # writes are not planned
        assert r.status == "ERROR" and "OR_KEYS" not in codes(r) and "NO_CROSS_PARTITION" in codes(r)


if __name__ == "__main__":
    unittest.main()
