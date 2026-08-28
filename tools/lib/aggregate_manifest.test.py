#!/usr/bin/env python3
"""Executable check of the aggregate design contract.

`/architect:design-aggregate` states seven well-formedness rules (@rules/aggregate-design.md §3)
and a concrete example per invariant. Prose cannot enforce either, so this asserts the validator
does: each case below is a model that reads perfectly well and is wrong, and the suite fails if
the validator would let it through.

    python3 tools/lib/aggregate_manifest.test.py

Exit 0 = all checks pass, 1 = at least one failed (the repo-wide convention).
"""

import copy
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aggregate_manifest import (MANIFEST_PATH,  # noqa: E402
                                load_and_validate,
                                validate_aggregate_manifest)

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
    errors = validate_aggregate_manifest(manifest)
    check(label, any(expect in error for error in errors),
          errors or "no violation reported")


def agg(m, i=0):
    return m["aggregates"][i]


# Two aggregates so that the cross-aggregate reference rule has something to point at:
# Order (root Order, interior OrderLine, value Money, reference to Customer) and Customer.
WELL_FORMED = {
    "schema_version": 1,
    "generated_at": "2026-08-28T00:00:00Z",
    "mode": "interactive",
    "aggregates": [
        {
            "id": "AGG-001",
            "name": "Order",
            "bounded_context": "Ordering",
            "document": "reports/03_design/aggregates/aggregate-order.md",
            "root": "Order",
            "members": [
                {"name": "Order", "kind": "root", "identity": "OrderId"},
                {"name": "OrderLine", "kind": "entity", "identity": "LineNo (local to Order)"},
                {"name": "Money", "kind": "value", "validation": "amount >= 0"},
                {"name": "customerId", "kind": "reference", "references": "Customer"},
            ],
            "invariants": [
                {"id": "INV-1", "statement": "total equals the sum of line totals",
                 "violated_by": ["addLine"],
                 "examples": [{"given": "two lines of 10", "when": "addLine(5)",
                               "then": "total 25, OrderLineAdded"}]},
            ],
            "commands": [
                {"name": "place", "creation": True, "actor": "Customer",
                 "guard": "cart has a line", "preserves": ["INV-1"],
                 "emits": "OrderPlaced", "consistency": "local"},
                {"name": "addLine", "actor": "Customer", "guard": "status is Draft",
                 "preserves": ["INV-1"], "emits": "OrderLineAdded", "consistency": "local"},
            ],
            "events": [
                {"name": "OrderPlaced", "payload": ["orderId"]},
                {"name": "OrderLineAdded", "payload": ["orderId", "lineNo"]},
            ],
            "specifications": [
                {"name": "CanBeShipped", "predicate": "every line allocated",
                 "used_by": ["ship"]},
            ],
            "repository": {"root": "Order", "lookups": ["byId"],
                           "loads_whole_aggregate": True},
            "state_machine": "STM-001",
        },
        {
            "id": "AGG-002",
            "name": "Customer",
            "bounded_context": "Customers",
            "document": "reports/03_design/aggregates/aggregate-customer.md",
            "root": "Customer",
            "members": [
                {"name": "Customer", "kind": "root", "identity": "CustomerId"},
                {"name": "Email", "kind": "value", "validation": "RFC 5322"},
            ],
            "invariants": [
                {"id": "INV-1", "statement": "email is unique per customer",
                 "violated_by": ["changeEmail"],
                 "examples": [{"given": "a customer", "when": "changeEmail(new)",
                               "then": "EmailChanged"}]},
            ],
            "commands": [
                {"name": "changeEmail", "actor": "Customer", "preserves": ["INV-1"],
                 "emits": "EmailChanged", "consistency": "local"},
            ],
            "events": [{"name": "EmailChanged", "payload": ["customerId"]}],
            "repository": {"root": "Customer", "lookups": ["byId"],
                           "loads_whole_aggregate": True},
        },
    ],
}


