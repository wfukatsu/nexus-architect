"""Validation for the aggregate models `/architect:design-aggregate` emits.

`reports/03_design/aggregates/aggregate-manifest.json` is the canonical model — the per-aggregate
Markdown is its projection — so the well-formedness rules of @rules/aggregate-design.md §3 are
checked here rather than trusted to prose. Every rule below is one a hand-written aggregate gets
wrong in a way no reader notices: two roots, an aggregate with no invariant (a table with a class
name), an invariant no command can violate, a command with no actor or no consistency class, a
member that is really another aggregate's root, a repository for an interior entity, an invariant
nobody tried on both sides of its boundary.

Usage:  python3 tools/lib/aggregate_manifest.py <project_dir>   (exit 1 on violations)
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manifest_common import (CONSISTENCY, MAX_DOCUMENT_BYTES,  # noqa: E402,F401
                             duplicates, inside_file, load_manifest, report)

MANIFEST_PATH = os.path.join("reports", "03_design", "aggregates", "aggregate-manifest.json")
STATE_MACHINE_MANIFEST_PATH = os.path.join("reports", "03_design", "state-machines",
                                           "state-machine-manifest.json")
LABEL = "aggregate manifest"
ID_RE = re.compile(r"^AGG-\d{3,}$")
STM_RE = re.compile(r"^STM-\d{3,}$")
MEMBER_KINDS = ("root", "entity", "value", "reference")
# Every invariant is tried on both sides of its boundary: a case it lets through and a case
# it rejects. One side alone has not located the boundary (@rules/aggregate-design.md §5).
EXAMPLE_KINDS = ("positive", "negative")
NO_EVENT = "none"


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _names(items, key="name"):
    return [i.get(key) for i in items if isinstance(i, dict)]


def validate_aggregate(aggregate, project_dir, index, all_roots, known_machines=None):
    label = aggregate.get("id") if _text(aggregate.get("id")) else "aggregate[%d]" % index
    errors = []

    if not ID_RE.match(str(aggregate.get("id", ""))):
        errors.append("%s: id must match AGG-###" % label)
    if not _text(aggregate.get("name")):
        errors.append("%s: name is required" % label)
    if not _text(aggregate.get("document")):
        errors.append("%s.document: path is required" % label)
    elif project_dir is not None and not inside_file(project_dir, aggregate.get("document")):
        errors.append("%s.document: non-empty file must resolve inside the project" % label)
    stm = aggregate.get("state_machine")
    if stm is not None:
        if not STM_RE.match(str(stm)):
            errors.append("%s.state_machine: must match STM-### when present" % label)
        elif known_machines is not None and stm not in known_machines:
            errors.append("%s.state_machine: %s is not a machine in %s"
                          % (label, stm, STATE_MACHINE_MANIFEST_PATH))

    members = aggregate.get("members")
    invariants = aggregate.get("invariants")
    commands = aggregate.get("commands")
    events = aggregate.get("events")
    for name, value in (("members", members), ("invariants", invariants),
                        ("commands", commands)):
        if not isinstance(value, list) or not value:
            errors.append("%s.%s: must be a non-empty array" % (label, name))
    if not isinstance(events, list):
        errors.append("%s.events: must be an array" % label)
        events = []
    if not isinstance(members, list) or not isinstance(invariants, list) \
            or not isinstance(commands, list):
        return errors

    member_names = _names(members)
    if duplicates(member_names):
        errors.append("%s: duplicate member name" % label)

    # Rule 1 — exactly one root, and it is the declared `root`.
    root = aggregate.get("root")
    if not _text(root):
        errors.append("%s: root is required" % label)
    roots = [m.get("name") for m in members if isinstance(m, dict) and m.get("kind") == "root"]
    if len(roots) != 1:
        errors.append("%s: %d members declare kind=root; exactly one root is required"
                      % (label, len(roots)))
    elif roots[0] != root:
        errors.append("%s: root is %r but %r declares kind=root" % (label, root, roots[0]))

    other_roots = {r for r in all_roots if _text(r) and r != root}
    for member in members:
        if not isinstance(member, dict):
            errors.append("%s.members: entry must be an object" % label)
            continue
        where = "%s.member %s" % (label, member.get("name"))
        if not _text(member.get("name")):
            errors.append("%s: name is required" % where)
        if member.get("kind") not in MEMBER_KINDS:
            errors.append("%s: kind must be one of %s" % (where, "/".join(MEMBER_KINDS)))
        # Rule 6 — another aggregate's root inside this boundary is held by ID, or it is a
        # boundary defect. A `reference` member says which aggregate it points at.
        if member.get("kind") == "reference":
            if not _text(member.get("references")):
                errors.append("%s: reference member must name the aggregate it references"
                              % where)
        elif member.get("name") in other_roots:
            errors.append("%s: is another aggregate's root — reference it by identity "
                          "(kind=reference)" % where)
        # Rule 5 — a value object with an identity is an entity in disguise; an interior
        # entity's identity is local to the root.
        if member.get("kind") == "value" and _text(member.get("identity")):
            errors.append("%s: a value object has no identity" % where)

    # Events — named, unique — before commands can emit them and invariants can name them.
    event_names = []
    for event in events:
        if not isinstance(event, dict) or not _text(event.get("name")):
            errors.append("%s.events: every event is an object with a name" % label)
            continue
        event_names.append(event["name"])
    if duplicates(event_names):
        errors.append("%s: duplicate event name" % label)

    command_names = [c.get("name") for c in commands if isinstance(c, dict) and _text(c.get("name"))]
    if duplicates(command_names):
        errors.append("%s: duplicate command name" % label)
    invariant_ids = [i.get("id") for i in invariants if isinstance(i, dict) and _text(i.get("id"))]
    if duplicates(invariant_ids):
        errors.append("%s: duplicate invariant id" % label)

    creations = 0
    for command in commands:
        if not isinstance(command, dict):
            errors.append("%s.commands: entry must be an object" % label)
            continue
        where = "%s.command %s" % (label, command.get("name"))
        if not _text(command.get("name")):
            errors.append("%s: name is required" % where)
        # Rule 4 — actor, consistency class, emitted event (or none).
        if not _text(command.get("actor")):
            errors.append("%s: actor is required" % where)
        if command.get("consistency") not in CONSISTENCY:
            errors.append("%s: consistency must be one of %s" % (where, "/".join(CONSISTENCY)))
        emits = command.get("emits")
        if not _text(emits) or (emits != NO_EVENT and emits not in event_names):
            errors.append("%s: emits must name a declared event or be %r" % (where, NO_EVENT))
        preserves = command.get("preserves")
        if not isinstance(preserves, list):
            errors.append("%s: preserves must be an array of invariant ids" % where)
        else:
            for inv in preserves:
                if inv not in invariant_ids:
                    errors.append("%s: preserves undeclared invariant %r" % (where, inv))
        if command.get("creation") is True:
            creations += 1
    if creations > 1:
        errors.append("%s: %d commands carry creation=true; at most one creates the aggregate"
                      % (label, creations))

    # Rules 2 and 3 — at least one invariant, each stated, violable by a declared command,
    # and tried on both sides of its boundary.
    for invariant in invariants:
        if not isinstance(invariant, dict):
            errors.append("%s.invariants: entry must be an object" % label)
            continue
        where = "%s.invariant %s" % (label, invariant.get("id"))
        if not _text(invariant.get("id")):
            errors.append("%s: id is required" % where)
        if not _text(invariant.get("statement")):
            errors.append("%s: statement is required" % where)
        violated_by = invariant.get("violated_by")
        if not isinstance(violated_by, list) or not violated_by:
            errors.append("%s: must name at least one command that can violate it" % where)
        else:
            for name in violated_by:
                if name not in command_names:
                    errors.append("%s: violated_by names undeclared command %r" % (where, name))
        examples = invariant.get("examples")
        if not isinstance(examples, list) or not examples:
            errors.append("%s: at least one concrete example per side is required" % where)
            continue
        kinds = set()
        for example in examples:
            if not isinstance(example, dict) or not all(
                    _text(example.get(k)) for k in ("given", "when", "then")):
                errors.append("%s: every example needs given/when/then" % where)
                break
            if example.get("kind") not in EXAMPLE_KINDS:
                errors.append("%s: every example is kind positive or negative" % where)
                break
            kinds.add(example["kind"])
        else:
            missing = [k for k in EXAMPLE_KINDS if k not in kinds]
            if missing:
                errors.append("%s: needs a %s example — the boundary has one side untried"
                              % (where, " and a ".join(missing)))

    # The repository — one per root, and for the root only (rule 5).
    repository = aggregate.get("repository")
    if not isinstance(repository, dict):
        errors.append("%s.repository: must be an object" % label)
    elif repository.get("root") != root:
        errors.append("%s.repository.root: must be the aggregate root %r, not %r"
                      % (label, root, repository.get("root")))

    for spec in aggregate.get("specifications") or []:
        if not isinstance(spec, dict) or not _text(spec.get("predicate")):
            errors.append("%s.specifications: every specification states its predicate" % label)
            break
    return errors


def validate_aggregate_manifest(manifest, project_dir=None, known_machines=None):
    """Every violation, as a list of one-line strings. Empty means the model is well-formed.

    `known_machines` is the set of `STM-` ids the state-machine manifest declares, when that
    manifest exists; None skips the cross-check (the link is validated by shape only)."""
    if not isinstance(manifest, dict):
        return ["%s: must be an object" % LABEL]
    if manifest.get("schema_version") != 1:
        return ["%s: schema_version must be 1" % LABEL]
    aggregates = manifest.get("aggregates")
    if not isinstance(aggregates, list) or not aggregates:
        return ["%s: aggregates must be a non-empty array" % LABEL]

    errors = []
    objects = [a for a in aggregates if isinstance(a, dict)]
    for key in ("id", "name", "document", "root"):
        if duplicates([a.get(key) for a in objects]):
            errors.append("%s: duplicate %s" % (LABEL, key))
    all_roots = [a.get("root") for a in objects]
    for index, aggregate in enumerate(aggregates):
        if not isinstance(aggregate, dict):
            errors.append("%s: aggregates[%d] must be an object" % (LABEL, index))
            continue
        errors.extend(validate_aggregate(aggregate, project_dir, index, all_roots,
                                         known_machines))
    return errors


def _known_machines(project_dir):
    """The STM- ids the project's state-machine manifest declares, or None when it has none —
    the aggregate skill runs first, so an absent machine manifest is the normal case."""
    path = os.path.join(project_dir, STATE_MACHINE_MANIFEST_PATH)
    if not os.path.isfile(path):
        return None
    try:
        import json
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    machines = data.get("machines") if isinstance(data, dict) else None
    if not isinstance(machines, list):
        return None
    return {m.get("id") for m in machines if isinstance(m, dict) and _text(m.get("id"))}


def load_and_validate(project_dir):
    """(manifest, errors) for a project directory; a missing manifest is (None, [])."""
    known = _known_machines(project_dir)
    return load_manifest(project_dir, MANIFEST_PATH, LABEL,
                         lambda manifest, root: validate_aggregate_manifest(manifest, root, known))


def main(argv):
    project_dir = argv[1] if len(argv) > 1 else "."
    manifest, errors = load_and_validate(project_dir)
    return report(manifest, errors, project_dir, LABEL, "aggregates")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
