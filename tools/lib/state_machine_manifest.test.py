#!/usr/bin/env python3
"""Executable check of the state transition model contract.

`/architect:design-state-machine` states seven well-formedness rules
(@rules/state-modeling.md §3) and a matrix with no blank cells. Prose cannot enforce either,
so this asserts the validator does: each case below is a model that reads perfectly well and
is wrong, and the suite fails if the validator would let it through.

    python3 tools/lib/state_machine_manifest.test.py

Exit 0 = all checks pass, 1 = at least one failed (the repo-wide convention).
"""

import copy
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state_machine_manifest import (MANIFEST_PATH,  # noqa: E402
                                    load_and_validate,
                                    validate_state_machine_manifest)

FAILURES = 0
CHECKS = 0


def check(label, condition, detail=""):
    global FAILURES, CHECKS
    CHECKS += 1
    print("  [%s] %s%s" % ("ok" if condition else "FAIL", label,
                           " — " + str(detail) if detail and not condition else ""))
    if not condition:
        FAILURES += 1


def rejects(label, mutate, *, expect):
    """Mutate the well-formed fixture and require the validator to name the defect."""
    manifest = mutate(copy.deepcopy(WELL_FORMED))
    errors = validate_state_machine_manifest(manifest)
    check(label, any(expect in error for error in errors),
          errors or "no violation reported")


# A minimal but complete order lifecycle: Draft -> Submitted -> {Approved, Rejected} -> Shipped.
# Every state x event pair is decided, so any check below fails only for the reason it names.
WELL_FORMED = {
    "schema_version": 1,
    "generated_at": "2026-08-27T00:00:00Z",
    "mode": "interactive",
    "machines": [{
        "id": "STM-001",
        "aggregate": "Order",
        "bounded_context": "Ordering",
        "document": "reports/03_design/state-machines/state-machine-order.md",
        "state_column": "status",
        "history": {"recorded": True, "store": "order_status_history"},
        "initial_state": "Draft",
        "terminal_states": ["Shipped", "Rejected"],
        "states": [
            {"name": "Draft", "kind": "initial", "invariant": "no stock reserved"},
            {"name": "Submitted", "invariant": "lines frozen"},
            {"name": "Approved", "invariant": "budget committed"},
            {"name": "Rejected", "kind": "terminal", "invariant": "no obligation"},
            {"name": "Shipped", "kind": "terminal", "invariant": "goods handed over"},
        ],
        "events": [
            {"name": "submit", "source": "command"},
            {"name": "approve", "source": "command"},
            {"name": "ship", "source": "command"},
        ],
        "transitions": [
            {"from": "Draft", "to": "Submitted", "event": "submit",
             "guard": "", "else": "", "effect": "freeze lines", "actor": "Customer",
             "consistency": "local", "idempotency": "ignore"},
            {"from": "Submitted", "to": "Approved", "event": "approve",
             "guard": "budget available", "else": "reject:no-budget",
             "effect": "commit budget", "actor": "Approver",
             "consistency": "distributed", "idempotency": "ignore"},
            {"from": "Submitted", "to": "Rejected", "event": "approve",
             "guard": "budget unavailable", "else": "reject:budget-check-failed",
             "effect": "notify requester", "actor": "Approver",
             "consistency": "local", "idempotency": "ignore"},
            {"from": "Approved", "to": "Shipped", "event": "ship",
             "guard": "", "else": "", "effect": "release stock", "actor": "Warehouse",
             "consistency": "saga", "idempotency": "ignore"},
        ],
        "matrix": [
            {"state": "Draft", "event": "submit", "verdict": "allow"},
            {"state": "Draft", "event": "approve", "verdict": "reject",
             "response": "order-not-submitted"},
            {"state": "Draft", "event": "ship", "verdict": "reject",
             "response": "order-not-approved"},
            {"state": "Submitted", "event": "submit", "verdict": "ignore",
             "response": "already submitted"},
            {"state": "Submitted", "event": "approve", "verdict": "allow"},
            {"state": "Submitted", "event": "ship", "verdict": "reject",
             "response": "order-not-approved"},
            {"state": "Approved", "event": "submit", "verdict": "ignore",
             "response": "already submitted"},
            {"state": "Approved", "event": "approve", "verdict": "ignore",
             "response": "already approved"},
            {"state": "Approved", "event": "ship", "verdict": "allow"},
            {"state": "Rejected", "event": "submit", "verdict": "reject",
             "response": "order-rejected"},
            {"state": "Rejected", "event": "approve", "verdict": "reject",
             "response": "order-rejected"},
            {"state": "Rejected", "event": "ship", "verdict": "reject",
             "response": "order-rejected"},
            {"state": "Shipped", "event": "submit", "verdict": "reject",
             "response": "order-shipped"},
            {"state": "Shipped", "event": "approve", "verdict": "reject",
             "response": "order-shipped"},
            {"state": "Shipped", "event": "ship", "verdict": "ignore",
             "response": "already shipped"},
        ],
    }],
}