def main():
    print("the fixture itself is well-formed")
    check("no violation in the reference model",
          validate_aggregate_manifest(WELL_FORMED) == [],
          validate_aggregate_manifest(WELL_FORMED))

    print("rule 1 — exactly one root")

    def two_roots(m):
        agg(m)["members"][1]["kind"] = "root"
        return m
    rejects("two members declaring kind=root", two_roots, expect="exactly one root")
    rejects("no member declaring kind=root",
            lambda m: agg(m)["members"][0].update(kind="entity") or m,
            expect="exactly one root")
    rejects("root field disagreeing with the kind=root member",
            lambda m: agg(m).update(root="OrderLine") or m, expect="declares kind=root")

    print("rule 2 — at least one invariant, stated")
    rejects("an aggregate with no invariant",
            lambda m: agg(m).update(invariants=[]) or m, expect="non-empty array")
    rejects("an invariant with no statement",
            lambda m: agg(m)["invariants"][0].update(statement="") or m,
            expect="statement is required")

    print("rule 3 — every invariant protected by a command")
    rejects("an invariant no command can violate",
            lambda m: agg(m)["invariants"][0].update(violated_by=[]) or m,
            expect="at least one command that can violate")
    rejects("an invariant violated by an undeclared command",
            lambda m: agg(m)["invariants"][0].update(violated_by=["cancel"]) or m,
            expect="undeclared command")

    print("rule 4 — actor, consistency class and emitted event per command")
    rejects("a command with no actor",
            lambda m: agg(m)["commands"][1].update(actor="") or m, expect="actor is required")
    rejects("a command with an unknown consistency class",
            lambda m: agg(m)["commands"][1].update(consistency="eventual") or m,
            expect="consistency must be one of")
    rejects("a command emitting an undeclared event",
            lambda m: agg(m)["commands"][1].update(emits="OrderShipped") or m,
            expect="emits must name a declared event")
    rejects("a command preserving an undeclared invariant",
            lambda m: agg(m)["commands"][1].update(preserves=["INV-9"]) or m,
            expect="undeclared invariant")

    def emits_none(m):
        agg(m)["commands"][1]["emits"] = "none"
        return m
    check("a command may declare it emits none",
          validate_aggregate_manifest(emits_none(copy.deepcopy(WELL_FORMED))) == [])

    def two_creations(m):
        agg(m)["commands"][1]["creation"] = True
        return m
    rejects("two creation commands", two_creations, expect="at most one creates")

    print("rule 5 — interior reachable only through the root")
    rejects("a value object carrying an identity",
            lambda m: agg(m)["members"][2].update(identity="MoneyId") or m,
            expect="value object has no identity")
    rejects("a repository for an interior entity",
            lambda m: agg(m)["repository"].update(root="OrderLine") or m,
            expect="must be the aggregate root")

    print("rule 6 — other aggregates by identity only")

    def embeds_customer(m):
        agg(m)["members"][3] = {"name": "Customer", "kind": "entity", "identity": "CustomerId"}
        return m
    rejects("another aggregate's root embedded as an entity", embeds_customer,
            expect="another aggregate's root")
    rejects("a reference member naming no aggregate",
            lambda m: agg(m)["members"][3].update(references="") or m,
            expect="must name the aggregate it references")
    rejects("a member with an unknown kind",
            lambda m: agg(m)["members"][1].update(kind="service") or m,
            expect="kind must be one of")

    print("concrete examples")
    rejects("an invariant with no example",
            lambda m: agg(m)["invariants"][0].update(examples=[]) or m,
            expect="concrete example is required")
    rejects("an example missing its outcome",
            lambda m: agg(m)["invariants"][0]["examples"][0].update(then="") or m,
            expect="given/when/then")

    print("structural contracts")
    rejects("an id that is not AGG-###",
            lambda m: agg(m).update(id="A1") or m, expect="id must match")
    rejects("a state_machine link that is not STM-###",
            lambda m: agg(m).update(state_machine="order-machine") or m,
            expect="must match STM-###")
    rejects("a specification without a predicate",
            lambda m: agg(m)["specifications"][0].update(predicate="") or m,
            expect="states its predicate")
    rejects("duplicate invariant ids within one aggregate",
            lambda m: agg(m)["invariants"].append(dict(agg(m)["invariants"][0])) or m,
            expect="duplicate invariant id")

    def duplicate_aggregate(m):
        m["aggregates"].append(copy.deepcopy(agg(m)))
        return m
    rejects("two aggregates sharing an id", duplicate_aggregate, expect="duplicate id")
    rejects("a manifest with the wrong schema version",
            lambda m: m.update(schema_version=2) or m, expect="schema_version")
    rejects("a manifest with no aggregates",
            lambda m: m.update(aggregates=[]) or m, expect="non-empty array")

    print("the document contract, against a scratch project")
    root = tempfile.mkdtemp(prefix="aggregate-manifest-")
    try:
        docs = os.path.join(root, "reports", "03_design", "aggregates")
        os.makedirs(docs)
        for name in ("order", "customer"):
            with open(os.path.join(docs, "aggregate-%s.md" % name), "w") as fh:
                fh.write("---\ntitle: %s\n---\n# %s\n" % (name, name))
        with open(os.path.join(root, MANIFEST_PATH), "w") as fh:
            json.dump(WELL_FORMED, fh)
        manifest, errors = load_and_validate(root)
        check("a manifest whose documents exist validates clean", manifest and not errors, errors)

        empty = copy.deepcopy(WELL_FORMED)
        agg(empty)["document"] = "reports/03_design/aggregates/empty.md"
        open(os.path.join(docs, "empty.md"), "w").close()
        with open(os.path.join(root, MANIFEST_PATH), "w") as fh:
            json.dump(empty, fh)
        _, errors = load_and_validate(root)
        check("an empty document is a violation",
              any("non-empty file" in e for e in errors), errors)

        outside = copy.deepcopy(WELL_FORMED)
        agg(outside)["document"] = "../outside.md"
        with open(os.path.join(root, MANIFEST_PATH), "w") as fh:
            json.dump(outside, fh)
        _, errors = load_and_validate(root)
        check("a document outside the project is a violation",
              any("inside the project" in e for e in errors), errors)

        os.remove(os.path.join(root, MANIFEST_PATH))
        manifest, errors = load_and_validate(root)
        check("no manifest is not an error — the phase is optional",
              manifest is None and errors == [])
    finally:
        shutil.rmtree(root)

    print()
    print("%d check(s), %d failure(s)" % (CHECKS, FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
