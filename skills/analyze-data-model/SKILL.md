---
description: |
  Analyze an existing data layer: entities and relationships, database design quality and the
  current ER diagram. Runs after analyze.
argument-hint: '[target_path]'
model: sonnet
---

# Data Model Analysis

**Usage:** `/architect:analyze-data-model [target_path]`

Shared files: a path written `@rules/…`, `@skills/…`, `@templates/…` or `@docs/…` is relative to the
plugin root, `${CLAUDE_PLUGIN_ROOT}` — not to the project being worked on. Read it from there.

## Desired Outcome

Perform a comprehensive analysis of the target system's data layer and generate the following:
1. **Data Model Analysis** — Entities, relationships, domain rules, normalization status
2. **ER Diagram (Current State)** — Current ER diagram in Mermaid erDiagram format

## Decision Criteria

- Cross-reference entity identification with domain terms
- When normalization deviations exist, determine whether they are intentional or problematic
- Evaluate the appropriateness of index design
- Verify the completeness of data integrity constraints (FK, UNIQUE, CHECK)

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/01_analysis/ | Recommended | /architect:analyze |
| Explicitly selected `reports/01_analysis/database-investigation/<target-id>/<mode>/<run-id>/` | Optional | /architect:investigate-db-design or /architect:investigate-db-live |

When a database investigation run is supplied, read its `inventory.json`,
`collection-summary.json` and review report. Preserve file/query evidence, native identifiers,
partial coverage and the difference between design declarations and live observations. Do not
silently select the latest run, combine baselines, infer missing statistics or replace unavailable
data with zero. Database-only analysis may use this input without the broader codebase analysis;
the existing pipeline prerequisites are unchanged.

## Output

| File | Content |
|------|---------|
| `reports/01_analysis/data-model-analysis.md` | Entity list, relationships, normalization assessment, index analysis |
| `reports/01_analysis/er-diagram-current.md` | Mermaid ER diagram |

Output language and frontmatter: @rules/output-conventions.md.

## Completion

1. Both output files have been written
2. Report a summary of findings and any unresolved concerns

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:analyze | Upstream (input source) |
| /architect:redesign | Downstream |
| /architect:design-scalardb | Downstream |
