---
description: |
  Turn the navigable UI mocks into a runnable React frontend — decompose the screens against the
  active design system using Atomic Design (tokens -> atoms -> molecules -> organisms -> templates ->
  pages), generate TypeScript React components styled by the design tokens (CSS Modules + CSS
  variables), wire the story flow with react-router, and register every component in Storybook with a
  story per variant/state. Emits a self-contained, installable scaffold under generated/frontend/.
  /product:generate-frontend [--design-system=<name>] [--out=<path>] [--auto] [--lang=ja|en].
model: sonnet
user_invocable: true
---

# Frontend Code Generation (React + Storybook)

## Desired Outcome

Produce one deliverable: a runnable React + TypeScript frontend scaffold under
**`generated/frontend/`** that an engineer can `npm install && npm run storybook` (or
`npm run dev`) without further wiring. It is the **implementation** of the UI mocks — the mocks show
*what each screen does and in what order*, the design system supplies *the visual language*, and this
skill turns both into reusable, story-backed React components organized by **Atomic Design**.

1. **Atomic-Design component library** — `generated/frontend/src/components/` split into
   `atoms/`, `molecules/`, `organisms/`, `templates/`:
   - Each `CMP-` from the design system's `components.md` becomes a component at the right atomic
     level (primitives → atoms; composed → molecules/organisms; page layouts → templates).
   - Per component: `Component.tsx` (typed props from the component's variants/states),
     `Component.module.css` (styling that references **design tokens only**, never raw values), and
     `Component.stories.tsx`.
2. **Pages + routing** — `src/pages/` (one page per UI-mock screen) and `src/app/router.tsx`:
   - Each `{STORY}-NN-{slug}.html` mock → a `Page` component composed from templates/organisms.
   - The story flow (`next`/`prev`) is wired with **react-router**, so the click-through path of the
     mock becomes real navigation; a missing step renders a disabled `TBD` route, never a dead end.
3. **Token theme** — `src/styles/tokens.css` (copied from the active design system's `tokens.css`)
   loaded globally and injected into Storybook via a `preview` decorator, so app and stories share
   one visual language.
4. **Storybook registration** — `.storybook/{main.ts,preview.ts}` plus a `*.stories.tsx` per
   component, with one story per **variant/state** declared in `components.md` (args/controls
   derived from the props). Pages also get a story.
5. **Runnable scaffold** — `package.json`, `vite.config.ts`, `tsconfig.json`, and an `index.html`
   entry, pinned to a coherent React 18 + Vite + Storybook 8 + TypeScript toolchain.

## Invocation

```
/product:generate-frontend [--design-system=<name>] [--out=<path>] [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--design-system=<name>` | Optional | Override the active design system. Default: `options.design_system` from the progress file. |
| `--out=<path>` | Optional | Output root. Default `generated/frontend/`. |
| `--auto` | Optional | Generate without elicitation; resolve every ambiguity with the best-justified default and log it. |
| `--lang` | Optional | Override output language (UI copy / comments). Code identifiers stay English. |

## Decision Criteria

- **Atomic Design is the decomposition, the design system is the source of parts.** Map each `CMP-`
  to exactly one atomic level (atom/molecule/organism) and each UI-mock screen to a template + page.
  Do not invent components that have no `CMP-` or screen origin; if a screen needs a part the design
  system lacks, generate it at the inferred level and flag it `TBD` with an Open Question.
- **Tokens only, never raw values.** Every `*.module.css` references `var(--token-*)` from
  `tokens.css`. A hard-coded color/space/type value is a defect. No active design system → copy the
  ad-hoc lo-fi styling from the mocks and note that no token theme was applied.
- **The mock's click path becomes routing.** Page routes and their `next`/`prev` links follow the
  story order encoded in the mock file names (`{STORY}-NN-{slug}.html`). A gap in the story is a
  disabled/`TBD` route, never a dead end — mirroring the mock's navigability contract.
- **Every component is story-backed.** Each component has a `*.stories.tsx` with one story per
  variant/state from `components.md`; props/controls are typed. A component without a story is
  incomplete.
- **The scaffold must actually run.** Dependency versions are mutually compatible and pinned; the
  generated `package.json` scripts (`dev`, `build`, `storybook`, `build-storybook`, `typecheck`)
  exist and are correct. Prefer a small, coherent toolchain over feature breadth.
- **Trace every component** to its `CMP-`/`TOK-` and every page to its `STORY-`/screen.
- **Stop condition**: every `CMP-` has a typed React component + a story covering its variants/states;
  every UI-mock screen has a page + a route in `router.tsx` + a story; `tokens.css` is wired globally
  and into Storybook's preview; `package.json`/`tsconfig`/`vite.config`/`.storybook` exist; the
  scaffold typechecks against the generated sources (logically verified); traceability is appended.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/02_spec/ui-mocks/` | Required | `/product:generate-ui-mock` | stop and report — there are no screens to implement |
| `design-system/{active}/tokens.css` + `components.md` | Recommended | `/product:design-system` | proceed with atoms inferred from the mocks and ad-hoc CSS; note no token theme/components were available |
| `reports/02_spec/feature-list.md` | Recommended | `/product:define-features` | proceed; derive screen actions from the mocks directly, note the thinner basis |
| `work/traceability.json` | Recommended | `/product:init-output` | proceed; create page/component nodes without upstream edges and note it |

## Process

1. **Read context** — UI mocks (`reports/02_spec/ui-mocks/*.html` + the per-story `*-index.html`),
   the active design system (`options.design_system` → `design-system/{name}/tokens.css`,
   `components.md`, `manifest.json`), `feature-list.md`, and `work/traceability.json`. Apply
   `@rules/product/atomic-react-storybook.md`.
2. **Classify components (Atomic Design)** — for each `CMP-` decide atom/molecule/organism from its
   composition; for each UI-mock screen decide its template (layout) and page. Record the mapping
   table (`CMP-`/screen → atomic level → file path).
3. **Resolve the token theme** — copy the active `tokens.css` to `src/styles/tokens.css`; build the
   list of available `var(--token-*)`. No system → fall back to mock-derived ad-hoc CSS (noted).
4. **Generate atoms → molecules → organisms** — for each, write `Component.tsx` (props typed from
   variants/states), `Component.module.css` (token-referencing), composing lower levels upward.
5. **Generate templates & pages** — turn each screen layout into a template (data-less) and each
   screen into a page (template + organisms + screen actions from `feature-list.md`).
6. **Wire routing** — generate `src/app/router.tsx` (react-router) following the story order from the
   mock file names; render missing steps as disabled/`TBD` routes; add `next`/`prev` navigation.
7. **Write Storybook** — `.storybook/main.ts` + `.storybook/preview.ts` (import `tokens.css`, apply a
   theme decorator); one `*.stories.tsx` per component (a story per variant/state) and per page.
8. **Emit the scaffold** — `package.json` (pinned React 18 + Vite + Storybook 8 + TS, with `dev`,
   `build`, `storybook`, `build-storybook`, `typecheck` scripts), `vite.config.ts`, `tsconfig.json`,
   `index.html`, `src/main.tsx`, `src/App.tsx`.
9. **Verify** — logically check that every `CMP-`/screen produced a component/page + story, imports
   resolve, props/stories are consistent, and no `*.module.css` uses a raw value. List any `TBD`.
10. **Append traceability** — add component nodes (Upstream `CMP-`/`TOK-`) and page nodes (Upstream
    `STORY-`/screen, with `next`/`prev` route edges) to `work/traceability.json`.
11. **Record** — write all files; append the component-mapping decisions and every `TBD` to
    `work/context.md`.

## Output

`generated/frontend/` — a runnable React + TypeScript + Vite + Storybook scaffold:
`src/components/{atoms,molecules,organisms,templates}/`, `src/pages/`, `src/app/router.tsx`,
`src/styles/tokens.css`, `.storybook/`, `package.json`, `vite.config.ts`, `tsconfig.json`. Each
component/page carries a `*.stories.tsx`; styling references design tokens only; routing mirrors the
mock's story flow. Code identifiers stay English; UI copy/comments use `options.output_language`.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/atomic-react-storybook.md` | CMP-↔Atomic-level mapping, token→CSS-variable wiring, React/Storybook conventions, routing-from-flow rule |
| `@rules/product/design-system.md` | Token/component layered model the decomposition reads from |
| `@rules/product/ui-to-domain.md` | How screens/flow were derived (upstream context) |

Generation engines you may delegate to: `example-skills:frontend-design`,
`example-skills:web-artifacts-builder`, `mcp__magic__21st_magic_component_builder`.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:generate-ui-mock` | Upstream — its screens/flow become pages + routing |
| `/product:design-system` | Upstream — its `tokens.css`/`CMP-` become the theme + components |
| `/product:define-features` | Upstream — screen actions become page handlers |
| `/product:adapt-change` | Re-runs this skill when the mocks or design system change |
