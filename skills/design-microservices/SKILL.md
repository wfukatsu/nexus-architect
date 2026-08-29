---
description: |
  Design target microservices architecture and transformation plan.
  /architect:design-microservices to invoke. Requires redesign output as a prerequisite.
model: opus
user_invocable: true
---

# Microservices Design

## Desired Outcome

1. **Target Architecture** -- Service catalog, classification, communication patterns, Mermaid diagrams
2. **Transformation Plan** -- Incremental migration roadmap from legacy
3. **Domain Event Catalog, consumer side** -- When `design-aggregate` ran, the cross-context
   consumers of every `published` event, now that the service split says which service reacts to
   what (see below)

Service classification:
- **Process**: Stateful, participates in cross-service transactions
- **Master**: CRUD-centric, master data management
- **Integration**: External system integration adapters
- **Supporting**: Cross-cutting concerns (authentication, notifications, etc.)

For each cross-service transaction in the target architecture, name the mechanism it uses rather
than defaulting to "Saga/2PC" (@rules/scalardb-2pc-patterns.md):

| Mechanism | Topology |
|-----------|----------|
| One-phase commit | Shared-cluster pattern — every service uses one ScalarDB Cluster instance. The documented recommendation whenever possible |
| Global Transaction API (ScalarDB 3.19+) | Separated clusters with a Transaction Coordinator node driving 2PC underneath; application code stays one-phase |
| Application-driven 2PC | Separated clusters without a Coordinator node, Core-only, or Spring Data JDBC. Keep to 2-3 services |
| ScalarDB Saga | Eventual consistency with compensations or TCC — see @rules/scalardb-saga-patterns.md |

The choice drives the deployment view (one Cluster instance vs several, plus the Coordinator table
owner, plus a saga server if used), so make it here and carry it into `/architect:design-scalardb`.
On a re-run where `design-scalardb` has already run and decided it, confirm or override that
decision here with a recorded reason — the ADR is still this skill's (@rules/architecture-decision-records.md
§1, "the skill that decides first writes the record"; when the record does not exist yet, write
it and say in its Context where the decision was actually taken).

### Domain Event Catalog — the consumer side

`reports/03_design/domain-event-catalog.json` (written by `/architect:design-aggregate`, shape in
its SKILL.md § Domain Event Catalog) lists every domain event with its publisher. This skill is
where the consumers become known: for each service edge that is event-driven rather than a
synchronous call, add the consuming context to the event's `consumers` with the relationship the
context map draws and the purpose of the reaction; set `scope: published` on an event that gained
a consumer and leave `internal` the ones that did not; state `delivery`, `idempotency_key`,
`version` and `evolution` per published event. Never rename an event or move its publisher — that
is an aggregate-model change and goes back through `design-aggregate`. Regenerate the `.md`
projection, then run
`python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/domain_event_catalog.py" <project_dir>`; a consumer that
is not a declared context, or a published event with no delivery contract, is fixed here. When
`design-aggregate` runs after this skill instead, it fills the consumer side itself from the
target architecture — whichever runs second completes the catalog.

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/03_design/bounded-contexts-redesign.md | Required | /architect:redesign |
| reports/03_design/context-map.md | Recommended | /architect:redesign |
| reports/03_design/domain-event-catalog.json | Optional | /architect:design-aggregate — the events whose consumer side this skill completes |
| reports/03_domain/architecture.md | Optional | /product:design-architecture — when present, treat its `ARCH-` runtime/deployment views as the **candidate architecture to refine** (confirm or override each element with a recorded reason), not as something to re-derive from scratch (@docs/design.md §1.3) |
| reports/03_domain/tech-stack-fitness.md | Optional | /product:design-architecture — Adopt/Conditional/Reject verdicts inform platform-technology placement |

## Output

| File | Content |
|------|---------|
| `reports/03_design/target-architecture.md` | Service catalog, architecture diagrams |
| `reports/03_design/transformation-plan.md` | Incremental migration roadmap |
| `reports/03_design/domain-event-catalog.json` / `.md` | Updated in place — consumer side of every published event (only when the catalog exists) |
| `reports/03_design/adr/adr-NNN-<slug>.md`, `adr/index.md` | This skill's Architecture Decision Records, appended to the log `redesign` opened (or opening it when this is the first skill to write one) |

## Completion Criteria

1. `target-architecture.md` and `transformation-plan.md` written, every cross-service transaction
   naming its mechanism
2. This skill's ADRs written and `python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/adr_records.py" <project_dir>` exits 0
3. When the catalog exists, its consumer side completed and
   `python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/domain_event_catalog.py" <project_dir>` exits 0
4. `ADR-` nodes (`type: decision`) appended to `work/traceability.json`
5. `work/pipeline-progress.json` stamped — `in_progress` with `plugin: "architect"` before the work,
   `completed` with `outputs` and `summary` after (@skills/common/progress-registry.md)

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

## Architecture Decision Records

The decisions this skill makes that a later phase depends on — the service split and its granularity, the cross-service transaction mechanism named above, and synchronous versus event-driven integration per edge — are each recorded as
`reports/03_design/adr/adr-NNN-<slug>.md` under @rules/architecture-decision-records.md: allocate
`ADR-` as `max + 1` over `work/traceability.json` and the directory (`redesign` registers the
prefix; this skill appends), cite the `CTX-` / `ARCH-` / `NFR-` nodes that drove the decision in `upstream` (never
empty), list the alternatives rejected, append one `{ "type": "decision" }` node per record to
the graph, regenerate `index.md`, and run
`python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/adr_records.py" <project_dir>` before completing. A
record you disagree with is superseded by a new one, never edited.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:redesign | Input source |
| /architect:design-scalardb | Output destination |
| /architect:design-api | Output destination |
