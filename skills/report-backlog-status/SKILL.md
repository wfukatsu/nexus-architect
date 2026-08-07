---
description: |
  Show backlog delivery progress as an Epic -> Sub-Epic -> Issue tree — each item's
  delivery status (todo/doing/review/done/blocked) and its Implemented / Reviewed /
  Merged stages — on the terminal, live or as a one-shot render.
  /architect:report-backlog-status [--once] [--sync] [--exec] [--epic=<id>] [--json] [--md] [--ascii] [--ambiguous-width=2] [--lang=ja|en] to invoke.
  Wraps ${CLAUDE_PLUGIN_ROOT}/tools/backlog-status.sh (the backlog view of
  tools/nexus-status.sh), which on a terminal defaults to a live dashboard polling
  backlog-manifest.json every 10s, with an action menu that generates the next slash
  command per item (copy to clipboard, or run via claude with --exec), an `a` key that
  asks Claude about the selected item, and a Tab key that cycles the dashboard's other
  views — Product, Architect (the two pipelines' phase progress) and Code Generation. The
  live mode runs in the user's own terminal, so pass --once for an in-session render.
  Only runs when explicitly invoked.
model: haiku
user_invocable: true
disable-model-invocation: true
---

# Backlog Status Dashboard

## Desired Outcome

The user sees, at a glance and in real time, where the whole delivery process stands:
how many Issues are done, which items are implemented / reviewed / merged, which are
blocked or drifting from the tracker — and can pick an item and get the exact slash
command to run next.

## Inputs

| File | Written by | Role |
|------|-----------|------|
| `reports/backlog/backlog-manifest.json` | /architect:export-backlog (+ delivery skills) | Required — the tree, `impl.status`, `pr` state |
| `reports/backlog/followup-queue.md` | /architect:capture-followup + feeders | Optional — unflushed follow-up count |
| `reports/backlog/impl-log/`, `reports/backlog/reviews/` | implement/review skills | Optional — detail pane |
| `work/pipeline-progress.json` | /architect:pipeline | Optional — pipeline phase strip, display language |
| Tracker labels via `glab` / `gh` | — | Optional — `--sync` / `s` key; the tracker wins over the manifest |

## Execution

One script does the whole job: `${CLAUDE_PLUGIN_ROOT}/tools/backlog-status.sh` — a thin
alias for `tools/nexus-status.sh --view=backlog`, so every option below is also available
on the unified tool, and `Tab` inside the dashboard cycles its other views: Product and
Architect (`/product:report-status`, `/architect:report-status` — two pipelines, so two
views) and Code Generation (`--view=codegen`).

| Invocation | Command | Effect |
|-----------|---------|--------|
| default (user's TTY) | `tools/backlog-status.sh` | Live dashboard: foldable tree + detail pane + action menu, manifest re-checked every 10s |
| in-session render | `tools/backlog-status.sh --once` | Static tree, prints and exits — **always use this when running it yourself** |
| tracker truth | `... --sync` | Fetch live `status::*` labels once at startup (also the `s` key) |
| run from the dashboard | `... --exec` | The action menu's `e` key suspends the dashboard and runs `claude "<command>"` in the foreground (requires the `claude` CLI) |
| one Epic | `... --epic=E1` | Limit the tree to that Epic (and its subtree). Orphans belong to no Epic, so a filter excludes them |
| machine-readable | `... --json` | Derived states as JSON. `--epic` narrows it exactly as it narrows the tree, and the `filters` object records what was applied — `summary` always covers the whole manifest |
| report file | `... --md[=PATH]` | Also write Markdown (default `reports/backlog/backlog-status.md`) |
| custom poll interval | `... --watch=SEC` | Live dashboard re-checking the manifest every SEC seconds (default 10; `--live` is the same flag) |
| display fixes | `... --ascii`, `--glyphs=auto\|ascii\|unicode`, `--ambiguous-width=2`, `--color\|--no-color`, `--lang=ja\|en`, `--width=N`, `--debug` | Same semantics as `tools/token-cost-report.sh` — see that skill's "When the bars look wrong" table |

Exit codes: `0` rendered, `1` no project or no `backlog-manifest.json`, `2` bad usage —
including an unknown `--epic`, which is reported with the manifest's real Epic IDs instead
of rendering an empty tree.

The header's pipeline strip (`pipeline 9/24 ▶ define-scope ↺ 2`) is derived by the same
state layer as the pipeline view, so it counts the manifest's phases — not just the ones
the registry happens to mention — and drops invalidated (`stale`) phases from the
completed count exactly as that view does.

**Live modes belong in the user's own terminal, not in an in-session tool call.** When
the user asks to watch progress live, do not run the dashboard yourself — tell them to
run, prefixing with `!` inside Claude Code:

- `!${CLAUDE_PLUGIN_ROOT}/tools/backlog-status.sh` — the dashboard
- add `--sync` for tracker truth, `--exec` to launch skills straight from the menu

Always pass `--once` (or `--json`/`--md`) when running it yourself: with no mode flag
the script starts the live dashboard on a terminal, which never exits on its own.

## How state is derived (and its honest limits)

- **Delivery status precedence**: tracker label (after a sync) > manifest `impl.status`
  > `todo`. A node's `labels` array is **never** read — it is the creation seed
  (deliver-backlog contract). Divergence is flagged as drift; the tracker wins.
- **Stages** `[I][R][M]` are derived from the manifest: `M` = `pr.merged` or status
  `done`; `R` = a `pr.url` exists; `I` = status `review`/`done` or a PR exists. While an
  Issue is still `doing` the manifest cannot express "implemented but unreviewed", so
  the boxes stay unmet — the item bodies' `## Delivery Status` checklists are the
  authoritative rendering (this tool does not fetch live bodies).
- **Parents** use their own `impl.status` (merge-issue writes roll-ups) or aggregate
  their children; `n/m` counts descend over Issues.
- Contracts are asserted by `tools/lib/backlog_status_data.test.py` (state derivation)
  and `tools/nexus-status.test.sh` (the CLI: exit codes, output modes, filters).

## Reporting Back

After relaying a `--once` render:
1. Lead with blocked items and tracker drift, if any — those need a human decision.
2. Note the follow-up queue count when non-zero (`/architect:capture-followup --flush`).
3. Suggest the next command for the most advanced in-flight item (the same one the
   dashboard's action menu would preselect).

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:export-backlog | Writes the manifest this dashboard renders |
| /architect:deliver-backlog | The loop this dashboard observes; its stages are the action menu |
| /architect:implement-backlog, /architect:review-issue, /architect:merge-issue | The commands the action menu generates |
| /architect:capture-followup | Follow-up queue surfaced in the header and menu |
| /architect:report-status, /product:report-status | The two pipeline views of the same tool (Tab key) |
| /architect:report-token-cost | Sibling terminal dashboard; shares display conventions |
