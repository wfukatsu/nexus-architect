# DDD Technique Coverage

Which Domain-Driven Design techniques this toolkit implements, where, and how far. Maintained
here so the question is answered from the repository rather than re-derived by an outside review
each time — the first such review (August 2026) mis-scored two rows because it did not find the
artifacts, which is the failure this table exists to prevent.

`tools/docs_consistency.test.py` asserts that every skill this table names is a registered command
and that every artifact path it cites is declared by a skill — in a SKILL.md, a manifest or the
output tree; a rule file merely discussing a path does not count. The **status** column is judgment
and is reviewed by hand when a row's skill changes.

A complete document set produced by these skills on the `ec-monolith` sample is committed under
`samples/ec-monolith/expected-reports/` (the real `reports/` tree is git-ignored);
`samples/ec-monolith/reference-set.test.py` keeps it valid and in step with this table.

Status legend: ◎ dedicated skill or artifact with a defined procedure · ○ built into another
skill · △ referenced, evaluated or partially produced, not a standalone method · × nothing.

## Domain discovery

| Technique | Status | Where | Artifact |
|-----------|--------|-------|----------|
| Domain Storytelling | ◎ | `/architect:create-domain-story`, `/product:create-domain-story` | `reports/04_stories/domain-story-{domain}.md`, `reports/01_ux/domain-stories/` |
| EventStorming — Big Picture | ◎ | `/product:map-domains --mode=event-storming` | `reports/03_domain/event-timeline.md` (session record; `CTX-` stay in `bounded-contexts.md`) |
| EventStorming — Process Modeling | ◎ | `/product:create-domain-story --mode=event-storming`, `/architect:create-domain-story --mode=event-storming` | the story's Process Model section |
| EventStorming — Software Design | ○ | `/architect:design-aggregate` | commands and events per aggregate |
| Event Modeling | × | deliberately not implemented — see below | — |
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
| Architecture Decision Records | ◎ | `/architect:redesign` opens the log; `/architect:design-microservices`, `/architect:design-scalardb`, `/architect:design-data-layer`, `/architect:design-api` append | `reports/03_design/adr/adr-NNN-<slug>.md` (`ADR-`), `reports/03_design/adr/index.md`, validated by `tools/lib/adr_records.py` |
| Domain Vision Statement | ◎ | `/product:define-vision` | the Domain Vision Statement section of `reports/00_core/vision-mission-value.md` |
| Core Domain investment guidance | ◎ | `/product:map-domains` | `reports/03_domain/domain-map.md` |
| Published Language / event contracts between contexts | ◎ | `/architect:design-aggregate` writes, `/architect:design-microservices` completes the consumer side, `/architect:design-api` emits AsyncAPI from it | `reports/03_design/domain-event-catalog.json` + `.md` (publisher, consumers per context-map relationship, delivery contract), validated by `tools/lib/domain_event_catalog.py`; `reports/03_design/api-specifications/asyncapi/` |
| Team topology / Conway alignment | ○ | `/architect:design-microservices` | `reports/03_design/target-architecture.md` |

## Tactical design

| Technique | Status | Where | Artifact |
|-----------|--------|-------|----------|
| Aggregate / Aggregate Root | ◎ | `/architect:design-aggregate` | `reports/03_design/aggregates/aggregate-manifest.json` (`AGG-`) |
| Entity | ◎ | `/product:define-data-model`, `/architect:design-aggregate` | `reports/02_spec/data-model.md` (`ENT-`), aggregate members |
| Value Object | ◎ | `/architect:design-aggregate` | aggregate members with `kind: value` and their validation rule |
| Invariant | ◎ | `/architect:design-aggregate` | invariants with positive and negative examples, validated by `tools/lib/aggregate_manifest.py` |
| Domain Event | ◎ | `/architect:design-aggregate`, `/architect:design-state-machine` | aggregate events, state-machine events, collected in `reports/03_design/domain-event-catalog.json` |
| Factory | ○ | `/architect:design-aggregate` | the creation command and what must hold at birth |
| Specification | ○ | `/architect:design-aggregate` | `specifications` per aggregate |
| Repository | ◎ | `/architect:design-aggregate`, `/architect:design-implementation` | one repository per root; `reports/06_implementation/repository-interfaces-spec.md` |
| Domain Service / Application Service | ○ | `/architect:design-implementation` | `reports/06_implementation/domain-services-spec.md`, `api-layer-spec.md` |
| Layered / Hexagonal architecture | ◎ | `/architect:evaluate-ddd` (evaluation), `/architect:design-implementation`, `/architect:generate-contract-tests` (ArchUnit) | `reports/02_evaluation/ddd-tactical-architecture-evaluation.md` |
| Clean Architecture naming (Use Case / Interactor / Presenter) | ◎ | `/architect:design-implementation --layering=clean`; read by `generate-api-code`, `generate-graphql-code`, `generate-scalardb-code`, `generate-contract-tests`, `generate-acceptance-tests`, `verify-implementation` | `layering_style` in `reports/06_implementation/api-layer-spec.md` frontmatter |
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
| Specification by Example / BDD | ◎ | `/architect:generate-test-specs` (scenarios), `/architect:generate-acceptance-tests` (executable) | `reports/07_test-specs/bdd-scenarios/` — `Rule:` / `Scenario:` from `RULE-` / `EX-`; Cucumber step definitions and `reports/07_test-specs/acceptance-test-coverage.md` |
| Acceptance criteria | ◎ | `/architect:export-backlog`, `/architect:define-requirements` | Issue acceptance criteria and FR acceptance criteria from `RULE-` |
| Contract testing | ◎ | `/architect:generate-contract-tests` | `generated/{service}/src/test/java/**/contract/` |
| Property-based testing | ◎ | `/architect:generate-test-specs`, `/architect:generate-scalardb-code` | `reports/07_test-specs/property-test-specs.md`; jqwik properties per invariant |
| Three Amigos session | × | a human meeting; the Example Mapping session is its artifact-producing part | — |
| User Story Mapping | ○ | `/product:define-features` | the User Story Map section of `reports/02_spec/feature-list.md` — journey stages as backbone, `FEAT-` as stories, MoSCoW bands as release slices, Must as the walking skeleton |
| Impact Mapping | × | deliberately not implemented — see below | — |

