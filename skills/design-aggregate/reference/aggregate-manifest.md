# Aggregate manifest — shape and field contracts

Read by `design-aggregate` Stage 6 and auto-mode step 5 before writing
`reports/03_design/aggregates/aggregate-manifest.json`. The Markdown documents are projections of
this file; it is never authored from them.

## Shape

```json
{
  "schema_version": 1,
  "generated_at": "ISO8601",
  "mode": "interactive",
  "aggregates": [
    {
      "id": "AGG-001",
      "name": "Order",
      "bounded_context": "Ordering",
      "document": "reports/03_design/aggregates/aggregate-order.md",
      "root": "Order",
      "members": [
        { "name": "Order", "kind": "root", "identity": "OrderId" },
        { "name": "OrderLine", "kind": "entity", "identity": "LineNo (local to Order)" },
        { "name": "Money", "kind": "value", "validation": "amount >= 0, ISO 4217 currency" },
        { "name": "customerId", "kind": "reference", "references": "Customer" }
      ],
      "invariants": [
        {
          "id": "INV-1",
          "statement": "total equals the sum of line totals",
          "violated_by": ["addLine", "removeLine"],
          "examples": [
            { "kind": "positive", "given": "two lines of 10 EUR", "when": "addLine(5 EUR)", "then": "total 25 EUR, OrderLineAdded" },
            { "kind": "negative", "given": "submitted order", "when": "addLine(5 EUR)", "then": "rejected: order-not-editable" }
          ]
        }
      ],
      "commands": [
        {
          "name": "place",
          "creation": true,
          "actor": "Customer",
          "guard": "cart has at least one line",
          "preserves": ["INV-1"],
          "emits": "OrderPlaced",
          "consistency": "local"
        },
        {
          "name": "addLine",
          "actor": "Customer",
          "guard": "status is Draft",
          "preserves": ["INV-1"],
          "emits": "OrderLineAdded",
          "consistency": "local",
          "also_writes": []
        }
      ],
      "events": [
        { "name": "OrderPlaced", "payload": ["orderId", "customerId", "total"] },
        { "name": "OrderLineAdded", "payload": ["orderId", "lineNo", "productId", "quantity"] }
      ],
      "specifications": [
        { "name": "CanBeShipped", "predicate": "status is Approved and every line is allocated",
          "used_by": ["ship", "shippable-orders query"] }
      ],
      "repository": {
        "root": "Order",
        "lookups": ["byId", "byCustomerAndStatus"],
        "loads_whole_aggregate": true
      },
      "state_machine": "STM-001"
    }
  ]
}
```

## Field contracts

Field contracts the validator enforces (`tools/lib/aggregate_manifest.py`; every one is also a
case in its contract test):

- **Manifest** — `schema_version: 1`; `aggregates` non-empty; `id`, `name`, `document` and `root`
  each unique across aggregates (two aggregates claiming one root is one aggregate drawn twice).
- **Aggregate** — `id` matches `AGG-###`; `name` and `root` present; `document` a non-empty file
  inside the project; `members`, `invariants`, `commands` non-empty arrays; `events` an array;
  `state_machine`, when present, matches `STM-###` **and** names a machine the state-machine
  manifest declares when that manifest exists (it is written by `design-state-machine`, see below).
- **Members** — names present and unique; exactly one `kind: root` whose `name` equals `root`;
  `kind` ∈ `root` | `entity` | `value` | `reference`; a `reference` names the aggregate it
  `references`; a member named after another aggregate's root without `kind: reference` is the
  rule-6 defect; a `value` carries no `identity` (a value object with identity is an entity).
- **Events** — every entry an object with a unique `name`.
- **Commands** — names unique; each has an `actor`, a `consistency` ∈ `local` | `distributed` |
  `saga`, an `emits` naming a declared event or the literal `none`, and a `preserves` list of
  declared invariant IDs; at most one carries `creation: true`; `also_writes`, when present, lists
  other aggregates in this manifest the command writes in the same transaction (never itself).
- **Events** — an event name is published by one aggregate: two aggregates declaring the same
  event name is a violation, the non-owner's command emits `none`.
- **Invariants** — `id` unique within the aggregate; `statement` present; `violated_by` non-empty
  and naming declared commands; `examples` non-empty, every example with `given` / `when` /
  `then` and a `kind` ∈ `positive` | `negative`, and **both kinds present** — an invariant with
  one side untried has not located its boundary.
- **Repository** — an object whose `root` equals the aggregate `root` (no repository for an
  interior entity). **Specifications**, when present, each state a `predicate`.

A malformed manifest (a list where a string belongs, a string where an object belongs) is reported
as a violation, never as a traceback.
