---
description: |
  Research the market and competitors in one pass — market sizing (TAM/SAM/SOM), trends,
  alternatives, a competitive matrix, and Kano classification — then recommend a differentiation
  (PoD) vs parity (PoP) strategy. Sources are always cited (name + URL).
  /product:research-landscape [target] [--input=<file|dir>] [--auto] [--lang=ja|en] [--no-research].
model: opus
user_invocable: true
---

# Market & Competitive Landscape

## Desired Outcome

Produce one deliverable:

1. **Market landscape** — `reports/00_core/market-landscape.md`:
   - **Market overview** — TAM/SAM/SOM (bottom-up preferred), trends, and alternatives incl. the
     status-quo / "do nothing"
   - **Competitive matrix** — direct & indirect competitors on dimensions the segment cares about
   - **Kano classification** — Must-be (→ PoP / parity) vs Delighter (→ PoD / differentiation)
   - **Strategy recommendation** — reach parity on PoP efficiently, concentrate on a few
     defensible PoDs; flag that delighters decay and need refresh

Every figure, competitor, and claim carries a source (name + URL). This file is consumed by
`define-vision`, `design-revenue`, and `design-positioning`.

## Invocation

```
/product:research-landscape [target] [--input=<file|dir>]... [--auto] [--lang=ja|en] [--no-research]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `target` | Optional | Product name / one-line idea (often passed by an internal caller) |
| `--input=<file\|dir>` | Optional, repeatable | Existing market/competitor material |
| `--auto` | Optional | Skip elicitation; synthesize from inputs/research only |
| `--lang` | Optional | Override output language |
| `--no-research` | Optional | Use only `--input`/existing docs; do not search the web |

## Decision Criteria

- **No source, no number.** Unsourced market sizes and competitor claims are omitted and logged as
  `TBD`, never estimated for effect.
- **Bottom-up over top-down** for sizing (# customers × price × frequency beats "X% of a big number").
- **Don't over-invest in parity.** Recommend efficiency on PoP, concentration on PoD (delighters).
- **`--no-research`** restricts to provided materials; gaps become `TBD`.
- **Stop condition**: market overview, competitive matrix, Kano split, and a PoD/PoP recommendation
  are present, each backed by a cited source or marked `TBD`.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| product idea / `target` / `--input` | Recommended | User or internal caller | proceed with what is known; mark gaps `TBD` |
| `reports/00_core/vision-mission-value.md` | Optional | `/product:define-vision` (may run before it) | proceed; this skill often runs first |

## Process

1. **Read context** — `target`, `--input`, `work/context.md`, vision if present.
2. **Size the market** — TAM/SAM/SOM bottom-up; record sources.
3. **Research** (unless `--no-research`) — trends, alternatives, competitors; cite name + URL for
   every fact.
4. **Compare** — build the competitive matrix on segment-relevant dimensions; identify white space.
5. **Classify & recommend** — Kano (Must-be→PoP, Delighter→PoD); recommend the differentiation
   strategy. Apply `@rules/product/positioning-kano-hook.md` and `@rules/product/revenue-models.md`.
6. **Append traceability** — add nodes for key findings to `work/traceability.json`.
7. **Record** — write the file; append decisions to `work/context.md`; log `TBD`s to Open Questions.

## Output

`reports/00_core/market-landscape.md`, with sourced market data, a competitive matrix, a Kano
split, and a PoD/PoP strategy recommendation.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/revenue-models.md` | TAM/SAM/SOM sizing, revenue model taxonomy |
| `@rules/product/positioning-kano-hook.md` | Competitive matrix, PoD/PoP, Kano |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:define-vision` | Consumer — feeds market facts into the Vision Board & PR-FAQ |
| `/product:design-revenue` | Downstream — revenue model builds on this market view |
| `/product:design-positioning` | Downstream — positioning builds on PoD/PoP & Kano |
| `/product:adapt-change` | Re-runs this skill when the market shifts |
