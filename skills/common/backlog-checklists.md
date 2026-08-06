# Backlog Checklist Contract

Shared by the backlog family: `/architect:export-backlog`, `/architect:implement-backlog`,
`/architect:review-issue`, `/architect:merge-issue`, `/architect:deliver-backlog`,
`/architect:capture-followup`.

Every Epic / Sub-Epic / Issue carries markdown checkboxes, and they are **live state**:
GitLab/GitHub render a task list as a progress counter, so a box left unticked after the work landed
under-reports progress to everyone reading the item, and a box ticked ahead of the work over-reports
it. Keeping them current is part of finishing a step, not a cosmetic extra.

Two kinds of state are tracked, and both are rendered in the bodies: **implementation state** —
the acceptance-criteria and child task-list checkboxes, ticked when the work is implemented and
its tests pass — and **delivery state** — each item's `## Delivery Status` section, whose status
line and stage checklist show how far the item has moved (implemented → reviewed → merged). The
machine-readable source of truth for delivery state stays in the **`status::*` labels and the
manifest's `impl.status`**; the section is a human-readable rendering of them. A Sub-Epic with
every child box ticked but a Delivery Status of `status::review` reads exactly as intended:
everything is implemented and tested, merges are pending.

## The three checklists

| Checklist | Lives in | One box per | Ticked by |
|-----------|----------|-------------|-----------|
| **Child task list** | Epic `## Sub-Epics`, Sub-Epic `## Issues` | child item, as `- [ ] #<iid> <title>` | `/architect:implement-backlog`, when that child's implementation **and tests** are complete (every acceptance criterion ticked); `/architect:review-issue` reconciles; `/architect:merge-issue` verifies at merge |
| **Acceptance criteria** | Issue `## Acceptance Criteria` | criterion, as `- [ ] <verifiable statement>` | `/architect:implement-backlog` (implemented, tests passing) then `/architect:review-issue` (verified) |
| **Delivery checklist** | every item's `## Delivery Status` | delivery stage (`Implemented` / `Reviewed` / `Merged`) | the skill that establishes the stage — see The Delivery Status section |

Ownership is exclusive: the skill named above is the only one that flips that kind of box. A child
box means **implemented and tested**, not merged: `implement-backlog` ticks it once all the Issue's
acceptance criteria are ticked with test evidence; `review-issue` unticks it (with the reason) when
a review round shows the implementation or its tests are not actually complete; `merge-issue` no
longer ticks in the normal flow — it **verifies** at merge, ticking only a box that was missed (the
green-CI, merged result is the evidence). The merge itself moves `status::done` / `impl.status`,
never the boxes — delivery state is read from labels, not from a task list.

One more operation exists on the child task list: **appending a new unticked box**. When
`/architect:capture-followup` creates a follow-up Issue mid-delivery, it appends `- [ ] #<iid>
<title>` to the parent's `## Issues` (or `## Sub-Epics`) list — in place, idempotently (skip if
`#<iid>` is already listed), using the same edit mechanics below. On the native-Epic/sub-issue path
the hierarchy link replaces the append, as it replaces the list. That skill only ever *adds* an
unticked box; ticking it remains `implement-backlog`'s (with `merge-issue` verifying at merge).

## The Delivery Status section

Every Epic / Sub-Epic / Issue body carries a `## Delivery Status` section so a reader can tell at
a glance how far the item has moved — in particular whether it is **merged**, which the
implementation checkboxes deliberately do not say. Format (authored unticked by `export-backlog`
and `capture-followup`; the status line mirrors the current tracker label):

```markdown
## Delivery Status

Status: `status::todo`

- [ ] Implemented — code committed, tests passing (all acceptance criteria ticked)
- [ ] Reviewed — review verdict Mergeable, PR/MR opened
- [ ] Merged — PR/MR merged, Issue closed
```

Epics and Sub-Epics carry two stages instead — `- [ ] Implemented — every child implemented and
tested` and `- [ ] Merged — every child merged (status::done)` — since "reviewed" is a per-Issue
stage.

- **The status line is a mirror, not a source.** Whichever skill transitions the tracker label
  also rewrites the `Status:` line to match; the label and `impl.status` remain authoritative, and
  a stale line is a defect for the transitioning skill to fix.
- **Stage ownership** follows the stage: `Implemented` is ticked by `implement-backlog` (and
  reconciled by `review-issue`, which unticks it with a reason when a round refutes completeness);
  `Reviewed` by `review-issue` when it opens the PR/MR; `Merged` by `merge-issue` after the merge.
  Parents' stage boxes roll up: `implement-backlog` ticks a parent's `Implemented` when the last
  child's implementation completes; `merge-issue` ticks a parent's `Merged` when the last child
  merges. Boxes are matched on their leading stage keyword and flipped in place.
- **Retrofit (existing items).** Items created before this contract have no `## Delivery Status`
  section. Any skill about to edit such a body first **appends the section**, initialized from the
  live tracker label and the evidence at hand (e.g. an Issue already `status::review` with all
  criteria ticked starts as `Implemented [x] / Reviewed [x] / Merged [ ]`), then makes its edit.
  This is the one case a skill adds a section to a body — everything else stays edit-in-place.
- **`export-backlog --update` must preserve it.** When `--update` syncs a body from the manifest,
  the remote item's `## Delivery Status` section (and every ticked box) is carried over, never
  overwritten with the manifest's creation-time body.

## Rules

- **Emit them as checkboxes.** `export-backlog` writes `- [ ]` lines for both kinds; a criterion
  written as prose (or a Given/When/Then spread over several lines with no box) can never be ticked
  later. One box per criterion — a Given/When/Then scenario goes *inside* one box.
- **Tick on evidence, never on intent.** A box becomes `- [x]` only when something checkable shows
  it: a committed change plus its passing test/build, a review verdict confirming it, or — for a
  child box — every acceptance criterion of that child ticked with test evidence. Anything unproven
  stays `- [ ]` and is named explicitly in the progress comment.
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
