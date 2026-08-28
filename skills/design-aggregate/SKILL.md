---
description: |
  Design the tactical model of each bounded context — aggregates with their root, interior
  entities, value objects, invariants, commands, domain events, factory, specifications and
  repository interface — as the unit a transaction writes, through facilitated dialogue.
  /architect:design-aggregate [--aggregate=<name>] [--context=<name>] [--auto] [--lang=en|ja] to invoke.
  Recommended prerequisite: redesign output. Feeds design-state-machine, design-scalardb /
  design-data-layer, design-api, design-implementation, generate-test-specs and the reviews.
model: opus
user_invocable: true
---

# Aggregate Design

## Desired Outcome

For every cluster of objects that changes together under an invariant, a model that answers
precisely: **which objects form one unit, what must be true of that unit at the end of every
transaction, which commands may change it, and what the rest of the system may hold of it.**

Per aggregate:

- **The root** — the entity that owns the identity and guards every change
- **Interior entities and value objects** — what lives inside the boundary, and what is a value
- **Invariants** — predicates that hold at the end of every transaction, each with the commands
  that can violate it and a concrete example
- **Commands and domain events** — every way the aggregate changes, with its actor, guard,
  consistency class and the event it emits
- **Factory, specifications, repository interface** — the creation rule, the reusable predicates,
  the one collection abstraction per root
- **A Mermaid `classDiagram`** and a machine-readable manifest downstream skills consume

The modeling method, the seven well-formedness rules and the transaction-boundary contract are
@rules/aggregate-design.md. Read it before Stage 1; this skill facilitates it, it does not restate it.

## Invocation

```
/architect:design-aggregate [--aggregate=<name>] [--context=<name>] [--auto] [--lang=en|ja]
```

- `--aggregate` — Model this aggregate only (e.g. `Order`, `Reservation`). Selected interactively
  when omitted.
- `--context` — Restrict the candidate list to one bounded context (e.g. `Ordering`).
- `--auto` — Skip facilitation and derive the models from existing reports. Lower fidelity; this is
  the mode `/architect:pipeline` uses.
- `--lang` — Output language for the generated documents. Defaults to
  `options.output_language` in `work/pipeline-progress.json`.

## Decision Criteria

- **Model what earns an aggregate** (@rules/aggregate-design.md §1). An invariant that spans more
  than one attribute, a root whose ID outsiders hold, and a unit one transaction writes — all
  three, or it is an entity inside someone else's aggregate, a value object, or reference data.
- **Value objects before entities.** Every attribute group with its own validation rule is a value
  object until identity is proven; `define-data-model`'s `ENT-` list is where to look for the
  values it promoted by mistake.
- **One command, one aggregate, one transaction.** A command that must write two aggregates is
  classified `distributed` or `saga` and says which aggregate owns the transaction; it is never
  left `local` (@rules/aggregate-design.md §4).
- **Other aggregates by ID only.** A member typed as another aggregate's root is a boundary defect
  to resolve in Stage 3, not a modeling convenience to record.
- **Every invariant has an example.** An instance with real values, a command, and the outcome —
  what `generate-test-specs` turns into tests and what a domain expert can check at a glance.
- **Resolve, then ask, then record.** Anything the input reports already answer is not a question
  (@rules/open-questions.md §1). What the user owns — whether a rule is an invariant or a
  preference, which aggregate owns a two-aggregate write, whether a collection is bounded — is
  asked with `AskUserQuestion`; what stays open becomes an `OQ-` entry in `work/context.md`, and
  the placeholder in the document carries its ID.

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/03_design/bounded-contexts-redesign.md | Recommended | /architect:redesign — the contexts whose interiors this skill models |
| reports/01_analysis/ubiquitous-language.md | Recommended | /architect:analyze — every name must come from here |
| reports/02_spec/data-model.md | Optional | /product:define-data-model — the `ENT-` list is the candidate set for roots, interior entities and mis-promoted value objects |
| reports/03_domain/bounded-contexts.md | Optional | /product:map-domains — the `CTX-` ownership of each entity |
| reports/01_analysis/data-model-analysis.md | Optional | /architect:analyze-data-model — existing tables and their foreign keys are the evidence of implicit boundaries |
| reports/04_stories/domain-story-{domain}.md | Optional | /architect:create-domain-story — work items are aggregate candidates, activities are commands |
| reports/02_spec/feature-list.md | Optional | /product:define-features — `FEAT-` commands map to aggregate commands |
| reports/02_spec/examples/example-map-{feat}.md | Optional | /product:example-map — `RULE-` entries are invariant candidates, `EX-` entries their first concrete examples |
| reports/03_design/scalardb-transaction.md | Optional | /architect:design-scalardb — when it already exists, its TX- entries fix each command's consistency class |

