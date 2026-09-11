#!/usr/bin/env python3
"""Validate the UI inventory `/architect:analyze-ui` emits.

The ten well-formedness rules of @rules/ui-analysis.md §4 are checked here rather than trusted
to prose: an inventory that lists a transition to a screen nobody declared, a component whose
`used_by` disagrees with the screens that use it, a submit button no feature owns, a task whose
path skips a screen, or a source line past the end of its file reads perfectly well and is wrong —
and everything downstream (`evaluate-ux`, the actor matrix, the legacy requirements) inherits it.

The inventory lives at `reports/before/<project>/ui-inventory.json`; every `source` in it is
relative to its `target_path` (resolved against the project directory unless absolute), so the
check reads the analysed codebase, not the report tree.

Usage:
    python3 tools/lib/ui_inventory.py <project_dir> [--target-root=<path>]   (exit 1 on violations)
"""

import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manifest_common import duplicates  # noqa: E402

INVENTORY_GLOB = os.path.join("reports", "before", "*", "ui-inventory.json")
LABEL = "ui-inventory.json"
LABEL_TOKENS = "ui-design-tokens.json"
EXTENSION = "nexus-architect"

SCREEN_RE = re.compile(r"^UIS-\d{3,}$")
COMPONENT_RE = re.compile(r"^UIC-\d{3,}$")
FEATURE_RE = re.compile(r"^UIF-\d{3,}$")
ACTION_RE = re.compile(r"^(UIS-\d{3,})\.A\d+$")
OQ_RE = re.compile(r"^OQ-\d{3,}$")
HEX_RE = re.compile(r"^#[0-9a-f]{6}$")
SOURCE_RE = re.compile(r"^(?P<path>[^:]+?)(?::(?P<start>\d+)(?:-(?P<end>\d+))?)?$")
ALIAS_RE = re.compile(r"^\{([^{}]+)\}$")

CONTROLS = ("text", "password", "email", "number", "tel", "date", "select", "radio",
            "checkbox", "textarea", "file", "hidden", "other")
DATA_TYPES = ("string", "integer", "decimal", "date", "boolean", "enum", "file", "other")
LABEL_ASSOCIATIONS = ("for", "wrapping", "aria", "legend", "placeholder-only", "none")
HIDDEN_ASSOCIATION = "n/a"
VALIDATION_RULES = ("required", "min", "max", "minLength", "maxLength", "pattern", "enum",
                    "format", "custom")
WHERE = ("client", "server", "both")
ENFORCEMENT = ("reject", "clamp", "ignore")
OUTPUT_KINDS = ("field", "table", "list", "message", "image", "chart", "download", "other")
MESSAGE_KINDS = ("error", "warning", "info", "success")
ACTION_KINDS = ("submit", "link", "button", "ajax", "other")
SENDING_KINDS = ("submit", "ajax")
ACTION_SCOPES = ("screen", "global")
GUARD_KINDS = ("view", "controller", "filter", "config", "route")
AUTHENTICATION = ("required", "none")
LOGIC_KINDS = ("calculation", "validation", "authorization", "workflow", "formatting",
               "data-access", "other")
LOGIC_HOMES = ("domain", "application", "presentation")
COMPONENT_KINDS = ("include", "tag", "fragment", "component", "macro", "css-class",
                   "inline-style", "copy", "other")
DUPLICATE_KINDS = ("inline-style", "copy")
LEVELS = ("atom", "molecule", "organism", "template")
TEXT_SIZES = ("normal", "large")
CRUD = set("CRUD")
TOKEN_TYPES = ("color", "dimension", "fontFamily", "fontWeight", "number", "shadow", "duration",
               "typography", "border", "cubicBezier")


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _list(value):
    return value if isinstance(value, list) else []


def _dicts(value):
    return [v for v in _list(value) if isinstance(v, dict)]


def _texts(value):
    """A non-empty list of non-empty strings."""
    return isinstance(value, list) and bool(value) and all(_text(v) for v in value)


