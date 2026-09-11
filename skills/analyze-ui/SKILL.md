---
description: |
  Analyze the user interface of an existing system: every screen with what it asks for (inputs, validation), what it shows (outputs, messages), what it lets a user do (actions, transitions) and who may see it; the UI components; the features and user tasks the screens expose; business logic embedded in the view layer; and the design tokens the UI actually uses.
  /architect:analyze-ui [target_path] [--ui-root=<path>] [--auto] to invoke.
  Optional phase after investigate and before analyze; skipped when the system has no UI layer.
model: sonnet
user_invocable: true
---

# Existing UI Analysis

## Desired Outcome

A complete, source-cited model of the existing UI, and four views of it:

1. **UI inventory** — `ui-inventory.json`: every screen (`UIS-`), component (`UIC-`), feature
   (`UIF-`) and task, in the shape of @rules/ui-analysis.md §3. The canonical model; the views are
   projections of it.
2. **Design tokens** — `ui-design-tokens.json`: the colors, type, spacing, radius, borders and
   shadows the UI uses, as W3C DTCG with provenance and clusters, ready for
   `/product:design-system --import`.
3. **Screen catalog** — per screen, its INPUT (fields, controls, validation and where it runs),
   OUTPUT (displayed data, tables, messages), actions and where they land, access, and the code
   behind it; the transition diagram; the business logic found in the view layer.
4. **Features** — the capabilities the screens expose, the tasks users walk to use them, who uses
   them and what they touch.
5. **Components** — the reusable UI parts, their variants and states, where they are used, and
   where the same element was rebuilt by hand.
6. **Design-system extract** — the as-is visual language, its fragmentation, and the semantic token
   candidates for a consolidated design system.

## Decision Criteria

- **Read the route map before the templates.** Routes decide which templates are screens
  (@rules/ui-analysis.md §1–2). A template reachable by URL is a screen even when nothing links to
  it — that is how an orphan becomes visible; a template that is neither a screen, a component nor
  included anywhere goes to `coverage.unresolved`.
- **Every screen, no sampling.** Three hundred screens yield three hundred entries, extracted in
  batches (§8 of the rule). Coverage is reported, never implied.
- **Record what the code does, not what it should do.** A rule enforced only by a script is
  `where: client`; a role check that exists only in a JSP is a `view` guard; a discount computed in a
  scriptlet is embedded logic. These are findings, and the inventory is where they are first
  visible.
- **Cite everything.** Every input, validation, action, message, guard, image, color pair and token
  carries a `source` into the target code.
- **Use the ui-to-domain vocabulary** — form fields → attributes, user action → a verb-first
  Command, action result → state or event (@rules/product/ui-to-domain.md) — so the as-is inventory
  and any to-be mock can be compared field by field.
- **Keep the fragmentation.** Near-identical values are separate raw tokens grouped by `cluster`;
  merging them here would erase the finding (@rules/ui-analysis.md §5).

## Prerequisites

| Input | Required/Recommended | Source | If missing |
|-------|---------------------|--------|------------|
| target_path (argument) | Required | User, or `target_path` in `work/pipeline-progress.json` | Ask for it; stop if it is not a directory |
| `reports/before/{project}/technology-stack.md`, `codebase-structure.md` | Recommended | `/architect:investigate` (it precedes this phase in a pipeline run) | Detect the UI technology from build files and extensions yourself (Step 2) |
| `reports/before/{project}/ui-inventory.json` | Optional | A previous run of this skill | First run: ids start at 001 |
| `work/traceability.json` | Optional | Any earlier skill | Created as `{ "schema_version": 1, "nodes": [] }` |
| `work/context.md` § Open Questions | Optional | All skills | Created on first entry |

`{project}` is `project_name` in `work/pipeline-progress.json` (fallback: the target directory's
base name) — the directory `/architect:investigate` writes to.

## Invocation

