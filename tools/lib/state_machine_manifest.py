"""Validation for the state transition models `/architect:design-state-machine` emits.

`reports/03_design/state-machines/state-machine-manifest.json` is the canonical model — the
per-aggregate Markdown is its projection — so the well-formedness rules of
@rules/state-modeling.md §3 are checked here rather than trusted to prose. Every rule below is
one a hand-written state machine gets wrong in a way no reader notices: a state nothing can
reach, a non-terminal state nothing leaves, two unguarded transitions on one `(state, event)`
pair, a guard whose false branch was never decided, a matrix cell left blank so the runtime
decides it instead.

Usage:  python3 tools/lib/state_machine_manifest.py <project_dir>   (exit 1 on violations)
"""

import json
import os
import re
import sys

MANIFEST_PATH = os.path.join("reports", "03_design", "state-machines",
                             "state-machine-manifest.json")
MAX_DOCUMENT_BYTES = 4 * 1024 * 1024
ID_RE = re.compile(r"^STM-\d{3,}$")
EVENT_SOURCES = ("command", "event", "timeout", "schedule")
CONSISTENCY = ("local", "distributed", "saga")
IDEMPOTENCY = ("allow", "ignore", "reject")
VERDICTS = ("allow", "reject", "ignore", "defer")


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


def _reachable(initial, transitions):
    seen, frontier = {initial}, [initial]
    while frontier:
        current = frontier.pop()
        for transition in transitions:
            if transition.get("from") == current and transition.get("to") not in seen:
                seen.add(transition.get("to"))
                frontier.append(transition.get("to"))
    return seen


def validate_machine(machine, project_dir, index):
    label = machine.get("id") or machine.get("aggregate") or "machine[%d]" % index
    errors = []

    if not ID_RE.match(str(machine.get("id", ""))):
        errors.append("%s: id must match STM-### " % label)
    if not str(machine.get("aggregate", "")).strip():
        errors.append("%s: aggregate is required" % label)
    if project_dir is not None and not _inside_file(project_dir, machine.get("document")):
        errors.append("%s.document: non-empty file must resolve inside the project" % label)

    states = machine.get("states")
    events = machine.get("events")
    transitions = machine.get("transitions")
    matrix = machine.get("matrix")
    for name, value in (("states", states), ("events", events),
                        ("transitions", transitions), ("matrix", matrix)):
        if not isinstance(value, list) or not value:
            errors.append("%s.%s: must be a non-empty array" % (label, name))
    if errors and (not isinstance(states, list) or not isinstance(transitions, list)):
        return errors

    state_names = [s.get("name") for s in states if isinstance(s, dict)]
    event_names = [e.get("name") for e in events if isinstance(e, dict)] \
        if isinstance(events, list) else []
    if len(set(state_names)) != len(state_names):
        errors.append("%s: duplicate state name" % label)
    if len(set(event_names)) != len(event_names):
        errors.append("%s: duplicate event name" % label)
    for event in events if isinstance(events, list) else []:
        if isinstance(event, dict) and event.get("source") not in EVENT_SOURCES:
            errors.append("%s.events[%s].source: must be one of %s"
                          % (label, event.get("name"), "/".join(EVENT_SOURCES)))

    # Rule 1 — exactly one initial state, and it is a declared state.
    initial = machine.get("initial_state")
    if initial not in state_names:
        errors.append("%s.initial_state: %r is not a declared state" % (label, initial))
    declared_initial = [s.get("name") for s in states
                        if isinstance(s, dict) and s.get("kind") == "initial"]
    if len(declared_initial) > 1:
        errors.append("%s: %d states declare kind=initial; exactly one initial state is allowed"
                      % (label, len(declared_initial)))
    if declared_initial and declared_initial[0] != initial:
        errors.append("%s: initial_state is %r but %r declares kind=initial"
                      % (label, initial, declared_initial[0]))

    terminal = machine.get("terminal_states") or []
    if not isinstance(terminal, list):
        errors.append("%s.terminal_states: must be an array" % label)
        terminal = []
    for name in terminal:
        if name not in state_names:
            errors.append("%s.terminal_states: %r is not a declared state" % (label, name))

    seen_pairs = {}
    for transition in transitions:
        if not isinstance(transition, dict):
            errors.append("%s.transitions: entry must be an object" % label)
            continue
        source, target = transition.get("from"), transition.get("to")
        event = transition.get("event")
        where = "%s.transition %s -[%s]-> %s" % (label, source, event, target)
        if source not in state_names:
            errors.append("%s: 'from' is not a declared state" % where)
        if target not in state_names:
            errors.append("%s: 'to' is not a declared state" % where)
        if event not in event_names:
            errors.append("%s: event is not declared" % where)
        if source in terminal:
            errors.append("%s: leaves a declared terminal state" % where)
        # Rule 6 — an actor and a consistency class, or the transition is not designed yet.
        if not str(transition.get("actor", "")).strip():
            errors.append("%s: actor is required" % where)
        if transition.get("consistency") not in CONSISTENCY:
            errors.append("%s: consistency must be one of %s" % (where, "/".join(CONSISTENCY)))
        if transition.get("idempotency") not in IDEMPOTENCY:
            errors.append("%s: idempotency must be one of %s" % (where, "/".join(IDEMPOTENCY)))
        # Rule 5 — a guard whose false branch nobody decided is the defect this catches.
        guard = str(transition.get("guard") or "").strip()
        if guard and not str(transition.get("else") or "").strip():
            errors.append("%s: guarded transition must declare its else branch" % where)
        seen_pairs.setdefault((source, event), []).append(guard)

    # Rule 4 — determinism. Two transitions on one (state, event) need stated guards; two
    # unguarded ones, or two with the same guard text, are a coin flip at runtime.
    for (source, event), guards in sorted(seen_pairs.items(), key=lambda kv: str(kv[0])):
        if len(guards) < 2:
            continue
        if any(not guard for guard in guards) or len(set(guards)) != len(guards):
            errors.append("%s: transitions on (%s, %s) are non-deterministic — each needs a "
                          "distinct, stated guard" % (label, source, event))

    # Rules 2 and 3 — reachability and dead ends.
    if initial in state_names:
        reachable = _reachable(initial, transitions)
        for name in state_names:
            if name not in reachable:
                errors.append("%s: state %r is unreachable from %r" % (label, name, initial))
    outgoing = {t.get("from") for t in transitions if isinstance(t, dict)}
    for name in state_names:
        if name not in outgoing and name not in terminal:
            errors.append("%s: state %r has no outgoing transition and is not declared terminal"
                          % (label, name))

    # The matrix — every state x event pair decided exactly once, and every `allow` backed by a
    # real transition. A blank cell is a decision the runtime makes instead of the designer.
    if isinstance(matrix, list) and state_names and event_names:
        cells = {}
        for cell in matrix:
            if not isinstance(cell, dict):
                errors.append("%s.matrix: entry must be an object" % label)
                continue
            key = (cell.get("state"), cell.get("event"))
            if key[0] not in state_names or key[1] not in event_names:
                errors.append("%s.matrix: cell (%s, %s) names an undeclared state or event"
                              % (label, key[0], key[1]))
                continue
            if key in cells:
                errors.append("%s.matrix: duplicate cell (%s, %s)" % (label, key[0], key[1]))
            cells[key] = cell.get("verdict")
            if cell.get("verdict") not in VERDICTS:
                errors.append("%s.matrix: cell (%s, %s) verdict must be one of %s"
                              % (label, key[0], key[1], "/".join(VERDICTS)))
        allowed = {(t.get("from"), t.get("event")) for t in transitions if isinstance(t, dict)}
        for state in state_names:
            for event in event_names:
                key = (state, event)
                if key not in cells:
                    errors.append("%s.matrix: cell (%s, %s) is undecided" % (label, state, event))
                    continue
                if cells[key] == "allow" and key not in allowed:
                    errors.append("%s.matrix: cell (%s, %s) allows an event with no transition"
                                  % (label, state, event))
                if cells[key] != "allow" and key in allowed:
                    errors.append("%s.matrix: cell (%s, %s) is %r but a transition fires there"
                                  % (label, state, event, cells[key]))
    return errors


