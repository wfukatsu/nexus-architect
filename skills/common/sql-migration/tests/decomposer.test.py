#!/usr/bin/env python3
"""Offline differential tests for the decomposer (ported from sql-migration tests/test_decomposer.py).

Full tables live in an in-memory SQLite database standing in for the source database. For each
statement: run the ORIGINAL SQL on the full tables (expected), then simulate the plan — fetch = run
each fetch's ScalarDB SQL on the full tables, residual = run the plan's python (sqlite) SQL on the
fetched rows only. Both must agree, which proves the pushdown never drops needed rows.
"""
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support  # noqa: E402

support.require_sqlglot()
import sqlglot  # noqa: E402
from scalardb_migrate.converter import convert_script  # noqa: E402

DDL = """
CREATE TABLE emp (empno INT, ename VARCHAR(10), sal DOUBLE, comm DOUBLE, deptno INT, hiredate DATE, PRIMARY KEY (empno));
CREATE TABLE dept (deptno INT PRIMARY KEY, dname VARCHAR(20));
CREATE TABLE bonus (empno INT PRIMARY KEY, amount INT);
CREATE INDEX ix ON emp (deptno);
"""
EMP = [(1, "smith", 800, None, 10, "2021-03-01"), (2, "allen", 1600, 300, 30, "2019-05-02"),
       (3, "ward", 1250, 500, 30, "2022-01-15"), (4, "jones", 2975, None, 20, "2020-11-11")]
DEPT = [(10, "ACCOUNTING"), (20, "RESEARCH"), (30, "SALES")]
BONUS = [(2, 100), (4, 200)]

CASES = [
    ("mysql", "SELECT ename, IFNULL(comm, 0) AS c FROM emp WHERE deptno = 30", "P1"),
    ("mysql", "SELECT UPPER(ename) FROM emp WHERE deptno IN (10, 20) AND sal > 700", "P1"),
    ("postgres", "SELECT DISTINCT deptno FROM emp ORDER BY deptno", "P3"),
    ("postgres", "SELECT ename FROM emp ORDER BY sal DESC LIMIT 2 OFFSET 1", "P4"),
    ("postgres", "SELECT ename FROM emp WHERE empno IN (SELECT empno FROM bonus WHERE amount > 150)", "P5"),
    ("postgres", "WITH big AS (SELECT * FROM emp WHERE sal > 1000) SELECT COUNT(*) FROM big", "P6"),
    ("postgres", "SELECT ename FROM emp WHERE deptno = 10 UNION SELECT ename FROM emp WHERE sal > 2000", "P6"),
    ("postgres", "SELECT e.ename, d.dname FROM emp e JOIN dept d ON e.deptno = d.deptno WHERE d.dname = 'SALES' AND LENGTH(e.ename) > 3", "P8"),
    ("postgres", "SELECT e.ename, d.dname FROM emp e LEFT JOIN dept d ON e.deptno = d.deptno WHERE d.dname IS NULL OR e.sal > 2000", "P8"),
    ("postgres", "SELECT deptno, COUNT(*) FROM emp WHERE NOT (sal < 1000) GROUP BY deptno HAVING MAX(sal) - MIN(sal) > 0", "P2"),
    ("postgres", "SELECT ename FROM emp e WHERE EXISTS (SELECT 1 FROM bonus b WHERE b.empno = e.empno)", "P5"),
    ("oracle", "SELECT ename, sal * 2 AS s2 FROM emp WHERE deptno = 30 AND ROWNUM <= 1", "P1",
     "SELECT ename, sal * 2 AS s2 FROM emp WHERE deptno = 30 LIMIT 1"),  # SQLite has no ROWNUM: expected via LIMIT
]
CASES = [c if len(c) == 4 else (*c, None) for c in CASES]

CASSANDRA_CASES = [  # (sql, pattern, access paths of the fetches)
    ("SELECT ename FROM emp WHERE deptno = 30 ORDER BY ename", "P13", ["INDEX_SCAN"]),
    ("SELECT ename FROM emp WHERE empno IN (1, 3, 4)", "P14", ["GET", "GET", "GET"]),
    ("SELECT ename FROM emp WHERE deptno IN (10, 30) AND sal > 900", "P14", ["INDEX_SCAN", "INDEX_SCAN"]),
    ("SELECT ename FROM emp WHERE empno IN (1, 2, 3) ORDER BY sal", "P13", ["GET", "GET", "GET"]),
]