# ------------------------------------------------------------------------------- tokens
def iter_tokens(tree, prefix=""):
    """(dotted path, token) for every DTCG leaf — a dict holding `$value`. Keys starting with
    `$` are group metadata, not children."""
    if not isinstance(tree, dict):
        return
    for key, value in tree.items():
        if key.startswith("$") or not isinstance(value, dict):
            continue
        path = "%s.%s" % (prefix, key) if prefix else key
        if "$value" in value:
            yield path, value
        else:
            yield from iter_tokens(value, path)


def token_extension(token):
    ext = token.get("$extensions") if isinstance(token, dict) else None
    ext = ext.get(EXTENSION) if isinstance(ext, dict) else None
    return ext if isinstance(ext, dict) else {}


def is_alias(token):
    return isinstance(token.get("$value"), str) and bool(ALIAS_RE.match(token["$value"]))


def validate_tokens(tokens, label=LABEL_TOKENS):
    """Rule 9, the file half: valid DTCG with provenance on every raw token."""
    if not isinstance(tokens, dict):
        return ["%s: must be an object" % label], {}
    errors = []
    leaves = dict(iter_tokens(tokens))
    if not leaves:
        errors.append("%s: declares no tokens" % label)
    for path, token in sorted(leaves.items()):
        if token.get("$type") not in TOKEN_TYPES:
            errors.append("%s: %s.$type must be one of %s" % (label, path, ", ".join(TOKEN_TYPES)))
        value = token.get("$value")
        if is_alias(token):
            target = ALIAS_RE.match(value).group(1)
            if target not in leaves:
                errors.append("%s: %s aliases {%s}, which is not a token" % (label, path, target))
            continue
        if value in (None, "", [], {}):
            errors.append("%s: %s.$value is empty" % (label, path))
        if token.get("$type") == "color" and not (isinstance(value, str) and HEX_RE.match(value)):
            errors.append("%s: %s.$value %r is not a 6-digit lowercase hex color"
                          % (label, path, value))
        ext = token_extension(token)
        if not [s for s in _list(ext.get("sources")) if _text(s)]:
            errors.append("%s: %s has no $extensions.%s.sources — a raw token names where it is "
                          "used" % (label, path, EXTENSION))
        count = ext.get("usage_count")
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            errors.append("%s: %s.usage_count must be a positive integer" % (label, path))
    return errors, leaves


def token_sources(leaves):
    """(where, source) for every raw token's provenance — rule 8 checks them like any other."""
    for path, token in leaves.items():
        if is_alias(token):
            continue
        for source in _list(token_extension(token).get("sources")):
            yield "%s (token %s)" % (LABEL_TOKENS, path), source


# ------------------------------------------------------------------------------ sources
class SourceChecker:
    """Rule 8 — every source is `path[:line[-end]]`, the file exists under the target and the
    line is within it. Line counts are cached: one inventory cites the same template often."""

    def __init__(self, root):
        self.root = os.path.realpath(root) if root else None
        self.lines = {}

    def line_count(self, path):
        if path not in self.lines:
            try:
                with open(path, "rb") as handle:
                    self.lines[path] = handle.read().count(b"\n") + 1
            except OSError:
                self.lines[path] = None
        return self.lines[path]

    def check(self, where, source):
        if not _text(source):
            return ["%s: source must be a non-empty string" % where]
        m = SOURCE_RE.match(source.strip())
        if not m or os.path.isabs(m.group("path")):
            return ["%s: source %r is not path[:line[-end]] relative to the target" % (where, source)]
        start, end = m.group("start"), m.group("end")
        if start is not None and int(start) < 1:
            return ["%s: source %r has a line below 1" % (where, source)]
        if end is not None and int(end) < int(start):
            return ["%s: source %r ends before it starts" % (where, source)]
        if self.root is None:
            return []
        full = os.path.realpath(os.path.join(self.root, m.group("path")))
        if not full.startswith(self.root + os.sep) or not os.path.isfile(full):
            return ["%s: source %r does not exist under the target" % (where, source)]
        last = int(end or start or 0)
        count = self.line_count(full)
        if last and count is not None and last > count:
            return ["%s: source %r is past the end of the file (%d lines)" % (where, source, count)]
        return []


