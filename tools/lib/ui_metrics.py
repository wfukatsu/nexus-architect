#!/usr/bin/env python3
"""The UX metrics of an existing UI, computed from its inventory — never estimated.

`/architect:evaluate-ux` scores five axes (@rules/ux-evaluation.md §2). Every count, ratio and
contrast value it rests on is computed here, deterministically, from the inventory and the design
token file `/architect:analyze-ui` wrote. The skill embeds this output verbatim in
`ux-evaluation.json`, and `ux_evaluation.py` recomputes it and fails when the two differ — so a
number in the evaluation is a measurement or it is a defect.

The navigation definitions (entry, depth, orphan, unreachable, dead end) are
@rules/ui-analysis.md §6; the caps are @rules/ux-evaluation.md §2.

Usage:
    python3 tools/lib/ui_metrics.py <project_dir> [--project=<name>]   (JSON on stdout; exit 1 when
                                                                         the inventory is missing
                                                                         or not well-formed)
"""

import json
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui_inventory import (  # noqa: E402
    find_inventories, is_alias, iter_tokens, token_extension, validate_inventory)

CONTRAST_MINIMUM = {"normal": 4.5, "large": 3.0}
UNLABELED = ("placeholder-only", "none")
MAX_TASK_STEPS = 5
MAX_VISIBLE_INPUTS = 12


def _list(value):
    return value if isinstance(value, list) else []


def _dicts(value):
    return [v for v in _list(value) if isinstance(v, dict)]


def _hex_rgb(value):
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    return tuple(int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _luminance(value):
    def channel(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in _hex_rgb(value))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg, bg):
    """WCAG 2.x contrast ratio of two hex colors, rounded to two decimals."""
    lighter, darker = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def _client_only(field):
    """Validation rules a field enforces only in the browser — the server accepts what they
    forbid. A rule enforced on both sides, or also stated server-side, is not client-only."""
    rules = _dicts(field.get("validation"))
    server = {r.get("rule") for r in rules if r.get("where") in ("server", "both")}
    return sorted({r.get("rule") for r in rules
                   if r.get("where") == "client" and r.get("rule") not in server})


def _screen_metrics(screen):
    visible = [f for f in _dicts(screen.get("inputs")) if f.get("control") != "hidden"]
    low_contrast = []
    for pair in _dicts(screen.get("color_pairs")):
        ratio = contrast_ratio(pair["fg"], pair["bg"])
        if ratio < CONTRAST_MINIMUM.get(pair.get("text", "normal"), 4.5):
            low_contrast.append({"fg": pair["fg"], "bg": pair["bg"], "ratio": ratio,
                                 "text": pair.get("text", "normal")})
    client_only = {f.get("name"): _client_only(f) for f in _dicts(screen.get("inputs"))}
    return {
        "inputs": len(visible),
        "required_inputs": sum(1 for f in visible if f.get("required") is True),
        "outputs": len(_list(screen.get("outputs"))),
        "actions": len(_list(screen.get("actions"))),
        "embedded_logic": len(_list(screen.get("embedded_logic"))),
        "unlabeled_inputs": sorted(f.get("name") for f in visible
                                   if f.get("label_association") in UNLABELED),
        "images_without_alt": sum(1 for i in _dicts(screen.get("images"))
                                  if i.get("alt") is None and i.get("decorative") is not True),
        "lang_missing": not screen.get("lang"),
        "low_contrast_pairs": low_contrast,
        "destructive_without_confirmation": sorted(
            a.get("id") for a in _dicts(screen.get("actions"))
            if a.get("destructive") is True and a.get("confirmation") is not True),
        "client_only_validations": sorted(n for n, rules in client_only.items() if rules),
        "redundant_inputs": sorted(f.get("name") for f in visible if f.get("redundant_with")),
        "depth": None,
    }


def _navigation(screens, per_screen):
    ids = [s.get("id") for s in screens]
    entry = sorted(s.get("id") for s in screens if s.get("entry") is True)
    edges = {sid: [] for sid in ids}
    incoming = {sid: set() for sid in ids}
    for screen in screens:
        for action in _dicts(screen.get("actions")):
            target = action.get("target")
            if target in edges:
                edges[screen.get("id")].append((target, action.get("scope", "screen")))
                if target != screen.get("id"):
                    incoming[target].add(screen.get("id"))

    depth = {sid: 0 for sid in entry}
    queue = deque(entry)
    while queue:
        current = queue.popleft()
        for target, _ in edges[current]:
            if target not in depth:
                depth[target] = depth[current] + 1
                queue.append(target)
    for sid in ids:
        per_screen[sid]["depth"] = depth.get(sid)

    entry_set = set(entry)
    orphans = sorted(sid for sid in ids if sid not in entry_set and not incoming[sid])
    unreachable = sorted(sid for sid in ids if sid not in depth)

    def exits(sid):
        return [t for t, scope in edges[sid]
                if t != sid and not (scope == "global" and t in entry_set)]
    dead_ends = sorted(sid for sid in ids if not exits(sid))
    return {
        "entry": entry,
        "max_depth": max(depth.values()) if depth else 0,
        "orphans": orphans,
        "unreachable": unreachable,
        "unreachable_not_orphan": sorted(set(unreachable) - set(orphans)),
        "dead_ends": dead_ends,
    }


