---
description: |
  Comprehensive investigation of the target system covering technology stack, codebase structure, technical debt, and DDD readiness.
  /architect:investigate [target_path] to invoke.
  Used as the first step in legacy system analysis.
model: sonnet
user_invocable: true
---

# System Investigation

## Desired Outcome

Gain a comprehensive understanding of the target system and generate the following four investigation reports:
1. **Technology Stack Analysis** — Languages, frameworks, libraries, external services
2. **Codebase Structure** — Directory layout, module structure, entry points
3. **Issues and Technical Debt** — Problem identification and severity classification (CRITICAL/High/Medium/Low)
4. **DDD Readiness** — Assessment of readiness for migration to domain-driven design

## Decision Criteria

- Prioritize deep-diving into areas where technical debt is most concentrated
- Especially flag coupling issues that hinder domain decomposition
- Evaluate DDD readiness based on evidence (not speculation); use the scoring formula from @rules/evaluation-frameworks.md — do not estimate the final score independently
- Record any security concerns found

## Prerequisites

| File | Required/Recommended | Description |
|------|---------------------|-------------|
| target_path (argument) | Required | Path to the codebase under investigation |

## Available Resources

- **Serena MCP** — AST analysis via `get_symbols_overview`, `find_symbol` (preferred)
- **Glob/Grep** — File pattern search, keyword search within code
- **Read** — Reading configuration files and dependency definition files
- **Task(Explore)** — Parallel investigation of large codebases

## Execution

### issues-and-debt.md — Counting Procedure

1. Write all individual issues (`SEC-xx`, `DEBT-xx`) in the body first
2. Count the written items by severity
3. Fill the summary table with those counts

**Anti-pattern**: Writing the summary table before the body. The table counts will not match the actual body items.

### ddd-readiness.md — Score Calculation Procedure

1. Score all 12 criteria individually (1–5 each)
2. After scoring, compute the total using the formula from @rules/evaluation-frameworks.md:
   ```
   DDD Score = (0.30 × Strategic_Avg + 0.45 × Tactical_Avg + 0.25 × Architecture_Avg) / 5 × 100
   ```
3. Enter the computed value as the Weighted Score table total
4. Use that value as the score in the Executive Summary

**Anti-pattern**: Writing the Executive Summary score first, then scoring individual criteria. The total will not match the table sum.

## Output

Write output files immediately upon completing each section:

| File | Content |
|------|---------|
| `reports/before/{project}/technology-stack.md` | Technology stack inventory and assessment |
| `reports/before/{project}/codebase-structure.md` | Directory and module structure |
| `reports/before/{project}/issues-and-debt.md` | Technical debt and issues list |
| `reports/before/{project}/ddd-readiness.md` | DDD readiness assessment |

All output files must include YAML frontmatter (title, schema_version: 1, phase, skill, generated_at).

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

## Completion

1. All four output files have been written
2. Verify numerical consistency:
   - `ddd-readiness.md`: Executive Summary score = sum of Weighted Score column in the table (not an independent estimate)
   - `issues-and-debt.md`: summary table severity counts = actual number of SEC-xx / DEBT-xx items in the body
3. Update investigate in pipeline-progress.json to "completed"
4. Report a summary of findings and any unresolved concerns

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:analyze | Downstream (uses these investigation results as input) |
| /architect:investigate-security | Related (detailed security investigation) |
