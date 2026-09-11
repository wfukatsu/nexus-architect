#!/usr/bin/env python3
"""Contract test for tools/lib/ux_evaluation.py — the ten rules of @rules/ux-evaluation.md §6.

The evaluation's judgement is fenced and its arithmetic is recomputed, so both are what this suite
pins: the UXI is the formula's value and its band the UXI's; every score stays within its metric
cap and within the bound its own findings' severity sets; every finding names a defect from the
rule's vocabulary on the axis that owns it; no defect is filed twice; locations exist and agree;
runtime evidence is a capture of the finding's own screen. Each negative case is an evaluation that
reads well and is wrong in exactly one of those ways.

Run: python3 tools/lib/ux_evaluation.test.py
Exit 0 = all checks pass, 1 = at least one failed (the repo-wide convention).
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import ui_fixture  # noqa: E402
from ui_metrics import compute  # noqa: E402
from ux_evaluation import (AXES, DEFECTS, OWNS, band, routed_from_inventory, uxi,  # noqa: E402
                           validate_evaluation)

TOOL = os.path.join(HERE, "ux_evaluation.py")
PASSED = 0
FAILED = 0


def check(label, condition, detail=""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print("  [ok] %s" % label)
    else:
        FAILED += 1
        print("  [FAIL] %s%s" % (label, (" — %s" % detail) if detail else ""))


INVENTORY = ui_fixture.inventory()
TOKENS = ui_fixture.tokens()


def finding(fid, axis, defect, criterion, severity, **location):
    loc = {"screen": None, "action": None, "input": None, "component": None, "feature": None,
           "token": None, "source": None}
    loc.update(location)
    return {"id": fid, "axis": axis, "defect": defect, "criterion": criterion, "severity": severity,
            "severity_reason": None, "location": loc, "title": "t", "description": "d",
            "recommendation": "r", "evidence": "static", "evidence_ref": None,
            "runtime_outcome": None}


def well_formed():
    """Every defect the fixture's metrics measure, filed once, where they measure it."""
    scores = {"H": 3, "A": 2, "E": 4, "C": 2, "N": 3}
    findings = [
        finding("UX-001", "H", "destructive-without-confirmation", "H5", "major",
                screen="UIS-003", action="UIS-003.A2", source="web/cart.jsp:24"),
        finding("UX-002", "A", "unlabeled-input", "WCAG 1.3.1", "major",
                screen="UIS-003", input="quantity", source="web/cart.jsp:12"),
        finding("UX-003", "A", "unlabeled-input", "WCAG 1.3.1", "major",
                screen="UIS-003", input="email", source="web/cart.jsp:16"),
        finding("UX-004", "A", "missing-alt", "WCAG 1.1.1", "major",
                screen="UIS-003", source="web/cart.jsp:21"),
        finding("UX-005", "A", "missing-lang", "WCAG 3.1.1", "major",
                screen="UIS-001", source="web/login.jsp"),
        finding("UX-006", "A", "low-contrast", "WCAG 1.4.3", "major",
                screen="UIS-003", source="web/css/common.css:14"),
        finding("UX-007", "N", "dead-end", "H3", "major", screen="UIS-004",
                source="web/complete.jsp"),
        finding("UX-008", "E", "redundant-input", "WCAG 3.3.7", "minor",
                screen="UIS-003", input="email", source="web/cart.jsp:16"),
        finding("UX-009", "C", "label-drift", "H4", "minor", feature="UIF-004",
                source="web/header.jspf:4"),
        finding("UX-010", "C", "hand-built-duplicate", "H4", "minor", component="UIC-003",
                source="web/cart.jsp:30"),
        finding("UX-011", "C", "token-fragmentation", "H4", "minor", token="color.hex-0066cc",
                source="web/css/common.css:3"),
        finding("UX-012", "N", "orphan-screen", "H10", "minor", screen="UIS-005",
                source="web/help.jsp"),
    ]
    by_axis = {}
    for f in findings:
        by_axis.setdefault(f["axis"], []).append(f["id"])
    return {
        "schema_version": 1,
        "generated_at": "2026-09-11T00:00:00Z",
        "inventory": ui_fixture.INVENTORY_PATH,
        "mode": "static",
        "primary_tasks": ["Buy"],
        "metrics": compute(INVENTORY, TOKENS),
        "axes": [{"key": k, "name": k, "weight": w, "score": scores[k], "rationale": "because",
                  "finding_ids": by_axis.get(k, [])} for k, w in AXES],
        "uxi": 56.0,
        "band": "needs-improvement",
        "findings": findings,
        "withdrawn": [],
        "routed": routed_from_inventory(INVENTORY),
        "runtime": {"base_url": None, "tool": None, "captured": []},
    }


