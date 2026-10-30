# Pattern Catalogue

Read before explaining any pattern (Step 6, Patterns). Each row gives the signals that justify
naming the pattern in *this* project and the repository file that governs it. Name a pattern only
when its signals are present; when only some are, say "looks like X, but …" and name what is
missing. When a row names a rule file, read the section it points to and explain the pattern as
that rule states it — the rule is how this toolkit designed and generated the artifact, so it is
the authority on what the project's version means. Without a rule file, the explanation is a
Concept from general knowledge and is labelled so. A governing file is listed only when it
defines or decides the pattern, not when it merely mentions it; `skills/explain/pattern-catalog.test.py`
checks that each one does.

Paths below are relative to the plugin root (`${CLAUDE_PLUGIN_ROOT}`).

## Architecture patterns

| Pattern | Signals in the project | Governing file |
|---------|------------------------|----------------|
| Bounded Context / Context Map | `bounded-contexts*.md`, `context-map.md`; relationship labels (Customer-Supplier, ACL, Published Language) | `rules/product/ddd-strategic.md`, `skills/redesign/SKILL.md` |
| Microservices (database per service) | One `generated/{service}/` per context; one schema or namespace per service in the data-layer design | `skills/design-microservices/SKILL.md` |
| Hexagonal / Ports and Adapters, Clean Architecture | `domain/` with no framework imports; port interfaces implemented under `infrastructure/`; `--layering=ddd\|clean` recorded in the implementation spec | `skills/design-implementation/SKILL.md`, `rules/tdd-workflow.md` (Fake per port) |
| Layered (controller → service → repository) | `controller`, `service`, `repository` packages; DTOs at the edge | `skills/design-implementation/SKILL.md` |
| API Gateway / Backend for Frontend | `api-gateway-design.md`; Experience APIs per channel | `skills/design-api/SKILL.md` (gateway), `rules/product/api-led-connectivity.md` (Experience API as BFF) |
| API-led connectivity (System / Process / Experience) | The three layers in `reports/03_domain/api-design.md` | `rules/product/api-led-connectivity.md` |
| Contract-first API | OpenAPI / SDL under `api-specifications/`; `operationId` bound in a contract map; contract tests | `rules/api-contract-fidelity.md`, `rules/graphql-contract-fidelity.md` |
| Event-driven integration, Domain Events | `domain-event-catalog.json`; publishers and consumers per event; delivery contract | `skills/design-aggregate/SKILL.md` § Domain Event Catalog |
| Saga (orchestration or choreography), TCC | Compensation steps; ScalarDB Saga definitions; per-step idempotency keys. Orchestration: one coordinator issues every step's command. Choreography: each participant reacts to the previous step's event, with no coordinator | `rules/scalardb-saga-patterns.md` |
| Two-phase commit across services | ScalarDB `TwoPhaseCommitTransaction`; coordinator / participant roles | `rules/scalardb-2pc-patterns.md` |
| Shared cluster / Global transaction | One ScalarDB cluster spanning services' namespaces | `rules/scalardb-2pc-patterns.md` |
| Strangler Fig | Transformation plan with stepwise extraction from the monolith; characterization tests gating each step | `skills/generate-characterization-tests/SKILL.md` (pinning behaviour before a module is strangled), `skills/design-microservices/SKILL.md` (the incremental transformation plan; it does not use the name) |
| HTAP / analytics separation | ScalarDB Analytics, Spark catalog | `skills/design-scalardb-analytics/SKILL.md` |
| GitOps, immutable images | Argo CD applications, image digests, Cosign signatures | `rules/okf-k8s-tf-bundle.md` |
| Architecture Decision Records | `adr-NNN-*.md` with MADR headings | `rules/architecture-decision-records.md` |

## Implementation patterns

