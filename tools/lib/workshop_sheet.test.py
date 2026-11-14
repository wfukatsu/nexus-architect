#!/usr/bin/env python3
"""Contract test for tools/lib/workshop_sheet.py — the workshop sheet round trip.

Usage: python3 tools/lib/workshop_sheet.test.py     (exit 1 on failure)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import workshop_sheet as W  # noqa: E402
import open_questions as Q  # noqa: E402
import audit_log as A  # noqa: E402

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
| OQ-001 | Grace period? | answered | 15 min | 5 / 15 / 30 | PO | FR-003 | 2026-01-01 | product owner |
| OQ-002 | Which region? | deferred | | eu / us | Ops lead | design-infrastructure | 2026-01-02 | operations |
| OQ-003 | Tenant key? | unasked | | per-tenant / shared | | AGG-002 | | |
| OQ-004 | Retention days? | unasked | | | Legal | NFR-009 | | |

## Decisions
"""


def cli(project, *args):
    return subprocess.run([sys.executable, os.path.join(HERE, "workshop_sheet.py"), project]
                          + list(args), capture_output=True, text=True)


def main():
    root = tempfile.mkdtemp(prefix="nx-ws-")
    try:
        proj = os.path.join(root, "p")
        os.makedirs(os.path.join(proj, "work"))
        with open(os.path.join(proj, "work", "context.md"), "w", encoding="utf-8") as fh:
            fh.write(STORE)
        print("render")
        path, chosen = W.render(proj, "define-requirements", plugin="architect")
        text = open(path, encoding="utf-8").read()
        check("every unasked and deferred row goes on the sheet, answered ones do not",
              chosen == ["OQ-002", "OQ-003", "OQ-004"], chosen)
        check("the sheet sits under work/workshop/<phase>.md with frontmatter naming the questions",
              path.endswith("work/workshop/define-requirements.md")
              and "questions: [OQ-002, OQ-003, OQ-004]" in text)
        check("options become tick boxes plus Other; a question without options has none",
              "- [ ] per-tenant\n- [ ] shared\n- [ ] Other (write it under Answer)" in text
              and text.count("## OQ-004") == 1 and "## OQ-004 — Retention days?\n\n> for: Legal\n\nAnswer:" in text,
              text)
        asked = A.read_events(proj, event="QUESTION_ASKED")
        check("one QUESTION_ASKED per question, naming the sheet",
              [e["ref"] for e in asked] == ["OQ-002", "OQ-003", "OQ-004"]
              and asked[0]["detail"].endswith("work/workshop/define-requirements.md")
              and asked[0]["phase"] == "define-requirements" and asked[0]["plugin"] == "architect", asked)
        path2, chosen2 = W.render(proj, "design-scalardb", ids=["OQ-003"])
        check("explicit ids select exactly those", chosen2 == ["OQ-003"])
        try:
            W.render(proj, "x", ids=["OQ-999"])
            check("an id not in the store is refused", False)
        except KeyError:
            check("an id not in the store is refused", True)

        print("collect")
        answered = text.replace("- [ ] eu", "- [x] eu")
        answered = answered.replace("## OQ-003 — Tenant key?", "## OQ-003 — Tenant key?", 1)
        # OQ-003: free text under Answer, signed with a role; OQ-004 untouched.
        answered = answered.replace(
            "- [ ] Other (write it under Answer)\n\nAnswer:\n\nAnswered by:\n\nRole:\n\n## OQ-004",
            "- [ ] Other (write it under Answer)\n\nAnswer:\nper-tenant, with the\ntenant id as partition key\n\n"
            "Answered by: Dana Architect\n\nRole: architect\n\n## OQ-004")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(answered)
        result = W.collect(proj, "define-requirements", plugin="architect")
        check("a ticked option and a written answer are collected; the untouched one stays pending",
              [a["id"] for a in result["answered"]] == ["OQ-002", "OQ-003"]
              and result["pending"] == ["OQ-004"], result)
        by_id = {a["id"]: a for a in result["answered"]}
        check("a multi-line answer is joined; the signer and role are read",
              by_id["OQ-003"]["answer"] == "per-tenant, with the tenant id as partition key"
              and by_id["OQ-003"]["answered_by"] == "Dana Architect" and by_id["OQ-003"]["role"] == "architect"
              and by_id["OQ-002"]["answer"] == "eu", by_id)
        rows, _ = Q.read_store(proj)
        store = {r["id"]: r for r in rows}
        check("the store rows are answered in place, role filled where given, the rest untouched",
              store["OQ-002"]["status_word"] == "answered" and store["OQ-002"]["answer"] == "eu"
              and store["OQ-003"]["status_word"] == "answered" and store["OQ-003"]["role"] == "architect"
              and store["OQ-004"]["status_word"] == "unasked" and store["OQ-001"]["answer"] == "15 min",
              store)
        full = open(os.path.join(proj, "work", "context.md"), encoding="utf-8").read()
        check("the rest of the file is untouched", full.startswith("# Context\n") and full.rstrip().endswith("## Decisions"))
        events = A.read_events(proj, event="QUESTION_ANSWERED")
        check("QUESTION_ANSWERED carries the signer as actor and the answer as detail",
              [(e["ref"], e["actor"], e["detail"]) for e in events]
              == [("OQ-002", A.actor_name(proj), "eu"),
                  ("OQ-003", "Dana Architect", "per-tenant, with the tenant id as partition key")], events)
        again = W.collect(proj, "define-requirements")
        check("collecting again answers the same rows again and keeps the pending one",
              [a["id"] for a in again["answered"]] == ["OQ-002", "OQ-003"] and again["pending"] == ["OQ-004"])

        print("command line")
        r = cli(proj, "render", "evaluate-ux", "ids=OQ-004")
        check("render prints the sheet and the questions", r.returncode == 0
              and json.loads(r.stdout) == {"sheet": "work/workshop/evaluate-ux.md", "questions": ["OQ-004"]}, r.stdout)
        r = cli(proj, "collect", "evaluate-ux")
        check("collect prints answered and pending", r.returncode == 0
              and json.loads(r.stdout)["pending"] == ["OQ-004"], r.stdout)
        check("a missing sheet exits 1", cli(proj, "collect", "nope").returncode == 1)
        check("a bad verb or argument exits 2", cli(proj, "fold", "x").returncode == 2
              and cli(proj, "render", "x", "--ids=OQ-001").returncode == 2)
        check("too few arguments prints usage and exits 2", cli(proj, "render").returncode == 2)
        check("a project without a store exits 1",
              cli(os.path.join(root), "render", "x").returncode == 1)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("%d failure(s)" % FAILURES)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
