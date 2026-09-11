---
description: |
  Analyze the user interface of an existing system: every screen with what it asks for (inputs, validation), what it shows (outputs, messages), what it lets a user do (actions, transitions) and who may see it; the UI components; the features the screens expose; business logic embedded in the view layer; and the design tokens the UI actually uses.
  /architect:analyze-ui [target_path] [--ui-root=<path>] [--auto] to invoke.
  Optional phase after investigate and before analyze; skipped when the system has no UI layer.
model: sonnet
user_invocable: true
---

# Existing UI Analysis

## Desired Outcome

A complete, source-cited model of the existing UI, and five views of it:

1. **UI inventory** — `ui-inventory.json`: every screen (`UIS-`), component (`UIC-`) and feature
   (`UIF-`), in the shape of @rules/ui-analysis.md §3. The canonical model; everything else is a
   projection of it.
2. **Design tokens** — `ui-design-tokens.json`: the colors, type, spacing, radius and shadows the UI
   uses, as W3C DTCG with provenance, ready for `/product:design-system --import`.
3. **Screen catalog** — per screen, its INPUT (fields, controls, validation and where it runs),
   OUTPUT (displayed data, tables, messages), actions and transitions, access, and the code behind
   it; the transition diagram; the business logic found in the view layer.
4. **Features** — the capabilities the screens expose, who uses them and what they touch.
5. **Components** — the reusable UI parts, their variants and states, where they are used, and
   where the same element was rebuilt by hand.
6. **Design-system extract** — the as-is visual language, its fragmentation, and the semantic token
   candidates for a consolidated design system.

## Decision Criteria

- **Read the route map before the templates.** Routes decide which templates are screens
  (@rules/ui-analysis.md §1–2); a template no route reaches is a component, an include or dead code,
  and is accounted for in `coverage.unresolved` when it is none of them.
- **Every screen, no sampling.** Three hundred screens yield three hundred entries, extracted in
  batches (§8 of the rule). Coverage is reported, never implied.
- **Record what the code does, not what it should do.** A rule enforced only by jQuery is
  `where: client`; a role check that exists only in a JSP is `guards: [{kind: view}]`; a discount
  computed in a scriptlet is embedded logic. These are findings, and the inventory is where they are
  first visible.
- **Cite everything.** Every input, action, message, guard and token carries a `source` into the
  target code. An element without one is not in the inventory.
- **Use the ui-to-domain vocabulary** — form fields → attributes, user action → a verb-first
  Command, action result → state or event (@rules/product/ui-to-domain.md) — so the as-is inventory
  and any to-be mock can be compared field by field.
- **Keep the fragmentation.** Near-identical colors are separate raw tokens grouped by `cluster`;
  merging them here would erase the finding (@rules/ui-analysis.md §5).

## Prerequisites

| Input | Required/Recommended | Source | If missing |
|-------|---------------------|--------|------------|
| target_path (argument) | Required | User, or `target_path` in `work/pipeline-progress.json` | Ask for it; stop if it is not a directory |
| `reports/before/{project}/technology-stack.md`, `codebase-structure.md` | Recommended | `/architect:investigate` | Detect the UI technology from build files and extensions yourself (step 2) |
| `reports/before/{project}/ui-inventory.json` | Optional | A previous run of this skill | First run: ids start at 001 |
| `work/traceability.json` | Optional | Any earlier skill | Created as `{ "schema_version": 1, "nodes": [] }` |
| `work/context.md` § Open Questions | Optional | All skills | Created on first entry |

`{project}` is `project_name` in `work/pipeline-progress.json` (fallback: the target directory's
base name) — the same directory `/architect:investigate` writes to.

## Invocation

