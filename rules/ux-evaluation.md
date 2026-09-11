# UX Evaluation of an Existing UI

Applies whenever a skill **scores the user experience of an existing system**:
`/architect:evaluate-ux`, and `/architect:integrate-evaluations` when it merges that score.

The evaluation is an **expert review grounded in the code**, not a usability test. It can say that a
form has no labels, that a delete button does not ask, that the same action has three names and the
primary blue has four shades; it cannot say how long real users take or where they give up. Every
report states which of the two it is, and a static finding is never presented as observed user
behaviour.

Judgement is unavoidable, so it is fenced: a fixed vocabulary of defects, each owned by one axis
with a default severity (§5); scores bounded by measured metrics and by the severity of their own
findings (§2); one finding per defect (§6). Two runs on the same UI should differ only where the
evidence differs.

## 1. Evidence

| Evidence | Where it comes from | What it can establish |
|----------|---------------------|-----------------------|
| `static` | `ui-inventory.json`, `ui-design-tokens.json` and the source they cite | Structure: labels, alt text, declared language, color pairs, navigation graph, input burden, consistency |
| `runtime` | `--base-url`: per screen route, a screenshot and an accessibility check — axe-core with the script driver, or the accessibility snapshot plus the computed-contrast check with the Playwright MCP driver | What the browser actually renders: accessible names, computed contrast, target sizes, content injected by script, error states of a submitted form |

A finding is `runtime` only when the claim itself is **observable in a capture**: an attribute, an
accessible name, a computed value, a measured size, a rendered error state. An interaction that was
not performed — what happens when a destructive button is clicked — stays `static` even when a
screenshot shows the button. Runtime evidence can confirm, refine or withdraw a static finding, and
the evaluation records which (§6 rule 10).

**Measure, do not estimate.** Every count and ratio in the evaluation comes from
`tools/lib/ui_metrics.py`, which computes them deterministically from the inventory and the token
file — including contrast ratios. Findings may quote a metric, as `metrics.<path>` with its value;
they do not state numbers the tool did not produce.

**Out of scope.** Authorization, injection and other security defects, business logic in the view
layer and client-only validation are facts of the inventory for `/architect:investigate-security`
and the redesign — not UX findings. The method statement lists them as routed, not scored.

## 2. Axes

| Key | Axis | Weight | Owns |
|-----|------|--------|------|
| H | Heuristic usability | 30% | H1, H2, H5, H8, H9 |
| A | Accessibility | 25% | WCAG criteria of §4 except 3.3.7 |
| E | Task efficiency and input burden | 20% | H7, WCAG 3.3.7 |
| C | Consistency | 15% | H4 |
| N | Navigation and information architecture | 10% | H3, H6, H10 |

A finding cites a criterion its axis owns. Every criterion has exactly one owner, so the same
defect cannot be scored twice under two names.

### Score bands (every axis)

| Score | Meaning |
|-------|---------|
| 5 | No finding above `info`; the axis would pass an expert review as is |
| 4 | Only `minor` findings |
| 3 | `major` findings on some screens, or `minor` findings across most of them |
| 2 | `major` findings across many screens, or a `critical` finding |
| 1 | `critical` findings that stop tasks or exclude users on several screens |

The bands bind in one direction: an axis with a `critical` finding scores at most 2, with a `major`
finding at most 3, with only `minor` findings at most 4. An axis scored 3 or lower names the findings
that justify it.

### Metric caps

A score also never exceeds the cap its metrics allow. Caps say "a measured defect exists, so this
axis is not perfect" — they never push a score below 3; how far below 3 it goes is decided by the
severity of the findings, above. `ui_metrics.py` computes them (`caps` in its output) as
`5 − min(2, points)`:

| Axis | One point each for |
|------|--------------------|
| H | one destructive action without confirmation; a second one |
| A | any screen with a static violation (unlabeled input, image without `alt`, missing `lang`, text pair below the contrast minimum); violations on more than 10% of the screens |
| E | any redundant input; a task longer than five screens; a screen with more than twelve visible inputs |
| C | any fragmented token cluster; any label drift for one command; any hand-built duplicate component |
| N | any orphan; any dead end; any unreachable screen that is not an orphan |

Unlabeled inputs exclude `hidden` controls; images marked `decorative` need no `alt`. Contrast
minimums are WCAG 1.4.3: 4.5:1 for normal text, 3:1 for large text. Depth and destination-label
variants are reported for judgement and cap nothing.

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

WCAG 2.2 criteria that code or a rendered page can show — the only ones a finding may cite, as
`WCAG <number>`:

| Criterion | Static | Runtime |
|-----------|--------|---------|
| 1.1.1 Non-text Content | `images[].alt` | accessible name of `img` |
| 1.3.1 Info and Relationships · 3.3.2 Labels or Instructions · 4.1.2 Name, Role, Value | `label_association` | accessible name of the control |
| 1.3.5 Identify Input Purpose | `autocomplete` on personal-data inputs | — |
| 1.4.1 Use of Color | messages and states told only by color | screenshot |
| 1.4.3 Contrast (Minimum) · 1.4.11 Non-text Contrast | `color_pairs` | computed contrast |
| 2.1.1 Keyboard | click handlers on non-interactive elements | keyboard walk |
| 2.4.2 Page Titled · 2.4.4 Link Purpose · 2.4.6 Headings and Labels | screen name, link labels, headings | accessibility snapshot |
| 2.5.8 Target Size (Minimum) | — | measured bounding boxes (24 × 24 px) |
| 3.1.1 Language of Page | `lang` | `html[lang]` |
| 3.3.1 Error Identification · 3.3.3 Error Suggestion | `messages` | a submitted invalid form |
| 3.3.7 Redundant Entry | `redundant_with` | prefilled value |

