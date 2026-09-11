# Existing UI Analysis

Applies whenever a skill **reads the user interface of an existing system**: `/architect:analyze-ui`
above all, plus the skills that consume its inventory — `/architect:evaluate-ux`, `/architect:analyze`,
`/architect:define-requirements` and `/architect:integrate-evaluations`.

The UI of a legacy system is the one place where its functions, its data and its rules are all
visible at once: a screen shows what a user can do, what they must type, what they get back, who is
allowed to see it — and, in most legacy code, a share of the business rules that never made it into
the domain layer. An analysis that reads only the backend misses all of that. The inventory below
exists to make it a checked fact rather than an impression.

## 1. What counts

| Element | Counts when | Does not count |
|---------|-------------|----------------|
| **Screen** (`UIS-`) | A distinct view a user navigates to and acts on: a page, a routed SPA view, a modal or wizard step **that carries its own inputs or actions** | A fragment or include rendered into a host page (it belongs to the host); an AJAX partial; a redirect-only endpoint; an error page with no action |
| **Component** (`UIC-`) | A reusable UI part: an include (`.jspf`, `th:fragment`, partial), a tag file or custom tag, a framework component, a shared CSS class that defines a visual element, **and a one-off inline-styled element that duplicates one of these** (recorded so the duplication is visible) | Layout boilerplate with no visual or behavioural identity (`<div class="row">`) |
| **Feature** (`UIF-`) | A user-visible capability: one or more submit/AJAX actions that carry the same command (`PlaceOrder`), across however many screens it takes | Pure navigation (`link` actions) — navigation is structure, not a feature |
| **Embedded logic** | A business rule, calculation, authorization decision or workflow step implemented **in the view layer** (scriptlet, template expression, client-side script) | Formatting that has no business meaning (date display format, pagination arithmetic) — record it only as `formatting` when the same format is a stated business rule |
| **Design token** | A raw visual value the UI uses: color, font family / size / weight, spacing, radius, shadow | Values inside vendored third-party CSS (a UI framework's own stylesheet) — record the framework in `technologies` instead |

**Every screen is counted — no sampling.** A UI of 300 screens yields 300 `UIS-` entries. A
screen the analysis could not resolve is listed under `coverage.unresolved` with the reason, never
dropped silently.

## 2. Detection by technology

Detect the UI technology from build files and file extensions first, then read routes before
templates: the route map is what decides which templates are screens.

| Technology | Screen sources | Route sources | Component sources | Style sources |
|------------|----------------|---------------|-------------------|---------------|
| JSP / Servlet | `**/*.jsp` | `web.xml` `<servlet-mapping>`, `@WebServlet`, forward/redirect targets in servlets | `**/*.jspf`, `WEB-INF/tags/**/*.tag`, TLDs | `**/*.css`, inline `style=` |
| Struts 1/2 | `**/*.jsp` | `struts-config.xml` / `struts.xml` action mappings and forwards | tiles definitions, tags | as JSP |
| JSF | `**/*.xhtml` | `faces-config.xml` navigation rules, implicit outcomes | composite components, `ui:include` | as JSP |
| Spring MVC + Thymeleaf | `templates/**/*.html` | `@Controller` / `@RequestMapping` return values | `th:fragment`, `th:replace` | as JSP |
| Rails ERB / Laravel Blade / ASP.NET Razor | `app/views/**/*.erb`, `resources/views/**/*.blade.php`, `Views/**/*.cshtml` | `routes.rb`, `routes/web.php`, controller conventions / `[Route]` | partials, `@component`, partial views / tag helpers | as JSP |
| React / Vue / Angular SPA | route-bound components | `react-router` config, `vue-router` routes, Angular `Routes` | `*.jsx`/`*.tsx`, `*.vue`, `*.component.ts` + template | CSS/SCSS modules, CSS-in-JS, Tailwind config, theme objects |

Client-side scripts (`**/*.js`, jQuery handlers, inline `<script>`) are read for three things:
validation (§3 input `validation`), embedded logic, and AJAX calls (actions of kind `ajax`).

## 3. The inventory

`reports/before/{project}/ui-inventory.json` is the canonical model; every Markdown the skill
writes is a projection of it. All `source` values are `path`, `path:line` or `path:start-end`,
relative to `target_path`.

### Screen

| Field | Meaning |
|-------|---------|
| `id`, `name` | `UIS-###`; the title a user sees |
| `route` | The URL pattern (`/order/entry`) or router path; `null` only with `route_unresolved` stating why |
| `source` | The template or component file that renders it |
| `entry` | `true` for a screen a user reaches without navigating from another screen (login, landing, home). Navigation depth is measured from these (§6) |
| `handlers` | `[{ref, source}]` — the controller/servlet/action method that serves it |
| `access` | `{authentication: required\|none, roles: [...], guards: [{kind: view\|controller\|filter\|config\|route, source}]}` — a role check that exists **only** as `kind: view` is a finding for `investigate-security`, and is recorded exactly as found |
| `inputs` | See Input |
| `outputs` | `[{name, label, kind: field\|table\|list\|message\|image\|chart\|download\|other, fields, source}]` — what the screen shows |
| `actions` | See Action |
| `messages` | `[{kind: error\|warning\|info\|success, text, source}]` — verbatim text a user can see |
| `components` | `UIC-` ids the screen uses |
| `embedded_logic` | `[{kind: calculation\|validation\|authorization\|workflow\|formatting\|data-access\|other, description, should_live_in: domain\|application\|presentation, source}]` |
| `lang` | The document language (`ja`), `null` when the page declares none |
| `images` | `[{src, alt, decorative, source}]` — `alt` is the attribute value or `null` when absent |
| `color_pairs` | `[{fg, bg, text: normal\|large, where, source}]` — hex foreground/background pairs the CSS applies to text, for the contrast check |

### Input

`{name, label, label_association, control, type, required, validation, prefilled_from, redundant_with, source}`

- `label` is the text a user sees (resource-bundle keys resolved), `null` when there is none.
- `label_association` is how the label is tied to the control: `for` (`<label for>`), `wrapping`
  (the input inside the label), `aria` (`aria-label` / `aria-labelledby`), `placeholder-only`, or
  `none`. Visible text next to an input that is not associated is `none`.
- `control` — `text | password | email | number | tel | date | select | radio | checkbox | textarea | file | hidden | other`.
- `type` — the data type: `string | integer | decimal | date | boolean | enum | file | other`.
- `validation` — `[{rule: required|min|max|minLength|maxLength|pattern|enum|format|custom, value, where: client|server|both, source}]`.
  `where` is what the code shows: a rule enforced only by a jQuery handler is `client`, and that is a
  finding in its own right (the server accepts what the rule forbids).
- `prefilled_from` — what the screen pre-populates it with (`session user email`), or `null`.
- `redundant_with` — the place the system already holds this value when the screen asks for it
  again without pre-filling (`logged-in user's email`), or `null`.

The vocabulary is the one `@rules/product/ui-to-domain.md` uses for generated mocks — **form fields
→ attributes, user action → Command, action result → state / event** — so an as-is inventory and a
to-be mock can be compared field by field.

### Action

`{id, label, command, kind, scope, method, endpoint, target, destructive, confirmation, unresolved, source}`

- `id` is `<screen id>.A<n>` (`UIS-006.A1`).
- `command` is the verb-first business command (`PlaceOrder`, `RemoveCartLine`), `null` for pure
  navigation. Two actions with the same command are the same capability, whatever their labels say.
- `kind` — `submit | link | button | ajax | other`; `scope` — `screen`, or `global` for chrome every
  screen inherits (header logout, footer links).
- `target` is the `UIS-` the action lands on; `endpoint` is `METHOD /path` when it calls one.
- `destructive` — it deletes, cancels or irreversibly changes something; `confirmation` — the UI asks
  before doing it (dialog, confirm step) or offers undo.

### Component

`{id, name, kind, level, source, variants, states, used_by, token_refs, duplicates, unused}`

- `kind` — `include | tag | fragment | component | macro | css-class | inline-style | other`.
- `level` — Atomic Design level (`atom | molecule | organism | template`), decided by whether the
  component contains other components — the same test `@rules/product/atomic-react-storybook.md` uses.
- `used_by` — the screens that use it; `unused: true` marks a declared component no screen uses.
- `token_refs` — dotted paths into the design-token file (`color.hex-0066cc`).
- `duplicates` — other `UIC-` that render the same element differently (the inline-styled button
  next to the button tag).

### Feature

`{id, name, command, actions, screens, actors, entities, handlers}`

`actions` are the `submit`/`ajax` actions that carry `command`; `screens` are exactly their screens,
in flow order; `actors` come from the screens' `access.roles`; `entities` are the backend entities
the handlers read or write, traced through the code (Serena `find_referencing_symbols`).

### Top level

`{schema_version: 1, project, target_path, ui_roots, technologies: [{name, evidence}], screens,
components, features, design_tokens, coverage: {template_files, screens, unresolved: [{ref, reason, oq}]}}`

`design_tokens` is the project-relative path of the token file (§5).

## 4. Well-formedness rules

An inventory is not written out until all nine hold. Each is mechanically checkable and each is
asserted by `tools/lib/ui_inventory.py` against the inventory the skill emits.

1. **Unique, well-formed ids** — `UIS-`, `UIC-` and `UIF-` ids are unique; every action id is
   `<its own screen id>.A<n>` and unique.
2. **Every screen has a name and a source**, and a route unless `route_unresolved` says why not.
3. **Every input and every accessibility fact is typed** — an input names its control, data type,
   label association and `required` (a boolean); every validation names its rule and where it runs;
   every image states `alt` (string or `null`); every color pair is two hex colors.
4. **Every action resolves** — to a declared target screen, to an endpoint, or it carries
   `unresolved` with the reason (and becomes an Open Question). A target that names no declared
   screen is a defect.
5. **Component references agree both ways** — every component a screen lists is declared, every
   component's `used_by` is exactly the set of screens that list it, and an unused component says
   `unused: true`.
6. **Every submit or AJAX action belongs to exactly one feature**, every feature cites at least one
   existing action, and its `screens` are the screens of its actions.
7. **Embedded logic is classified** — every item names its kind, where it should live, and its source.
8. **Every source is real** — it is `path[:line[-end]]`, the file exists under the target, and the line
   is within the file. An inventory that cites code nobody can open is a narrative, not evidence.
9. **The design-token file is valid DTCG** — it exists, every token has `$type` and `$value`, every
   alias resolves, every raw token carries its sources and a usage count, and every component
   `token_refs` entry resolves.

## 5. Design tokens

`reports/before/{project}/ui-design-tokens.json` is a **W3C DTCG** file — the format
`/product:design-system --import=<path>` already accepts (`@rules/product/design-system.md`), so the
as-is visual language can be incorporated without conversion.

- **One raw token per distinct value, named by the value** — `color.hex-0066cc`, `font.size.px-14`,
  `space.px-8`, `radius.px-4`. Near-identical values are **not** merged here: the as-is file must
  show the fragmentation, because the fragmentation is the finding.
- Each raw token carries `$extensions["nexus-architect"]`: `sources` (every place it is used,
  `path:line`), `usage_count`, and `cluster` — the name of the group of near-identical values it
  belongs to (`primary-blue`). A cluster with more than one member is a consolidation candidate.
- A `semantic` group holds **candidate** aliases (`semantic.color.primary` = `{color.hex-0066cc}`),
  each pointing at the most-used member of its cluster, with a `$description` saying it is a
  candidate. Semantic names follow `@rules/product/design-system.md` (`color.bg`, `color.fg`,
  `color.primary`, `color.danger`, …).
- Values from vendored third-party CSS are excluded (§1).

## 6. Navigation semantics

These definitions are what `tools/lib/ui_metrics.py` computes; the skill states them, it does not
re-derive them.

- **Transition** — an action with a `target`.
- **Depth** — the shortest number of transitions from any `entry` screen.
- **Orphan** — a non-entry screen no other screen transitions to.
- **Unreachable** — a screen with no path from any entry screen (orphans, and screens reachable
  only from orphans).
- **Dead end** — a screen whose only ways out are global actions that land on an entry screen
  (logging out) or that has no way out at all: the task ends with nowhere to go.

## 7. Stable ids

Re-running the analysis keeps ids. Before assigning, read the existing inventory: a screen whose
`route` and `source` match keeps its `UIS-`, a component whose `source` and `name` match keeps its
`UIC-`, a feature whose `command` matches keeps its `UIF-`. New elements take `max + 1` over the
inventory **and** over `work/traceability.json` for their prefix. A screen that no longer exists is
removed from the inventory and its traceability node is marked `status: "removed"` rather than
deleted, so downstream links do not dangle.

## 8. Large UIs

Extract screens in batches of about twenty per sub-agent, issued in one message, each batch
returning its screens as JSON in the §3 shape. The parent — never a sub-agent — assigns ids, merges
components that two batches both found, synthesizes features, and writes the inventory. Coverage is
complete or it is reported as incomplete: `coverage.screens` equals the number of screen entries,
and every template that is neither a screen nor a component is accounted for in
`coverage.unresolved`.

## 9. What downstream consumes

| Consumer | What it takes |
|----------|---------------|
| `/architect:evaluate-ux` | The whole inventory and the token file, through the metrics of `tools/lib/ui_metrics.py` |
| `/architect:analyze` | `access` → evidence for the actor/role/permission matrix; labels vs code names → ubiquitous-language synonyms; screens → the screen column of the domain-code mapping |
| `/architect:define-requirements` | `UIF-` as the upstream of legacy `FR-`s; validation rules as acceptance-criteria candidates |
| `/architect:integrate-evaluations` | The UX evaluation built on it |
| `/product:design-system --import` | `ui-design-tokens.json`, as-is |

**The view layer is evidence, not the design.** Embedded logic found here is recorded where it is,
and the redesign moves it to where `should_live_in` says it belongs — the inventory never presents a
rule enforced only in a template as a rule the system enforces.