def resolve_target(inventory, project_dir, target_root=None):
    if target_root:
        return target_root
    target = inventory.get("target_path") if isinstance(inventory, dict) else None
    if not _text(target):
        return None
    if os.path.isabs(target) or project_dir is None:
        return target
    return os.path.join(project_dir, target)


# ------------------------------------------------------------------------------ screens
def _validate_guard(where, guard, *, needs_roles):
    if not isinstance(guard, dict) or guard.get("kind") not in GUARD_KINDS:
        return ["%s.kind must be one of %s" % (where, ", ".join(GUARD_KINDS))]
    if needs_roles and not _texts(guard.get("roles")):
        return ["%s.roles must name the roles the check lets through" % where]
    return []


def _validate_screen(screen, index, screen_ids, component_ids):
    errors = []
    sid = screen.get("id") if _text(screen.get("id")) else "screens[%d]" % index
    # Rule 1 — ids.
    if not (isinstance(screen.get("id"), str) and SCREEN_RE.match(screen["id"])):
        errors.append("%s: id must be UIS-###" % sid)
    # Rule 2 — name, source, route, entry, access.
    if not _text(screen.get("name")):
        errors.append("%s: name is required" % sid)
    if not _text(screen.get("source")):
        errors.append("%s: source is required" % sid)
    if not _text(screen.get("route")) and not _text(screen.get("route_unresolved")):
        errors.append("%s: route is required unless route_unresolved says why" % sid)
    if not isinstance(screen.get("entry"), bool):
        errors.append("%s: entry must be a boolean" % sid)
    access = screen.get("access")
    if not isinstance(access, dict):
        errors.append("%s: access must be an object" % sid)
    else:
        if access.get("authentication") not in AUTHENTICATION:
            errors.append("%s: access.authentication must be required or none" % sid)
        if not _texts(access.get("roles")):
            errors.append("%s: access.roles must name at least one role (anonymous when no "
                          "authentication is needed)" % sid)
        for g, guard in enumerate(_list(access.get("guards"))):
            errors.extend(_validate_guard("%s: access.guards[%d]" % (sid, g), guard,
                                          needs_roles=False))
    for h, handler in enumerate(_list(screen.get("handlers"))):
        if not isinstance(handler, dict) or not _text(handler.get("ref")):
            errors.append("%s.handlers[%d]: ref is required" % (sid, h))

    # Rule 3 — typed inputs and accessibility facts.
    names = set()
    for i, field in enumerate(_list(screen.get("inputs"))):
        where = "%s.inputs[%d]" % (sid, i)
        if not isinstance(field, dict):
            errors.append("%s must be an object" % where)
            continue
        if not _text(field.get("name")):
            errors.append("%s: name is required" % where)
        else:
            names.add(field["name"])
        if field.get("control") not in CONTROLS:
            errors.append("%s: control must be one of %s" % (where, ", ".join(CONTROLS)))
        if field.get("type") not in DATA_TYPES:
            errors.append("%s: type must be one of %s" % (where, ", ".join(DATA_TYPES)))
        association = field.get("label_association")
        if association == HIDDEN_ASSOCIATION:
            if field.get("control") != "hidden":
                errors.append("%s: label_association n/a is only for hidden controls" % where)
        elif association not in LABEL_ASSOCIATIONS:
            errors.append("%s: label_association must be one of %s"
                          % (where, ", ".join(LABEL_ASSOCIATIONS)))
        if not isinstance(field.get("required"), bool):
            errors.append("%s: required must be a boolean" % where)
        if not isinstance(field.get("validation", []), list):
            errors.append("%s: validation must be an array" % where)
        for v, rule in enumerate(_list(field.get("validation"))):
            at = "%s.validation[%d]" % (where, v)
            if not isinstance(rule, dict) or rule.get("rule") not in VALIDATION_RULES \
                    or rule.get("where") not in WHERE:
                errors.append("%s: rule and where (client|server|both) are required" % at)
                continue
            if rule.get("enforcement", "reject") not in ENFORCEMENT:
                errors.append("%s: enforcement must be one of %s" % (at, ", ".join(ENFORCEMENT)))
            if rule["where"] == "both" and not _text(rule.get("client_source")):
                errors.append("%s: a rule enforced on both sides cites the client check too "
                              "(client_source)" % at)
    for i, image in enumerate(_list(screen.get("images"))):
        if not isinstance(image, dict) or "alt" not in image \
                or not (image["alt"] is None or isinstance(image["alt"], str)):
            errors.append("%s.images[%d]: alt must be stated, as a string or null" % (sid, i))
        elif not isinstance(image.get("decorative"), bool):
            errors.append("%s.images[%d]: decorative must be a boolean" % (sid, i))
    if "lang" not in screen or not (screen["lang"] is None or _text(screen["lang"])):
        errors.append("%s: lang must be stated, as a language code or null" % sid)
    for i, pair in enumerate(_list(screen.get("color_pairs"))):
        if not isinstance(pair, dict) or not all(
                isinstance(pair.get(k), str) and HEX_RE.match(pair[k]) for k in ("fg", "bg")):
            errors.append("%s.color_pairs[%d]: fg and bg must be 6-digit lowercase hex colors"
                          % (sid, i))
        elif pair.get("text", "normal") not in TEXT_SIZES:
            errors.append("%s.color_pairs[%d]: text must be normal or large" % (sid, i))
    for i, output in enumerate(_list(screen.get("outputs"))):
        if not isinstance(output, dict) or output.get("kind") not in OUTPUT_KINDS \
                or not _text(output.get("name")):
            errors.append("%s.outputs[%d]: name and kind are required" % (sid, i))
        elif not all(isinstance(f, str) for f in _list(output.get("fields"))):
            errors.append("%s.outputs[%d]: fields are field names" % (sid, i))
    for i, message in enumerate(_list(screen.get("messages"))):
        if not isinstance(message, dict) or message.get("kind") not in MESSAGE_KINDS \
                or not _text(message.get("text")):
            errors.append("%s.messages[%d]: kind and text are required" % (sid, i))

    # Rule 4 — every action resolves; Rule 6 (the action half) — senders carry a command.
    for i, action in enumerate(_list(screen.get("actions"))):
        where = "%s.actions[%d]" % (sid, i)
        if not isinstance(action, dict):
            errors.append("%s must be an object" % where)
            continue
        aid = action.get("id")
        m = ACTION_RE.match(aid) if isinstance(aid, str) else None
        if not m or m.group(1) != screen.get("id"):
            errors.append("%s: id must be %s.A<n>" % (where, screen.get("id")))
        if not _text(action.get("label")):
            errors.append("%s: label is required" % where)
        if action.get("kind") not in ACTION_KINDS:
            errors.append("%s: kind must be one of %s" % (where, ", ".join(ACTION_KINDS)))
        if action.get("scope", "screen") not in ACTION_SCOPES:
            errors.append("%s: scope must be screen or global" % where)
        for flag in ("destructive", "confirmation"):
            if not isinstance(action.get(flag), bool):
                errors.append("%s: %s must be a boolean" % (where, flag))
        target = action.get("target")
        if target is not None and (not isinstance(target, str) or target not in screen_ids):
            errors.append("%s: target %r is not a declared screen" % (where, target))
        if target is None and not _text(action.get("endpoint")) \
                and not _text(action.get("unresolved")):
            errors.append("%s: resolves to neither a target screen nor an endpoint, and says "
                          "nothing about why (unresolved)" % where)
        command = action.get("command")
        if command is not None and not _text(command):
            errors.append("%s: command must be a verb-first name or null" % where)
        if action.get("kind") in SENDING_KINDS:
            if not _text(command):
                errors.append("%s: a %s action changes something and must carry a command"
                              % (where, action["kind"]))
            if not isinstance(action.get("inputs"), list):
                errors.append("%s: a %s action lists the inputs it sends (inputs, possibly [])"
                              % (where, action["kind"]))
        for name in _list(action.get("inputs")):
            if not isinstance(name, str) or name not in names:
                errors.append("%s: sends %r, which is not an input of %s" % (where, name, sid))
        if "guard" in action and action["guard"] is not None:
            errors.extend(_validate_guard("%s: guard" % where, action["guard"], needs_roles=True))

    # Rule 5 (the screen half) — listed components are declared.
    for cid in _list(screen.get("components")):
        if not isinstance(cid, str) or cid not in component_ids:
            errors.append("%s: component %r is not declared" % (sid, cid))

    # Rule 7 — embedded logic is classified.
    for i, item in enumerate(_list(screen.get("embedded_logic"))):
        if not isinstance(item, dict) or item.get("kind") not in LOGIC_KINDS \
                or item.get("should_live_in") not in LOGIC_HOMES \
                or not _text(item.get("description")) or not _text(item.get("source")):
            errors.append("%s.embedded_logic[%d]: kind, should_live_in, description and source "
                          "are required" % (sid, i))
    return errors


