---
description: |
  Design positioning (Dunford 5-component canvas), the touchpoint × device × timing matrix, and the
  motivation/retention loop (Fogg + Hook + Kano delighter refresh) in one document. Claims customer
  value, not features; avoids dark patterns. /product:design-positioning [--auto] [--lang=ja|en].
model: opus
user_invocable: true
---

# Positioning & Engagement

## Desired Outcome

Produce one deliverable:

1. **Positioning** — `reports/01_ux/positioning.md` (`POS-` and `HOOK-` IDs):
   1. **Positioning canvas (Dunford 5)** — competitive alternatives, unique attributes,
      value (+proof), target segment, market category
   2. **Differentiation vs parity** — chosen PoDs vs PoPs (from the market landscape)
   3. **Touchpoint × device × timing matrix** — per journey touchpoint, the device and the moment
      the message is delivered
   4. **Hook canvas** (`HOOK-`) — Trigger → Action → Variable Reward → Investment
   5. **Kano delighter refresh plan** — how differentiation is continuously replenished as
      delighters decay into expectations

## Invocation

```
/product:design-positioning [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--auto` | Optional | Generate from upstream artifacts without elicitation; gaps → `TBD` |
| `--lang` | Optional | Override output language |

## Decision Criteria

- **Claim value (customer outcomes), not features.** Positioning is derived deliberately via the
  Dunford order (alternatives → attributes → value → segment → category).
- **Don't fight on parity.** Concentrate on a few defensible PoDs; assume delighters decay and plan
  refresh.
- **Retention must move a metric.** Each Hook/engagement tactic should advance an `NSM-`
  retention/engagement input metric.
- **No dark patterns.** Engagement is earned through value, never coercion or deceptive UX.
- **Stop condition**: a 5-component positioning canvas, a touchpoint×device×timing matrix, a Hook
  canvas tied to `NSM-`, and a delighter-refresh plan.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/01_ux/journey-maps.md` | Required | `/product:map-journey` | block with a message — the matrix needs touchpoints |
| `reports/00_core/market-landscape.md` | Optional | `/product:research-landscape` | derive PoD/PoP inline or mark `TBD` |
| `reports/00_core/success-metrics.md` | Recommended | `/product:define-success-metrics` | Hook tactics lack `NSM-` anchors; mark `TBD` |
| `reports/00_core/vision-mission-value.md` | Required | `/product:define-vision` | block with a message |

## Process

1. **Read context** — journey maps, market landscape, success metrics, vision,
   `work/traceability.json`.
2. **Frame positioning** — category → value → unique attributes via the Dunford order. Apply
   `@rules/product/positioning-kano-hook.md`.
3. **Build the matrix** — assign device + timing to each journey touchpoint.
4. **Design engagement** — motivation via Fogg (Motivation × Ability × Prompt); retention via the
   Hook loop whose Investment step accumulates switching cost.
5. **Refresh plan** — schedule replenishment of Kano delighters.
6. **Append traceability** — add `POS-`/`HOOK-` nodes to `work/traceability.json` with Upstream
   `JNY-`/`NSM-`/market references.
7. **Record** — write the file; append decisions to `work/context.md`;
   ask remaining unknowns and log only what stays open (@rules/open-questions.md).

## Output

`reports/01_ux/positioning.md`, with `POS-`/`HOOK-` ID tables (Upstream column), the touchpoint
matrix, and the delighter-refresh plan.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/positioning-kano-hook.md` | Dunford canvas, PoD/PoP, Kano, Fogg + Hook, touchpoint matrix |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:map-journey` | Upstream — touchpoints feed the matrix |
| `/product:research-landscape` | Upstream (optional) — PoD/PoP & Kano source |
| `/product:define-success-metrics` | Upstream — Hook tactics target `NSM-` metrics |
| `/product:generate-ui-mock` | Downstream — positioning informs the mocks |
| `/product:adapt-change` | Re-runs this skill when the competitive frame shifts |
