# Nexus Architect Skill Reference

Skills are invoked by plugin namespace: `/product:skill-name` (product direction),
`/architect:skill-name` (system architecture), and `/scalardb:skill-name` (ScalarDB development).
The architect skills are catalogued first, followed by ScalarDB Development, Database Migration,
and Product Direction.

## Orchestration

| Command | Model | Description |
|---------|-------|-------------|
| `/architect:start` | sonnet | Interactively start system analysis and design |
| `/architect:pipeline` | sonnet | Automated pipeline execution (--resume-from, --rerun-from, --skip-{phase}, --no-scalardb, --lang) |

## Requirements

| Command | Model | Description |
|---------|-------|-------------|
| `/architect:define-requirements` | opus | Requirements definition: FR/NFR classification, data/transaction requirements, ScalarDB applicability (greenfield entry point; supports --input, --auto, --no-scalardb) |

## Investigation

| Command | Model | Description |
|---------|-------|-------------|
| `/architect:investigate` | sonnet | Tech stack, structure, debt, DDD readiness survey |
| `/architect:investigate-security` | sonnet | OWASP Top 10, access control assessment |

## Analysis

| Command | Model | Description |
|---------|-------|-------------|
| `/architect:analyze` | opus | Ubiquitous language, actors, domain mapping |
| `/architect:analyze-data-model` | sonnet | Data model, DB design, ER diagrams |

## Evaluation

| Command | Model | Description |
|---------|-------|-------------|
| `/architect:evaluate-mmi` | sonnet | MMI 4-axis qualitative evaluation |
| `/architect:evaluate-ddd` | sonnet | DDD 12-criteria 3-layer evaluation |
| `/architect:integrate-evaluations` | sonnet | MMI+DDD integration, improvement plan |

## Design

| Command | Model | Condition | Description |
|---------|-------|-----------|-------------|
| `/architect:map-domains` | opus | - | Domain classification, BC mapping |
| `/architect:redesign` | opus | - | Bounded context redesign |
| `/architect:create-domain-story` | opus | Optional | Domain Storytelling: visualize business processes per domain |
| `/architect:design-microservices` | opus | - | Target architecture |
| `/architect:select-scalardb-edition` | sonnet | ScalarDB | Edition selection |
| `/architect:design-scalardb` | opus | ScalarDB | Schema and transaction design |
| `/architect:design-scalardb-analytics` | sonnet | Premium | HTAP analytics platform design |
| `/architect:design-data-layer` | opus | Non-ScalarDB | Generic DB design |
| `/architect:design-api` | opus | - | REST/GraphQL/gRPC/AsyncAPI |

## Implementation

| Command | Model | Description |
|---------|-------|-------------|
| `/architect:design-implementation` | opus | Implementation specifications (services, repositories, VOs) |
| `/architect:generate-test-specs` | sonnet | BDD/unit/integration test specifications |
| `/architect:generate-scalardb-code` | opus | Spring Boot + ScalarDB code generation |
| `/architect:generate-infra-code` | sonnet | K8s/Terraform/Helm code generation |

## Review

| Command | Model | ID Prefix | Description |
|---------|-------|-----------|-------------|
| `/architect:review-consistency` | sonnet | CON- | Structural coherence |
| `/architect:review-scalardb` | sonnet | SDB- | ScalarDB constraints |
| `/architect:review-data-integrity` | sonnet | DIN- | Data integrity (non-ScalarDB) |
| `/architect:review-operations` | sonnet | OPS- | Operational readiness |
| `/architect:review-risk` | opus | RSK- | Distributed system risks |
| `/architect:review-business` | sonnet | BIZ- | Business requirements |
| `/architect:review-synthesizer` | sonnet | SYN- | Consolidation and quality gate |

## Infrastructure

| Command | Model | Description |
|---------|-------|-------------|
| `/architect:design-infrastructure` | opus | K8s, IaC, multi-environment |
| `/architect:design-security` | sonnet | Authentication, authorization, secrets management |
| `/architect:design-observability` | sonnet | Monitoring, tracing, alerting |
| `/architect:design-disaster-recovery` | sonnet | RTO/RPO, backup, DR |

## Reporting

| Command | Model | Description |
|---------|-------|-------------|
| `/architect:report` | haiku | Markdown to HTML consolidated report |
| `/architect:review-report` | sonnet | Review the quality of the generated HTML report (completeness, score accuracy, Mermaid syntax) |
| `/architect:render-mermaid` | haiku | Mermaid to PNG/SVG + syntax fix |
| `/architect:estimate-cost` | sonnet | Infrastructure, license, and operational costs |

## Utility

| Command | Model | Description |
|---------|-------|-------------|
| `/architect:init-output` | haiku | Initialize output directories |

## ScalarDB Development

| Command | Model | Description |
|---------|-------|-------------|
| `/scalardb:model` | sonnet | Interactive schema design wizard (keys, indexes, data types) |
| `/scalardb:config` | sonnet | Configuration file generator (6 interface combinations) |
| `/scalardb:scaffold` | sonnet | Complete starter project generator |
| `/scalardb:error-handler` | sonnet | Exception handling code generator and code reviewer |
| `/scalardb:crud-ops` | sonnet | CRUD API operation patterns guide |
| `/scalardb:jdbc-ops` | sonnet | JDBC/SQL operation patterns guide |
| `/scalardb:local-env` | sonnet | Docker Compose local environment setup |
| `/scalardb:docs` | sonnet | ScalarDB documentation search |
| `/scalardb:build-app` | opus | Build complete application from domain requirements |
| `/scalardb:review-code` | sonnet | Java code review (16 check categories) |
| `/scalardb:migrate` | sonnet | Migration advisor (Core/Cluster, CRUD/JDBC, 1PC/2PC) |

