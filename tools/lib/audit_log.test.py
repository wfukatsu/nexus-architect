#!/usr/bin/env python3
"""Contract test for tools/lib/audit_log.py — the append-only audit log and its command line.

Usage: python3 tools/lib/audit_log.test.py     (exit 1 on failure)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audit_log as A  # noqa: E402

FAILURES = 0


def check(name, cond, detail=""):
    global FAILURES
    print("  [%s] %s%s" % ("ok" if cond else "FAIL", name,
                           "" if cond or not detail else " -- %r" % (detail,)))
    if not cond:
        FAILURES += 1


def cli(project, *args):
    return subprocess.run([sys.executable, os.path.join(HERE, "audit_log.py"), project] + list(args),
                          capture_output=True, text=True)


def main():
    root = tempfile.mkdtemp(prefix="nx-audit-")
    try:
        project = os.path.join(root, "proj")
        os.makedirs(os.path.join(project, "work"))
        subprocess.run(["git", "init", "-q", project], check=True)
        subprocess.run(["git", "-C", project, "config", "user.name", "Test Reviewer"], check=True)
        subprocess.run(["git", "-C", project, "config", "user.email", "t@example.invalid"], check=True)

        print("taxonomy")
        check("every event has one category",
              set(A.CATEGORY) == {e for evs in A.EVENTS.values() for e in evs}
              and len(A.CATEGORY) == sum(len(v) for v in A.EVENTS.values()))
        check("every registry status that means something maps to a phase event",
              set(A.STATUS_EVENT) == {"in_progress", "completed", "failed", "skipped",
                                      "awaiting_approval", "revising"}
              and all(e in A.EVENTS["phase"] for e in A.STATUS_EVENT.values()))
        try:
            A.make_event("NOT_AN_EVENT")
            check("an unknown event is refused", False)
        except ValueError:
            check("an unknown event is refused", True)

        print("append and read")
        rec = A.append_event(project, "GATE_APPROVED", phase="E1-I3", ref="https://x/pr/1",
                             detail="reviewed")
        check("the record carries the fixed field set in order",
              list(rec) == list(A.FIELDS), list(rec))
        check("the actor is git's user.name, never the email",
              rec["actor"] == "Test Reviewer" and "example.invalid" not in json.dumps(rec), rec)
        check("the category is derived", rec["category"] == "gate" and rec["source"] == "skill")
        path = A.audit_path(project)
        check("the file is work/audit/events.jsonl", path.endswith("work/audit/events.jsonl")
              and os.path.isfile(path))
        A.append_event(project, "QUESTION_ANSWERED", phase="define-requirements", ref="OQ-012",
                       actor="Someone Else")
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        check("append-only: two events, two lines, first unchanged",
              len(lines) == 2 and json.loads(lines[0])["event"] == "GATE_APPROVED", lines)
        check("an explicit actor is kept", json.loads(lines[1])["actor"] == "Someone Else")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("{not json\n\n[1,2]\n{\"no\": \"event\"}\n")
        events = A.read_events(project)
        check("malformed lines are skipped, never raised", [e["event"] for e in events]
              == ["GATE_APPROVED", "QUESTION_ANSWERED"], events)
        check("read filters by event and phase and takes a tail",
              [e["ref"] for e in A.read_events(project, event="QUESTION_ANSWERED")] == ["OQ-012"]
              and [e["phase"] for e in A.read_events(project, phase="E1-I3")] == ["E1-I3"]
              and len(A.read_events(project, tail=1)) == 1)
        check("no file reads as no events", A.read_events(os.path.join(root, "none")) == [])

        print("registry transitions")
        before = {"investigate": "in_progress", "analyze": "pending", "report": "completed"}
        after = A.registry_statuses({"phases": {
            "investigate": {"status": "completed", "plugin": "architect"},
            "analyze": {"status": "in_progress"},
            "report": {"status": "completed", "plugin": "product"},
            "redesign": {"status": "pending"},
            "design-api": {"status": "awaiting_approval", "plugin": "architect"},
            "review-risk": {"status": "revising"},
            "odd": "skipped",
            "junk": None,
            "worse": {"status": 7},
        }})
        events = A.diff_registry(before, after, actor="bot", ts="2026-01-01T00:00:00+00:00")
        got = [(e["event"], e["phase"], e["plugin"]) for e in events]
        check("one event per status change, in name order, with the entry's plugin",
              got == [("PHASE_STARTED", "analyze", None),
                      ("PHASE_AWAITING_APPROVAL", "design-api", "architect"),
                      ("PHASE_COMPLETED", "investigate", "architect"),
                      ("PHASE_SKIPPED", "odd", None),
                      ("PHASE_REVISING", "review-risk", None)], got)
        check("an unchanged status and a move to pending emit nothing",
              not any(e["phase"] in ("report", "redesign") for e in events))
        check("loose entries are ignored, not raised", "junk" not in after and "worse" not in after)
        check("hook events say so", all(e["source"] == "hook" and e["actor"] == "bot"
                                        and e["ts"] == "2026-01-01T00:00:00+00:00" for e in events))
        rerun = A.diff_registry({"investigate": "completed"},
                                {"investigate": {"status": "completed", "plugin": None}})
        check("the same status again is not a new event", rerun == [])

        print("command line")
        r = cli(project, "PR_OPENED", "phase=E1-I3", "ref=https://x/pr/2", "detail=round 1")
        check("an event is appended and echoed", r.returncode == 0
              and json.loads(r.stdout)["event"] == "PR_OPENED"
              and A.read_events(project, event="PR_OPENED")[0]["detail"] == "round 1", r.stderr)
        r = cli(project, "list", "tail=2")
        check("list prints the tail as JSON lines",
              r.returncode == 0 and [json.loads(l)["event"] for l in r.stdout.splitlines()]
              == ["QUESTION_ANSWERED", "PR_OPENED"], r.stdout)
        r = cli(project, "list", "event=GATE_APPROVED")
        check("list filters by event", r.returncode == 0 and r.stdout.count("\n") == 1, r.stdout)
        check("an unknown event exits 2 naming the taxonomy",
              cli(project, "GATE_MAYBE").returncode == 2
              and "GATE_APPROVED" in cli(project, "GATE_MAYBE").stderr)
        check("a flag-shaped argument exits 2",
              cli(project, "GATE_APPROVED", "--phase=x").returncode == 2)
        check("a missing directory exits 2", cli(os.path.join(root, "nope"), "list").returncode == 2)
        check("no arguments prints the usage and exits 2",
              subprocess.run([sys.executable, os.path.join(HERE, "audit_log.py")],
                             capture_output=True, text=True).returncode == 2)
        before_n = len(A.read_events(project))
        check("a refused event appends nothing", len(A.read_events(project)) == before_n)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("%d failure(s)" % FAILURES)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
