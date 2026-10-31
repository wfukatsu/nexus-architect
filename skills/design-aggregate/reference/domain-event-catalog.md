# Domain Event Catalog — shape, field contracts and projection frontmatter

Read by `design-aggregate` Stage 6 and auto-mode step 5 before writing
`reports/03_design/domain-event-catalog.json` and its `.md` projection. The judgment rules the
validator cannot check (who counts as a consumer, orphans, key ownership) are in the skill body
§ Domain Event Catalog; this file holds the shape and what `tools/lib/domain_event_catalog.py` enforces.

## Shape

```json
{
  "schema_version": 1,
  "generated_at": "ISO8601",
  "contexts": ["Ordering", "Inventory", "Payment"],
  "events": [
    {
      "name": "OrderPlaced",
      "scope": "published",
      "publisher": { "aggregate": "Order", "bounded_context": "Ordering" },
      "consumers": [
        { "bounded_context": "Inventory", "relationship": "customer-supplier",
          "purpose": "reserve stock for every line" },
        { "bounded_context": "Payment", "relationship": "customer-supplier",
          "purpose": "authorize the order total" }
      ],
      "payload": ["orderId", "customerId", "lines[].productId", "lines[].quantity", "total"],
      "delivery": "at-least-once",
      "idempotency_key": "orderId",
      "version": 1,
      "evolution": "additive-only"
    },
    {
      "name": "OrderLineAdded",
      "scope": "internal",
      "publisher": { "aggregate": "Order", "bounded_context": "Ordering" },
      "consumers": [],
      "payload": ["orderId", "lineNo", "productId", "quantity"]
    }
  ],
  "orphan_events": [
    { "name": "PointsEarned", "named_in": "reports/03_design/bounded-contexts-redesign.md",
      "reason": "LoyaltyAccount was not modeled — CTX-006 is a candidate context (OQ-008)" }
  ]
}
```

## Field contracts

Field contracts the validator enforces (`tools/lib/domain_event_catalog.py`; every one is a case
in its contract test):

- **Catalog** — `schema_version: 1`; `events` non-empty; names unique (one event, one entry);
  `contexts`, when present, lists the bounded contexts the design knows.
- **Event** — `name` PascalCase; `publisher` names an aggregate and its `bounded_context`, and
  when the aggregate manifest exists the aggregate **declares** that event and lives in that
  context; `scope` ∈ `internal` | `published`; `payload` a non-empty list of field names —
  identities and values, never another aggregate's interior.
- **Consumers** — each names a declared `bounded_context` other than the publisher's (a reaction
  inside one context is not published), a `relationship` from the context map's vocabulary
  (`partnership` | `shared-kernel` | `customer-supplier` | `conformist` | `anticorruption-layer` |
  `open-host-service` | `published-language` | `separate-ways`) and its `purpose`; no context
  twice. A `published` event has at least one; an `internal` event has none — the scope is what
  the consumers say. A consumer is an **asynchronous subscriber**: a context that receives the
  event as the reply to a command it issued (the calling service reading `PaymentDeclined` as
  the response to `charge`) is not a consumer, and that event stays `internal` — when
  `api-style-decisions.json` / `asyncapi/` already classify the exchange, they win over prose in
  the design documents. A consumer that is still a **candidate** context (its `CTX-` carries an
  open `OQ-`) is listed, added to `contexts`, and flagged `"candidate": true`; the event's
  scope is what it would be if the candidate is confirmed.
- **Orphans** — an event the design documents name that no aggregate in the manifest declares
  (an entity that was never modeled) is not silently dropped: list it under the catalog's
  `orphan_events` with the document that names it, and in the `.md` Open Items. An event named
  only in another spelling (a state-machine transition `reservation_expired`) is listed in
  PascalCase with the source spelling in `named_in`. The validator accepts the list; a re-run
  that models the aggregate moves the event into `events`.
- **Delivery contract** (`published` only) — `delivery` ∈ `at-least-once` | `at-most-once` |
  `exactly-once`, an `idempotency_key` whenever delivery is at-least-once, an integer
  `version` ≥ 1 and an `evolution` rule ∈ `additive-only` | `versioned` | `frozen`. The key
  must be unique **per event type**: two events of one aggregate sharing `orderId` as their key
  (`OrderCancelled` and `PaymentDeclined` for the same order) collide in a consumer's inbox —
  scope it (`orderId` + event type, or a dedicated `eventId`), and check `review-risk` /
  `review-consistency` findings before copying a key from the context map. Ownership is split
  and one-directional: the key's **value** is this catalog's (`design-api` copies it, never
  re-derives it); the **dedup rule** a consumer applies — `(eventType, key)` or the bare key — is
  the contract's, decided by `design-api` and recorded as its ADR. A colliding value is therefore
  fixed here (catalog first, then the contract follows on its next run) and, until then, recorded
  as an Open Item owned by `design-aggregate`; `design-api` may close the gap on its side by
  making the dedup pair explicit, never by changing the value.
- **Completeness** — every event an aggregate declares has a catalog entry. An event the
  manifest emits and the catalog omits is a contract nobody wrote down.

## Projection frontmatter

The `.md` projection's frontmatter:

```yaml
---
title: "Domain Event Catalog"
schema_version: 1
phase: "Phase 3: Design"
skill: design-aggregate
completed_by: design-microservices   # only when that skill completed the consumer side
generated_at: "ISO8601"
mode: "interactive|auto"
input_files:
  - reports/03_design/aggregates/aggregate-manifest.json
  - reports/03_design/context-map.md
---
```
