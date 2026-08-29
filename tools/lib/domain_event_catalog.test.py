#!/usr/bin/env python3
"""Contract test for `domain_event_catalog.py` — the Published Language rules stated in
`skills/design-aggregate/SKILL.md` § Domain Event Catalog, each with a well-formed case and the
defect it rejects. Exit 1 on any failure."""

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import domain_event_catalog as C  # noqa: E402

checks = failures = 0


def check(label, condition, detail=""):
    global checks, failures
    checks += 1
    if condition:
        print("  ok    %s" % label)
    else:
        failures += 1
        print("  FAIL  %s%s" % (label, (" — %s" % detail) if detail else ""))


MANIFEST = {
    "schema_version": 1,
    "aggregates": [
        {"id": "AGG-001", "name": "Order", "bounded_context": "Ordering",
         "events": [{"name": "OrderPlaced"}, {"name": "OrderLineAdded"}]},
        {"id": "AGG-002", "name": "StockItem", "bounded_context": "Inventory",
         "events": [{"name": "StockReserved"}]},
    ],
}


def published(name="OrderPlaced", aggregate="Order", context="Ordering", consumer="Inventory",
              **overrides):
    event = {
        "name": name, "scope": "published",
        "publisher": {"aggregate": aggregate, "bounded_context": context},
        "consumers": [{"bounded_context": consumer, "relationship": "customer-supplier",
                       "purpose": "reserve stock for the order"}],
        "payload": ["orderId", "customerId", "lines"],
        "delivery": "at-least-once", "idempotency_key": "orderId",
        "version": 1, "evolution": "additive-only",
    }
    event.update(overrides)
    return event


def internal(name="OrderLineAdded"):
    return {"name": name, "scope": "internal",
            "publisher": {"aggregate": "Order", "bounded_context": "Ordering"},
            "consumers": [], "payload": ["orderId", "lineNo"]}


def catalog(*events, **extra):
    data = {"schema_version": 1, "events": list(events)}
    data.update(extra)
    return data


FULL = catalog(published(), internal(),
               published("StockReserved", "StockItem", "Inventory", "Ordering"))


def errs(cat, manifest=MANIFEST):
    return C.validate_catalog(cat, manifest)


print("A complete, well-formed catalog passes")
check("against the aggregate manifest", errs(FULL) == [], errs(FULL))
check("by shape alone, without a manifest", errs(FULL, None) == [], errs(FULL, None))

print("Envelope")
check("not an object", any("object" in e for e in errs([])))
check("schema_version must be 1", any("schema_version" in e for e in errs({"schema_version": 2, "events": [1]})))
check("events non-empty", any("non-empty" in e for e in errs(catalog())))
check("contexts, when present, is a list of names",
      any("contexts" in e for e in errs(catalog(*FULL["events"], contexts="Ordering"))))

print("One event, one publisher, and the publisher declares it")
two = catalog(published(), published(), internal(), published("StockReserved", "StockItem", "Inventory", "Ordering"))
check("duplicate event name", any("one publisher" in e for e in errs(two)))
wrong = copy.deepcopy(FULL)
wrong["events"][0]["publisher"]["aggregate"] = "StockItem"
check("publisher must be the declaring aggregate", any("aggregate manifest says" in e for e in errs(wrong)), errs(wrong))
wrong = copy.deepcopy(FULL)
wrong["events"][0]["publisher"]["bounded_context"] = "Inventory"
check("publisher context must be the aggregate's", any("lives in" in e for e in errs(wrong)), errs(wrong))
ghost = catalog(*FULL["events"], published("Ghost", "Order", "Ordering"))
check("an event no aggregate declares", any("no aggregate" in e for e in errs(ghost)), errs(ghost))
check("publisher must name aggregate and context",
      any("publisher must name" in e for e in errs(catalog(published(publisher={"aggregate": "Order"})))))

print("Completeness against the aggregate manifest")
short = catalog(published(), internal())
check("an aggregate event the catalog omits", any("omits" in e and "StockReserved" in e for e in errs(short)), errs(short))
check("no manifest → completeness not checked", not any("omits" in e for e in errs(short, None)))

print("Scope and consumers")
e = errs(catalog(*FULL["events"][1:], published(consumers=[])))
check("published with no consumer is internal", any("with none it is internal" in e_ for e_ in e), e)
e = errs(catalog(*FULL["events"][:1], published("StockReserved", "StockItem", "Inventory", "Ordering"),
                 {**internal(), "consumers": [{"bounded_context": "Inventory", "relationship": "conformist", "purpose": "x"}]}))
