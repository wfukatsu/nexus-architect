#!/usr/bin/env python3
"""Contract test for tools/lib/ui_metrics.py — the numbers `/architect:evaluate-ux` may cite.

The metrics are the half of a UX evaluation that must not be judgement: contrast ratios, the
navigation graph (@rules/ui-analysis.md §6), input burden, token fragmentation, and the per-axis
caps of @rules/ux-evaluation.md §2. Each check pins one of them against the shared fixture, whose
defects are planted so that every metric has something to find.

Run: python3 tools/lib/ui_metrics.test.py
Exit 0 = all checks pass, 1 = at least one failed (the repo-wide convention).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ui_fixture  # noqa: E402
from ui_metrics import axis_caps, compute, contrast_ratio  # noqa: E402

TOOL = os.path.join(HERE, "ui_metrics.py")
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


def screen(inv, sid):
    return next(s for s in inv["screens"] if s["id"] == sid)


print("contrast follows WCAG 2.x")
check("black on white is 21:1", contrast_ratio("#000000", "#ffffff") == 21.0)
check("order does not matter", contrast_ratio("#ffffff", "#000") == 21.0)
check("#aaaaaa on white is 2.32:1", contrast_ratio("#aaaaaa", "#ffffff") == 2.32,
      contrast_ratio("#aaaaaa", "#ffffff"))
check("#767676 on white passes 4.5:1", contrast_ratio("#767676", "#ffffff") >= 4.5,
      contrast_ratio("#767676", "#ffffff"))

m = compute(ui_fixture.inventory(), ui_fixture.tokens())
cart = m["per_screen"]["UIS-003"]

print("per screen")
check("hidden inputs are not counted", cart["inputs"] == 2, cart["inputs"])
check("placeholder-only and unassociated labels are unlabeled",
      cart["unlabeled_inputs"] == ["email", "quantity"], cart["unlabeled_inputs"])
check("an image with alt null is counted", cart["images_without_alt"] == 1)
decorative = ui_fixture.inventory()
screen(decorative, "UIS-003")["images"][0]["decorative"] = True
check("a decorative image without alt is not",
      compute(decorative, ui_fixture.tokens())["per_screen"]["UIS-003"]["images_without_alt"] == 0)
check("the low-contrast pair is found with its ratio",
      cart["low_contrast_pairs"] == [{"fg": "#aaaaaa", "bg": "#ffffff", "ratio": 2.32,
                                      "text": "normal"}], cart["low_contrast_pairs"])
check("large text uses the 3:1 minimum", compute(
    (lambda i: (screen(i, "UIS-003")["color_pairs"][0].update(fg="#949494", text="large"), i)[1])(
        ui_fixture.inventory()), ui_fixture.tokens())["per_screen"]["UIS-003"][
    "low_contrast_pairs"] == [])
check("an unconfirmed destructive action is listed",
      cart["destructive_without_confirmation"] == ["UIS-003.A2"])
check("a rule enforced on both sides is not client-only, a client-only one is",
      cart["client_only_validations"] == ["email"], cart["client_only_validations"])
check("a redundant input is listed", cart["redundant_inputs"] == ["email"])
check("a missing lang is flagged", m["per_screen"]["UIS-001"]["lang_missing"] is True)

print("navigation — @rules/ui-analysis.md §6")
nav = m["navigation"]
check("entry screens", nav["entry"] == ["UIS-001"], nav["entry"])
check("depth is the shortest path from an entry",
      [m["per_screen"][s]["depth"] for s in ("UIS-001", "UIS-002", "UIS-003", "UIS-004")]
      == [0, 1, 2, 3])
check("the help page nothing links to is an orphan", nav["orphans"] == ["UIS-005"], nav["orphans"])
check("an orphan is unreachable, and not counted twice",
      nav["unreachable"] == ["UIS-005"] and nav["unreachable_not_orphan"] == [])
check("a page whose only exit is logging out is a dead end", nav["dead_ends"] == ["UIS-004"],
      nav["dead_ends"])
check("a self-loop is not an exit", "UIS-003" not in nav["dead_ends"])
check("max depth", nav["max_depth"] == 3)
inv = ui_fixture.inventory()
screen(inv, "UIS-004")["actions"].append({
    "id": "UIS-004.A2", "label": "Menu", "command": None, "kind": "link", "scope": "global",
    "method": "GET", "endpoint": None, "target": "UIS-002", "destructive": False,
    "confirmation": False, "unresolved": None, "source": "web/header.jspf:5"})
check("global navigation to a non-entry screen is an exit",
      "UIS-004" not in compute(inv, ui_fixture.tokens())["navigation"]["dead_ends"])

print("features, input burden, consistency")
check("a feature's steps are its actions", m["features"]["UIF-003"]["steps"] == 1)
check("input burden totals", m["input_burden"] == {
    "avg_visible_inputs": 0.8, "max_visible_inputs": 2, "max_feature_steps": 1,
    "redundant_inputs": 1, "client_only_validations": 1}, m["input_burden"])
con = m["consistency"]
check("one fragmented cluster: two shades of the primary blue",
      con["fragmented_clusters"] == ["color:primary-blue"], con["fragmented_clusters"])
check("aliases are not counted as colors", con["colors"] == 4, con["colors"])
check("label drift for the same command",
      con["label_drift"] == [{"command": "LogOut", "labels": ["Log out", "Sign out"]}],
      con["label_drift"])
check("a component duplicate", con["components_with_duplicates"] == ["UIC-003"])
check("accessibility summary", m["accessibility"]["violating_screens"] == ["UIS-001", "UIS-003"]
      and m["accessibility"]["screens_with_violations"] == 2)

print("caps — @rules/ux-evaluation.md §2")
check("the fixture's caps", m["caps"] == ui_fixture.EXPECTED_CAPS, m["caps"])
clean = json.loads(json.dumps(m))
for sid in clean["per_screen"]:
    clean["per_screen"][sid]["destructive_without_confirmation"] = []
clean["accessibility"]["screens_with_violations"] = 0
clean["input_burden"].update(redundant_inputs=0)
clean["consistency"].update(fragmented_clusters=[], label_drift=[], components_with_duplicates=[])
clean["navigation"].update(orphans=[], dead_ends=[], unreachable_not_orphan=[])
check("a clean UI caps every axis at 5", axis_caps(clean) == dict.fromkeys("HAECN", 5),
      axis_caps(clean))
many = json.loads(json.dumps(clean))
many["per_screen"]["UIS-003"]["destructive_without_confirmation"] = ["a", "b", "c"]
many["accessibility"]["screens_with_violations"] = 5
many["input_burden"].update(redundant_inputs=2, max_feature_steps=6, max_visible_inputs=13)
many["consistency"].update(fragmented_clusters=["a", "b", "c"], label_drift=[{}],
                           components_with_duplicates=["x"])
many["navigation"].update(orphans=["x"], dead_ends=["y"], unreachable_not_orphan=["z"],
                          max_depth=5)
check("caps never go below 1", axis_caps(many) == {"H": 3, "A": 1, "E": 2, "C": 1, "N": 1},
      axis_caps(many))
check("ten percent of screens caps A at 4", axis_caps(dict(clean, accessibility=dict(
    clean["accessibility"], screens_with_violations=1), per_screen={
        str(n): clean["per_screen"]["UIS-001"] for n in range(10)}))["A"] == 4)

print("CLI")
tmp = tempfile.mkdtemp(prefix="ui-metrics-test-")
try:
    root = os.path.join(tmp, "clean")
    ui_fixture.write_project(root)
    proc = subprocess.run([sys.executable, TOOL, root], capture_output=True, text=True)
    check("exit 0 and JSON on stdout", proc.returncode == 0 and json.loads(proc.stdout) == m,
          proc.stderr)
    inv = ui_fixture.inventory()
    inv["screens"][1]["actions"][0]["target"] = "UIS-099"
    root = os.path.join(tmp, "invalid")
    ui_fixture.write_project(root, inv)
    proc = subprocess.run([sys.executable, TOOL, root], capture_output=True, text=True)
    check("an inventory that is not well-formed is refused",
          proc.returncode == 1 and "UIS-099" in proc.stderr, proc.stderr)
    empty = os.path.join(tmp, "empty")
    os.makedirs(empty)
    proc = subprocess.run([sys.executable, TOOL, empty], capture_output=True, text=True)
    check("no inventory is exit 1 with a reason",
          proc.returncode == 1 and "no ui-inventory.json" in proc.stderr, proc.stderr)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n%d checks, %d failed" % (PASSED + FAILED, FAILED))
sys.exit(1 if FAILED else 0)
