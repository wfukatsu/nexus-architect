# Nexus Architect Skill Reference

All skills are invoked as `/architect:skill-name`.

## Orchestration

| Command | Model | Description |
|---------|-------|-------------|
| `/architect:start` | sonnet | Interactively start system analysis and design |
| `/architect:pipeline` | sonnet | Automated pipeline execution (supports --resume, --skip) |

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
| `/architect:render-mermaid` | haiku | Mermaid to PNG/SVG + syntax fix |
| `/architect:estimate-cost` | sonnet | Infrastructure, license, and operational costs |

## Utility

| Command | Model | Description |
|---------|-------|-------------|
| `/architect:init-output` | haiku | Initialize output directories |

## ScalarDB Development

| Command | Model | Description |
|---------|-------|-------------|
| `/architect:scalardb-model` | sonnet | Interactive schema design wizard (keys, indexes, data types) |
| `/architect:scalardb-config` | sonnet | Configuration file generator (6 interface combinations) |
| `/architect:scalardb-scaffold` | sonnet | Complete starter project generator |
| `/architect:scalardb-error-handler` | sonnet | Exception handling code generator and code reviewer |
| `/architect:scalardb-crud-ops` | sonnet | CRUD API operation patterns guide |
| `/architect:scalardb-jdbc-ops` | sonnet | JDBC/SQL operation patterns guide |
| `/architect:scalardb-local-env` | sonnet | Docker Compose local environment setup |
| `/architect:scalardb-docs` | sonnet | ScalarDB documentation search |
| `/architect:scalardb-build-app` | opus | Build complete application from domain requirements |
| `/architect:scalardb-review-code` | sonnet | Java code review (16 check categories) |
| `/architect:scalardb-migrate` | sonnet | Migration advisor (Core/Cluster, CRUD/JDBC, 1PC/2PC) |

See [ScalarDB Development Guide](scalardb-development.md) for detailed usage.

## Database Migration

| Command | Model | Database | Description |
|---------|-------|----------|-------------|
| `/architect:migrate-database` | sonnet | All | Unified migration router (auto-detects DB type) |
| `/architect:migrate-oracle` | sonnet | Oracle | Full pipeline: schema extraction, analysis, AQ integration, SP/trigger conversion |
| `/architect:migrate-mysql` | sonnet | MySQL | Full pipeline: schema extraction, analysis, SP/trigger conversion |
| `/architect:migrate-postgresql` | sonnet | PostgreSQL | Full pipeline: schema extraction, analysis, PL/pgSQL conversion |

See [Database Migration Guide](database-migration.md) for detailed usage.
