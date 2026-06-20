---
description: |
  Turn the product vision into a measurable shape — one North Star Metric plus 3–5 input metrics
  with targets and guardrails — that anchors downstream prioritization (RICE Impact, scope,
  positioning). /product:define-success-metrics [--auto] [--lang=ja|en].
model: opus
user_invocable: true
---

# Success Metrics / North Star

## Desired Outcome

Produce one deliverable:

1. **Success metrics** — `reports/00_core/success-metrics.md` (`NSM-` IDs):
   - **One North Star Metric** — a *leading* indicator of revenue/retention that expresses
     customer-received value (never raw revenue, never a vanity metric)
   - **3–5 input metrics** that the team can move directly and that drive the NSM
   - A mapping onto **AARRR or HEART** (one lens, not both mechanically)
   - For each metric: definition, measurement method/source, target value, and a **guardrail**
     counter-metric (`TBD` where no credible source exists)

These `NSM-` IDs become the anchor for RICE Impact in `define-scope`/`define-features` and for the
value hypotheses in `design-revenue`.

## Invocation

```
/product:define-success-metrics [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--auto` | Optional | Skip elicitation; generate from the vision only. Unknowns → `TBD` |
| `--lang` | Optional | Override output language |

## Decision Criteria

- **The North Star leads revenue — it is not revenue.** If improving the metric would not
  reliably pull future revenue/retention up, it is the wrong metric.
- **Express value in the customer's terms** and only choose metrics the team can actually move.
- **Every metric needs a measurement method.** Targets without a credible source are `TBD`, never
  invented.
- **Stop condition**: exactly one North Star, 3–5 input metrics, a guardrail per optimized metric,
  and each metric has a definition + measurement method.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/00_core/vision-mission-value.md` | Required | `/product:define-vision` | block with a message — metrics need the vision |
| `work/pipeline-progress.json` | Recommended | `/product:init-output` | ask for `output_language` |

## Process

1. **Read context** — vision, `work/context.md`, `work/traceability.json`.
2. **Define winning** — translate the vision's "definition of success" into a single North Star.
3. **Decompose** — derive 3–5 input metrics (e.g. breadth × depth × frequency × efficiency); each
   maps to a product lever.
4. **Map** — place the NSM and inputs on AARRR or HEART to expose which stage the strategy bets on.
   Apply `@rules/product/success-metrics.md`.
5. **Targets & guardrails** — set target values (or `TBD`) and a counter-metric per optimized
   metric; record measurement method/source.
6. **Append traceability** — add `NSM-` nodes to `work/traceability.json` with Upstream `VIS-`
   references.
7. **Record** — write the file; append decisions to `work/context.md`; log `TBD`s to Open Questions.

## Output

`reports/00_core/success-metrics.md`, with an `NSM-` ID table including an Upstream column.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/success-metrics.md` | North Star, input metrics, AARRR/HEART, targets & guardrails |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:define-vision` | Upstream — provides the vision the NSM measures |
| `/product:define-scope` | Downstream — RICE Impact references `NSM-` IDs |
| `/product:design-revenue` | Downstream — value hypotheses move `NSM-` metrics |
| `/product:validate-assumptions` | Downstream — metric targets become assumptions to test |
| `/product:adapt-change` | Re-runs this skill when the vision changes |