def validate(ev):
    return validate_evaluation(ev, inventory=INVENTORY, tokens=TOKENS)


def rejects(label, mutate, *, expect):
    ev = well_formed()
    mutate(ev)
    try:
        errors = validate(ev)
    except Exception as exc:  # noqa: BLE001
        check(label, False, "raised %r" % exc)
        return
    check(label, any(expect in e for e in errors), errors)


def accepts(label, mutate):
    ev = well_formed()
    mutate(ev)
    try:
        errors = validate(ev)
    except Exception as exc:  # noqa: BLE001
        check(label, False, "raised %r" % exc)
        return
    check(label, errors == [], errors)


def axis(ev, key):
    return next(a for a in ev["axes"] if a["key"] == key)


def fnd(ev, fid):
    return next(f for f in ev["findings"] if f["id"] == fid)


print("the fixture is well-formed")
check("valid against its inventory", validate(well_formed()) == [], validate(well_formed()))
check("the formula", uxi({"H": 3, "A": 2, "E": 4, "C": 2, "N": 3}) == 56.0)
check("bands are half-open", [band(v) for v in (100, 80, 79.9, 60, 59.9, 40, 39.9, 0)]
      == ["mature", "mature", "adequate", "adequate", "needs-improvement", "needs-improvement",
          "poor", "poor"])

print("the rule and the code agree")
rule = open(os.path.join(REPO, "rules", "ux-evaluation.md"), encoding="utf-8").read()
table = re.findall(r"^\| ([HAECN]) \| [^|]+\| (\d+)% \|", rule, re.M)
check("§2 states the weights the validator enforces",
      [(k, int(w) / 100.0) for k, w in table] == list(AXES), table)
check("the formula uses the same weights",
      "0.30 × H + 0.25 × A + 0.20 × E + 0.15 × C + 0.10 × N" in rule)
rows = dict(re.findall(r"^\| `([a-z-]+)` \| ([HAECN]|any) \|", rule, re.M))
check("§5 lists exactly the defects the validator knows, on the same axes",
      {k: v for k, v in rows.items() if k != "other"} == {k: v[0] for k, v in DEFECTS.items()},
      sorted(set(rows) ^ set(DEFECTS) - {"other"}))
owned = [c for criteria in OWNS.values() for c in criteria]
check("every criterion has exactly one owning axis", len(owned) == len(set(owned)))

print("rules 1 and 2 — the axes, their caps and their severity bounds")
rejects("a missing axis", lambda e: e["axes"].pop(), expect="axes must be exactly")
rejects("a changed weight", lambda e: axis(e, "H").update(weight=0.4), expect="weight must be 0.3")
rejects("a fractional score", lambda e: axis(e, "E").update(score=3.5),
        expect="integer from 1 to 5")
rejects("a score above its cap",
        lambda e: (axis(e, "C").update(score=4), e.update(uxi=59.0)),
        expect="axis C scores 4 above its metric cap 3")
rejects("a score above its severity bound",
        lambda e: (fnd(e, "UX-007").update(severity="critical", severity_reason="x"),
                   axis(e, "N").update(score=3)),
        expect="axis N scores 3 but has a critical finding — at most 2")
rejects("a major finding on an axis scored 4",
        lambda e: (axis(e, "N").update(score=4), e.update(uxi=58.0)),
        expect="axis N scores 4 but has a major finding — at most 3")

print("rules 3 and 4 — the index and its band")
rejects("a UXI that is not the formula's", lambda e: e.update(uxi=70.0),
        expect="the formula gives 56.0")
rejects("a UXI off by more than the rounding", lambda e: e.update(uxi=56.4),
        expect="the formula gives 56.0")
rejects("a band that is not the UXI's", lambda e: e.update(band="adequate"),
        expect="is 'needs-improvement'")

print("rule 5 — complete findings from the vocabulary")
rejects("a defect outside the vocabulary", lambda e: fnd(e, "UX-001").update(defect="ugly"),
        expect="not in the vocabulary")
rejects("a defect on an axis that does not own it",
        lambda e: fnd(e, "UX-002").update(axis="H", criterion="H5"),
        expect="unlabeled-input belongs to axis A, not H")
