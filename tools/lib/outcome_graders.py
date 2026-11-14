#!/usr/bin/env python3
"""Outcome graders: what a pipeline run produced, measured over its artifacts.

The trigger evals (evals/triggers, tools/eval-plugin.sh) ask whether the right skill fired.
These ask what the run left behind, reading the project directory only — never the
transcript — so a run of this toolkit, a rerun after a skill change, and a run of another
toolkit on the same brief are scored by the same yardstick (evals/README.md § Outcome evals):

  requirement_coverage  every FR-/NFR- node of work/traceability.json reached by a later node
  open_questions        the store's rows by status; `unasked` is what the run never asked
  adrs                  records, validator errors, accepted records naming an approver
  report_validity       reports/**/*.md through the two output validators (CLI mode)
  quality_gate          reports/09_verification/quality-gate.json: verdict, stages, tests, mutation
  test_results          JUnit XML under generated/**/test-results/<suite>/: pass rate per suite
  phase_completion      work/pipeline-progress.json: phases by status
  cost                  work/token-usage.json: USD total and per phase
  duration              wall-clock from the first started_at to the last completed_at
  human_effort          the audit log: questions asked / answered / deferred, gates rejected,
                        phases revised — the review rounds a run cost its people

Each metric is {"measured": bool, ...}; an input that does not exist is "not measured",
never a crash and never a zero that reads as a result. Thresholds (expected.json) are
`{"<metric>.<field>": {"min": x} | {"max": x} | {"in": [..]}}`; a threshold over an
unmeasured metric is reported as unmeasured, and the verdict is PASS when no measured
threshold fails.

    python3 tools/lib/outcome_graders.py <project_dir> [expected=<file>] [format=text|json] [out=<file>]

Exit 0 PASS (or no thresholds), 1 FAIL, 2 usage.
"""
import glob
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
HOOKS = os.path.join(ROOT, "hooks")
sys.path.insert(0, HERE)

GRAPH = os.path.join("work", "traceability.json")
PROGRESS = os.path.join("work", "pipeline-progress.json")
LEDGER = os.path.join("work", "token-usage.json")
GATE = os.path.join("reports", "09_verification", "quality-gate.json")
REQUIREMENT_PREFIXES = ("FR-", "NFR-")


