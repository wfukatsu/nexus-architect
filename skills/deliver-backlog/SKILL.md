---
description: |
  Drive each Issue of an Epic through implement, review, human approval and merge, resuming where it
  stopped and pausing at every human gate.
argument-hint: '[--epic=<id>] [--issue=<id>] [--from=implement|review|merge] [--parallel=N] [--steal] [--worktree-root=<path>] [--integration-branch=<name>] [--auto] [--yes-merge] [--max-fix-rounds=N] [--export] [--dry-run] [--lang=en|ja]'
model: sonnet
disable-model-invocation: true
---

# Backlog Delivery Orchestrator

Shared files: a path written `@rules/…`, `@skills/…`, `@templates/…` or `@docs/…` is relative to the
plugin root, `${CLAUDE_PLUGIN_ROOT}` — not to the project being worked on. Read it from there.

**Usage:** `/architect:deliver-backlog [--epic=<id>] [--issue=<id>] [--from=implement|review|merge] [--parallel=N] [--steal] [--worktree-root=<path>] [--integration-branch=<name>] [--auto] [--yes-merge] [--max-fix-rounds=N] [--export] [--dry-run] [--lang=en|ja]`

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

The markdown **checkboxes** on the items (child task lists and acceptance criteria, maintained by the
wrapped skills per @skills/common/backlog-checklists.md) are a *rendering* of **implementation
state** (implemented + tests passing) for humans, and each item's `## Delivery Status` section
(status line + `Implemented`/`Reviewed`/`Merged` stages) is the matching rendering of **delivery
state** — neither is an input: read stage from `impl.status`/labels, and treat a mismatched box or
stale status line as something the responsible skill should fix, not as state.

Read state from `impl.status` and the tracker, **never from a node's `labels` array** — that field
is the creation seed `export-backlog` wrote and is not advanced as work progresses, so trusting it
would re-deliver finished Issues. When the two disagree, the tracker wins and the manifest is
brought up to date.

Follow-up nodes added by `/architect:capture-followup` (`F`-suffixed local IDs, an `origin` field)
are ordinary Issues to this orchestrator: they join the working set as `status::todo` and flow
through the same implement → review → merge loop, with no special handling.

## Command-Line Options

- `--epic=<id>`: Deliver the Issues under this Epic. If omitted, the target Epic is chosen interactively.
- `--issue=<id>`: Deliver a single Issue (`I1.2.3` / `#<iid>` / URL) and stop.
- `--from=implement|review|merge`: Force the re-entry stage for the current Issue (overrides the status-derived stage).
- `--parallel=N`: Dispatch up to N independent Issues at once, each as a foreground sub-agent in its own worktree, three at a time (@skills/common/backlog-claims.md § Parallel delivery). Default 1.
- `--steal`: Take Issues another person holds (their claim is released as `stolen`, the holder recorded). Without it, held Issues are skipped and named.
- `--worktree-root=<path>`: Where each Issue's worktree is created (default `../<project>-worktrees`); passed through to `implement-backlog`. Implied by `--parallel`.
- `--integration-branch=<name>`: Every Issue's PR/MR targets this branch instead of the default branch; the Epic ends with the integration branch's own PR/MR into the default branch as a final human gate.
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
(`status::todo`/`doing`/`review`; `blocked` included but flagged). Read the claims
(`python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/backlog_claims.py" <project_dir> list format=json`, @skills/common/backlog-claims.md): an Issue another person holds leaves
the working set and is named with its holder, unless `--steal`. Present the ordered list and
confirm before starting, unless `--auto`. With `--issue`, the working set is that single Issue.
Claim each Issue as its turn comes — `python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/backlog_claims.py" <project_dir> claim <item> [integration=<branch>] [steal=true]` — never
all of them at the start, so a run that stops leaves nothing held that it did not touch.

### Step 2 — Per-Issue delivery loop
For each Issue in order (determine its current stage from `impl.status`/labels, or `--from`):

- **(a) implement** — If not yet implemented (`todo`/`doing`), run
  `/architect:implement-backlog <issue> [--auto]` (the first Issue builds the shared-context pack;
  its Step 5b runs `/architect:generate-docs`, so the README/docs updates are committed to the same
  branch and arrive in the same PR/MR). If the Issue is already at `review`, skip implement.
