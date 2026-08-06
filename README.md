# Nexus Architect

System architecture toolkit for Claude Code and Codex. Claude Code uses this repository as three plugins with 80 skills; Codex uses the same skill files through `AGENTS.md` compatibility rules.

- **product** (26 skills) — Product direction: validation-driven, dialogue-based pipeline from product vision to SLA/NFR; hands off to architect for system implementation design
- **architect** (43 skills) — Legacy refactoring, greenfield design, database migration, consulting deliverables
- **scalardb** (11 skills) — ScalarDB application development toolkit

## Installation

### As a Claude Code Plugin (Recommended)

```bash
# 1. Add the marketplace
claude plugin marketplace add wfukatsu/nexus-architect

# 2. Install the plugins
claude plugin install product@nexus-architect --scope user
claude plugin install architect@nexus-architect --scope user
claude plugin install scalardb@nexus-architect --scope user
```

After installation, commands are available as `/product:skill-name`, `/architect:skill-name`, and `/scalardb:skill-name`.

To update to the latest version:

```bash
claude plugin update product@nexus-architect
claude plugin update architect@nexus-architect
claude plugin update scalardb@nexus-architect
```

### Manual Installation

```bash
# 1. Clone the repository (with the ScalarDB/ScalarDL knowledge bundle submodule)
git clone --recurse-submodules https://github.com/wfukatsu/nexus-architect.git

# 2. Add as a local marketplace
claude plugin marketplace add ./nexus-architect

# 3. Install the plugins
claude plugin install product@nexus-architect --scope user
claude plugin install architect@nexus-architect --scope user
claude plugin install scalardb@nexus-architect --scope user
```

### Verify Installation

In a Claude Code session, type any command to confirm:

```bash
/product:start
/architect:start
/scalardb:model
```

If the skills are recognized, the installation is successful.

### Using with Codex

Codex can use the same skill files without installing Claude Code plugins.

```bash
# 1. Clone the repository (with the ScalarDB/ScalarDL knowledge bundle submodule)
git clone --recurse-submodules https://github.com/wfukatsu/nexus-architect.git
cd nexus-architect

# 2. Optional Python dependencies
pip install -r requirements.txt
```

Open Codex at the repository root. `AGENTS.md` tells Codex how to translate Claude Code conventions:

- `/product:<name>` -> `skills/product/<name>/SKILL.md` (product skills are nested under `skills/product/`)
- `/architect:<name>` -> `skills/<name>/SKILL.md`
- `/scalardb:<name>` -> `skills/<name>/SKILL.md`
- `CLAUDE_PLUGIN_ROOT` -> the repository root
- `.claude/docs/*` -> `skills/common/references/*`
- `.claude/rules/*` -> `rules/*` (product rules are nested under `rules/product/*`)
- `${CLAUDE_PLUGIN_ROOT}/subagents/*` -> `skills/common/subagents/*`

Then invoke the same command text in chat:

```bash
/product:start
/architect:start ./path/to/target
/architect:pipeline ./path/to/target
/scalardb:model
/scalardb:review-code ./path/to/app
```

When a skill asks to use Claude tools, Codex follows these mappings:

| Claude Code reference | Codex behavior |
|---|---|
| `Read`, `Glob`, `Grep`, `LS` | Use shell reads, `rg`, `rg --files`, `find`, or `ls` |
| `Write`, `Edit`, `MultiEdit` | Edit files with `apply_patch` |
| `Bash` | Run shell commands |
| `AskUserQuestion` | Present numbered choices in chat and wait for the reply |
| `Task`, `Subagent` | Run in the main Codex thread unless the user explicitly asks for sub-agents |
| `WebFetch`, `WebSearch` | Use Codex web access, Context7, or approved `curl` |

After editing generated reports or Mermaid diagrams in Codex, run the hooks manually when relevant:

```bash
hooks/validate-frontmatter.sh reports/before/example/technology-stack.md
hooks/validate-mermaid.sh reports/before/example/codebase-structure.md
```

Claude Code continues to use the plugin metadata and slash commands unchanged. See [Using Nexus Architect with Codex](docs/codex-usage.md) for the full Codex guide.

## Quick Start