With none of these present, ask the user to name the aggregates and describe what must always be
true of each; do not derive an aggregate from a table name.

## Execution Modes

### Interactive Mode (default)

Six stages. Batch questions (1–4 per `AskUserQuestion` call), always offer candidates derived from
the inputs rather than blank prompts, and keep the whole interview inside two rounds per stage.

**Stage 1 — Select the aggregates**
Build a candidate list with its evidence: entities that other entities point at, entities with a
status column, work items a domain story creates or changes, features whose names are commands on
one object ("approve order", "cancel reservation"). Group the candidates by bounded context.
Present it with `multiSelect: true`, each option carrying its evidence, and let the user add one
through the appended free-text option. Record the entities deliberately **not** made an aggregate
and what they are instead (interior entity of which root, value object, reference data) — that
list is an answer, not an omission.

**Stage 2 — Root, interior, values**
Per aggregate, propose the root and everything inside the boundary. For each member ask whether it
has identity of its own (interior entity) or is defined by its attributes (value object), and for
each value object what makes an instance legal. Push back on: a value object with a surrogate key,
an interior entity another aggregate references directly, and a collection with no upper bound.

**Stage 3 — Invariants**
Ask what must be true of the aggregate at the end of every change. Per invariant capture: the
predicate, the commands that can violate it, and one concrete example on each branch — an
instance that satisfies it after a command, and one the command must reject. Distinguish
invariants (always true, transactional) from preferences (usually true, a warning) and from rules
between aggregates (eventually consistent, enforced by a reaction to an event) — the last two are
recorded, but not as invariants. When `RULE-` entries exist for the mapped features, present them
as the candidates.

**Stage 4 — Commands and events**
Start with creation: what must already hold at birth and where its inputs come from — that is the
factory, and the same creation event `design-state-machine` models. Then, per command: actor or
role, guard, the invariants it must preserve, the event it emits (payload: IDs and values, not the
aggregate), and its consistency class — `local` when it writes this aggregate only, `distributed` or
`saga` when it must write another, taking the class from `scalardb-transaction.md` when it exists
and feeding it when it does not. A guard that more than one caller evaluates is a specification;
name it.

**Stage 5 — References and repository**
Walk every member typed as another aggregate's root and resolve it: an ID reference, a value
object copied at the time of the command (a price snapshot), or evidence the boundary is wrong.
Then the repository interface: the lookup keys, whether it loads the whole aggregate, the
consistency it reads with. One repository per root; a repository for an interior entity is a
rule-5 violation and is challenged, not recorded.

**Stage 6 — Validate, review, write**
Run the well-formedness checks below **before** presenting anything. Show the user the class
diagram, the invariant table with its examples and any check that failed, correct together, then
write the documents and the manifest.

### Auto Mode (`--auto`)

Derive the models without facilitation:

1. Read `bounded-contexts-redesign.md` for contexts and the entities each owns, `data-model.md` /
   `data-model-analysis.md` for entities and their relationships, `ubiquitous-language.md` for the
   exact terms.
2. Take as roots the entities that other entities reference and that a feature or domain story
   commands; take as interior the entities referenced by exactly one root and by nothing else;
   take as value objects the entities with no identity of their own in any operation.
3. Derive commands from the operations the feature list and the domain stories name, using their
   verbs verbatim; derive invariants from the constraints the data model states and from `RULE-`
   entries where an example map exists.
4. Default every command's consistency class to `local` and every unresolved cross-aggregate
   member to an ID reference, and **mark each default** in the document as assumed, with an `OQ-`
   entry per aggregate recording that the ownership of two-aggregate writes was never asked
   (@rules/open-questions.md §5).
