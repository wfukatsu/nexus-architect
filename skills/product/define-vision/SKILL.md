---
description: |
  Define the product core — Vision / Mission / Values — through dialogue, as a Product Vision
  Board plus an Amazon-style PR-FAQ. Research market/competitors as needed and feed it back.
  /product:define-vision [target] [--input=<file|dir>] [--auto] [--lang=ja|en] [--no-research].
  Entry point of the product pipeline.
model: opus
user_invocable: true
---

# Vision / Mission / Values

## Desired Outcome

Produce the product core as two deliverables:

1. **Vision / Mission / Values** — `reports/00_core/vision-mission-value.md`
   - A Product Vision Board (Vision, Target Group, Needs, Product, Business Goals)
   - Mission (how the vision is pursued) and Values (decision principles)
   - Each element carries a `VIS-` ID
2. **PR-FAQ** — `reports/00_core/pr-faq.md`
   - Press release (heading → subheading[target+benefit] → summary → problem[customer's words]
     → solution[product+differentiation] → quotes & CTA)
   - External FAQ (pricing, functionality, purchase, support) and Internal FAQ (market size,
     competition, unit economics, risks, **Go/No-Go criteria**)

The Go/No-Go criteria here are not decoration: they become the real gate enforced by
`/product:validate-assumptions`.

## Invocation

```
/product:define-vision [target] [--input=<file|dir>]... [--auto] [--lang=ja|en] [--no-research]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `target` | Optional | Product name / one-line idea |
| `--input=<file\|dir>` | Optional, repeatable | Business brief, RFP, notes, prior docs |
| `--auto` | Optional | Skip elicitation; generate from inputs only. Unknowns → `TBD` |
| `--lang` | Optional | Override output language |
| `--no-research` | Optional | Suppress web research |

## Decision Criteria

- **Vision**: ambitious, memorable, one sentence.
- **Target Group**: must be segmented — never "everyone".
- **Never fabricate.** Market facts, competitor names, and numbers come from `--input`, user
  answers, or cited web research. Unknowns become `TBD` in Open Questions — never guessed.
- **Stop condition**: all five Vision Board elements are filled (or explicitly `TBD`), and the
  PR-FAQ has a problem, a differentiated solution, and Go/No-Go criteria.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| product idea / `--input` | Recommended | User | proceed with interactive elicitation |
| `reports/00_core/market-landscape.md` | Optional | `/product:research-landscape` (may be absent) | gather inline (unless `--no-research`) or `TBD` |
| `work/pipeline-progress.json` | Recommended | `/product:init-output` | ask for `output_language` |

## Process

1. **Read context** — load `--input`, `work/context.md`, `work/traceability.json`.
2. **Elicit (gap-driven)** — draw out target group, problem/job, and benefit. Ask only what the
   materials do not answer.
3. **Research** (unless `--no-research`) — when external facts are needed (market size,
   competitors, alternatives), search, cite source + URL, write findings into
   `reports/00_core/market-landscape.md`, and reflect them in the artifacts.
4. **Generate** — fill the Vision Board, then write the PR-FAQ. Apply `@rules/product/vision-frameworks.md`.
   Assign `VIS-` IDs.
5. **Validate** — target is segmented; differentiation is explicit; Go/No-Go criteria present.
6. **Append traceability** — for each `VIS-` ID add a node to `work/traceability.json`
   (`{id, type:"vision", title, skill:"define-vision", source_file, upstream:[]}`).
7. **Record** — write both files; append key decisions to `work/context.md`; log unknowns to
   Open Questions.

## Output

`reports/00_core/vision-mission-value.md` (includes a `VIS-` ID table with an Upstream column)
and `reports/00_core/pr-faq.md`.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/vision-frameworks.md` | Product Vision Board + Working Backwards PR-FAQ |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:define-success-metrics` | Downstream — turns the vision into a North Star |
| `/product:define-scope` | Downstream — bounds the product |
| `/product:validate-assumptions` | Enforces the PR-FAQ Go/No-Go criteria |
| `/product:adapt-change` | Re-runs this skill when upstream context changes |
