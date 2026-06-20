---
description: |
  Review the accumulated product artifacts through four lenses — consistency, traceability,
  extensibility, and strategy — and return an actionable findings list (severity + location + fix).
  Rerunnable, can run mid-pipeline. /product:review [--auto] [--lang=ja|en].
model: opus
user_invocable: true
---

# Multi-Lens Review

## Desired Outcome

Produce one deliverable:

1. **Review** — `reports/report/review.md`: findings from four lenses, each with **lens, severity
   (blocker / major / minor), location (file + ID), and a concrete fix**:
   - **Consistency** — broken ID refs, contradictions, terminology drift
   - **Traceability** — `work/traceability.json` vs. documents; orphans & dangling refs
   - **Extensibility** — domain boundaries & API reuse vs. future features
   - **Strategy** — Vision↔scope alignment, unit-economics health, durable differentiation

## Invocation

```
/product:review [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--auto` | Optional | Run without elicitation; report on whatever artifacts exist |
| `--lang` | Optional | Override output language |

## Decision Criteria

- **Actionable, not cosmetic.** Every finding has a severity, a location (file + ID), and a fix.
- **Surface goal–work misalignment** (strategy lens), not just typos.
- **Never fabricate a pass.** Missing artifacts and `no-go` verdicts are reported as findings.
- **Stop condition**: all four lenses applied to the available artifacts and findings ranked by
  severity.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/01_ux/journey-maps.md` | Required (minimum) | `/product:map-journey` | block with a message — too little to review before this |
| later-phase artifacts | Optional | spec/domain/quality skills | review only what exists; note coverage gaps |
| `work/traceability.json` | Recommended | all skills | traceability lens degrades; note it |

## Process

1. **Read** all existing artifacts and `work/traceability.json`.
2. **Consistency lens** — cross-check ID usage and terminology. Apply
   `@rules/product/review-and-report.md`.
3. **Traceability lens** — validate the graph; flag orphans and dangling references.
4. **Extensibility lens** — test domain boundaries and API reuse against future features.
5. **Strategy lens** — Vision↔scope, economics, differentiation durability.
6. **Rank & record** — order findings by severity; write the file; append a summary to
   `work/context.md`.

## Rerun

Designed to be re-run mid-pipeline as artifacts accumulate — it reviews whatever exists.

## Output

`reports/report/review.md`, a severity-ranked findings list across the four lenses.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/review-and-report.md` | The four lenses and how to score findings |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:report` | Downstream — consolidates artifacts; surfaces review findings |
| `/product:validate-assumptions` | Related — the gate verdict feeds the strategy lens |
| `/product:adapt-change` | Related — review findings can trigger re-propagation |
