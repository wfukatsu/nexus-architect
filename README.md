# Nexus Architect

Unified system architecture agent for Claude Code. Covers legacy system refactoring, greenfield ScalarDB design, ScalarDB application development, and consulting deliverable generation.

## Installation

### As a Claude Code Plugin (Recommended)

```bash
# Install from GitHub
claude plugin add --scope user github:wfukatsu/nexus-architect
```

After installation, all commands are available as `/architect:skill-name` in any Claude Code session.

### Manual Installation

```bash
# 1. Clone the repository
git clone https://github.com/wfukatsu/nexus-architect.git

# 2. Copy to the plugin cache
mkdir -p ~/.claude/plugins/cache/scalar-plugins/nexus-architect/0.3.0
cp -r nexus-architect/* ~/.claude/plugins/cache/scalar-plugins/nexus-architect/0.3.0/
cp -r nexus-architect/.claude-plugin ~/.claude/plugins/cache/scalar-plugins/nexus-architect/0.3.0/

# 3. Register in installed_plugins.json
# Add the following entry to ~/.claude/plugins/installed_plugins.json under "plugins":
#
#   "architect@scalar-plugins": [{
#     "scope": "user",
#     "installPath": "<HOME>/.claude/plugins/cache/scalar-plugins/nexus-architect/0.3.0",
#     "version": "0.3.0",
#     "installedAt": "<ISO8601>",
#     "lastUpdated": "<ISO8601>"
#   }]

# 4. Restart Claude Code to load the plugin
```

### Verify Installation

In a Claude Code session, type any command to confirm:

```bash
/architect:start
```

If the skill is recognized, the installation is successful.

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
/architect:scalardb-scaffold
/architect:scalardb-model
/architect:scalardb-build-app
```

## Commands

All 47 skills are invoked as `/architect:skill-name`.

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
| **ScalarDB Development** | |
| `/architect:scalardb-model` | Interactive schema design wizard |
| `/architect:scalardb-config` | Configuration file generator (6 interface combos) |
| `/architect:scalardb-scaffold` | Complete starter project generator |
| `/architect:scalardb-error-handler` | Exception handling code generator and reviewer |
| `/architect:scalardb-crud-ops` | CRUD API operation patterns guide |
| `/architect:scalardb-jdbc-ops` | JDBC/SQL operation patterns guide |
| `/architect:scalardb-local-env` | Docker Compose local environment setup |
| `/architect:scalardb-docs` | ScalarDB documentation search |
| `/architect:scalardb-build-app` | Build complete app from requirements |
| `/architect:scalardb-review-code` | Java code review (16 check categories) |
| `/architect:scalardb-migrate` | Migration advisor (Core/Cluster, CRUD/JDBC, 1PC/2PC) |

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
scalardb-model -> scalardb-config -> scalardb-scaffold -> scalardb-review-code
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
