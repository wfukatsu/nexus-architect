#!/usr/bin/env python3
"""Contract and safety invariants, including a fourth adapter with no core edits."""
import copy
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from core.registry import load_adapter
from core.connection import connection_config, Port, verify_probe
from core.design import parse_design
from core.output import validate


class ContractTests(unittest.TestCase):
    def test_each_adapter_bounds_server_results_with_bound_parameters(self):
        for product in ("oracle","postgresql","mysql"):
            _,module=load_adapter(product)
            self.assertTrue(callable(getattr(module,"bound_query",None)))
            sql,params=module.bound_query("SELECT x WHERE owner="+(":scope" if product=="oracle" else "%s"),"a' OR 1=1",3)
            self.assertNotIn("a' OR 1=1",sql)
            self.assertIn(4,params.values() if isinstance(params,dict) else params)

    def test_probe_accepts_packaging_suffix_but_rejects_wrong_release(self):
        class Probe:
            def query(self, *args):
                return [{"product":"PostgreSQL", "version":"18.6 (Debian build)", "catalog":"app"}]
        spec={"id":"postgresql","probe":"SELECT version", "min_major":14}
        self.assertEqual(verify_probe(spec,Probe(),"18.6","app")["version"], "18.6 (Debian build)")
        with self.assertRaises(ValueError):
            verify_probe(spec,Probe(),"18.5","app")

    def test_probe_rejects_compatible_products_declared_by_the_adapter(self):
        spec = load_adapter("postgresql")[0]
        for row in ({"product": "PostgreSQL 15.4 on aarch64", "version": "15.4", "catalog": "app", "compatible_product": "aurora_version"},
                    {"product": "PostgreSQL 15.2-YB-2.25.0.0-b0 on x86_64", "version": "15.2-YB-2.25.0.0-b0", "catalog": "app", "compatible_product": None}):
            class Probe:
                def query(self, *args, row=row):
                    return [row]
            with self.subTest(row=row["product"]), self.assertRaises(ValueError):
                verify_probe(spec, Probe(), "15", "app")

    def test_probe_major_version_comes_from_the_numeric_release(self):
        class Probe:
            def query(self, *args):
                return [{"product": "PostgreSQL", "version": "17beta1", "catalog": "app", "compatible_product": None}]
        self.assertEqual(verify_probe({"id": "postgresql", "probe": "SELECT", "min_major": 14}, Probe(), "17", "app")["version"], "17beta1")

    def test_catalog_queries_exclude_duplicates_of_declared_structure(self):
        oracle = next(q for q in load_adapter("oracle")[0]["queries"] if q["id"] == "constraints")["sql"]
        self.assertIn("IS NOT NULL", oracle, "Oracle NOT NULL constraints must not be reported as CHECK constraints")
        pg = {q["id"]: q["sql"] for q in load_adapter("postgresql")[0]["queries"]}
        for query in ("tables", "columns", "constraints", "indexes", "triggers"):
            self.assertIn("relispartition", pg[query], query + " must not list partition children as tables")
        for query in ("rows", "bytes", "index_scans"):
            self.assertIn("AS granularity", pg[query], query + " must label partition-level statistics")

    def test_fourth_adapter_loads_without_modifying_core(self):
        import adapters
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "adapters/fourth").mkdir(parents=True)
            (root / "adapters/registry.json").write_text('{"fourth":"fourth"}')
            (root / "adapters/fourth/adapter.json").write_text('{"id":"fourth","fold":"preserve","queries":[]}')
            (root / "fourth.py").write_text('def connect(config):\n    return "fourth port"\n')
            adapters.__path__.append(d)
            try:
                spec, module = load_adapter("fourth", root)
                self.assertEqual(module.connect({}), "fourth port")
                p = root / "input.sql"
                p.write_text("CREATE TABLE t(id INT);")
                self.assertEqual(parse_design([p], spec, "app")["objects"][0]["name"], "t")
            finally:
                adapters.__path__.remove(d)
                sys.modules.pop("adapters.fourth", None)

    def test_profile_cannot_inject_module_or_remote_plaintext(self):
        for profile in ({"module":"os"}, {"password":"secret"}):
            with self.assertRaises(ValueError):
                connection_config(profile)
        from unittest.mock import patch
        with patch.dict(os.environ, {"INV_HOST":"remote.example", "INV_PORT":"5432", "INV_USER":"reader"}):
            with self.assertRaises(ValueError):
                connection_config({"host_env":"INV_HOST","port_env":"INV_PORT","user_env":"INV_USER","allow_local_plaintext":True})

    def test_registry_has_scoped_single_selects_and_no_sensitive_values(self):
        for product in ("oracle","postgresql","mysql"):
            spec, _ = load_adapter(product)
            self.assertGreaterEqual(len(spec["queries"]), 8)
            for q in spec["queries"]:
                self.assertTrue(q["sql"].startswith("SELECT "))
                self.assertNotIn(";", q["sql"])
                self.assertTrue(":scope" in q["sql"] or "%s" in q["sql"])
                for denied in ("most_common_vals", "histogram_bounds", "query_text", "DBA_HIST", "v$active_session_history"):
                    self.assertNotIn(denied.lower(), q["sql"].lower())

    def test_expression_index_is_not_misreported_as_plain_column(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "input.sql"
            p.write_text('CREATE TABLE t(name TEXT); CREATE INDEX idx ON t(lower(name));')
            result = parse_design([p], {"id":"postgresql","fold":"lower"}, "app")
            self.assertTrue(any(c["status"] == "unsupported" for c in result["collections"]))
            self.assertFalse(any(o.get("extensions",{}).get("columns") == ["lower"] for o in result["objects"]))

    def test_quoted_keyword_is_a_column_not_constraint(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"input.sql"
            p.write_text('CREATE TABLE t("PRIMARY" INT, "a.b" VARCHAR(2));')
            result=parse_design([p], {"id":"postgresql","fold":"lower"}, "app")
            self.assertEqual([c["name"] for c in result["objects"][0]["columns"]], ["PRIMARY","a.b"])

    def test_nested_evidence_is_checked(self):
        inv=dict(schema_version=1,run_id="r",mode="design",product="p",target_id="t",schema="app",status="complete",objects=[dict(id="x",schema="app",columns=[dict(evidence_ids=["missing"])],constraints=[],evidence_ids=["E1"])],statistics=[],collections=[],evidence=[dict(id="E1")],findings=[])
        with self.assertRaises(ValueError):
            validate(inv)


if __name__ == "__main__":
    unittest.main()
