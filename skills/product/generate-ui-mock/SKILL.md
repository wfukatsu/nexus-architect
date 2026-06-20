---
description: |
  Generate lo-fi UI mocks for the key screens from the journey, positioning, and personas — after
  briefly exploring 2–3 solution approaches per priority job and selecting one with rationale, so
  mocks render a chosen solution rather than locking in the first sketch. Self-contained HTML per
  screen. /product:generate-ui-mock [--auto] [--lang=ja|en].
model: sonnet
user_invocable: true
---

# UI Mocks

## Desired Outcome

Produce one deliverable:

1. **UI mocks** — `reports/02_spec/ui-mocks/` (one self-contained HTML file per screen, inline CSS):
   - A short **solution-exploration note** per priority job: 2–3 approaches compared, one selected
     with rationale
   - The screens the selected approach needs, each annotated with the `JNY-`/`JOB-` it serves
   - Lo-fi fidelity — readable function and data, not visual polish

## Invocation

```
/product:generate-ui-mock [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--auto` | Optional | Generate without elicitation; pick the best-justified approach automatically |
| `--lang` | Optional | Override output language (UI copy) |

## Decision Criteria

- **Explore before drawing.** Each priority job gets 2–3 approaches compared and one selected with
  an explicit rationale — the mock is a rendering of a *chosen* solution.
- **Readability over fidelity.** A reader must be able to tell what function and what data each
  screen involves. Lo-fi is fine; ambiguous is not.
- **Trace every screen** to a `JNY-` opportunity / `JOB-`.
- **Stop condition**: each priority job has a selected approach and its screens rendered as
  self-contained HTML with `JNY-`/`JOB-` annotations.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/01_ux/journey-maps.md` | Required | `/product:map-journey` | block with a message — screens derive from opportunities |
| `reports/01_ux/positioning.md` | Recommended | `/product:design-positioning` | proceed; note positioning gaps as `TBD` |
| `reports/01_ux/personas.md` | Recommended | `/product:generate-persona` | proceed with the primary persona only |

## Process

1. **Read context** — journey opportunities, positioning, personas, `work/traceability.json`.
2. **Explore solutions** — per priority job, sketch 2–3 approaches, compare, select with rationale.
   Apply `@rules/product/ui-to-domain.md`.
3. **Enumerate screens** — list the screens the selected approach needs.
4. **Lay out & render** — element placement → self-contained HTML (inline CSS) per screen.
5. **Annotate** — tag each screen with `JNY-`/`JOB-`.
6. **Append traceability** — add screen nodes to `work/traceability.json` with Upstream `JNY-`
   references and the selected-approach rationale.
7. **Record** — write the HTML files + the exploration note; append decisions to `work/context.md`.

## Output

`reports/02_spec/ui-mocks/` — one self-contained HTML file per screen plus a solution-exploration
note, each screen annotated with `JNY-`/`JOB-`.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/ui-to-domain.md` | Solution exploration, screen derivation, lo-fi fidelity rule |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:map-journey` | Upstream — opportunities drive the screens |
| `/product:design-positioning` | Upstream — positioning informs the screens |
| `/product:define-features` | Downstream — extracts features from these mocks |
| `/product:define-data-model` | Downstream — derives entities from these mocks |
| `/product:adapt-change` | Re-runs this skill when the solution changes |
