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
| **Screen** (`UIS-`) | A view a user lands on: a routed page, a template reachable directly by URL, a routed SPA view, a modal or wizard step with its own inputs or actions. A landing page with nothing to do on it (an order-complete page) **is** a screen — that is how a dead end becomes visible | A fragment or include rendered into a host page (it belongs to the host); an AJAX partial; a redirect-only endpoint (`/logout`); the container's default error page |
| **Component** (`UIC-`) | A reusable UI part: an include (`.jspf`, `th:fragment`, partial), a tag file or custom tag, a framework component, a CSS class that defines a visual element (color, border, background or typography) **and is used on two or more screens** — and a hand-built duplicate of one of these (§3 Component) | Layout boilerplate with no visual or behavioural identity (`<div class="row">`); a class used on one screen only |
| **Feature** (`UIF-`) | A capability: every action that carries the same verb-first command (`PlaceOrder`), across however many screens it appears on | Pure navigation — an action with no command |
| **Task** | A user goal walked across screens: the ordered path a user takes and the features they use on it (checkout = cart → entry → confirm → complete) | — (every feature belongs to at least one task; a one-screen feature is a one-screen task) |
| **Embedded logic** | A business rule, calculation, authorization decision or workflow step implemented **in the view layer** (scriptlet, template expression, client-side script) | Formatting with no business meaning (a date display format, pager arithmetic) |
| **Design token** | A raw visual value the UI uses: color, font family / size / weight, spacing, radius, border width, shadow | Values inside vendored third-party CSS (record the framework in `technologies`); layout sizes (widths, heights); zero, `inherit`, `transparent` |

**Every screen is counted — no sampling.** A UI of 300 screens yields 300 `UIS-` entries. A
template that is neither a screen, a component nor included anywhere is listed under
`coverage.unresolved` with the reason, never dropped silently.

## 2. Detection by technology

Detect the UI technology from build files and file extensions first, then read routes before
templates: the route map is what decides which templates are screens.

| Technology | Screen sources | Route sources | Component sources | Style sources |
|------------|----------------|---------------|-------------------|---------------|
| JSP / Servlet | `**/*.jsp` | `web.xml` `<servlet-mapping>`, `@WebServlet`, forward/redirect targets in servlets; a JSP outside `WEB-INF` is reachable by URL | `**/*.jspf`, `WEB-INF/tags/**/*.tag`, TLDs | `**/*.css`, inline `style=` |
| Struts 1/2 | `**/*.jsp` | `struts-config.xml` / `struts.xml` action mappings and forwards | tiles definitions, tags | as JSP |
| JSF | `**/*.xhtml` | `faces-config.xml` navigation rules, implicit outcomes | composite components, `ui:include` | as JSP |
| Spring MVC + Thymeleaf | `templates/**/*.html` | `@Controller` / `@RequestMapping` return values | `th:fragment`, `th:replace` | as JSP |
| Rails ERB / Laravel Blade / ASP.NET Razor | `app/views/**/*.erb`, `resources/views/**/*.blade.php`, `Views/**/*.cshtml` | `routes.rb`, `routes/web.php`, controller conventions / `[Route]` | partials, `@component`, partial views / tag helpers | as JSP |
| React / Vue / Angular SPA | route-bound components | `react-router` config, `vue-router` routes, Angular `Routes` | `*.jsx`/`*.tsx`, `*.vue`, `*.component.ts` + template | CSS/SCSS modules, CSS-in-JS, Tailwind config, theme objects |

Client-side scripts (`**/*.js`, jQuery handlers, inline `<script>`) are read for three things:
validation, embedded logic, and AJAX calls.

## 3. The inventory

`reports/before/{project}/ui-inventory.json` is the canonical model; every Markdown the skill
writes is a projection of it. Every `source` is `path`, `path:line` or `path:start-end`, relative to
`target_path` — and every element below that says `source` has one.

### Screen

