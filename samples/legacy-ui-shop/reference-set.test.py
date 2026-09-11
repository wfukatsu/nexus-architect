#!/usr/bin/env python3
"""The committed UI reference set of legacy-ui-shop, checked against its own answer key.

`expected-reports/` is what `/architect:analyze-ui` and `/architect:evaluate-ux` produced on this
sample, reviewed and kept. This suite stages it as a project and asserts three things:

1. It is well-formed: the three UI validators pass (the inventory's sources resolved against this
   sample's code), and every Markdown view passes both output hooks with body headings from `##`.
2. It is measured: the evaluation's metrics equal what `ui_metrics.py` computes from the inventory.
3. It is complete: every defect planted in the sample (`planted-defects.json`) is visible — in the
   inventory or its metrics for the inventory-level categories, and as an evaluation finding at the
   right place with an acceptable criterion for the UX categories.

A skill change that makes the reference set stale fails here first; regenerate it with the skills,
review it, and commit it — never edit the expected files by hand to make this pass.

Run: python3 samples/legacy-ui-shop/reference-set.test.py
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
EXPECTED = os.path.join(HERE, "expected-reports")
EXPECTED_WORK = os.path.join(HERE, "expected-work")
PROJECT = "legacy-ui-shop"
LANG = "ja"   # the output language the reference set was produced in
LIB = os.path.join(REPO, "tools", "lib")
HOOKS = os.path.join(REPO, "hooks")

sys.path.insert(0, LIB)
from ui_metrics import compute  # noqa: E402
from ui_views import VIEWS, render  # noqa: E402

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


# The defect of @rules/ux-evaluation.md §5 each planted UX category must be filed as. The
# vocabulary fixes the axis and the criterion, so matching on it is matching on both.
UX_DEFECT = {
    "unlabeled-input": "unlabeled-input",
    "missing-alt": "missing-alt",
    "low-contrast": "low-contrast",
    "missing-lang": "missing-lang",
    "destructive-without-confirmation": "destructive-without-confirmation",
    "vague-error-message": "vague-error-message",
    "inconsistent-button": "hand-built-duplicate",
    "inconsistent-color": "token-fragmentation",
    "label-drift": "label-drift",
    "dead-end": "dead-end",
    "orphan-screen": "orphan-screen",
    "redundant-input": "redundant-input",
}
INVENTORY_ONLY = ("embedded-logic", "role-guard", "client-only-validation")


def source_path(source):
    return (source or "").split(":", 1)[0]


def source_span(source):
    m = re.match(r"^[^:]+:(\d+)(?:-(\d+))?$", source or "")
    if not m:
        return None
    return int(m.group(1)), int(m.group(2) or m.group(1))


def near(source, file, line, slack=3):
    """A cited source that is the defect's file and covers (or sits within a few lines of) it."""
    if source_path(source) != file:
        return False
    span = source_span(source)
    return span is None or span[0] - slack <= line <= span[1] + slack


def route_key(route):
    return (route or "").split("?", 1)[0].rstrip("/")


if not os.path.isdir(EXPECTED):
    print("no expected-reports/ — nothing to check")
    sys.exit(1)

