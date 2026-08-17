# Nexus Architect Skill Reference

Skills are invoked by plugin namespace: `/product:skill-name` (product direction),
`/architect:skill-name` (system architecture), and `/scalardb:skill-name` (ScalarDB development).
The architect skills are catalogued first, followed by ScalarDB Development, Database Migration,
and Product Direction.

For the inputs you should prepare before running each pipeline, see the
[product Input Requirements](product-input-requirements.md) and
[architect Input Requirements](architect-input-requirements.md) guides.

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
| `/architect:design-scalardb-analytics` | sonnet | Analytics Option | HTAP analytics platform design |
| `/architect:design-data-layer` | opus | Non-ScalarDB | Generic DB design |
| `/architect:design-api` | opus | - | Select REST/GraphQL/hybrid/gRPC/AsyncAPI per surface and generate shared verifiable contracts |
| `/architect:design-graphql` | opus | GraphQL/hybrid | Spring GraphQL SDL, field-coordinate resolver contracts, authorization, batching, query governance and transport design |

## Implementation

Manual extension tier — **not** run by `/architect:pipeline`. Invoke individually after the design
phases, in the listed order. Output lands under `generated/` (git-ignored, overwritten on re-run).

| Command | Model | Requires | Description |
|---------|-------|----------|-------------|
| `/architect:design-implementation` | opus | `reports/03_design/` | Implementation specifications — API layer (controller/DTO/validation/mapper, transaction boundary, authorization point) plus services, repositories, VOs |
| `/architect:generate-test-specs` | sonnet | `reports/06_implementation/` | BDD/contract/unit/integration/performance test specifications |
| `/architect:generate-scalardb-code` | opus | `reports/06_implementation/` + `scalardb-schema.md` | Spring Boot + ScalarDB code generation — owns `domain/` and `infrastructure/` |
| `/architect:generate-api-code` | opus | `api-specifications/` + `api-layer-spec.md` | API layer from the OpenAPI contract — controllers 1:1 with `operationId`, DTOs + derived Bean Validation, mappers, RFC 9457 handler, and `api-contract-map.json` |
| `/architect:generate-graphql-code` | opus | GraphQL specifications + `api-layer-spec.md` | Spring GraphQL API layer — resolver bindings, DTOs/mappers, security/context, DataLoader, errors, query limits and combined contract map |
| `/architect:generate-contract-tests` | sonnet | `api-contract-map.json` + `contract-test-specs.md` | Executable contract tests (swagger-request-validator + `@WebMvcTest` by default; Schemathesis / Pact / ArchUnit opt-in) |
| `/architect:generate-infra-code` | sonnet | `reports/08_infrastructure/` | K8s/Terraform/Helm code generation |
| `/architect:generate-docs` | sonnet | generated/implemented code | README + `docs/` for generated/implemented code (runs after codegen; Step 5b of implement-backlog) |
| `/architect:verify-implementation` | opus | generated/implemented code + design | Design ↕ code conformance on four axes (contract, transaction, security, requirement); `--gate` runs the eight-stage AI code quality gate (Step 5c of implement-backlog) |

## Backlog Delivery

Turns the reports into tracker work items and drives them to merged code. Unlike the codegen skills
above, this path writes **merge-bound code into the project's real source tree**, never `generated/`.
Requires `gh` / `glab` authenticated.

| Command | Model | Description |
|---------|-------|-------------|
| `/architect:export-backlog` | opus | Reports → Epic (What/Why) / Sub-Epic (What/Key Results) / Issue (How) on GitLab or GitHub; review-first plan + approval gate, idempotent creation |
| `/architect:deliver-backlog` | sonnet | Orchestrates implement → review → approval → merge per Issue under an Epic; resumes from `backlog-manifest.json`, stops at every human gate |
| `/architect:implement-backlog` | sonnet | Implements one item Epic-consistently on a working branch; Step 5b runs `generate-docs` so docs ship in the same PR/MR |
| `/architect:review-issue` | opus | Whole-Epic consistency review, bounded blocker auto-fix loop, opens the PR/MR and hands off for approval |
| `/architect:merge-issue` | opus | Merge preflight + explicit confirmation, merge, close the Issue, roll up to Sub-Epic/Epic |
| `/architect:capture-followup` | sonnet | Queue follow-up work discovered mid-delivery, then register it as Issues linked to the in-flight Sub-Epic/Epic (`F`-namespace manifest nodes) |
| `/architect:report-backlog-status` | haiku | Terminal dashboard for backlog delivery: Epic/Sub-Epic/Issue tree with delivery status + I/R/M stages, tracker sync, and a next-command action menu (wraps `tools/backlog-status.sh`) |