def _screen_sources(screen, sid):
    """Rule 8 — every place a screen cites code. Elements that must carry a source yield it even
    when it is missing, so the checker reports the omission."""
    yield sid, screen.get("source")
    for i, handler in enumerate(_dicts(screen.get("handlers"))):
        yield "%s.handlers[%d]" % (sid, i), handler.get("source")
    access = screen.get("access") if isinstance(screen.get("access"), dict) else {}
    for i, guard in enumerate(_dicts(access.get("guards"))):
        yield "%s.access.guards[%d]" % (sid, i), guard.get("source")
    for key in ("inputs", "outputs", "actions", "messages", "embedded_logic", "images",
                "color_pairs"):
        for i, item in enumerate(_dicts(screen.get(key))):
            yield "%s.%s[%d]" % (sid, key, i), item.get("source")
            if key == "inputs":
                for v, rule in enumerate(_dicts(item.get("validation"))):
                    yield "%s.inputs[%d].validation[%d]" % (sid, i, v), rule.get("source")
                    if _text(rule.get("client_source")):
                        yield ("%s.inputs[%d].validation[%d].client_source" % (sid, i, v),
                               rule["client_source"])
            if key == "actions" and isinstance(item.get("guard"), dict):
                yield "%s.actions[%d].guard" % (sid, i), item["guard"].get("source")


