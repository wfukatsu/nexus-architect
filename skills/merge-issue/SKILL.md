---
description: |
  Merge the Pull/Merge Request raised for a backlog Issue after the user has approved it, then roll
  up status across the Issue, Sub-Epic, and Epic. Runs a preflight (PR/MR open, review verdict
  Mergeable with no open blockers, required approvals present, CI green, no conflicts, base
  up-to-date), gates the merge itself on explicit user confirmation, executes the merge via
  glab / gh, closes the Issue, and updates the backlog manifest and progress comments.
  /architect:merge-issue [item|mr|pr] [--strategy=merge|squash|rebase] [--delete-branch] [--yes-merge] [--dry-run] [--auto] [--lang=en|ja].
  Only runs when explicitly invoked. Raise the PR/MR first with /architect:review-issue.
model: opus
user_invocable: true
disable-model-invocation: true
---

# Backlog Issue Merge

## Desired Outcome

Complete a backlog Issue by merging its approved PR/MR and reflecting that everywhere the backlog
tracks progress:

- **Safe merge.** Merge only after a preflight confirms the change is actually ready, and only after
  the user explicitly confirms the (irreversible) merge action.
- **Consistent roll-up.** After merging, the Issue is closed and set `status::done`, and the
  Sub-Epic and Epic get progress roll-ups; a completed Sub-Epic triggers the whole-Epic review.
- **Traceable.** The manifest and progress comments record the merge, so the backlog stays the
  source of truth.

Runs against the **target project** holding `reports/backlog/backlog-manifest.json` and the tracked
repository. It never edits nexus-architect itself.

## Decision Criteria

- **Target resolution** — Accept the Issue (`I1.2.3`, `#<iid>`, URL) or the PR/MR directly. Resolve
  the linked PR/MR from the manifest node's `pr` field or the Issue's comments. If none exists, stop
  and point the user to `/architect:review-issue`.
- **Merge readiness is non-negotiable** — Every preflight check must pass. If any fails, report which
  and stop; do not merge or "force" past a failing gate.
- **Explicit confirmation** — Merging is irreversible and outward-facing. Always confirm the exact
  action (PR/MR, base, strategy) with the user before merging, even when the PR/MR is already
  approved. The **only** thing that skips this gate is an explicit `--yes-merge` (pre-authorization,
  e.g. passed through by `/architect:deliver-backlog`); `--auto` never bypasses the merge gate.

## Prerequisites

| File / source | Required | Produced by |
|---------------|----------|-------------|
| `reports/backlog/backlog-manifest.json` with a `pr` on the node | Required | /architect:review-issue |
| An open, approved PR/MR for the Issue | Required | /architect:review-issue + user approval |
| `glab` / `gh` authenticated for the target project | Required | user |

Read the output language from `work/pipeline-progress.json` (`options.output_language`, default
`en`); `--lang` overrides. Comments/reports use that language; code, labels, and IDs stay English.

## Status Taxonomy (shared with the backlog family)

`status::todo · status::doing · status::review · status::done · status::blocked`
(GitHub form `status:todo` …). This skill moves the Issue `review → done`.

## Steps

### Step 0 — Load the backlog and resolve the target
Read `reports/backlog/backlog-manifest.json`; take platform, project/group, and the node. Resolve
the Issue and its PR/MR (manifest `pr`, else Issue comments, else the argument). Verify auth
(`glab auth status` / `gh auth status`).

### Step 1 — Preflight (all must pass)
Check, and stop with a clear reason if any fails:
- The PR/MR is **open** (not already merged/closed).
- The latest review verdict for the Issue is **Mergeable** with **no open `[B]` blockers**
  (read `reports/backlog/reviews/review-<issue>-round*.md` — highest round).
- **Required approvals** are present (GitLab approvals / GitHub required reviews).
- **CI / pipeline is green** if the project runs one (`glab ci status` / `gh pr checks`).
- **No merge conflicts** and the branch is **up to date** with base (offer to rebase/update, but do
  not merge through a conflict).

### Step 2 — Confirmation gate (required)
Present the PR/MR title + URL, the base branch, the merge strategy (`--strategy`, default project
default), and whether the source branch will be deleted (`--delete-branch`). Get an explicit
go-ahead — skipped only when `--yes-merge` was passed (still print what is about to merge). On
`--dry-run`, stop here and report what would be merged.

### Step 3 — Execute the merge
- GitLab: `glab mr merge <iid> [--squash|--rebase] [--remove-source-branch] [--yes]`.
- GitHub: `gh pr merge <number> [--squash|--merge|--rebase] [--delete-branch]`.
Capture the merge commit SHA / result.

### Step 4 — Post-merge roll-up
- **Issue** — set `status::done`, close it (if not auto-closed by `Closes #`), and comment the merge
  result (merge commit / URL).
- **Sub-Epic** — comment a roll-up (N/M Issues done); when all its Issues are done, set the Sub-Epic
  `status::done` and run the whole-Epic review (`/architect:implement-backlog --review-epic=<epic>`,
  or note it for the user).
- **Epic** — comment progress roll-up.
- **Manifest** — update the node: `impl.status = done`, `pr.merged = true`, merge SHA, `updated_at`.
- Report the merged URL and the updated Epic progress (e.g. "Epic E1: 4/9 Issues done").

## Acceptance Criteria

- No merge happens unless every preflight check passes **and** the user explicitly confirms (or
  explicitly pre-authorized with `--yes-merge` — preflight is never skippable).
- After a successful merge, the Issue is closed + `status::done`, and the Sub-Epic/Epic roll-ups and
  manifest are updated.
- A completed Sub-Epic triggers (or clearly recommends) the whole-Epic review.
- `--dry-run` performs no merge and no writes; it only reports readiness and intent.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:review-issue | Upstream — raises and gets approval for the PR/MR this skill merges |
| /architect:implement-backlog | Runs the whole-Epic review (`--review-epic`) after a Sub-Epic completes |
| /architect:export-backlog | Source of the manifest and Epic/Sub-Epic/Issue hierarchy |
