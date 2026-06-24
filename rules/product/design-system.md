# Rules: Design System (design-system, consumed by generate-ui-mock)

Reference for building and incorporating a design system in the product pipeline. The design system
is the **"how it looks" layer**: domain stories decide *what* a screen does and in what order; the
design system decides the *visual language* every screen shares. It is managed **separately** from a
single pipeline run so it can be reused, versioned, and swapped across projects.

## Layered model (each layer depends on the one below)

```
Guidelines / Usage   — when to use what; accessibility; voice & tone
Patterns             — form, table, empty/loading/error states, navigation
Components           — Button / Input / Card / Modal … (variants + states)
Primitives           — Box / Stack / Text (layout atoms)
Design Tokens        — color / typography / spacing / radius / elevation / motion   ← foundation
```

**Tokens are the foundation.** With a single token source, every mock can stay self-contained yet
visually consistent (the same token CSS is injected into each HTML file — no shared external asset).

## Two modes

- **Build (greenfield)** — derive tokens from `positioning` (brand personality / Kano delighters),
  `personas` (accessibility needs: contrast, target size, motion sensitivity), and `vision` (tone).
  Choose a base hue + scale, a type scale, a spacing scale (e.g. 4/8 px base), radius/elevation
  steps; generate semantic aliases (`color.bg`, `color.fg`, `color.primary`, `color.danger`, …).
- **Incorporate (brownfield)** — `--import=<path>` reads an existing system and **normalizes it to
  the same token schema**: Tailwind config, W3C DTCG JSON, Figma Tokens export, or a CSS/SCSS
  variable theme (MUI/Chakra). Unmapped values → `TBD` with an Open Question; never invent brand
  values silently.

Both modes converge on **one DTCG token file**, so downstream tooling is identical.

## Token format — W3C DTCG

Use the Design Tokens Community Group format (`$value`, `$type`, `$description`; groups by category).
It is interoperable: convert to CSS variables, Tailwind, or native via Style Dictionary.

```json
{
  "color": {
    "primary": { "$type": "color", "$value": "#2563eb", "$description": "Primary brand / CTA" },
    "bg":      { "$type": "color", "$value": "#ffffff" },
    "fg":      { "$type": "color", "$value": "#0f172a" }
  },
  "space": { "2": { "$type": "dimension", "$value": "8px" } },
  "font":  { "body": { "$type": "fontFamily", "$value": ["Inter", "system-ui", "sans-serif"] } }
}
```

Emit a paired `tokens.css` (`:root { --color-primary: #2563eb; … }`) so mocks consume tokens via
CSS variables.

## Separate management

- Output to a **dedicated `design-system/<name>/` tree** (sibling to `reports/`, NOT inside it), so a
  pipeline rerun does not overwrite it and it can be shared across projects.
- Each system carries a `manifest.json`: `name`, `version` (semver — bump on change), `mode`
  (`built` | `imported`), `source`, `fidelity_support`, `generated_at`.
- Multiple named systems may coexist (themes); the active one is recorded in
  `work/pipeline-progress.json` → `options.design_system` (a name or path). `generate-ui-mock` reads
  that pointer; absent → it falls back to ad-hoc lo-fi styling.
- The skill is **standalone**: it can run any time, independent of a full pipeline run.

## Fidelity (selectable, consumed by generate-ui-mock)

- **lo** (default) — inject only the token CSS (color/space/type/radius). Lo-fi layout, but
  consistent palette/rhythm. Cheapest; good for fast iteration.
- **mid** — additionally apply component styles (Button/Input/Card/… classes) from `components.md`.
  Screens look closer to real UI. Higher generation cost.
- The system should provide both layers so either fidelity renders from the same source.

## Accessibility (non-negotiable in build mode)

- Body text contrast ≥ WCAG AA (4.5:1); large text ≥ 3:1. Record the checked pairs.
- Don't encode meaning by color alone (pair with icon/label).
- Respect `prefers-reduced-motion` for any motion tokens.

## ID convention & traceability

`DS-` for a design system, `TOK-` for tokens, `CMP-` for components. Append to
`work/traceability.json` with Upstream references (`POS-`/`PER-` → `TOK-`/`CMP-`); ui-mock screens
reference the `CMP-` they use.

## Tooling / sources

- W3C Design Tokens Community Group format (DTCG)
- Style Dictionary — token transformation/export
- Existing harness skills usable as generation engines: `example-skills:theme-factory`,
  `example-skills:brand-guidelines`, `example-skills:frontend-design`, `design-html`