Progress is reflected on the tracker as `status::*` labels, progress comments, and ticked
checkboxes (acceptance criteria when implemented/verified; a parent's task-list box when its child
merges).

## Review

| Command | Model | ID Prefix | Description |
|---------|-------|-----------|-------------|
| `/architect:review-consistency` | sonnet | CON- | Structural coherence |
| `/architect:review-scalardb` | sonnet | SDB- | ScalarDB constraints |
| `/architect:review-data-integrity` | sonnet | DIN- | Data integrity (non-ScalarDB) |
| `/architect:review-operations` | sonnet | OPS- | Operational readiness |
| `/architect:review-risk` | opus | RSK- | Distributed system risks |
| `/architect:review-api-security` | opus | ASEC- | OWASP API Security Top 10, tenant isolation, transaction-boundary security; `--mode=code` re-runs it against the implemented source |
| `/architect:review-business` | sonnet | BIZ- | Business requirements |
| `/architect:review-synthesizer` | sonnet | SYN- | Consolidation and quality gate |

## Infrastructure

| Command | Model | Description |
|---------|-------|-------------|
| `/architect:design-infrastructure` | opus | K8s, IaC, multi-environment |
| `/architect:design-security` | sonnet | Authentication, object-level authorization, tenant isolation, secrets management, OWASP API Security Top 10 mapping |
| `/architect:design-observability` | sonnet | Monitoring, tracing, alerting |
| `/architect:design-disaster-recovery` | sonnet | RTO/RPO, backup, DR |

## Reporting

| Command | Model | Description |
|---------|-------|-------------|
| `/architect:report` | haiku | Markdown to HTML consolidated report |
| `/architect:review-report` | sonnet | Review the quality of the generated HTML report (completeness, score accuracy, Mermaid syntax) |
| `/architect:render-mermaid` | haiku | Mermaid to PNG/SVG + syntax fix |
| `/architect:estimate-cost` | sonnet | Infrastructure, license, and operational costs |
| `/architect:estimate-token-cost` | sonnet | Token usage and USD cost of running the agent (a-priori, calibrated by actuals) |
| `/architect:report-token-cost` | haiku | Terminal report of the recorded actual agent cost — interactive two-pane dashboard by default (10s poll; selection above, detail/session log below), `--once`, `--follow`, `--session=ID`, `--since`, `--breakdown=tokens\|cost` (dashboard defaults to `$`, `b` toggles), `--ascii`, `--ambiguous-width=2`, `--debug`, `--md`, `--json` |
| `/architect:report-status` | haiku | Terminal dashboard for pipeline progress: phase tree with status (`stale` once an upstream phase changed after it finished), declared-output completion, "running now" heartbeat, unmet dependencies and per-phase cost, with a next-command action menu, an ask-Claude key and `Tab` cycling its four views — Product, Architect, Code Generation, Backlog Delivery (wraps `tools/nexus-status.sh`) |

## Utility

| Command | Model | Description |
|---------|-------|-------------|
| `/architect:init-output` | haiku | Initialize output directories |
| `/architect:update-knowledge` | haiku | Fetch or update the version-pinned OKF ScalarDB/ScalarDL/ScalarDB Saga knowledge bundle (wraps `tools/update-okf-bundle.sh`; no flag = ensure present, `--latest` = pull newest, `--status` = show resolved path/commits/versions) |

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
| `/product:report-status` | haiku | R. Review & Report | Terminal dashboard for product-pipeline progress: phase tree with status (`stale` once an upstream phase changed after it finished), declared-output completion, gate verdict + open assumptions, per-phase cost, next-command action menu — the Product view of `tools/nexus-status.sh`; `generate-frontend` is tracked in its Code Generation view |
| `/product:adapt-change` | opus | 6. Adaptation | Re-propagation engine: compute affected scope from a change and re-run only impacted skills |