| Field | Meaning |
|-------|---------|
| `id`, `name` | `UIS-###`; the title a user sees |
| `route` | The URL path (`/order/entry`, no query string) or router path; `null` only with `route_unresolved` stating why |
| `source` | The template or component file that renders it |
| `entry` | `true` for a screen a user reaches without navigating from another screen **and without being authenticated first**: the login page, a public landing page. A home page reached only after logging in is not an entry — it is one transition away from the login. At least one screen is an entry |
| `handlers` | `[{ref, source, services, entities}]` — the controller/servlet/action that serves the screen, the services it calls and the entities it reads or writes (for the screen-to-code map) |
| `access` | `{authentication: required\|none, roles, guards}`. `roles` is never empty: the roles allowed to see the screen — every role the system defines when the screen is authenticated but checks no role, `["anonymous"]` when it needs no authentication. `guards` are the checks that protect the **whole screen**: `[{kind: view\|controller\|filter\|config\|route, source}]`. A guard that exists only as `kind: view` is a finding for `investigate-security` and is recorded exactly as found |
| `inputs` | See Input |
| `outputs` | `[{name, label, kind, fields, source}]` — what the screen shows. `kind`: `field` (values of one record shown as label/value pairs), `table` or `list` (rows), `message`, `image`, `chart`, `download`, `other`. `fields` lists the displayed field names |
| `actions` | See Action |
| `messages` | `[{kind: error\|warning\|info\|success, text, source}]` — verbatim text a user can see on this screen. `source` is where the text is authored: the resource-bundle line for bundle text, the template line for literal text, the handler line for text the handler passes in (including `sendError` messages shown on an error page) |
| `components` | `UIC-` ids the screen uses |
| `embedded_logic` | `[{kind: calculation\|validation\|authorization\|workflow\|formatting\|data-access\|other, description, should_live_in: domain\|application\|presentation, source}]` |
| `lang` | The document language (`ja`), `null` when the page declares none |
| `images` | `[{src, alt, decorative, source}]` — `alt` is the attribute value, `null` when the attribute is absent; `decorative` is a boolean |
| `color_pairs` | `[{fg, bg, text: normal\|large, where, source}]` — for text whose color (declared or inherited) sits on a declared background: the 6-digit lowercase hex pair, and `large` for WCAG large text (≥ 24 px, or ≥ 18.66 px bold). Shared chrome's pairs are recorded on every screen that includes it — they are part of what the user sees there |

Chrome **actions** (header logout, footer links) are recorded on every screen that includes the
chrome, with `scope: global`; chrome **outputs** (the logged-in user's name) belong to the component,
not to each screen.

### Input

`{name, label, label_association, control, type, required, validation, prefilled_from, redundant_with, source}`

- `label` — the text a user sees for the field, resource-bundle keys resolved; the placeholder text
  when the placeholder is all there is; `null` when there is nothing. Decorations inside the label
  (a "required" badge) are not part of it — `required` records them.
- `label_association` — how the label is tied to the control: `for` (`<label for>`), `wrapping`
  (the input inside the label), `aria` (`aria-label` / `aria-labelledby`), `legend` (a radio or
  checkbox group inside a `<fieldset>` with a `<legend>`), `placeholder-only`, or `none` — visible
  text next to an input that nothing associates is `none`. `n/a` only for `hidden` controls.
- `control` — `text | password | email | number | tel | date | select | radio | checkbox | textarea | file | hidden | other`.
- `type` — the data type: `string | integer | decimal | date | boolean | enum | file | other`.
- `validation` — `[{rule: required|min|max|minLength|maxLength|pattern|enum|format|custom, value, where: client|server|both, enforcement, source, client_source}]`.
  `where` is what the code shows: a rule enforced only by a script is `client`, and that is a finding
  in its own right. `source` cites the enforcing check — the server's when `where` is `server` or
  `both` — and `client_source` cites the client check when `where` is `both`. `enforcement` is
  `reject` (the default), `clamp` (the server silently corrects the value) or `ignore`.
- `prefilled_from` — the system-held data or default the screen pre-populates it with (`session
  user's e-mail`), or `null`. Re-displaying what the user just submitted is not pre-filling.
- `redundant_with` — where the system already holds this value when the screen asks for it again
  without pre-filling (`logged-in user's e-mail`), or `null`.
- Hidden inputs are recorded when they carry data the action depends on (an id, a token); a hidden
  field that only tells one button from another (`action=add`) is not an input.

The vocabulary is the one `@rules/product/ui-to-domain.md` uses for generated mocks — **form fields
→ attributes, user action → Command, action result → state / event** — so an as-is inventory and a
to-be mock can be compared field by field.

### Action

`{id, label, command, kind, scope, method, endpoint, target, inputs, guard, destructive, confirmation, unresolved, source}`

- `id` is `<screen id>.A<n>` (`UIS-006.A1`).
- `kind` is decided by **effect**, not by markup: `submit` sends data or changes state; `link`
  navigates without changing anything (a GET form that only moves to the next screen is a `link`);
  `ajax` calls an endpoint without leaving the screen; `button` acts on the page itself (toggle,
  print).
- `command` is the verb-first business command (`PlaceOrder`, `RemoveCartLine`, `SearchProducts`,
  `LogOut`). **Every `submit` and `ajax` action has one**, and so does any link that changes state
  (a `GET /logout` destroys the session). Pure navigation has `null`. Two actions with the same
  command are the same capability, whatever their labels say.
- `scope` — `screen`, or `global` for chrome every screen inherits.
- `endpoint` is `METHOD /path` the action calls. `target` is the `UIS-` the user **lands on**: after
  the handler's success path (its redirect or forward), not the URL the form posts to. A redirect
  through a non-screen route (`/logout` → `/login`) is followed to the screen. A re-render on a
  validation failure is not a transition.
- `inputs` — for `submit` and `ajax`, the names of the screen's inputs the action sends (possibly
  none); two forms on one screen send different inputs.
