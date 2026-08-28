---
description: |
  Abstract features and entities into bounded contexts (DDD strategic design) — a Core/Supporting/
  Generic domain map, a context map with relationships, and a ubiquitous language — sized to absorb
  future features. Bridges to nexus-architect. Boundaries are derived from features and entities
  by default, or found with the user in a Big Picture EventStorming walk (--mode=event-storming).
  /product:map-domains [--mode=derive|event-storming] [--auto] [--lang=ja|en].
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
/product:map-domains [--mode=derive|event-storming] [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--mode=derive\|event-storming` | Optional | `derive` (default): read the contexts off features and entities. `event-storming`: find them in a Big Picture EventStorming walk with the user — events in the business's words, pivotal events as boundary candidates, hotspots as `OQ-` — then run the same steps 2–8 (@rules/product/event-storming.md). Refused under `--auto`: a walk with nobody to walk with is derivation, and the skill says so and derives |
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
| `reports/00_core/vision-mission-value.md` | Recommended | `/product:define-vision` | the Domain Vision Statement is the prior for the Core classification; without it, Core is chosen from features alone and said so |

## Process

1. **Read context** — data model, features, `work/traceability.json`.
   **`--mode=event-storming` only** — before step 2, run the Big Picture walk exactly as
   @rules/product/event-storming.md §3 lays it out, write `reports/03_domain/event-timeline.md`
   as its record (§4), and take the context candidates from the runs between pivotal events into
   step 2 — `bounded-contexts.md` cites the pivotal events each boundary rests on.
2. **Classify subdomains** — Core / Supporting / Generic; record investment guidance. Start from the
   Domain Vision Statement's named core and cite its `VIS-` as the upstream of every `Core`
   classification (a Core the statement did not name is a finding to raise, not a silent addition). Apply
   `@rules/product/ddd-strategic.md`.
3. **Draw contexts** — group entities/features into `CTX-` bounded contexts sized for the future,
   and write each as a Bounded Context Canvas (below); a part that cannot be filled is asked, and
   what stays open is an `OQ-` in the Canvas's last row.
4. **Map relationships** — type each context-to-context relationship (ACL, Published Language, …).
5. **Tag consistency hint** — for each `CTX-`, mark a coarse `Strong` / `Eventual` / `TBD` hint
   from the nature of its operations (money/inventory/booking invariants → `Strong`; read models,
   analytics, notifications → `Eventual`; unclear → `TBD`), with a one-line rationale. This is a
   seed for architect, not a binding transaction decision.
6. **Define language** — the ubiquitous language per context.
7. **Append traceability** — add `CTX-` nodes to `work/traceability.json` with Upstream
   `ENT-`/`FEAT-` references.
8. **Record** — write the three files; append decisions to `work/context.md`;
   ask remaining unknowns and log only what stays open (@rules/open-questions.md).

### Bounded Context Canvas (one per context, in `bounded-contexts.md`)

Each context is written in the same nine-part shape (after Nick Tune's Bounded Context Canvas),
so product's `bounded-contexts.md` and architect's `bounded-contexts-redesign.md` can be laid side
by side and `/product:review` and `/architect:review-consistency` can check that a context did not change meaning across the
handoff:

| Part | Content |
|------|---------|
| **Name** | `CTX-` id and the name in the ubiquitous language |
| **Purpose** | One paragraph: what this context is responsible for, and what it is not |
| **Strategic classification** | Core / Supporting / Generic; business model role (revenue, engagement, compliance, cost reduction); evolution stage (genesis / custom / product / commodity) |
| **Domain roles** | The archetypes it plays: specification, execution, analysis, gateway, draft, … |
| **Inbound communication** | Who calls it, with which messages (commands / queries), over which relationship type (Customer/Supplier, Conformist, ACL, OHS/PL, …) |
| **Outbound communication** | Whom it calls or notifies, with which events / requests, and the relationship type |
| **Ubiquitous language** | The five to ten terms that mean something specific here — the ones that would be misread from outside |
| **Business decisions** | The rules and policies this context decides — the `RULE-` entries and invariants it owns |
| **Assumptions and open questions** | What the boundary rests on, and the `OQ-` entries still open about it |

## Handoff

The `CTX-` bounded contexts + ubiquitous language map to architect's Bounded Context inputs
(`docs/design.md` §1.3) — the bridge to `/architect:define-requirements`. The per-context
**consistency hint** (`Strong`/`Eventual`/`TBD`) seeds architect's per-process
transaction-consistency classification — the §1.4 designed gap product cannot fully close;
architect confirms or overrides it and makes the binding ACID/Saga/Local-Tx decision.

## Output

`reports/03_domain/domain-map.md`, `reports/03_domain/bounded-contexts.md` (with `CTX-` table +
Context Map + per-context consistency hint), and `reports/03_domain/ubiquitous-language.md`.
With `--mode=event-storming`, also `reports/03_domain/event-timeline.md` — the Big Picture record
(ordered events, pivotal events, swimlanes, hotspots with their `OQ-` IDs). It is a session record:
`CTX-` IDs live in `bounded-contexts.md` alone, never in the timeline.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/ddd-strategic.md` | Subdomain classification, bounded contexts, context mapping |
| `@rules/product/event-storming.md` | The Big Picture walk behind `--mode=event-storming`: notation, pivotal events as boundary candidates, hotspots, what is written |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:define-data-model` | Upstream — entities grouped into contexts |
| `/product:define-features` | Upstream — capabilities define boundaries |
| `/product:design-api` | Downstream — APIs realize the contexts |
| `/architect:define-requirements` | Handoff — consumes the bounded contexts |
| `/product:adapt-change` | Re-runs this skill when the domain evolves |