```
/architect:analyze-ui [target_path] [--ui-root=<path>] [--auto]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `target_path` | Optional | The codebase to analyze; defaults to `target_path` in `work/pipeline-progress.json` |
| `--ui-root=<path>` | Optional | A UI source root, relative to `target_path` or absolute. Repeatable. Use when the UI lives outside the detected roots (a separate frontend repository, a second web module) |
| `--auto` | Optional | Ask nothing: every unresolved route, target or guard becomes an `unasked` Open Question (@rules/open-questions.md §5). `/architect:pipeline` invokes it this way |

## Available Resources

- **Serena MCP** — `find_symbol`, `find_referencing_symbols`: handlers → services → entities, and
  where a request parameter is validated server-side
- **Glob/Grep** — templates, routes, includes, style and script files
- **Read** — templates, resource bundles, stylesheets, route configuration
- **Task (general-purpose)** — batched per-screen extraction (step 4)
- `tools/lib/ui_inventory.py` — validates the inventory (step 8)
- `tools/lib/ui_metrics.py` — the navigation and consistency figures the views show (step 9)

## Execution

Write each step's output as soon as the step completes. Intermediate results go under
`work/ui-analysis/`, so an interrupted run resumes from the last completed step.

### Step 0: Register the phase

Stamp `analyze-ui` in `work/pipeline-progress.json` as `in_progress` with `"plugin": "architect"`
and `started_at`, per @skills/common/progress-registry.md — before reading anything else.

### Step 1: Resolve the scope

1. Resolve `target_path`, `{project}` and the UI roots (`--ui-root`, else detected in step 2).
2. Read the investigate reports if they exist — the technology stack names the UI framework, the
   codebase structure names the web modules.
3. Load the previous inventory, if any, for id stability (@rules/ui-analysis.md §7), and read
   `work/traceability.json` for the highest existing `UIS-` / `UIC-` / `UIF-` numbers.
4. Load the Open Questions store and pick up any `deferred` / `unasked` entry about the UI
   (@rules/open-questions.md §7).

**No UI layer** — no templates, no SPA, no server-rendered views (a pure API or batch system): write
nothing, stamp the phase `skipped` with `summary: "no UI layer found"`, and stop.

### Step 2: Detect the technology

Apply the detection table of @rules/ui-analysis.md §2: build files and dependencies first, then
file extensions. Record each technology with the file that proves it. Identify **vendored**
third-party assets (`js/lib/`, `webjars/`, `node_modules/`, `*.min.css` of a UI framework) so steps
5 and 6 exclude them. Write `work/ui-analysis/technologies.json`.

### Step 3: Build the route map and the screen list

Read every route source the technology has (`web.xml`, `@WebServlet`, `struts-config.xml`,
`@RequestMapping`, router configuration) and resolve each route to the template it renders,
following forwards. Each routed template is a screen; a template reachable by URL without a route
(a JSP outside `WEB-INF`) is a screen too. Mark `entry: true` on the screens a user reaches without
navigating from another screen (login, landing, home).

Assign ids: reuse the previous inventory's id where `route` and `source` match; number new screens
`max + 1` over the inventory and the traceability graph. Write `work/ui-analysis/route-map.json`
(`[{id, route, source, handlers, entry}]`).

### Step 4: Extract each screen (parallel batches)

Split the route map into batches of about twenty screens and, **in a single message**, issue one
`Task()` per batch so they run in parallel:

```
Task(
  subagent_type: "general-purpose",
  description: "UI extraction batch <N>",
  prompt: """
You are extracting screens of an existing web UI into a JSON inventory. Read the code; do not guess.
Target root: <TARGET_PATH> — every `source` you write is `path` or `path:line` or `path:start-end`
relative to it, and must point at the construct you describe.

Screens in this batch:
<SCREENS>  [id, route, template source, handler refs — from the route map]

Route map of the whole UI (to resolve where a link or a form posts):
<ROUTE_MAP>  [route -> screen id]

For each screen, read the template, every include/fragment/tag it uses, the scripts it loads, and
the handler that serves it. Return the screen in this shape (@rules/ui-analysis.md §3):
{ "id", "name" (the title a user sees), "route", "source", "entry",
  "handlers": [{"ref", "source"}],
  "access": {"authentication": "required|none", "roles": [], "guards": [{"kind": "view|controller|filter|config|route", "source"}]},
  "inputs": [{"name", "label", "label_association": "for|wrapping|aria|placeholder-only|none",
              "control", "type", "required", "validation": [{"rule", "value", "where": "client|server|both", "source"}],
              "prefilled_from", "redundant_with", "source"}],
  "outputs": [{"name", "label", "kind", "fields", "source"}],
  "actions": [{"local_id": "A1", "label", "command" (verb-first, null for pure navigation),
               "kind": "submit|link|button|ajax|other", "scope": "screen|global",
               "method", "endpoint", "target_route", "destructive", "confirmation", "source"}],
  "messages": [{"kind", "text" (verbatim), "source"}],
  "components_used": [{"name", "kind", "source"}],
  "inline_duplicates": [{"name", "mimics" (the shared component it rebuilds), "source"}],
  "embedded_logic": [{"kind", "description", "should_live_in": "domain|application|presentation", "source"}],
  "lang", "images": [{"src", "alt" (null when absent), "decorative", "source"}],
  "color_pairs": [{"fg", "bg", "text": "normal|large", "where", "source"}] }

Rules:
- Resolve resource-bundle keys to the text a user sees; keep labels and messages verbatim.
- Visible text next to an input that no <label for>, wrapping label or aria attribute ties to it is
  "none"; a placeholder alone is "placeholder-only".
- `where` is what the code shows: validate the same field in the handler before writing `server`.
- A rule that exists only in JavaScript is `client`, even if it looks complete.
- An input asking for data the system already holds (the logged-in user's e-mail) without
  pre-filling it sets `redundant_with` to where the system holds it.
- Actions from shared chrome (header logout, footer links) are `scope: global` with the include as
  their source.
- `destructive`: deletes, cancels or irreversibly changes something. `confirmation`: a dialog, a
  confirm step or an undo exists — check the script, not the label.
- A role check in the template is a guard of kind `view`; check the handler, filters and security
  config for the same check before recording anything else.
- color_pairs: for text elements whose CSS sets a color, record that color and the nearest declared
  background (walk up to the container; `#ffffff` when none is declared — say so in `where`).
  Normalize colors to 6-digit lowercase hex.
- Skip vendored third-party files: <VENDORED>.
- Do not assign ids other than `local_id`; do not invent routes; when a link target is built at
  runtime, give `target_route: null` and say so in `endpoint` or leave both null.

Return ONLY a JSON array of the screens (no markdown fences, no explanation).
"""
)
```

Write each batch's result to `work/ui-analysis/batch-<N>.json` as it returns. Then resolve every
action: `target_route` → the target screen's `UIS-` via the route map; an unmatched route with an
endpoint keeps the endpoint; neither → `unresolved` with the reason. Assign action ids
`<screen id>.A<n>` in `local_id` order.

### Step 5: Components

Collect every component source of @rules/ui-analysis.md §2 (includes, fragments, tag files,
framework components, shared CSS classes that define a visual element) plus the `components_used`
the batches reported. Deduplicate by source, keep previous ids where `source` and `name` match, and
assign new `UIC-` ids. For each: read it for its `variants` (attribute or prop values that change
its rendering) and `states` (disabled, error, loading…); decide `level` by whether it contains other
components; set `used_by` from the screens that use it and `token_refs` from the values it applies.
Each `inline_duplicates` entry becomes a `kind: inline-style` component whose `duplicates` names the
component it mimics. A declared component no screen uses is `unused: true`.

### Step 6: Design tokens

Scan the style sources (stylesheets, `<style>` blocks, inline `style=` attributes, theme or
Tailwind configuration), excluding vendored files. For every distinct value record where it is used
and how often:

- **Normalize** — colors to 6-digit lowercase hex (`#06c` → `#0066cc`, `rgb()` → hex); sizes to px.
- **One raw token per distinct value, named by it** — `color.hex-0066cc`, `font.size.px-14`,
  `font.family.<slug>`, `font.weight.w-700`, `space.px-8`, `radius.px-4`, `shadow.<slug>`.