def _consistency(inventory, tokens):
    raw = {path: token for path, token in iter_tokens(tokens or {}) if not is_alias(token)}
    clusters = {}
    for path, token in raw.items():
        cluster = token_extension(token).get("cluster")
        if cluster:
            clusters.setdefault((token.get("$type"), cluster), []).append(path)
    fragmented = sorted("%s:%s" % key for key, members in clusters.items() if len(members) > 1)

    def count(prefix):
        return sum(1 for path in raw if path.startswith(prefix))

    labels = {}
    for screen in _dicts(inventory.get("screens")):
        for action in _dicts(screen.get("actions")):
            if action.get("command"):
                labels.setdefault(action["command"], set()).add(action.get("label"))
    drift = [{"command": command, "labels": sorted(str(l) for l in found)}
             for command, found in sorted(labels.items()) if len(found) > 1]
    # Navigation to one destination under several names. Reported, not capped: "continue
    # shopping" and "find products" may both be right in their context — the evaluator judges.
    destinations = {}
    for screen in _dicts(inventory.get("screens")):
        for action in _dicts(screen.get("actions")):
            if not action.get("command") and isinstance(action.get("target"), str):
                destinations.setdefault(action["target"], set()).add(action.get("label"))
    variants = [{"target": target, "labels": sorted(str(l) for l in found)}
                for target, found in sorted(destinations.items()) if len(found) > 1]
    return {
        "colors": sum(1 for t in raw.values() if t.get("$type") == "color"),
        "font_sizes": count("font.size."),
        "spacing_values": count("space."),
        "radius_values": count("radius."),
        "fragmented_clusters": fragmented,
        "label_drift": drift,
        "destination_label_variants": variants,
        "components_with_duplicates": sorted(
            c.get("id") for c in _dicts(inventory.get("components")) if _list(c.get("duplicates"))),
    }


def _sent(inventory):
    """{action id: (screen id, visible inputs sent, required visible inputs sent)} for every
    submit/AJAX action — what a user has to type to fire it. Hidden inputs are not typed."""
    out = {}
    for screen in _dicts(inventory.get("screens")):
        fields = {f.get("name"): f for f in _dicts(screen.get("inputs"))}
        for action in _dicts(screen.get("actions")):
            if action.get("kind") not in ("submit", "ajax"):
                continue
            visible = [fields[n] for n in _list(action.get("inputs"))
                       if n in fields and fields[n].get("control") != "hidden"]
            out[action.get("id")] = (screen.get("id"), len(visible),
                                     sum(1 for f in visible if f.get("required") is True))
    return out


def _features(inventory, sent):
    out = {}
    for feature in _dicts(inventory.get("features")):
        mine = [sent[a] for a in _list(feature.get("actions")) if a in sent]
        out[feature.get("id")] = {
            "occurrences": len(_list(feature.get("actions"))),
            "screens": len(_list(feature.get("screens"))),
            "inputs": sum(m[1] for m in mine),
            "required_inputs": sum(m[2] for m in mine),
        }
    return out


def _tasks(inventory, sent):
    """@rules/ui-analysis.md §6 — a task's steps are the screens on its path; its inputs are what
    its features' actions on that path make the user type."""
    features = {f.get("id"): f for f in _dicts(inventory.get("features"))}
    out = {}
    for task in _dicts(inventory.get("tasks")):
        path = set(_list(task.get("screens")))
        mine = [sent[a] for fid in _list(task.get("features")) if fid in features
                for a in _list(features[fid].get("actions")) if a in sent and sent[a][0] in path]
        out[task.get("name")] = {
            "steps": len(_list(task.get("screens"))),
            "inputs": sum(m[1] for m in mine),
            "required_inputs": sum(m[2] for m in mine),
        }
    return out


