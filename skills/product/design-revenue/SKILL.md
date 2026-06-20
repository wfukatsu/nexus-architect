---
description: |
  Design the revenue/business model and a recomputable benefit-evaluation template — Lean
  Canvas/BMC, a chosen revenue model, unit-economics formulas (LTV/CAC, payback, ROI/NPV), and
  falsifiable value hypotheses. Price and CAC are sent to validate-assumptions, not computed as fact.
  /product:design-revenue [--input=<file|dir>] [--auto] [--lang=ja|en].
model: opus
user_invocable: true
---

# Revenue Model & Benefit Evaluation

## Desired Outcome

Produce two deliverables:

1. **Revenue model** — `reports/00_core/revenue-model.md` (`REV-` IDs):
   - **Lean Canvas / BMC** — the 9 blocks (Lean Canvas for new/uncertain products)
   - **Revenue model selection** — which pattern and *why it fits the value created*
2. **Benefit evaluation** — `reports/00_core/benefit-evaluation.md`:
   - **Quantitative (recomputable template)** — LTV, CAC, LTV:CAC (≥3 benchmark), CAC payback,
     ROI/NPV — formulas with inputs, where price/CAC are `TBD-assumption` not fixed numbers
   - **Qualitative** — value hypotheses framed as "If we ship X, metric Y moves Z% within T"
     (referencing `NSM-`), each with a validation method

## Invocation

```
/product:design-revenue [--input=<file|dir>]... [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--input=<file\|dir>` | Optional, repeatable | Pricing material, financial assumptions, prior models |
| `--auto` | Optional | Skip elicitation; unknowns → `TBD` / `TBD-assumption` |
| `--lang` | Optional | Override output language |

## Decision Criteria

- **Price and CAC are assumptions, not arithmetic.** Record them as `TBD-assumption` and hand them
  to `/product:validate-assumptions` to test in the market (Van Westendorp, pre-sale). Do not
  present spreadsheet outputs as established facts.
- **The model must fit how value is delivered** — justify the chosen revenue pattern, don't just
  name it.
- **Unit economics are a template, not a verdict** — set up formulas so they recompute once real
  evidence arrives; flag the LTV:CAC ≥ 3 / payback < 12mo benchmarks.
- **Every value hypothesis is falsifiable** and references an `NSM-` metric.
- **Stop condition**: a justified revenue model on a canvas, a recomputable unit-economics
  template with assumptions flagged, and falsifiable value hypotheses.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/00_core/vision-mission-value.md` | Required | `/product:define-vision` | block with a message |
| `reports/00_core/success-metrics.md` | Recommended | `/product:define-success-metrics` | value hypotheses lack `NSM-` anchors; mark `TBD` |
| `reports/00_core/market-landscape.md` | Optional | `/product:research-landscape` | proceed; pull sizing/pricing context if present |

## Process

1. **Read context** — vision, success metrics, market landscape, `work/traceability.json`.
2. **Canvas** — fill Lean Canvas/BMC 9 blocks from upstream artifacts.
3. **Select model** — choose the revenue pattern and justify the fit. Apply
   `@rules/product/revenue-models.md`.
4. **Quantitative template** — set up LTV/CAC/payback/ROI/NPV formulas; mark price & CAC as
   `TBD-assumption` for the gate.
5. **Qualitative** — write value hypotheses ("If we ship X, metric Y moves Z%") with validation
   methods, referencing `NSM-`.
6. **Append traceability** — add `REV-` nodes to `work/traceability.json` with Upstream
   `VIS-`/`NSM-` references; mark `TBD-assumption` items so `validate-assumptions` can pick them up.
7. **Record** — write both files; append decisions to `work/context.md`; log assumptions to Open
   Questions.

## Output

`reports/00_core/revenue-model.md` and `reports/00_core/benefit-evaluation.md`, with `REV-` ID
tables (Upstream column) and price/CAC flagged as `TBD-assumption`.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/revenue-models.md` | BMC/Lean Canvas, revenue taxonomy, unit economics, value hypothesis |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:define-vision` | Upstream — business goals originate here |
| `/product:define-success-metrics` | Upstream — value hypotheses move `NSM-` metrics |
| `/product:research-landscape` | Upstream (optional) — market sizing & pricing context |
| `/product:validate-assumptions` | Downstream — price/CAC `TBD-assumption`s validated here |
| `/product:adapt-change` | Re-runs this skill when economics change |