def _db():
    con = sqlite3.connect(":memory:")
    con.executescript("CREATE TABLE emp (empno, ename, sal, comm, deptno, hiredate); CREATE TABLE dept (deptno, dname);"
                      "CREATE TABLE bonus (empno, amount);")
    con.executemany("INSERT INTO emp VALUES (?,?,?,?,?,?)", EMP)
    con.executemany("INSERT INTO dept VALUES (?,?)", DEPT)
    con.executemany("INSERT INTO bonus VALUES (?,?)", BONUS)
    return con


def _plan(dialect, sql, storage="jdbc"):
    results, _ = convert_script(DDL + sql, "mysql" if dialect == "mysql" else dialect, storage=storage)
    r = results[-1]
    assert r.status == "PLANNED", [(i.code, i.message) for i in r.issues]
    return r.plan


def _simulate(dialect, sql, plan, expected_sql=None):
    """Run the original SQL on the full tables and the plan (fetches + residual) on the fetched rows only."""
    full = _db()
    expected = full.execute(expected_sql or sqlglot.transpile(sql, read=dialect, write="sqlite")[0]).fetchall()
    sim = sqlite3.connect(":memory:")
    for f in plan["fetch"]:
        rows = full.execute(f["scalardb_sql"].replace(":", "")).fetchall()  # ScalarDB SQL is plain enough for SQLite
        cols = f["columns"] or [d[0] for d in full.execute(f"SELECT * FROM {f['table']} LIMIT 0").description]
        # a split IN-list fetches one table several times (disjoint rows); the runtime merges them the same way
        sim.execute(f"CREATE TABLE IF NOT EXISTS {f['table']} ({', '.join(cols)})")
        sim.executemany(f"INSERT INTO {f['table']} VALUES ({', '.join('?' for _ in cols)})", rows)
        assert len(rows) <= len(full.execute(f"SELECT * FROM {f['table']}").fetchall())
    actual = sim.execute(plan["residual"]["python"]["sql"]).fetchall()
    return expected, actual


