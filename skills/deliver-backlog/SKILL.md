---
description: |
  Orchestrate the implementation skill group over a backlog: drive each Issue under an Epic through
  implement → review → (human approval) → merge, in order, until the Epic's Issues are done. Wraps
  /architect:implement-backlog, /architect:review-issue, and /architect:merge-issue; sequences and
  gates them, and resumes from progress recorded in backlog-manifest.json. Semi-autonomous — it
  stops for the human gates (PR/MR approval, merge, blocker decisions) rather than merging on its own.
  /architect:deliver-backlog [--epic=<id>] [--issue=<id>] [--from=implement|review|merge] [--auto] [--yes-merge] [--max-fix-rounds=N] [--export] [--dry-run] [--lang=en|ja].
  Only runs when explicitly invoked. Requires a backlog from /architect:export-backlog.
model: sonnet
user_invocable: true
disable-model-invocation: true
---

# Backlog Delivery Orchestrator

## Expected Outcome

Take an Epic's Issues from "planned" to "merged" by running the implementation skill group in order,
Issue by Issue: implement the code, review it for whole-Epic consistency (auto-fixing blockers and
raising a PR/MR), pause for the human to approve, then merge and roll up. The per-Issue work is done
by the existing delivery skills; this orchestrator owns **ordering, selection, the human gates, and
resume**. The end state is the target Epic's Issues at `status::done` with their PR/MRs merged.

## Skills Orchestrated (the implementation group)

`/architect:implement-backlog` → `/architect:review-issue` → `/architect:merge-issue`, per Issue.
`/architect:export-backlog` is the upstream prerequisite (it creates the backlog + manifest); run it
first, or pass `--export` to have this skill run it when the manifest is missing.

## Progress Registry

This orchestrator does **not** create a new progress file. The source of truth is the existing
`reports/backlog/backlog-manifest.json` (each node's `impl.status` and the tracker `status::*`
labels: `todo · doing · review · done · blocked`). Re-running resumes from there — completed Issues
are skipped, in-flight Issues continue from their current stage.

## Command-Line Options

- `--epic=<id>`: Deliver the Issues under this Epic. If omitted, the target Epic is chosen interactively.
- `--issue=<id>`: Deliver a single Issue (`I1.2.3` / `#<iid>` / URL) and stop.
- `--from=implement|review|merge`: Force the re-entry stage for the current Issue (overrides the status-derived stage).
- `--auto`: Skip the interactive confirmations inside implement/review. Does **not** bypass the approval or merge gate unless `--yes-merge` is also set.
- `--yes-merge`: Pre-authorize the PR/MR approval + merge gate; passed through to `/architect:merge-issue` (use only when you intend unattended merges).
- `--max-fix-rounds=N`: Passed through to `review-issue` for the blocker auto-fix loop (default from that skill).
- `--export`: Run `/architect:export-backlog` first if no manifest exists.
- `--dry-run`: Report the planned sequence and per-Issue actions without implementing, commenting, raising a PR/MR, or merging.
- `--lang=en|ja`: Output language (default from `work/pipeline-progress.json` → `options.output_language`).

## Execution Strategy

### Step 0 — Preconditions
Read `reports/backlog/backlog-manifest.json` and the platform (gitlab/github). If it is missing:
with `--export`, run `/architect:export-backlog` first (confirm target/platform); otherwise stop and
tell the user to run `/architect:export-backlog`. Verify tracker auth (`glab auth status` /
`gh auth status`).

### Step 1 — Scope
Resolve the target Epic (`--epic`, else present the Epics and ask via AskUserQuestion). Enumerate its
Issues in dependency order and form the working set — by default the not-done Issues
(`status::todo`/`doing`/`review`; `blocked` included but flagged). Present the ordered list and
confirm before starting, unless `--auto`. With `--issue`, the working set is that single Issue.

### Step 2 — Per-Issue delivery loop
For each Issue in order (determine its current stage from `impl.status`/labels, or `--from`):

- **(a) implement** — If not yet implemented (`todo`/`doing`), run
  `/architect:implement-backlog <issue> [--auto]` (the first Issue builds the shared-context pack). If
  the Issue is already at `review`, skip implement.
- **(b) review** — Run `/architect:review-issue <issue> [--max-fix-rounds=N] [--auto]`. This performs
  the whole-Epic review, the bounded blocker auto-fix loop, the knowledge-base update, and (on zero
  blockers) opens the PR/MR.
  - If review ends **blocked / non-converged** (`status::blocked`): **stop the loop.** Surface the
    Issue's "decision needed" note and ask the user how to proceed (skip this Issue / abort / change
    approach). Do not spin or auto-advance.
- **(c) approval gate (human — hard stop)** — With the PR/MR open, pause and ask the user to review
  and approve it. This is a hard stop by default. Continue only if `--yes-merge` (with `--auto`)
  pre-authorized it.
- **(d) merge** — After approval, run `/architect:merge-issue <issue>`, **passing `--yes-merge`
  through** when the user pre-authorized it (otherwise merge-issue's own confirmation gate applies;
  its preflight always runs either way). The post-merge roll-up updates Sub-Epic/Epic status; a
  completed Sub-Epic triggers the whole-Epic review.
- **(e) advance** — Move to the next Issue. The user may stop between Issues.

On `--dry-run`, walk the working set reporting the stage and the command that would run for each,
with no side effects.

### Step 3 — Completion
Stop when every Issue in the working set is `done`, is `blocked` awaiting a decision, or the user
halts. Print a summary: N/M Issues done, blocked list, PR/MRs opened, merges completed, and the
Epic's overall progress.

## Error Handling

- **No manifest**: stop (or run export with `--export`).
- **A sub-skill fails or stops** (missing prereq, auth, blocked, declined confirmation): stop at that
  Issue, report the reason, and ask whether to continue with the next Issue — never auto-advance past
  a failure.
- **Never auto-merge** without the approval gate (or an explicit `--yes-merge`).

## Completion Criteria

1. Every targeted Issue is `status::done` (merged), or explicitly `blocked`/deferred by the user.
2. `backlog-manifest.json` reflects the final `impl.status` / `pr` state for each processed Issue.
3. A delivery summary has been presented.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:export-backlog | Upstream — creates the backlog + manifest this orchestrator drives |
| /architect:implement-backlog | Stage (a) — implements each Issue |
| /architect:review-issue | Stage (b) — reviews, auto-fixes blockers, raises the PR/MR |
| /architect:merge-issue | Stage (d) — merges after approval and rolls up |
| /architect:pipeline | Analogue — the analysis/design pipeline orchestrator |
