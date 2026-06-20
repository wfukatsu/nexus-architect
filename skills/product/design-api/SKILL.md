---
description: |
  Design the logical API surface in three API-Led layers — System APIs (CRUD over entities),
  Process APIs (business-flow orchestration), Experience APIs (per-channel) — maximizing reuse, with
  a dependency graph and per-API OpenAPI sketches. /product:design-api [--auto] [--lang=ja|en].
model: opus
user_invocable: true
---

# API Design (API-Led)

## Desired Outcome

Produce one deliverable:

1. **API design** — `reports/03_domain/api-design.md` (`API-` IDs):
   - A **layered catalog**: System (CRUD), Process (business flow), Experience (per-channel)
   - A **dependency graph** (Experience → Process → System, acyclic, downward)
   - A per-API **OpenAPI (OAS) sketch** — key paths, methods, main request/response shapes

## Invocation

```
/product:design-api [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--auto` | Optional | Derive without elicitation; open questions → `TBD` |
| `--lang` | Optional | Override output language |

## Decision Criteria

- **Maximize reuse**: one Process API serves many Experience APIs; one System API serves many
  Process APIs.
- **Don't force all three layers** — a batch may be Process + System only; add a layer when it
  earns its keep.
- **Never expose a System API directly to the UI** — channels talk to Experience (or Process) APIs.
- **Keep the dependency graph acyclic and downward** (Experience → Process → System).
- **Stop condition**: every feature is realized by an API path, layers are assigned, the dependency
  graph is acyclic, and each API has an OAS sketch.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/03_domain/bounded-contexts.md` | Required | `/product:map-domains` | block with a message — APIs align to contexts |
| `reports/02_spec/data-model.md` | Required | `/product:define-data-model` | block with a message — System APIs need entities |
| `reports/02_spec/feature-list.md` | Recommended | `/product:define-features` | Process-API flows degrade to `TBD` |

## Process

1. **Read context** — bounded contexts, data model, features, `work/traceability.json`.
2. **System layer** — entities × CRUD → one System API per entity cluster / context. Apply
   `@rules/product/api-led-connectivity.md`.
3. **Process layer** — compose System APIs into business flows (cross-entity transactions/sagas).
4. **Experience layer** — tailor Process/System APIs per channel from screens/journeys.
5. **Graph & sketches** — build the dependency graph; write an OAS sketch per API.
6. **Append traceability** — add `API-` nodes to `work/traceability.json` with Upstream
   `ENT-`/`FEAT-`/`CTX-` references.
7. **Record** — write the file; append decisions to `work/context.md`; log `TBD`s.

## Output

`reports/03_domain/api-design.md`, with a layered `API-` catalog, a dependency graph, and per-API
OAS sketches.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/api-led-connectivity.md` | System/Process/Experience layers, reuse rules, OAS sketch |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:map-domains` | Upstream — contexts frame the APIs |
| `/product:define-data-model` | Upstream — entities back the System APIs |
| `/product:define-features` | Upstream — features drive Process APIs |
| `/product:define-nfr` | Downstream — NFRs constrain the API surface |
| `/product:adapt-change` | Re-runs this skill when contexts or entities change |
