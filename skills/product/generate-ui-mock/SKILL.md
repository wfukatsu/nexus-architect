---
description: |
  Generate UI mocks for the key screens, driven by the domain stories — each story's numbered
  activities become the screen-by-screen interaction sequence — and styled by the active design
  system (DTCG tokens injected per screen), after briefly exploring 2–3 solution approaches per
  priority job and selecting one with rationale. Self-contained HTML per screen, at lo or mid
  fidelity. /product:generate-ui-mock [--fidelity=lo|mid] [--auto] [--lang=ja|en].
model: sonnet
user_invocable: true
---

# UI Mocks

## Desired Outcome

Produce one deliverable:

1. **UI mocks** — `reports/02_spec/ui-mocks/` (one self-contained HTML file per screen, inline CSS):
   - A short **solution-exploration note** per priority job: 2–3 approaches compared, one selected
     with rationale
   - The screens the selected approach needs, **derived from the domain story for that persona×job**
     — each numbered activity in the story becomes a screen interaction — each annotated with the
     `STORY-`/`JNY-`/`JOB-` it serves and the `CMP-` components it uses
   - **Styled by the active design system**: the system's `tokens.css` is injected into each screen
     so all mocks share one visual language (color/space/type). At **mid** fidelity, component
     styles are applied too; at **lo** fidelity, only tokens
   - Fidelity per `--fidelity` (default `lo`) — readable function and data over visual polish

## Invocation

```
/product:generate-ui-mock [--fidelity=lo|mid] [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--fidelity=lo\|mid` | Optional | `lo` (default) = tokens only; `mid` = tokens + design-system component styles. Capped by the active system's `fidelity_support`. |
| `--auto` | Optional | Generate without elicitation; pick the best-justified approach automatically |
| `--lang` | Optional | Override output language (UI copy) |

## Decision Criteria

- **The domain story is the axis.** When a domain story exists for the persona×job, the screen flow
  follows the story's numbered activities (one activity ≈ one screen interaction). Do not invent a
  flow that contradicts the story; if the story is missing a step, mark it `TBD` and note it.
- **The design system is the visual language.** Resolve the active system from
  `work/pipeline-progress.json` → `options.design_system`; inject its `tokens.css` into every screen
  and reference tokens (never hard-coded values). No system configured → fall back to ad-hoc lo-fi
  styling and note it. Never silently invent a competing palette.
- **Explore before drawing.** Each priority job gets 2–3 approaches compared and one selected with
  an explicit rationale — the mock is a rendering of a *chosen* solution for the story's flow.
- **Readability over fidelity.** A reader must be able to tell what function and what data each
  screen involves. Lo-fi is fine; ambiguous is not.
- **Trace every screen** to a `STORY-` activity (when present) / `JNY-` opportunity / `JOB-`.
- **Stop condition**: each priority job has a selected approach and its screens rendered as
  self-contained HTML, with each screen annotated with its `STORY-`/`JNY-`/`JOB-`.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/01_ux/domain-stories/` | Recommended | `/product:create-domain-story` | proceed; derive the screen flow from journey opportunities directly, note the thinner basis |
| `design-system/{active}/tokens.css` | Recommended | `/product:design-system` | proceed with ad-hoc lo-fi styling; note no design system was applied |
| `reports/01_ux/journey-maps.md` | Required | `/product:map-journey` | block with a message — screens derive from opportunities |
| `reports/01_ux/positioning.md` | Recommended | `/product:design-positioning` | proceed; note positioning gaps as `TBD` |
| `reports/01_ux/personas.md` | Recommended | `/product:generate-persona` | proceed with the primary persona only |

## Process

1. **Read context** — domain stories, journey opportunities, positioning, personas, and the active
   design system (`options.design_system` → `design-system/{name}/tokens.css` + `components.md`),
   `work/traceability.json`.
2. **Explore solutions** — per priority job, sketch 2–3 approaches, compare, select with rationale.
   Apply `@rules/product/ui-to-domain.md`.
3. **Enumerate screens** — walk the domain story's numbered activities and map each to a screen
   interaction (one activity ≈ one screen step); fall back to journey opportunities for any
   persona×job without a story. List the screens the selected approach needs.
4. **Lay out & render** — element placement → self-contained HTML per screen, injecting the design
   system's `tokens.css` inline and referencing tokens. At `--fidelity=mid`, also apply the `CMP-`
   component styles; at `lo`, tokens only. No active system → ad-hoc inline CSS (noted).
5. **Annotate** — tag each screen with `STORY-` (when present) / `JNY-` / `JOB-` and the `CMP-` used.
6. **Append traceability** — add screen nodes to `work/traceability.json` with Upstream
   `STORY-`/`JNY-`/`CMP-` references and the selected-approach rationale.
7. **Record** — write the HTML files + the exploration note; append decisions to `work/context.md`.

## Output

`reports/02_spec/ui-mocks/` — one self-contained HTML file per screen plus a solution-exploration
note, each screen annotated with `STORY-`/`JNY-`/`JOB-`.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/ui-to-domain.md` | Solution exploration, screen derivation, lo-fi fidelity rule |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:create-domain-story` | Upstream — its activities are the screen-flow axis |
| `/product:design-system` | Upstream — supplies the tokens/components (visual language) |
| `/product:map-journey` | Upstream — opportunities drive the screens |
| `/product:design-positioning` | Upstream — positioning informs the screens |
| `/product:define-features` | Downstream — extracts features from these mocks |
| `/product:define-data-model` | Downstream — derives entities from these mocks |
| `/product:adapt-change` | Re-runs this skill when the solution changes |
