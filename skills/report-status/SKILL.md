---
description: |
  Show where the architect pipeline stands — every phase's status
  (pending/in_progress/completed/failed/skipped, plus stale when an upstream phase
  changed after it finished), how many of its declared outputs exist, whether it is
  running right now, and what it has cost — on the terminal, live or as a one-shot
  render.
  /architect:report-status [--once] [--group=core|extension] [--phase=<name>] [--json] [--md] [--ascii] [--ambiguous-width=2] [--lang=ja|en] to invoke.
  Wraps ${CLAUDE_PLUGIN_ROOT}/tools/nexus-status.sh, which on a terminal defaults to a
  live dashboard polling work/pipeline-progress.json every 10s, with an action menu that
  generates the next slash command per phase, an `a` key that asks Claude about the
  selected phase, and a Tab key that cycles the dashboard's other views — Product (the
  product pipeline), Code Generation and Backlog Delivery. The live mode runs in the
  user's own terminal, so pass --once for an in-session render.
  Only runs when explicitly invoked.
model: haiku
user_invocable: true
disable-model-invocation: true
---

# Pipeline Status Dashboard

## Desired Outcome

The user sees, at a glance and in real time, where the project stands in the architect
pipeline: which phase is running, how far into its outputs it is, what is blocked behind
an unmet dependency or a failure, where the recorded state and the files on disk
disagree — and can pick a phase and get the exact slash command to run next.

## Inputs

| File | Written by | Role |
|------|-----------|------|
| `work/pipeline-progress.json` | /architect:init-output + every phase | Required — phase status, options, errors, display language |
| `@skills/common/skill-dependencies.yaml` | this repo | Phase order, dependencies, declared outputs, model tier |
| `reports/**` (the declared outputs) | the phase skills | Progress inside a running phase, and the activity timestamp |
| `work/token-usage.json`, `work/token-usage.jsonl` | `record_token_usage.py` hook | Per-phase cost and the "running now" heartbeat |
| `reports/backlog/backlog-manifest.json` | /architect:export-backlog | Optional — backlog summary line and the Backlog Delivery tab |

## Execution

One script does the whole job: `${CLAUDE_PLUGIN_ROOT}/tools/nexus-status.sh`.

