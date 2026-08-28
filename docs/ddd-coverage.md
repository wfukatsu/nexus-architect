# DDD Technique Coverage

Which Domain-Driven Design techniques this toolkit implements, where, and how far. Maintained
here so the question is answered from the repository rather than re-derived by an outside review
each time — the first such review (August 2026) mis-scored two rows because it did not find the
artifacts, which is the failure this table exists to prevent.

`tools/docs_consistency.test.py` asserts that every skill this table names is a registered command
and that every artifact path it cites is declared by a skill — in a SKILL.md, a manifest or the
output tree; a rule file merely discussing a path does not count. The **status** column is judgment
and is reviewed by hand when a row's skill changes.

Status legend: ◎ dedicated skill or artifact with a defined procedure · ○ built into another
skill · △ referenced, evaluated or partially produced, not a standalone method · × nothing.

## Domain discovery

| Technique | Status | Where | Artifact |
|-----------|--------|-------|----------|
| Domain Storytelling | ◎ | `/architect:create-domain-story`, `/product:create-domain-story` | `reports/04_stories/domain-story-{domain}.md`, `reports/01_ux/domain-stories/` |
| EventStorming — Big Picture | ◎ | `/product:map-domains --mode=event-storming` | `reports/03_domain/event-timeline.md` (session record; `CTX-` stay in `bounded-contexts.md`) |
| EventStorming — Process Modeling | ◎ | `/product:create-domain-story --mode=event-storming`, `/architect:create-domain-story --mode=event-storming` | the story's Process Model section |
| EventStorming — Software Design | ○ | `/architect:design-aggregate` | commands and events per aggregate |
| Event Modeling | △ | state machines and aggregates carry events, commands and read models; no timeline-first artifact | — |
| Knowledge crunching | ○ | the facilitated stages of the discovery skills, the ubiquitous language | — |
| CRC cards | × | — | — |

## Strategic design

| Technique | Status | Where | Artifact |
|-----------|--------|-------|----------|
| Ubiquitous Language | ◎ | `/architect:analyze`, `/product:map-domains` | `reports/01_analysis/ubiquitous-language.md`, `reports/03_domain/ubiquitous-language.md` |
| Subdomain classification (Core / Supporting / Generic) | ◎ | `/product:map-domains`, `/architect:map-domains` | `reports/03_domain/domain-map.md`, `reports/03_design/domain-analysis.md` |
| Bounded Context | ◎ | `/product:map-domains`, `/architect:redesign` | `reports/03_domain/bounded-contexts.md`, `reports/03_design/bounded-contexts-redesign.md` |
| Bounded Context Canvas | ◎ | `/architect:redesign`, `/product:map-domains` | the per-context Canvas section of both artifacts |
| Context Mapping | ◎ | `/architect:redesign`, `/product:map-domains` | `reports/03_design/context-map.md`, the Context Map in `bounded-contexts.md` |
| Domain Vision Statement | ◎ | `/product:define-vision` | the Domain Vision Statement section of `reports/00_core/vision-mission-value.md` |
| Core Domain investment guidance | ◎ | `/product:map-domains` | `reports/03_domain/domain-map.md` |
| Team topology / Conway alignment | ○ | `/architect:design-microservices` | `reports/03_design/target-architecture.md` |

## Tactical design