rejects("a criterion the axis does not own",
        lambda e: fnd(e, "UX-011").update(criterion="H6"), expect="is not one axis C owns")
rejects("a WCAG criterion that does not exist",
        lambda e: fnd(e, "UX-002").update(criterion="WCAG 4.9.9"), expect="is not one axis A owns")
rejects("a severity off the default without a reason",
        lambda e: fnd(e, "UX-011").update(severity="major"), expect="departs from the default")
accepts("a severity off the default with a reason",
        lambda e: (fnd(e, "UX-002").update(severity="critical", severity_reason="required input "
                                           "on the Buy task"),))
rejects("an 'other' defect without a reason",
        lambda e: fnd(e, "UX-012").update(defect="other"), expect="departs from the default")
rejects("no recommendation", lambda e: fnd(e, "UX-001").pop("recommendation"),
        expect="recommendation is required")
rejects("a malformed id", lambda e: fnd(e, "UX-001").update(id="F-1"), expect="UX-###")

print("rule 6 — locations exist and agree")
rejects("a screen that does not exist",
        lambda e: fnd(e, "UX-007")["location"].update(screen="UIS-099"),
        expect="location.screen 'UIS-099'")
rejects("an action of another screen",
        lambda e: fnd(e, "UX-001")["location"].update(action="UIS-001.A1"),
        expect="is not an action of UIS-003")
rejects("an input the screen does not have",
        lambda e: fnd(e, "UX-002")["location"].update(input="phone"),
        expect="is not an input of UIS-003")
rejects("a component the screen does not use",
        lambda e: fnd(e, "UX-007")["location"].update(component="UIC-002"),
        expect="UIC-002 is not used by UIS-004")
rejects("a feature with no action on the screen",
        lambda e: fnd(e, "UX-007")["location"].update(feature="UIF-001"),
        expect="UIF-001 has no action on UIS-004")
rejects("a token that does not exist",
        lambda e: fnd(e, "UX-011")["location"].update(token="color.hex-000000"),
        expect="location.token")
rejects("an input without its screen",
        lambda e: fnd(e, "UX-002")["location"].update(screen=None), expect="names its screen")
rejects("a malformed source",
        lambda e: fnd(e, "UX-002")["location"].update(source="web/cart.jsp:12,18"),
        expect="is not path[:line[-end]]")
rejects("a location naming nothing",
        lambda e: fnd(e, "UX-011")["location"].update(token=None), expect="names none of")

print("rule 7 — justified scores, findings listed by their own axis")
rejects("a 3 with no finding on its axis",
        lambda e: (e["findings"].pop(11), e["findings"].pop(6), axis(e, "N").update(finding_ids=[])),
        expect="axis N scores 3 with no finding")
rejects("a finding no axis lists", lambda e: axis(e, "C").update(finding_ids=[]),
        expect="UX-009: is not listed")
rejects("an axis citing another axis's finding",
        lambda e: axis(e, "E").update(finding_ids=["UX-008", "UX-002"]), expect="a finding on axis A")

print("rule 8 — measured metrics")
rejects("a metric edited by hand",
        lambda e: e["metrics"]["accessibility"].update(screens_with_violations=0),
        expect="metrics differ from what ui_metrics.py computes now (accessibility")
rejects("no metrics at all", lambda e: e.pop("metrics"), expect="metrics must be")

print("rule 9 — one defect, one finding")
rejects("the same defect on the same subject twice",
        lambda e: (e["findings"].append(dict(fnd(e, "UX-002"), id="UX-013")),
                   axis(e, "A")["finding_ids"].append("UX-013")),
        expect="one defect, one finding")
accepts("two defects on one input (the fixture's e-mail: unlabeled and redundant)", lambda e: None)
rejects("a fragmented cluster filed twice",
        lambda e: (e["findings"].append(finding("UX-013", "C", "token-fragmentation", "H4", "minor",
                                                token="color.hex-1a73e8", source="web/cart.jsp:30")),
                   axis(e, "C")["finding_ids"].append("UX-013")),
        expect="one defect, one finding")
rejects("a shared-chrome action as a subject",
        lambda e: (e["findings"].append(finding("UX-013", "H", "no-feedback", "H1", "minor",
                                                screen="UIS-003", action="UIS-003.A1",
                                                source="web/header.jspf:4")),
                   axis(e, "H")["finding_ids"].append("UX-013")),
        expect="is a shared-chrome action")
rejects("a measured defect nobody files",
        lambda e: (e["findings"].pop(4), axis(e, "A")["finding_ids"].remove("UX-005")),
        expect="the metrics measure missing-lang on UIS-001 but no finding files it")