5. Run the same well-formedness checks. A model that fails them is written with the failures listed
   under Open Items — never silently repaired by inventing an invariant.

Auto mode never invents an invariant that appears in no input. An aggregate candidate with no
stated invariant is reported as not modeled — an entity, not an aggregate.

## Well-formedness Checks (run before writing)

The seven rules of @rules/aggregate-design.md §3, in the order it is cheapest to fix them:

1. Exactly one root
2. At least one invariant, stated as a predicate
3. Every invariant names at least one command that can violate it
4. Every command names an actor, a consistency class and its emitted event (or `none`)
5. Interior entities and value objects are reachable only through the root — no repository for
   an interior entity
6. Other aggregates are referenced by identity only
7. Every name exists in the ubiquitous language, or its addition is proposed explicitly

These are also machine-checked: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/aggregate_manifest.py" <project_dir>` validates
the emitted manifest and exits non-zero with one line per violation. Run it after writing, and treat
a failure as a defect in the model rather than in the checker.

## Output

| File | Content |
|------|---------|
| `reports/03_design/aggregates/aggregate-{aggregate}.md` | One document per aggregate — root, interior, value objects, invariants with examples, commands, events, factory, specifications, repository, diagram |
| `reports/03_design/aggregates/aggregate-manifest.json` | **Canonical machine-readable model.** Downstream skills and the validator read this; the Markdown is its human-readable projection and is never authored separately |

`{aggregate}` is the kebab-case aggregate name (`order`, `payment-request`). Write document content
in the configured output language; YAML frontmatter keys and every identifier (aggregate, member,
command, event, invariant) stay English.

### Manifest shape

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
            { "given": "two lines of 10 EUR", "when": "addLine(5 EUR)", "then": "total 25 EUR, OrderLineAdded" },
            { "given": "submitted order", "when": "addLine(5 EUR)", "then": "rejected: order-not-editable" }
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
          "consistency": "local"
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

Field contracts the validator enforces: `id` matches `AGG-###` and is unique; `document` resolves
to a non-empty file inside the project; exactly one member has `kind: root` and its `name` equals
`root`; every member `kind` ∈ `root` | `entity` | `value` | `reference`, and a `reference` member
names the aggregate it `references` — a member whose name is another aggregate's root without
`kind: reference` is the rule-6 defect; `invariants` is non-empty, each with an `id` unique within
the aggregate, a `statement`, a non-empty `violated_by` naming declared commands, and at least one
example; every command has an `actor`, a `consistency` ∈ `local` | `distributed` | `saga`, an
`emits` naming a declared event or the literal `none`, and a `preserves` list of declared invariant
IDs; at most one command carries `creation: true`; `repository.root` equals `root`; `state_machine`,
when present, matches `STM-###`.

## Output Document Structure

```markdown
---
title: "Aggregate: {Aggregate}"
schema_version: 1
phase: "Phase 3: Design"
skill: design-aggregate
generated_at: "ISO8601"
aggregate: "{Aggregate}"
mode: "interactive|auto"
input_files:
  - reports/03_design/bounded-contexts-redesign.md
  - reports/01_analysis/ubiquitous-language.md
---

# Aggregate: {Aggregate}

## Scope

[Which bounded context, what this aggregate is the unit of, and the candidates considered and
deliberately not made aggregates — with what they are instead.]

## Boundary

| Member | Kind | Identity / Validation | Notes |
|--------|------|-----------------------|-------|
| Order | root | OrderId | held by Shipment, Invoice |
| OrderLine | entity | LineNo, local to Order | never referenced from outside |
| Money | value object | amount >= 0, ISO 4217 currency | |
| customerId | reference → Customer | | ID only; name snapshot copied at `place` |

## Invariants

| ID | Invariant | Violated by | Enforced |
|----|-----------|-------------|----------|
| INV-1 | total equals the sum of line totals | addLine, removeLine | in the root, inside the command's transaction |

### Examples

| Invariant | Given | When | Then |
|-----------|-------|------|------|
| INV-1 | two lines of 10 EUR | addLine(5 EUR) | total 25 EUR; OrderLineAdded |
| INV-1 | submitted order | addLine(5 EUR) | rejected: order-not-editable |

## Commands and Events

| Command | Creation | Actor | Guard | Preserves | Emits | Consistency |
|---------|----------|-------|-------|-----------|-------|-------------|
| place | yes (factory: cart, pricing, customer) | Customer | cart has a line | INV-1 | OrderPlaced | local |
| addLine | | Customer | status is Draft | INV-1 | OrderLineAdded | local |

[Then: every `distributed` / `saga` command with the aggregate that owns the transaction and the
compensation, and the events' payloads.]

## Specifications

| Specification | Predicate | Used by |
|---------------|-----------|---------|
| CanBeShipped | status is Approved and every line is allocated | ship, shippable-orders query |

## Repository

[Lookups, whether the whole aggregate is loaded, the read consistency, the OCC scope.]

## Diagram

```mermaid
classDiagram
    class Order {
        <<aggregate root>>
        +OrderId id
        +Money total
        +place(cart, pricing)
        +addLine(product, quantity)
    }
    class OrderLine {
        <<entity>>
        +LineNo lineNo
        +Quantity quantity
    }
    class Money {
        <<value object>>
        +amount
        +currency
    }
    Order "1" *-- "1..*" OrderLine : lines
    Order --> Money
