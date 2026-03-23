---
name: design-scalardb
description: |
  Design ScalarDB schema, transaction boundaries, and storage backend.
  /architect:design-scalardb to invoke. For ScalarDB projects only.
  Do NOT use for projects not using ScalarDB (use /architect:design-data-layer instead).
model: opus
user_invocable: true
---

# ScalarDB Design

## Desired Outcome

Design a data architecture leveraging ScalarDB:
1. **Schema Design** -- Partition keys, clustering keys, secondary indexes
2. **Transaction Boundaries** -- Selection and boundary definition for Consensus Commit/2PC/Saga
3. **Migration Plan** -- Migration strategy from existing databases to ScalarDB

## Decision Criteria

- Consult the latest ScalarDB specifications via Context7 MCP before starting the design
- Limit 2PC to a maximum of 2-3 services
- Design keys targeting an OCC conflict rate below 5%
- Select storage backend based on requirements (JDBC/Cassandra/DynamoDB, etc.)
- Do not use DB-specific features on ScalarDB-managed tables

Detailed patterns: @rules/scalardb-coding-patterns.md
Edition comparison: @rules/scalardb-edition-profiles.md

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/03_design/target-architecture.md | Required | /architect:design-microservices |
| reports/01_analysis/data-model-analysis.md | Recommended | /architect:analyze-data-model |

## Available Resources

- **Context7 MCP** -- Fetch latest ScalarDB documentation (libraryId: /llmstxt/scalardb_scalar-labs_llms-full_txt)
- **research/** -- Pre-research materials (16 documents)

## Output

| File | Content |
|------|---------|
| `reports/03_design/scalardb-schema.md` | Table design, key strategy |
| `reports/03_design/scalardb-transaction.md` | Transaction boundaries, pattern selection |
| `reports/03_design/scalardb-migration.md` | Data migration plan |

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-microservices | Input source |
| /architect:review-scalardb | Review target |
| /architect:design-api | Related |
