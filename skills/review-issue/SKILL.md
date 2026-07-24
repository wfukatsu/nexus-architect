---
description: |
  Review a backlog Issue's implementation for whole-Epic consistency, then drive it to a mergeable
  Pull/Merge Request. Checks the Issue plus its parent Sub-Epic and Epic and the related Issues under
  the same Epic; when blockers are found it spawns fix subagents and re-reviews until they clear;
  if it fails to converge it stops, writes a decision request on the Issue, and asks the user. When
  no blockers remain it opens a PR/MR linked to the Issue and hands off to the user for approval.
  /architect:review-issue [item] [--epic=<id>] [--max-fix-rounds=N] [--base=<branch>] [--no-fix] [--dry-run] [--auto] [--lang=en|ja].
  With no item, picks the status::doing / status::review items and confirms with the user.
  Only runs when explicitly invoked. Merging is a separate step (/architect:merge-issue).
model: opus
user_invocable: true
disable-model-invocation: true
---

# Backlog Issue Review → PR/MR

## Desired Outcome

Take an implemented backlog Issue from "coded" to "ready to merge", without breaking the rest of the
Epic:

- **Whole-Epic review.** The Issue is reviewed together with its parent Sub-Epic and Epic and the
  related Issues under the same Epic, so contracts, naming, data model, ubiquitous language, and NFR
  budgets stay consistent and nothing is duplicated or contradicted.
- **Blockers get fixed, not just filed.** Each blocker is handed to a fix subagent that edits and
  commits on the Issue's branch; the review re-runs until blockers are gone.
- **No infinite loops.** A fix round cap plus no-progress detection stops runaway loops; on
  non-convergence the skill writes a "decision needed" note on the Issue and asks the user.
- **Clean hand-off.** With zero blockers, a PR/MR is opened linked to the Issue and the user is
  asked to approve it; the actual merge is `/architect:merge-issue`.
- **Findings become knowledge.** Every review distills its findings into a persistent, project-wide
  knowledge base (`reports/backlog/shared-context/review-knowledge.md`) so recurring problems turn
  into guardrails that later planning (`/architect:export-backlog`) and implementation
  (`/architect:implement-backlog`) consult — the same issues are not re-introduced next time.

Runs against the **target project** (the one holding `reports/backlog/backlog-manifest.json` and the
tracked repository). It never edits nexus-architect itself.

## Decision Criteria

- **Item selection** — Use the item argument (`I1.2.3`, `#<iid>`, or URL). With none, list
  `status::doing` / `status::review` items (filtered to `--epic` when given) and confirm the choice
  via AskUserQuestion. Never review-and-fix an item the user hasn't confirmed (unless `--auto`).
- **Blocker vs non-blocker** — `[B]` blocks the PR/MR and triggers auto-fix. `[S]` (important) and
  `[Q]` (question) are recorded but do not block; surface them in the PR/MR description.
- **Convergence** — Stop the fix loop on zero blockers, on reaching `--max-fix-rounds` (default 3),
  or on no-progress (same blocker signature persists across two rounds, or the set oscillates).
  Never loop unbounded.
- **Outward-facing actions** — Opening a PR/MR and writing tracker comments are outward-facing;
  gate them on confirmation unless `--auto`, and skip them entirely on `--dry-run`.

## Prerequisites

| File / source | Required/Recommended | Produced by |
|---------------|----------------------|-------------|
| `reports/backlog/backlog-manifest.json` | Required | /architect:export-backlog |
| The Issue implemented on a working branch | Required | /architect:implement-backlog |
| `reports/backlog/shared-context/` (guardrails, coding-standards, decisions) | Recommended | /architect:implement-backlog |
| `reports/backlog/impl-log/<item>.md` | Recommended | /architect:implement-backlog |
| `glab` / `gh` authenticated for the target project | Required | user |

Read the output language from `work/pipeline-progress.json` (`options.output_language`, default
`en`); `--lang` overrides. Review docs and comments use that language; code, label keys, and IDs
stay in English.

## Severity & Verdict (shared with the review family)

- `[B]` blocker · `[S]` important · `[Q]` question.
- Verdict: **Mergeable** (0 blockers) · **Conditional** (N blockers, mergeable once cleared) ·
  **Redesign needed** (architecture-level problem — do not auto-fix; escalate to the user).

## Status Taxonomy (shared with export/implement-backlog)

`status::todo · status::doing · status::review · status::done · status::blocked`
(GitHub form `status:todo` …). This skill moves an Issue `doing → review` (PR/MR raised) or
`→ blocked` (non-convergence).

## Steps

### Step 0 — Load the backlog and resolve the platform
Read `reports/backlog/backlog-manifest.json`; if absent, stop and tell the user to run
`/architect:export-backlog` (and `/architect:implement-backlog`) first. Take platform
(`gitlab`/`github`), project (`owner/name` or GitLab path), group, and node `remote` URLs. Verify
auth non-destructively (`glab auth status` / `gh auth status`); if unauthenticated, stop and ask the
user to run `! glab auth login` / `! gh auth login`.

### Step 1 — Resolve the Issue and its working branch
Select the Issue (see Decision Criteria) and confirm. Resolve the working branch
`feature/<issue-id>-<slug>` (the shared branch contract with `/architect:implement-backlog`, which
created and committed to it) and the base branch (`--base`, else
the repo default). Determine the review round from existing files:
`reports/backlog/reviews/review-<issue>-round*.md` — none → round 1, else max+1.

### Step 2 — Gather the whole-Epic review context
Collect, and hold in view for the review:
- **The Issue** — What / How / acceptance criteria, its `impl-log/`, and the branch diff
  (`git diff <base>...HEAD`, or the platform diff API as in the gitlab-review reference:
  `glab api "projects/<enc>/merge_requests/.../diffs"` / `gh pr diff`). Verify claims against the
  actual latest commit, not just comments.
