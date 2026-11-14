#!/usr/bin/env python3
"""Contract test for tools/lib/outcome_graders.py — the outcome scorecard over a scratch project.

Usage: python3 tools/lib/outcome_graders.test.py     (exit 1 on failure)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import outcome_graders as G  # noqa: E402

FAILURES = 0


def check(name, cond, detail=""):
    global FAILURES
    print("  [%s] %s%s" % ("ok" if cond else "FAIL", name,
                           "" if cond or not detail else " -- %r" % (detail,)))
    if not cond:
        FAILURES += 1


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


ADR = """---
id: ADR-001
title: "A decision"
status: accepted
skill: redesign
decided_at: "2026-08-29"
upstream: [FR-001]
supersedes: []
deciders: [architect]
approved_by: ["Dana"]
schema_version: 2
---

## Context

x

## Decision

y

## Alternatives considered

z

## Consequences

w
"""
INDEX = "---\ntitle: \"ADR Index\"\nschema_version: 1\nskill: redesign\n---\n\n# ADR Index\n\n| ID |\n|----|\n| ADR-001 |\n"
GOOD_REPORT = "---\ntitle: \"T\"\nschema_version: 1\nskill: report\n---\n\n# T\n\n```mermaid\nflowchart LR\n  a --> b\n```\n"
BAD_REPORT = "no frontmatter\n\n```mermaid\nnot-a-diagram\n```\n"
JUNIT = """<?xml version="1.0"?>
<testsuite name="OrderTest" tests="%d" skipped="%d" failures="%d" errors="%d"></testsuite>
"""


def build(root):
    write(os.path.join(root, "work", "traceability.json"), json.dumps({"schema_version": 1, "nodes": [
        {"id": "FR-001", "type": "requirement", "upstream": []},
        {"id": "FR-002", "type": "requirement", "upstream": []},
        {"id": "NFR-001", "type": "nfr", "upstream": []},
        {"id": "CTX-001", "type": "context", "upstream": ["FR-001", "NFR-001", "FEAT-099"]},
        {"id": "ADR-001", "type": "decision", "upstream": ["FR-001"]},
    ]}))
    write(os.path.join(root, "work", "context.md"),
          "## Open Questions\n\n| ID | Question | Status | Answer | Options offered | Owner | Impact | Asked at | Role |\n"
          "|---|---|---|---|---|---|---|---|---|\n"
          "| OQ-001 | a? | answered | x | | | | | |\n| OQ-002 | b? | unasked | | | | | | |\n"
          "| OQ-003 | c? | deferred | | | | | | |\n")
    write(os.path.join(root, "reports", "03_design", "adr", "adr-001-a.md"), ADR)
    write(os.path.join(root, "reports", "03_design", "adr", "index.md"), INDEX)
    write(os.path.join(root, "reports", "01_analysis", "good.md"), GOOD_REPORT)
    write(os.path.join(root, "reports", "01_analysis", "bad.md"), BAD_REPORT)
    write(os.path.join(root, "reports", "09_verification", "quality-gate.json"), json.dumps({
        "schema_version": 1, "verdict": "CONDITIONAL_PASS", "stages": [
            {"stage": "build", "status": "passed"},
            {"stage": "unit", "status": "passed", "tests": {"run": 10, "passed": 10},
             "mutation": {"score": 81}},
            {"stage": "contract", "status": "failed"},
            {"stage": "sast", "status": "skipped", "reason": "not-configured"}],
        "blocking": ["VER-004"]}))
    write(os.path.join(root, "generated", "svc", "build", "test-results", "test", "a.xml"), JUNIT % (10, 1, 1, 0))
    write(os.path.join(root, "generated", "svc", "build", "test-results", "contractTest", "b.xml"), JUNIT % (4, 0, 0, 0))
    write(os.path.join(root, "generated", "svc", "build", "test-results", "contractTest", "junk.xml"), "<not xml")
    write(os.path.join(root, "work", "pipeline-progress.json"), json.dumps({
        "options": {"profile": "poc"},
        "phases": {"investigate": {"status": "completed", "started_at": "2026-01-01T00:00:00Z",
                                   "completed_at": "2026-01-01T00:10:00Z"},
                   "analyze": {"status": "completed", "started_at": "2026-01-01T00:10:00Z",
                               "completed_at": "2026-01-01T00:25:00Z"},
                   "report": {"status": "failed", "started_at": "2026-01-01T00:25:00Z"},
                   "odd": "skipped"},
        "warnings": ["w1"]}))
    write(os.path.join(root, "work", "token-usage.json"), json.dumps({
        "total_cost_usd": 12.5, "phases": {"investigate": {"cost_usd": 4.0}, "analyze": {"cost_usd": 8.0},
                                          "_unassigned": {"cost_usd": 0.5}}}))
    write(os.path.join(root, "work", "audit", "events.jsonl"), "\n".join(json.dumps(e) for e in [
        {"event": "QUESTION_ASKED"}, {"event": "QUESTION_ASKED"}, {"event": "QUESTION_ANSWERED"},
        {"event": "QUESTION_DEFERRED"}, {"event": "GATE_REJECTED"}, {"event": "PHASE_REVISING"},
        {"event": "PHASE_REVISING"}, {"event": "GATE_APPROVED"}]) + "\n")


def main():
    root = tempfile.mkdtemp(prefix="nx-outcome-")
    try:
        proj = os.path.join(root, "p")
        build(proj)
        card = G.scorecard(proj)
        m = card["metrics"]
        print("graders")
        check("requirement coverage: 2 of 3 requirements reached, the uncovered named, the dangling id named",
              m["requirement_coverage"]["value"] == round(2 / 3, 4)
              and m["requirement_coverage"]["uncovered"] == ["FR-002"]
              and m["requirement_coverage"]["dangling_upstream"] == ["FEAT-099"], m["requirement_coverage"])
        check("open questions by status", m["open_questions"]["unasked"] == 1
              and m["open_questions"]["open"] == 2 and m["open_questions"]["total"] == 3, m["open_questions"])
        check("adrs: one valid record, accepted with approver", m["adrs"]["records"] == 1
              and m["adrs"]["errors"] == 0 and m["adrs"]["accepted_with_approver"] == 1, m["adrs"])
        rv = m["report_validity"]
        check("report validity: the bad report fails both validators, the good one neither, the ADRs pass",
              rv["measured"] and rv["files"] == 4 and rv["frontmatter_failures"] == ["reports/01_analysis/bad.md"]
              and rv["mermaid_failures"] == ["reports/01_analysis/bad.md"] and rv["failures"] == 2, rv)
        qg = m["quality_gate"]
        check("quality gate: verdict, stage counts, unit tests and mutation score",
              qg["verdict"] == "CONDITIONAL_PASS" and qg["passed"] == 2 and qg["failed"] == 1
              and qg["skipped"] == 1 and qg["unit_tests_run"] == 10 and qg["mutation_score"] == 81
              and qg["blocking"] == ["VER-004"], qg)
        tr = m["test_results"]
        check("test results: per suite from JUnit XML, the unparseable file skipped",
              tr["suites"]["test"]["pass_rate"] == round(8 / 9, 4) and tr["suites"]["contractTest"]["pass_rate"] == 1.0
              and tr["tests"] == 14 and tr["pass_rate"] == round(12 / 13, 4), tr)
        pc = m["phase_completion"]
        check("phase completion: counts by status, a bare-string entry counted, the profile and warnings read",
              pc["completed"] == 2 and pc["failed"] == 1 and pc["skipped"] == 1 and pc["profile"] == "poc"
              and pc["warnings"] == 1, pc)
        check("cost: total and per phase", m["cost"]["total_usd"] == 12.5
              and m["cost"]["per_phase_usd"]["analyze"] == 8.0 and m["cost"]["unassigned_usd"] == 0.5)
        du = m["duration"]
        check("duration: wall clock from first start to last end, phase time summed over stamped phases",
              du["wall_clock_s"] == 1500 and du["phase_time_s"] == 1500 and "report" not in du["per_phase_s"], du)
        he = m["human_effort"]
        check("human effort: questions, gates and revisions counted into review rounds",
              he["questions_asked"] == 2 and he["questions_answered"] == 1 and he["questions_deferred"] == 1
              and he["gates_rejected"] == 1 and he["revisions"] == 2 and he["review_rounds"] == 3, he)

        print("thresholds")
        expected = {"requirement_coverage.value": {"min": 0.9}, "open_questions.unasked": {"max": 0},
                    "adrs.errors": {"max": 0}, "quality_gate.verdict": {"in": ["PASS", "CONDITIONAL_PASS"]},
                    "test_results.suites.contractTest.pass_rate": {"min": 1.0},
                    "nonexistent.value": {"min": 1}, "cost.total_usd": {"max": 20}}
        result = G.evaluate(card, expected)
        status = {c["metric"]: c["status"] for c in result["checks"]}
        check("min, max, in and nested fields are applied; the unmeasured metric is listed, not failed",
              result["verdict"] == "FAIL" and result["failed"] == 2
              and status["requirement_coverage.value"] == "fail" and status["open_questions.unasked"] == "fail"
              and status["adrs.errors"] == "pass" and status["quality_gate.verdict"] == "pass"
              and status["test_results.suites.contractTest.pass_rate"] == "pass"
              and status["cost.total_usd"] == "pass" and result["unmeasured"] == ["nonexistent.value"], result)
        check("no failing measured threshold is PASS even with unmeasured ones",
              G.evaluate(card, {"nonexistent.value": {"min": 1}, "adrs.errors": {"max": 0}})["verdict"] == "PASS")
        text = G.render_text(card, result)
        check("the text scorecard names every metric and the verdict",
              all(n in text for n in ("requirement_coverage", "human_effort", "thresholds: FAIL")), text)

        print("empty project and command line")
        empty = os.path.join(root, "empty")
        os.makedirs(empty)
        card_e = G.scorecard(empty)
        check("nothing measured on an empty project, and nothing crashed",
              all(not v["measured"] and v.get("reason") for v in card_e["metrics"].values()))
        exp_path = os.path.join(root, "expected.json")
        write(exp_path, json.dumps(expected))
        out_path = os.path.join(root, "card.json")
        r = subprocess.run([sys.executable, os.path.join(HERE, "outcome_graders.py"), proj,
                            "expected=" + exp_path, "format=json", "out=" + out_path],
                           capture_output=True, text=True)
        card_cli = json.loads(r.stdout)
        check("cli: json with thresholds, written to out=, exit 1 on FAIL",
              r.returncode == 1 and card_cli["thresholds"]["verdict"] == "FAIL" and os.path.isfile(out_path), r.stderr)
        r = subprocess.run([sys.executable, os.path.join(HERE, "outcome_graders.py"), proj],
                           capture_output=True, text=True)
        check("cli: no thresholds is exit 0 with the text card", r.returncode == 0 and "outcome scorecard" in r.stdout)
        check("cli: usage errors exit 2",
              subprocess.run([sys.executable, os.path.join(HERE, "outcome_graders.py"), proj, "--json"],
                             capture_output=True).returncode == 2
              and subprocess.run([sys.executable, os.path.join(HERE, "outcome_graders.py")],
                                 capture_output=True).returncode == 2
              and subprocess.run([sys.executable, os.path.join(HERE, "outcome_graders.py"), proj,
                                  "expected=" + os.path.join(root, "nope.json")], capture_output=True).returncode == 2)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("%d failure(s)" % FAILURES)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