```bash
# Product direction (greenfield: start here, then hand off to /architect:define-requirements)
/product:start

# Interactive workflow (recommended)
/architect:start ./path/to/target

# Automated full pipeline
/architect:pipeline ./path/to/target

# Individual skills
/architect:investigate ./path/to/target
/architect:analyze ./path/to/target
/architect:evaluate-mmi ./path/to/target

# Code generation (after the design pipeline — see Code Generation & Delivery below)
/architect:design-implementation
/architect:generate-scalardb-code
/architect:generate-docs

# Backlog delivery (merge-bound code: implement -> review -> merge, per Issue)
/architect:export-backlog --target=github --repo=<owner>/<name>
/architect:deliver-backlog --epic=E1

# ScalarDB development
/scalardb:scaffold
/scalardb:model
/scalardb:build-app
```

## Commands

### Product Direction (`/product:*`)

Validation-driven pipeline from product vision to SLA/NFR. Hands off to `/architect:define-requirements` for system implementation design.

| Command | Description |
|---------|-------------|
| `/product:start` | Interactively start product-direction design (`--profile=mvp\|core-only\|ux-to-spec\|full`; selectable frontend codegen via `--frontend`/`--no-frontend`) |
| `/product:init-output` | Initialize the product output tree, progress file, and traceability graph |
| `/product:define-vision` | Define product core (Vision/Mission/Values) via dialogue |
| `/product:name-product` | Name the product as an acronym — a pronounceable Latin-letter name whose every letter is the initial of an English word, expanding into a value phrase (optional; in `full`) |
| `/product:define-success-metrics` | One North Star Metric plus 3–5 input metrics |
| `/product:research-landscape` | Market/competitor research: sizing (TAM/SAM/SOM), trends |
| `/product:design-revenue` | Revenue/business model and a recomputable benefit-evaluation template |
| `/product:define-scope` | Normalize constraints and decide product scope (in/out) |
| `/product:validate-assumptions` | Extract riskiest assumptions, cheapest test, Go/No-Go gate (re-runnable) |
| `/product:generate-persona` | Jobs-to-be-Done–anchored personas (job stories + persona cards) |
| `/product:map-journey` | Customer journey as a stages × layers grid |
| `/product:design-positioning` | Positioning (Dunford canvas), touchpoint × device × timing matrix |
| `/product:create-domain-story` | Persona-anchored domain stories; the axis UI mocks render along |
| `/product:design-system` | Build or `--import` a separately-managed design system (DTCG tokens + components + guidelines) |
| `/product:generate-ui-mock` | Navigable UI mocks for key screens (domain-story-driven, design-system-styled) |
| `/product:define-features` | Extract features from UI mocks (each screen action → Command/feature) |
| `/product:define-data-model` | Derive data model from UI mocks and features (explicit → implicit, 2 passes) |
| `/product:generate-frontend` | Turn UI mocks + design system into a runnable React + Storybook frontend (Atomic Design, token-styled, react-router) |
| `/product:map-domains` | Abstract features/entities into bounded contexts (DDD strategic) |
| `/product:design-api` | Logical API surface in three API-Led layers (System/Process/Experience) |
| `/product:design-architecture` | Architecture & technology-fitness synthesis (capstone of domain/API/data + NFR) |
| `/product:design-sla` | Per-service SLI/SLO/SLA with error budgets |
| `/product:define-nfr` | Turn SLOs into measurable NFRs (availability, latency p95/p99, ...) |
| `/product:review` | Review product artifacts (consistency, traceability, extensibility, strategy) |
| `/product:report` | Consolidate artifacts into one self-contained HTML report (validation status first) |
| `/product:adapt-change` | Re-propagation engine: compute affected scope and re-run only impacted skills |

### Orchestration

| Command | Description |
|---------|-------------|
| `/architect:start` | Interactively start system analysis and design |
| `/architect:pipeline` | Automated pipeline execution (`--resume-from`, `--rerun-from`, `--skip-{phase}`, `--no-scalardb`, `--lang`) |
| `/architect:init-output` | Initialize output directories |

### Requirements

| Command | Description |
|---------|-------------|
| `/architect:define-requirements` | Requirements definition: FR/NFR classification, data/transaction requirements, Scalar product applicability — ScalarDB / ScalarDB Saga (greenfield entry point) |

### Investigation & Analysis