- **Cluster** near-identical values that play the same role — colors within roughly 40 in RGB
  distance used for the same purpose (the primary action, body text, borders) — and name the
  cluster by the role (`primary-blue`, `text-muted`).
- **Semantic candidates** — for each role cluster, `semantic.color.<role>` aliasing its most-used
  member, with a `$description` stating it is a candidate
  (`semantic.color.primary` = `{color.hex-0066cc}`). Use the names of
  @rules/product/design-system.md where they fit (`bg`, `fg`, `primary`, `danger`, …).

Write `reports/before/{project}/ui-design-tokens.json`:

```json
{
  "$description": "As-is design tokens of <project>, extracted by /architect:analyze-ui",
  "color": {
    "hex-0066cc": { "$type": "color", "$value": "#0066cc",
      "$extensions": { "nexus-architect": { "sources": ["src/main/webapp/css/common.css:12"],
                                            "usage_count": 14, "cluster": "primary-blue" } } }
  },
  "font": { "size": { "px-14": { "$type": "dimension", "$value": "14px", "$extensions": { "nexus-architect": { "sources": ["..."], "usage_count": 31 } } } } },
  "semantic": { "color": { "primary": { "$type": "color", "$value": "{color.hex-0066cc}",
                                        "$description": "candidate — most-used member of primary-blue" } } }
}
```