def validate_state_machine_manifest(manifest, project_dir=None):
    """Every violation, as a list of one-line strings. Empty means the model is well-formed."""
    if not isinstance(manifest, dict):
        return ["state machine manifest: must be an object"]
    if manifest.get("schema_version") != 1:
        return ["state machine manifest: schema_version must be 1"]
    machines = manifest.get("machines")
    if not isinstance(machines, list) or not machines:
        return ["state machine manifest: machines must be a non-empty array"]

    errors = []
    ids = [m.get("id") for m in machines if isinstance(m, dict)]
    aggregates = [m.get("aggregate") for m in machines if isinstance(m, dict)]
    documents = [m.get("document") for m in machines if isinstance(m, dict)]
    for values, what in ((ids, "id"), (aggregates, "aggregate"), (documents, "document")):
        if len(set(values)) != len(values):
            errors.append("state machine manifest: duplicate %s" % what)
    for index, machine in enumerate(machines):
        if not isinstance(machine, dict):
            errors.append("state machine manifest: machines[%d] must be an object" % index)
            continue
        errors.extend(validate_machine(machine, project_dir, index))
    return errors


def load_and_validate(project_dir):
    """(manifest, errors) for a project directory. A missing manifest is not an error here —
    the phase is optional, and a project that never modeled a lifecycle has nothing to check."""
    path = os.path.join(project_dir, MANIFEST_PATH)
    if not os.path.isfile(path):
        return None, []
    try:
        with open(path, encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError) as exc:
        return None, ["state machine manifest: unreadable — %s" % exc]
    return manifest, validate_state_machine_manifest(manifest, project_dir)


def main(argv):
    project_dir = argv[1] if len(argv) > 1 else "."
    manifest, errors = load_and_validate(project_dir)
    if manifest is None and not errors:
        print("no state machine manifest in %s — nothing to validate" % project_dir)
        return 0
    for error in errors:
        print(error)
    if errors:
        print("%d violation(s)" % len(errors))
        return 1
    print("state machine manifest is well-formed (%d machine(s))"
          % len(manifest.get("machines", [])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
