---
name: select-scalardb-edition
description: |
  Interactive selection of the optimal ScalarDB edition (OSS/Enterprise Standard/Premium).
  /architect:select-scalardb-edition to invoke.
model: sonnet
user_invocable: true
---

# ScalarDB Edition Selection

## Desired Outcome

Select the optimal ScalarDB edition and deployment mode based on project requirements.

## Decision Criteria

Use AskUserQuestion to confirm the following step by step:
1. Need for multi-DB distributed transactions
2. Whether an SQL interface is required
3. Whether analytical queries (HTAP) are required
4. SLA requirements (99.9% vs 99.99%)
5. Support level requirements

Edition comparison: @rules/scalardb-edition-profiles.md

## Output

| File | Content |
|------|---------|
| `reports/03_design/scalardb-edition-selection.md` | Selection result and rationale |

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-scalardb | Output destination (uses edition information as input) |
