---
name: design-data-layer
description: |
  Generic database design for non-ScalarDB projects.
  /architect:design-data-layer to invoke. For projects not using ScalarDB.
  Do NOT use for ScalarDB projects (use /architect:design-scalardb instead).
model: opus
user_invocable: true
---

# Data Layer Design

## Desired Outcome

Generic data layer design for projects not using ScalarDB:
- Database selection and configuration (RDB/NoSQL/hybrid)
- Connection pool design
- Migration strategy
- Transaction management patterns
- ORM/data access patterns

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/03_design/target-architecture.md | Required | /architect:design-microservices |

## Output

| File | Content |
|------|---------|
| `reports/03_design/data-layer-design.md` | DB design, transaction management, migration |

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-microservices | Input source |
| /architect:review-data-integrity | Review target |