## Invocation signatures

The complete flag set for every command, harvested from each `SKILL.md` frontmatter (the
authoritative source) and from the tools the status/cost commands wrap. A command listed with no
flags takes none. Skills nested under a migration router (`skills/migrate-oracle/…`) are read by
path by their router and are not slash commands.

```text
# Orchestration & setup
/architect:start [target_path]
/architect:pipeline [target_path] [--skip-{phase}] [--resume-from=phase-N] [--rerun-from=phase-N] [--analyze-only] [--no-scalardb] [--lang=en|ja]
/architect:init-output [project_name] [--reset]
/product:start [target] [--auto] [--profile=mvp|core-only|ux-to-spec|full] [--frontend|--no-frontend] [--lang=ja|en]
/product:init-output [project_name] [--reset]

# Requirements, investigation, analysis, evaluation
/architect:define-requirements [target_path] [--input=<file|dir>] [--auto] [--no-scalardb]
/architect:investigate [target_path]
/architect:investigate-security [target_path]
/architect:analyze [target_path]
/architect:analyze-data-model [target_path]
/architect:evaluate-mmi [target_path]
/architect:evaluate-ddd [target_path]
/architect:integrate-evaluations

# Design
/architect:map-domains
/architect:redesign
/architect:create-domain-story [--domain=<name>] [--auto]
/architect:design-microservices
/architect:select-scalardb-edition
/architect:design-scalardb
/architect:design-scalardb-analytics
/architect:design-data-layer
/architect:design-api
/architect:design-graphql [--service=<name>] [--lang=en|ja]
/architect:design-implementation
/architect:design-infrastructure
/architect:design-security
/architect:design-observability
/architect:design-disaster-recovery

# Code generation & verification
/architect:generate-test-specs
/architect:generate-scalardb-code
/architect:generate-api-code [--service=<name>] [--out=<path>] [--confirm-versions|--no-confirm-versions] [--dry-run] [--auto] [--lang=en|ja]
/architect:generate-graphql-code [--service=<name>] [--out=<path>] [--confirm-versions|--no-confirm-versions] [--dry-run] [--auto] [--lang=en|ja]
/architect:generate-contract-tests [--service=<name>] [--out=<path>] [--stack=default|schemathesis|pact|archunit] [--confirm-versions|--no-confirm-versions] [--dry-run] [--auto] [--lang=en|ja]
/architect:generate-infra-code
/architect:generate-docs [target] [--scope=changed|service|repo] [--source-root=<path>] [--readme-only] [--issue=<id>] [--dry-run] [--auto] [--lang=en|ja]
/architect:verify-implementation [target_path] [--service=<name>] [--scope=changed|service|repo] [--source-root=<path>] [--gate] [--item=<backlog-id>] [--auto] [--lang=en|ja]

# Review
/architect:review-consistency
/architect:review-scalardb
/architect:review-data-integrity
/architect:review-operations
/architect:review-risk
/architect:review-business
/architect:review-api-security [--mode=design|code] [--source-root=<path>] [--scope=changed|service|repo]
/architect:review-synthesizer
/architect:review-report

# Backlog delivery
/architect:export-backlog [--target=gitlab|github] [--project=<path>|--repo=<owner/name>] [--group=<gitlab-group>] [--dry-run] [--update] [--lang=en|ja]
/architect:deliver-backlog [--epic=<id>] [--issue=<id>] [--from=implement|review|merge] [--auto] [--yes-merge] [--max-fix-rounds=N] [--export] [--dry-run] [--lang=en|ja]
/architect:implement-backlog [item] [--epic=<id>] [--build-context] [--review-epic[=<id>]] [--out=<path>] [--confirm-versions|--no-confirm-versions] [--refresh-versions] [--dry-run] [--auto] [--lang=en|ja]
/architect:review-issue [item] [--epic=<id>] [--max-fix-rounds=N] [--base=<branch>] [--no-fix] [--dry-run] [--auto] [--lang=en|ja]
/architect:merge-issue [item|mr|pr] [--strategy=merge|squash|rebase] [--delete-branch] [--yes-merge] [--dry-run] [--auto] [--lang=en|ja]
/architect:capture-followup [title] [--parent=<local_id|#iid>] [--from=<file|issue-ref>] [--queue-only] [--flush] [--dry-run] [--auto] [--lang=en|ja]
/architect:report-backlog-status [--once] [--no-sync] [--exec] [--epic=<id>] [--json] [--md] [--ascii] [--ambiguous-width=2] [--lang=ja|en]

# Reporting, cost & status
/architect:report
/architect:render-mermaid [target_path]
/architect:estimate-cost
/architect:estimate-token-cost [target_path]
/architect:report-token-cost [--once] [--follow] [--session=ID] [--since=7d] [--breakdown=tokens|cost] [--ascii] [--ambiguous-width=2] [--md] [--json] [--lang=ja|en]
/architect:report-status [--once] [--view=product|architect|codegen|backlog] [--group=core|extension] [--phase=<name>] [--exec] [--json] [--md] [--ascii] [--ambiguous-width=2] [--lang=ja|en]
/architect:update-knowledge [--latest] [--status]
/product:report [--auto] [--lang=ja|en]
/product:report-status [--once] [--phase=<name>] [--exec] [--json] [--md] [--ascii] [--ambiguous-width=2] [--lang=ja|en]

# Database migration
/architect:migrate-database
/architect:migrate-oracle
/architect:migrate-mysql
/architect:migrate-postgresql

# ScalarDB development
/scalardb:model
/scalardb:config
/scalardb:scaffold
/scalardb:error-handler
/scalardb:crud-ops
/scalardb:jdbc-ops
/scalardb:local-env
/scalardb:docs
/scalardb:build-app
/scalardb:review-code
/scalardb:migrate

# Product direction
/product:define-vision [target] [--input=<file|dir>] [--auto] [--lang=ja|en] [--no-research]
/product:name-product [target] [--input=<file|dir>] [--count=N] [--style=acronym|initialism|hybrid] [--seed=<letters|word>] [--auto] [--lang=ja|en]
/product:define-success-metrics [--auto] [--lang=ja|en]
/product:research-landscape [target] [--input=<file|dir>] [--auto] [--lang=ja|en] [--no-research]
/product:design-revenue [--input=<file|dir>] [--auto] [--lang=ja|en]
/product:define-scope [--constraints=<file|text>] [--input=<file|dir>] [--auto] [--lang=ja|en]
/product:validate-assumptions [--auto] [--lang=ja|en]
/product:generate-persona [--input=<file|dir>] [--auto] [--lang=ja|en]
/product:map-journey [--auto] [--lang=ja|en]
/product:design-positioning [--auto] [--lang=ja|en]
/product:create-domain-story [--persona=<PER>] [--job=<JOB>] [--domain=<CTX>] [--auto] [--lang=ja|en]
/product:design-system [--name=<id>] [--import=<path>] [--fidelity=lo|mid] [--auto] [--lang=ja|en]
/product:generate-ui-mock [--fidelity=lo|mid] [--auto] [--lang=ja|en]
/product:define-features [--auto] [--lang=ja|en]
/product:define-data-model [--auto] [--lang=ja|en]
/product:generate-frontend [--design-system=<name>] [--out=<path>] [--auto] [--lang=ja|en]
/product:map-domains [--auto] [--lang=ja|en]
/product:design-api [--auto] [--lang=ja|en]
/product:design-sla [--auto] [--lang=ja|en]
/product:define-nfr [--auto] [--lang=ja|en]
/product:design-architecture [--auto] [--lang=ja|en]
/product:review [--auto] [--lang=ja|en]
/product:adapt-change --change="<text>" [--type=constraint|market|competitor|tech|regulation] [--auto] [--lang=ja|en]
```