## Test-driven development

Where the toolkit stands on the practices that make a DDD model executable. The techniques above
produce the oracles (invariants, matrices, examples); these rows are about whether the code is
driven by them.

| Technique | Status | Where | Artifact |
|-----------|--------|-------|----------|
| Red → Green → Refactor (test-first, verifiable from history) | ◎ | `/architect:implement-backlog` Step 5, `rules/tdd-workflow.md` §2 | `test:` → `feat:` → `refactor:` commit series per unit on the working branch; the sequence recorded in `reports/09_verification/quality-gate.json` (`test_first`) |
| Double loop (ATDD outside, TDD inside) | ◎ | `/architect:generate-acceptance-tests` (the outer loop's tests), `/architect:implement-backlog` Step 5, `rules/tdd-workflow.md` §3 | The acceptance-level test that carried the outer loop, named in the Issue's progress comment; `@wip` scenarios flipped by the item that makes them pass |
| Walking skeleton | ◎ | `/product:define-features` (Must row), `/architect:export-backlog` (one `walking-skeleton` Issue per new service, first in order), `/architect:implement-backlog` (implements it first) | the User Story Map's Must row; the `walking-skeleton` Issue |
| Test doubles — Fake per repository port, injected Clock / id generator | ◎ | `/architect:design-implementation` (specifies), `/architect:generate-scalardb-code` (emits), `/architect:generate-contract-tests` (ArchUnit enforces) | `generated/{service}/src/test/java/**/fakes/`; `reports/06_implementation/repository-interfaces-spec.md` |
| Coverage threshold on the change | ◎ | `/architect:verify-implementation --gate` stage 2, `rules/ai-code-quality-gate.md` §Test quality | `reports/09_verification/quality-gate.json` (`coverage`), JaCoCo verification in `generated/{service}/build.gradle` |
| Mutation testing on the domain layer | ◎ | `/architect:verify-implementation --gate` stage 2 | `reports/09_verification/quality-gate.json` (`mutation`, survivors by line, invariant survivors by name) |
| Characterization / golden-master tests for legacy code | ◎ | `/architect:generate-characterization-tests`; baseline in `/architect:implement-backlog` Step 5, stage 4 of the gate | `reports/07_test-specs/characterization-test-coverage.md`; the `characterizationTest` task each transformation-plan step is gated on |
| Transaction-scenario integration tests over a real engine | ◎ | `/architect:generate-scalardb-code` (`*IT` per `TX-`, SQLite-backed in-process ScalarDB), `/scalardb:scaffold` / `/scalardb:build-app` | `generated/{service}/src/test/java/**/integration/`; stage 4 of the gate |
| Bug fix as a reproduction test first | ◎ | `/architect:review-issue` Step 4 | `test: reproduce <blocker>` commit before `fix:` on the working branch |
| Frontend component / routing / e2e tests | ◎ | `/product:generate-frontend` | `*.test.tsx` per component and page over composed stories, `e2e/` Playwright story flow, `vitest.config.ts` thresholds |
| Suite runtime budget / shape | ◎ | `rules/tdd-workflow.md` §6, `rules/ai-code-quality-gate.md` §Test quality | Wall-clock per task against the layer budget and tests per layer in `reports/09_verification/quality-gate.json` |
| Flaky-test policy | ◎ | `rules/tdd-workflow.md` §6 — quarantine by tag, counted and aged, never retried; seeded properties, masked characterization fixtures | Quarantined tests with age in `reports/09_verification/quality-gate.json`; follow-up Issues via `/architect:capture-followup` |
| Test naming from the ubiquitous language | ◎ | `rules/tdd-workflow.md` §6, `/architect:review-consistency` terminology dimension | `should_<outcome>_when_<condition>` in glossary terms; CON-3xx findings on test and scenario names |

## Deliberately not implemented

| Technique | Reason |
|-----------|--------|
| CRC cards | Superseded by the aggregate manifest, which records responsibilities and collaborators with a validator behind them |
| Three Amigos | A meeting format, not an artifact; `/product:example-map` produces what the meeting would |
| Impact Mapping | The `NSM-` → `FEAT-` traceability graph already answers "which deliverable serves which goal" |
| Event Modeling | Its three lanes are already the artifacts: commands and events in the aggregate manifest, state transitions and the state × event matrix in the state-machine manifest, cross-context flow in the Domain Event Catalog, read models in the CQRS section. A timeline-first rendering would be a fourth view of the same manifests with no validator of its own; the catalog's publisher → consumer diagram is the swimlane view |

## Updating this table

Change the row when its skill changes, in the same commit. A new technique gets a row with `×`
before it gets a skill, so the gap is visible rather than discovered by the next outside review.
