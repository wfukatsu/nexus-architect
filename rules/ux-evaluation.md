# UX Evaluation of an Existing UI

Applies whenever a skill **scores the user experience of an existing system**:
`/architect:evaluate-ux`, and `/architect:integrate-evaluations` when it merges that score.

The evaluation is an **expert review grounded in the code**, not a usability test. It can say that a
form has no labels, that a delete button does not ask, that the same action has three names and the
primary blue has four shades; it cannot say how long real users take or where they give up. Every
report states which of the two it is, and a static finding is never presented as observed user
behaviour.

## 1. Evidence

| Evidence | Where it comes from | What it can establish |
|----------|---------------------|-----------------------|
| `static` | `ui-inventory.json`, `ui-design-tokens.json` and the source they cite | Structure: labels, alt text, declared language, color pairs, navigation graph, input burden, consistency |
| `runtime` | `--base-url`: the rendered page, a screenshot and an axe-core run per screen route | What the browser actually renders: computed contrast, focus order, target size, content injected by script |

A finding is `runtime` only when a rendered page backs it, and it cites the evidence file. Runtime
evidence can confirm, refine or withdraw a static finding; it never adds a score the static pass
could not justify without saying so.

**Measure, do not estimate.** Every count and ratio in the evaluation comes from
`tools/lib/ui_metrics.py`, which computes them deterministically from the inventory and the token
file — including contrast ratios. The model writes judgements and findings; it does not write
numbers the tool can compute.

## 2. Axes

| Key | Axis | Weight | Grounded in |
|-----|------|--------|-------------|
| H | Heuristic usability | 30% | Nielsen's ten heuristics (§4) |
| A | Accessibility | 25% | WCAG 2.2 level A and AA success criteria that code can show (§4) |
| E | Task efficiency and input burden | 20% | Screens per task, inputs per task and per screen, required inputs, redundant entry |
| C | Consistency | 15% | Token fragmentation, component duplicates, label drift for the same command |
| N | Navigation and information architecture | 10% | Depth, orphans, unreachable screens, dead ends |

### Score bands (every axis)

| Score | Meaning |
|-------|---------|
| 5 | No finding above `info`; the axis would pass an expert review as is |
| 4 | Only `minor` findings, confined to a few screens |
| 3 | `major` findings on some screens, or `minor` findings across most of them |
| 2 | `major` findings across many screens, or one `critical` finding |
| 1 | `critical` findings that stop tasks or exclude users on several screens |

### Metric caps

A score never exceeds the cap its metrics allow. The caps are computed by `ui_metrics.py`
(`caps` in its output) and asserted by the validator; judgement may score lower, never higher.

| Axis | Cap |
|------|-----|
| H | 5, minus 1 if any destructive action has no confirmation, minus 1 more if three or more do |
| A | Share of screens with at least one static violation (unlabeled input, image without `alt`, missing `lang`, text pair below the contrast minimum): 0 → 5, ≤ 10% → 4, ≤ 25% → 3, ≤ 50% → 2, more → 1 |
| E | 5, minus 1 each for: any redundant input; a task longer than five screens; a screen with more than twelve visible inputs |
| C | 5, minus 1 each for: any fragmented token cluster; three or more fragmented clusters or more than twelve distinct colors; any label drift; any component duplicate |
| N | 5, minus 1 each for: any orphan; any dead end; any unreachable screen that is not an orphan; a depth greater than four |

Caps never go below 1. Unlabeled inputs exclude `hidden` controls; images marked `decorative` need
no `alt`. Contrast minimums are WCAG 1.4.3: 4.5:1 for normal text, 3:1 for large text.

## 3. Formula and bands

```
UXI = (0.30 × H + 0.25 × A + 0.20 × E + 0.15 × C + 0.10 × N) / 5 × 100     (rounded to 0.1)
```

| UXI | Band | Reading |
|-----|------|---------|
| 80 – 100 | `mature` | Improve incrementally alongside the migration |
| 60 – below 80 | `adequate` | Carry the UI over; fix the listed findings in the new implementation |
| 40 – below 60 | `needs-improvement` | Redesign the affected flows rather than port them |
| below 40 | `poor` | Treat the UI as a requirement source only; design the new UI from the journeys |