rejects("a measured defect filed where the metrics do not show it",
        lambda e: (e["findings"].append(finding("UX-013", "H", "destructive-without-confirmation",
                                                "H5", "major", screen="UIS-003",
                                                action="UIS-003.A3", source="web/cart.jsp:30")),
                   axis(e, "H")["finding_ids"].append("UX-013")),
        expect="the metrics do not show destructive-without-confirmation there")
rejects("a redundant input the inventory does not record",
        lambda e: fnd(e, "UX-008")["location"].update(input="quantity"),
        expect="the metrics do not show redundant-input there")
rejects("a dead end on a screen with exits",
        lambda e: fnd(e, "UX-007")["location"].update(screen="UIS-003", source="web/cart.jsp"),
        expect="the metrics do not show dead-end there")
rejects("a source that is not a file of the located screen",
        lambda e: fnd(e, "UX-005")["location"].update(source="web/css/common.css:3"),
        expect="is not a file of the located element")
rejects("an unlabeled input escalated off the primary tasks",
        lambda e: (fnd(e, "UX-002").update(severity="critical", severity_reason="checkout"),
                   e.update(primary_tasks=["Log in"])),
        expect="escalates to critical only for a required input on a primary task's path")
accepts("an unlabeled required input escalated on a primary task",
        lambda e: fnd(e, "UX-002").update(severity="critical", severity_reason="Buy task"))
accepts("a navigation label variant (not a command) on consistency",
        lambda e: (e["findings"].append(finding("UX-013", "C", "navigation-label-variant", "H4",
                                                "minor", screen="UIS-005",
                                                source="web/help.jsp:3")),
                   axis(e, "C")["finding_ids"].append("UX-013")))
rejects("routed items missing from the evaluation", lambda e: e["routed"].pop(),
        expect="routed lacks 1 item(s) of the inventory")

print("rule 10 — runtime evidence and the evaluation's own fields")
rejects("a static finding with an evidence file",
        lambda e: fnd(e, "UX-002").update(evidence_ref="reports/02_evaluation/ux-evidence/x.png"),
        expect="a static finding cites no evidence file")
rejects("a runtime finding in a static evaluation",
        lambda e: fnd(e, "UX-002").update(evidence="runtime", runtime_outcome="confirmed",
                                          evidence_ref="reports/02_evaluation/ux-evidence/UIS-003.png"),
        expect="needs mode static+runtime")


def runtime(e, captured=None):
    e.update(mode="static+runtime", runtime={
        "base_url": "http://localhost:8080", "tool": "playwright-mcp",
        "captured": captured if captured is not None else [
            {"screen": "UIS-003", "url": "http://localhost:8080/cart", "role": "customer",
             "status": "captured", "screenshot": "reports/02_evaluation/ux-evidence/UIS-003.png",
             "a11y": "reports/02_evaluation/ux-evidence/UIS-003.a11y.json"}]})


accepts("a confirmed runtime finding on a captured screen",
        lambda e: (runtime(e), fnd(e, "UX-002").update(
            evidence="runtime", runtime_outcome="confirmed",
            evidence_ref="reports/02_evaluation/ux-evidence/UIS-003.a11y.json")))
rejects("a runtime finding with no outcome",
        lambda e: (runtime(e), fnd(e, "UX-002").update(
            evidence="runtime", evidence_ref="reports/02_evaluation/ux-evidence/UIS-003.png")),
        expect="runtime_outcome must be one of")
rejects("runtime evidence outside the evidence directory",
        lambda e: (runtime(e), fnd(e, "UX-002").update(evidence="runtime",
                                                       runtime_outcome="new",
                                                       evidence_ref="/etc/hosts")),
        expect="cites a file under reports/02_evaluation/ux-evidence/")
rejects("runtime evidence for a screen that was not captured",
        lambda e: (runtime(e), fnd(e, "UX-007").update(
            evidence="runtime", runtime_outcome="new",
            evidence_ref="reports/02_evaluation/ux-evidence/UIS-003.png")),
        expect="a screen that was not captured")
rejects("static+runtime without a URL",
        lambda e: (runtime(e), e["runtime"].update(base_url="yes")), expect="needs runtime.base_url")
rejects("static+runtime with nothing captured", lambda e: runtime(e, captured=[]),
        expect="with nothing captured is a static evaluation")
