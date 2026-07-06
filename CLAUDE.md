# CLAUDE.md

Guidance for Claude Code in the **nexus-architect** repository.

## What This Is

Three-plugin system architecture toolkit:
- **product** — Product direction agent: validation-driven, dialogue-based pipeline from product vision to SLA/NFR; hands off to architect for system implementation design
- **architect** — System architecture agent for legacy refactoring, greenfield design, and consulting deliverables
- **scalardb** — ScalarDB application development toolkit

Workflows:
- **Product direction**: vision -> success metrics / revenue -> scope -> validate -> personas/journey/positioning -> domain-stories/design-system -> UI/features/data/frontend -> domains/API -> SLA/NFR -> review/report (handoff to `/architect:define-requirements`)
- **Legacy refactoring**: investigate -> analyze -> evaluate -> redesign -> implement
- **Greenfield design**: requirements -> domain modeling -> ScalarDB design -> infra -> deploy
- **Consulting deliverables**: reports, cost estimates, domain stories

Product direction skills: `/product:skill-name`. Architecture skills: `/architect:skill-name`. ScalarDB development tools: `/scalardb:skill-name`.
Use `/product:start` to design product direction, `/architect:start` for interactive system analysis/design selection, or `/architect:pipeline` for automated execution.

## Output Language

Output language is configurable per project. Set in `work/pipeline-progress.json`:
```json
{ "options": { "output_language": "ja" } }
```
Supported: `en` (English, default), `ja` (Japanese). The `/architect:start` orchestrator asks the user to select a language at project initialization.

## Command Reference

### Product Direction (`/product:*`)
Validation-driven pipeline from product vision to SLA/NFR. Skills are namespaced under `skills/product/`; rules under `rules/product/`. Use `/product:start` for interactive/automated execution; hands off to `/architect:define-requirements` for system implementation design.

- `/product:start [target] [--auto] [--profile=mvp|core-only|ux-to-spec|full] [--frontend|--no-frontend] [--lang=ja|en]` — Interactively start product-direction design; runs the validation-driven pipeline in dependency order, gating on the riskiest assumptions. After the UI mocks, offers a selectable `generate-frontend` step (React + Storybook codegen); `--frontend`/`--no-frontend` force the choice
- `/product:init-output [project]` — Initialize the product output tree, pipeline progress file, and traceability graph
- `/product:define-vision` — Define product core (Vision/Mission/Values) as a Product Vision via dialogue
- `/product:name-product` — Name the product as an alphabetic acronym: a short pronounceable Latin-letter name whose every letter is the initial of an English word, so the name expands into a value phrase; grounded in vision/positioning, shortlists candidates and recommends one
- `/product:define-success-metrics` — One North Star Metric plus 3–5 input metrics
- `/product:research-landscape` — Market/competitor research: market sizing (TAM/SAM/SOM), trends
- `/product:design-revenue` — Revenue/business model and a recomputable benefit-evaluation template
- `/product:define-scope` — Normalize constraints and decide product scope (in/out)
- `/product:validate-assumptions` — Extract riskiest assumptions, attach cheapest test, Go/No-Go gate (re-runnable)
- `/product:generate-persona` — Jobs-to-be-Done–anchored personas (job stories + persona cards)
- `/product:map-journey` — Customer journey as a stages × layers grid (touchpoints, actions, emotions)
- `/product:design-positioning` — Positioning (Dunford 5-component canvas), touchpoint × device × timing matrix
- `/product:create-domain-story` — Persona-anchored Domain Storytelling (actors=personas, activities=job stories/journey); the axis UI mocks render
- `/product:design-system` — Build or `--import` a separately-managed design system (DTCG tokens + components + guidelines); the visual language UI mocks render at lo/mid fidelity
- `/product:generate-ui-mock` — Navigable UI mocks for key screens, driven by domain stories and styled by the design system (each activity → a screen, wired into a clickable flow you can step through in story order; tokens injected)
- `/product:generate-frontend` — Turn UI mocks + design system into a runnable React + TypeScript frontend: Atomic Design decomposition (tokens→atoms→molecules→organisms→templates→pages), token-styled components (CSS Modules + CSS variables), react-router wiring from the story flow, and a Storybook story per component variant/state (emits `generated/frontend/`)
- `/product:define-features` — Extract features from UI mocks (each screen action becomes a Command/feature)
- `/product:define-data-model` — Derive data model from UI mocks and features (explicit → implicit, 2 passes)
- `/product:map-domains` — Abstract features/entities into bounded contexts (DDD strategic; Core/Supporting/Generic)
- `/product:design-api` — Logical API surface in three API-Led layers (System/Process/Experience)
- `/product:design-sla` — Per-service SLI/SLO/SLA with error budgets from customer expectations
- `/product:define-nfr` — Turn SLOs into measurable NFRs (availability, latency p95/p99, ...)
- `/product:review` — Review product artifacts through four lenses (consistency, traceability, ...)
- `/product:report [--auto] [--lang=ja|en]` — Consolidate artifacts into one self-contained HTML report (validation status first)
- `/product:adapt-change` — Re-propagation engine: compute affected scope from a change and re-run only impacted skills

