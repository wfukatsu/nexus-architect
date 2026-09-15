#!/usr/bin/env python3
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from core.live import collect


class FakePort:
    """In-memory query port with explicit errors and bounded result sets."""
    def __init__(self, results):
        self.results, self.calls, self.closed = results, [], False

    def query(self, spec, schema, limit, timeout):
        self.calls.append((spec["id"], schema, limit, timeout))
        value = self.results.get(spec["id"], [])
        if isinstance(value, Exception):
            raise value
        return value[:limit + 1]

    def close(self):
        self.closed = True


class LiveTests(unittest.TestCase):
    def adapter(self):
        return {"id": "testdb", "queries": [
            {"id": "tables", "kind": "table", "sql": "SELECT fixed"},
            {"id": "columns", "kind": "column", "sql": "SELECT fixed"},
            {"id": "rows", "kind": "statistic", "metric": "rows", "semantics": "estimate", "unit": "rows", "sql": "SELECT fixed"},
        ]}

    def test_rows_empty_and_permission_denied_are_distinct(self):
        port = FakePort({"tables": [{"schema": "app", "name": "t"}], "columns": PermissionError("secret password")})
        result = collect(self.adapter(), port, "app", lambda: "2026-09-15T00:00:00Z")
        self.assertEqual([c["status"] for c in result["collections"]], ["ok", "permission_denied", "empty"])
        self.assertNotIn("secret", str(result))
        self.assertTrue(port.closed)

    def test_truncation_and_scope_are_enforced(self):
        port = FakePort({"tables": [{"schema": "app", "name": "a"}, {"schema": "app", "name": "b"}]})
        result = collect(self.adapter(), port, "app", lambda: "now", limit=1)
        self.assertEqual(len(result["objects"]), 1)
        self.assertTrue(result["collections"][0]["truncated"])
        port = FakePort({"tables": [{"schema": "other", "name": "secret"}]})
        result = collect(self.adapter(), port, "app", lambda: "now")
        self.assertEqual(result["collections"][0]["status"], "error")
        self.assertNotIn("secret", str(result))

    def test_statistics_preserve_zero_unknown_and_time(self):
        port = FakePort({"rows": [{"schema": "app", "name": "t", "value": 0, "updated_at": None}]})
        result = collect(self.adapter(), port, "app", lambda: "now")
        self.assertEqual(result["statistics"][0]["value"], 0)
        self.assertEqual(result["statistics"][0]["semantics"], "estimate")
        self.assertIsNone(result["statistics"][0]["updated_at"])

    def test_timeout_and_unsupported_do_not_hide_failure(self):
        port = FakePort({"tables": TimeoutError(), "columns": NotImplementedError()})
        result = collect(self.adapter(), port, "app", lambda: "now")
        self.assertEqual([c["status"] for c in result["collections"]][:2], ["timeout", "unsupported"])
        self.assertTrue(port.closed)


if __name__ == "__main__":
    unittest.main()
