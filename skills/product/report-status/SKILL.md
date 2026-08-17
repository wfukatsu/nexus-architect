---
description: |
  Show where the product pipeline stands — every phase's status
  (pending/in_progress/completed/failed/skipped, plus stale when an upstream phase
  changed after it finished), how many of its declared outputs exist, whether it is
  running right now, and the validation gate's verdict — on the terminal, live or as a
  one-shot render.
  /product:report-status [--once] [--phase=<name>] [--exec] [--json] [--md] [--ascii] [--ambiguous-width=2] [--lang=ja|en] to invoke.
  Wraps ${CLAUDE_PLUGIN_ROOT}/tools/nexus-status.sh, which on a terminal defaults to a
  live dashboard polling work/pipeline-progress.json every 10s, with an action menu that
  generates the next slash command per phase, an `a` key that asks Claude about the
  selected phase, and a Tab key that cycles the dashboard's other views — Architect (the
  architect pipeline), Code Generation and Backlog Delivery. The live mode runs in the
  user's own terminal, so pass --once for an in-session render.
  Only runs when explicitly invoked.
model: haiku
user_invocable: true
disable-model-invocation: true
---

# Product Pipeline Status Dashboard

## Desired Outcome

The user sees, at a glance and in real time, where the product-direction work stands:
which phase is running, how far into its outputs it is, whether the validation gate has
returned a verdict and how many assumptions are still open, what is blocked behind an
unmet dependency — and can pick a phase and get the exact slash command to run next.

## Inputs

| File | Written by | Role |
|------|-----------|------|
| `work/pipeline-progress.json` | /product:init-output + every phase | Required — phase status, `gates.validate-assumptions`, options, display language |
| `@skills/product/common/skill-dependencies.yaml` | this repo | Phase order, dependencies, declared outputs, model tier |
| `reports/**`, `design-system/`, `generated/frontend/` | the phase skills | Progress inside a running phase, and the activity timestamp |
| `work/token-usage.json`, `work/token-usage.jsonl` | `record_token_usage.py` hook | Per-phase cost and the "running now" heartbeat |

## Execution

One script does the whole job: `${CLAUDE_PLUGIN_ROOT}/tools/nexus-status.sh`.

| Invocation | Command | Effect |
|-----------|---------|--------|
| default (user's TTY) | `tools/nexus-status.sh --view=product` | Live dashboard: foldable phase tree grouped by pipeline stage + detail pane + action menu |
| in-session render | `tools/nexus-status.sh --view=product --once` | Static tree, prints and exits — **always use this when running it yourself** |
| the frontend codegen | `... --view=codegen --once` | `/product:generate-frontend` lives in the Code Generation view with the architect codegen phases, not in this tree |
| one phase | `... --phase=validate-assumptions --once` | Render a single phase with its outputs (one-shot renders only; the live dashboard ignores it) |
| run from the dashboard | `... --exec` | The action menu's `e` key and the `a` ask key suspend the dashboard and run `claude` in the foreground (requires the `claude` CLI) |
| machine-readable | `... --json` | Derived phase states as JSON (includes the gate verdict). `--phase` narrows it exactly as it narrows the tree, and the `filters` object records what was applied — `summary` always covers the whole project |
| report file | `... --md[=PATH]` | Also write Markdown (default `reports/pipeline-status.md`, or `reports/codegen-status.md` for `--view=codegen`) |
| custom poll interval | `... --watch=SEC` | Live dashboard re-checking the inputs every SEC seconds (default 10; `--live` is the same flag) |
| display fixes | `... --ascii`, `--glyphs=auto\|ascii\|unicode`, `--ambiguous-width=2`, `--color\|--no-color`, `--lang=ja\|en`, `--width=N`, `--debug` | Same semantics as `tools/token-cost-report.sh` |

Product and architect are separate pipelines, so they are separate views: `--view=product`
names this one outright rather than relying on the plugin detected from the recorded phase
names (which `--view=auto` and `--plugin=product` still do). `--group=core|extension` is an
architect-only filter — the product pipeline has no manual extension tier, so
`--group=extension` here renders a "nothing to show" line saying exactly that.

`/product:generate-frontend` is **not** in this tree. Code generation is run by hand after
the pipeline and emits code rather than reports, so it has its own view alongside the
architect codegen phases (`--view=codegen`, or `Tab` twice from here).

Exit codes: `0` rendered, `1` no project, `2` bad usage — including an unknown `--phase`,
which is reported with the pipeline's real phase names instead of an empty tree.

**Live modes belong in the user's own terminal, not in an in-session tool call.** When
the user asks to watch progress live, tell them to run, prefixing with `!` inside
Claude Code:

- `!${CLAUDE_PLUGIN_ROOT}/tools/nexus-status.sh --view=product`
- add `--exec` to launch phases (and ask questions) straight from the menu

Always pass `--once` (or `--json`/`--md`) when running it yourself.

## How state is derived (and its honest limits)

- **Status precedence**: `work/pipeline-progress.json` wins; a phase with no entry there
  is derived from its declared outputs (all present → `completed`, some → `in_progress`,
  none → `pending`).
- **Drift** is raised when the record and the filesystem disagree — `completed` with
  nothing written, or `pending` with every output present. The registry still wins on
  status; the flag says the two need reconciling.
- **`completed` expires.** A finished phase whose upstream wrote something afterwards —
  a rerun, or a hand edit of the earlier artifact — is shown as **`stale`** (`↺`)
  instead of `completed`, naming the dependency that changed and when. Invalidation
  propagates down the chain, so revising the vision visibly un-completes the personas,
  mocks and features derived from it: they leave the `n/m done` fraction, become
  runnable again, and the suggested `next:` is the earliest of them. On this pipeline
  the deliberate reply to that is usually `/product:adapt-change`, which re-runs the
  affected skills rather than the whole tail. The recorded status is untouched
  (`--json` carries both `status` and `display_status`).
- **The gate is reported, never inferred**: the header shows
  `gates.validate-assumptions.verdict` verbatim (`pending` until the skill writes one)
  with the count of open assumptions. A `go` verdict here is the only thing that means
  the pipeline passed its gate — a completed `validate-assumptions` phase does not.
- **"Running now"** means a declared output was written, or tokens were attributed to
  the phase, in the last 5 minutes; the registry's `in_progress` status is the reliable
  signal (@skills/common/progress-registry.md).
- **Optional and standalone phases** (`research-landscape`, `name-product`,
  `design-system`, `generate-frontend`, `create-domain-story`, `review`, `report`,
  `adapt-change`) are marked; the suggested `next:` skips them in favour of the
  required path.
- Contracts are asserted by `tools/lib/pipeline_status_data.test.py` (state derivation)
  and `tools/nexus-status.test.sh` (the CLI: exit codes, output modes, filters).

## Reporting Back

After relaying a `--once` render:
1. Lead with the gate: verdict and open assumptions — that is what governs whether deep
   design work should continue at all.
2. Then anything needing a decision: `failed` phases, `stale` phases and what
   invalidated them, drift, recorded errors.
3. State the current phase and the suggested next one.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /product:start | The run this dashboard observes; it writes the registry it reads |
| /product:validate-assumptions | Owns the gate verdict shown in the header |
| /product:generate-frontend | Tracked in the same tool's Code Generation view, not in this one |
| /architect:report-status | The Architect view of the same tool (Tab key) |
| /architect:report-backlog-status | The Backlog Delivery view of the same tool (Tab key) |
