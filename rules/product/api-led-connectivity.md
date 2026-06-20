# Rules: API-Led Connectivity (design-api)

Reference for `/product:design-api`. Design the logical API surface in **three layers**
(MuleSoft API-Led Connectivity) so that data, business logic, and channel concerns are separated
and reusable. The layers are a *logical* design tool — not every API needs all three.

## The three layers

1. **System API** — exposes a system/data source through clean **CRUD** operations on its entities.
   One System API per data domain (maps to `ENT-` / a bounded context's store). It hides the
   underlying storage and is the only thing that touches it.
2. **Process API** — orchestrates **business flows** by composing multiple System APIs (and other
   Process APIs). Holds business logic and cross-entity transactions/sagas. No direct storage access.
3. **Experience API** — adapts a Process/System API for a **specific channel** (web, mobile,
   partner), shaping payloads for that journey/screen. Optimizes for the consumer, not the source.

```
Experience (channel-optimized)
   └─ Process (business flow / orchestration)
        └─ System (CRUD over entities)
```

## Derivation order

1. **Entities × CRUD → System APIs** — from `data-model.md`, one System API per entity cluster.
2. **Business flows → Process APIs** — from `feature-list.md`/journeys, compose System APIs into
   flows.
3. **Screens/journeys → Experience APIs** — from `ui-mocks/`/journeys, tailor per channel.

## Reuse & extensibility rules

- **Maximize reuse**: one Process API should serve **many** Experience APIs; one System API should
  serve **many** Process APIs. Reuse is the whole point of the layering.
- **Don't force all three layers.** A batch job may be Process + System only; a trivial read may be
  Experience → System. Add a layer when it earns its keep.
- **Never expose a System API directly to the UI.** Channels talk to Experience (or Process) APIs,
  so storage stays decoupled from clients.
- Keep the **dependency graph acyclic** and downward (Experience → Process → System).

## Per-API specification

For each API (`API-` id) record: layer, name, purpose, the entities/APIs it depends on, and an
**OpenAPI (OAS) sketch** — key paths, methods, and the main request/response shapes.

## ID convention

`API-` ids tagged by layer; append to `work/traceability.json` with Upstream `ENT-`/`FEAT-`/`CTX-`
references. The catalog also records the cross-API dependency graph.

## Sources

- MuleSoft — "API-Led Connectivity" (System / Process / Experience APIs)
- OpenAPI Specification — for the per-API sketches