The bands are half-open, so every score falls in exactly one. The parent skill computes the UXI
from the axis scores after every axis evaluator has returned — a sub-agent returns a score and its
findings, never the index.

## 4. Criteria vocabulary

Every finding cites one criterion, either a Nielsen heuristic or a WCAG 2.2 success criterion.

| Id | Nielsen heuristic |
|----|-------------------|
| H1 | Visibility of system status |
| H2 | Match between the system and the real world |
| H3 | User control and freedom |
| H4 | Consistency and standards |
| H5 | Error prevention |
| H6 | Recognition rather than recall |
| H7 | Flexibility and efficiency of use |
| H8 | Aesthetic and minimalist design |
| H9 | Help users recognize, diagnose and recover from errors |
| H10 | Help and documentation |

WCAG 2.2 criteria that code or a rendered page can show, cited as `WCAG <number>`:

| Criterion | Static | Runtime |
|-----------|--------|---------|
| 1.1.1 Non-text Content | `images[].alt` | axe `image-alt` |
| 1.3.1 Info and Relationships · 3.3.2 Labels or Instructions · 4.1.2 Name, Role, Value | `label_association` | axe `label` |
| 1.4.1 Use of Color | messages and states told only by color | screenshot |
| 1.4.3 Contrast (Minimum) | `color_pairs` | axe `color-contrast` |
| 2.1.1 Keyboard | click handlers on non-interactive elements | keyboard walk |
| 2.4.2 Page Titled · 2.4.6 Headings and Labels | screen name and headings | axe |
| 2.5.8 Target Size (Minimum) | — | measured |
| 3.1.1 Language of Page | `lang` | axe `html-has-lang` |
| 3.3.1 Error Identification · 3.3.3 Error Suggestion | `messages` | submitted form |
| 3.3.7 Redundant Entry | `redundant_with` | — |

## 5. Findings

Findings use the review shape so `review-synthesizer`-style tooling can read them:

`{id: UX-###, axis, criterion, severity, location: {screen, component, feature, token, source}, title,
description, recommendation, evidence: static|runtime, evidence_ref}`

- At least one of `screen` (`UIS-`), `component` (`UIC-`), `feature` (`UIF-`) or `token` (a dotted
  token path) is set, and it exists in the inventory.
- Severity follows `skills/review-registry.json`: `critical` blocks a task or excludes a group of
  users (a form a screen-reader user cannot complete, an irreversible money-moving action with no
  confirmation); `major` must be fixed before the new UI ships; `minor` should be fixed; `info` is a
  suggestion.
- An axis scored 3 or lower names the findings that justify it.

## 6. Well-formedness rules

An evaluation is not written out until all nine hold. Each is asserted by
`tools/lib/ux_evaluation.py` against `reports/02_evaluation/ux-evaluation.json`.

1. **Exactly the five axes**, each once, each with the weight of §2.
2. **Every axis score is an integer from 1 to 5.**
3. **The UXI is the formula's value** (§3), within 0.5.
4. **The band is the UXI's band.**
5. **Every finding is complete** — a unique `UX-###` id, a declared axis, a criterion from §4, a
   severity, a title, a description and a recommendation.
6. **Every finding's location exists** in the inventory or the token file.
7. **Every score of 3 or lower is justified** by at least one finding on that axis, and every finding
   an axis lists is a finding on that axis.
8. **The metrics are the tool's** — the `metrics` block equals what `ui_metrics.py` computes from the
   inventory now, and **no score exceeds its cap**.
9. **Runtime evidence is real** — a `runtime` finding cites an evidence file that exists, and the
   evaluation records the base URL it was captured from.

## 7. What downstream consumes

| Consumer | What it takes |
|----------|---------------|
| `/architect:integrate-evaluations` | The UXI, the band and the `critical`/`major` findings, as the UX track of the unified improvement plan |
| `/architect:redesign` and later design skills | The band as a decision input: `needs-improvement` and `poor` flows are redesigned, not ported |
| `/product:design-system` | The consistency findings, as the consolidation list for `--import` |

**A score is a summary, the findings are the result.** A reader who acts on the UXI alone acts on
nothing; the report leads with the findings that cost users the most.
