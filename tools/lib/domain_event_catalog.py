"""Validation for the Domain Event Catalog `/architect:design-aggregate` emits and
`/architect:design-microservices` completes.

`reports/03_design/domain-event-catalog.json` is the Published Language of the context map: every
domain event the aggregates declare, who publishes it, who consumes it across which relationship,
and the delivery contract a consumer may rely on. The rules that keep it honest are checked here
rather than trusted to two skills' prose: one publisher per event and that publisher really
declares it; the catalog complete against the aggregate manifest (an event an aggregate emits but
the catalog omits is a contract nobody wrote down); consumers that are declared contexts other
than the publisher's; and for every published event a delivery guarantee, an idempotency key and
a payload of identities and values — never another aggregate's interior.

Usage:  python3 tools/lib/domain_event_catalog.py <project_dir>   (exit 1 on violations)
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manifest_common import duplicates, load_manifest, report  # noqa: E402

CATALOG_PATH = os.path.join("reports", "03_design", "domain-event-catalog.json")
AGGREGATE_MANIFEST_PATH = os.path.join("reports", "03_design", "aggregates",
                                       "aggregate-manifest.json")
LABEL = "domain event catalog"
SCOPES = ("internal", "published")
DELIVERY = ("at-least-once", "at-most-once", "exactly-once")
RELATIONSHIPS = ("partnership", "shared-kernel", "customer-supplier", "conformist",
                 "anticorruption-layer", "open-host-service", "published-language",
                 "separate-ways")
EVOLUTION = ("additive-only", "versioned", "frozen")
NAME_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def aggregate_events(aggregate_manifest):
    """{event name: (aggregate name, bounded context)} and the set of declared contexts, read from
    the aggregate manifest; (None, None) when it is absent or unusable."""
    if not isinstance(aggregate_manifest, dict):
        return None, None
    aggregates = aggregate_manifest.get("aggregates")
    if not isinstance(aggregates, list):
        return None, None
    declared, contexts = {}, set()
    for agg in aggregates:
        if not isinstance(agg, dict):
            continue
        if _text(agg.get("bounded_context")):
            contexts.add(agg["bounded_context"])
        for event in agg.get("events") if isinstance(agg.get("events"), list) else []:
            if isinstance(event, dict) and _text(event.get("name")):
                declared.setdefault(event["name"], (agg.get("name"), agg.get("bounded_context")))
    return declared, contexts


def validate_catalog(catalog, aggregate_manifest=None):
    """Every violation as a one-line string; empty means well-formed. `aggregate_manifest` is the
    parsed aggregate manifest when the project has one — then publishers and completeness are
    cross-checked; None validates the catalog by shape alone."""
    if not isinstance(catalog, dict):
        return ["%s: must be an object" % LABEL]
    if catalog.get("schema_version") != 1:
        return ["%s: schema_version must be 1" % LABEL]
    events = catalog.get("events")
    if not isinstance(events, list):
        return ["%s: events must be an array" % LABEL]

    errors = []
    declared, manifest_contexts = aggregate_events(aggregate_manifest)
    contexts = set(manifest_contexts or ())
    listed = catalog.get("contexts")
    if listed is not None:
        if not isinstance(listed, list) or not all(_text(c) for c in listed):
            errors.append("%s: contexts must be an array of names" % LABEL)
        else:
            contexts |= set(listed)

    names = [e.get("name") for e in events if isinstance(e, dict) and _text(e.get("name"))]
    if duplicates(names):
        errors.append("%s: duplicate event name — one event, one entry, one publisher" % LABEL)
    # The contexts a consumer may name: the aggregate manifest's and the catalog's own list.
    # A publisher's context is deliberately NOT added — a misspelt publisher would otherwise
    # legitimise the same misspelling as a consumer. With neither source the check is skipped.
    known_contexts = contexts if (manifest_contexts or listed) else None

    for index, event in enumerate(events):
        if not isinstance(event, dict):
            errors.append("%s: events[%d] must be an object" % (LABEL, index))
            continue
        name = event.get("name")
        where = "event %s" % (name if _text(name) else "[%d]" % index)
        if not _text(name) or not NAME_RE.match(name):
            errors.append("%s: name must be a PascalCase identifier" % where)
        publisher = event.get("publisher")
        if not isinstance(publisher, dict) or not _text(publisher.get("aggregate")) \
                or not _text(publisher.get("bounded_context")):
            errors.append("%s: publisher must name an aggregate and its bounded_context" % where)
            publisher = {}
        elif declared is not None and _text(name):
            owner = declared.get(name)
            if owner is None:
                errors.append("%s: no aggregate in %s declares it"
                              % (where, AGGREGATE_MANIFEST_PATH))
            elif owner[0] != publisher["aggregate"]:
                errors.append("%s: publisher is %r but the aggregate manifest says %r"
                              % (where, publisher["aggregate"], owner[0]))
            elif _text(owner[1]) and owner[1] != publisher["bounded_context"]:
                errors.append("%s: publisher context is %r but aggregate %r lives in %r"
                              % (where, publisher["bounded_context"], owner[0], owner[1]))
        if known_contexts is not None and _text(publisher.get("bounded_context")) \
                and publisher["bounded_context"] not in known_contexts:
            errors.append("%s: publisher context %r is not a declared bounded context"
                          % (where, publisher["bounded_context"]))

        scope = event.get("scope")
        if scope not in SCOPES:
            errors.append("%s: scope must be one of %s" % (where, "/".join(SCOPES)))
        payload = event.get("payload")
        if not isinstance(payload, list) or not payload or not all(_text(p) for p in payload):
            errors.append("%s: payload must be a non-empty array of field names" % where)

        consumers = event.get("consumers")
        if not isinstance(consumers, list):
            errors.append("%s: consumers must be an array" % where)
            consumers = []
        if scope == "published" and not consumers:
            errors.append("%s: a published event names at least one consuming context — "
                          "with none it is internal" % where)
        if scope == "internal" and consumers:
            errors.append("%s: an internal event has no consuming context — "
                          "with consumers it is published" % where)
        seen = set()
        for consumer in consumers:
            if not isinstance(consumer, dict) or not _text(consumer.get("bounded_context")):
                errors.append("%s: every consumer names its bounded_context" % where)
                continue
            ctx = consumer["bounded_context"]
            if ctx == publisher.get("bounded_context"):
                errors.append("%s: consumer %r is the publishing context — a reaction inside "
                              "one context is not a published event" % (where, ctx))
            if ctx in seen:
                errors.append("%s: consumer %r listed twice" % (where, ctx))
            seen.add(ctx)
            if consumer.get("relationship") not in RELATIONSHIPS:
                errors.append("%s: consumer %r relationship must be one of %s"
                              % (where, ctx, "/".join(RELATIONSHIPS)))
            if not _text(consumer.get("purpose")):
                errors.append("%s: consumer %r states its purpose" % (where, ctx))
            if "candidate" in consumer and not isinstance(consumer["candidate"], bool):
                errors.append("%s: consumer %r candidate must be true or false" % (where, ctx))
        if scope == "published":
            if event.get("delivery") not in DELIVERY:
                errors.append("%s: delivery must be one of %s" % (where, "/".join(DELIVERY)))
            if event.get("delivery") == "at-least-once" and not _text(event.get("idempotency_key")):
                errors.append("%s: at-least-once delivery requires an idempotency_key" % where)
            if event.get("evolution") not in EVOLUTION:
                errors.append("%s: evolution must be one of %s" % (where, "/".join(EVOLUTION)))
            version = event.get("version")
            if not (isinstance(version, int) and not isinstance(version, bool) and version >= 1):
                errors.append("%s: version must be an integer >= 1" % where)

    # The consumers are contexts the design knows: the aggregate manifest's, the catalog's own
    # `contexts` list, or a publisher's. A consumer nobody declared is a typo or a context that
    # was never designed.
    for event in events if known_contexts is not None else []:
        if not isinstance(event, dict):
            continue
        for consumer in event.get("consumers") if isinstance(event.get("consumers"), list) else []:
            if isinstance(consumer, dict) and _text(consumer.get("bounded_context")) \
                    and consumer["bounded_context"] not in known_contexts:
                errors.append("event %s: consumer %r is not a declared bounded context"
                              % (event.get("name"), consumer["bounded_context"]))

    # Orphans: events the design names but no aggregate declares — listed, not dropped.
    orphans = catalog.get("orphan_events")
    if orphans is not None:
        if not isinstance(orphans, list):
            errors.append("%s: orphan_events must be an array" % LABEL)
        else:
            for orphan in orphans:
                if not isinstance(orphan, dict) or not _text(orphan.get("name")) \
                        or not _text(orphan.get("named_in")):
                    errors.append("%s: every orphan event names itself and the document that "
                                  "names it (named_in)" % LABEL)
                    break
                if declared is not None and orphan["name"] in declared:
                    errors.append("%s: orphan event %s is declared by aggregate %s — it belongs in "
                                  "events" % (LABEL, orphan["name"], declared[orphan["name"]][0]))
                if orphan["name"] in names:
                    errors.append("%s: orphan event %s is also a catalog event" % (LABEL, orphan["name"]))

    # Completeness: every event an aggregate declares has a catalog entry.
    if declared is not None:
        missing = sorted(set(declared) - {n for n in names if _text(n)})
        for name in missing:
            errors.append("%s: aggregate %s declares event %s, which the catalog omits"
                          % (LABEL, declared[name][0], name))
    return errors


def _aggregate_manifest(project_dir):
    """(manifest, error). Absent is (None, None) — the cross-checks are skipped. Present but
    unreadable is (None, message): the cross-checks cannot run, and saying nothing would report
    a catalog as well-formed against a manifest nobody could read."""
    path = os.path.join(project_dir, AGGREGATE_MANIFEST_PATH)
    if not os.path.isfile(path):
        return None, None
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle), None
    except (OSError, ValueError) as exc:
        return None, "%s: %s is unreadable, so publishers and completeness were not " \
                     "cross-checked — %s" % (LABEL, AGGREGATE_MANIFEST_PATH, exc)


def load_and_validate(project_dir):
    """(catalog, errors) for a project directory; a missing catalog is (None, [])."""
    manifest, manifest_error = _aggregate_manifest(project_dir)
    catalog, errors = load_manifest(project_dir, CATALOG_PATH, LABEL,
                                    lambda cat, root: validate_catalog(cat, manifest))
    if catalog is not None and manifest_error:
        errors = [manifest_error] + errors
    return catalog, errors


def main(argv):
    project_dir = argv[1] if len(argv) > 1 else "."
    catalog, errors = load_and_validate(project_dir)
    return report(catalog, errors, project_dir, LABEL, "events")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