def axis_caps(metrics):
    """@rules/ux-evaluation.md §2 — the highest score each axis's metrics allow: 5 minus one point
    per measured defect class, never below 3. A cap says the axis is not perfect; how far below 3
    it goes is the severity of its findings, which the evaluation validator bounds."""
    screens = metrics["per_screen"]
    acc = metrics["accessibility"]
    nav = metrics["navigation"]
    con = metrics["consistency"]
    burden = metrics["input_burden"]

    destructive = sum(len(s["destructive_without_confirmation"]) for s in screens.values())
    share = acc["screens_with_violations"] / float(len(screens)) if screens else 0.0
    points = {
        "H": (destructive >= 1) + (destructive >= 2),
        "A": (acc["screens_with_violations"] >= 1) + (share > 0.10),
        "E": (burden["redundant_inputs"] >= 1) + (burden["max_task_steps"] > MAX_TASK_STEPS)
             + (burden["max_visible_inputs"] > MAX_VISIBLE_INPUTS),
        "C": (len(con["fragmented_clusters"]) >= 1) + (len(con["label_drift"]) >= 1)
             + (len(con["components_with_duplicates"]) >= 1),
        "N": (len(nav["orphans"]) >= 1) + (len(nav["dead_ends"]) >= 1)
             + (len(nav["unreachable_not_orphan"]) >= 1),
    }
    return {key: 5 - min(2, int(points[key])) for key in ("H", "A", "E", "C", "N")}


def compute(inventory, tokens):
    """The metrics of a well-formed inventory. Run `validate_inventory` first: this function
    reads the shape the validator guarantees and does not re-check it."""
    screens = _dicts(inventory.get("screens"))
    per_screen = {s.get("id"): _screen_metrics(s) for s in screens}
    navigation = _navigation(screens, per_screen)
    sent = _sent(inventory)
    features = _features(inventory, sent)
    tasks = _tasks(inventory, sent)
    violating = sorted(sid for sid, m in per_screen.items()
                       if m["unlabeled_inputs"] or m["images_without_alt"] or m["lang_missing"]
                       or m["low_contrast_pairs"])
    visible = [m["inputs"] for m in per_screen.values()]
    metrics = {
        "schema_version": 1,
        "counts": {"screens": len(screens),
                   "components": len(_list(inventory.get("components"))),
                   "features": len(features)},
        "per_screen": per_screen,
        "navigation": navigation,
        "features": features,
        "tasks": tasks,
        "accessibility": {
            "screens_with_violations": len(violating),
            "violating_screens": violating,
            "unlabeled_inputs": sum(len(m["unlabeled_inputs"]) for m in per_screen.values()),
            "images_without_alt": sum(m["images_without_alt"] for m in per_screen.values()),
            "screens_without_lang": sum(1 for m in per_screen.values() if m["lang_missing"]),
            "low_contrast_pairs": sum(len(m["low_contrast_pairs"]) for m in per_screen.values()),
        },
        "input_burden": {
            "avg_visible_inputs": round(sum(visible) / float(len(visible)), 2) if visible else 0.0,
            "max_visible_inputs": max(visible) if visible else 0,
            "max_task_steps": max((t["steps"] for t in tasks.values()), default=0),
            "max_task_inputs": max((t["inputs"] for t in tasks.values()), default=0),
            "redundant_inputs": sum(len(m["redundant_inputs"]) for m in per_screen.values()),
            "client_only_validations": sum(len(m["client_only_validations"])
                                           for m in per_screen.values()),
        },
        "consistency": _consistency(inventory, tokens),
    }
    metrics["caps"] = axis_caps(metrics)
    return metrics


def load(project_dir, project=None):
    """(inventory, tokens, errors) for the project's inventory; errors when there is none,
    when there are several and no project is named, or when it is not well-formed."""
    paths = find_inventories(project_dir)
    if project:
        paths = [p for p in paths if os.path.basename(os.path.dirname(p)) == project]
    if not paths:
        return None, None, ["no ui-inventory.json under %s/reports/before/" % project_dir]
    if len(paths) > 1:
        names = [os.path.basename(os.path.dirname(p)) for p in paths]
        return None, None, ["several inventories (%s) — pass --project=<name>" % ", ".join(names)]
    try:
        with open(paths[0], encoding="utf-8") as handle:
            inventory = json.load(handle)
    except (OSError, ValueError) as exc:
        return None, None, ["ui-inventory.json: unreadable — %s" % exc]
    errors = validate_inventory(inventory, project_dir, check_sources=False)
    if errors:
        return inventory, None, errors
    with open(os.path.join(project_dir, inventory["design_tokens"]), encoding="utf-8") as handle:
        tokens = json.load(handle)
    return inventory, tokens, []


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    project = None
    for arg in argv[1:]:
        if arg.startswith("--project="):
            project = arg.split("=", 1)[1]
    project_dir = args[0] if args else "."
    inventory, tokens, errors = load(project_dir, project)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(json.dumps(compute(inventory, tokens), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