```

## Lifecycle

[The `STM-` this aggregate's root carries, or the statement that it has no lifecycle worth a
machine and why (@rules/state-modeling.md §1).]

## Open Items

[Failed well-formedness checks, defaulted consistency classes, and TBDs carrying their `OQ-` IDs.]
```

## Traceability

Append one node per aggregate to `work/traceability.json` (create it as
`{ "schema_version": 1, "nodes": [] }` if absent — never start a second graph, @docs/design.md §1.5):

```json
{ "id": "AGG-001", "type": "aggregate", "title": "Order",
  "skill": "design-aggregate",
  "source_file": "reports/03_design/aggregates/aggregate-order.md",
  "upstream": ["CTX-002", "ENT-004", "RULE-003"] }
```

`upstream` points at the bounded context and the entities the aggregate is built from when those
nodes exist, at the `FEAT-` entries whose commands became its commands, and at the `RULE-` entries
that became its invariants. Allocate each `AGG-` as `max + 1` over the whole graph, per prefix. An
aggregate with no product-side origin carries an empty `upstream` — it is architect-originated, and
the graph should say so.

## Completion Criteria

1. One document per modeled aggregate under `reports/03_design/aggregates/`, plus the manifest
2. `python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/aggregate_manifest.py" <project_dir>` exits 0, or every violation it
   reports is listed under Open Items with an owner
3. Every invariant has at least one concrete example on each branch
4. Every name matches `ubiquitous-language.md`, or its addition is proposed
5. `AGG-` nodes appended to `work/traceability.json`
6. `work/pipeline-progress.json` stamped — `in_progress` with `plugin: "architect"` before the work,
   `completed` with `outputs` and `summary` after (@skills/common/progress-registry.md)

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:redesign | Upstream — the bounded contexts whose interiors are modeled |
| /architect:analyze-data-model | Upstream — existing tables and foreign keys are the evidence of implicit boundaries |
| /product:define-data-model | Upstream — the `ENT-` candidates, including the value objects it promoted |
| /product:example-map | Upstream — `RULE-` entries are invariant candidates, `EX-` entries their examples |
| /architect:create-domain-story | Upstream — work items are candidates, activities are commands |
| /architect:design-state-machine | Downstream — the root's commands with a guard on its condition are its transitions; this skill's aggregate list is its Stage 1 candidate list |
| /architect:design-scalardb | Downstream — the aggregate as OCC scope and partition-key unit; one repository per root |
| /architect:design-data-layer | Downstream — the same, for non-ScalarDB projects |
| /architect:design-api | Downstream — commands become operations on the root's resource; invariant violations become problem types |
| /architect:design-implementation | Downstream — the domain layer skeleton and the repository interfaces |
| /architect:generate-test-specs | Downstream — unit and property tests per invariant, seeded by the examples |
| /architect:review-consistency | Downstream — checks the model against the schema and transaction design |
