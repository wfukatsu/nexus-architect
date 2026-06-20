# Rules: Strategic DDD (define-data-model, map-domains)

Reference for the strategic Domain-Driven Design concepts used when deriving the data model and,
in Phase 4, the bounded contexts. Keep the model anchored to the **ubiquitous language**.

## Building blocks (tactical, used in the data model)

- **Entity** — has identity that persists through state changes (tracked by a key, not by
  attribute values). Promote a concept to an entity only when it is persisted, identified, and
  receives multiple operations.
- **Value Object** — defined by its attributes, no identity, immutable (e.g. Money, Address,
  DateRange). Prefer value objects over entities to avoid over-normalization.
- **Aggregate** — a cluster of entities/value objects treated as one consistency unit. The
  **aggregate root** is the only entry point; invariants hold within the aggregate boundary.
- **Command → Aggregate → Event** — a command requests a change, the aggregate enforces invariants
  and applies it, an event records that it happened. This drives entity discovery.

**Transactional boundary = aggregate boundary.** Keep aggregates small; reference other aggregates
by id, not by direct object containment.

## Strategic design (used by map-domains in Phase 4)

- **Ubiquitous Language** — one shared, precise vocabulary per context, used in code, docs, and
  conversation. Every `ENT-`/term should appear in it.
- **Bounded Context** — an explicit boundary within which a model and its language are consistent.
  The same word can mean different things in different contexts; that is expected. Each gets a
  `CTX-` id.
- **Subdomain classification** — split the problem space:
  - **Core** — the differentiating domain; where competitive advantage lives. **Invest here**;
    build it, don't buy it.
  - **Supporting** — necessary but not differentiating; build pragmatically.
  - **Generic** — solved problems (auth, billing, notifications); **buy/adopt, don't over-engineer**.
- **Context mapping** — relationships between contexts (Partnership, Customer/Supplier,
  Conformist, **Anticorruption Layer**, **Open Host Service / Published Language**, Shared Kernel).
  Aim for loose coupling between contexts; protect Core with an ACL.
- **Boundary sizing for extensibility** — draw boundaries that absorb likely future features; align
  contexts to business capabilities, not current screens, so they survive change.

## Handoff to nexus-architect

The `CTX-` bounded contexts and ubiquitous language map to architect's Bounded Context inputs
(design.md §1.3). `map-domains` output is the bridge to `/architect:define-requirements`.

## Discipline

- Model the **domain**, not the database schema; let storage follow the model.
- Avoid an anemic model where convenient, but do not invent behavior the requirements don't need.
- Record the rationale for each aggregate/entity boundary so `adapt-change` can revisit it.

## ID convention

`ENT-` for entities (data model); `DOM-`/`BC-` for domains/bounded contexts (Phase 4). Append to
`work/traceability.json` with Upstream `FEAT-`/`JOB-` references.

## Sources

- Eric Evans — "Domain-Driven Design" (entities, value objects, aggregates, ubiquitous language)
- Vaughn Vernon — "Implementing DDD" (aggregate design rules, context mapping)
