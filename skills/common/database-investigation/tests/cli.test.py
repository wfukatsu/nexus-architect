#!/usr/bin/env python3
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/investigate.py"


class CLITests(unittest.TestCase):
    def test_design_run_writes_valid_evidence_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "schema.sql").write_text("CREATE TABLE p(id INT PRIMARY KEY); CREATE TABLE c(p INT REFERENCES p(id));")
            args = [sys.executable, str(SCRIPT), "design", "--product", "postgresql", "--schema", "app", "--target-id", "demo", "--input", str(root / "schema.sql"), "--output-root", str(root / "reports"), "--run-id", "fixed"]
            first = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            folder = root / "reports/demo/design/fixed"
            self.assertTrue((folder / "inventory.json").exists())
            inv = json.loads((folder / "inventory.json").read_text())
            self.assertEqual(inv["status"], "complete")
            self.assertEqual(len(inv["objects"]), 2)
            self.assertIn("erDiagram", (folder / "er-diagram.md").read_text())
            before = (folder / "inventory.json").read_bytes()
            second = subprocess.run(args, capture_output=True)
            self.assertEqual(second.returncode, 1)
            self.assertEqual((folder / "inventory.json").read_bytes(), before)

    def test_unsupported_sql_returns_partial_not_success(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "input.sql"
            p.write_text("VACUUM;")
            r = subprocess.run([sys.executable, str(SCRIPT), "design", "--product", "postgresql", "--schema", "app", "--target-id", "demo", "--input", str(p), "--output-root", d], capture_output=True)
            self.assertEqual(r.returncode, 2)

    def test_profile_rejects_literal_password_without_disclosing_it(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "profile.json"
            p.write_text(json.dumps({"product": "postgresql", "password": "TOP_SECRET", "schema": "app", "expected_version": "18", "target_id": "demo"}))
            r = subprocess.run([sys.executable, str(SCRIPT), "live", "--profile", str(p), "--output-root", d], capture_output=True)
            self.assertEqual(r.returncode, 1)
            self.assertNotIn(b"TOP_SECRET", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