class DecomposerTests(unittest.TestCase):
    def test_fetch_plus_residual_equals_original(self):
        for dialect, sql, pattern, expected_sql in CASES:
            with self.subTest(sql=sql):
                plan = _plan(dialect, sql)
                assert pattern in plan["pattern"]
                assert not plan["unresolved"], plan["unresolved"]
                expected, actual = _simulate(dialect, sql, plan, expected_sql)
                assert sorted(map(str, actual)) == sorted(map(str, expected))

    def test_pushdown_predicates_and_access_path(self):
        plan = _plan("mysql", "SELECT UPPER(ename) FROM emp WHERE deptno IN (10, 20) AND sal > 700")
        f = plan["fetch"][0]
        assert f["table"] == "emp" and f["columns"] == ["empno", "ename", "sal", "deptno"]
        assert f["scalardb_sql"] == "SELECT empno, ename, sal, deptno FROM emp WHERE (deptno = 10 OR deptno = 20) AND sal > 700"
        assert _plan("postgres", "SELECT UPPER(ename) FROM emp WHERE empno = 1")["fetch"][0]["access_path"] == "GET"
        assert _plan("postgres", "SELECT UPPER(ename) FROM emp WHERE deptno = 1")["fetch"][0]["access_path"] == "INDEX_SCAN"

    def test_outer_join_null_test_is_not_pushed_down(self):
        plan = _plan("postgres", "SELECT e.ename FROM emp e LEFT JOIN dept d ON e.deptno = d.deptno WHERE d.dname IS NULL")
        assert [f for f in plan["fetch"] if f["table"] == "dept"][0]["predicates"] == []

    def test_oracle_join_mark_outer_join_keeps_null_test_out_of_fetch(self):
        plan = _plan("oracle", "SELECT e.ename, d.dname FROM emp e, dept d WHERE e.deptno = d.deptno(+) "
                               "AND (d.dname LIKE 'S%' OR d.dname IS NULL)")
        assert [f for f in plan["fetch"] if f["table"] == "dept"][0]["predicates"] == []
        assert "LEFT JOIN dept d ON e.deptno = d.deptno" in plan["residual"]["java"]["sql"]

    def test_correlated_scalar_subquery_fetches_outer_columns_and_minus_is_planned(self):
        plan = _plan("oracle", "SELECT e.ename, (SELECT d.dname FROM dept d WHERE d.deptno = e.deptno) AS dn FROM emp e")
        assert "deptno" in [f for f in plan["fetch"] if f["table"] == "emp"][0]["columns"]
        plan = _plan("oracle", "SELECT deptno FROM dept MINUS SELECT deptno FROM emp")
        assert {f["table"] for f in plan["fetch"]} == {"dept", "emp"}

    def test_h2_date_rewrites(self):
        sql = _plan("oracle", "SELECT ename, TRUNC(hiredate, 'MM') AS m, DATE '1982-01-01' - hiredate AS d FROM emp")["residual"]["java"]["sql"]
        assert "DATE_TRUNC('MONTH', hiredate)" in sql and "DAYS_BETWEEN(" in sql

    def test_residual_java_keeps_original_sql_and_h2_mode(self):
        plan = _plan("mysql", "SELECT DATE_FORMAT(hiredate, '%Y-%m') AS ym FROM emp WHERE deptno = 30")
        assert plan["residual"]["java"]["mode"] == "MySQL"
        assert "FORMATDATETIME(hiredate, 'yyyy-MM')" in plan["residual"]["java"]["sql"]
        plan = _plan("oracle", "SELECT NVL(comm, 0) FROM emp WHERE deptno = 30")
        assert plan["residual"]["java"]["sql"] == "SELECT NVL(comm, 0) FROM emp WHERE deptno = 30"

    def test_write_statements_are_not_planned(self):
        results, _ = convert_script(DDL + "UPDATE emp SET sal = sal + 1 WHERE empno = 1", "postgres")
        assert results[-1].status == "ERROR" and results[-1].plan is None

    def test_residual_makes_source_null_ordering_explicit(self):
        """H2 sorts NULLs first for ASC; Oracle and PostgreSQL sort them last. The residual SQL must say which."""
        assert "ORDER BY comm NULLS LAST" in _plan("oracle", "SELECT NVL(comm, 0) AS c FROM emp ORDER BY comm")["residual"]["java"]["sql"]
        assert "ORDER BY comm DESC NULLS FIRST" in _plan("oracle", "SELECT NVL(comm, 0) AS c FROM emp ORDER BY comm DESC")["residual"]["java"]["sql"]
        assert "ORDER BY comm NULLS LAST" in _plan("postgres", "SELECT COALESCE(comm, 0) AS c FROM emp ORDER BY comm")["residual"]["java"]["sql"]
        # MySQL sorts NULLs first for ASC, which is also H2's rule, so nothing has to be added
        assert "NULLS" not in _plan("mysql", "SELECT IFNULL(comm, 0) AS c FROM emp ORDER BY comm")["residual"]["java"]["sql"]

    def test_cassandra_plans_sort_in_h2_and_split_key_in_lists(self):
        for sql, pattern, paths in CASSANDRA_CASES:
            with self.subTest(sql=sql):
                plan = _plan("postgres", sql, storage="cassandra")
                assert pattern in plan["pattern"]
                assert [f["access_path"] for f in plan["fetch"]] == paths
                assert all("ORDER BY" not in f["scalardb_sql"] for f in plan["fetch"])
                expected, actual = _simulate("postgres", sql, plan)
                assert actual == expected if "ORDER BY" in sql and "LIMIT" in sql else sorted(map(str, actual)) == sorted(map(str, expected))

    def test_cassandra_statements_without_a_key_to_fetch_by_are_not_executable(self):
        for sql in ["SELECT ename, sal FROM emp ORDER BY sal DESC LIMIT 2",
                    "SELECT e.ename, d.dname FROM emp e JOIN dept d ON e.deptno = d.deptno ORDER BY e.ename",
                    "SELECT deptno, COUNT(*) FROM emp GROUP BY deptno",
                    "SELECT UPPER(ename) FROM emp WHERE sal > 1000"]:
            with self.subTest(sql=sql):
                results, _ = convert_script(DDL + sql, "postgres", storage="cassandra")
                r = results[-1]
                assert r.status == "ERROR" and r.plan is None and "FULL_SCAN" in {i.code for i in r.issues}
                results, _ = convert_script(DDL + sql, "postgres")  # the same statement on a JDBC backend
                assert results[-1].status in ("WARN", "PLANNED")

    def test_jdbc_plans_are_not_split(self):
        plan = _plan("postgres", "SELECT UPPER(ename) FROM emp WHERE empno IN (1, 3)")
        assert len(plan["fetch"]) == 1 and plan["fetch"][0]["access_path"] == "CROSS_PARTITION"
        plan = _plan("postgres", "SELECT UPPER(ename) FROM emp WHERE empno IN (1, 3)", storage="cassandra")
        assert [f["scalardb_sql"] for f in plan["fetch"]] == ["SELECT empno, ename FROM emp WHERE empno = 1",
                                                              "SELECT empno, ename FROM emp WHERE empno = 3"]


if __name__ == "__main__":
    unittest.main()
