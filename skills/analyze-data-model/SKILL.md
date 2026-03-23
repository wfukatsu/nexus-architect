---
name: analyze-data-model
description: |
  Comprehensive data layer analysis including entity/relationship analysis, DB design evaluation, and ER diagram generation.
  /architect:analyze-data-model [target_path] to invoke.
  Requires analyze-system output as a prerequisite.
model: sonnet
user_invocable: true
---

# Data Model Analysis

## Outcome

Perform a comprehensive analysis of the target system's data layer and generate the following:
1. **Data Model Analysis** — Entities, relationships, domain rules, normalization status
2. **ER Diagram (Current State)** — Current ER diagram in Mermaid erDiagram format

## Judgment Criteria

- Cross-reference entity identification with domain terms
- When normalization deviations exist, determine whether they are intentional or problematic
- Evaluate the appropriateness of index design
- Verify the completeness of data integrity constraints (FK, UNIQUE, CHECK)

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/01_analysis/ | Recommended | /architect:analyze |

## Output

| File | Content |
|------|---------|
| `reports/01_analysis/data-model-analysis.md` | Entity list, relationships, normalization assessment, index analysis |
| `reports/01_analysis/er-diagram-current.md` | Mermaid ER diagram |

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

## Completion

1. Both output files have been written
2. Report a summary of findings and any unresolved concerns

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:analyze | Upstream (input source) |
| /architect:redesign | Downstream |
| /architect:design-scalardb | Downstream |