```
/architect:analyze-ui [target_path] [--ui-root=<path>] [--auto]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `target_path` | Optional | The codebase to analyze; defaults to `target_path` in `work/pipeline-progress.json` |
| `--ui-root=<path>` | Optional | A UI source root, relative to `target_path` or absolute. Repeatable. Use when the UI lives outside the detected roots (a separate frontend repository, a second web module) |
| `--auto` | Optional | Ask nothing: every unresolved route, target, guard or behaviour question becomes an `unasked` Open Question (@rules/open-questions.md §5). `/architect:pipeline` invokes it this way |

## Available Resources

- **Serena MCP** — activate the target first (`activate_project` with `target_path`), then
  `find_symbol` / `find_referencing_symbols` for handler → service → entity and for where a request
  parameter is validated server-side. Without Serena, Grep and Read do the same on a small codebase.
- **Glob/Grep/Read** — templates, routes, includes, resource bundles, style and script files
- **Task (general-purpose)** — batched per-screen extraction (Step 4)
- `tools/lib/ui_inventory.py` — validates the inventory (Step 8)
- `tools/lib/ui_metrics.py` — the navigation, task and consistency figures the views show (Step 9)

## Execution

Write each step's output as soon as the step completes. Intermediate results go under
`work/ui-analysis/`, so an interrupted run resumes from the last completed step.

### Step 0: Register the phase

Stamp `analyze-ui` in `work/pipeline-progress.json` as `in_progress` with `"plugin": "architect"`
and `started_at`, per @skills/common/progress-registry.md — before reading anything else.

### Step 1: Resolve the scope

1. Resolve `target_path`, `{project}` and the UI roots (`--ui-root`, else detected in Step 2).
2. Read the investigate reports if they exist — the Presentation Layer section of the technology
   stack names the UI framework and roots.
3. Load the previous inventory, if any, for id stability (@rules/ui-analysis.md §7), and read
   `work/traceability.json` for the highest existing `UIS-` / `UIC-` / `UIF-` numbers.
4. Load the Open Questions store and pick up any `deferred` / `unasked` entry about the UI
   (@rules/open-questions.md §7).

**No UI layer** — no templates, no SPA, no server-rendered views (a pure API or batch system): write
nothing, stamp the phase `skipped` with `summary: "no UI layer found"`, and stop.

### Step 2: Detect the technology

Apply the detection table of @rules/ui-analysis.md §2: build files and dependencies first, then
file extensions. Record each technology with the file that proves it. Identify **vendored**
third-party assets (`js/lib/`, `webjars/`, `node_modules/`, a UI framework's `*.min.css`) so the
later steps exclude them. Write `work/ui-analysis/technologies.json`.

### Step 3: Build the route map and the screen list

Read every route source the technology has (`web.xml`, `@WebServlet`, `struts-config.xml`,
`@RequestMapping`, router configuration) and follow each route through its handler: to the template
it renders, and to where its success path redirects or forwards.

- A route that renders a template is a **screen** (@rules/ui-analysis.md §1) — including a landing
  page with nothing to do on it. A template reachable by URL without a route (a JSP outside
  `WEB-INF`) is a screen too.
- A route that only redirects (`/logout` → `/login`) is a **non-screen route**: recorded so actions
  through it can be followed to the screen they land on.
- `entry: true` only for screens reached without navigating from another screen and without
  authenticating first — the login page, a public landing page. The home page after login is not an
  entry.

Assign ids: reuse the previous inventory's id where `route` and `source` match; number new screens
`max + 1` over the inventory and the traceability graph. Write `work/ui-analysis/route-map.json`:
`{screens: [{id, route, source, handlers, entry}], non_screen_routes: [{route, handlers,
redirects_to}]}`.

### Step 4: Extract each screen (parallel batches)

Split the screens into batches of about ten and, **in a single message**, issue one `Task()` per
batch. Each sub-agent writes its batch to a file and replies with a short summary, so no reply
carries a whole UI:

```
Task(
  subagent_type: "general-purpose",
  description: "UI extraction batch <N>",
  prompt: """
You are extracting screens of an existing web UI into JSON. Read the code; do not guess.
The authoritative shape and definitions are in <PLUGIN_ROOT>/rules/ui-analysis.md §3 — read §1 and
§3 before you start.
Target root: <TARGET_PATH>. Every `source` you write is `path`, `path:line` or `path:start-end`
relative to it, and must point at the construct you describe.

Screens in this batch: <SCREENS>   [id, route, template source, handler refs — from the route map]
Route map of the whole UI:        <ROUTE_MAP>   [screens and non-screen routes with their redirects]
Vendored files to skip:           <VENDORED>

For each screen read the template, every include/fragment/tag it uses, the scripts it loads, and the
handler that serves it. Produce:
{ "id", "name" (the title a user sees), "route" (no query string), "source", "entry",
  "handlers": [{"ref", "source", "services": [], "entities": []}],
  "access": {"authentication": "required|none", "roles": [...], "guards": [{"kind", "source"}]},
  "inputs": [{"name", "label", "label_association", "control", "type", "required",
              "validation": [{"rule", "value", "where", "enforcement", "source", "client_source"}],
              "prefilled_from", "redundant_with", "source"}],
  "outputs": [{"name", "label", "kind", "fields": ["field names"], "source"}],
  "actions": [{"local_id": "A1", "label", "command", "kind", "scope", "method", "endpoint",
               "lands_on_route", "inputs": ["input names it sends"], "guard": null | {"kind", "roles", "source"},
               "destructive", "confirmation", "unresolved", "source"}],
  "messages": [{"kind", "text", "source"}],
  "components_used": [{"name", "kind", "source"}],
  "hand_built": [{"name", "kind": "inline-style|copy", "mimics_source", "source"}],
  "embedded_logic": [{"kind", "description", "should_live_in", "source"}],
  "lang", "images": [{"src", "alt", "decorative", "source"}],
  "color_pairs": [{"fg", "bg", "text", "where", "source"}] }

Allowed values:
- label_association: for | wrapping | aria | legend | placeholder-only | none (n/a for hidden only)
- control: text password email number tel date select radio checkbox textarea file hidden other
- type: string integer decimal date boolean enum file other
- validation.rule: required min max minLength maxLength pattern enum format custom;
  where: client | server | both; enforcement: reject | clamp | ignore
- outputs.kind: field (one record as label/value) | table | list | message | image | chart | download | other
- actions.kind — by effect: submit (sends data / changes state) | link (navigates only; a GET form
  that only moves on is a link) | ajax | button (acts on the page itself) | other; scope: screen | global
- messages.kind: error warning info success
- guards.kind: view controller filter config route
- embedded_logic.kind: calculation validation authorization workflow formatting data-access other;
  should_live_in: domain | application | presentation

Rules:
- access.roles is never empty: the roles the screen admits — every role the system defines when it
  is authenticated but checks no role; ["anonymous"] when no authentication is needed. access.guards
  are checks that protect the whole screen; a check that shows or hides one link or button is that
  action's `guard`. Before recording a view guard, look for the same check in the handler, filters
  and security config.
- command: verb-first (PlaceOrder, SearchProducts). Every submit and ajax action has one, and so
  does a link that changes state (GET /logout). Pure navigation: null.
- lands_on_route: where the user ends up on the handler's success path — follow its redirect or
  forward, and follow non-screen routes (/logout -> /login). A re-render on validation failure is not
  where it lands. Leave it null and fill `unresolved` only when the path itself is built at runtime.
- inputs (on submit/ajax actions): the names of this screen's inputs the action sends.
- destructive: deletes, cancels or discards something the user would lose (including a session cart
  dropped by logging out). confirmation: a dialog, a confirm step or undo exists — read the script,
  not the label; a submit on a review screen that shows what will happen is confirmed by it.
- labels: the text a user sees, bundle keys resolved; the placeholder when that is all there is;
  without decorations like a "required" badge. Visible text that nothing associates with the input
  is `none`.
- validation: `where` is what the code shows; confirm a server rule in the handler before writing
  `server`. For `both`, `source` is the server check and `client_source` the client one. A server that
  silently corrects the value is `enforcement: clamp`.
- prefilled_from: system-held data or defaults only — not a value re-displayed after a failed submit.
  redundant_with: where the system already holds a value the screen asks for again.
- hidden inputs: record those carrying data the action depends on (ids, tokens); skip ones that only
  tell buttons apart (action=add).
- messages: verbatim; `source` is where the text is authored (bundle line, template line, or the
  handler line for text it passes in or sends as an error).
- chrome: record header/footer actions on each screen that includes them (scope global); do not
  record chrome outputs per screen.
- color_pairs: text whose color (declared or inherited) sits on a declared background — the nearest
  declared background up the containers, #ffffff when none is (say so in `where`). 6-digit lowercase
  hex. `large` = WCAG large text (>= 24px, or >= 18.66px bold). Include the chrome's pairs.
- hand_built: an element rebuilt with inline styles instead of a shared component (inline-style), or
  a shared component's markup pasted by hand (copy); `mimics_source` is the shared component's file.

Write the array of screens to <PROJECT_DIR>/work/ui-analysis/batch-<N>.json. Reply with one line per
screen: id, inputs, actions, embedded-logic items — and every point where the code did not settle a
field, with file:line.
"""
)
```

When every batch has returned, convert the batch shape to the inventory shape (@rules/ui-analysis.md §3):

| Batch field | Inventory field |
|-------------|-----------------|
| `local_id` | `id` = `<screen id>.A<n>`, in `local_id` order |
| `lands_on_route` | `target` = the `UIS-` of that route, following non-screen routes; `null` when it lands nowhere a route map knows (the `endpoint` remains) |
| `components_used` | `components` = the `UIC-` ids assigned in Step 5 |
| `hand_built` | a component of kind `inline-style` / `copy` (Step 5), whose `duplicates` is the `UIC-` of `mimics_source`; the screen lists it in `components` |
| everything else | unchanged |

### Step 5: Components

Collect every component source of @rules/ui-analysis.md §2 (includes, fragments, tag files,
framework components, CSS classes that define a visual element and are used on two or more screens)
plus the batches' `components_used` and `hand_built` entries. Deduplicate by source, keep previous ids
where `source` and `name` match, and assign new `UIC-` ids. For each: read it for its `variants`
(attribute or prop values that change its rendering) and `states` (disabled, error, loading…); set
`level` — `template` for an include that opens or closes the page structure, otherwise by whether it
contains other components; set `used_by` from the screens that use it (for a class a script injects,
the screens whose scripts inject it) and `token_refs` from the values it applies. A declared
component no screen uses is `unused: true`.

### Step 6: Design tokens

Scan the style sources (stylesheets, `<style>` blocks, inline `style=` attributes, theme or Tailwind
configuration), excluding vendored files, and apply @rules/ui-analysis.md §5:

- **Normalize** colors to 6-digit lowercase hex (`#06c`, `rgb()`, named colors), sizes to px, `bold`
  to 700 and `normal` to 400. Skip zero, `inherit`, `transparent` and layout sizes.