### Step 7: Features

Group the `submit` and `ajax` actions by `command`; each group is one feature (`UIF-`, previous id
kept where the command matches). Name it verb-first in the output language. `screens` are its
actions' screens in flow order; `actors` come from their `access.roles`; `handlers` are the
endpoints' handler methods; `entities` are the domain entities those handlers read or write —
trace them with Serena (`find_symbol` on the handler, then `find_referencing_symbols` through
services and repositories). Every submit and AJAX action belongs to exactly one feature.

### Step 8: Assemble and validate the inventory

Write `reports/before/{project}/ui-inventory.json` — top level `{schema_version: 1, project,
target_path, ui_roots, technologies, screens, components, features, design_tokens, coverage}` — with
`coverage.template_files` (templates examined), `coverage.screens` (equal to the number of screens)
and `coverage.unresolved` (every template that is neither a screen nor a component, every
unresolvable route or target, each with its reason and Open Question id).

Then run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/ui_inventory.py" <project_dir>
```

It checks the nine rules of @rules/ui-analysis.md §4, including that every `source` exists and every
line is inside its file. Treat a violation as a defect in the inventory, not in the checker: fix the
model and re-run until it exits 0.

### Step 9: Write the views

Run `python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/ui_metrics.py" <project_dir>` and take depth, orphans,
dead ends, unreachable screens, label drift and fragmented clusters **from its output** — the views
show measured figures, they do not re-derive them.

Every view carries the frontmatter of @rules/output-conventions.md
(`phase: "Phase 1: Investigation"`, `skill: analyze-ui`, `input_files` naming the inventory), starts
its headings at `##`, and is written in the configured `output_language`. Labels, messages and
screen names stay verbatim as the UI shows them.

**`ui-screen-catalog.md`**
- `## Summary` — screens, entry screens, components, features, unresolved items.
- `## Screen Transition Diagram` — Mermaid `flowchart LR`; node ids without hyphens (`UIS001`),
  labels quoted; global actions omitted; orphans and dead ends styled distinctly. Over about forty
  screens, one diagram per feature or per top-level area instead of one unreadable graph.
- `## Screen List` — id, name, route, roles, input / output / action counts, source.
- `## Screen Details` — one `###` per screen: an **INPUT** table (label, name, control, type,
  required, validation with where it runs), an **OUTPUT** table (label, kind, fields), an
  **Actions** table (label, command, target or endpoint, destructive, confirmation), messages, and
  access with its guards.
- `## Screen-to-Code Map` — screen → handler → service → entity.
- `## Business Logic in the View Layer` — kind, description, where it should live, source.
- `## Unresolved` — the `coverage.unresolved` rows with their Open Question ids.