- `guard` — `{kind, roles, source}` when a role check shows or hides **this action** only (an admin
  link on a shared menu). A check that protects the whole screen is an `access.guards` entry.
- `destructive` — it deletes, cancels or irreversibly discards something the user would lose,
  including a session cart discarded by logging out. `confirmation` — the UI asks before doing it
  (dialog, confirm step, undo). A submit on a review screen that shows exactly what will happen is
  confirmed by that screen.
- `unresolved` — why neither a target nor an endpoint could be determined: the **path** is built at
  runtime (a query string built at runtime does not count).

### Component

`{id, name, kind, level, source, variants, states, used_by, token_refs, duplicates, unused}`

- `kind` — `include | tag | fragment | component | macro | css-class | inline-style | copy | other`.
  `inline-style` is an element rebuilt with inline styles instead of the shared component (the
  inline-styled save button next to the button tag); `copy` is a hand-copied duplicate of a shared
  component's markup (a title bar pasted into a page that does not include the header).
- `level` — Atomic Design level (`atom | molecule | organism | template`): an include that opens or
  closes the page structure (header, footer, layout) is a `template`; otherwise decide by whether it
  contains other components, the test `@rules/product/atomic-react-storybook.md` uses.
- `used_by` — the screens that use it (for a class a script injects, the screens whose scripts
  inject it); `unused: true` marks a declared component no screen uses.
- `token_refs` — dotted paths into the design-token file (`color.hex-0066cc`).
- `duplicates` — for `inline-style` and `copy` components, the component they rebuild.

### Feature

`{id, name, command, actions, screens, actors, entities, entity_operations, handlers}`

`actions` are every action that carries `command`; `screens` are exactly their screens; `actors` are
the union of their screens' `access.roles` (so an unauthenticated feature's actor is `anonymous`);
`entities` are the entities the handlers read or write, and `entity_operations` maps each to the
operations the feature performs on it (`{"Order": "C", "Cart": "RU"}`, letters from `CRUD`).

### Task

`{name, goal, features, screens}` — `screens` is the ordered path a user walks, each screen reached
from the previous one by a declared transition; `features` are the features used along it. Tasks are
the unit of efficiency: `ui_metrics.py` counts a task's screens as its steps and adds up the inputs
its features' actions send.

### Top level

`{schema_version: 1, project, target_path, ui_roots, technologies: [{name, evidence}], screens,
components, features, tasks, design_tokens, coverage: {template_files, screens, unresolved: [{ref,
reason, oq}]}}`

`design_tokens` is the project-relative path of the token file (§5). `coverage.template_files` is
the number of templates examined; every `unresolved` item cites the Open Question it became.

## 4. Well-formedness rules

An inventory is not written out until all ten hold. Each is mechanically checkable and each is
asserted by `tools/lib/ui_inventory.py` against the inventory the skill emits.

1. **Unique, well-formed ids** — `UIS-`, `UIC-` and `UIF-` ids are unique; every action id is
   `<its own screen id>.A<n>` and unique; task names are unique.
2. **Every screen has a name, a source, an access block with at least one role**, and a route unless
   `route_unresolved` says why not; **at least one screen is an entry**.
3. **Every input and every accessibility fact is typed** — an input names its control, data type,
   label association and `required`; every validation names its rule and where it runs, and a rule
   enforced on both sides cites both; every image states `alt` and `decorative`; every color pair is
   two 6-digit lowercase hex colors.
4. **Every action resolves** — to a declared target screen, to an endpoint, or it carries
   `unresolved` with the reason; the inputs it sends exist on its screen; its guard, if any, is typed.
5. **Component references agree both ways** — every component a screen lists is declared, every
   component's `used_by` is exactly the set of screens that list it, an unused component says
   `unused: true`, and a duplicate names another declared component.
6. **Commands and features agree** — every `submit` and `ajax` action has a command; every action
   with a command belongs to exactly one feature; a feature's command is its actions' command, no two
   features share one, its `screens` are its actions' screens, and it names its actors.
