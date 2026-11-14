#!/usr/bin/env python3
"""Contract test for tools/lib/open_questions.py — the store read by header, grouped by role.

Usage: python3 tools/lib/open_questions.test.py     (exit 1 on failure)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import open_questions as Q  # noqa: E402

FAILURES = 0


def check(name, cond, detail=""):
    global FAILURES
    print("  [%s] %s%s" % ("ok" if cond else "FAIL", name,
                           "" if cond or not detail else " -- %r" % (detail,)))
    if not cond:
        FAILURES += 1


STORE = """# Context

## Open Questions

| ID | Question | Status | Answer | Options offered | Owner | Impact | Asked at | Role |
|----|----------|--------|--------|-----------------|-------|--------|----------|------|
| OQ-001 | Grace period? | answered | 15 min | 5 / 15 / 30 | PO | define-requirements FR-003 | 2026-01-01 | product owner |
| OQ-002 | Which region? | **deferred** | | eu / us | Ops lead | design-infrastructure | 2026-01-02 | operations |
| OQ-003 | Tenant key? | `unasked` | | per-tenant / shared | | design-scalardb AGG-002 | | architect |
| OQ-004 | Trademark clear? | external | | | Legal | | | |
| OQ-002 | Which region? | answered | eu | eu / us | Ops lead | design-infrastructure | 2026-01-02 | operations |
"""

OLD_STORE = """## Open Questions

| OQ-### | Question | Status | Answer | Options offered | Owner | Impact | Asked at |
|---|---|---|---|---|---|---|---|
| OQ-010 | Old shape? | unasked | | a / b | Someone | analyze | |
"""


def cli(project, *args):
    return subprocess.run([sys.executable, os.path.join(HERE, "open_questions.py"), project]
                          + list(args), capture_output=True, text=True)


def main():
    root = tempfile.mkdtemp(prefix="nx-oq-")
    try:
        proj = os.path.join(root, "p")
        os.makedirs(os.path.join(proj, "work"))
        with open(os.path.join(proj, "work", "context.md"), "w", encoding="utf-8") as fh:
            fh.write(STORE)
        print("reading the store")
        rows, exists = Q.read_store(proj)
        by_id = {r["id"]: r for r in rows}
        check("exists, latest row per id wins", exists and len(rows) == 4
              and by_id["OQ-002"]["status_word"] == "answered", [r["id"] for r in rows])
        check("every column is kept under its header name, Role included",
              by_id["OQ-003"]["role"] == "architect" and by_id["OQ-001"]["options offered"] == "5 / 15 / 30")
        check("status emphasis and code marks are stripped",
              by_id["OQ-003"]["status_word"] == "unasked")
        check("open = everything but answered",
              sorted(r["id"] for r in Q.select(rows)) == ["OQ-003", "OQ-004"])
        check("a named status selects it", [r["id"] for r in Q.select(rows, "external")] == ["OQ-004"])
        g = Q.group(Q.select(rows), "role")
        check("grouped by role, the roleless row under (no role)",
              list(g) == ["architect", "(no role)"] and g["(no role)"][0]["id"] == "OQ-004", list(g))
        check("grouped by phase from the Impact column",
              list(Q.group(Q.select(rows, "all"), "phase")) == ["define-requirements", "design-infrastructure",
                                                               "design-scalardb", "(no phase)"],
              list(Q.group(Q.select(rows, "all"), "phase")))
        try:
            Q.group(rows, "colour")
            check("an unknown grouping is refused", False)
        except ValueError:
            check("an unknown grouping is refused", True)
        old = os.path.join(root, "old")
        os.makedirs(os.path.join(old, "work"))
        with open(os.path.join(old, "work", "context.md"), "w", encoding="utf-8") as fh:
            fh.write(OLD_STORE)
        rows_old, _ = Q.read_store(old)
        check("a store headed OQ-### without a Role column still reads",
              rows_old and rows_old[0]["id"] == "OQ-010" and rows_old[0].get("role") is None)
        check("a missing store is (no rows, absent)", Q.read_store(os.path.join(root, "none")) == ([], False))

        print("command line")
        r = cli(proj)
        check("default: open questions by role as text", r.returncode == 0
              and r.stdout.startswith("role: architect (1)") and "OQ-004" in r.stdout, r.stdout)
        r = cli(proj, "by=owner", "status=all", "format=json")
        data = json.loads(r.stdout)
        check("json by owner over every row", r.returncode == 0 and data["by"] == "owner"
              and set(data["groups"]) == {"PO", "Ops lead", "(no owner)", "Legal"}, r.stdout)
        check("a missing store exits 1", cli(os.path.join(root, "none")).returncode == 1)
        check("a bad argument exits 2", cli(proj, "--by=role").returncode == 2
              and cli(proj, "by=colour").returncode == 2 and cli(proj, "format=xml").returncode == 2)
        check("no arguments prints usage and exits 2",
              subprocess.run([sys.executable, os.path.join(HERE, "open_questions.py")],
                             capture_output=True, text=True).returncode == 2)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("%d failure(s)" % FAILURES)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
