#!/usr/bin/env python3
"""Contract test for tools/lib/learned_rules.py — the learning loop's store and command line.

Usage: python3 tools/lib/learned_rules.test.py     (exit 1 on failure)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import learned_rules as L  # noqa: E402
import audit_log as A  # noqa: E402

FAILURES = 0


def check(name, cond, detail=""):
    global FAILURES
    print("  [%s] %s%s" % ("ok" if cond else "FAIL", name,
                           "" if cond or not detail else " -- %r" % (detail,)))
    if not cond:
        FAILURES += 1


def cli(project, *args):
    return subprocess.run([sys.executable, os.path.join(HERE, "learned_rules.py"), project] + list(args),
                          capture_output=True, text=True)


def main():
    root = tempfile.mkdtemp(prefix="nx-lr-")
    try:
        proj = os.path.join(root, "p")
        os.makedirs(os.path.join(proj, "work"))
        with open(os.path.join(proj, "work", "pipeline-progress.json"), "w") as fh:
            json.dump({"project_name": "demo", "phases": {}}, fh)
        print("propose")
        r1, created = L.propose(proj, "Every non-2xx response is a registered problem type.",
                                "design-api,generate-api-code", "api-contract",
                                anti_pattern="ad-hoc error bodies", rationale="RFC 9457", finding="SYN-004")
        check("a new rule is LR-001, proposed, with scope, origin and one occurrence",
              created and r1["id"] == "LR-001" and r1["status"] == "proposed"
              and r1["scope"] == ["design-api", "generate-api-code"] and r1["occurrences"] == 1
              and r1["origin"][0]["finding"] == "SYN-004" and r1["origin"][0]["project"] == "demo", r1)
        r2, created = L.propose(proj, "  every non-2xx response is a registered problem type ",
                                "design-graphql", "api-contract", finding="SYN-011")
        check("the same rule again is an occurrence, not a second id; scope widens",
              not created and r2["id"] == "LR-001" and r2["occurrences"] == 2
              and r2["scope"] == ["design-api", "generate-api-code", "design-graphql"]
              and [o["finding"] for o in r2["origin"]] == ["SYN-004", "SYN-011"], r2)
        r3, _ = L.propose(proj, "Name the aggregate's OCC scope in the schema document.", "design-scalardb",
                          "data-model")
        check("the next rule is LR-002", r3["id"] == "LR-002")
        for bad in ({"category": "colour"}, {"scope": " , "}, {"rule": "   "}):
            kw = dict(rule="x", scope="design-api", category="naming")
            kw.update(bad)
            try:
                L.propose(proj, kw["rule"], kw["scope"], kw["category"])
                check("a bad %s is refused" % list(bad)[0], False)
            except ValueError:
                check("a bad %s is refused" % list(bad)[0], True)
        events = A.read_events(proj, event="RULE_PROPOSED")
        check("every proposal is a RULE_PROPOSED event naming the rule id",
              [e["ref"] for e in events] == ["LR-001", "LR-001", "LR-002"]
              and events[1]["detail"].startswith("occurrence 2"), events)

        print("decide and list")
        check("nothing is accepted yet", L.select(L.load(L.store_path(proj))) == [])
        d = L.decide(proj, "LR-001", "accepted", by="Dana Architect", reason="agreed in review")
        check("a decision sets status, who and when", d["status"] == "accepted"
              and d["decided_by"] == "Dana Architect" and d["decided_at"] and d["decision_reason"] == "agreed in review")
        L.decide(proj, "LR-002", "rejected", by="Dana Architect")
        data = L.load(L.store_path(proj))
        check("list by scope returns the accepted rules for that phase only",
              [r["id"] for r in L.select(data, scope="design-graphql")] == ["LR-001"]
              and L.select(data, scope="design-scalardb") == []
              and [r["id"] for r in L.select(data, status="rejected")] == ["LR-002"]
              and len(L.select(data, status="all")) == 2)
        check("decisions are audit events", [e["event"] for e in A.read_events(proj)][-2:]
              == ["RULE_ACCEPTED", "RULE_REJECTED"])
        r4, created = L.propose(proj, "Name the aggregate's OCC scope in the schema document.", "design-scalardb",
                                "data-model")
        check("a rejected rule proposed again is a new id, not an occurrence of the rejected one",
              created and r4["id"] == "LR-003")
        try:
            L.decide(proj, "LR-999", "accepted")
            check("an unknown id is refused", False)
        except KeyError:
            check("an unknown id is refused", True)
        view = L.render_markdown(proj)
        text = open(view, encoding="utf-8").read()
        check("the Markdown view lists every status with frontmatter",
              view.endswith("work/learned-rules.md") and text.startswith("---\ntitle: \"Learned Rules\"")
              and "## Accepted (1)" in text and "## Proposed (1)" in text and "## Rejected (1)" in text
              and "| LR-001 | api-contract |" in text, text[:300])

        print("shared store")
        shared = os.path.join(root, "shared", "rules.json")
        other = os.path.join(root, "q")
        os.makedirs(os.path.join(other, "work"))
        with open(os.path.join(other, "work", "pipeline-progress.json"), "w") as fh:
            json.dump({"project_name": "other", "phases": {}, "options": {"learned_rules_path": shared}}, fh)
        check("options.learned_rules_path points the store elsewhere", L.store_path(other) == shared)
        r5, _ = L.propose(other, "Shared lesson.", "design-api", "process")
        check("the shared store is created where named and records the project in the origin",
              os.path.isfile(shared) and r5["origin"][0]["project"] == "other"
              and not os.path.exists(os.path.join(other, "work", "learned-rules.json")))
        rel = os.path.join(root, "r")
        os.makedirs(os.path.join(rel, "work"))
        with open(os.path.join(rel, "work", "pipeline-progress.json"), "w") as fh:
            json.dump({"options": {"learned_rules_path": "../shared/rules.json"}}, fh)
        check("a relative path resolves against the project",
              os.path.normpath(L.store_path(rel)) == os.path.normpath(shared))
        with open(shared, "w") as fh:
            fh.write("{\"rules\": 3}")
        try:
            L.load(shared)
            check("a file that is not a store is refused", False)
        except ValueError:
            check("a file that is not a store is refused", True)

        print("command line")
        r = cli(proj, "propose", "rule=Idempotency keys on every command endpoint.", "scope=design-api",
                "category=api-contract", "finding=SYN-020")
        check("propose prints the id and whether it was created", r.returncode == 0
              and json.loads(r.stdout) == {"id": "LR-004", "created": True, "occurrences": 1, "status": "proposed"}, r.stderr)
        r = cli(proj, "decide", "LR-004", "accepted", "by=Dana")
        check("decide prints the decision", r.returncode == 0 and json.loads(r.stdout)["status"] == "accepted", r.stderr)
        r = cli(proj, "list", "scope=design-api")
        check("list prints the accepted rules for the scope", r.returncode == 0
              and r.stdout.count("\n") == 4 and "LR-001 [accepted]" in r.stdout and "LR-004 [accepted]" in r.stdout, r.stdout)
        r = cli(proj, "list", "status=all", "format=json")
        check("list json over every rule", r.returncode == 0 and len(json.loads(r.stdout)) == 4)
        check("render prints the view path", cli(proj, "render").stdout.strip() == "work/learned-rules.md")
        check("usage errors exit 2", cli(proj, "propose", "rule=x").returncode == 2
              and cli(proj, "decide", "LR-404", "accepted").returncode == 2
              and cli(proj, "decide", "LR-001", "maybe").returncode == 2
              and cli(proj, "list", "status=odd").returncode == 2
              and cli(proj, "list", "--scope=x").returncode == 2
              and cli(proj, "fold").returncode == 2
              and subprocess.run([sys.executable, os.path.join(HERE, "learned_rules.py")],
                                 capture_output=True).returncode == 2)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("%d failure(s)" % FAILURES)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
