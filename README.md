# Nexus Architect

Unified system architecture agent for Claude Code. Covers legacy system refactoring, greenfield ScalarDB design, and consulting deliverable generation.

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
```

## Commands

All 36 skills are invoked as `/architect:skill-name`.

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
| **Implementation** | |
| `/architect:design-implementation` | Implementation specifications |
| `/architect:generate-test-specs` | BDD/unit/integration test specifications |
| `/architect:generate-scalardb-code` | Spring Boot + ScalarDB code generation |
| `/architect:generate-infra-code` | K8s/Terraform/Helm code generation |
| **Infrastructure** | |
| `/architect:design-infrastructure` | K8s, IaC, multi-environment |
| `/architect:design-security` | Authentication, authorization, secrets management |
| `/architect:design-observability` | Monitoring, tracing, alerting |
| `/architect:design-disaster-recovery` | RTO/RPO, backup, DR |
| **Review** | |
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

## Workflows

### Legacy Refactoring

```
investigate -> analyze -> evaluate -> redesign -> implement -> review -> report
```

### Greenfield Design

```
requirements -> domain modeling -> ScalarDB design -> infra -> deploy
```

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