check("internal with a consumer is published", any("with consumers it is published" in e_ for e_ in e), e)
e = errs(catalog(*FULL["events"][1:], published(consumer="Ordering")))
check("the publishing context cannot be its own consumer", any("publishing context" in e_ for e_ in e), e)
e = errs(catalog(*FULL["events"][1:], published(consumer="Shipping")))
check("a consumer must be a declared context", any("not a declared bounded context" in e_ for e_ in e), e)
listed = catalog(*FULL["events"][1:], published(consumer="Shipping"), contexts=["Shipping"])
check("…unless the catalog's contexts list declares it", not any("not a declared" in e_ for e_ in errs(listed)), errs(listed))
e = errs(catalog(*FULL["events"][1:], published(consumers=[
    {"bounded_context": "Inventory", "relationship": "customer-supplier", "purpose": "a"},
    {"bounded_context": "Inventory", "relationship": "conformist", "purpose": "b"}])))
check("a consumer listed twice", any("twice" in e_ for e_ in e), e)
e = errs(catalog(*FULL["events"][1:], published(consumers=[{"bounded_context": "Inventory", "relationship": "friends", "purpose": "a"}])))
check("relationship is a context-map pattern", any("relationship" in e_ for e_ in e), e)
e = errs(catalog(*FULL["events"][1:], published(consumers=[{"bounded_context": "Inventory", "relationship": "conformist"}])))
check("a consumer states its purpose", any("purpose" in e_ for e_ in e), e)
check("scope is internal or published", any("scope" in e for e in errs(catalog(*FULL["events"][1:], published(scope="global")))))

print("Delivery contract of a published event")
check("delivery is one of the three", any("delivery" in e for e in errs(catalog(*FULL["events"][1:], published(delivery="whenever")))))
check("at-least-once needs an idempotency key",
      any("idempotency_key" in e for e in errs(catalog(*FULL["events"][1:], published(idempotency_key="")))))
check("at-most-once does not", not any("idempotency_key" in e for e in
      errs(catalog(*FULL["events"][1:], published(delivery="at-most-once", idempotency_key="")))))
check("evolution is declared", any("evolution" in e for e in errs(catalog(*FULL["events"][1:], published(evolution="yolo")))))
check("version is an integer >= 1", any("version" in e for e in errs(catalog(*FULL["events"][1:], published(version="1")))))
check("payload is a non-empty list of names", any("payload" in e for e in errs(catalog(*FULL["events"][1:], published(payload=[])))))
check("name is PascalCase", any("PascalCase" in e for e in errs(catalog(*FULL["events"][1:], published(name="order placed")))))
check("an internal event needs no delivery contract", not any("delivery" in e or "evolution" in e for e in errs(FULL)))

print("Malformed shapes are reported, not raised")
for junk in ([1, 2], {"schema_version": 1, "events": [None, "x", {"name": 3, "publisher": [], "consumers": "no", "payload": "p"}]}):
    try:
        out = C.validate_catalog(junk, {"aggregates": "nope"})
        check("junk %r → violations" % type(junk).__name__, isinstance(out, list) and out)
    except Exception as exc:  # noqa: BLE001
        check("junk %r → violations" % type(junk).__name__, False, repr(exc))

print("CLI envelope")
tmp = tempfile.mkdtemp()
try:
    r = subprocess.run([sys.executable, C.__file__, tmp], capture_output=True, text=True)
    check("no catalog → exit 0", r.returncode == 0, r.stdout)
    os.makedirs(os.path.join(tmp, "reports", "03_design", "aggregates"))
    with open(os.path.join(tmp, C.AGGREGATE_MANIFEST_PATH), "w", encoding="utf-8") as f:
        json.dump(MANIFEST, f)
    with open(os.path.join(tmp, C.CATALOG_PATH), "w", encoding="utf-8") as f:
        json.dump(short, f)
    r = subprocess.run([sys.executable, C.__file__, tmp], capture_output=True, text=True)
    check("incomplete catalog → exit 1 naming the omitted event", r.returncode == 1 and "StockReserved" in r.stdout, r.stdout)
    with open(os.path.join(tmp, C.CATALOG_PATH), "w", encoding="utf-8") as f:
        json.dump(FULL, f)
    r = subprocess.run([sys.executable, C.__file__, tmp], capture_output=True, text=True)
    check("complete catalog → exit 0 with a summary", r.returncode == 0 and "3 events" in r.stdout, r.stdout)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("%d check(s), %d failure(s)" % (checks, failures))
sys.exit(1 if failures else 0)