# ----------------------------------------------------------------------------- manifest
def validate_inventory(inventory, project_dir=None, target_root=None, check_sources=True):
    """Every violation, as a list of one-line strings. Empty means the inventory is well-formed.

    `project_dir` locates the token file and the target; without it only the shape is checked.
    `check_sources=False` skips rule 8 — the metrics tool reads a validated inventory and has no
    reason to re-open the analysed codebase."""
    if not isinstance(inventory, dict):
        return ["%s: must be an object" % LABEL]
    if inventory.get("schema_version") != 1:
        return ["%s: schema_version must be 1" % LABEL]
    screens = inventory.get("screens")
    if not isinstance(screens, list) or not screens:
        return ["%s: screens must be a non-empty array" % LABEL]
    errors = []
    for key in ("project", "target_path"):
        if not _text(inventory.get(key)):
            errors.append("%s: %s is required" % (LABEL, key))
    for key in ("components", "features", "tasks"):
        if not isinstance(inventory.get(key, []), list):
            errors.append("%s: %s must be an array" % (LABEL, key))

    screen_objs = [s for s in screens if isinstance(s, dict)]
    components = _dicts(inventory.get("components"))
    features = _dicts(inventory.get("features"))
    tasks = _dicts(inventory.get("tasks"))
    screen_ids = {s.get("id") for s in screen_objs if _text(s.get("id"))}
    component_ids = {c.get("id") for c in components if _text(c.get("id"))}
    feature_ids = {f.get("id") for f in features if _text(f.get("id"))}

    # Rule 1 — unique ids, across every kind.
    for kind, items in (("screen", screen_objs), ("component", components),
                        ("feature", features)):
        if duplicates([i.get("id") for i in items]):
            errors.append("%s: duplicate %s id" % (LABEL, kind))
    if duplicates([t.get("name") for t in tasks]):
        errors.append("%s: duplicate task name" % LABEL)
    action_ids = [a.get("id") for s in screen_objs for a in _dicts(s.get("actions"))]
    if duplicates(action_ids):
        errors.append("%s: duplicate action id" % LABEL)

    for index, screen in enumerate(screens):
        if not isinstance(screen, dict):
            errors.append("%s: screens[%d] must be an object" % (LABEL, index))
            continue
        errors.extend(_validate_screen(screen, index, screen_ids, component_ids))
    # Rule 2 — navigation needs somewhere to start.
    if not any(s.get("entry") is True for s in screen_objs):
        errors.append("%s: no screen is an entry — depth and reachability cannot be measured"
                      % LABEL)

    # Rule 5 — component references agree both ways.
    listed_by = {}
    for screen in screen_objs:
        for cid in _list(screen.get("components")):
            if isinstance(cid, str) and isinstance(screen.get("id"), str):
                listed_by.setdefault(cid, set()).add(screen["id"])
    for index, component in enumerate(inventory.get("components") or []):
        if not isinstance(component, dict):
            errors.append("%s: components[%d] must be an object" % (LABEL, index))
            continue
        cid = component.get("id") if _text(component.get("id")) else "components[%d]" % index
        if not (isinstance(component.get("id"), str) and COMPONENT_RE.match(component["id"])):
            errors.append("%s: id must be UIC-###" % cid)
        if not _text(component.get("name")) or not _text(component.get("source")):
            errors.append("%s: name and source are required" % cid)
        if component.get("kind") not in COMPONENT_KINDS:
            errors.append("%s: kind must be one of %s" % (cid, ", ".join(COMPONENT_KINDS)))
        if component.get("level") not in LEVELS:
            errors.append("%s: level must be one of %s" % (cid, ", ".join(LEVELS)))
        used_by = component.get("used_by")
        if not isinstance(used_by, list):
            errors.append("%s: used_by must be an array" % cid)
            used_by = []
        declared = {u for u in used_by if isinstance(u, str)}
        actual = listed_by.get(component.get("id"), set()) \
            if isinstance(component.get("id"), str) else set()
        if declared != actual:
            errors.append("%s: used_by %s disagrees with the screens that list it %s"
                          % (cid, sorted(declared), sorted(actual)))
        if not actual and component.get("unused") is not True:
            errors.append("%s: no screen uses it — mark it unused: true" % cid)
        for other in _list(component.get("duplicates")):
            if not isinstance(other, str) or other not in component_ids \
                    or other == component.get("id"):
                errors.append("%s: duplicates names %r, which is not another declared component"
                              % (cid, other))
        if component.get("kind") in DUPLICATE_KINDS and not _list(component.get("duplicates")):
            errors.append("%s: an %s component names the component it rebuilds (duplicates)"
                          % (cid, component.get("kind")))

    # Rule 6 — commands and features agree.
    # Screens whose id is not a string are already reported (rule 1); leaving them out here keeps
    # the id sets below hashable instead of crashing on the malformed entry.
    named = [s for s in screen_objs if isinstance(s.get("id"), str)]
    actions = {a.get("id"): (s.get("id"), a)
               for s in named for a in _dicts(s.get("actions")) if _text(a.get("id"))}
    owners = {}
    commands = []
    for index, feature in enumerate(inventory.get("features") or []):
        if not isinstance(feature, dict):
            errors.append("%s: features[%d] must be an object" % (LABEL, index))
            continue
        fid = feature.get("id") if _text(feature.get("id")) else "features[%d]" % index
        if not (isinstance(feature.get("id"), str) and FEATURE_RE.match(feature["id"])):
            errors.append("%s: id must be UIF-###" % fid)
        if not _text(feature.get("name")) or not _text(feature.get("command")):
            errors.append("%s: name and command are required" % fid)
        commands.append(feature.get("command"))
        if not _texts(feature.get("actors")):
            errors.append("%s: actors must name who uses it (the union of its screens' roles)"
                          % fid)
        for entity, ops in (feature.get("entity_operations") or {}).items() \
                if isinstance(feature.get("entity_operations"), dict) else []:
            if not isinstance(ops, str) or not ops or not set(ops) <= CRUD:
                errors.append("%s: entity_operations[%r] must be letters of CRUD" % (fid, entity))
        cited = [a for a in _list(feature.get("actions")) if isinstance(a, str)]
        if not cited:
            errors.append("%s: cites no action" % fid)
        for aid in cited:
            if aid not in actions:
                errors.append("%s: action %r does not exist" % (fid, aid))
                continue
            owners.setdefault(aid, []).append(str(feature.get("id")))
            if actions[aid][1].get("command") != feature.get("command"):
                errors.append("%s: action %s carries command %r, not the feature's %r"
                              % (fid, aid, actions[aid][1].get("command"), feature.get("command")))
        expected = {actions[a][0] for a in cited if a in actions}
        stated = {s for s in _list(feature.get("screens")) if isinstance(s, str)}
        if stated != expected:
            errors.append("%s: screens %s are not the screens of its actions %s"
                          % (fid, sorted(stated), sorted(expected)))
    if duplicates([c for c in commands if _text(c)]):
        errors.append("%s: two features share a command — one command is one feature" % LABEL)
    for aid, (sid, action) in sorted(actions.items()):
        if _text(action.get("command")):
            count = len(owners.get(aid, []))
            if count != 1:
                errors.append("%s: action with command %r belongs to %d features — exactly one "
                              "is required" % (aid, action.get("command"), count))

    # Rule 10 — every feature is used in a walkable task.
    edges = {(s["id"], a.get("target")) for s in named for a in _dicts(s.get("actions"))
             if isinstance(a.get("target"), str)}
    action_screens = {f.get("id"): {actions[a][0] for a in _list(f.get("actions")) if a in actions}
                      for f in features}
    in_task = set()
    if features and not tasks:
        errors.append("%s: tasks must be declared — every feature is used in at least one task"
                      % LABEL)
    for index, task in enumerate(inventory.get("tasks") or []):
        if not isinstance(task, dict):
            errors.append("%s: tasks[%d] must be an object" % (LABEL, index))
            continue
        name = task.get("name") if _text(task.get("name")) else "tasks[%d]" % index
        if not _text(task.get("name")):
            errors.append("%s: name is required" % name)
        path = task.get("screens")
        if not isinstance(path, list) or not path:
            errors.append("task %s: screens must be the non-empty path a user walks" % name)
            path = []
        for sid in path:
            if not isinstance(sid, str) or sid not in screen_ids:
                errors.append("task %s: screen %r is not declared" % (name, sid))
        for a, b in zip(path, path[1:]):
            if (a, b) not in edges:
                errors.append("task %s: no declared transition leads from %s to %s" % (name, a, b))
        cited = _list(task.get("features"))
        if not cited:
            errors.append("task %s: names no feature" % name)
        for fid in cited:
            if not isinstance(fid, str) or fid not in feature_ids:
                errors.append("task %s: feature %r does not exist" % (name, fid))
                continue
            in_task.add(fid)
            if not action_screens.get(fid, set()) & {s for s in path if isinstance(s, str)}:
                errors.append("task %s: feature %s has no action on the task's path" % (name, fid))
    for fid in sorted(f for f in feature_ids if f not in in_task):
        if tasks:
            errors.append("%s: is used in no task" % fid)

    coverage = inventory.get("coverage")
    if not isinstance(coverage, dict):
        errors.append("%s: coverage must be an object" % LABEL)
    else:
        if coverage.get("screens") != len(screens):
            errors.append("%s: coverage.screens is %r but %d screens are declared"
                          % (LABEL, coverage.get("screens"), len(screens)))
        count = coverage.get("template_files")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            errors.append("%s: coverage.template_files must be the number of templates examined"
                          % LABEL)
        for i, item in enumerate(_list(coverage.get("unresolved"))):
            if not isinstance(item, dict) or not _text(item.get("ref")) \
                    or not _text(item.get("reason")):
                errors.append("%s: coverage.unresolved[%d] needs ref and reason" % (LABEL, i))
            elif not (isinstance(item.get("oq"), str) and OQ_RE.match(item["oq"])):
                errors.append("%s: coverage.unresolved[%d] cites the Open Question it became (oq)"
                              % (LABEL, i))

    # Rule 9 — the token file, and every component's references into it.
    leaves = None
    tokens_path = inventory.get("design_tokens")
    if not _text(tokens_path):
        errors.append("%s: design_tokens must name the token file" % LABEL)
    elif project_dir is not None:
        full = os.path.join(project_dir, tokens_path)
        try:
            with open(full, encoding="utf-8") as handle:
                tokens = json.load(handle)
        except (OSError, ValueError) as exc:
            errors.append("%s: design_tokens %r is unreadable — %s" % (LABEL, tokens_path, exc))
        else:
            token_errors, leaves = validate_tokens(tokens)
            errors.extend(token_errors)
    if leaves is not None:
        for component in components:
            for ref in _list(component.get("token_refs")):
                if ref not in leaves:
                    errors.append("%s: token_refs names %r, which is not a token"
                                  % (component.get("id"), ref))

    # Rule 8 — sources are real.
    if check_sources:
        root = resolve_target(inventory, project_dir, target_root)
        if project_dir is not None and root is not None and not os.path.isdir(root):
            errors.append("%s: target_path %r is not a directory — sources cannot be checked "
                          "(pass --target-root)" % (LABEL, root))
        else:
            checker = SourceChecker(root if project_dir is not None else None)
            cited = []
            for screen in screen_objs:
                cited.extend(_screen_sources(screen, screen.get("id")))
            for component in components:
                cited.append((str(component.get("id")), component.get("source")))
            if leaves is not None:
                cited.extend(token_sources(leaves))
            for where, source in cited:
                errors.extend(checker.check(where, source))
    return errors