def main():
    print("the fixture itself is well-formed")
    check("no violation in the reference model",
          validate_state_machine_manifest(WELL_FORMED) == [],
          validate_state_machine_manifest(WELL_FORMED))

    print("rule 1 — exactly one initial state")

    def two_initials(m):
        m["machines"][0]["states"][1]["kind"] = "initial"
        return m
    rejects("two states declaring kind=initial", two_initials, expect="kind=initial")
    rejects("initial_state that is not a declared state",
            lambda m: m["machines"][0].update(initial_state="Pending") or m,
            expect="initial_state")

    print("rule 2 — every state reachable")

    def unreachable(m):
        machine = m["machines"][0]
        machine["states"].append({"name": "Archived", "kind": "terminal", "invariant": "cold"})
        for event in ("submit", "approve", "ship"):
            machine["matrix"].append({"state": "Archived", "event": event, "verdict": "reject",
                                      "response": "order-archived"})
        return m
    rejects("a state nothing transitions into", unreachable, expect="unreachable")

    print("rule 3 — no undeclared dead end")
    rejects("a non-terminal state with no outgoing transition",
            lambda m: m["machines"][0].update(terminal_states=["Rejected"]) or m,
            expect="no outgoing transition")

    print("rule 4 — determinism")

    def unguarded_pair(m):
        m["machines"][0]["transitions"][1]["guard"] = ""
        m["machines"][0]["transitions"][1]["else"] = ""
        m["machines"][0]["transitions"][2]["guard"] = ""
        m["machines"][0]["transitions"][2]["else"] = ""
        return m
    rejects("two unguarded transitions on one (state, event)", unguarded_pair,
            expect="non-deterministic")

    def same_guard(m):
        m["machines"][0]["transitions"][2]["guard"] = \
            m["machines"][0]["transitions"][1]["guard"]
        return m
    rejects("two transitions whose guards are identical text", same_guard,
            expect="non-deterministic")

    print("rule 5 — a guard declares its else branch")
    rejects("guard with no else",
            lambda m: m["machines"][0]["transitions"][1].update(**{"else": ""}) or m,
            expect="else branch")

    print("rule 6 — actor and consistency class")
    rejects("transition with no actor",
            lambda m: m["machines"][0]["transitions"][0].update(actor="") or m,
            expect="actor is required")
    rejects("transition with an unknown consistency class",
            lambda m: m["machines"][0]["transitions"][0].update(consistency="eventual") or m,
            expect="consistency must be one of")
    rejects("transition with an unknown idempotency verdict",
            lambda m: m["machines"][0]["transitions"][0].update(idempotency="maybe") or m,
            expect="idempotency must be one of")
    # "allow" was a value once: firing a committed transition again is the (to, event) matrix
    # cell's decision, so a transition-level "allow" had no meaning and is rejected.
    rejects("transition claiming idempotency=allow",
            lambda m: m["machines"][0]["transitions"][0].update(idempotency="allow") or m,
            expect="idempotency must be one of")

    print("the matrix has no blank cell and does not disagree with the transitions")
    def drop_cell(m):
        m["machines"][0]["matrix"].pop(6)
        return m
    rejects("an undecided cell", drop_cell, expect="undecided")
    rejects("a duplicated cell",
            lambda m: m["machines"][0]["matrix"].append(
                {"state": "Draft", "event": "submit", "verdict": "reject"}) or m,
            expect="duplicate cell")
    rejects("an allow cell with no transition behind it",
            lambda m: m["machines"][0]["matrix"][1].update(verdict="allow") or m,
            expect="allows an event with no transition")
    rejects("a reject cell a transition contradicts",
            lambda m: m["machines"][0]["matrix"][0].update(verdict="reject") or m,
            expect="but a transition fires there")
    rejects("a cell naming an undeclared event",
            lambda m: m["machines"][0]["matrix"][0].update(event="withdraw") or m,
            expect="undeclared state or event")

    print("structural contracts")
    rejects("a transition leaving a declared terminal state",
            lambda m: m["machines"][0]["transitions"].append(
                {"from": "Shipped", "to": "Draft", "event": "submit", "guard": "", "else": "",
                 "effect": "reopen", "actor": "Admin", "consistency": "local",
                 "idempotency": "reject"}) or m,
            expect="leaves a declared terminal state")
    rejects("an id that is not STM-###",
            lambda m: m["machines"][0].update(id="SM1") or m, expect="id must match")
    rejects("an event with an unknown source",
            lambda m: m["machines"][0]["events"][0].update(source="magic") or m,
            expect="source: must be one of")

    def duplicate_machine(m):
        m["machines"].append(copy.deepcopy(m["machines"][0]))
        return m
    rejects("two machines sharing an id", duplicate_machine, expect="duplicate id")

    check("schema_version must be 1",
          validate_state_machine_manifest(dict(WELL_FORMED, schema_version=2)) != [])
    check("machines must be a non-empty array",
          validate_state_machine_manifest({"schema_version": 1, "machines": []}) != [])
    check("a non-object manifest is rejected",
          validate_state_machine_manifest([]) != [])

    print("document resolution against a real project directory")
    root = tempfile.mkdtemp(prefix="nexus-stm-")
    try:
        doc = os.path.join(root, "reports", "03_design", "state-machines",
                           "state-machine-order.md")
        os.makedirs(os.path.dirname(doc))
        with open(doc, "w", encoding="utf-8") as handle:
            handle.write("# State Transition Model: Order\n")
        with open(os.path.join(root, MANIFEST_PATH), "w", encoding="utf-8") as handle:
            json.dump(WELL_FORMED, handle)
        manifest, errors = load_and_validate(root)
        check("a well-formed manifest with its document on disk passes", errors == [], errors)
        check("the manifest is returned to the caller", manifest is not None)

        escaping = copy.deepcopy(WELL_FORMED)
        escaping["machines"][0]["document"] = "../../../etc/hosts"
        check("a document outside the project is rejected",
              any("document" in e for e in
                  validate_state_machine_manifest(escaping, root)))

        empty = copy.deepcopy(WELL_FORMED)
        empty["machines"][0]["document"] = "reports/03_design/state-machines/empty.md"
        open(os.path.join(root, "reports", "03_design", "state-machines", "empty.md"),
             "w").close()
        check("an empty document is rejected",
              any("document" in e for e in validate_state_machine_manifest(empty, root)))

        os.remove(os.path.join(root, MANIFEST_PATH))
        manifest, errors = load_and_validate(root)
        check("a project with no manifest is not an error — the phase is optional",
              manifest is None and errors == [], errors)

        with open(os.path.join(root, MANIFEST_PATH), "w", encoding="utf-8") as handle:
            handle.write("{ not json")
        manifest, errors = load_and_validate(root)
        check("unreadable JSON is reported, not raised", manifest is None and errors, errors)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print()
    print("%d check(s), %d failure(s)" % (CHECKS, FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