See [ScalarDB Development Guide](scalardb-development.md) for detailed usage.

## Database Migration

| Command | Model | Database | Description |
|---------|-------|----------|-------------|
| `/architect:migrate-database` | sonnet | All | Unified migration router (auto-detects DB type) |
| `/architect:migrate-oracle` | sonnet | Oracle | Full pipeline: schema extraction, analysis, AQ integration, SP/trigger conversion |
| `/architect:migrate-mysql` | sonnet | MySQL | Full pipeline: schema extraction, analysis, SP/trigger conversion |
| `/architect:migrate-postgresql` | sonnet | PostgreSQL | Full pipeline: schema extraction, analysis, PL/pgSQL conversion |

See [Database Migration Guide](database-migration.md) for detailed usage.

## Product Direction

All skills are invoked as `/product:skill-name`. Validation-driven pipeline from product vision
to SLA/NFR; hands off to `/architect:define-requirements` for system implementation design.
Phase order and the `mvp`/`core-only`/`ux-to-spec`/`full` profiles are defined in
`skills/product/common/skill-dependencies.yaml`.

| Command | Model | Phase | Description |
|---------|-------|-------|-------------|
| `/product:start` | sonnet | Orchestration | Interactively start product-direction design; runs the pipeline in dependency order, gating on the riskiest assumptions; offers a selectable `generate-frontend` step after the mocks (`--auto`, `--profile`, `--frontend`/`--no-frontend`, `--lang`) |
| `/product:init-output` | sonnet | Orchestration | Initialize the product output tree, `work/pipeline-progress.json`, and `work/traceability.json` |
| `/product:define-vision` | opus | 1. Product Core | Define product core (Vision/Mission/Values) as a Product Vision Board plus PR-FAQ |
| `/product:name-product` | opus | 1. Product Core | Name the product as an acronym — a short pronounceable Latin-letter name whose every letter is the initial of an English word, expanding into a value phrase grounded in vision/positioning; shortlists candidates, recommends one (optional; in `full`) |
| `/product:define-success-metrics` | opus | 1. Product Core | One North Star Metric plus 3–5 input metrics |
| `/product:research-landscape` | opus | 1. Product Core | Market/competitor research: sizing (TAM/SAM/SOM), trends, Kano classification |
| `/product:design-revenue` | opus | 1. Product Core | Revenue/business model and a recomputable benefit-evaluation template |
| `/product:define-scope` | sonnet | 1. Product Core | Normalize constraints and decide product scope (in/out) |
| `/product:validate-assumptions` | opus | Gate | Extract riskiest assumptions, attach cheapest test and Go/No-Go (re-runnable) |
| `/product:generate-persona` | opus | 2. UX Foundation | Jobs-to-be-Done–anchored personas (job stories + persona cards) |
| `/product:map-journey` | sonnet | 2. UX Foundation | Customer journey as a stages × layers grid (touchpoints, actions, emotions) |
| `/product:design-positioning` | opus | 2. UX Foundation | Positioning (Dunford 5-component canvas), touchpoint × device × timing matrix |
| `/product:create-domain-story` | opus | 2. UX Foundation | Persona-anchored Domain Storytelling (actors=personas, activities=job stories ordered by journey); the axis the UI mocks render (optional) |
| `/product:design-system` | opus | 2. UX Foundation | Build or `--import` a separately-managed design system (DTCG tokens + components + guidelines); styles the UI mocks (optional, standalone) |
| `/product:generate-ui-mock` | sonnet | 3. UX → Spec | Navigable UI mocks for key screens, driven by domain stories and styled by the design system (each activity → a screen, wired into a clickable story flow) |
| `/product:define-features` | sonnet | 3. UX → Spec | Extract features from UI mocks (each screen action → Command/feature) |
| `/product:define-data-model` | opus | 3. UX → Spec | Derive the data model in two passes (explicit → implicit) |
| `/product:generate-frontend` | sonnet | 3. UX → Spec | Turn UI mocks + design system into a runnable React + Storybook frontend (Atomic Design, token-styled, react-router) — selectable, end of spec phase |
| `/product:map-domains` | opus | 4. Domain & API | Abstract features/entities into bounded contexts (DDD strategic) |
| `/product:design-api` | opus | 4. Domain & API | Logical API surface in three API-Led layers (System/Process/Experience) |
| `/product:design-sla` | sonnet | 5. Quality & NFR | Per-service SLI/SLO/SLA with error budgets |
| `/product:define-nfr` | sonnet | 5. Quality & NFR | Turn SLOs into measurable NFRs (availability, latency p95/p99, ...) |
| `/product:design-architecture` | opus | 4/5. Synthesis | Runtime architecture diagrams (container/critical-path/deployment) + technology fitness (Kong / ScalarDB / ScalarDB Analytics / ScalarDL) with Adopt/Conditional/Reject rationale |
| `/product:review` | opus | R. Review & Report | Review product artifacts (consistency, traceability, extensibility, strategy) |
| `/product:report` | sonnet | R. Review & Report | Consolidate artifacts into one self-contained HTML report (validation status first) |
| `/product:adapt-change` | opus | 6. Adaptation | Re-propagation engine: compute affected scope from a change and re-run only impacted skills |