| Command | Description |
|---------|-------------|
| `/architect:investigate` | Tech stack, structure, debt, DDD readiness survey |
| `/architect:investigate-security` | OWASP Top 10, access control assessment |
| `/architect:analyze` | Ubiquitous language, actors, domain mapping |
| `/architect:analyze-data-model` | Data model, DB design, ER diagrams |

### Evaluation

| Command | Description |
|---------|-------------|
| `/architect:evaluate-mmi` | MMI 4-axis qualitative evaluation |
| `/architect:evaluate-ddd` | DDD 12-criteria 3-layer evaluation |
| `/architect:integrate-evaluations` | MMI+DDD integration, improvement plan |

### Design

| Command | Description |
|---------|-------------|
| `/architect:map-domains` | Domain classification, BC mapping |
| `/architect:redesign` | Bounded context redesign |
| `/architect:create-domain-story` | Domain Storytelling: visualize business processes per domain (optional) |
| `/architect:design-microservices` | Target architecture |
| `/architect:select-scalardb-edition` | ScalarDB edition selection |
| `/architect:design-scalardb` | ScalarDB schema and transaction design |
| `/architect:design-scalardb-analytics` | HTAP analytics platform design |
| `/architect:design-data-layer` | Generic DB design (non-ScalarDB) |
| `/architect:design-api` | REST/GraphQL/gRPC/AsyncAPI specifications |

### Implementation & Codegen