- **One raw token per distinct value, named by it** — `color.hex-0066cc`, `font.size.px-14`,
  `font.family.<first family slug>`, `font.weight.w-700`, `space.px-8`, `radius.px-4`,
  `border.width.px-1`, `shadow.<slug>` — with `sources` and `usage_count` (declarations using it).
- **Cluster** by role, then closeness: colors for the same purpose within about 48 in RGB distance,
  font sizes within 2 px for the same text role, spacing within 2 px for the same purpose; a hover or
  active shade is its own role.
- **Semantic candidates** — `semantic.color.<role>` aliasing the most-used member of each role cluster
  (ties: the member a shared component uses, then the lexically first), `$description` stating it is
  a candidate.

Write `reports/before/{project}/ui-design-tokens.json`:

```json
{
  "$description": "As-is design tokens of <project>, extracted by /architect:analyze-ui",
  "color": {
    "hex-0066cc": { "$type": "color", "$value": "#0066cc",
      "$extensions": { "nexus-architect": { "sources": ["src/main/webapp/css/common.css:12"],
                                            "usage_count": 14, "cluster": "primary-blue" } } }
  },
  "font": { "size": { "px-14": { "$type": "dimension", "$value": "14px", "$extensions": { "nexus-architect": { "sources": ["..."], "usage_count": 31, "cluster": "body-text" } } } } },
  "semantic": { "color": { "primary": { "$type": "color", "$value": "{color.hex-0066cc}",
                                        "$description": "candidate — most-used member of primary-blue" } } }
}
```

