# Nexus Architect

System architecture toolkit for Claude Code. Two plugins:
- **architect** — Legacy refactoring, greenfield design, database migration, consulting deliverables
- **scalardb** — ScalarDB application development toolkit

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

Architecture skills use `/architect:skill-name`. ScalarDB tools use `/scalardb:skill-name`.

| Command | Description |
|---------|-------------|
| **Orchestration** | |
| `/architect:start` | Interactively start system analysis and design |
| `/architect:pipeline` | Automated pipeline execution (supports --resume, --skip) |
| `/architect:init-output` | Initialize output directories |
| **Investigation & Analysis** | |
| `/architect:investigate` | Tech stack, structure, debt, DDD readiness survey |
| `/architect:investigate-security` | OWASP Top 10, access control assessment |
| `/architect:analyze` | Ubiquitous language, actors, domain mapping |
| `/architect:analyze-data-model` | Data model, DB design, ER diagrams |
| **Evaluation** | |
| `/architect:evaluate-mmi` | MMI 4-axis qualitative evaluation |
| `/architect:evaluate-ddd` | DDD 12-criteria 3-layer evaluation |
| `/architect:integrate-evaluations` | MMI+DDD integration, improvement plan |
| **Design** | |
| `/architect:map-domains` | Domain classification, BC mapping |
| `/architect:redesign` | Bounded context redesign |
| `/architect:design-microservices` | Target architecture |
| `/architect:select-scalardb-edition` | ScalarDB edition selection |
| `/architect:design-scalardb` | ScalarDB schema and transaction design |
| `/architect:design-scalardb-analytics` | HTAP analytics platform design |
| `/architect:design-data-layer` | Generic DB design (non-ScalarDB) |
| `/architect:design-api` | REST/GraphQL/gRPC/AsyncAPI specifications |
| **Implementation & Codegen** | |
| `/architect:design-implementation` | Implementation specifications |
| `/architect:generate-test-specs` | BDD/unit/integration test specifications |
| `/architect:generate-scalardb-code` | Spring Boot + ScalarDB code generation |
| `/architect:generate-infra-code` | K8s/Terraform/Helm code generation |
| **Infrastructure** | |
| `/architect:design-infrastructure` | K8s, IaC, multi-environment |
| `/architect:design-security` | Authentication, authorization, secrets management |
| `/architect:design-observability` | Monitoring, tracing, alerting |
| `/architect:design-disaster-recovery` | RTO/RPO, backup, DR |
| **Review (5-perspective parallel)** | |
| `/architect:review-consistency` | Structural coherence |
| `/architect:review-scalardb` | ScalarDB constraints |
| `/architect:review-data-integrity` | Data integrity (non-ScalarDB) |
| `/architect:review-operations` | Operational readiness |
| `/architect:review-risk` | Distributed system risks |
| `/architect:review-business` | Business requirements |
| `/architect:review-synthesizer` | Consolidation and quality gate |
| **Reporting** | |
| `/architect:report` | Markdown to HTML consolidated report |
| `/architect:render-mermaid` | Mermaid to PNG/SVG + syntax fix |
| `/architect:estimate-cost` | Infrastructure, license, and operational costs |
| **ScalarDB Development (`/scalardb:*`)** | |
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
| **Database Migration** | |
| `/architect:migrate-database` | Unified migration router (Oracle/MySQL/PostgreSQL) |
| `/architect:migrate-oracle` | Oracle → ScalarDB (schema, analysis, AQ, SP/trigger) |
| `/architect:migrate-mysql` | MySQL → ScalarDB (schema, analysis, SP/trigger) |
| `/architect:migrate-postgresql` | PostgreSQL → ScalarDB (schema, analysis, SP/trigger) |

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

## Output Language

Output language is configurable per project. Set during `/architect:start` initialization or via flag:

```bash
/architect:pipeline ./path/to/project --lang=ja
```

Supported: `en` (English, default), `ja` (Japanese).

## Requirements

- Claude Code CLI (latest)
- Python 3.9+
- Node.js 18+ (optional, for Mermaid rendering)

## Optional MCP Servers

- **Serena**: Advanced code analysis with AST-level understanding
- **Context7**: Latest ScalarDB documentation

## Output Structure

All outputs are written to git-ignored directories:

```
reports/          # Analysis and design documents
generated/        # Generated code per service
work/             # Pipeline state and intermediate files
```

## License

MIT