## 5. Findings

`{id: UX-###, axis, defect, criterion, severity, severity_reason, location: {screen, action, input,
component, feature, token, source}, title, description, recommendation, evidence: static|runtime,
evidence_ref, runtime_outcome}`

Title, description, recommendation and rationale are written in the configured `output_language`.

### Defect vocabulary

Every finding names its defect. The defect decides the axis, the default criterion and the default
severity; a severity other than the default carries a one-line `severity_reason`.

| Defect | Axis | Criterion | Default severity |
|--------|------|-----------|------------------|
| `unlabeled-input` | A | WCAG 1.3.1 (or 3.3.2 / 4.1.2) | `major` — `critical` when a required input on a primary task has no accessible name at all |
| `missing-alt` | A | WCAG 1.1.1 | `major` |
| `low-contrast` | A | WCAG 1.4.3 / 1.4.11 | `major` |
| `missing-lang` | A | WCAG 3.1.1 | `major` |
| `small-target` | A | WCAG 2.5.8 | `minor` |
| `error-not-identified` | A | WCAG 3.3.1 / 3.3.3 | `minor` |
| `missing-input-purpose` | A | WCAG 1.3.5 | `minor` |
| `destructive-without-confirmation` | H | H5 | `major` — `critical` when it irreversibly deletes business data |
| `vague-error-message` | H | H9 | `major` |
| `no-feedback` | H | H1 | `minor` |
| `script-dependent-content` | H | H1 | `minor` |
| `redundant-input` | E | WCAG 3.3.7 (or H7) | `minor` |
| `excessive-steps` | E | H7 | `minor` |
| `excessive-inputs` | E | H7 | `minor` |
| `label-drift` | C | H4 | `minor` |
| `hand-built-duplicate` | C | H4 | `minor` |
| `token-fragmentation` | C | H4 | `minor` |
| `dead-end` | N | H3 | `major` |
| `missing-path` | N | H3 | `major` — a capability with no way in |
| `orphan-screen` | N | H10 (help) or H6 | `minor` — `major` when a task needs what it holds |
| `other` | any | any the axis owns | judged; `severity_reason` required |

Severity follows the table rather than `skills/review-registry.json`: `critical` blocks a task or
excludes a group of users from one; `major` makes a task error-prone or markedly harder, or must be
fixed before the new UI ships; `minor` is friction; `info` is a suggestion.

### Location

At least one of `screen`, `component`, `feature` or `token` is set, and what is set agrees:
`action` is an action id of `screen`, `input` is an input name of `screen`, `component` is used by
`screen`, `feature` has an action on `screen`. `source` is `path:line` into the target code. The
**subject** of a finding is its most specific element — action, then input, then component, token,
feature, screen.

## 6. Well-formedness rules

An evaluation is not written out until all ten hold. Each is asserted by
`tools/lib/ux_evaluation.py` against `reports/02_evaluation/ux-evaluation.json`.

1. **Exactly the five axes**, each once, each with the weight of §2.
2. **Every axis score is an integer from 1 to 5, within its metric cap and its severity bound**
   (§2).
3. **The UXI is the formula's value** (§3), to the rounding.
4. **The band is the UXI's band.**
5. **Every finding is complete** — a unique `UX-###` id, a defect from §5 on its axis, a criterion
   its axis owns, a severity (with a reason when it is not the defect's default), a title, a
   description and a recommendation.
6. **Every location exists and agrees** (§5 Location), and its source is real.
7. **Every score of 3 or lower is justified** by a finding on its axis, and every finding is listed
   by exactly its own axis.
8. **The metrics are the tool's** — the `metrics` block equals what `ui_metrics.py` computes from
   the inventory now.
9. **One defect, one finding** — no two findings share a defect and a subject.
10. **Runtime evidence is real** — `mode`, `base_url` and the capture list agree; a runtime finding
    cites a file under `reports/02_evaluation/ux-evidence/` for a screen that was captured, and says
    whether it `confirmed`, `refined` or is `new` against the static pass; a static finding cites no
    evidence file; a withdrawn static finding is listed with its reason and evidence.

## 7. What downstream consumes

| Consumer | What it takes |
|----------|---------------|
| `/architect:integrate-evaluations` | The UXI, the band and the `critical`/`major` findings, as the UX track of the unified improvement plan |
| `/architect:redesign` and later design skills | The band as a decision input: `needs-improvement` and `poor` flows are redesigned, not ported |
| `/architect:investigate-security` | The out-of-scope facts the method statement routes to it |
| `/product:design-system` | The `C` findings, as the consolidation list for `--import` |

**A score is a summary, the findings are the result.** A reader who acts on the UXI alone acts on
nothing; the report leads with the findings that cost users the most.
