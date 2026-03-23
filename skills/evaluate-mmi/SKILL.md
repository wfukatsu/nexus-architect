---
name: evaluate-mmi
description: |
  Qualitative evaluation of Modularity Maturity Index across 4 axes: cohesion, coupling, independence, reusability.
  /architect:evaluate-mmi [target_path] to invoke.
  Requires analyze-system output as a prerequisite. Can run in parallel with evaluate-ddd.
model: sonnet
user_invocable: true
---

# MMI Evaluation

## Desired Outcome

Evaluate each module of the target system across the 4 MMI axes and determine microservice readiness.

## Decision Criteria

For detailed scoring criteria and algorithms, refer to:
@rules/evaluation-frameworks.md

- 4 axes: Cohesion (30%), Coupling (30%), Independence (20%), Reusability (20%)
- Each axis scored 1-5
- MMI = (0.3 x C + 0.3 x K + 0.2 x I + 0.2 x R) / 5 x 100
- Maturity: 80-100 (Ready), 60-80 (Moderate), 40-60 (Needs Improvement), 0-40 (Immature)

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/01_analysis/ | Required | /architect:analyze |

## Output

| File | Content |
|------|---------|
| `reports/02_evaluation/mmi-overview.md` | Overall MMI score, maturity assessment, improvement priorities |
| `reports/02_evaluation/mmi-by-module.md` | Per-module 4-axis score details |

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:analyze | Input source |
| /architect:evaluate-ddd | Parallel execution |
| /architect:integrate-evaluations | Output destination |