tmp = tempfile.mkdtemp(prefix="legacy-ui-reference-")
try:
    shutil.copytree(EXPECTED, os.path.join(tmp, "reports"))
    # The Open Questions store the views read their questions from.
    if os.path.isdir(EXPECTED_WORK):
        shutil.copytree(EXPECTED_WORK, os.path.join(tmp, "work"))

    print("the reference set is well-formed")
    for tool, extra in (("ui_inventory.py", ["--target-root=%s" % HERE]),
                        ("ui_metrics.py", []), ("ux_evaluation.py", [])):
        proc = subprocess.run([sys.executable, os.path.join(LIB, tool), tmp] + extra,
                              capture_output=True, text=True)
        check("%s exits 0" % tool, proc.returncode == 0 and "nothing to validate" not in proc.stdout,
              (proc.stdout + proc.stderr)[-1500:])

    markdown = sorted(os.path.join(root, f) for root, _, files in os.walk(os.path.join(tmp, "reports"))
                      for f in files if f.endswith(".md"))
    check("the reference set has its Markdown views", len(markdown) >= 5, markdown)
    for path in markdown:
        rel = os.path.relpath(path, tmp)
        for hook in ("validate-frontmatter.sh", "validate-mermaid.sh"):
            proc = subprocess.run(["bash", os.path.join(HOOKS, hook), path],
                                  capture_output=True, text=True)
            check("%s passes %s" % (rel, hook), proc.returncode == 0,
                  (proc.stdout + proc.stderr)[-600:])
        body = open(path, encoding="utf-8").read().split("\n---", 1)[-1]
        body = re.sub(r"```.*?```", "", body, flags=re.S)
        check("%s starts its body headings at ##" % rel, not re.search(r"^# ", body, re.M))

    inv_path = os.path.join(tmp, "reports", "before", PROJECT, "ui-inventory.json")
    ev_path = os.path.join(tmp, "reports", "02_evaluation", "ux-evaluation.json")
    inventory = json.load(open(inv_path, encoding="utf-8"))
    tokens = json.load(open(os.path.join(tmp, inventory["design_tokens"]), encoding="utf-8"))
    evaluation = json.load(open(ev_path, encoding="utf-8"))
    metrics = compute(inventory, tokens)

    print("the reference set is measured and rendered, not written")
    check("the evaluation's metrics are ui_metrics.py's", evaluation.get("metrics") == metrics)
    rendered = render(tmp, inventory, tokens, LANG)
    for name in VIEWS:
        committed = open(os.path.join(tmp, "reports", "before", PROJECT, name), encoding="utf-8").read()
        check("%s is exactly what ui_views.py renders from the inventory" % name,
              committed == rendered[name],
              "re-render with: python3 tools/lib/ui_views.py <project> --lang=%s" % LANG)

    screens_by_route = {route_key(s.get("route")): s for s in inventory["screens"]}
    findings = evaluation.get("findings") or []
    features = {f["id"]: f for f in inventory.get("features") or []}

    def screen_of(defect):
        return screens_by_route.get(route_key(defect.get("route")))

    print("every planted defect is visible")
    key = json.load(open(os.path.join(HERE, "planted-defects.json"), encoding="utf-8"))
    for defect in key["defects"]:
        category, file, line = defect["category"], defect["file"], defect["line"]
        label = "%s %s (%s:%d)" % (defect["id"], category, file, line)
        screen = screen_of(defect)
        sid = screen.get("id") if screen else None
        per = metrics["per_screen"].get(sid, {}) if sid else {}

        if category == "embedded-logic":
            found = any(near(item.get("source"), file, line)
                        for s in inventory["screens"] for item in s.get("embedded_logic") or [])
        elif category == "role-guard":
            guards = list((screen or {}).get("access", {}).get("guards") or []) + [
                a["guard"] for a in (screen or {}).get("actions") or []
                if isinstance(a.get("guard"), dict)]
            found = any(g.get("kind") == "view" and source_path(g.get("source")) == file
                        for g in guards)
        elif category == "client-only-validation":
            found = bool(per.get("client_only_validations"))
        else:
            measured = {
                "unlabeled-input": bool(per.get("unlabeled_inputs")),
                "missing-alt": per.get("images_without_alt", 0) > 0,
                "low-contrast": bool(per.get("low_contrast_pairs")),
                "missing-lang": per.get("lang_missing") is True,
                "destructive-without-confirmation": bool(per.get("destructive_without_confirmation")),
                "vague-error-message": bool(screen and screen.get("messages")),
                "inconsistent-button": bool(metrics["consistency"]["components_with_duplicates"]),
                "inconsistent-color": bool(metrics["consistency"]["fragmented_clusters"]),
                "label-drift": bool(metrics["consistency"]["label_drift"]),
                "dead-end": sid in metrics["navigation"]["dead_ends"],
                "orphan-screen": sid in metrics["navigation"]["orphans"],
                "redundant-input": bool(per.get("redundant_inputs")),
            }[category]
            check("%s is in the inventory's metrics" % label, measured)

            def placed(f):
                loc = f.get("location") or {}
                if sid and loc.get("screen") == sid:
                    return True
                if loc.get("feature") in features and sid in features[loc["feature"]]["screens"]:
                    return True
                if not defect.get("route") or category in ("inconsistent-button",
                                                           "inconsistent-color"):
                    return bool(loc.get("token") or loc.get("component")) \
                        or source_path(loc.get("source")) == file
                return False
            found = any(f.get("defect") == UX_DEFECT[category] and placed(f) for f in findings)
        check("%s is found" % label, found)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n%d checks, %d failed" % (PASSED + FAILED, FAILED))
sys.exit(1 if FAILED else 0)
