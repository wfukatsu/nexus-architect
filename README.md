# Nexus Architect

Unified system architecture agent for Claude Code. Covers legacy system refactoring, greenfield ScalarDB design, and consulting deliverable generation.

## Quick Start

```bash
# Interactive workflow (recommended)
/architect ./path/to/target

# Automated full pipeline
/full-pipeline ./path/to/target

# Individual skills
/investigate-system ./path/to/target
/analyze-system ./path/to/target
/evaluate-mmi ./path/to/target
```

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

## Skill Categories

| Category | Count | Purpose |
|----------|-------|---------|
| orchestration | 2 | Workflow selection, pipeline execution |
| investigation | 2 | System survey, security analysis |
| analysis | 2 | Domain analysis, data model |
| evaluation | 3 | MMI scoring, DDD assessment |
| design | 7 | DDD, microservices, ScalarDB, API |
| implementation | 4 | Design, test specs, code generation |
| review | 7 | 5-perspective parallel review |
| infra | 4 | K8s, security, observability, DR |
| reporting | 3 | Reports, Mermaid, cost estimation |

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
