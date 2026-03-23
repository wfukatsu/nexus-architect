---
name: design-scalardb-analytics
description: |
  Design HTAP analytics platform using ScalarDB Analytics with Apache Spark.
  /architect:design-scalardb-analytics to invoke. Enterprise Premium only.
model: sonnet
user_invocable: true
---

# ScalarDB Analytics Design

## Desired Outcome

- HTAP (Hybrid Transactional/Analytical Processing) architecture design
- Apache Spark integration configuration
- Cross-database analytical query design across heterogeneous DBs
- Data catalog (logical-to-physical mapping)
- Timeline-consistent read configuration

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/03_design/scalardb-schema.md | Required | /architect:design-scalardb |

## Output

| File | Content |
|------|---------|
| `reports/03_design/scalardb-analytics-design.md` | Overall Analytics design |

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-scalardb | Input source |
