#!/usr/bin/env python3
"""Contract test for tools/lib/ux_evaluation.py — the nine rules of @rules/ux-evaluation.md §6.

The evaluation's arithmetic is the part a reader trusts without re-doing, so it is the part that
must be checked: the UXI is the formula's value, the band is the UXI's band, the metrics are what
`ui_metrics.py` computes now, and no axis scores above its cap. Each negative case is an evaluation
that reads well and is wrong in exactly one of those ways, or cites something that does not exist.

Run: python3 tools/lib/ux_evaluation.test.py
Exit 0 = all checks pass, 1 = at least one failed (the repo-wide convention).
"""

import copy
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
from ux_evaluation import AXES, band, uxi, validate_evaluation  # noqa: E402

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


def finding(fid, axis, criterion, severity, **location):
    return {"id": fid, "axis": axis, "criterion": criterion, "severity": severity,
            "location": dict({"screen": None, "component": None, "feature": None, "token": None,
                              "source": None}, **location),
            "title": "t", "description": "d", "recommendation": "r", "evidence": "static",
            "evidence_ref": None}


def well_formed():
    scores = {"H": 3, "A": 2, "E": 4, "C": 2, "N": 3}
    findings = [
        finding("UX-001", "A", "WCAG 1.1.1", "major", screen="UIS-003"),
        finding("UX-002", "H", "H5", "major", screen="UIS-003"),
        finding("UX-003", "C", "H4", "minor", token="color.hex-1a73e8"),
        finding("UX-004", "N", "H3", "major", screen="UIS-004"),
    ]
    by_axis = {}
    for f in findings:
        by_axis.setdefault(f["axis"], []).append(f["id"])
    return {
        "schema_version": 1,
        "inventory": ui_fixture.INVENTORY_PATH,
        "mode": "static",
        "metrics": compute(INVENTORY, TOKENS),
        "axes": [{"key": k, "name": k, "weight": w, "score": scores[k], "rationale": "because",
                  "finding_ids": by_axis.get(k, [])} for k, w in AXES],
        "uxi": 56.0,
        "band": "needs-improvement",
        "findings": findings,
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


def axis(ev, key):
    return next(a for a in ev["axes"] if a["key"] == key)


print("the fixture is well-formed")
check("valid against its inventory", validate(well_formed()) == [], validate(well_formed()))
check("the formula", uxi({"H": 3, "A": 2, "E": 4, "C": 2, "N": 3}) == 56.0)
check("bands are half-open", [band(v) for v in (100, 80, 79.9, 60, 59.9, 40, 39.9, 0)]
      == ["mature", "mature", "adequate", "adequate", "needs-improvement", "needs-improvement",
          "poor", "poor"])

print("the rule and the code agree on the weights")
rule = open(os.path.join(REPO, "rules", "ux-evaluation.md"), encoding="utf-8").read()
table = re.findall(r"^\| ([HAECN]) \| [^|]+\| (\d+)% \|", rule, re.M)
check("rules/ux-evaluation.md §2 states the weights the validator enforces",
      [(k, int(w) / 100.0) for k, w in table] == list(AXES), table)
check("the rule's formula uses the same weights",
      "0.30 × H + 0.25 × A + 0.20 × E + 0.15 × C + 0.10 × N" in rule)

print("rules 1 and 2 — the five axes")
rejects("a missing axis", lambda e: e["axes"].pop(), expect="axes must be exactly")
rejects("an axis twice", lambda e: e["axes"].append(dict(e["axes"][0])),
        expect="axes must be exactly")
rejects("a changed weight", lambda e: axis(e, "H").update(weight=0.4), expect="weight must be 0.3")
rejects("a score of 6", lambda e: axis(e, "E").update(score=6), expect="integer from 1 to 5")
rejects("a fractional score", lambda e: axis(e, "E").update(score=3.5),
        expect="integer from 1 to 5")
rejects("no rationale", lambda e: axis(e, "E").update(rationale=""), expect="needs a rationale")

print("rules 3 and 4 — the index and its band")
rejects("a UXI that is not the formula's", lambda e: e.update(uxi=70.0),
        expect="the formula gives 56.0")
check("within tolerance", validate(dict(well_formed(), uxi=56.4)) == [])
rejects("a band that is not the UXI's", lambda e: e.update(band="adequate"),
        expect="is 'needs-improvement'")

print("rule 5 — complete findings")
rejects("a malformed id", lambda e: e["findings"][0].update(id="F-1"), expect="UX-###")
rejects("a duplicate id", lambda e: e["findings"][1].update(id="UX-001"),
        expect="duplicate finding id")
rejects("an unknown criterion", lambda e: e["findings"][0].update(criterion="H11"),
        expect="neither H1-H10")
rejects("a WCAG criterion without its number",
        lambda e: e["findings"][0].update(criterion="WCAG contrast"), expect="neither H1-H10")
rejects("an unknown severity", lambda e: e["findings"][0].update(severity="high"),
        expect="severity must be one of")
rejects("no recommendation", lambda e: e["findings"][0].pop("recommendation"),
        expect="recommendation is required")

print("rule 6 — locations exist")
rejects("a screen that does not exist",
        lambda e: e["findings"][0]["location"].update(screen="UIS-099"),
        expect="location.screen 'UIS-099'")
rejects("a token that does not exist",
        lambda e: e["findings"][2]["location"].update(token="color.hex-000000"),
        expect="location.token")
rejects("a location naming nothing",
        lambda e: e["findings"][2]["location"].update(token=None), expect="names none of")

print("rule 7 — low scores are justified")
rejects("a 3 with no finding on its axis",
        lambda e: (e["findings"].pop(3), axis(e, "N").update(finding_ids=[])),
        expect="axis N scores 3 with no finding")
rejects("an axis citing a finding of another axis",
        lambda e: axis(e, "E").update(finding_ids=["UX-001"]), expect="a finding on axis A")
rejects("an axis citing a finding that does not exist",
        lambda e: axis(e, "E").update(finding_ids=["UX-099"]), expect="is not a finding")

print("rule 8 — measured metrics and their caps")
rejects("a metric edited by hand",
        lambda e: e["metrics"]["accessibility"].update(screens_with_violations=0),
        expect="metrics differ from what ui_metrics.py computes now (accessibility")
rejects("a score above its cap", lambda e: (axis(e, "A").update(score=3), e.update(uxi=61.0,
                                                                                    band="adequate")),
        expect="axis A scores 3 above its metric cap 2")
rejects("no metrics at all", lambda e: e.pop("metrics"), expect="metrics must be")

print("rule 9 — runtime evidence is real")
rejects("a runtime finding in a static evaluation",
        lambda e: e["findings"][0].update(evidence="runtime", evidence_ref="x.png"),
        expect="needs mode static+runtime")
rejects("a runtime finding with no evidence file",
        lambda e: (e.update(mode="static+runtime", runtime={"base_url": "http://localhost:8080"}),
                   e["findings"][0].update(evidence="runtime")),
        expect="cites its evidence_ref")

print("hostile shapes report, never crash")
for label, mutate in (("axes as an object", lambda e: e.update(axes={"H": 3})),
                      ("a finding as a string", lambda e: e["findings"].append("UX-9")),
                      ("location as a list", lambda e: e["findings"][0].update(location=[1])),
                      ("scores as booleans", lambda e: axis(e, "H").update(score=True)),
                      ("not an object", None)):
    try:
        ev = "nope" if mutate is None else well_formed()
        if mutate:
            mutate(ev)
        errors = validate(ev)
        check(label, bool(errors), errors)
    except Exception as exc:  # noqa: BLE001
        check(label, False, "raised %r" % exc)

print("CLI against a scratch project")
tmp = tempfile.mkdtemp(prefix="ux-evaluation-test-")


def project(name, ev):
    root = os.path.join(tmp, name)
    ui_fixture.write_project(root)
    path = os.path.join(root, "reports", "02_evaluation", "ux-evaluation.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(ev, handle)
    return root


def run(root):
    return subprocess.run([sys.executable, TOOL, root], capture_output=True, text=True)


try:
    proc = run(project("clean", well_formed()))
    check("exit 0 on a clean evaluation",
          proc.returncode == 0 and "UXI 56.0, needs-improvement, 4 findings" in proc.stdout,
          proc.stdout)
    ev = well_formed()
    ev["uxi"] = 90.0
    proc = run(project("wrong-uxi", ev))
    check("exit 1 on a wrong UXI", proc.returncode == 1 and "violation(s)" in proc.stdout,
          proc.stdout)
    ev = well_formed()
    ev.update(mode="static+runtime", runtime={"base_url": "http://localhost:8080"})
    ev["findings"][0].update(evidence="runtime",
                             evidence_ref="reports/02_evaluation/ux-evidence/UIS-003.png")
    root = project("runtime", ev)
    proc = run(root)
    check("a runtime evidence file that does not exist",
          proc.returncode == 1 and "does not exist" in proc.stdout, proc.stdout)
    os.makedirs(os.path.join(root, "reports", "02_evaluation", "ux-evidence"))
    open(os.path.join(root, "reports", "02_evaluation", "ux-evidence", "UIS-003.png"), "w").close()
    proc = run(root)
    check("the same finding once the file exists", proc.returncode == 0, proc.stdout)
    ev = well_formed()
    ev["inventory"] = "reports/before/none/ui-inventory.json"
    proc = run(project("no-inventory", ev))
    check("an inventory that cannot be read is a violation",
          proc.returncode == 1 and "is unreadable" in proc.stdout, proc.stdout)
    empty = os.path.join(tmp, "empty")
    os.makedirs(empty)
    proc = run(empty)
    check("nothing to validate is exit 0", proc.returncode == 0 and "nothing to validate"
          in proc.stdout, proc.stdout)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n%d checks, %d failed" % (PASSED + FAILED, FAILED))
sys.exit(1 if FAILED else 0)