def find_inventories(project_dir):
    return sorted(glob.glob(os.path.join(project_dir, INVENTORY_GLOB)))


def load_and_validate(project_dir, target_root=None):
    """[(path, inventory, errors)] — one per project under reports/before/."""
    results = []
    for path in find_inventories(project_dir):
        try:
            with open(path, encoding="utf-8") as handle:
                inventory = json.load(handle)
        except (OSError, ValueError) as exc:
            results.append((path, None, ["%s: unreadable — %s" % (LABEL, exc)]))
            continue
        results.append((path, inventory,
                        validate_inventory(inventory, project_dir, target_root)))
    return results


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    target_root = None
    for arg in argv[1:]:
        if arg.startswith("--target-root="):
            target_root = arg.split("=", 1)[1]
    project_dir = args[0] if args else "."
    results = load_and_validate(project_dir, target_root)
    if not results:
        print("no %s in %s — nothing to validate" % (LABEL, project_dir))
        return 0
    failed = 0
    for path, inventory, errors in results:
        rel = os.path.relpath(path, project_dir)
        for error in errors:
            print("%s: %s" % (rel, error))
        if errors:
            failed += len(errors)
        else:
            print("%s is well-formed (%d screens, %d components, %d features, %d tasks)"
                  % (rel, len(inventory["screens"]), len(inventory.get("components") or []),
                     len(inventory.get("features") or []), len(inventory.get("tasks") or [])))
    if failed:
        print("%d violation(s)" % failed)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