### Step 7: Features and tasks

**Features.** Group every action that carries a command by that command; each group is one feature
(`UIF-`, previous id kept where the command matches). Name it verb-first in the output language.
`screens` are its actions' screens; `actors` are the union of those screens' `access.roles`;
`handlers` are the endpoints' handler methods; `entities` and `entity_operations` (C/R/U/D per
entity) come from tracing those handlers through services and repositories.

**Tasks.** Name the user goals the features serve and the path a user walks for each: `screens` in
order, each reached from the previous by a declared transition; `features` used along it. Checkout
is one task across cart, entry, confirm and complete even when it spans two commands; a feature used
on one screen is a one-screen task. Every feature appears in at least one task.

### Step 8: Assemble and validate the inventory

Write `reports/before/{project}/ui-inventory.json` — top level `{schema_version: 1, project,
target_path, ui_roots, technologies, screens, components, features, tasks, design_tokens,
coverage}` — with `coverage.template_files` (the number of templates examined), `coverage.screens`
(equal to the number of screens) and `coverage.unresolved` (every template that is neither a screen,
a component nor included anywhere, and every route or target the code cannot settle, each with its
reason and Open Question id — Step 11).

Then run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/ui_inventory.py" <project_dir>
```

It checks the ten rules of @rules/ui-analysis.md §4, including that every `source` exists and every
line is inside its file. Treat a violation as a defect in the inventory, not in the checker: fix the
model and re-run until it exits 0.

### Step 9: Write the views

Render the four views **from the inventory** with a small script under `work/ui-analysis/`, so a
rerun regenerates them rather than re-authoring them. Take depth, orphans, dead ends, unreachable
screens, task steps, label drift and fragmented clusters **from**
`python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/ui_metrics.py" <project_dir>` — the views show measured
figures, they do not re-derive them.

