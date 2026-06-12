# Nexus Architect

System architecture toolkit for Claude Code and Codex. Claude Code uses this repository as two plugins with 52 skills; Codex uses the same skill files through `AGENTS.md` compatibility rules.

- **architect** (41 skills) — Legacy refactoring, greenfield design, database migration, consulting deliverables
- **scalardb** (11 skills) — ScalarDB application development toolkit

## Installation

### As a Claude Code Plugin (Recommended)

```bash
# 1. Add the marketplace
claude plugin marketplace add wfukatsu/nexus-architect

# 2. Install both plugins
claude plugin install architect@nexus-architect --scope user
claude plugin install scalardb@nexus-architect --scope user
```

After installation, commands are available as `/architect:skill-name` and `/scalardb:skill-name`.

To update to the latest version:

```bash
claude plugin update architect@nexus-architect
claude plugin update scalardb@nexus-architect
```

### Manual Installation

```bash
# 1. Clone the repository
git clone https://github.com/wfukatsu/nexus-architect.git

# 2. Add as a local marketplace
claude plugin marketplace add ./nexus-architect

# 3. Install both plugins
claude plugin install architect@nexus-architect --scope user
claude plugin install scalardb@nexus-architect --scope user
```

### Verify Installation

In a Claude Code session, type any command to confirm:

```bash
/architect:start
/scalardb:model
```

If the skills are recognized, the installation is successful.

### Using with Codex

Codex can use the same skill files without installing Claude Code plugins.

```bash
# 1. Clone the repository
git clone https://github.com/wfukatsu/nexus-architect.git
cd nexus-architect

# 2. Optional Python dependencies
pip install -r requirements.txt
```

Open Codex at the repository root. `AGENTS.md` tells Codex how to translate Claude Code conventions:

- `/architect:<name>` -> `skills/<name>/SKILL.md`
- `/scalardb:<name>` -> `skills/<name>/SKILL.md`
- `CLAUDE_PLUGIN_ROOT` -> the repository root
- `.claude/docs/*` -> `skills/common/references/*`
- `.claude/rules/*` -> `rules/*`
- `${CLAUDE_PLUGIN_ROOT}/subagents/*` -> `skills/common/subagents/*`

Then invoke the same command text in chat:

```bash
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
# Interactive workflow (recommended)
/architect:start ./path/to/target

# Automated full pipeline
/architect:pipeline ./path/to/target

# Individual skills
/architect:investigate ./path/to/target
/architect:analyze ./path/to/target
/architect:evaluate-mmi ./path/to/target

# ScalarDB development
/scalardb:scaffold
/scalardb:model
/scalardb:build-app
```

## Commands

### Orchestration

| Command | Description |
|---------|-------------|
| `/architect:start` | Interactively start system analysis and design |
| `/architect:pipeline` | Automated pipeline execution (supports `--resume`, `--skip`) |
| `/architect:init-output` | Initialize output directories |

### Requirements

| Command | Description |
|---------|-------------|
| `/architect:define-requirements` | Requirements definition: FR/NFR classification, data/transaction requirements, ScalarDB applicability (greenfield entry point) |

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
| `/architect:design-microservices` | Target architecture |
| `/architect:select-scalardb-edition` | ScalarDB edition selection |
| `/architect:design-scalardb` | ScalarDB schema and transaction design |
| `/architect:design-scalardb-analytics` | HTAP analytics platform design |
| `/architect:design-data-layer` | Generic DB design (non-ScalarDB) |
| `/architect:design-api` | REST/GraphQL/gRPC/AsyncAPI specifications |

### Implementation & Codegen

| Command | Description |
|---------|-------------|
| `/architect:design-implementation` | Implementation specifications |
| `/architect:generate-test-specs` | BDD/unit/integration test specifications |
| `/architect:generate-scalardb-code` | Spring Boot + ScalarDB code generation |
| `/architect:generate-infra-code` | K8s/Terraform/Helm code generation |

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
| `/architect:render-mermaid` | Mermaid to PNG/SVG + syntax fix |
| `/architect:estimate-cost` | Infrastructure, license, and operational costs |

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
  -> redesign -> design-microservices -> [design-scalardb | design-data-layer, design-api]
  -> [review-consistency, review-scalardb | review-data-integrity,
     review-operations, review-risk, review-business]
  -> review-synthesizer -> report
```

## Output Language

Output language is configurable per project. Set during `/architect:start` initialization or via flag:

```bash
/architect:pipeline ./path/to/project --lang=ja
```

Supported: `en` (English, default), `ja` (Japanese).

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
| [Codex Usage](docs/codex-usage.md) | Using the same skills from Codex |
| [Skill Reference](docs/skill-reference.md) | Complete skill catalog |
| [ScalarDB Development](docs/scalardb-development.md) | ScalarDB development guide |
| [Database Migration](docs/database-migration.md) | Migration guide (Oracle/MySQL/PostgreSQL) |

Japanese translations:
[Getting Started (日本語)](docs/getting-started_ja.md) |
[Codex Usage (日本語)](docs/codex-usage_ja.md) |
[Skill Reference (日本語)](docs/skill-reference_ja.md) |
[ScalarDB Development (日本語)](docs/scalardb-development_ja.md) |
[Database Migration (日本語)](docs/database-migration_ja.md)

## License

MIT
