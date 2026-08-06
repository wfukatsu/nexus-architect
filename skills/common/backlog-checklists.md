# Backlog Checklist Contract

Shared by the backlog family: `/architect:export-backlog`, `/architect:implement-backlog`,
`/architect:review-issue`, `/architect:merge-issue`, `/architect:deliver-backlog`,
`/architect:capture-followup`.

Every Epic / Sub-Epic / Issue carries markdown checkboxes, and they are **live state**:
GitLab/GitHub render a task list as a progress counter, so a box left unticked after the work landed
under-reports progress to everyone reading the item, and a box ticked ahead of the work over-reports
it. Keeping them current is part of finishing a step, not a cosmetic extra.

## The two checklists

| Checklist | Lives in | One box per | Ticked by |
|-----------|----------|-------------|-----------|
| **Child task list** | Epic `## Sub-Epics`, Sub-Epic `## Issues` | child item, as `- [ ] #<iid> <title>` | `/architect:merge-issue`, when that child reaches `done` |
| **Acceptance criteria** | Issue `## Acceptance Criteria` | criterion, as `- [ ] <verifiable statement>` | `/architect:implement-backlog` (implemented) then `/architect:review-issue` (verified) |

Ownership is exclusive: the skill named above is the only one that flips that kind of box. An Issue
is not `done` until its PR/MR merges, so nothing before `merge-issue` ticks a parent's child box.

One more operation exists on the child task list: **appending a new unticked box**. When
`/architect:capture-followup` creates a follow-up Issue mid-delivery, it appends `- [ ] #<iid>
<title>` to the parent's `## Issues` (or `## Sub-Epics`) list — in place, idempotently (skip if
`#<iid>` is already listed), using the same edit mechanics below. On the native-Epic/sub-issue path
the hierarchy link replaces the append, as it replaces the list. That skill only ever *adds* an
unticked box; ticking it remains `merge-issue`'s alone.

## Rules

- **Emit them as checkboxes.** `export-backlog` writes `- [ ]` lines for both kinds; a criterion
  written as prose (or a Given/When/Then spread over several lines with no box) can never be ticked
  later. One box per criterion — a Given/When/Then scenario goes *inside* one box.
- **Tick on evidence, never on intent.** A box becomes `- [x]` only when something checkable shows
  it: a committed change plus its test/build, a review verdict confirming it, or a child's `done`
  transition. Anything unproven stays `- [ ]` and is named explicitly in the progress comment.
- **Edit in place, idempotently.** Read the current body, flip only the `[ ]` → `[x]` marker on the
  matched line, and write the body back. Match child boxes on `#<iid>`, criteria on their text.
  **Never regenerate a body from `backlog-manifest.json`** — that discards human edits. A box that is
  already `[x]` is a no-op.
  - GitLab issue: `glab issue view <iid> -F json` → `glab issue update <iid> -d <body>`
  - GitHub issue: `gh issue view <num> --json body` → `gh issue edit <num> --body-file -`
  - GitLab native Epic: `glab api "groups/<group>/epics/<iid>"` →
    `glab api --method PUT "groups/<group>/epics/<iid>" -f description=<body>`
- **Unticking is allowed, with a reason.** If a review, revert, or failing test shows a ticked
  criterion is not actually met, set it back to `- [ ]` and say why in the comment. An honest
  unticked box beats a tick that silently reverses.
- **Never tick a box to clear a gate.** Unmet criteria are reported to the user (and waived
  explicitly, in writing) — not ticked to make a check pass.
- **Native hierarchy links replace the child task list.** On the GitLab native-Epic path (and GitHub
  native sub-issues) the parent has no task list, so there is nothing to tick — the link is the
  progress source. Do not fabricate a duplicate list.
- **Checkboxes are output, not input.** Stage/selection decisions read the tracker `status::*` label
  and the manifest's `impl.status`; a box that disagrees is a defect for the owning skill to fix, not
  a state to resume from.
- **`--dry-run` never edits a body.** Report which boxes would flip.