Every view carries the frontmatter of @rules/output-conventions.md
(`phase: "Phase 1: Investigation"`, `skill: analyze-ui`, `input_files` naming the inventory), starts
its headings at `##`, and is written in the configured `output_language`. The section names below
are canonical; in another language write the translation with the English name in parentheses
(`## 画面一覧（Screen List）`). Labels, messages and screen names stay verbatim as the UI shows them.

**`ui-screen-catalog.md`**
- `## Summary` — screens, entry screens, components, features, tasks, unresolved items.
- `## Screen Transition Diagram` — Mermaid `flowchart LR`; node ids without hyphens (`UIS001`),
  labels quoted; global actions omitted; orphans and dead ends styled distinctly. Over about forty
  screens, one diagram per task or per top-level area instead of one unreadable graph.
- `## Screen List` — id, name, route, roles, input / output / action counts, source.
- `## Screen Details` — one `###` per screen: an **INPUT** table (label, name, control, type,
  required, validation with where it runs), an **OUTPUT** table (label, kind, fields), an
  **Actions** table (label, command, where it lands or its endpoint, the inputs it sends, destructive,
  confirmation, guard), messages, and access with its guards.
- `## Screen-to-Code Map` — screen → handler → services → entities, from `handlers`.
- `## Business Logic in the View Layer` — kind, description, where it should live, source.
- `## Unresolved` — the `coverage.unresolved` rows with their Open Question ids.

**`ui-features.md`** — `## Feature List` (id, name, command, screens, actors, entities),
`## Tasks` (name, goal, screen path, steps, inputs — from the metrics), `## Actor × Feature`,
`## Feature × Entity` (`entity_operations`), and `## Validation Rules as Acceptance-Criteria
Candidates` (feature → the inputs its actions send → each rule and where it runs; a client-only rule
is flagged).

**`ui-components.md`** — `## Component Inventory` (id, name, kind, level, variants, states, used by,
source), `## Hand-Built Duplicates` (each `inline-style` / `copy` component and what it rebuilds),
`## Unused Components`.

**`ui-design-system-extract.md`** — `## Palette` (every color token with usage count and cluster),
`## Typography`, `## Spacing, Radius, Borders and Shadow`, `## Fragmentation` (each cluster with
more than one member and a consolidation proposal), `## Semantic Token Candidates`,
`## Component Variants`, and `## Importing into a Design System`:

