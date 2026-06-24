---
description: |
  Build or incorporate a design system — DTCG design tokens (color/type/spacing/radius/elevation),
  a component inventory, and usage guidelines — managed separately from a single pipeline run so it
  can be reused, versioned, and swapped. Build from positioning/personas, or --import an existing
  system (Tailwind / DTCG / Figma Tokens / CSS theme). Feeds generate-ui-mock at lo or mid fidelity.
  /product:design-system [--name=<id>] [--import=<path>] [--fidelity=lo|mid] [--auto] [--lang=ja|en].
model: opus
user_invocable: true
---

# Design System

## Desired Outcome

Produce one separately-managed design system under `design-system/{name}/`:

1. **Tokens** — `tokens.json` (W3C **DTCG** format) + `tokens.css` (`:root` CSS variables): color,
   typography, spacing, radius, elevation, motion — raw scales plus semantic aliases
   (`color.bg/fg/primary/danger`, …).
2. **Components** — `components.md` (`CMP-` IDs): a component inventory (Button, Input, Card, Modal,
   …) with variants/states and the token-based CSS classes used at **mid** fidelity.
3. **Guidelines** — `guidelines.md`: when to use what, accessibility rules (contrast, target size,
   reduced motion), voice & tone.
4. **Manifest** — `manifest.json`: `name`, `version` (semver), `mode` (`built`|`imported`),
   `source`, `fidelity_support`, `generated_at`.
5. **Preview** — `preview.html`: self-contained token + component gallery for visual review.

It is the **"how it looks" layer** that `generate-ui-mock` consumes — domain stories decide *what*
each screen does; the design system decides the shared *visual language*.

## Invocation

```
/product:design-system [--name=<id>] [--import=<path>] [--fidelity=lo|mid] [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--name=<id>` | Optional | Name of the design system (kebab-case). Default `default`. Multiple named systems may coexist; the active one is recorded in the progress file. |
| `--import=<path>` | Optional | Incorporate an existing system: Tailwind config, DTCG JSON, Figma Tokens export, or a CSS/SCSS variable theme. Switches to **incorporate** mode. |
| `--fidelity=lo\|mid` | Optional | Fidelity the system must support (`lo` = tokens only, `mid` = tokens + component styles). Default `lo`; recorded in the manifest so mocks can render either. |
| `--auto` | Optional | Skip elicitation; derive/normalize from inputs only. |
| `--lang` | Optional | Override output language (guidelines/descriptions). |

## Decision Criteria

- **Tokens are the foundation.** Everything (components, mocks) references tokens, never raw values —
  so one source of truth governs the visual language and self-contained mocks stay consistent.
- **Build vs incorporate is explicit.** `--import` → normalize the existing system to the DTCG
  schema; unmapped values become `TBD` + Open Question. No `--import` → derive tokens from brand.
- **Never fabricate brand values.** In incorporate mode, an unknown maps to `TBD`, not a guess.
- **Accessibility is a gate (build mode).** Body contrast ≥ 4.5:1, large text ≥ 3:1; meaning never
  by color alone; honor reduced motion. Record the checked pairs.
- **Managed separately.** Write to `design-system/{name}/`, not under `reports/`; bump `version` on
  change; point `options.design_system` at the active system. The skill is **standalone** (runnable
  any time, independent of a full pipeline run).
- **Stop condition**: `tokens.json` (valid DTCG) + `tokens.css` + `components.md` + `guidelines.md` +
  `manifest.json` + `preview.html` exist; the progress file points at this system; contrast checks
  recorded (build mode) or import gaps listed as `TBD` (incorporate mode).

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/01_ux/positioning.md` | Recommended (build) | `/product:design-positioning` | derive a neutral, accessible default palette; mark brand choices `TBD` |
| `reports/01_ux/personas.md` | Recommended (build) | `/product:generate-persona` | apply default accessibility baseline (AA) |
| `reports/00_core/vision-mission-value.md` | Optional (build) | `/product:define-vision` | tone defaults to neutral |
| `--import` target | Required (incorporate) | User | if unreadable/unparseable, stop and report |

## Process

1. **Resolve mode** — `--import` present → incorporate; else build. Resolve `--name` (default
   `default`) and `--fidelity` (default `lo`).
2. **Build mode** — read positioning (brand), personas (a11y), vision (tone). Choose base hue + scale,
   type scale, spacing scale (4/8 base), radius/elevation steps; derive semantic aliases. Apply
   `@rules/product/design-system.md`. Run the contrast gate.
3. **Incorporate mode** — read `--import`; map its values into the DTCG schema (colors, type, spacing,
   radius, …). Record every unmapped concept as `TBD` + Open Question.
4. **Emit tokens** — write `tokens.json` (DTCG) and the paired `tokens.css` (`:root` variables).
5. **Inventory components** — write `components.md` with `CMP-` entries (variants/states) and, for
   **mid** fidelity, token-based CSS classes.
6. **Write guidelines** — usage, accessibility, voice & tone.
7. **Manifest + preview** — write `manifest.json` (with `version`); render `preview.html` (token +
   component gallery, self-contained).
8. **Activate** — set `work/pipeline-progress.json` → `options.design_system = "{name}"`.
9. **Append traceability** — add `DS-`/`TOK-`/`CMP-` nodes to `work/traceability.json` with Upstream
   `POS-`/`PER-` references (build) or `source` provenance (incorporate).
10. **Record** — append decisions to `work/context.md`; log every `TBD`.

## Output

`design-system/{name}/` — `tokens.json`, `tokens.css`, `components.md`, `guidelines.md`,
`manifest.json`, `preview.html`. Managed separately from `reports/`; `options.design_system` points
at the active system. Frontmatter/JSON keys stay English; guideline prose uses
`options.output_language`.

> Note: `design-system/` is a durable, separately-versioned asset (unlike the per-run `reports/`
> tree). Decide per project whether to commit it to version control.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/design-system.md` | Layered model, DTCG format, build vs incorporate, fidelity, a11y |
| `@rules/product/positioning-kano-hook.md` | Brand personality / delighters feeding token choices |

Generation engines you may delegate to: `example-skills:theme-factory`,
`example-skills:brand-guidelines`, `example-skills:frontend-design`, `design-html`.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:design-positioning` | Upstream — brand personality informs tokens (build mode) |
| `/product:generate-persona` | Upstream — accessibility needs constrain tokens |
| `/product:generate-ui-mock` | Downstream — injects `tokens.css`, renders at lo/mid fidelity |
| `/product:adapt-change` | Re-runs this skill when brand or the imported system changes |
