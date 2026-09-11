#!/usr/bin/env python3
"""Validate the UX evaluation `/architect:evaluate-ux` emits.

The ten well-formedness rules of @rules/ux-evaluation.md §6 are checked here rather than trusted
to prose. Judgement is fenced three ways, and each fence is a check: the metrics are exactly what
`ui_metrics.py` computes from the inventory now and every score stays within its cap; every
finding names a defect from the rule's vocabulary, which fixes its axis, its criterion and its
default severity; and every score stays within the bound its own findings' severity sets. The
arithmetic — the UXI and its band — is recomputed.

Usage:
    python3 tools/lib/ux_evaluation.py <project_dir>   (exit 1 on violations)
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manifest_common import duplicates  # noqa: E402
from ui_inventory import SourceChecker, iter_tokens, resolve_target, validate_inventory  # noqa: E402
from ui_metrics import compute  # noqa: E402

EVALUATION_PATH = os.path.join("reports", "02_evaluation", "ux-evaluation.json")
EVIDENCE_DIR = "reports/02_evaluation/ux-evidence/"
LABEL = "ux-evaluation.json"

# @rules/ux-evaluation.md §2 — the test asserts the rule's table says the same.
AXES = (("H", 0.30), ("A", 0.25), ("E", 0.20), ("C", 0.15), ("N", 0.10))
# §4 — the WCAG 2.2 criteria code or a rendered page can show.
WCAG = ("1.1.1", "1.3.1", "1.3.5", "1.4.1", "1.4.3", "1.4.11", "2.1.1", "2.4.2", "2.4.4",
        "2.4.6", "2.5.8", "3.1.1", "3.3.1", "3.3.2", "3.3.3", "3.3.7", "4.1.2")
OWNS = {
    "H": {"H1", "H2", "H5", "H8", "H9"},
    "A": {"WCAG " + c for c in WCAG if c != "3.3.7"},
    "E": {"H7", "WCAG 3.3.7"},
    "C": {"H4"},
    "N": {"H3", "H6", "H10"},
}
# §5 — defect: (axis, default severity). `other` belongs to any axis and always needs a reason.
DEFECTS = {
    "unlabeled-input": ("A", "major"), "missing-alt": ("A", "major"),
    "low-contrast": ("A", "major"), "missing-lang": ("A", "major"),
    "small-target": ("A", "minor"), "error-not-identified": ("A", "minor"),
    "missing-input-purpose": ("A", "minor"),
    "destructive-without-confirmation": ("H", "major"), "vague-error-message": ("H", "major"),
    "no-feedback": ("H", "minor"), "script-dependent-content": ("H", "minor"),
    "redundant-input": ("E", "minor"), "excessive-steps": ("E", "minor"),
    "excessive-inputs": ("E", "minor"),
    "label-drift": ("C", "minor"), "hand-built-duplicate": ("C", "minor"),
    "token-fragmentation": ("C", "minor"),
    "dead-end": ("N", "major"), "missing-path": ("N", "major"), "orphan-screen": ("N", "minor"),
}
OTHER = "other"
# §3 — half-open bands, highest first: a score belongs to the first floor it reaches.
BANDS = ((80.0, "mature"), (60.0, "adequate"), (40.0, "needs-improvement"), (0.0, "poor"))
SEVERITIES = ("critical", "major", "minor", "info")
# §2 — the highest score an axis may have given the worst severity among its findings.
SEVERITY_BOUND = {"critical": 2, "major": 3, "minor": 4, "info": 5}
EVIDENCE = ("static", "runtime")
MODES = ("static", "static+runtime")
OUTCOMES = ("confirmed", "refined", "new")
CAPTURE_STATUS = ("captured", "partial", "not-captured")
FINDING_RE = re.compile(r"^UX-\d{3,}$")
URL_RE = re.compile(r"^https?://[^\s/]+")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")
TOLERANCE = 0.05
SUBJECT_ORDER = ("action", "input", "component", "token", "feature", "screen")


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _list(value):
    return value if isinstance(value, list) else []


def _dicts(value):
    return [v for v in _list(value) if isinstance(v, dict)]


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


def subject(finding):
    """§5 — the most specific element a finding is about; the key of rule 9."""
    loc = finding.get("location") if isinstance(finding.get("location"), dict) else {}
    for key in SUBJECT_ORDER:
        if _text(loc.get(key)):
            value = loc[key]
            if key == "input":
                value = "%s:%s" % (loc.get("screen"), value)
            return "%s=%s" % (key, value)
    return None


def _axis(axis, expected):
    return isinstance(axis, dict) and isinstance(axis.get("key"), str) and axis["key"] in expected


class Model:
    """The inventory the evaluation was built on, indexed for the location checks."""

    def __init__(self, inventory, tokens, project_dir=None):
        self.inventory = inventory
        self.tokens = tokens
        screens = _dicts(inventory.get("screens"))
        self.screens = {s.get("id"): s for s in screens if isinstance(s.get("id"), str)}
        self.actions = {a.get("id"): sid for sid, s in self.screens.items()
                        for a in _dicts(s.get("actions")) if isinstance(a.get("id"), str)}
        self.inputs = {sid: {f.get("name") for f in _dicts(s.get("inputs"))}
                       for sid, s in self.screens.items()}
        self.components = {c.get("id"): set(_list(c.get("used_by")))
                           for c in _dicts(inventory.get("components"))
                           if isinstance(c.get("id"), str)}
        self.features = {f.get("id"): set(_list(f.get("screens")))
                         for f in _dicts(inventory.get("features")) if isinstance(f.get("id"), str)}
        self.tasks = {t.get("name") for t in _dicts(inventory.get("tasks"))}
        self.token_paths = {path for path, _ in iter_tokens(tokens or {})}
        root = resolve_target(inventory, project_dir) if project_dir else None
        self.sources = SourceChecker(root if root and os.path.isdir(root) else None)


def validate_evaluation(evaluation, project_dir=None, inventory=None, tokens=None):
    """Every violation, as a list of one-line strings.

    `inventory` / `tokens` are the model the evaluation was built on. When they are not given
    and `project_dir` is, they are read from the `inventory` path the evaluation cites; with
    neither, the cross-checks (locations, metrics) are skipped and only the shape is checked."""
    if not isinstance(evaluation, dict):
        return ["%s: must be an object" % LABEL]
    if evaluation.get("schema_version") != 1:
        return ["%s: schema_version must be 1" % LABEL]
    errors = []

    if inventory is None and project_dir is not None:
        inventory, tokens, load_errors = _load_model(evaluation, project_dir)
        errors.extend(load_errors)
    model = Model(inventory, tokens, project_dir) if inventory is not None else None

    if not (isinstance(evaluation.get("generated_at"), str) and ISO_RE.match(evaluation["generated_at"])):
        errors.append("%s: generated_at must be an ISO-8601 timestamp" % LABEL)
    if evaluation.get("mode") not in MODES:
        errors.append("%s: mode must be static or static+runtime" % LABEL)
    if model is not None:
        for name in _list(evaluation.get("primary_tasks")):
            if name not in model.tasks:
                errors.append("%s: primary task %r is not a task of the inventory" % (LABEL, name))

    # Rule 1 — exactly the five axes, with the rule's weights.
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

    # Runtime block — read before the findings, which rule 10 checks against it.
    runtime = evaluation.get("runtime") if isinstance(evaluation.get("runtime"), dict) else {}
    if "captured" in runtime and not isinstance(runtime["captured"], list):
        errors.append("%s: runtime.captured must be an array" % LABEL)
    captured = {}
    for i, entry in enumerate(_list(runtime.get("captured"))):
        if not isinstance(entry, dict) or entry.get("status") not in CAPTURE_STATUS \
                or not _text(entry.get("screen")):
            errors.append("%s: runtime.captured[%d] needs screen and status (%s)"
                          % (LABEL, i, "|".join(CAPTURE_STATUS)))
            continue
        captured[entry["screen"]] = entry
        if entry["status"] != "not-captured":
            for key in ("screenshot", "a11y"):
                ref = entry.get(key)
                if not _text(ref) or not ref.startswith(EVIDENCE_DIR):
                    errors.append("%s: runtime.captured[%d].%s must be a file under %s"
                                  % (LABEL, i, key, EVIDENCE_DIR))
                elif project_dir is not None and not os.path.isfile(os.path.join(project_dir, ref)):
                    errors.append("%s: runtime.captured[%d].%s %r does not exist"
                                  % (LABEL, i, key, ref))
        elif not _text(entry.get("reason")):
            errors.append("%s: runtime.captured[%d] says why it was not captured (reason)"
                          % (LABEL, i))
    if evaluation.get("mode") == "static" and captured:
        errors.append("%s: a static evaluation has no runtime captures" % LABEL)
    if evaluation.get("mode") == "static+runtime":
        if not (isinstance(runtime.get("base_url"), str) and URL_RE.match(runtime["base_url"])):
            errors.append("%s: static+runtime needs runtime.base_url (an http(s) URL)" % LABEL)
        if not any(e.get("status") != "not-captured" for e in captured.values()):
            errors.append("%s: static+runtime with nothing captured is a static evaluation" % LABEL)

    # Rule 5 — every finding is complete.
    findings = evaluation.get("findings")
    if not isinstance(findings, list):
        errors.append("%s: findings must be an array" % LABEL)
        findings = []
    objects = [f for f in findings if isinstance(f, dict)]
    if duplicates([f.get("id") for f in objects]):
        errors.append("%s: duplicate finding id" % LABEL)
    by_id = {}
    worst = {}
    subjects = {}
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            errors.append("%s: findings[%d] must be an object" % (LABEL, index))
            continue
        fid = finding.get("id") if _text(finding.get("id")) else "findings[%d]" % index
        if _text(finding.get("id")):
            by_id[finding["id"]] = finding
        if not (isinstance(finding.get("id"), str) and FINDING_RE.match(finding["id"])):
            errors.append("%s: id must be UX-###" % fid)
        axis_key = finding.get("axis") if isinstance(finding.get("axis"), str) else None
        if axis_key not in expected:
            errors.append("%s: axis must be one of %s" % (fid, ", ".join(expected)))
            axis_key = None
        defect = finding.get("defect")
        if not isinstance(defect, str) or (defect not in DEFECTS and defect != OTHER):
            errors.append("%s: defect %r is not in the vocabulary of @rules/ux-evaluation.md §5"
                          % (fid, defect))
            defect = None
        elif defect != OTHER and axis_key and DEFECTS[defect][0] != axis_key:
            errors.append("%s: %s belongs to axis %s, not %s"
                          % (fid, defect, DEFECTS[defect][0], axis_key))
        criterion = finding.get("criterion")
        if axis_key and (not isinstance(criterion, str) or criterion not in OWNS[axis_key]):
            errors.append("%s: criterion %r is not one axis %s owns (%s)"
                          % (fid, criterion, axis_key, ", ".join(sorted(OWNS[axis_key]))))
        severity = finding.get("severity")
        if severity not in SEVERITIES:
            errors.append("%s: severity must be one of %s" % (fid, ", ".join(SEVERITIES)))
        elif defect and (defect == OTHER or DEFECTS[defect][1] != severity) \
                and not _text(finding.get("severity_reason")):
            errors.append("%s: a %s %s departs from the default severity — say why "
                          "(severity_reason)" % (fid, severity, defect))
        if severity in SEVERITIES and axis_key:
            if SEVERITY_BOUND[severity] < SEVERITY_BOUND.get(worst.get(axis_key, "info"), 5):
                worst[axis_key] = severity
        for key in ("title", "description", "recommendation"):
            if not _text(finding.get(key)):
                errors.append("%s: %s is required" % (fid, key))
        errors.extend(_check_location(fid, finding.get("location"), model))
        # Rule 9 — one defect, one finding.
        key = (defect or finding.get("criterion"), subject(finding))
        if defect == OTHER:
            key = (OTHER, finding.get("criterion"), subject(finding))
        if key[-1] is not None:
            if key in subjects:
                errors.append("%s: the same defect on the same %s as %s — one defect, one finding"
                              % (fid, key[-1], subjects[key]))
            else:
                subjects[key] = fid
        # Rule 10 — evidence.
        evidence = finding.get("evidence")
        if evidence not in EVIDENCE:
            errors.append("%s: evidence must be static or runtime" % fid)
        elif evidence == "static":
            if finding.get("evidence_ref") or finding.get("runtime_outcome"):
                errors.append("%s: a static finding cites no evidence file and no runtime outcome"
                              % fid)
        else:
            errors.extend(_check_runtime(fid, finding, evaluation, captured, project_dir))

    # Rule 7 — low scores are justified; every finding is listed by exactly its own axis.
    listed = {}
    for axis in axes:
        if not _axis(axis, expected):
            continue
        key = axis["key"]
        for fid in _list(axis.get("finding_ids")):
            if not isinstance(fid, str) or fid not in by_id:
                errors.append("%s: axis %s cites %r, which is not a finding" % (LABEL, key, fid))
                continue
            listed.setdefault(fid, []).append(key)
            if by_id[fid].get("axis") != key:
                errors.append("%s: axis %s cites %s, a finding on axis %s"
                              % (LABEL, key, fid, by_id[fid].get("axis")))
        if key in scores and scores[key] <= 3 \
                and not any(f.get("axis") == key for f in objects):
            errors.append("%s: axis %s scores %d with no finding to justify it"
                          % (LABEL, key, scores[key]))
    for fid, finding in sorted(by_id.items()):
        if finding.get("axis") in expected and listed.get(fid) != [finding["axis"]]:
            errors.append("%s: is not listed (once) in its axis's finding_ids" % fid)

    # Rule 2 — severity bounds.
    for key, score in sorted(scores.items()):
        severity = worst.get(key)
        if severity and score > SEVERITY_BOUND[severity]:
            errors.append("%s: axis %s scores %d but has a %s finding — at most %d"
                          % (LABEL, key, score, severity, SEVERITY_BOUND[severity]))

    # Rule 8 — the metrics are the tool's; Rule 2 — no score exceeds its cap.
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

    for i, item in enumerate(_list(evaluation.get("withdrawn"))):
        if not isinstance(item, dict) or not _text(item.get("title")) \
                or not _text(item.get("reason")) or not _text(item.get("evidence_ref")):
            errors.append("%s: withdrawn[%d] needs title, reason and evidence_ref" % (LABEL, i))
    return errors


def _check_location(fid, location, model):
    """Rule 6 — a finding points at something that exists, and its parts agree."""
    if not isinstance(location, dict):
        return ["%s: location must be an object" % fid]
    keys = ("screen", "component", "feature", "token")
    screen = location.get("screen") if _text(location.get("screen")) else None
    if (_text(location.get("action")) or _text(location.get("input"))) and not screen:
        return ["%s: an action or input location names its screen" % fid]
    if not any(_text(location.get(k)) for k in keys):
        return ["%s: location names none of %s" % (fid, ", ".join(keys))]
    errors = []
    if model is None:
        return errors
    if screen and screen not in model.screens:
        errors.append("%s: location.screen %r does not exist in the inventory" % (fid, screen))
        return errors
    action = location.get("action")
    if _text(action) and model.actions.get(action) != screen:
        errors.append("%s: location.action %r is not an action of %s" % (fid, action, screen))
    name = location.get("input")
    if _text(name) and screen and name not in model.inputs.get(screen, set()):
        errors.append("%s: location.input %r is not an input of %s" % (fid, name, screen))
    component = location.get("component")
    if _text(component):
        if component not in model.components:
            errors.append("%s: location.component %r does not exist in the inventory"
                          % (fid, component))
        elif screen and screen not in model.components[component]:
            errors.append("%s: %s is not used by %s" % (fid, component, screen))
    feature = location.get("feature")
    if _text(feature):
        if feature not in model.features:
            errors.append("%s: location.feature %r does not exist in the inventory" % (fid, feature))
        elif screen and screen not in model.features[feature]:
            errors.append("%s: %s has no action on %s" % (fid, feature, screen))
    token = location.get("token")
    if _text(token) and token not in model.token_paths:
        errors.append("%s: location.token %r does not exist in the token file" % (fid, token))
    if location.get("source") is not None:
        errors.extend(model.sources.check("%s: location" % fid, location.get("source")))
    return errors


def _check_runtime(fid, finding, evaluation, captured, project_dir):
    """Rule 10 — a runtime finding is backed by a capture of its own screen."""
    errors = []
    ref = finding.get("evidence_ref")
    if evaluation.get("mode") != "static+runtime":
        errors.append("%s: runtime evidence needs mode static+runtime" % fid)
    if not _text(ref) or not ref.startswith(EVIDENCE_DIR) or ".." in ref:
        errors.append("%s: a runtime finding cites a file under %s" % (fid, EVIDENCE_DIR))
    elif project_dir is not None and not os.path.isfile(os.path.join(project_dir, ref)):
        errors.append("%s: evidence_ref %r does not exist" % (fid, ref))
    screen = (finding.get("location") or {}).get("screen") \
        if isinstance(finding.get("location"), dict) else None
    entry = captured.get(screen)
    if not entry or entry.get("status") == "not-captured":
        errors.append("%s: runtime evidence for %r, a screen that was not captured" % (fid, screen))
    elif _text(ref) and ref not in (entry.get("screenshot"), entry.get("a11y")) \
            and not os.path.basename(ref).startswith(str(screen)):
        errors.append("%s: evidence_ref %r is not a capture of %s" % (fid, ref, screen))
    if finding.get("runtime_outcome") not in OUTCOMES:
        errors.append("%s: runtime_outcome must be one of %s" % (fid, ", ".join(OUTCOMES)))
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
