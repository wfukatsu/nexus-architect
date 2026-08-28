"""Validation for the aggregate models `/architect:design-aggregate` emits.

`reports/03_design/aggregates/aggregate-manifest.json` is the canonical model — the per-aggregate
Markdown is its projection — so the well-formedness rules of @rules/aggregate-design.md §3 are
checked here rather than trusted to prose. Every rule below is one a hand-written aggregate gets
wrong in a way no reader notices: two roots, an aggregate with no invariant (a table with a class
name), an invariant no command can violate, a command with no actor or no consistency class, a
member that is really another aggregate's root, a repository for an interior entity, an invariant
nobody tried an example against.

Usage:  python3 tools/lib/aggregate_manifest.py <project_dir>   (exit 1 on violations)
"""

import json
import os
import re
import sys

MANIFEST_PATH = os.path.join("reports", "03_design", "aggregates", "aggregate-manifest.json")
MAX_DOCUMENT_BYTES = 4 * 1024 * 1024
ID_RE = re.compile(r"^AGG-\d{3,}$")
STM_RE = re.compile(r"^STM-\d{3,}$")
MEMBER_KINDS = ("root", "entity", "value", "reference")
CONSISTENCY = ("local", "distributed", "saga")
NO_EVENT = "none"


def _inside_file(project_dir, relative):
    """A declared document must be a non-empty file that stays inside the project."""
    if not isinstance(relative, str) or not relative.strip():
        return False
    root = os.path.realpath(project_dir) + os.sep
    path = os.path.realpath(os.path.join(project_dir, relative))
    if not path.startswith(root) or not os.path.isfile(path):
        return False
    size = os.path.getsize(path)
    return 0 < size <= MAX_DOCUMENT_BYTES


def _names(items, key="name"):
    return [i.get(key) for i in items if isinstance(i, dict)]


def validate_aggregate(aggregate, project_dir, index, all_roots):
    label = aggregate.get("id") or aggregate.get("name") or "aggregate[%d]" % index
    errors = []

    if not ID_RE.match(str(aggregate.get("id", ""))):
        errors.append("%s: id must match AGG-###" % label)
    if not str(aggregate.get("name", "")).strip():
        errors.append("%s: name is required" % label)
    if project_dir is not None and not _inside_file(project_dir, aggregate.get("document")):
        errors.append("%s.document: non-empty file must resolve inside the project" % label)
    stm = aggregate.get("state_machine")
    if stm is not None and not STM_RE.match(str(stm)):
        errors.append("%s.state_machine: must match STM-### when present" % label)

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
    if len(set(member_names)) != len(member_names):
        errors.append("%s: duplicate member name" % label)

    # Rule 1 — exactly one root, and it is the declared `root`.
    root = aggregate.get("root")
    roots = [m.get("name") for m in members if isinstance(m, dict) and m.get("kind") == "root"]
    if len(roots) != 1:
        errors.append("%s: %d members declare kind=root; exactly one root is required"
                      % (label, len(roots)))
    elif roots[0] != root:
        errors.append("%s: root is %r but %r declares kind=root" % (label, root, roots[0]))

    other_roots = {r for r in all_roots if r and r != root}
    for member in members:
        if not isinstance(member, dict):
            errors.append("%s.members: entry must be an object" % label)
            continue
        where = "%s.member %s" % (label, member.get("name"))
        if member.get("kind") not in MEMBER_KINDS:
            errors.append("%s: kind must be one of %s" % (where, "/".join(MEMBER_KINDS)))
        # Rule 6 — another aggregate's root inside this boundary is held by ID, or it is a
        # boundary defect. A `reference` member says which aggregate it points at.
        if member.get("kind") == "reference":
            if not str(member.get("references", "")).strip():
                errors.append("%s: reference member must name the aggregate it references"
                              % where)
        elif member.get("name") in other_roots:
            errors.append("%s: is another aggregate's root — reference it by identity "
                          "(kind=reference)" % where)
        # Rule 5 — a value object with an identity is an entity in disguise; an interior
        # entity's identity is local to the root.
        if member.get("kind") == "value" and str(member.get("identity", "")).strip():
            errors.append("%s: a value object has no identity" % where)

    # Commands and events, before invariants can point at them.
    command_names = _names(commands)
    event_names = _names(events)
    if len(set(command_names)) != len(command_names):
        errors.append("%s: duplicate command name" % label)
    if len(set(event_names)) != len(event_names):
        errors.append("%s: duplicate event name" % label)
    invariant_ids = _names(invariants, "id")
    if len(set(invariant_ids)) != len(invariant_ids):
        errors.append("%s: duplicate invariant id" % label)

    creations = 0
    for command in commands:
        if not isinstance(command, dict):
            errors.append("%s.commands: entry must be an object" % label)
            continue
        where = "%s.command %s" % (label, command.get("name"))
        if not str(command.get("name", "")).strip():
            errors.append("%s: name is required" % where)
        # Rule 4 — actor, consistency class, emitted event (or none).
        if not str(command.get("actor", "")).strip():
            errors.append("%s: actor is required" % where)
        if command.get("consistency") not in CONSISTENCY:
            errors.append("%s: consistency must be one of %s" % (where, "/".join(CONSISTENCY)))
        emits = command.get("emits")
        if emits != NO_EVENT and emits not in event_names:
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
    # and tried against at least one example.
    for invariant in invariants:
        if not isinstance(invariant, dict):
            errors.append("%s.invariants: entry must be an object" % label)
            continue
        where = "%s.invariant %s" % (label, invariant.get("id"))
        if not str(invariant.get("id", "")).strip():
            errors.append("%s: id is required" % where)
        if not str(invariant.get("statement", "")).strip():
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
            errors.append("%s: at least one concrete example is required" % where)
        else:
            for example in examples:
                if not isinstance(example, dict) or not all(
                        str(example.get(k, "")).strip() for k in ("given", "when", "then")):
                    errors.append("%s: every example needs given/when/then" % where)
                    break

    # The repository — one per root, and for the root only (rule 5).
    repository = aggregate.get("repository")
    if not isinstance(repository, dict):
        errors.append("%s.repository: must be an object" % label)
    elif repository.get("root") != root:
        errors.append("%s.repository.root: must be the aggregate root %r, not %r"
                      % (label, root, repository.get("root")))

    for spec in aggregate.get("specifications") or []:
        if not isinstance(spec, dict) or not str(spec.get("predicate", "")).strip():
            errors.append("%s.specifications: every specification states its predicate" % label)
            break
    return errors