### Orchestration
- `/architect:start [target_path]` — Interactively start system analysis and design
- `/architect:pipeline [target_path]` — Automated pipeline execution (--resume-from, --rerun-from, --skip-{phase}, --no-scalardb, --lang=en|ja)
- `/architect:init-output [project]` — Initialize output directories

### Requirements
- `/architect:define-requirements [target_path] [--input=<file|dir>] [--auto] [--no-scalardb]` — Requirements definition: FR/NFR classification, data/transaction requirements, ScalarDB applicability (greenfield entry point)

### Investigation & Analysis
- `/architect:investigate [target_path]` — Tech stack, structure, debt, DDD readiness
- `/architect:investigate-security [target_path]` — OWASP Top 10, access control
- `/architect:analyze [target_path]` — Ubiquitous language, actors, domain mapping
- `/architect:analyze-data-model [target_path]` — Data model, DB design, ER diagrams

### Evaluation
- `/architect:evaluate-mmi [target_path]` — MMI 4-axis qualitative evaluation
- `/architect:evaluate-ddd [target_path]` — DDD 12-criteria 3-layer evaluation
- `/architect:integrate-evaluations` — Merge MMI+DDD, improvement plan

### Design
- `/architect:map-domains` — Domain classification, BC mapping
- `/architect:redesign` — Bounded context redesign
- `/architect:create-domain-story [--domain=<name>] [--auto]` — Domain Storytelling: visualize business processes per domain (interactive 7-stage facilitation or auto-generation from analysis files)
- `/architect:design-microservices` — Target architecture
- `/architect:select-scalardb-edition` — ScalarDB edition selection
- `/architect:design-scalardb` — ScalarDB schema and transaction design
- `/architect:design-scalardb-analytics` — HTAP analytics platform design
- `/architect:design-data-layer` — Generic DB design (non-ScalarDB)
- `/architect:design-api` — REST/GraphQL/gRPC/AsyncAPI specs

### Implementation & Codegen
- `/architect:design-implementation` — Implementation specs
- `/architect:generate-test-specs` — BDD/unit/integration test specs
- `/architect:generate-scalardb-code` — Spring Boot + ScalarDB code generation
- `/architect:generate-infra-code` — K8s/Terraform/Helm code generation

### Infrastructure
- `/architect:design-infrastructure` — K8s, IaC, multi-environment
- `/architect:design-security` — Auth, secrets management
- `/architect:design-observability` — Monitoring, tracing, alerting
- `/architect:design-disaster-recovery` — RTO/RPO, backup, DR

### Review (5 parallel reviews — scalardb and data-integrity are mutually exclusive)
- `/architect:review-consistency` — Structural coherence (CON-)
- `/architect:review-scalardb` — ScalarDB constraints (SDB-) — runs when scalardb_enabled
- `/architect:review-data-integrity` — Data integrity (DIN-) — runs when scalardb_disabled
- `/architect:review-operations` — Operational readiness (OPS-)
- `/architect:review-risk` — Distributed system risks (RSK-)
- `/architect:review-business` — Business requirements (BIZ-)
- `/architect:review-synthesizer` — Consolidation and quality gate

### Reporting
- `/architect:report` — Markdown to HTML consolidated report
- `/architect:review-report` — Review quality of generated HTML report (completeness, score accuracy, Mermaid syntax, language, structure)
- `/architect:render-mermaid [target_path]` — Mermaid to PNG/SVG + syntax fix
- `/architect:estimate-cost` — Infrastructure, license, operational costs

### ScalarDB Development (`/scalardb:*`)
- `/scalardb:model` — Interactive schema design wizard (keys, indexes, data types)
- `/scalardb:config` — Configuration file generator (Core/Cluster, CRUD/JDBC, 1PC/2PC)
- `/scalardb:scaffold` — Complete starter project generator (all 6 interface combos)
- `/scalardb:error-handler` — Exception handling code generator and code reviewer
- `/scalardb:crud-ops` — CRUD API operation patterns (Get, Scan, Insert, Upsert, Update, Delete)
- `/scalardb:jdbc-ops` — JDBC/SQL operation patterns (SELECT, INSERT, JOIN, aggregates)
- `/scalardb:local-env` — Local Docker Compose environment setup
- `/scalardb:docs` — ScalarDB documentation search and lookup
- `/scalardb:build-app` — Build complete ScalarDB application from requirements
- `/scalardb:review-code` — Review Java code for ScalarDB correctness (16 checks)
- `/scalardb:migrate` — Migration advisor (Core→Cluster, CRUD→JDBC, 1PC→2PC)

### Database Migration (Oracle/MySQL/PostgreSQL → ScalarDB)
- `/architect:migrate-database` — Unified migration router (detects DB type, delegates)
- `/architect:migrate-oracle` — Oracle → ScalarDB (schema extraction, analysis, AQ integration, SP/trigger Java conversion)
- `/architect:migrate-mysql` — MySQL → ScalarDB (schema extraction, analysis, SP/trigger Java conversion)
- `/architect:migrate-postgresql` — PostgreSQL → ScalarDB (schema extraction, analysis, SP/trigger Java conversion)