7. **Embedded logic is classified** — every item names its kind, where it should live, and its source.
8. **Every source is real** — it is `path[:line[-end]]`, the file exists under the target, and the
   line is within the file. An inventory that cites code nobody can open is a narrative, not evidence.
9. **The design-token file is valid DTCG** — it exists, every token has `$type` and `$value`, colors
   are 6-digit lowercase hex, every alias resolves, every raw token carries its sources and a usage
   count, and every component `token_refs` entry resolves.
10. **Every feature is used in a walkable task** — every task's screens are declared and each is
    reached from the previous one by a declared transition, each of its features has an action on
    its path, and every feature appears in at least one task.

## 5. Design tokens

`reports/before/{project}/ui-design-tokens.json` is a **W3C DTCG** file — the format
`/product:design-system --import=<path>` accepts (`@rules/product/design-system.md`), so the as-is
visual language can be incorporated without conversion.

- **One raw token per distinct value, named by the value** — `color.hex-0066cc`, `font.size.px-14`,
  `font.weight.w-700`, `font.family.<first family, lowercased, non-alphanumerics as ->`, `space.px-8`,
  `radius.px-4`, `border.width.px-1`, `shadow.<slug>`. Near-identical values are **not** merged here:
  the as-is file must show the fragmentation, because the fragmentation is the finding.
- **Normalize** colors to 6-digit lowercase hex (`#06c`, `rgb()` and named colors alike), sizes to
  px, `bold` to 700 and `normal` to 400. Zero, `inherit`, `transparent` and layout sizes are not
  tokens.
- Each raw token carries `$extensions["nexus-architect"]`: `sources` (every place it is used,
  `path:line`), `usage_count` (the number of declarations that use it — two on one line count two),
  and `cluster` — the group of near-identical values that play the same role.
- **Clusters** are decided by role first and closeness second: colors used for the same purpose
  (the primary action, body text, borders, surfaces) within about 48 in RGB distance; font sizes
  within 2 px for the same text role (button text at 13 and 14 px); spacing within 2 px for the same
  purpose. A hover or active shade is its own role. A cluster with more than one member is a
  consolidation candidate.
- A `semantic` group holds **candidate** aliases, `semantic.color.<role>` = `{color.hex-…}`, each
  pointing at the most-used member of its cluster (ties: the member a shared component uses, then
  the lexically first), with a `$description` saying it is a candidate. Role names follow
  `@rules/product/design-system.md` where they fit (`semantic.color.bg`, `.fg`, `.primary`,
  `.danger`).
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
- **Task steps** — the number of screens on a task's path.

## 7. Stable ids and traceability

Re-running the analysis keeps ids. Before assigning, read the existing inventory: a screen whose
`route` and `source` match keeps its `UIS-`, a component whose `source` and `name` match keeps its
`UIC-`, a feature whose `command` matches keeps its `UIF-`. New elements take `max + 1` over the
inventory **and** over `work/traceability.json` for their prefix.

Each screen, component and feature is a node in `work/traceability.json` (`type` `ui-screen`,
`ui-component`, `ui-feature`; `source_file` the inventory). `UIS-` and `UIC-` nodes are as-is facts
with an empty `upstream`; a `UIF-` node's upstream is its screens. A screen that no longer exists
keeps its node with `status: "removed"`, so downstream links do not dangle.

## 8. Large UIs

Extract screens in batches of about ten per sub-agent, issued in one message; each sub-agent writes
its screens to its own batch file and returns only a summary, so no single reply carries the whole
UI. The parent — never a sub-agent — assigns ids, merges components two batches both found,
synthesizes features and tasks, and writes the inventory. Coverage is complete or it is reported as
incomplete: `coverage.screens` equals the number of screen entries, and every template that is
neither a screen, a component nor included anywhere is accounted for in `coverage.unresolved`.

## 9. What downstream consumes

| Consumer | What it takes |
|----------|---------------|
| `/architect:evaluate-ux` | The whole inventory and the token file, through the metrics of `tools/lib/ui_metrics.py` |
| `/architect:analyze` | `access` and action `guard`s → evidence for the actor/role/permission matrix; labels vs code names → ubiquitous-language synonyms; screens and handlers → the screen column of the domain-code mapping |
| `/architect:define-requirements` | `UIF-` as the upstream of legacy `FR-`s; validation rules as acceptance-criteria candidates |
| `/architect:integrate-evaluations` | The UX evaluation built on it |
| `/product:design-system --import` | `ui-design-tokens.json`, as-is |

**The view layer is evidence, not the design.** Embedded logic found here is recorded where it is,
and the redesign moves it to where `should_live_in` says it belongs — the inventory never presents a
rule enforced only in a template as a rule the system enforces.
