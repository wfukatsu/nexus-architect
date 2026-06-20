---
description: |
  Extract the riskiest assumptions the strategy depends on, attach the cheapest test and a
  kill/pivot threshold to each, and return a Go/No-Go verdict. The validation gate that connects
  document generation to hypothesis testing.
  /product:validate-assumptions [--auto] [--lang=ja|en]. Rerunnable as evidence arrives.
model: opus
user_invocable: true
---

# Validate Assumptions (Gate)

## Desired Outcome

Produce two deliverables and a gate verdict:

1. **Assumptions** — `reports/00_core/assumptions.md` (`ASM-` IDs): each falsifiable assumption
   classified as **desirability** (will they want it) / **viability** (will it make money) /
   **feasibility** (can we build it), and ranked by collapse impact ("if this is wrong, how much
   of the strategy falls?").
2. **Validation plan** — `reports/00_core/validation-plan.md`: for each top `ASM-`, the cheapest
   test (customer interview, smoke test / fake-door landing page, concierge MVP, Wizard-of-Oz,
   **pre-sale** — the strongest viability test), a **kill/pivot threshold**, and current status.
3. **Gate verdict** — written to `work/pipeline-progress.json` → `gates.validate-assumptions`:
   `go` or `no-go`, with the list of open (untested, high-risk) assumptions.

## Invocation

```
/product:validate-assumptions [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--auto` | Optional | Generate without elicitation; record gaps as `TBD` |
| `--lang` | Optional | Override output language |

## Decision Criteria

- **Name what would falsify the strategy.** This skill is not complete until each top assumption
  has a falsifiable statement, a cheapest test, and a kill/pivot threshold.
- **Price and CAC are assumptions, not arithmetic.** Pull any `TBD-assumption` values from the
  vision/scope/revenue work and treat them as items to validate in the market (e.g.
  Van Westendorp, pre-sale), not numbers to compute.
- **Verdict logic**: `no-go` if any collapse-critical assumption is both untested and lacks a
  defined test+threshold; otherwise `go` (with open assumptions listed for tracking).
- **Stop condition**: top assumptions ranked, each with test + threshold, and a verdict recorded.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/00_core/vision-mission-value.md` | Required | `/product:define-vision` | block with a message |
| `reports/00_core/scope-definition.md` | Required | `/product:define-scope` | block with a message |
| `reports/00_core/success-metrics.md` | Optional | `/product:define-success-metrics` | use if present |
| `reports/00_core/revenue-model.md` | Optional | `/product:design-revenue` | pull price/CAC assumptions if present |

## Process

1. **Read** all Phase-1 artifacts and `work/traceability.json`.
2. **Extract** every falsifiable assumption (focus on demand, price, CAC, channel, key technical
   risk). Classify desirability / viability / feasibility.
3. **Rank** by collapse impact (use the Riskiest-Assumption-Test mindset: the most dangerous
   belief first).
4. **Plan** — for each top assumption assign the cheapest credible test and a kill/pivot
   threshold. Apply `@rules/product/assumption-validation.md`.
5. **Verdict** — compute `go` / `no-go`; write it (and `open_assumptions`) to
   `pipeline-progress.json` → `gates`.
6. **Append traceability** — add `ASM-` nodes to `work/traceability.json` with upstream
   `VIS-`/`SCP-`/`NSM-`/revenue references (so `adapt-change` can re-open the gate).
7. **Record** — write both files; append the verdict to `work/context.md`.

## Rerun

As evidence arrives, re-run to update each assumption's status and the verdict. The gate is meant
to be revisited, not run once.

## Output

`reports/00_core/assumptions.md` and `reports/00_core/validation-plan.md`, plus the gate verdict
in `work/pipeline-progress.json`.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/assumption-validation.md` | Riskiest Assumption Test, test catalog, Van Westendorp, Go/No-Go |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:define-vision` | Upstream — Go/No-Go criteria originate here |
| `/product:define-scope` | Upstream — scope assumptions validated here |
| `/product:start` | Reads the verdict to gate the pipeline |
| `/product:adapt-change` | Re-opens the gate when external change invalidates an assumption |