**`ui-features.md`** — `## Feature List` (id, name, command, screen path, steps, actors, entities),
`## Actor × Feature`, `## Feature × Entity` (C/R/U/D where the handler shows it), and
`## Validation Rules as Acceptance-Criteria Candidates` (feature → field → rule → where it runs;
a client-only rule is flagged).

**`ui-components.md`** — `## Component Inventory` (id, name, kind, level, variants, states, used by,
source), `## Duplicates` (each inline rebuild and what it mimics), `## Unused Components`.

**`ui-design-system-extract.md`** — `## Palette` (every color token with usage count and cluster),
`## Typography`, `## Spacing, Radius and Shadow`, `## Fragmentation` (each cluster with more than
one member and a consolidation proposal), `## Semantic Token Candidates`, `## Component Variants`,
and `## Importing into a Design System`:

```
/product:design-system --import=reports/before/{project}/ui-design-tokens.json --name=<name>
```

### Step 10: Append traceability

Append one node per screen, component and feature to `work/traceability.json` (create it as
`{ "schema_version": 1, "nodes": [] }` if absent; never start a second graph):

```json
{ "id": "UIS-006", "type": "ui-screen", "title": "注文入力", "skill": "analyze-ui",
  "source_file": "reports/before/{project}/ui-inventory.json", "upstream": [] }
{ "id": "UIF-004", "type": "ui-feature", "title": "Place an order", "skill": "analyze-ui",
  "source_file": "reports/before/{project}/ui-features.md", "upstream": ["UIS-006", "UIS-007"] }
```

`UIS-` and `UIC-` nodes are as-is facts with empty `upstream`; a `UIF-` node's upstream is its
screens. On a rerun, update nodes in place by id; a screen that no longer exists keeps its node with
`"status": "removed"`.

### Step 11: Open Questions

A route, target or guard the code cannot settle — a URL assembled at runtime, a role resolved from
the database, a template no route reaches — is asked, per @rules/open-questions.md: one
`AskUserQuestion` batch of at most four, options derived from the candidates the code suggests.
Under `--auto`, record each as `unasked` with the question and the options that would have been
offered. Either way it appears in `coverage.unresolved` with its `OQ-` id.

### Step 12: Complete the phase

Stamp `analyze-ui` `completed` with `completed_at`, `outputs` (the six files) and a one-line
`summary` (screens, components, features, embedded-logic items, unresolved items).

## Output

| File | Content |
|------|---------|
| `reports/before/{project}/ui-inventory.json` | Canonical inventory: screens, components, features, coverage |
| `reports/before/{project}/ui-design-tokens.json` | As-is design tokens (W3C DTCG) with provenance and clusters |
| `reports/before/{project}/ui-screen-catalog.md` | Screens with INPUT / OUTPUT / actions / access, transition diagram, screen-to-code map, view-layer business logic |
| `reports/before/{project}/ui-features.md` | Features, actor × feature, feature × entity, acceptance-criteria candidates |
| `reports/before/{project}/ui-components.md` | Component inventory, duplicates, unused components |
| `reports/before/{project}/ui-design-system-extract.md` | Palette, typography, spacing, fragmentation, semantic token candidates, import instructions |

Intermediate: `work/ui-analysis/` (technologies, route map, per-batch extractions).

## Completion

1. The six outputs are written, and `python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/ui_inventory.py"
   <project_dir>` exits 0.
2. `coverage.screens` equals the number of screens, and every unresolved item has an Open Question.
3. `UIS-` / `UIC-` / `UIF-` nodes are in `work/traceability.json`.
4. The phase is stamped `completed` (or `skipped` with the reason when there is no UI layer).
5. Report the counts, the view-layer business logic found, and the unresolved items to the user.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:investigate | Upstream — the technology stack and module structure |
| /architect:evaluate-ux | Downstream — scores the UX from this inventory |
| /architect:analyze | Downstream — takes role guards, labels and screens as evidence for actors, the ubiquitous language and the domain-code mapping |
| /architect:define-requirements | Downstream — `UIF-` as the upstream of legacy `FR-`s |
| /product:design-system | Downstream — `--import` the token file |
