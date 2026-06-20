---
description: |
  Derive the data model from UI mocks and features in two passes — Pass 1 reads explicit entities
  from screens/forms/actions; Pass 2 uses a feature×entity CRUD matrix to surface implicit entities
  (joins, history, audit, state machines) with recorded rationale. Outputs a Mermaid ER diagram.
  /product:define-data-model [--auto] [--lang=ja|en].
model: opus
user_invocable: true
---

# Data Model (2-pass)

## Desired Outcome

Produce one deliverable:

1. **Data model** — `reports/02_spec/data-model.md` (`ENT-` IDs):
   - Entities, attributes, and relationships
   - A **Mermaid ER diagram** of the final model (explicit + implicit)
   - For each Pass-2 addition, the functional-relationship rationale

## Invocation

```
/product:define-data-model [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--auto` | Optional | Derive without elicitation; record ambiguous concepts as `TBD` |
| `--lang` | Optional | Override output language |

## Decision Criteria

- **Entity criteria**: a concept becomes an entity only if it is **persisted**, has **identity/key**,
  and **receives multiple operations**. Prefer value objects; avoid over-normalization.
- **Two passes are mandatory.** Pass 1 = explicit (UI + features); Pass 2 = implicit via the CRUD
  matrix — every implicit addition records *why* (the functional relationship).
- **Model the domain, not the schema.** Let storage follow the model.
- **Stop condition**: all explicit concepts captured (Pass 1), the CRUD matrix run to surface
  implicit entities (Pass 2), and a valid Mermaid ER diagram produced.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/02_spec/feature-list.md` | Required | `/product:define-features` | block with a message — the CRUD matrix needs features |
| `reports/02_spec/ui-mocks/` | Required | `/product:generate-ui-mock` | block with a message — Pass 1 needs screens/forms |

## Process

1. **Read context** — features, mocks, `work/traceability.json`.
2. **Pass 1 (explicit)** — screen/concept → entity; form fields → attributes; action results →
   state/events; Command-receiving/Event-emitting aggregate → entity. Apply
   `@rules/product/ui-to-domain.md` and `@rules/product/ddd-strategic.md`.
3. **Pass 2 (implicit)** — build the feature×entity CRUD matrix; detect many-to-many/history/audit/
   state-machine concepts; add them with rationale.
4. **Relate** — define relationships and cardinalities; keep aggregates small (reference by id).
5. **Diagram** — render the Mermaid ER diagram of the final model.
6. **Append traceability** — add `ENT-` nodes to `work/traceability.json` with Upstream
   `FEAT-`/`JOB-` references.
7. **Record** — write the file; append decisions to `work/context.md`; log `TBD`s.

## Output

`reports/02_spec/data-model.md`, with an `ENT-` ID table (Upstream column), Pass-2 rationale notes,
and a Mermaid ER diagram.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/ui-to-domain.md` | Two-pass derivation, CRUD matrix, entity criteria |
| `@rules/product/ddd-strategic.md` | Entity vs value object, aggregates, ubiquitous language |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:define-features` | Upstream — features drive the CRUD matrix |
| `/product:generate-ui-mock` | Upstream — screens/forms drive Pass 1 |
| `/product:map-domains` | Downstream — groups entities into bounded contexts |
| `/product:design-api` | Downstream — API resources map to entities |
| `/product:adapt-change` | Re-runs this skill when features change |