```
/product:design-system --import=reports/before/{project}/ui-design-tokens.json --name=<name>
```

### Step 10: Append traceability

Append one node per screen, component and feature to `work/traceability.json` (create it as
`{ "schema_version": 1, "nodes": [] }` if absent; never start a second graph), all citing the
inventory (@rules/ui-analysis.md §7):

```json
{ "id": "UIS-006", "type": "ui-screen", "title": "注文入力", "skill": "analyze-ui",
  "source_file": "reports/before/{project}/ui-inventory.json", "upstream": [] }
{ "id": "UIC-003", "type": "ui-component", "title": "button.tag", "skill": "analyze-ui",
  "source_file": "reports/before/{project}/ui-inventory.json", "upstream": [] }
{ "id": "UIF-004", "type": "ui-feature", "title": "Place an order", "skill": "analyze-ui",
  "source_file": "reports/before/{project}/ui-inventory.json", "upstream": ["UIS-006", "UIS-007"] }
```

On a rerun, update nodes in place by id; a screen that no longer exists keeps its node with
`"status": "removed"`.

### Step 11: Open Questions

Two kinds of question come out of this skill, both per @rules/open-questions.md:

- **What the code cannot settle about the model** — a route or target whose path is assembled at
  runtime, a role resolved from the database, a template nothing reaches. These are also rows of
  `coverage.unresolved`, citing their `OQ-` id.
- **What the code cannot settle about behaviour** — a screen that claims something no code does
  (a confirmation mail nobody sends), a capability with no way in (an edit screen no list links to).
  These are Open Questions only.

Interactive runs ask them in one `AskUserQuestion` batch of at most four, with options derived from
what the code suggests. Under `--auto`, record each as `unasked` with the question and the options
that would have been offered. The store is the table in `work/context.md` § Open Questions:

```
| ID | Question | Status | Answer | Options offered | Owner | Impact | Asked at |
```

### Step 12: Complete the phase

Stamp `analyze-ui` `completed` with `completed_at`, `outputs` (the six files) and a one-line
`summary` (screens, components, features, tasks, embedded-logic items, unresolved items).

## Output

| File | Content |
|------|---------|
| `reports/before/{project}/ui-inventory.json` | Canonical inventory: screens, components, features, tasks, coverage |
| `reports/before/{project}/ui-design-tokens.json` | As-is design tokens (W3C DTCG) with provenance and clusters |
| `reports/before/{project}/ui-screen-catalog.md` | Screens with INPUT / OUTPUT / actions / access, transition diagram, screen-to-code map, view-layer business logic |
| `reports/before/{project}/ui-features.md` | Features, tasks, actor × feature, feature × entity, acceptance-criteria candidates |
| `reports/before/{project}/ui-components.md` | Component inventory, hand-built duplicates, unused components |
| `reports/before/{project}/ui-design-system-extract.md` | Palette, typography, spacing, fragmentation, semantic token candidates, import instructions |

Intermediate: `work/ui-analysis/` (technologies, route map, per-batch extractions, the view renderer).

## Completion

1. The six outputs are written, and `python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/ui_inventory.py"
   <project_dir>` exits 0.
2. `coverage.screens` equals the number of screens, and every unresolved item has an Open Question.
3. `UIS-` / `UIC-` / `UIF-` nodes are in `work/traceability.json`.
4. The phase is stamped `completed` (or `skipped` with the reason when there is no UI layer).
5. Report the counts, the view-layer business logic and UI-only role checks found, and the open
   questions to the user.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:investigate | Upstream — the technology stack and module structure |
| /architect:evaluate-ux | Downstream — scores the UX from this inventory |
| /architect:analyze | Downstream — takes role guards, labels and screens as evidence for actors, the ubiquitous language and the domain-code mapping |
| /architect:define-requirements | Downstream — `UIF-` as the upstream of legacy `FR-`s |
| /architect:investigate-security | Related — view-only role guards and unescaped output are security findings |
| /product:design-system | Downstream — `--import` the token file |
