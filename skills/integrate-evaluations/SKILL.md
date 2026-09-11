---
description: |
  Merge MMI and DDD evaluation results — and the UX evaluation when it exists — into a unified improvement plan.
  /architect:integrate-evaluations to invoke.
model: sonnet
user_invocable: true
---

# Evaluation Integration

## Desired Outcome

Integrate the MMI and DDD evaluation results and formulate a unified improvement plan for microservice transformation.

## Decision Criteria

- Prioritize areas that scored low in both evaluations as top improvement targets
- Rank improvement items by both business impact and technical feasibility
- Classify into short-term (quick wins) and medium-to-long-term (structural improvements)
- When a UX evaluation exists, add a **UX track**: its `critical` and `major` findings become
  improvement items with their screens, and its band decides per affected flow whether the UI is
  carried over or redesigned (@rules/ux-evaluation.md §3, §7). A module that scores low on MMI and
  whose screens carry `critical` UX findings is a stronger redesign candidate than either alone

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/02_evaluation/mmi-overview.md | Required | /architect:evaluate-mmi |
| reports/02_evaluation/ddd-strategic-evaluation.md | Required | /architect:evaluate-ddd |
| reports/02_evaluation/ux-evaluation.md, ux-evaluation.json | Optional | /architect:evaluate-ux (when the system has a UI) |

## Output

| File | Content |
|------|---------|
| `reports/02_evaluation/integrated-evaluation.md` | Integrated evaluation results |
| `reports/02_evaluation/unified-improvement-plan.md` | Prioritized improvement plan |

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:evaluate-mmi | Input source |
| /architect:evaluate-ddd | Input source |
| /architect:evaluate-ux | Input source (optional) |
| /architect:redesign | Output destination |
