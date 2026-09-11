#!/usr/bin/env python3
"""Validate the UX evaluation `/architect:evaluate-ux` emits.

The nine well-formedness rules of @rules/ux-evaluation.md §6 are checked here rather than
trusted to prose. The two that matter most are arithmetic: the UXI must be the formula's value,
and the `metrics` block must be exactly what `ui_metrics.py` computes from the inventory today —
which is what stops an evaluation from carrying a number nobody measured, or a score above what
its own metrics allow.

Usage:
    python3 tools/lib/ux_evaluation.py <project_dir>   (exit 1 on violations)
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manifest_common import duplicates  # noqa: E402
from ui_inventory import iter_tokens, validate_inventory  # noqa: E402
from ui_metrics import compute  # noqa: E402

EVALUATION_PATH = os.path.join("reports", "02_evaluation", "ux-evaluation.json")
LABEL = "ux-evaluation.json"

# @rules/ux-evaluation.md §2 — the test asserts the rule's table says the same.
AXES = (("H", 0.30), ("A", 0.25), ("E", 0.20), ("C", 0.15), ("N", 0.10))
# §3 — half-open bands, highest first: a score belongs to the first floor it reaches.
BANDS = ((80.0, "mature"), (60.0, "adequate"), (40.0, "needs-improvement"), (0.0, "poor"))
SEVERITIES = ("critical", "major", "minor", "info")
EVIDENCE = ("static", "runtime")
MODES = ("static", "static+runtime")
FINDING_RE = re.compile(r"^UX-\d{3,}$")
CRITERION_RE = re.compile(r"^(?:H(?:10|[1-9])|WCAG [1-4]\.\d{1,2}\.\d{1,2})$")
TOLERANCE = 0.5


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _list(value):
    return value if isinstance(value, list) else []


def _score(value):
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 5


def uxi(scores):
    """The formula of §3 for a {key: score} map, rounded to 0.1."""
    total = sum(weight * scores[key] for key, weight in AXES)
    return round(total / 5.0 * 100.0, 1)


def band(value):
    for floor, name in BANDS:
        if value >= floor:
            return name
    return BANDS[-1][1]


def validate_evaluation(evaluation, project_dir=None, inventory=None, tokens=None):
    """Every violation, as a list of one-line strings.

    `inventory` / `tokens` are the model the evaluation was built on. When they are not given
    and `project_dir` is, they are read from the `inventory` path the evaluation cites; with
    neither, the cross-checks (rules 6 and 8) are skipped and only the shape is checked."""
    if not isinstance(evaluation, dict):
        return ["%s: must be an object" % LABEL]
    if evaluation.get("schema_version") != 1:
        return ["%s: schema_version must be 1" % LABEL]
    errors = []

    if inventory is None and project_dir is not None:
        inventory, tokens, load_errors = _load_model(evaluation, project_dir)
        errors.extend(load_errors)

    if evaluation.get("mode") not in MODES:
        errors.append("%s: mode must be static or static+runtime" % LABEL)

    # Rules 1 and 2 — exactly the five axes, with the rule's weights and integer scores.
    axes = evaluation.get("axes")
    scores = {}
    if not isinstance(axes, list):
        errors.append("%s: axes must be an array" % LABEL)
        axes = []
    expected = dict(AXES)
    keys = [a.get("key") for a in axes if isinstance(a, dict)]
    if sorted(k for k in keys if isinstance(k, str)) != sorted(expected) or len(keys) != len(axes):
        errors.append("%s: axes must be exactly %s, each once" % (LABEL, ", ".join(expected)))
    for axis in axes:
        if not _axis(axis, expected):
            continue
        key = axis["key"]
        weight = axis.get("weight")
        if not isinstance(weight, (int, float)) or abs(weight - expected[key]) > 1e-9:
            errors.append("%s: axis %s weight must be %s" % (LABEL, key, expected[key]))
        if not _score(axis.get("score")):
            errors.append("%s: axis %s score must be an integer from 1 to 5" % (LABEL, key))
        else:
            scores[key] = axis["score"]
        if not _text(axis.get("rationale")):
            errors.append("%s: axis %s needs a rationale" % (LABEL, key))

    # Rules 3 and 4 — the index is the formula's, the band is the index's.
    if len(scores) == len(AXES):
        computed = uxi(scores)
        stated = evaluation.get("uxi")
        if not isinstance(stated, (int, float)) or isinstance(stated, bool) \
                or abs(stated - computed) > TOLERANCE:
            errors.append("%s: uxi is %r but the formula gives %s" % (LABEL, stated, computed))
        if evaluation.get("band") != band(computed):
            errors.append("%s: band is %r but a UXI of %s is %r"
                          % (LABEL, evaluation.get("band"), computed, band(computed)))

    # Rule 5 — every finding is complete.
    findings = evaluation.get("findings")
    if not isinstance(findings, list):
        errors.append("%s: findings must be an array" % LABEL)
        findings = []
    objects = [f for f in findings if isinstance(f, dict)]
    if duplicates([f.get("id") for f in objects]):
        errors.append("%s: duplicate finding id" % LABEL)
    by_id = {}
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            errors.append("%s: findings[%d] must be an object" % (LABEL, index))
            continue
        fid = finding.get("id") if _text(finding.get("id")) else "findings[%d]" % index
        if _text(finding.get("id")):
            by_id[finding["id"]] = finding
        if not (isinstance(finding.get("id"), str) and FINDING_RE.match(finding["id"])):
            errors.append("%s: id must be UX-###" % fid)
        if not isinstance(finding.get("axis"), str) or finding["axis"] not in expected:
            errors.append("%s: axis must be one of %s" % (fid, ", ".join(expected)))
        if not (isinstance(finding.get("criterion"), str)
                and CRITERION_RE.match(finding["criterion"])):
            errors.append("%s: criterion %r is neither H1-H10 nor a WCAG success criterion"
                          % (fid, finding.get("criterion")))
        if finding.get("severity") not in SEVERITIES:
            errors.append("%s: severity must be one of %s" % (fid, ", ".join(SEVERITIES)))
        for key in ("title", "description", "recommendation"):
            if not _text(finding.get(key)):
                errors.append("%s: %s is required" % (fid, key))
        if finding.get("evidence") not in EVIDENCE:
            errors.append("%s: evidence must be static or runtime" % fid)
        errors.extend(_check_location(fid, finding.get("location"), inventory, tokens))
        # Rule 9 — runtime evidence is real.
        if finding.get("evidence") == "runtime":
            ref = finding.get("evidence_ref")
            if not _text(ref):
                errors.append("%s: a runtime finding cites its evidence_ref" % fid)
            elif project_dir is not None and not os.path.isfile(os.path.join(project_dir, ref)):
                errors.append("%s: evidence_ref %r does not exist" % (fid, ref))
            runtime = evaluation.get("runtime") if isinstance(evaluation.get("runtime"), dict) \
                else {}
            if evaluation.get("mode") != "static+runtime" or not _text(runtime.get("base_url")):
                errors.append("%s: runtime evidence needs mode static+runtime and runtime.base_url"
                              % fid)

    # Rule 7 — low scores are justified, and axes cite only their own findings.
    for axis in axes:
        if not _axis(axis, expected):
            continue
        key = axis["key"]
        cited = _list(axis.get("finding_ids"))
        for fid in cited:
            if not isinstance(fid, str) or fid not in by_id:
                errors.append("%s: axis %s cites %r, which is not a finding" % (LABEL, key, fid))
            elif by_id[fid].get("axis") != key:
                errors.append("%s: axis %s cites %s, a finding on axis %s"
                              % (LABEL, key, fid, by_id[fid].get("axis")))
        if key in scores and scores[key] <= 3 \
                and not any(f.get("axis") == key for f in objects):
            errors.append("%s: axis %s scores %d with no finding to justify it"
                          % (LABEL, key, scores[key]))

    # Rule 8 — the metrics are the tool's, and no score exceeds its cap.
    metrics = evaluation.get("metrics")
    if not isinstance(metrics, dict):
        errors.append("%s: metrics must be the ui_metrics.py output" % LABEL)
        metrics = {}
    if inventory is not None and tokens is not None:
        recomputed = compute(inventory, tokens)
        if metrics != recomputed:
            differing = sorted(k for k in set(metrics) | set(recomputed)
                               if metrics.get(k) != recomputed.get(k))
            errors.append("%s: metrics differ from what ui_metrics.py computes now (%s) — "
                          "re-run it and embed its output verbatim" % (LABEL, ", ".join(differing)))
        metrics = recomputed
    caps = metrics.get("caps") if isinstance(metrics.get("caps"), dict) else {}
    for key, score in sorted(scores.items()):
        cap = caps.get(key)
        if isinstance(cap, int) and score > cap:
            errors.append("%s: axis %s scores %d above its metric cap %d" % (LABEL, key, score, cap))
    return errors


def _axis(axis, expected):
    return isinstance(axis, dict) and isinstance(axis.get("key"), str) and axis["key"] in expected


def _check_location(fid, location, inventory, tokens):
    """Rule 6 — a finding points at something that exists."""
    if not isinstance(location, dict):
        return ["%s: location must be an object" % fid]
    keys = ("screen", "component", "feature", "token")
    if not any(_text(location.get(k)) for k in keys):
        return ["%s: location names none of %s" % (fid, ", ".join(keys))]
    if inventory is None:
        return []
    known = {
        "screen": {s.get("id") for s in _list(inventory.get("screens")) if isinstance(s, dict)},
        "component": {c.get("id") for c in _list(inventory.get("components"))
                      if isinstance(c, dict)},
        "feature": {f.get("id") for f in _list(inventory.get("features")) if isinstance(f, dict)},
        "token": {path for path, _ in iter_tokens(tokens or {})},
    }
    errors = []
    for key in keys:
        value = location.get(key)
        if _text(value) and value not in known[key]:
            errors.append("%s: location.%s %r does not exist in the inventory" % (fid, key, value))
    return errors


def _load_model(evaluation, project_dir):
    path = evaluation.get("inventory")
    if not _text(path):
        return None, None, ["%s: inventory must name the ui-inventory.json it evaluates" % LABEL]
    try:
        with open(os.path.join(project_dir, path), encoding="utf-8") as handle:
            inventory = json.load(handle)
    except (OSError, ValueError) as exc:
        return None, None, ["%s: inventory %r is unreadable — %s" % (LABEL, path, exc)]
    problems = validate_inventory(inventory, project_dir, check_sources=False)
    if problems:
        return None, None, ["%s: the inventory it cites is not well-formed (%d violation(s)) — "
                            "run tools/lib/ui_inventory.py" % (LABEL, len(problems))]
    with open(os.path.join(project_dir, inventory["design_tokens"]), encoding="utf-8") as handle:
        tokens = json.load(handle)
    return inventory, tokens, []


def load_and_validate(project_dir):
    path = os.path.join(project_dir, EVALUATION_PATH)
    if not os.path.isfile(path):
        return None, []
    try:
        with open(path, encoding="utf-8") as handle:
            evaluation = json.load(handle)
    except (OSError, ValueError) as exc:
        return None, ["%s: unreadable — %s" % (LABEL, exc)]
    return evaluation, validate_evaluation(evaluation, project_dir)


def main(argv):
    project_dir = argv[1] if len(argv) > 1 else "."
    evaluation, errors = load_and_validate(project_dir)
    if evaluation is None and not errors:
        print("no %s in %s — nothing to validate" % (LABEL, project_dir))
        return 0
    for error in errors:
        print(error)
    if errors:
        print("%d violation(s)" % len(errors))
        return 1
    print("%s is well-formed (UXI %s, %s, %d findings)"
          % (LABEL, evaluation.get("uxi"), evaluation.get("band"),
             len(evaluation.get("findings") or [])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
