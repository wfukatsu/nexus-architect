---
description: |
  Show where the architect pipeline stands — every phase's status
  (pending/in_progress/completed/failed/skipped), how many of its declared outputs
  exist, whether it is running right now, and what it has cost — on the terminal,
  live or as a one-shot render.
  /architect:report-status [--once] [--group=core|extension] [--phase=<name>] [--json] [--md] [--ascii] [--ambiguous-width=2] [--lang=ja|en] to invoke.
  Wraps ${CLAUDE_PLUGIN_ROOT}/tools/nexus-status.sh, which on a terminal defaults to a
  live dashboard polling work/pipeline-progress.json every 10s, with an action menu that
  generates the next slash command per phase, an `a` key that asks Claude about the
  selected phase, and a Tab key that switches to the backlog delivery view. The live
  mode runs in the user's own terminal, so pass --once for an in-session render.
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
| `reports/backlog/backlog-manifest.json` | /architect:export-backlog | Optional — backlog summary line and the Tab view |

## Execution

One script does the whole job: `${CLAUDE_PLUGIN_ROOT}/tools/nexus-status.sh`.

| Invocation | Command | Effect |
|-----------|---------|--------|
| default (user's TTY) | `tools/nexus-status.sh` | Live dashboard: foldable phase tree + detail pane + action menu, inputs re-checked every 10s |
| in-session render | `tools/nexus-status.sh --view=pipeline --once` | Static tree, prints and exits — **always use this when running it yourself** |
| core phases only | `... --group=core` | Hide the manual extension tier |
| extension tier only | `... --group=extension` | Only the skills the pipeline never runs |
| one phase | `... --phase=analyze --once` | Render a single phase with its outputs (one-shot renders only; the live dashboard ignores it) |
| run from the dashboard | `... --exec` | The action menu's `e` key and the `a` ask key suspend the dashboard and run `claude` in the foreground (requires the `claude` CLI) |
| machine-readable | `... --json` | Derived phase states as JSON |
| report file | `... --md[=PATH]` | Also write Markdown (default `reports/pipeline-status.md`) |
| display fixes | `... --ascii`, `--ambiguous-width=2`, `--lang=ja\|en`, `--width=N`, `--debug` | Same semantics as `tools/token-cost-report.sh` — see that skill's "When the bars look wrong" table |

**Live modes belong in the user's own terminal, not in an in-session tool call.** When
the user asks to watch progress live, do not run the dashboard yourself — tell them to
run, prefixing with `!` inside Claude Code:

- `!${CLAUDE_PLUGIN_ROOT}/tools/nexus-status.sh` — the dashboard
- add `--exec` to launch phases (and ask questions) straight from the menu

Always pass `--once` (or `--json`/`--md`) when running it yourself: with no mode flag
the script starts the live dashboard on a terminal, which never exits on its own.

## How state is derived (and its honest limits)

- **Status precedence**: `work/pipeline-progress.json` wins; a phase with no entry there
  is derived from its declared outputs (all present → `completed`, some → `in_progress`,
  none → `pending`). This is what makes the manual extension tier and older projects
  visible at all.
- **Drift** is raised, not hidden, when the record and the filesystem disagree:
  `completed` with no declared output on disk, or `pending` with every output present.
  The registry still wins on status — the flag says the two need reconciling.
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
- Contracts are asserted by `tools/lib/pipeline_status_data.test.py`.

## Reporting Back

After relaying a `--once` render:
1. Lead with anything that needs a human decision: `failed` phases, drift, recorded errors.
2. State the current phase and the suggested next one (the dashboard's `next:`), which
   skips optional entry points in favour of the required path.
3. Mention the follow-up: `/architect:report-backlog-status` once delivery has started.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:pipeline, /architect:start | The runs this dashboard observes; they write the registry it reads |
| /architect:report-backlog-status | The other view of the same tool (Tab key) |
| /architect:report-token-cost | Sibling terminal dashboard; shares display conventions |
| /architect:estimate-token-cost | A-priori cost estimate; this shows the recorded actual |
| /product:report-status | The same dashboard for the product pipeline |