- **(b) review** — Run `/architect:review-issue <issue> [--max-fix-rounds=N] [--auto]`. This performs
  the whole-Epic review, the bounded blocker auto-fix loop, the knowledge-base update, and (on zero
  blockers) opens the PR/MR.
  - If review ends **blocked / non-converged** (`status::blocked`): **stop the loop.** Surface the
    Issue's "decision needed" note and ask the user how to proceed (skip this Issue / abort / change
    approach). Do not spin or auto-advance.
- **(c) approval gate (human — hard stop)** — With the PR/MR open, pause and ask the user to review
  and approve it. This is a hard stop by default. Continue only if `--yes-merge` (with `--auto`)
  pre-authorized it. Record the outcome in the audit log (@skills/common/progress-registry.md
  § Audit Log): `python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/audit_log.py" <project_dir> GATE_APPROVED phase=<issue id> ref=<pr/mr url>` on approval, `GATE_REJECTED`
  with the reason in `detail=` when the user sends it back, `GATE_SKIPPED detail="--yes-merge"`
  when it was pre-authorized.
- **(d) merge** — After approval, run `/architect:merge-issue <issue>`, **passing `--yes-merge`
  through** when the user pre-authorized it (otherwise merge-issue's own confirmation gate applies;
  its preflight always runs either way), and `--integration-branch` when the Epic uses one. The
  post-merge roll-up updates Sub-Epic/Epic status; a completed Sub-Epic triggers the whole-Epic
  review. `merge-issue` releases the Issue's claim.
- **(e) advance** — Move to the next Issue. The user may stop between Issues.

With `--parallel=N`, stages (a) and (b) run for up to N Issues at once — only Issues with no
`depends_on` between them and no shared files per the export's dependency notes — each as a
foreground sub-agent (`model: sonnet`, `run_in_background: false`) given its Issue, its worktree
root and the same flags, three at a time; the sub-agent stops at stage (c) and reports the open
PR/MR. The orchestrator then asks for the approvals in one batch (one AskUserQuestion per PR/MR),
runs (d) for each approved one, and only then dispatches the next Issues.

On `--dry-run`, walk the working set reporting the stage and the command that would run for each,
with no side effects.

### Step 3 — Completion
Stop when every Issue in the working set is `done`, is `blocked` awaiting a decision, or the user
halts. With `--integration-branch`, when every Issue of the Epic is `done`, open the integration
branch's PR/MR into the default branch, pause for approval (a hard stop, `GATE_APPROVED` /
`GATE_REJECTED` in the audit log like stage (c)), merge it, and release the Epic's remaining
claims. Print a summary: N/M Issues done, blocked list, Issues skipped as held by others, PR/MRs
opened, merges completed, and the Epic's overall progress.

## Error Handling

- **No manifest**: stop (or run export with `--export`).
- **A sub-skill fails or stops** (missing prereq, auth, blocked, declined confirmation): stop at that
  Issue, report the reason, and ask whether to continue with the next Issue — never auto-advance past
  a failure.
- **Never auto-merge** without the approval gate (or an explicit `--yes-merge`).

## Completion Criteria

1. Every targeted Issue is `status::done` (merged), or explicitly `blocked`/deferred by the user.
2. `backlog-manifest.json` reflects the final `impl.status` / `pr` state for each processed Issue.
3. Each processed item's checkboxes match its outcome — acceptance criteria ticked (or explicitly
   reported as open/waived), and implemented-and-tested Issues ticked off in their Sub-Epic's task
   list (verified again at merge).
4. A delivery summary has been presented.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:export-backlog | Upstream — creates the backlog + manifest this orchestrator drives |
| /architect:implement-backlog | Stage (a) — implements each Issue |
| /architect:review-issue | Stage (b) — reviews, auto-fixes blockers, raises the PR/MR |
| /architect:merge-issue | Stage (d) — merges after approval and rolls up |
| /architect:capture-followup | Adds follow-up Issues mid-delivery; they enter this loop as `status::todo` |
| /architect:pipeline | Analogue — the analysis/design pipeline orchestrator |
