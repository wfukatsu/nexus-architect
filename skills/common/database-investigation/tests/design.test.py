#!/usr/bin/env python3
"""Executable acceptance examples; no services or third-party packages."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from core.design import parse_design
from core.registry import load_adapter


class DesignTests(unittest.TestCase):
    def test_table_primary_key_implies_not_null(self):
        result=self.parse('CREATE TABLE t(a INT,b INT,PRIMARY KEY(a));')
        self.assertFalse(result["objects"][0]["columns"][0]["nullable"])
        self.assertTrue(result["objects"][0]["columns"][1]["nullable"])

    def parse(self, ddl, product="postgresql", schema="app"):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "input.sql"
            p.write_text(ddl)
            return parse_design([p], load_adapter(product)[0], schema)

    def test_composite_constraints_and_quoted_names_keep_evidence(self):
        result = self.parse('''CREATE TABLE app."Parent" (a INT, b INT, PRIMARY KEY(a,b));
        CREATE TABLE app.child (a INT NOT NULL, b INT, CONSTRAINT fk FOREIGN KEY(a,b) REFERENCES app."Parent"(a,b));
        CREATE UNIQUE INDEX ci ON app.child(a,b);''')
        tables = [o for o in result["objects"] if o["kind"] == "table"]
        self.assertEqual([o["name"] for o in tables], ["Parent", "child"])
        self.assertEqual(tables[1]["constraints"][0]["columns"], ["a", "b"])
        self.assertEqual(tables[1]["constraints"][0]["references"]["name"], "Parent")
        self.assertFalse(tables[1]["columns"][0]["nullable"])
        self.assertTrue(all(o["evidence_ids"] for o in result["objects"]))
        self.assertEqual(len(result["objects"]), 3)

    def test_dialect_blocks_do_not_swallow_following_tables(self):
        cases = {
            "postgresql": "CREATE FUNCTION f() RETURNS void AS $$ BEGIN RAISE NOTICE 'x;y'; END; $$ LANGUAGE plpgsql;",
            "oracle": "CREATE OR REPLACE EDITIONABLE PROCEDURE f AS BEGIN NULL; NULL; END;\n/\n",
            "mysql": "DELIMITER $$\nCREATE PROCEDURE f() BEGIN SELECT 'x;y'; END$$\nDELIMITER ;\n",
        }
        for product, block in cases.items():
            with self.subTest(product=product):
                result = self.parse(block + '\nCREATE TABLE tail (id INT);', product)
                self.assertEqual(len([o for o in result["objects"] if o["kind"] == "table"]), 1)
                self.assertTrue(any(o["kind"] == "procedure" or o["kind"] == "function" for o in result["objects"]))

    def test_unknown_sql_is_not_silently_successful(self):
        result = self.parse("CREATE TABLE t (id INT); VACUUM; ALTER TABLE t DROP COLUMN id;")
        self.assertEqual(sum(c["status"] == "unsupported" for c in result["collections"]), 2)

    def test_literals_comments_and_delimiters_are_not_leaked(self):
        result = self.parse("-- secret-comment\nCREATE TABLE t (id INT, note VARCHAR(100) DEFAULT 'secret;|value'); COMMENT ON TABLE t IS 'secret-doc';")
        encoded = json.dumps(result)
        self.assertNotIn("secret", encoded)
        self.assertEqual(len(result["objects"][0]["columns"]), 2)

    def test_alter_constraint_resolves_across_files(self):
        with tempfile.TemporaryDirectory() as d:
            paths = [Path(d) / "a.sql", Path(d) / "b.sql"]
            paths[0].write_text("ALTER TABLE child ADD CONSTRAINT fk FOREIGN KEY(p) REFERENCES parent(id);")
            paths[1].write_text("CREATE TABLE parent(id INT PRIMARY KEY); CREATE TABLE child(p INT);")
            result = parse_design(paths, {"id": "postgresql", "fold": "lower"}, "app")
        child = next(o for o in result["objects"] if o["name"] == "child")
        self.assertEqual(child["constraints"][0]["references"]["name"], "parent")

    def test_mysql_inline_keys_become_table_scoped_indexes_not_columns(self):
        result = self.parse("""CREATE TABLE `orders` (
  `id` int NOT NULL,
  `cust` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cust` (`cust`),
  KEY `idx_cust` (`cust`),
  CONSTRAINT `fk` FOREIGN KEY (`cust`) REFERENCES `cust` (`id`)
);""", "mysql", "shop")
        table = next(o for o in result["objects"] if o["kind"] == "table")
        self.assertEqual([c["name"] for c in table["columns"]], ["id", "cust"])
        self.assertIn({"kind": "unique", "name": "uk_cust", "columns": ["cust"]}, table["constraints"])
        indexes = {o["name"]: o["extensions"] for o in result["objects"] if o["kind"] == "index"}
        self.assertEqual(indexes["orders.idx_cust"], {"table_schema": "shop", "table": "orders", "columns": ["cust"], "unique": False})
        self.assertTrue(indexes["orders.uk_cust"]["unique"])
        self.assertEqual(result["collections"][0]["status"], "ok")

    def test_mysql_create_index_uses_the_same_table_scoped_name(self):
        result = self.parse("CREATE TABLE a(x INT); CREATE TABLE b(x INT); CREATE INDEX ix ON a(x); CREATE INDEX ix ON b(x);", "mysql", "shop")
        self.assertEqual(sorted(o["name"] for o in result["objects"] if o["kind"] == "index"), ["a.ix", "b.ix"])
        self.assertFalse(result["findings"])

    def test_key_is_an_ordinary_column_name_outside_mysql(self):
        result = self.parse("CREATE TABLE t (key varchar(10), index int);")
        self.assertEqual([c["name"] for c in result["objects"][0]["columns"]], ["key", "index"])

    def test_nullability_is_unknown_when_column_parsing_stops_early(self):
        result = self.parse("CREATE TABLE t (a int AUTO_INCREMENT NOT NULL, b int NOT NULL AUTO_INCREMENT, c int);", "mysql", "app")
        self.assertEqual([c["nullable"] for c in result["objects"][0]["columns"]], [None, False, True])

    def test_owner_differing_from_requested_schema_only_by_case_is_reported(self):
        result = self.parse("CREATE TABLE t1 (a NUMBER); CREATE TABLE app.t2 (a NUMBER);", "oracle", "app")
        self.assertEqual([o["name"] for o in result["objects"]], ["T1"])
        self.assertEqual(result["collections"][1]["status"], "not_collected")
        self.assertEqual([f["code"] for f in result["findings"]], ["schema_case_mismatch"])
        other = self.parse("CREATE TABLE other.t (a INT);")
        self.assertEqual(other["collections"][0]["status"], "empty")
        self.assertFalse(other["findings"])

    def test_pg_dump_snapshot_attaches_constraints_and_skips_session_noise(self):
        result = self.parse("""SET statement_timeout = 0;
SELECT pg_catalog.set_config('search_path', '', false);
CREATE TABLE public.cust (id integer NOT NULL);
CREATE TABLE public.orders (id integer NOT NULL, cust integer NOT NULL);
ALTER TABLE public.orders OWNER TO app_owner;
ALTER TABLE ONLY public.orders ALTER COLUMN id SET DEFAULT nextval('public.orders_id_seq'::regclass);
ALTER TABLE ONLY public.cust ADD CONSTRAINT cust_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.orders ADD CONSTRAINT orders_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.orders
    ADD CONSTRAINT fk FOREIGN KEY (cust) REFERENCES public.cust(id) ON UPDATE CASCADE ON DELETE RESTRICT;
CREATE INDEX orders_cust_idx ON public.orders USING btree (cust);""", "postgresql", "public")
        index = next(o for o in result["objects"] if o["kind"] == "index")
        self.assertEqual((index["extensions"]["columns"], index["extensions"]["method"]), (["cust"], "btree"))
        orders = next(o for o in result["objects"] if o["name"] == "orders")
        self.assertEqual([c["kind"] for c in orders["constraints"]], ["primary_key", "foreign_key"])
        fk = orders["constraints"][1]
        self.assertEqual((fk["on_update"], fk["on_delete"]), ("cascade", "restrict"))
        self.assertEqual({c["status"] for c in result["collections"]}, {"ok", "empty"})
        self.assertFalse(result["findings"])

    def test_statement_status_keeps_the_most_severe_outcome(self):
        for body in ("a INT AUTO_INCREMENT, b INT DEFAULT 0", "b INT DEFAULT 0, a INT AUTO_INCREMENT"):
            with self.subTest(body=body):
                status = self.parse(f"CREATE TABLE t ({body});", "mysql", "app")["collections"][0]
                self.assertEqual(status["status"], "unsupported")
                self.assertNotIn("default", status.get("reason", ""))
                self.assertEqual(status["withheld"], ["default_expression"])

    def test_policy_withholding_is_not_a_coverage_gap(self):
        result = self.parse("CREATE TABLE t (id INT DEFAULT 1, CHECK (id > 0)); COMMENT ON TABLE t IS 'doc'; CREATE VIEW v AS SELECT id FROM t;")
        self.assertEqual([c["status"] for c in result["collections"]], ["ok", "empty", "ok"])
        self.assertEqual([c.get("withheld") for c in result["collections"]], [["default_expression", "check_expression"], ["comment_text"], ["definition"]])

    def test_column_types_keep_their_native_compact_spelling(self):
        result = self.parse("CREATE TABLE t (a decimal(10, 2), b VARCHAR2(20 CHAR), c timestamp with time zone);", "oracle", "APP")
        self.assertEqual([c["type"] for c in result["objects"][0]["columns"]], ["decimal(10,2)", "VARCHAR2(20 CHAR)", "timestamp with time zone"])

    def test_schema_filter_duplicate_and_unterminated_input(self):
        result = self.parse("CREATE TABLE other.t(id INT); CREATE TABLE app.t(id INT); CREATE TABLE app.t(x INT); SELECT 'oops")
        self.assertEqual(len(result["objects"]), 1)
        self.assertTrue(any(c["status"] == "error" for c in result["collections"]))
        self.assertTrue(result["findings"])


if __name__ == "__main__":
    unittest.main()
