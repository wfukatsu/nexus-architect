---
description: |
  Abstract features and entities into bounded contexts (DDD strategic design) — a Core/Supporting/
  Generic domain map, a context map with relationships, and a ubiquitous language — sized to absorb
  future features. Bridges to nexus-architect. /product:map-domains [--auto] [--lang=ja|en].
model: opus
user_invocable: true
---

# Domain Map & Bounded Contexts

## Desired Outcome

Produce three deliverables:

1. **Domain map** — `reports/03_domain/domain-map.md`: subdomains classified **Core / Supporting /
   Generic**, with investment guidance (build Core, pragmatic Supporting, buy Generic).
2. **Bounded contexts** — `reports/03_domain/bounded-contexts.md` (`CTX-` IDs): each context, the
   entities/features it owns, a **Context Map** of relationships (ACL, Open Host / Published
   Language, Shared Kernel, Customer/Supplier, Conformist, Partnership), and a coarse
   **consistency hint** per context (`Strong` / `Eventual` / `TBD`) — a *hint*, not a decision:
   it seeds architect's per-process transaction-consistency classification (see Handoff), which
   makes the final ACID/Saga/Local-Tx call.
3. **Ubiquitous language** — `reports/03_domain/ubiquitous-language.md`: the shared vocabulary per
   context (every `ENT-`/term appears here).

## Invocation

```
/product:map-domains [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--auto` | Optional | Derive without elicitation; ambiguous boundaries → `TBD` |
| `--lang` | Optional | Override output language |

## Decision Criteria

- **Boundaries follow business capabilities, not screens** — and are sized to absorb likely future
  features (extensibility).
- **Invest in Core, not Generic.** Don't over-engineer Generic subdomains (auth, billing); protect
  Core with an Anticorruption Layer.
- **Loose coupling between contexts** — relationships are explicit (ACL / Published Language).
- **Stop condition**: every entity/feature belongs to a context, subdomains are classified
  Core/Supporting/Generic, the context map has typed relationships, and the ubiquitous language
  covers all terms.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/02_spec/data-model.md` | Required | `/product:define-data-model` | block with a message — contexts group entities |
| `reports/02_spec/feature-list.md` | Required | `/product:define-features` | block with a message — capabilities define boundaries |

## Process

1. **Read context** — data model, features, `work/traceability.json`.
2. **Classify subdomains** — Core / Supporting / Generic; record investment guidance. Apply
   `@rules/product/ddd-strategic.md`.
3. **Draw contexts** — group entities/features into `CTX-` bounded contexts sized for the future.
4. **Map relationships** — type each context-to-context relationship (ACL, Published Language, …).
5. **Tag consistency hint** — for each `CTX-`, mark a coarse `Strong` / `Eventual` / `TBD` hint
   from the nature of its operations (money/inventory/booking invariants → `Strong`; read models,
   analytics, notifications → `Eventual`; unclear → `TBD`), with a one-line rationale. This is a
   seed for architect, not a binding transaction decision.
6. **Define language** — the ubiquitous language per context.
7. **Append traceability** — add `CTX-` nodes to `work/traceability.json` with Upstream
   `ENT-`/`FEAT-` references.
8. **Record** — write the three files; append decisions to `work/context.md`; log `TBD`s.

## Handoff

The `CTX-` bounded contexts + ubiquitous language map to architect's Bounded Context inputs
(`docs/design.md` §1.3) — the bridge to `/architect:define-requirements`. The per-context
**consistency hint** (`Strong`/`Eventual`/`TBD`) seeds architect's per-process
transaction-consistency classification — the §1.4 designed gap product cannot fully close;
architect confirms or overrides it and makes the binding ACID/Saga/Local-Tx decision.

## Output

`reports/03_domain/domain-map.md`, `reports/03_domain/bounded-contexts.md` (with `CTX-` table +
Context Map + per-context consistency hint), and `reports/03_domain/ubiquitous-language.md`.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/ddd-strategic.md` | Subdomain classification, bounded contexts, context mapping |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:define-data-model` | Upstream — entities grouped into contexts |
| `/product:define-features` | Upstream — capabilities define boundaries |
| `/product:design-api` | Downstream — APIs realize the contexts |
| `/architect:define-requirements` | Handoff — consumes the bounded contexts |
| `/product:adapt-change` | Re-runs this skill when the domain evolves |