| Pattern | Signals in the project | Governing file |
|---------|------------------------|----------------|
| Aggregate (root, invariants, one transaction per command) | `aggregate-manifest.json`; a root class guarding invariants; references to other aggregates by ID | `rules/aggregate-design.md` |
| Entity / Value Object | Immutable value types with equality by value; entities with identity | `rules/aggregate-design.md` |
| Repository | One repository interface per aggregate root in `domain/`, implemented in `infrastructure/` | `rules/aggregate-design.md` |
| Domain Service / Application Service | Use-case classes orchestrating aggregates and transactions | `skills/design-implementation/SKILL.md` |
| Factory, Specification | `create(...)` factories; predicate objects named for a rule | `rules/aggregate-design.md` |
| State machine | `state-machine-manifest.json`; transition methods rejecting illegal events | `rules/state-modeling.md` |
| Transaction boundary / Unit of Work | `begin` → `commit` / `abort` in one application-service method | `rules/scalardb-crud-patterns.md`, `rules/scalardb-jdbc-patterns.md` |
| Optimistic concurrency and retry | Conflict exceptions caught and the transaction retried with backoff | `rules/scalardb-exception-handling.md` |
| Unknown-outcome handling | `UnknownTransactionStatusException` branch; status check before retry | `rules/scalardb-exception-handling.md`, `rules/api-error-standard.md` |
| Idempotency key | Header or field deduplicating retried commands | `rules/api-contract-fidelity.md`, `rules/scalardb-saga-patterns.md` |
| Problem Details error responses | `application/problem+json`, problem type registry, exception handler mapping | `rules/api-error-standard.md` |
| DTO mapping and validation at the edge | Request/response DTOs, Bean Validation annotations | `skills/design-implementation/SKILL.md`, `rules/api-contract-fidelity.md` |
| DataLoader batching | GraphQL `@BatchMapping` / DataLoader per request, tenant-partitioned | `rules/graphql-security-checks.md` |
| Tenant isolation | Tenant ID in keys and in every query; authorization per operation | `rules/api-security-checks.md` |
| Test-first (Red → Green → Refactor), ATDD | `test:` → `feat:` → `refactor:` commits; Gherkin scenarios as the outer loop; a Fake per port; an injected Clock | `rules/tdd-workflow.md` |
| Contract tests, characterization tests | Tests generated from the contract; tests pinning legacy behaviour | `rules/api-contract-fidelity.md`, `skills/generate-characterization-tests/SKILL.md` |
| Quality gate | The eight stages in CI | `rules/ai-code-quality-gate.md` |
| Atomic Design components, Storybook | `atoms/`, `molecules/`, `organisms/`; a story per variant | `rules/product/atomic-react-storybook.md` |
| Design tokens (DTCG) | `$value` / `$type` token JSON consumed by components | `rules/product/design-system.md` |

## Legacy shapes

What the legacy path usually finds before the redesign. Explaining them is how the reader sees what
the target design changes; name them as observations, not as faults to be scored. No rule in this
toolkit defines these shapes, so they are explained as Concepts; what makes them Facts is the
project's own record of them, in the output the last column names.

| Shape | Signals in the project | Governing file | Where the project records it |
|-------|------------------------|----------------|------------------------------|
| Transaction Script | One service method per use case doing reads, rules and writes in sequence; entities with getters and setters only | — | `reports/before/{project}/issues-and-debt.md`, `reports/02_evaluation/ddd-tactical-architecture-evaluation.md` |
| Anemic domain model | Entities with no behaviour; every rule in services | — | `reports/before/{project}/issues-and-debt.md`, `reports/02_evaluation/ddd-tactical-architecture-evaluation.md` |
| God service / shared database | One service class touching most tables; several modules writing the same tables | `skills/evaluate-mmi/SKILL.md` (god-class as low cohesion) | `reports/02_evaluation/mmi-by-module.md`, `reports/before/{project}/issues-and-debt.md` |
| Framework-owned repository | Spring Data / JPA repositories exposing every entity, not one per aggregate root | `rules/aggregate-design.md` (the target it departs from) | `reports/01_analysis/domain-code-mapping.md` |

## Product frameworks

The patterns of a product document. Explain the framework, then how this project filled it in.

| Framework | Where it appears | Governing file |
|-----------|------------------|----------------|
| Product Vision Board, PR-FAQ | `vision-mission-value.md`, `pr-faq.md` | `rules/product/vision-frameworks.md` |
| North Star Metric, input metrics, guardrails | `success-metrics.md` | `rules/product/success-metrics.md` |
| TAM / SAM / SOM, Kano | `market-landscape.md` | `skills/product/research-landscape/SKILL.md`, `rules/product/positioning-kano-hook.md` (Kano) |
| Lean Canvas, unit economics (LTV/CAC, payback) | `revenue-model.md`, `benefit-evaluation.md` | `rules/product/revenue-models.md` |
| MoSCoW, RICE | `scope-definition.md`, `feature-list.md` | `rules/product/scope-prioritization.md` |
| Riskiest assumption test, Go/No-Go gate | `assumptions.md`, `validation-plan.md` | `rules/product/assumption-validation.md` |
| Jobs-to-be-Done, proto-persona | `personas.md` | `rules/product/persona-jtbd.md` |
| Customer journey map, Moments of Truth | `journey-maps.md` | `rules/product/journey-mapping.md` |
| Positioning canvas, Fogg model, Hook model | `positioning.md` | `rules/product/positioning-kano-hook.md` |
| Acronym naming | `product-name.md` | `rules/product/naming-frameworks.md` |
| Domain Storytelling | `domain-stories/` | `skills/create-domain-story/SKILL.md` |
| EventStorming | `event-timeline.md`, a domain map found in a Big Picture walk | `rules/product/event-storming.md` |
| Example Mapping | `examples/` | `rules/product/example-mapping.md` |
| UI-to-domain derivation | `feature-list.md`, `data-model.md` from the mocks | `rules/product/ui-to-domain.md` |
| SLI / SLO / SLA, error budget | `sla.md`, `nfr.md` | `rules/product/sla-nfr.md` |
| Technology fitness (Adopt / Conditional / Reject) | `tech-stack-fitness.md` | `rules/product/architecture-and-tech-fitness.md` |
| Change propagation over a traceability graph | `reports/05_adaptation/` | `rules/product/adaptation-engine.md` |