rejects("captures in a static evaluation",
        lambda e: (runtime(e), e.update(mode="static")), expect="has no runtime captures")
rejects("a not-captured screen without a reason",
        lambda e: runtime(e, captured=[{"screen": "UIS-004", "status": "not-captured"},
                                       {"screen": "UIS-003", "status": "captured",
                                        "screenshot": "reports/02_evaluation/ux-evidence/UIS-003.png",
                                        "a11y": "reports/02_evaluation/ux-evidence/UIS-003.a11y.json"}]),
        expect="says why it was not captured")
rejects("a withdrawn finding without its evidence",
        lambda e: e["withdrawn"].append({"title": "t", "reason": "r"}),
        expect="withdrawn[0] needs title, reason and evidence_ref")
rejects("a primary task that is not a task", lambda e: e.update(primary_tasks=["Nope"]),
        expect="primary task 'Nope'")
rejects("no timestamp", lambda e: e.pop("generated_at"), expect="generated_at")

print("hostile shapes report, never crash")
for label, mutate in (("axes as an object", lambda e: e.update(axes={"H": 3})),
                      ("a finding as a string", lambda e: e["findings"].append("UX-9")),
                      ("location as a list", lambda e: fnd(e, "UX-001").update(location=[1])),
                      ("scores as booleans", lambda e: axis(e, "H").update(score=True)),
                      ("an axis key as a list", lambda e: axis(e, "H").update(key=["H"])),
                      ("captured as a string", lambda e: e["runtime"].update(captured="all")),
                      ("not an object", None)):
    try:
        ev = "nope" if mutate is None else well_formed()
        if mutate:
            mutate(ev)
        check(label, bool(validate(ev)))
    except Exception as exc:  # noqa: BLE001
        check(label, False, "raised %r" % exc)

print("CLI against a scratch project")
tmp = tempfile.mkdtemp(prefix="ux-evaluation-test-")


def project(name, ev, files=()):
    root = os.path.join(tmp, name)
    ui_fixture.write_project(root)
    path = os.path.join(root, "reports", "02_evaluation", "ux-evaluation.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(ev, handle)
    for relative in files:
        full = os.path.join(root, relative)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        open(full, "w").close()
    return root


def run(root):
    return subprocess.run([sys.executable, TOOL, root], capture_output=True, text=True)


try:
    proc = run(project("clean", well_formed()))
    check("exit 0 on a clean evaluation",
          proc.returncode == 0 and "UXI 56.0, needs-improvement, 12 findings" in proc.stdout,
          proc.stdout)
    proc = subprocess.run([sys.executable, TOOL, os.path.join(tmp, "clean"), "--routed"],
                          capture_output=True, text=True)
    check("--routed compiles the routed items from the inventory",
          proc.returncode == 0 and json.loads(proc.stdout) == routed_from_inventory(INVENTORY)
          and len(json.loads(proc.stdout)) == 2, proc.stdout + proc.stderr)
    ev = well_formed()
    fnd(ev, "UX-002")["location"]["source"] = "web/cart.jsp:400"
    proc = run(project("bad-source", ev))
    check("a finding's source is checked against the target",
          proc.returncode == 1 and "past the end of the file" in proc.stdout, proc.stdout)
    ev = well_formed()
    runtime(ev)
    fnd(ev, "UX-002").update(evidence="runtime", runtime_outcome="confirmed",
                            evidence_ref="reports/02_evaluation/ux-evidence/UIS-003.a11y.json")
    proc = run(project("runtime-missing", ev))
    check("capture files that do not exist",
          proc.returncode == 1 and "does not exist" in proc.stdout, proc.stdout)
    proc = run(project("runtime", ev, files=("reports/02_evaluation/ux-evidence/UIS-003.png",
                                             "reports/02_evaluation/ux-evidence/UIS-003.a11y.json")))
    check("the same evaluation once the captures exist", proc.returncode == 0, proc.stdout)
    ev = well_formed()
    ev["inventory"] = "reports/before/none/ui-inventory.json"
    proc = run(project("no-inventory", ev))
    check("an inventory that cannot be read is a violation",
          proc.returncode == 1 and "is unreadable" in proc.stdout, proc.stdout)
    empty = os.path.join(tmp, "empty")
    os.makedirs(empty)
    proc = run(empty)
    check("nothing to validate is exit 0",
          proc.returncode == 0 and "nothing to validate" in proc.stdout, proc.stdout)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n%d checks, %d failed" % (PASSED + FAILED, FAILED))
sys.exit(1 if FAILED else 0)