- **Parent Sub-Epic** (What / Key Results) and **parent Epic** (What / Why / Success Metrics) —
  does the change advance them without scope drift?
- **Related Issues** — siblings under the same Sub-Epic/Epic plus traceability-referenced Issues:
  check contract/naming/API-shape/data-model/ubiquitous-language consistency and detect
  duplication or conflict.
- **Shared-context pack** — `architecture-guardrails.md`, `coding-standards.md`, `nfr-budgets.md`,
  `decisions.md`.

### Step 3 — Generate the review
Write `reports/backlog/reviews/review-<issue>-round<R>.md` (required frontmatter, output language),
following the reference structure: **Overall verdict → Good → Findings → Conclusion**. Each finding
is tagged `[B]/[S]/[Q]` with file/location, why it matters, and a recommended fix. From round 2,
add a "Previous findings check" section verifying each prior `[B]` against the current code (guard
against "fixed in comment only"). Classify the verdict.

### Step 3b — Distill findings into the project knowledge base
Update `reports/backlog/shared-context/review-knowledge.md` (create it with frontmatter on first
use) so the review's findings become reusable project knowledge. This is a **distilled, deduplicated
catalog of generalized lessons**, not a copy of every finding — the per-round review docs remain the
raw record. For each `[B]`/`[S]` finding (skip pure `[Q]`), generalize it into a rule and:
- if an equivalent entry already exists, append the current Issue to its `occurrences` and bump the
  count (do not duplicate);
- otherwise add a new entry `KN-<n>` with: `category` (e.g. naming, api-contract, data-model,
  transaction, error-handling, nfr, security, testing), `rule` (the guardrail, imperative), the
  `anti-pattern` it prevents, `rationale`, a short code/So-What example, `severity` pattern, and
  `occurrences` (Issue refs, first-seen).
Group entries by category and keep the top recurring rules near the top. This file is local-only
(no remote write), so it is updated even on `--dry-run`. When a blocker fix in Step 4 also
establishes a cross-cutting decision, record that in `shared-context/decisions.md` as well.

### Step 4 — Blocker auto-fix loop (bounded)
If the verdict has `[B]` blockers and `--no-fix` is not set (and the verdict is not
**Redesign needed** — that escalates to the user directly):

1. For each blocker, **spawn a fix subagent** (Agent tool, `general-purpose`) with: the blocker
   description and location, the affected files, `coding-standards.md`, the relevant sibling
   contracts, and the project knowledge base (`review-knowledge.md`) so the fix does not re-introduce
   a known anti-pattern. Instruct it to make the minimal correct fix **on the working branch and
   commit it**, without touching unrelated code.
2. Re-run Step 3 (round + 1) against the new commits.
3. **Loop guard** — end the loop when:
   - blockers reach 0 → proceed to Step 5;
   - the round count reaches `--max-fix-rounds` (default 3); or
   - **no progress** — the same blocker signature (file + rule) survives two consecutive rounds, or
     the blocker set oscillates.
4. **On non-convergence** (guard tripped with blockers remaining): do **not** keep looping.
   - Append a comment to the Issue listing the unresolved blocker(s), what was tried each round, and
     an explicit **"Decision needed"** request with concrete options (e.g. accept-as-is / change
     approach / split the Issue / adjust acceptance criteria).
   - Set the Issue to `status::blocked`.
   - Ask the user via AskUserQuestion how to proceed, and stop.

### Step 5 — Raise the PR/MR (blockers = 0)
- Push the working branch. Open a PR/MR that links and closes the Issue (`Closes #<iid>`), with a
  body assembled from the Issue, the review summary, the acceptance-criteria checklist, and any
  remaining `[S]`/`[Q]` notes. GitLab: `glab mr create -s <branch> -t <base> --title … --description …`;
  GitHub: `gh pr create --base <base> --head <branch> --title … --body …`.
- Gate creation on user confirmation unless `--auto`. On `--dry-run`, stop after Step 3b (the
  review doc and the local knowledge-base update still happen) with no fixes, comments, or PR/MR —
  report what would happen.
- Set the Issue to `status::review`, comment the PR/MR URL on the Issue, and update the manifest
  node (`impl.status`, `pr: { url, iid/number }`).
- **Stop here** and ask the user to review and approve the PR/MR. Print the URL and state that
  `/architect:merge-issue` performs the merge after approval.

## Acceptance Criteria

- The review covers the Issue **and** its Sub-Epic, Epic, and related Issues; cross-item conflicts
  are reported (and fixed when they are blockers).
- The fix loop is bounded: it never runs past `--max-fix-rounds` or a no-progress condition, and
  non-convergence always ends in an Issue "Decision needed" comment + `status::blocked` + a user
  prompt.
- A PR/MR is opened only when blockers are 0, linked to the Issue, and the skill hands off for
  approval rather than merging.
- `--dry-run` performs no fixes, comments, or PR/MR creation (but the local knowledge base is still
  updated).
- Every review updates `reports/backlog/shared-context/review-knowledge.md` with distilled,
  deduplicated lessons; recurring findings accrue occurrences rather than duplicate entries.
- Review docs and comments trace to the code and reports — no fabricated findings.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:implement-backlog | Upstream — produces the branch, impl-log, and shared-context |
| /architect:merge-issue | Downstream — merges the PR/MR this skill raises, after approval |
| /architect:export-backlog | Source of the manifest and Epic/Sub-Epic/Issue hierarchy |
| /architect:review-consistency, /architect:review-synthesizer | Review lenses reused for the whole-Epic check |
