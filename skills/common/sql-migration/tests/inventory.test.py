#!/usr/bin/env python3
"""The SQL inventory contract: every statement a migration must decide, from each source kind, with its
evidence, its dynamic-SQL flags and no stored literal."""
import hashlib
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
import inventory  # noqa: E402

SCRIPT = support.ROOT / "scripts/inventory.py"

MAPPER = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
    <mapper namespace="com.shop.OrderMapper">
      <sql id="orderColumns">order_id, customer_id, status</sql>
      <!-- <select id="commented">SELECT 1 FROM dual</select> -->
      <select id="findById" resultType="Order">
        SELECT <include refid="orderColumns"/> FROM orders WHERE order_id = #{orderId}
      </select>
      <select id="search" resultType="Order">
        SELECT order_id FROM orders
        <where>
          <if test="status != null">status = #{status}</if>
        </where>
      </select>
      <delete id="purge">DELETE FROM ${tableName} WHERE status = 'SECRET-LITERAL'</delete>
      <update id="close">UPDATE orders SET status = 'CLOSED' WHERE order_id IN
        <foreach collection="ids" item="id" open="(" separator="," close=")">#{id}</foreach>
      </update>
    </mapper>
    """)

DAO = textwrap.dedent('''\
    package com.shop;

    public class OrderDao {
      private static final String FIND = "SELECT order_id, total FROM orders " +
          "WHERE customer_id = ?";
      // conn.prepareStatement("SELECT not_a_statement FROM comments")

      Order find(Connection conn, long id) throws SQLException {
        try (PreparedStatement ps = conn.prepareStatement("SELECT order_id FROM orders WHERE order_id = ?")) {
          return map(ps.executeQuery());
        }
      }

      List<Order> byCustomer(Connection conn) throws SQLException {
        return list(conn.prepareStatement(FIND));
      }

      List<Order> sorted(Connection conn, String column) throws SQLException {
        return list(conn.createStatement().executeQuery("SELECT order_id FROM orders ORDER BY " + column));
      }

      int archive(JdbcTemplate jdbc) {
        return jdbc.update("""
            UPDATE orders
               SET status = 'SECRET-LITERAL'
             WHERE order_date < ?
            """);
      }
    }
    ''')

REPO = textwrap.dedent('''\
    package com.shop;

    public interface OrderRepository extends JpaRepository<Order, Long> {
      @Query(value = "SELECT * FROM orders WHERE status = :status", nativeQuery = true)
      List<Order> nativeByStatus(@Param("status") String status);

      @Query("SELECT o FROM Order o WHERE o.total > :min")
      List<Order> jpqlByTotal(@Param("min") BigDecimal min);
    }
    ''')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def by_locator(result, suffix):
    return next(s for s in result["statements"] if s["origin"].get("locator", "").endswith(suffix))


class AppCodeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src/main/resources/mapper").mkdir(parents=True)
        (self.root / "src/main/java/com/shop").mkdir(parents=True)
        (self.root / "src/main/resources/mapper/OrderMapper.xml").write_text(MAPPER)
        (self.root / "src/main/java/com/shop/OrderDao.java").write_text(DAO)
        (self.root / "src/main/java/com/shop/OrderRepository.java").write_text(REPO)
        self.result = inventory.build(source="oracle", app_roots=[self.root])

    def tearDown(self):
        self.tmp.cleanup()

    def test_mybatis_static_statement_resolves_includes_and_binds(self):
        s = by_locator(self.result, "OrderMapper#findById")
        self.assertEqual(s["sql"], "SELECT order_id, customer_id, status FROM orders WHERE order_id = ?")
        self.assertEqual(s["binds"], ["orderId"])
        self.assertFalse(s["dynamic"])
        self.assertEqual((s["origin"]["kind"], s["category"], s["language"]), ("app_code", "query", "sql"))
        start, end = s["origin"]["lines"]
        self.assertIn("findById", (self.root / s["origin"]["path"]).read_text().splitlines()[start - 1])
        self.assertGreaterEqual(end, start)

    def test_mybatis_dynamic_elements_are_flagged_not_expanded(self):
        self.assertEqual(by_locator(self.result, "OrderMapper#search")["dynamic_reasons"], ["mybatis_where", "mybatis_if"])
        self.assertEqual(by_locator(self.result, "OrderMapper#purge")["dynamic_reasons"], ["mybatis_dollar"])
        self.assertEqual(by_locator(self.result, "OrderMapper#close")["dynamic_reasons"], ["mybatis_foreach"])
        self.assertFalse(any("commented" in s["origin"].get("locator", "") for s in self.result["statements"]))

    def test_java_literals_constants_and_text_blocks_are_static(self):
        dao = [s for s in self.result["statements"] if s["origin"]["path"].endswith("OrderDao.java")]
        static = {s["sql"] for s in dao if not s["dynamic"]}
        self.assertIn("SELECT order_id FROM orders WHERE order_id = ?", static)
        self.assertIn("SELECT order_id, total FROM orders WHERE customer_id = ?", static)
        self.assertTrue(any(s.startswith("UPDATE orders") and "WHERE order_date < ?" in s for s in static))
        self.assertFalse(any("not_a_statement" in s["sql"] for s in dao))

    def test_java_concatenation_with_a_variable_is_dynamic(self):
        dynamic = [s for s in self.result["statements"] if s["dynamic"] and s["origin"]["path"].endswith("OrderDao.java")]
        self.assertEqual(len(dynamic), 1)
        self.assertEqual(dynamic[0]["dynamic_reasons"], ["java_concatenation"])
        self.assertTrue(dynamic[0]["sql"].startswith("SELECT order_id FROM orders ORDER BY"))

    def test_jpa_native_query_is_sql_and_jpql_is_marked(self):
        native = by_locator(self.result, "OrderRepository#nativeByStatus")
        self.assertEqual((native["language"], native["sql"]), ("sql", "SELECT * FROM orders WHERE status = :status"))
        self.assertEqual(by_locator(self.result, "OrderRepository#jpqlByTotal")["language"], "jpql")

    def test_string_literals_are_never_stored(self):
        encoded = json.dumps(self.result)
        self.assertNotIn("SECRET-LITERAL", encoded)
        self.assertNotIn("CLOSED", encoded)
        purge = by_locator(self.result, "OrderMapper#purge")
        self.assertIn("'?'", purge["sql"])
        self.assertRegex(purge["text_sha256"], r"^[0-9a-f]{64}$")

    def test_full_text_is_recovered_from_the_source_on_demand(self):
        s = by_locator(self.result, "OrderMapper#purge")
        text = inventory.statement_text(s, project_dir=self.root)
        self.assertIn("'SECRET-LITERAL'", text)
        (self.root / "src/main/resources/mapper/OrderMapper.xml").write_text(MAPPER.replace("SECRET-LITERAL", "CHANGED"))
        with self.assertRaises(inventory.StaleEvidence):
            inventory.statement_text(s, project_dir=self.root)

    def test_ids_are_sequential_and_kept_across_runs(self):
        ids = [s["id"] for s in self.result["statements"]]
        self.assertEqual(ids, [f"SQM-{i:03d}" for i in range(1, len(ids) + 1)])
        (self.root / "src/main/resources/mapper/OrderMapper.xml").write_text(
            MAPPER.replace('<delete id="purge">', '<select id="added">SELECT 1 FROM dual</select>\n  <delete id="purge">'))
        again = inventory.build(source="oracle", app_roots=[self.root], previous=self.result)
        old = {s["fingerprint"]: s["id"] for s in self.result["statements"]}
        for s in again["statements"]:
            if s["fingerprint"] in old:
                self.assertEqual(s["id"], old[s["fingerprint"]])
        self.assertEqual(by_locator(again, "OrderMapper#added")["id"], f"SQM-{len(ids) + 1:03d}")


class UnextractedCallTests(unittest.TestCase):
    """What static reading cannot resolve is counted, so absence from the inventory is never silent."""

    def extract(self, java):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Dao.java").write_text(java)
            return inventory.build(source="postgres", app_roots=[root], project_dir=root)

    def test_constant_built_from_a_variable_stays_a_dynamic_statement(self):
        result = self.extract(textwrap.dedent('''\
            class Dao {
              List<Row> sorted(Connection conn, String column) throws SQLException {
                String sql = "SELECT id FROM t ORDER BY " + column;
                return rows(conn.prepareStatement(sql));
              }
            }
            '''))
        self.assertEqual([(s["sql"], s["dynamic_reasons"]) for s in result["statements"]],
                         [("SELECT id FROM t ORDER BY ${column}", ["java_concatenation"])])
        self.assertEqual(result["unextracted"], [])

    def test_sql_passed_in_from_elsewhere_is_counted_not_guessed(self):
        result = self.extract(textwrap.dedent('''\
            class Dao {
              int run(Connection conn, JdbcTemplate jdbcTemplate, ExecutorService executor, String sql) throws Exception {
                conn.prepareStatement(sql);
                jdbcTemplate.update(buildUpdate());
                executor.execute(() -> work());
                return list.update(sql);
              }
            }
            '''))
        self.assertEqual(result["statements"], [])
        self.assertEqual([(u["method"], u["locator"], u["lines"]) for u in result["unextracted"]],
                         [("prepareStatement", "Dao#run", [3, 3]), ("update", "Dao#run", [4, 4])])
        self.assertEqual(result["summary"]["unextracted"], 2)


class SqlFileAndDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_sql_file_statements_carry_lines_and_categories(self):
        f = self.root / "batch.sql"
        f.write_text("-- nightly\nUPDATE stock SET qty = 0\n  WHERE qty < 0;\n\nSELECT COUNT(*) FROM stock;\n")
        result = inventory.build(source="postgres", sql_files=[f], project_dir=self.root)
        self.assertEqual([(s["category"], s["origin"]["lines"]) for s in result["statements"]], [("dml", [2, 3]), ("query", [5, 5])])
        self.assertEqual(result["statements"][0]["origin"]["sha256"], sha(f))

    def design_run(self, ddl_text, tamper=False):
        ddl = self.root / "schema.sql"
        ddl.write_text(ddl_text)
        run = self.root / "reports/01_analysis/database-investigation/shop/design/r1"
        run.mkdir(parents=True)
        digest = sha(ddl)
        inv = {
            "mode": "design", "product": "postgresql", "schema": "app",
            "evidence": [
                {"id": "E1", "kind": "file", "path": "schema.sql", "sha256": digest, "lines": [1, 1]},
                {"id": "E2", "kind": "file", "path": "schema.sql", "sha256": digest, "lines": [2, 3]},
            ],
            "objects": [
                {"id": '[null,"app","table","orders"]', "kind": "table", "name": "orders", "evidence_ids": ["E1"]},
                {"id": '[null,"app","view","open_orders"]', "kind": "view", "name": "open_orders", "evidence_ids": ["E2"]},
            ],
        }
        (run / "inventory.json").write_text(json.dumps(inv))
        if tamper:
            ddl.write_text(ddl_text + "-- edited after the investigation\n")
        return run

    def test_design_run_evidence_is_reread_and_linked_to_objects(self):
        run = self.design_run("CREATE TABLE app.orders (id INT PRIMARY KEY);\nCREATE VIEW app.open_orders AS\n  SELECT id FROM app.orders;\n")
        result = inventory.build(source="postgres", db_runs=[run], project_dir=self.root)
        self.assertEqual([(s["category"], s["origin"]["object_ids"]) for s in result["statements"]],
                         [("ddl", ['[null,"app","table","orders"]']), ("view", ['[null,"app","view","open_orders"]'])])
        self.assertEqual(result["problems"], [])

    def test_design_run_evidence_that_no_longer_matches_is_a_problem(self):
        run = self.design_run("CREATE TABLE app.orders (id INT PRIMARY KEY);\nCREATE VIEW app.open_orders AS\n  SELECT id FROM app.orders;\n", tamper=True)
        result = inventory.build(source="postgres", db_runs=[run], project_dir=self.root)
        self.assertEqual(result["statements"], [])
        self.assertEqual({p["code"] for p in result["problems"]}, {"stale_evidence"})

    def test_live_run_objects_without_source_are_counted_not_invented(self):
        run = self.root / "live-run"
        run.mkdir()
        (run / "inventory.json").write_text(json.dumps({
            "mode": "live", "product": "oracle", "schema": "APP",
            "evidence": [{"id": "E1", "kind": "query", "query_id": "views", "schema": "APP", "collected_at": "t"}],
            "objects": [{"id": '[null,"APP","view","V1"]', "kind": "view", "name": "V1", "evidence_ids": ["E1"]},
                        {"id": '[null,"APP","table","T1"]', "kind": "table", "name": "T1", "evidence_ids": ["E1"]}],
        }))
        result = inventory.build(source="oracle", db_runs=[run], project_dir=self.root)
        self.assertEqual(result["statements"], [])
        self.assertEqual([u["object_id"] for u in result["unavailable"]], ['[null,"APP","view","V1"]'])

    def test_cli_writes_the_inventory_and_reports_problems_with_exit_2(self):
        run = self.design_run("CREATE TABLE app.orders (id INT PRIMARY KEY);\nCREATE VIEW app.open_orders AS\n  SELECT id FROM app.orders;\n", tamper=True)
        out = self.root / "work/sql-inventory.json"
        r = subprocess.run([sys.executable, str(SCRIPT), "--source", "postgres", "--db-run", str(run), "--out", str(out)],
                           capture_output=True, text=True, cwd=self.root)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertEqual(json.loads(out.read_text())["schema_version"], 1)
        r = subprocess.run([sys.executable, str(SCRIPT), "--source", "postgres", "--out", str(out)], capture_output=True, text=True, cwd=self.root)
        self.assertEqual(r.returncode, 1)  # no source given at all


if __name__ == "__main__":
    unittest.main()