| Technique | Status | Where | Artifact |
|-----------|--------|-------|----------|
| Aggregate / Aggregate Root | ◎ | `/architect:design-aggregate` | `reports/03_design/aggregates/aggregate-manifest.json` (`AGG-`) |
| Entity | ◎ | `/product:define-data-model`, `/architect:design-aggregate` | `reports/02_spec/data-model.md` (`ENT-`), aggregate members |
| Value Object | ◎ | `/architect:design-aggregate` | aggregate members with `kind: value` and their validation rule |
| Invariant | ◎ | `/architect:design-aggregate` | invariants with positive and negative examples, validated by `tools/lib/aggregate_manifest.py` |
| Domain Event | ◎ | `/architect:design-aggregate`, `/architect:design-state-machine` | aggregate events, state-machine events |
| Factory | ○ | `/architect:design-aggregate` | the creation command and what must hold at birth |
| Specification | ○ | `/architect:design-aggregate` | `specifications` per aggregate |
| Repository | ◎ | `/architect:design-aggregate`, `/architect:design-implementation` | one repository per root; `reports/06_implementation/repository-interfaces-spec.md` |
| Domain Service / Application Service | ○ | `/architect:design-implementation` | `reports/06_implementation/domain-services-spec.md`, `api-layer-spec.md` |
| Layered / Hexagonal architecture | ◎ | `/architect:evaluate-ddd` (evaluation), `/architect:design-implementation`, `/architect:generate-contract-tests` (ArchUnit) | `reports/02_evaluation/ddd-tactical-architecture-evaluation.md` |
| DDD maturity evaluation of an existing system | ◎ | `/architect:evaluate-ddd` | `reports/02_evaluation/ddd-strategic-evaluation.md`, `ddd-tactical-architecture-evaluation.md` |

## Behaviour, consistency and transactions

| Technique | Status | Where | Artifact |
|-----------|--------|-------|----------|
| State transition modeling | ◎ | `/architect:design-state-machine` | `reports/03_design/state-machines/state-machine-manifest.json` (`STM-`) |
| State × event matrix | ◎ | `/architect:design-state-machine` | every cell decided, validated by `tools/lib/state_machine_manifest.py` |
| Concurrency / contention design | ◎ | `/architect:design-state-machine` | the contention table |
| Local / distributed / saga classification | ◎ | `/architect:design-aggregate`, `/architect:design-state-machine`, `/architect:design-scalardb` | per command / transition; `reports/03_design/scalardb-transaction.md` |
| Saga / compensation | ◎ | `/architect:design-scalardb` | the saga design checklist in `scalardb-transaction.md` |
| CQRS / read models | ◎ | `/architect:design-scalardb`, `/architect:design-data-layer` | the Read Model, CQRS and Event Sourcing Decisions section |
| Event Sourcing | ◎ | `/architect:design-scalardb`, `/architect:design-data-layer` | the same section; the Event Store pattern in `rules/scalardb-schema-design.md` |

## Requirements and examples

| Technique | Status | Where | Artifact |
|-----------|--------|-------|----------|
| Example Mapping | ◎ | `/product:example-map` | `reports/02_spec/examples/example-map-{feat}.md` (`RULE-`, `EX-`) |
| Specification by Example / BDD | ◎ | `/architect:generate-test-specs` | `reports/07_test-specs/bdd-scenarios/` — `Rule:` / `Scenario:` from `RULE-` / `EX-` |
| Acceptance criteria | ◎ | `/architect:export-backlog`, `/architect:define-requirements` | Issue acceptance criteria and FR acceptance criteria from `RULE-` |
| Contract testing | ◎ | `/architect:generate-contract-tests` | `generated/{service}/src/test/java/**/contract/` |
| Property-based testing | ◎ | `/architect:generate-test-specs`, `/architect:generate-scalardb-code` | `reports/07_test-specs/property-test-specs.md`; jqwik properties per invariant |
| Three Amigos session | × | a human meeting; the Example Mapping session is its artifact-producing part | — |
| User Story Mapping | △ | journeys, jobs and features carry the content; no backbone / walking-skeleton artifact | — |
| Impact Mapping | △ | success metrics → features traceability covers the chain; no dedicated map | — |

## Deliberately not implemented

| Technique | Reason |
|-----------|--------|
| CRC cards | Superseded by the aggregate manifest, which records responsibilities and collaborators with a validator behind them |
| Three Amigos | A meeting format, not an artifact; `/product:example-map` produces what the meeting would |
| Impact Mapping | The `NSM-` → `FEAT-` traceability graph already answers "which deliverable serves which goal" |

## Updating this table

Change the row when its skill changes, in the same commit. A new technique gets a row with `×`
before it gets a skill, so the gap is visible rather than discovered by the next outside review.