These are **not** part of `/architect:pipeline`. Run them individually after the design phases, in
the order below (see [Code Generation & Delivery](#code-generation--delivery)).

| Command | Description | Requires |
|---------|-------------|----------|
| `/architect:design-implementation` | Implementation specifications | `reports/03_design/` |
| `/architect:generate-test-specs` | BDD/unit/integration test specifications | `reports/06_implementation/` |
| `/architect:generate-scalardb-code` | Spring Boot + ScalarDB code generation | `reports/06_implementation/` + `scalardb-schema.md` |
| `/architect:generate-infra-code` | K8s/Terraform/Helm code generation | `reports/08_infrastructure/` (from `design-infrastructure`) |
| `/architect:generate-docs` | README + `docs/` for the generated/implemented code — runs after codegen, and as Step 5b of `implement-backlog` | generated or implemented code |

### Backlog Delivery

Turn the reports into tracker work items and drive them to merged code. Unlike the codegen skills
above, this path writes **merge-bound code into the project's real source tree**, not `generated/`.

| Command | Description |
|---------|-------------|
| `/architect:export-backlog` | Reports → Epic / Sub-Epic / Issue hierarchy on GitLab or GitHub (review-first, idempotent) |
| `/architect:deliver-backlog` | Orchestrates implement → review → approval → merge for each Issue under an Epic |
| `/architect:implement-backlog` | Implements one item, Epic-consistently; Step 5b runs `generate-docs` onto the same branch |
| `/architect:review-issue` | Whole-Epic consistency review, bounded blocker auto-fix, opens the PR/MR |
| `/architect:merge-issue` | Merge preflight + confirmation, merge, close the Issue, roll up to Sub-Epic/Epic |
| `/architect:capture-followup` | Queues follow-up work discovered mid-delivery, then registers it as Issues linked to the in-flight Sub-Epic/Epic |
| `/architect:report-backlog-status` | Live terminal dashboard: Epic/Sub-Epic/Issue tree with delivery status + Implemented/Reviewed/Merged stages, and an action menu that generates the next command |

Progress is visible on the tracker: `status::*` labels, progress comments, and the items' markdown
checkboxes — acceptance criteria are ticked as they are implemented and verified, and a parent's
task-list box is ticked as soon as its child's implementation and tests are complete, so the
Epic/Sub-Epic progress counters render implementation state. Delivery state is rendered too: every
item body carries a `## Delivery Status` section (a `Status:` line mirroring the label, plus
`Implemented`/`Reviewed`/`Merged` stage boxes ticked by the skill that establishes each stage), so
"did it merge?" is answerable from the body; the `status::*` labels remain the machine-readable
source of truth.

### Infrastructure

| Command | Description |
|---------|-------------|
| `/architect:design-infrastructure` | K8s, IaC, multi-environment |
| `/architect:design-security` | Authentication, authorization, secrets management |
| `/architect:design-observability` | Monitoring, tracing, alerting |
| `/architect:design-disaster-recovery` | RTO/RPO, backup, DR |

### Review (5-perspective parallel)

| Command | Description |
|---------|-------------|
| `/architect:review-consistency` | Structural coherence |
| `/architect:review-scalardb` | ScalarDB constraints |
| `/architect:review-data-integrity` | Data integrity (non-ScalarDB) |
| `/architect:review-operations` | Operational readiness |
| `/architect:review-risk` | Distributed system risks |
| `/architect:review-business` | Business requirements |
| `/architect:review-synthesizer` | Consolidation and quality gate |

### Reporting

| Command | Description |
|---------|-------------|
| `/architect:report` | Markdown to HTML consolidated report |
| `/architect:review-report` | Review the quality of the generated HTML report |
| `/architect:render-mermaid` | Mermaid to PNG/SVG + syntax fix |
| `/architect:estimate-cost` | Infrastructure, license, and operational costs |
| `/architect:estimate-token-cost` | Token usage and USD cost of *running the agent* (a-priori from LOC, calibrated by recorded actuals) |
| `/architect:report-token-cost` | Report the recorded actual agent cost from `work/token-usage.json`/`.jsonl` on the terminal — interactive two-pane dashboard by default (10s poll; pick a phase/model/session/day/event above, read its detail — a session shows its transcript log — below), `--once` single render, `--follow` event stream, `--session=ID` one session + its log, plus `--since`, `--breakdown=cost`, `--ascii` (ASCII bars for terminals that garble the Unicode ones), `--ambiguous-width=2` (terminals that render East Asian ambiguous characters double-width), `--debug`, `--md`, `--json` |
| `/architect:update-knowledge` | Fetch/update the OKF ScalarDB/ScalarDL knowledge bundle from remote (`--latest`, `--status`) |

### Database Migration

| Command | Description |
|---------|-------------|
| `/architect:migrate-database` | Unified migration router (Oracle/MySQL/PostgreSQL) |
| `/architect:migrate-oracle` | Oracle to ScalarDB (schema, analysis, AQ, SP/trigger) |
| `/architect:migrate-mysql` | MySQL to ScalarDB (schema, analysis, SP/trigger) |
| `/architect:migrate-postgresql` | PostgreSQL to ScalarDB (schema, analysis, SP/trigger) |

### ScalarDB Development (`/scalardb:*`)

| Command | Description |
|---------|-------------|
| `/scalardb:model` | Interactive schema design wizard |
| `/scalardb:config` | Configuration file generator (6 interface combos) |
| `/scalardb:scaffold` | Complete starter project generator |
| `/scalardb:error-handler` | Exception handling code generator and reviewer |
| `/scalardb:crud-ops` | CRUD API operation patterns guide |
| `/scalardb:jdbc-ops` | JDBC/SQL operation patterns guide |
| `/scalardb:local-env` | Docker Compose local environment setup |
| `/scalardb:docs` | ScalarDB documentation search |
| `/scalardb:build-app` | Build complete app from requirements |
| `/scalardb:review-code` | Java code review (16 check categories) |
| `/scalardb:migrate` | Migration advisor (Core/Cluster, CRUD/JDBC, 1PC/2PC) |

## Workflows

### Product Direction

Decide product direction before system design: validate the riskiest assumptions early, then derive UX, spec, domains, API, and SLA/NFR. Hands off to the greenfield path via `/architect:define-requirements`.

```
vision -> success-metrics / revenue -> scope -> validate-assumptions [gate]
  -> personas/journey/positioning -> ui-mock/features/data-model
  -> domains/API -> SLA/NFR -> review -> report -> /architect:define-requirements
```

### Legacy Refactoring

Analyze existing systems, evaluate architecture maturity, and design microservices transformation.

```
investigate -> analyze -> evaluate -> redesign -> implement -> review -> report
```

### Greenfield Design

Design new systems from requirements through ScalarDB architecture to deployment.

```
requirements -> domain modeling -> ScalarDB design -> infra -> deploy
```

### Code Generation & Delivery

Code generation is a **manual extension tier**: `/architect:pipeline` and `/architect:start` stop at
the review/report phase, and the codegen skills are invoked individually afterwards. There are two
paths, and they differ in what the output *is*.

**A. Scaffold — regenerable output under `generated/` (git-ignored).**

```
/architect:pipeline ./path/to/project      # design phases, through review + report
  -> /architect:design-implementation      # requires reports/03_design/
  -> /architect:generate-test-specs        # requires reports/06_implementation/
  -> /architect:design-infrastructure      # requires target-architecture.md   (infra path only)
  -> /architect:generate-scalardb-code     # -> generated/{service}/
  -> /architect:generate-infra-code        # -> generated/infrastructure/
  -> /architect:generate-docs              # READMEs + docs/ for what was emitted
```

Each step only needs the reports of the step before it, so you can enter the chain partway. A re-run
overwrites what it owns — treat this tree as disposable.

**B. Delivery — merge-bound code in the project's real source tree.**

```
/architect:export-backlog --target=github --repo=<owner>/<name>   # Epic / Sub-Epic / Issue
  -> /architect:deliver-backlog --epic=E1                          # per Issue, in order:
       implement  -> review (auto-fix blockers, open PR/MR)
                  -> [human approval]  -> merge -> roll up
```

`implement-backlog` resolves the source root (never `generated/`, verified not git-ignored), commits
to a working branch, and runs `generate-docs` as Step 5b so code and docs land in the same PR/MR.
`deliver-backlog` stops at the human gates; it never merges without approval (or `--yes-merge`).

Single steps are available too: `/architect:implement-backlog <issue>`, `/architect:review-issue
<issue>`, `/architect:merge-issue <issue>`. Work discovered mid-delivery but deferred is captured
with `/architect:capture-followup` — queued locally, then (after an approval gate) registered as
new Issues linked to the in-flight Sub-Epic/Epic, re-entering the loop as `status::todo`. Watch it
all live with `tools/backlog-status.sh` (`/architect:report-backlog-status`): the tree, per-item
delivery stages, and an action menu that hands you the next command.

**C. Frontend** — `/product:generate-frontend` (offered by `/product:start` after the UI mocks) emits
a runnable React + Storybook scaffold under `generated/frontend/`.

**D. ScalarDB only** — `/scalardb:build-app` or `/scalardb:scaffold` generate a working application
without needing the report tree.

### ScalarDB Application Development

Build ScalarDB applications with guided schema design, code generation, and code review.

```
/scalardb:model -> /scalardb:config -> /scalardb:scaffold -> /scalardb:review-code
```

### Database Migration to ScalarDB

Migrate existing Oracle, MySQL, or PostgreSQL databases to ScalarDB with automated schema analysis, migration planning, and Java code generation.

```
migrate-database -> schema extraction -> migration analysis -> SP/trigger conversion -> (AQ integration)
```

## Pipeline Dependency Graph

```
investigate -> analyze -> [evaluate-mmi, evaluate-ddd] -> integrate-evaluations
  -> redesign -> [create-domain-story (optional, per domain)]
  -> design-microservices -> [design-scalardb | design-data-layer, design-api]
  -> [review-consistency, review-scalardb | review-data-integrity,
     review-operations, review-risk, review-business]
  -> review-synthesizer -> report -> review-report
```

Everything after `review-report` — the codegen, infrastructure-design, security/observability/DR,
cost and documentation skills — is the **manual extension tier**: not executed by
`/architect:pipeline`, invoked individually. Within it the codegen order is fixed: generate code,
then `generate-docs`.

## Dependency Versions

Any generated file that pins a version (`build.gradle`/`pom.xml`, `package.json`, image tags,
Helm/Terraform/Kubernetes) uses a version that was **looked up from its registry at generation
time** — never recalled from memory — and that is a stable, non-EOL, mutually compatible release.
The decision table is recorded in the artifact and in `work/version-decisions.json`.

Whether the resolved set is confirmed with you is your choice:

```bash
/architect:implement-backlog I1.2.3 --confirm-versions      # always show the table and ask
/product:generate-frontend --no-confirm-versions            # adopt the resolved stable set silently
/architect:generate-scalardb-code --refresh-versions        # ignore the cache, re-resolve
```

```json
// work/pipeline-progress.json — project-level default (asked at /architect:start)
{ "options": { "confirm_versions": true } }
```

Unset means interactive runs ask and `--auto` runs adopt. Some cases always ask: a failed lookup, a
brand-new major as the only option, an EOL current pin, no compatible set, or a licensed/private
registry. See [`rules/dependency-versions.md`](rules/dependency-versions.md).

## ScalarDB / ScalarDL / ScalarDB Saga Knowledge Bundle

Every ScalarDB / ScalarDL / ScalarDB Saga implementation decision (API usage, config keys,
transaction patterns, exception retryability, edition-gated features) is grounded in the
[OKF-ScalarDB-ScalarDL](https://github.com/wfukatsu/OKF-ScalarDB-ScalarDL) knowledge bundle — the
complete official documentation from developers.scalar-labs.com plus the documentation ScalarDB Saga
keeps in its source repository, split **per product and per version** (ScalarDB 3.14–3.19,
ScalarDB Saga 3.19, ScalarDL 3.10–3.13, ScalarDB Community 3.4–3.13; 2,015 concepts).

It is vendored as a git submodule at `knowledge/okf-scalardb-scalardl/`. One command fetches or
updates it from remote (also available as `/architect:update-knowledge`):

```bash
tools/update-okf-bundle.sh           # ensure the bundle is available (fetches only if absent)
tools/update-okf-bundle.sh update    # pull the newest bundle from remote
tools/update-okf-bundle.sh status    # resolved path, local/remote commits, bundled versions
```

Skills follow the protocol in [`rules/okf-knowledge-bundle.md`](rules/okf-knowledge-bundle.md):
pin the project's product, version, and edition first; answer only from that release's docs; cite
the canonical `resource` URL; never mix versions. When the submodule is absent, the script falls
back to a shallow clone under `~/.cache/nexus-architect/`, then skills fall back to the online
docs (explicitly labeled as not version-pinned).

## Output Language

Output language is configurable per project. Set during `/architect:start` initialization or via flag:

```bash
/architect:pipeline ./path/to/project --lang=ja
```

Supported: `en` (English, default), `ja` (Japanese).

### Documentation language policy

All skill instructions (`SKILL.md`), rule files, and embedded prompts are written in **English**; `output_language` applies only to generated report artifacts. User guides under `docs/` are maintained as EN/JA pairs (`getting-started`, `product-input-requirements`, `architect-input-requirements`, `skill-reference`, `scalardb-development`, `database-migration`, `codex-usage`). Exceptions by design: `docs/design.md` (internal design spec, EN only) and the `docs/codex-*` audit records (point-in-time internal audits, JA only).

## Output Structure

All outputs are written to git-ignored directories:

```
reports/          # Analysis and design documents
generated/        # Generated code per service
work/             # Pipeline state and intermediate files
```

## Requirements

- Claude Code CLI (latest), for Claude Code plugin usage
- Codex, for Codex usage
- Python 3.9+
- Node.js 18+ (optional, for Mermaid rendering)

## Optional MCP Servers

- **Serena**: Advanced code analysis with AST-level understanding
- **Context7**: Latest ScalarDB documentation

## Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/getting-started.md) | Installation and first steps |
| [product Input Requirements](docs/product-input-requirements.md) | Inputs you supply to run the product pipeline |
| [architect Input Requirements](docs/architect-input-requirements.md) | Inputs you supply to run the architect pipeline |
| [Skill Reference](docs/skill-reference.md) | Complete skill catalog |
| [ScalarDB Development](docs/scalardb-development.md) | ScalarDB development guide |
| [Database Migration](docs/database-migration.md) | Migration guide (Oracle/MySQL/PostgreSQL) |
| [Codex Usage](docs/codex-usage.md) | Using the same skills from Codex |
| [Changelog](CHANGELOG.md) | Release notes and version history |

Japanese translations:
[Getting Started (日本語)](docs/getting-started_ja.md) |
[product Input Requirements (日本語)](docs/product-input-requirements_ja.md) |
[architect Input Requirements (日本語)](docs/architect-input-requirements_ja.md) |
[Skill Reference (日本語)](docs/skill-reference_ja.md) |
[ScalarDB Development (日本語)](docs/scalardb-development_ja.md) |
[Database Migration (日本語)](docs/database-migration_ja.md) |
[Codex Usage (日本語)](docs/codex-usage_ja.md) |
[Changelog (日本語)](CHANGELOG_ja.md)

## License

MIT
