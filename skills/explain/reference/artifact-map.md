# Artifact Map

Where each pipeline writes, used by Step 1 when a file has no `skill` in its frontmatter and no
`work/pipeline-progress.json` entry lists it. The manifests
(`skills/common/skill-dependencies.yaml`, `skills/product/common/skill-dependencies.yaml`) and
`templates/output-structure.md` are the source; this is a reading aid, not a contract. When a file
here disagrees with them, trust them.

## Product pipeline (`/product:*`)

| Location | Producer | What it is |
|----------|----------|------------|
| `reports/00_core/vision-mission-value.md`, `pr-faq.md` | `define-vision` | Product Vision Board and Amazon-style PR-FAQ |
| `reports/00_core/success-metrics.md` | `define-success-metrics` | North Star Metric, input metrics, guardrails |
| `reports/00_core/market-landscape.md` | `research-landscape` | TAM/SAM/SOM, competitors, Kano classification |
| `reports/00_core/revenue-model.md`, `benefit-evaluation.md` | `design-revenue` | Lean Canvas, revenue model, unit-economics formulas |
| `reports/00_core/constraints.md`, `scope-definition.md` | `define-scope` | Constraints, MoSCoW / RICE scope |
| `reports/00_core/product-name.md` | `name-product` | Acronym name candidates and the choice |
| `reports/00_core/assumptions.md`, `validation-plan.md` | `validate-assumptions` | Riskiest assumptions, tests, Go/No-Go |
| `reports/01_ux/personas.md` | `generate-persona` | JTBD job stories and persona cards |
| `reports/01_ux/journey-maps.md` | `map-journey` | Stages × layers journey grid |
| `reports/01_ux/positioning.md` | `design-positioning` | Positioning canvas, touchpoint matrix, Hook loop |
| `reports/01_ux/domain-stories/` | `product:create-domain-story` | Persona-anchored domain stories |
| `design-system/` | `design-system` | DTCG tokens, component inventory, usage guidelines |
| `reports/02_spec/ui-mocks/` | `generate-ui-mock` | Navigable HTML mocks |
| `reports/02_spec/feature-list.md` | `define-features` | Features traced to jobs, journeys and metrics |
| `reports/02_spec/examples/` | `example-map` | Rules (`RULE-`), examples (`EX-`), questions |
| `reports/02_spec/data-model.md` | `define-data-model` | Two-pass data model and ER diagram |
| `generated/frontend/` | `generate-frontend` | React + TypeScript, Atomic Design, Storybook |
| `reports/03_domain/domain-map.md`, `bounded-contexts.md`, `ubiquitous-language.md` | `product:map-domains` | Strategic DDD: subdomains, context map, glossary |
| `reports/03_domain/api-design.md` | `product:design-api` | API-led layers: System / Process / Experience |
| `reports/03_domain/architecture.md`, `tech-stack-fitness.md` | `design-architecture` | Runtime architecture, Adopt/Conditional/Reject |
| `reports/04_quality/sla.md`, `nfr.md` | `design-sla`, `define-nfr` | SLI/SLO/SLA, error budgets, measurable NFRs |
| `reports/report/review.md`, `full-report.html` | `product:review`, `product:report` | Four-lens review, consolidated report |
| `reports/05_adaptation/` | `adapt-change` | Change log and impact analysis |

## Architect pipeline (`/architect:*`)

| Location | Producer | What it is |
|----------|----------|------------|
| `reports/00_requirements/` | `define-requirements` | FR/NFR, data and transaction requirements, ScalarDB applicability, Open Questions view; `examples/` holds the example maps (`RULE-`, `EX-`) for requirements product did not map |
| `reports/before/{project}/` | `investigate`, `analyze-ui` | As-is technology, structure, debt, UI inventory |
| `reports/01_analysis/` | `analyze`, `analyze-data-model` | Ubiquitous language, actors, domain-code mapping, current data model |
| `reports/02_evaluation/` | `evaluate-mmi`, `evaluate-ddd`, `evaluate-ux`, `integrate-evaluations` | Scores and the unified improvement plan |
| `reports/03_design/` | `map-domains`, `redesign`, `design-microservices`, `design-scalardb` / `design-data-layer`, `design-api`, `design-graphql` | Bounded contexts, context map, target architecture, transformation plan, data layer, API specifications |
| `reports/03_design/aggregates/`, `state-machines/` | `design-aggregate`, `design-state-machine` | Tactical model and lifecycles (canonical `*-manifest.json` plus views) |
| `reports/03_design/adr/` | `redesign` and later design skills | Architecture Decision Records |
| `reports/04_stories/` | `architect:create-domain-story` | Domain stories per domain |
| `reports/05_estimate/` | `estimate-cost`, `estimate-token-cost` | Cost estimates |
| `reports/06_implementation/` | `design-implementation`, `generate-test-specs`, the codegen skills | Implementation specs, test specs, contract maps |
| `reports/08_infrastructure/` | `design-infrastructure`, `design-security`, `design-observability`, `design-disaster-recovery`, `/infra:*` | Infrastructure, security, observability and DR design |
| `reports/09_verification/` | `verify-implementation`, `review-api-security`, `verify-sql-migration` | Verification and quality-gate results |
| `reports/review/` | `review-*`, `review-synthesizer`, `review-report` | Parallel review results and the synthesis |
| `reports/backlog/` | Backlog Delivery skills | Backlog plan, manifest, implementation logs, reviews |
| `reports/00_summary/full-report.html` | `report` | Consolidated HTML report |

## Generated code (`generated/`)

| Location | Producer | What it is |
|----------|----------|------------|
| `generated/{service}/src/main/java/` | `generate-scalardb-code`, `generate-api-code`, `generate-graphql-code` | Domain, infrastructure (ScalarDB) and API layers of one service |
| `generated/{service}/src/test/` | `generate-contract-tests`, `generate-acceptance-tests` | Contract tests and the ATDD outer loop |
| `generated/characterization/{module}/` | `generate-characterization-tests` | Tests pinning the current behaviour of legacy modules |
| `generated/infrastructure/` | `generate-infra-code` | Terraform, Kubernetes, Helm, the quality-gate CI workflow |
| `generated/sql-migration/` | `implement-sql-migration` | ScalarDB SQL, schema, application-side skeletons |
| `generated/frontend/` | `product:generate-frontend` | See the product table |

Merge-bound code written by `/architect:implement-backlog` or `/infra:implement` lives in the
project's own source tree, not here; its design inputs are the same reports.

## Shared files (`work/`)

`pipeline-progress.json` (one `phases` map for both pipelines, with a `plugin` field per entry),
`traceability.json` (one ID graph: `FR-`, `NFR-`, `RULE-`, `ADR-` and the rest, with their edges)
and `context.md` (decisions and the Open Questions store). They explain *why* and *what links to
what*; cite them like any other file.