def _load_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _parse_ts(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


# ------------------------------------------------------------------------------ graders
def requirement_coverage(project):
    graph = _load_json(os.path.join(project, GRAPH))
    nodes = graph.get("nodes") if isinstance(graph, dict) else None
    if not isinstance(nodes, list):
        return {"measured": False, "reason": "no %s" % GRAPH}
    ids = {n["id"] for n in nodes if isinstance(n, dict) and isinstance(n.get("id"), str)}
    requirements = sorted(i for i in ids if i.startswith(REQUIREMENT_PREFIXES))
    referenced, dangling = set(), set()
    for n in nodes:
        if not isinstance(n, dict):
            continue
        for up in n.get("upstream") or []:
            if isinstance(up, str):
                referenced.add(up)
                if up not in ids:
                    dangling.add(up)
    if not requirements:
        return {"measured": False, "reason": "no FR-/NFR- node in the graph", "nodes": len(ids)}
    covered = [r for r in requirements if r in referenced]
    return {"measured": True, "value": round(len(covered) / len(requirements), 4),
            "requirements": len(requirements), "covered": len(covered),
            "uncovered": [r for r in requirements if r not in referenced],
            "nodes": len(ids), "dangling_upstream": sorted(dangling)}


def open_questions(project):
    import open_questions as Q
    rows, exists = Q.read_store(project)
    if not exists:
        return {"measured": False, "reason": "no work/context.md"}
    counts = {}
    for r in rows:
        counts[r["status_word"]] = counts.get(r["status_word"], 0) + 1
    return {"measured": True, "total": len(rows), "by_status": counts,
            "unasked": counts.get("unasked", 0), "answered": counts.get("answered", 0),
            "open": sum(v for k, v in counts.items() if k != "answered")}


def adrs(project):
    import adr_records as A
    records, errors = A.load_and_validate(project)
    if records is None:
        return {"measured": False, "reason": "no %s" % A.ADR_DIR}
    accepted = [r for r in records.values() if r.get("status") == "accepted"]
    approved = [r for r in accepted if r.get("approved_by")]
    return {"measured": True, "records": len(records), "errors": len(errors),
            "error_lines": errors[:10], "accepted": len(accepted),
            "accepted_with_approver": len(approved)}


def report_validity(project):
    files = sorted(glob.glob(os.path.join(project, "reports", "**", "*.md"), recursive=True))
    if not files:
        return {"measured": False, "reason": "no reports/**/*.md"}
    failures = {"frontmatter": [], "mermaid": []}
    for script, key in (("validate-frontmatter.sh", "frontmatter"), ("validate-mermaid.sh", "mermaid")):
        path = os.path.join(HOOKS, script)
        if not os.path.isfile(path):
            return {"measured": False, "reason": "no %s" % path}
        for f in files:
            r = subprocess.run(["bash", path, f], capture_output=True, text=True)
            if r.returncode != 0:
                failures[key].append(os.path.relpath(f, project))
    total = len(failures["frontmatter"]) + len(failures["mermaid"])
    return {"measured": True, "files": len(files), "failures": total,
            "frontmatter_failures": failures["frontmatter"], "mermaid_failures": failures["mermaid"]}


def quality_gate(project):
    gate = _load_json(os.path.join(project, GATE))
    if not isinstance(gate, dict):
        return {"measured": False, "reason": "no %s" % GATE}
    stages = [s for s in gate.get("stages") or [] if isinstance(s, dict)]
    by_status = {}
    for s in stages:
        by_status[s.get("status")] = by_status.get(s.get("status"), 0) + 1
    unit = next((s for s in stages if s.get("stage") == "unit"), {})
    tests = unit.get("tests") if isinstance(unit.get("tests"), dict) else {}
    mutation = unit.get("mutation") if isinstance(unit.get("mutation"), dict) else {}
    return {"measured": True, "verdict": gate.get("verdict"), "stages": len(stages),
            "by_status": by_status, "passed": by_status.get("passed", 0),
            "failed": by_status.get("failed", 0), "skipped": by_status.get("skipped", 0),
            "unit_tests_run": tests.get("run"), "unit_tests_passed": tests.get("passed"),
            "mutation_score": mutation.get("score"), "blocking": gate.get("blocking") or []}


def test_results(project):
    files = sorted(glob.glob(os.path.join(project, "generated", "**", "test-results", "*", "*.xml"),
                             recursive=True))
    if not files:
        return {"measured": False, "reason": "no generated/**/test-results/<suite>/*.xml"}
    suites = {}
    for f in files:
        suite = os.path.basename(os.path.dirname(f))
        try:
            root = ET.parse(f).getroot()
        except ET.ParseError:
            continue
        cases = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
        acc = suites.setdefault(suite, {"tests": 0, "failures": 0, "errors": 0, "skipped": 0})
        for ts in cases:
            for key in acc:
                try:
                    acc[key] += int(ts.get(key) or 0)
                except ValueError:
                    pass
    for acc in suites.values():
        ran = acc["tests"] - acc["skipped"]
        acc["pass_rate"] = round((ran - acc["failures"] - acc["errors"]) / ran, 4) if ran else None
    total = sum(a["tests"] for a in suites.values())
    bad = sum(a["failures"] + a["errors"] for a in suites.values())
    skipped = sum(a["skipped"] for a in suites.values())
    ran = total - skipped
    return {"measured": bool(suites), "suites": suites, "tests": total,
            "pass_rate": round((ran - bad) / ran, 4) if ran else None}


def phase_completion(project):
    progress = _load_json(os.path.join(project, PROGRESS))
    phases = progress.get("phases") if isinstance(progress, dict) else None
    if not isinstance(phases, dict):
        return {"measured": False, "reason": "no %s" % PROGRESS}
    counts = {}
    for entry in phases.values():
        status = entry.get("status") if isinstance(entry, dict) else entry
        status = status if isinstance(status, str) else "unknown"
        counts[status] = counts.get(status, 0) + 1
    return {"measured": True, "phases": len(phases), "by_status": counts,
            "completed": counts.get("completed", 0), "failed": counts.get("failed", 0),
            "skipped": counts.get("skipped", 0),
            "profile": (progress.get("options") or {}).get("profile") if isinstance(progress.get("options"), dict) else None,
            "warnings": len(progress.get("warnings") or []) if isinstance(progress.get("warnings"), list) else 0}


def cost(project):
    ledger = _load_json(os.path.join(project, LEDGER))
    if not isinstance(ledger, dict):
        return {"measured": False, "reason": "no %s" % LEDGER}
    per_phase = {name: p.get("cost_usd") for name, p in (ledger.get("phases") or {}).items()
                 if isinstance(p, dict)}
    return {"measured": True, "total_usd": ledger.get("total_cost_usd"),
            "unassigned_usd": per_phase.get("_unassigned"), "per_phase_usd": per_phase}


def duration(project):
    progress = _load_json(os.path.join(project, PROGRESS))
    phases = progress.get("phases") if isinstance(progress, dict) else None
    if not isinstance(phases, dict):
        return {"measured": False, "reason": "no %s" % PROGRESS}
    starts, ends, per_phase = [], [], {}
    for name, entry in phases.items():
        if not isinstance(entry, dict):
            continue
        s, e = _parse_ts(entry.get("started_at")), _parse_ts(entry.get("completed_at"))
        if s:
            starts.append(s)
        if e:
            ends.append(e)
        if s and e and e >= s:
            per_phase[name] = round(e - s)
    if not starts or not ends:
        return {"measured": False, "reason": "no started_at / completed_at stamps"}
    return {"measured": True, "wall_clock_s": round(max(ends) - min(starts)),
            "phase_time_s": sum(per_phase.values()), "per_phase_s": per_phase}


def human_effort(project):
    import audit_log as A
    events = A.read_events(project)
    if not events:
        return {"measured": False, "reason": "no audit events"}
    count = {}
    for e in events:
        count[e["event"]] = count.get(e["event"], 0) + 1
    return {"measured": True, "events": len(events),
            "questions_asked": count.get("QUESTION_ASKED", 0),
            "questions_answered": count.get("QUESTION_ANSWERED", 0),
            "questions_deferred": count.get("QUESTION_DEFERRED", 0),
            "gates_approved": count.get("GATE_APPROVED", 0),
            "gates_rejected": count.get("GATE_REJECTED", 0),
            "revisions": count.get("PHASE_REVISING", 0),
            "review_rounds": count.get("GATE_REJECTED", 0) + count.get("PHASE_REVISING", 0),
            "by_event": count}


GRADERS = [requirement_coverage, open_questions, adrs, report_validity, quality_gate, test_results,
           phase_completion, cost, duration, human_effort]


def scorecard(project):
    metrics = {}
    for grader in GRADERS:
        try:
            metrics[grader.__name__] = grader(project)
        except Exception as exc:  # a grader must never take the scorecard down
            metrics[grader.__name__] = {"measured": False, "reason": "grader error: %s" % exc}
    return {"project": os.path.abspath(project),
            "graded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "metrics": metrics}


# --------------------------------------------------------------------------- thresholds
def _lookup(metrics, dotted):
    metric, _, field = dotted.partition(".")
    m = metrics.get(metric)
    if not isinstance(m, dict) or not m.get("measured"):
        return None, False
    value = m
    for part in field.split(".") if field else []:
        value = value.get(part) if isinstance(value, dict) else None
    return value, True


def evaluate(card, expected):
    """Apply expected.json; returns {"verdict", "checks": [...], "unmeasured": [...]}."""
    checks, unmeasured, failed = [], [], 0
    for dotted, rule in (expected or {}).items():
        value, measured = _lookup(card["metrics"], dotted)
        if not measured or value is None:
            unmeasured.append(dotted)
            checks.append({"metric": dotted, "rule": rule, "value": value, "status": "unmeasured"})
            continue
        ok = True
        if "min" in rule and not (value >= rule["min"]):
            ok = False
        if "max" in rule and not (value <= rule["max"]):
            ok = False
        if "in" in rule and value not in rule["in"]:
            ok = False
        if "equals" in rule and value != rule["equals"]:
            ok = False
        failed += 0 if ok else 1
        checks.append({"metric": dotted, "rule": rule, "value": value, "status": "pass" if ok else "fail"})
    return {"verdict": "FAIL" if failed else "PASS", "failed": failed, "checks": checks,
            "unmeasured": unmeasured}


def render_text(card, result=None):
    m = card["metrics"]
    lines = ["outcome scorecard: %s" % card["project"]]
    def row(label, value):
        lines.append("  %-22s %s" % (label, value))
    def show(name, fmt):
        x = m.get(name, {})
        row(name, fmt(x) if x.get("measured") else "not measured (%s)" % x.get("reason"))
    show("requirement_coverage", lambda x: "%.0f%% (%d/%d, uncovered %s)" % (
        x["value"] * 100, x["covered"], x["requirements"], x["uncovered"] or "none"))
    show("open_questions", lambda x: "%d rows, %d open, %d unasked" % (x["total"], x["open"], x["unasked"]))
    show("adrs", lambda x: "%d records, %d errors, %d/%d accepted with approver" % (
        x["records"], x["errors"], x["accepted_with_approver"], x["accepted"]))
    show("report_validity", lambda x: "%d files, %d failures" % (x["files"], x["failures"]))
    show("quality_gate", lambda x: "%s (%d passed / %d failed / %d skipped; mutation %s)" % (
        x["verdict"], x["passed"], x["failed"], x["skipped"], x["mutation_score"]))
    show("test_results", lambda x: "%d tests, pass rate %s" % (x["tests"], x["pass_rate"]))
    show("phase_completion", lambda x: "%d phases: %s%s" % (
        x["phases"], ", ".join("%s %d" % kv for kv in sorted(x["by_status"].items())),
        (" (profile %s)" % x["profile"]) if x.get("profile") else ""))
    show("cost", lambda x: "USD %s" % x["total_usd"])
    show("duration", lambda x: "%ss wall clock, %ss in phases" % (x["wall_clock_s"], x["phase_time_s"]))
    show("human_effort", lambda x: "%d asked / %d answered / %d deferred, %d review rounds" % (
        x["questions_asked"], x["questions_answered"], x["questions_deferred"], x["review_rounds"]))
    if result is not None:
        lines.append("thresholds: %s (%d failed, %d unmeasured)" % (
            result["verdict"], result["failed"], len(result["unmeasured"])))
        for c in result["checks"]:
            lines.append("  [%s] %s = %r vs %s" % (c["status"], c["metric"], c["value"], json.dumps(c["rule"])))
    return "\n".join(lines)


def main(argv):
    if not argv:
        sys.stderr.write(__doc__)
        return 2
    project = argv[0]
    opts = {"expected": None, "format": "text", "out": None}
    for arg in argv[1:]:
        key, sep, value = arg.partition("=")
        if not sep or key not in opts:
            sys.stderr.write("outcome_graders: expected expected=, format= or out=, got %r\n" % arg)
            return 2
        opts[key] = value
    if not os.path.isdir(project):
        sys.stderr.write("outcome_graders: not a directory: %s\n" % project)
        return 2
    if opts["format"] not in ("text", "json"):
        sys.stderr.write("outcome_graders: format must be text or json\n")
        return 2
    expected = None
    if opts["expected"]:
        expected = _load_json(opts["expected"])
        if not isinstance(expected, dict):
            sys.stderr.write("outcome_graders: cannot read thresholds from %s\n" % opts["expected"])
            return 2
    card = scorecard(project)
    result = evaluate(card, expected) if expected is not None else None
    if result is not None:
        card["thresholds"] = result
    if opts["out"]:
        with open(opts["out"], "w", encoding="utf-8") as fh:
            json.dump(card, fh, ensure_ascii=False, indent=2)
    if opts["format"] == "json":
        sys.stdout.write(json.dumps(card, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(render_text(card, result) + "\n")
    return 1 if result is not None and result["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