| Invocation | Command | Effect |
|-----------|---------|--------|
| default (user's TTY) | `tools/nexus-status.sh` | Live dashboard: foldable phase tree + detail pane + action menu, inputs re-checked every 10s |
| in-session render | `tools/nexus-status.sh --view=architect --once` | Static tree, prints and exits — **always use this when running it yourself** |
| the other pipeline | `... --view=product --once` | The product pipeline's tree — a separate pipeline, so a separate view (`/product:report-status`) |
| code generation | `... --view=codegen --once` | The code-generation phases of both plugins, grouped by plugin — they are not part of either pipeline tree |
| core phases only | `... --group=core` | Hide the manual extension tier |
| extension tier only | `... --group=extension` | Only the skills the pipeline never runs |
| one phase | `... --phase=analyze --once` | Render a single phase with its outputs (one-shot renders only; the live dashboard ignores it) |
| force the pipeline | `... --plugin=product\|architect` | Which pipeline `--view=pipeline\|auto` resolves to, when the detection from the recorded phase names is wrong |
| run from the dashboard | `... --exec` | The action menu's `e` key and the `a` ask key suspend the dashboard and run `claude` in the foreground (requires the `claude` CLI) |
| machine-readable | `... --json` | Derived phase states as JSON. `--group` / `--phase` narrow it exactly as they narrow the tree, and the `filters` object records what was applied — `summary` always covers the whole project |
| report file | `... --md[=PATH]` | Also write Markdown (default `reports/pipeline-status.md`, or `reports/codegen-status.md` for `--view=codegen`) |
| custom poll interval | `... --watch=SEC` | Live dashboard re-checking the inputs every SEC seconds (default 10; `--live` is the same flag) |
| display fixes | `... --ascii`, `--glyphs=auto\|ascii\|unicode`, `--ambiguous-width=2`, `--color\|--no-color`, `--lang=ja\|en`, `--width=N`, `--debug` | Same semantics as `tools/token-cost-report.sh` — see that skill's "When the bars look wrong" table |

Exit codes: `0` rendered, `1` no project (or the view's input file is missing), `2` bad
usage — an unknown option, and also an unknown `--phase`, which is reported with the
pipeline's real phase names instead of rendering an empty tree. A filter that legally
matches nothing (`--group=extension` on a product project) renders a "nothing to show"
line and exits `0`.

**Live modes belong in the user's own terminal, not in an in-session tool call.** When
the user asks to watch progress live, do not run the dashboard yourself — tell them to
run, prefixing with `!` inside Claude Code:

- `!${CLAUDE_PLUGIN_ROOT}/tools/nexus-status.sh` — the dashboard
- add `--exec` to launch phases (and ask questions) straight from the menu

Always pass `--once` (or `--json`/`--md`) when running it yourself: with no mode flag
the script starts the live dashboard on a terminal, which never exits on its own.

## The four views

The dashboard is one tool with four tabs, cycled with `Tab` / `Shift-Tab` and selectable
directly with `--view=`. Each keeps its own selection, folds and status filter, and a tab
this project has nothing behind is dimmed and skipped by `Tab`.

| View | `--view=` | What it holds |
|------|-----------|---------------|
| Product | `product` | The product pipeline's phases (`skills/product/common/skill-dependencies.yaml`) |
| Architect | `architect` | The architect pipeline's phases, core tier plus the manual extension tier |
| Code Generation | `codegen` | `generate-scalardb-code`, `generate-infra-code`, `generate-docs` and `/product:generate-frontend`, grouped by plugin |
| Backlog Delivery | `backlog` | The Epic → Sub-Epic → Issue tree (`/architect:report-backlog-status`) |

Why they are separate rather than one tree:

- **Product and architect are two pipelines**, with their own manifests, phase names and
  entry points. Which one a tab shows is stated, never guessed — the old single view had
  to detect a plugin from the recorded phase names and then hid the other one entirely.
  A project that ran both shows both; `--view=auto` still opens the detected one.
- **Code generation is neither.** It runs by hand after whichever pipeline designed the
  system, it emits code into the target project rather than reports under `reports/`, and
  the same tab covers both plugins — so each row offers *its own* plugin's slash command.
  `generate-test-specs` stays in the architect pipeline: it writes specs, not code.
- Dependencies still cross the boundary. `generate-scalardb-code` is blocked by
  `design-implementation` on the Architect tab, and staleness propagates between them —
  only the grouping and the progress fraction are per-view.

## How state is derived (and its honest limits)

- **Status precedence**: `work/pipeline-progress.json` wins; a phase with no entry there
  is derived from its declared outputs (all present → `completed`, some → `in_progress`,
  none → `pending`). This is what makes the manual extension tier and older projects
  visible at all.
- **Drift** is raised, not hidden, when the record and the filesystem disagree:
  `completed` with no declared output on disk, or `pending` with every output present.
  The registry still wins on status — the flag says the two need reconciling.
- **`completed` expires.** A finished phase whose upstream wrote something afterwards —
  a rerun, or a hand edit of the earlier report — is shown as **`stale`** (`↺`) instead
  of `completed`, naming the dependency that changed and when. Invalidation propagates
  down the dependency chain, so fixing one early phase visibly un-completes everything
  derived from it: those phases leave the `n/m done` fraction, become runnable again,
  their default action is a rerun, and the suggested `next:` is the earliest of them —
  rerunning from the top is what clears the rest. The recorded status is untouched
  (`--json` carries both `status` and `display_status`); nothing rewrites the registry.
  Staleness is claimed only where it is knowable: a phase that declares outputs but
  wrote none is drift, not stale, and a dependency that never ran invalidates nothing.
- **"Running now"** means a declared output was written, or tokens were attributed to
  the phase, in the last 5 minutes. A phase that thinks for a long time without writing
  anything will not blink; the registry's `in_progress` status is the reliable signal,
  which is why the orchestrators set it *before* invoking a skill (@skills/common/progress-registry.md).
- **Cost** comes from the recorded ledger; a ledger entry attributed to parallel phases
  (`evaluate-mmi+evaluate-ddd`) is split evenly, so per-phase cost is an estimate while
  the total is exact.
- **Exclusions**: `options.skip_phases` and unmet `conditions:` (e.g. the ScalarDB
  branch when `scalardb_enabled` is false) render as `skipped`, count as satisfied
  dependencies — the same rule the orchestrators use — and count as resolved in the
  `n/m done` fraction, since a branch that will never run is not outstanding work.
- **Group counts always describe the whole group**, including under a status filter, so
  `Design 2/7` next to one filtered row means "2 of the 7 Design phases are done", not
  "2 of 7 shown".
- A half-written or loosely-shaped registry degrades instead of failing: a phase
  recorded as a bare string is read as that status, an unrecognized value falls back to
  filesystem derivation, and malformed sections are dropped.
- Contracts are asserted by `tools/lib/pipeline_status_data.test.py` (state derivation)
  and `tools/nexus-status.test.sh` (the CLI: exit codes, output modes, filters).

## Reporting Back

After relaying a `--once` render:
1. Lead with anything that needs a human decision: `failed` phases, `stale` phases and
   what invalidated them, drift, recorded errors.
2. State the current phase and the suggested next one (the dashboard's `next:`), which
   skips optional entry points in favour of the required path.
3. Mention the follow-up: `/architect:report-backlog-status` once delivery has started.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:pipeline, /architect:start | The runs this dashboard observes; they write the registry it reads |
| /architect:report-backlog-status | The Backlog Delivery view of the same tool (Tab key) |
| /architect:generate-scalardb-code, /architect:generate-infra-code, /architect:generate-docs | The phases the Code Generation view (`--view=codegen`) tracks |
| /architect:report-token-cost | Sibling terminal dashboard; shares display conventions |
| /architect:estimate-token-cost | A-priori cost estimate; this shows the recorded actual |
| /product:report-status | The same dashboard for the product pipeline |