## Pipeline Dependencies

```
investigate -> analyze -> [evaluate-mmi, evaluate-ddd] -> integrate-evaluations
  -> redesign -> [create-domain-story (optional, per domain)]
  -> design-microservices -> [design-scalardb | design-data-layer, design-api]
  -> [review-consistency, review-scalardb|review-data-integrity, review-operations, review-risk, review-business]
  -> review-synthesizer -> report -> review-report
```

Dependency manifest (architect): @skills/common/skill-dependencies.yaml

The **product** plugin has its own pipeline and manifest: `skills/product/common/skill-dependencies.yaml` (vision -> success-metrics/revenue -> scope -> validate-assumptions [gate] -> persona/journey/positioning -> create-domain-story/design-system -> ui-mock/features/data-model/frontend -> map-domains/api -> sla/nfr -> review -> report; `adapt-change` on demand). It ends by handing off to `/architect:define-requirements`.

## Output Conventions

All outputs are git-ignored:

```
reports/                    # Analysis and design documents
generated/                  # Generated code per service
work/                       # Pipeline state, intermediate files
```

Naming and frontmatter rules: @rules/output-conventions.md

## Model Assignment

| Model | Use For | Examples |
|-------|---------|----------|
| **opus** | Architecture decisions, tradeoff analysis, risk | review-risk, redesign, design-microservices |
| **sonnet** | Standard analysis, document generation, reviews | analyze, review-consistency, report |
| **haiku** | Template generation, status checks, simple transforms | init-output, render-mermaid |

The **product** plugin follows the same tiers (per-skill `model` in `skills/product/common/skill-dependencies.yaml`): **opus** for strategy/judgment (`define-vision`, `validate-assumptions`, `design-positioning`, `map-domains`, `design-api`, `review`, `adapt-change`), **sonnet** for structured generation (`define-scope`, `generate-ui-mock`, `generate-frontend`, `define-features`, `design-sla`, `define-nfr`, `report`, and the `start` orchestrator).

## Tool Priority

1. **Serena MCP** (get_symbols_overview, find_symbol) — structural understanding
2. **Glob/Grep** — file discovery and pattern search
3. **Read** — targeted file reading
4. **Task (sub-agent)** — large-scale exploration across many files

## Rules & References

Read these files on demand with the Read tool when the "When to Read" condition applies.
They are intentionally NOT auto-imported (no `@` prefix) to keep session context small —
do not load ScalarDB rules for non-ScalarDB work.

| Resource | Location | When to Read |
|----------|----------|--------------|
| ScalarDB exception handling | rules/scalardb-exception-handling.md | Exception handling, retry logic |
| ScalarDB CRUD patterns | rules/scalardb-crud-patterns.md | CRUD API operations |
| ScalarDB JDBC patterns | rules/scalardb-jdbc-patterns.md | JDBC/SQL operations |
| ScalarDB 2PC patterns | rules/scalardb-2pc-patterns.md | Two-phase commit protocol |
| ScalarDB config validation | rules/scalardb-config-validation.md | Configuration correctness |
| ScalarDB schema design | rules/scalardb-schema-design.md | Schema and key design |
| ScalarDB Java best practices | rules/scalardb-java-best-practices.md | Java coding standards |
| ScalarDB coding patterns | rules/scalardb-coding-patterns.md | Code generation, design-scalardb, generate-scalardb-code |
| ScalarDB edition profiles | rules/scalardb-edition-profiles.md | Edition selection |
| Evaluation frameworks | rules/evaluation-frameworks.md | MMI/DDD scoring |
| Mermaid best practices | rules/mermaid-best-practices.md | Creating diagrams |
| Spring Boot integration | rules/spring-boot-integration.md | Java code generation |
| Output structure contract | templates/output-structure.md | File dependencies |
| Sub-agent patterns | skills/common/sub-agent-patterns.md | Spawning sub-agents |
| Progress registry | skills/common/progress-registry.md | pipeline-progress.json schema and resume behavior |
| API reference | skills/common/references/api-reference.md | ScalarDB API details |
| Interface matrix | skills/common/references/interface-matrix.md | 6 interface combinations |
| Exception hierarchy | skills/common/references/exception-hierarchy.md | Exception decision tree |
| SQL reference | skills/common/references/sql-reference.md | SQL grammar and limitations |
| Schema format | skills/common/references/schema-format.md | JSON/SQL schema format |
| Configuration reference | skills/common/references/configuration-reference.md | All ScalarDB config properties by backend |
| Code patterns | skills/common/references/code-patterns/ | Complete app templates for all 6 interface combos |

## Conventions

- **Output language**: Configurable per project (`en` default, `ja` supported)
- **File naming**: kebab-case for all generated files
- **Frontmatter**: Every output file must include YAML frontmatter with `schema_version`
- **Diagrams**: All diagrams use Mermaid syntax (validated by hook)
- **Immediate output**: Each skill step writes its output file upon completion
- **ScalarDB-optional**: When ScalarDB is not used, ScalarDB-specific skills are skipped and review-data-integrity replaces review-scalardb
