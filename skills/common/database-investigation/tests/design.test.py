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


class DesignTests(unittest.TestCase):
    def test_table_primary_key_implies_not_null(self):
        result=self.parse('CREATE TABLE t(a INT,b INT,PRIMARY KEY(a));')
        self.assertFalse(result["objects"][0]["columns"][0]["nullable"])
        self.assertTrue(result["objects"][0]["columns"][1]["nullable"])

    def parse(self, ddl, product="postgresql", schema="app"):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "input.sql"
            p.write_text(ddl)
            return parse_design([p], {"id": product, "fold": {"oracle": "upper", "postgresql": "lower", "mysql": "preserve"}[product]}, schema)

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
            "oracle": "CREATE OR REPLACE PROCEDURE f AS BEGIN NULL; NULL; END;\n/\n",
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

    def test_schema_filter_duplicate_and_unterminated_input(self):
        result = self.parse("CREATE TABLE other.t(id INT); CREATE TABLE app.t(id INT); CREATE TABLE app.t(x INT); SELECT 'oops")
        self.assertEqual(len(result["objects"]), 1)
        self.assertTrue(any(c["status"] == "error" for c in result["collections"]))
        self.assertTrue(result["findings"])


if __name__ == "__main__":
    unittest.main()