def validate_aggregate_manifest(manifest, project_dir=None):
    """Every violation, as a list of one-line strings. Empty means the model is well-formed."""
    if not isinstance(manifest, dict):
        return ["aggregate manifest: must be an object"]
    if manifest.get("schema_version") != 1:
        return ["aggregate manifest: schema_version must be 1"]
    aggregates = manifest.get("aggregates")
    if not isinstance(aggregates, list) or not aggregates:
        return ["aggregate manifest: aggregates must be a non-empty array"]

    errors = []
    ids = [a.get("id") for a in aggregates if isinstance(a, dict)]
    names = [a.get("name") for a in aggregates if isinstance(a, dict)]
    documents = [a.get("document") for a in aggregates if isinstance(a, dict)]
    for values, what in ((ids, "id"), (names, "name"), (documents, "document")):
        if len(set(values)) != len(values):
            errors.append("aggregate manifest: duplicate %s" % what)
    all_roots = [a.get("root") for a in aggregates if isinstance(a, dict)]
    for index, aggregate in enumerate(aggregates):
        if not isinstance(aggregate, dict):
            errors.append("aggregate manifest: aggregates[%d] must be an object" % index)
            continue
        errors.extend(validate_aggregate(aggregate, project_dir, index, all_roots))
    return errors


def load_and_validate(project_dir):
    """(manifest, errors) for a project directory. A missing manifest is not an error here —
    the phase is optional, and a project that never modeled an aggregate has nothing to check."""
    path = os.path.join(project_dir, MANIFEST_PATH)
    if not os.path.isfile(path):
        return None, []
    try:
        with open(path, encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError) as exc:
        return None, ["aggregate manifest: unreadable — %s" % exc]
    return manifest, validate_aggregate_manifest(manifest, project_dir)


def main(argv):
    project_dir = argv[1] if len(argv) > 1 else "."
    manifest, errors = load_and_validate(project_dir)
    if manifest is None and not errors:
        print("no aggregate manifest in %s — nothing to validate" % project_dir)
        return 0
    for error in errors:
        print(error)
    if errors:
        print("%d violation(s)" % len(errors))
        return 1
    print("aggregate manifest is well-formed (%d aggregate(s))"
          % len(manifest.get("aggregates", [])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
