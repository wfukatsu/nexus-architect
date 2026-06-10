# CLAUDE.md

Guidance for Claude Code in the **nexus-architect** repository.

## What This Is

Two-plugin system architecture toolkit:
- **architect** — System architecture agent for legacy refactoring, greenfield design, and consulting deliverables
- **scalardb** — ScalarDB application development toolkit

Workflows:
- **Legacy refactoring**: investigate -> analyze -> evaluate -> redesign -> implement
- **Greenfield design**: requirements -> domain modeling -> ScalarDB design -> infra -> deploy
- **Consulting deliverables**: reports, cost estimates, domain stories

Architecture skills: `/architect:skill-name`. ScalarDB development tools: `/scalardb:skill-name`.
Use `/architect:start` for interactive selection or `/architect:pipeline` for automated execution.

## Output Language

Output language is configurable per project. Set in `work/pipeline-progress.json`:
```json
{ "options": { "output_language": "ja" } }
```
Supported: `en` (English, default), `ja` (Japanese). The `/architect:start` orchestrator asks the user to select a language at project initialization.

## Command Reference

### Orchestration
- `/architect:start [target_path]` — Interactively start system analysis and design
- `/architect:pipeline [target_path]` — Automated pipeline execution (--resume-from, --rerun-from, --skip-{phase}, --no-scalardb, --lang=en|ja)
- `/architect:init-output [project]` — Initialize output directories

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

Dependency manifest: @skills/common/skill-dependencies.yaml

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

## Tool Priority

1. **Serena MCP** (get_symbols_overview, find_symbol) — structural understanding
2. **Glob/Grep** — file discovery and pattern search
3. **Read** — targeted file reading
4. **Task (sub-agent)** — large-scale exploration across many files

## Rules & References

| Resource | Location | When to Read |
|----------|----------|--------------|
| ScalarDB exception handling | @rules/scalardb-exception-handling.md | Exception handling, retry logic |
| ScalarDB CRUD patterns | @rules/scalardb-crud-patterns.md | CRUD API operations |
| ScalarDB JDBC patterns | @rules/scalardb-jdbc-patterns.md | JDBC/SQL operations |
| ScalarDB 2PC patterns | @rules/scalardb-2pc-patterns.md | Two-phase commit protocol |
| ScalarDB config validation | @rules/scalardb-config-validation.md | Configuration correctness |
| ScalarDB schema design | @rules/scalardb-schema-design.md | Schema and key design |
| ScalarDB Java best practices | @rules/scalardb-java-best-practices.md | Java coding standards |
| ScalarDB coding patterns | @rules/scalardb-coding-patterns.md | Code generation, design-scalardb, generate-scalardb-code |
| ScalarDB edition profiles | @rules/scalardb-edition-profiles.md | Edition selection |
| Evaluation frameworks | @rules/evaluation-frameworks.md | MMI/DDD scoring |
| Mermaid best practices | @rules/mermaid-best-practices.md | Creating diagrams |
| Spring Boot integration | @rules/spring-boot-integration.md | Java code generation |
| Output structure contract | @templates/output-structure.md | File dependencies |
| Sub-agent patterns | @skills/common/sub-agent-patterns.md | Spawning sub-agents |
| Progress registry | @skills/common/progress-registry.md | pipeline-progress.json schema and resume behavior |
| API reference | @skills/common/references/api-reference.md | ScalarDB API details |
| Interface matrix | @skills/common/references/interface-matrix.md | 6 interface combinations |
| Exception hierarchy | @skills/common/references/exception-hierarchy.md | Exception decision tree |
| SQL reference | @skills/common/references/sql-reference.md | SQL grammar and limitations |
| Schema format | @skills/common/references/schema-format.md | JSON/SQL schema format |
| Configuration reference | @skills/common/references/configuration-reference.md | All ScalarDB config properties by backend |
| Code patterns | @skills/common/references/code-patterns/ | Complete app templates for all 6 interface combos |

## Conventions

- **Output language**: Configurable per project (`en` default, `ja` supported)
- **File naming**: kebab-case for all generated files
- **Frontmatter**: Every output file must include YAML frontmatter with `schema_version`
- **Diagrams**: All diagrams use Mermaid syntax (validated by hook)
- **Immediate output**: Each skill step writes its output file upon completion
- **ScalarDB-optional**: When ScalarDB is not used, ScalarDB-specific skills are skipped and review-data-integrity replaces review-scalardb
