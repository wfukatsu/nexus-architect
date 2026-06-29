# Rules: Atomic Design → React → Storybook (generate-frontend)

Reference for turning the navigable UI mocks and the active design system into a runnable React +
TypeScript frontend, decomposed with **Atomic Design** and registered in **Storybook**. The mocks
are the concrete screens and flow; the design system is the visual language and parts inventory; this
layer is the *implementation* — each component traces to a `CMP-`/`TOK-`, each page to a
`STORY-`/screen.

## Atomic Design ↔ source mapping

The design system already declares a layered model (tokens → primitives → components → patterns →
guidelines). Map it to Atomic Design like this:

| Atomic Design level | Source | Examples |
|---------------------|--------|----------|
| **Design Tokens** (foundation) | `design-system/{name}/tokens.css` (`TOK-`) | color / space / type / radius / elevation |
| **Atoms** | primitive / single-purpose `CMP-` | Button, Input, Text, Icon, Badge, Label |
| **Molecules** | `CMP-` composed of atoms + simple patterns | FormField (Label+Input+Error), SearchBar, Card |
| **Organisms** | patterns / composed sections | NavBar, DataTable, Form, Modal, Header |
| **Templates** | a UI-mock screen's layout, **data-less** | DashboardLayout, DetailLayout |
| **Pages** | a UI-mock screen `{STORY}-NN-{slug}.html` | template + organisms + real/sample data |

**Classification rule:** a `CMP-` is an **atom** if it has no other `CMP-` inside it; a **molecule**
if it composes only atoms; an **organism** if it composes molecules/atoms into a standalone section.
When a screen needs a part the design system does not declare, generate it at the inferred level and
flag it `TBD` with an Open Question — do not silently invent design-system parts.

## Tokens → styling (CSS Modules + CSS variables)

- Copy the active `tokens.css` to `src/styles/tokens.css` and import it once globally (`main.tsx`)
  **and** in `.storybook/preview.ts`, so app and stories share one theme.
- Every `*.module.css` references tokens via `var(--token-*)`. **A raw color/space/type value is a
  defect.** Map design-system semantic aliases (`--color-primary`, `--space-2`, …) straight through.
- **Structural values not governed by any token are allowed** — e.g. a `1px` hairline border width, a
  container `max-width`, `margin: 0 auto`, `100vh` — when the design system declares no token for that
  concept. Prefer a token when one exists; if a recurring structural value clearly wants one (a shared
  border width or container width), add it as an Open Question for the design system rather than
  scattering the literal. Colors, font sizes, and spacing must always be tokens.
- At **mid** design-system fidelity, port the `CMP-` component CSS classes from `components.md` into
  the component's `*.module.css`; at **lo**, style from tokens only.
- No active design system → copy the mock's ad-hoc inline CSS into modules and note that no token
  theme was applied (no fabricated palette).

## Component generation (React + TypeScript)

- One directory per component: `Component.tsx`, `Component.module.css`, `Component.stories.tsx`,
  optional `index.ts` re-export.
- **Props are typed from the component's variants/states** in `components.md`: each variant → a prop
  union (`variant: 'primary' | 'secondary'`), each state → a boolean/enum (`disabled`, `loading`).
- Components compose **upward only** (a molecule imports atoms; an organism imports molecules/atoms).
  No level imports a higher level. Keep components presentational; page-level state lives in pages.
- Identifiers (component names, props, files) are **English**; only user-facing copy and comments use
  `options.output_language`.

## Pages & routing (react-router, from the mock flow)

- Each UI-mock screen → one `src/pages/{Story}/{NN}-{slug}.tsx` page, composed from templates +
  organisms; screen actions come from `feature-list.md` (`FEAT-`) as handlers/`<Link>`s.
- `src/app/router.tsx` defines routes in the **story order encoded in the mock file names**
  (`{STORY}-NN-{slug}`); the `next`/`prev` links from the mock become `<Link>` navigation.
- A story step missing from the mocks renders as a **disabled `TBD` route** (a stub page noting the
  gap), never a dead end — mirroring the mock's navigability contract. Branches link to their target
  pages.
- A per-story entry route mirrors the mock's `{STORY}-index.html`.

## Storybook registration

- `.storybook/main.ts`: Vite builder, `stories: ['../src/**/*.stories.@(tsx|mdx)']`, the React
  framework addon, essentials.
- `.storybook/preview.ts`: import `../src/styles/tokens.css`; add a decorator that applies the theme
  wrapper so every story renders with tokens.
- **One story file per component**, with **one story per variant/state** from `components.md`
  (`Primary`, `Secondary`, `Disabled`, `Loading`, …); use `argTypes`/`args` so controls are typed.
  Pages also get a story (rendered inside a router decorator).
- Group stories by atomic level via the `title` (`Atoms/Button`, `Molecules/FormField`,
  `Organisms/NavBar`, `Pages/{Story}/{Screen}`).

## Scaffold (runnable, pinned)

- Toolchain: **React 18 + Vite + TypeScript + Storybook 8** — versions mutually compatible and
  pinned. `package.json` scripts: `dev`, `build`, `preview`, `storybook`, `build-storybook`,
  `typecheck`.
- Files: `package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`, `src/main.tsx`,
  `src/App.tsx` (mounts the router), `src/styles/tokens.css`.
- The skill **emits source**; it does not run `npm install`. Verification is logical: imports
  resolve, every `CMP-`/screen produced a component/page + story, props↔stories are consistent, and
  no module CSS uses raw values.

## ID convention & traceability

- `COMP-` for a React component, `PAGE-` for a page. Append to `work/traceability.json` with Upstream
  references: components → `CMP-`/`TOK-`; pages → `STORY-`/screen, plus `next`/`prev` route edges.
- Record the full `CMP-`/screen → atomic-level → file-path mapping table and every `TBD` in
  `work/context.md`.

## Sources

- Brad Frost — *Atomic Design* (atoms/molecules/organisms/templates/pages)
- W3C Design Tokens Community Group (DTCG) — token format the design system emits
- Storybook Component Story Format (CSF 3) — `*.stories.tsx` structure
