# Backlog Claims and Worktrees — the multi-team contract

One Epic, several people (or several agents) at once. Two Issues of one Epic delivered from one
checkout step on each other's branch; two people starting the same Issue waste a day. This
contract keeps both from happening: a **claim** says who holds an Issue, a **worktree** gives
each Issue its own checkout, an **integration branch** collects an Epic's merges before the
default branch sees them. The tool is `tools/lib/backlog_claims.py`; the file is
`reports/backlog/claims.json` — this checkout's record of what it claimed, under `reports/` and
therefore git-ignored. **The tracker is the fact other machines see**: a claim is mirrored there
as the Issue's assignee plus a `claim::<login>` label (GitLab scoped; GitHub `claim:<login>`),
and a run reads the tracker before the file (§ Claims).

## Claims

| Field | Meaning |
|-------|---------|
| `item` | The Issue's local id (`I1.2.3`) or `#<iid>` |
| `claimed_by` | `git config user.name` of whoever claimed, or `by=` — required when no name is configured; the tool never records "unknown" |
| `claimed_at`, `updated_at` | ISO8601 |
| `branch`, `worktree` | Where the work is — set by `worktree add`, or passed on the claim |
| `integration_branch` | The branch the Issue's PR/MR targets when the Epic uses one |
| `stolen_from` | The previous holder when the claim was taken with `steal=true` |
| `released_at`, `released_by`, `reason` | Set when the claim ends: `merged`, `stolen`, or the reason given |

Rules:

- **Claim before starting, and mirror it.** `/architect:deliver-backlog` claims each Issue as it
  selects it (`claim <item> integration=<branch>`); `/architect:implement-backlog` run by hand
  claims the Issue it is given. Right after the tool's claim the skill writes the tracker:
  assign the Issue to the claimant and add the label `claim::<login>` (`glab issue update <iid>
  --assignee <login> --label "claim::<login>"` / `gh issue edit <n> --add-assignee <login>
  --add-label "claim:<login>"`), where `<login>` is the tracker account the CLI is signed in as
  (`glab api user --jq .username` / `gh api user --jq .login`), created once like the `status::*`
  labels. A claim is an `ITEM_CLAIMED` audit event. On `--dry-run` nothing is written anywhere.
- **Read the tracker first.** Before forming its working set, a run lists the Epic's Issues with
  their `claim::*` labels (one `glab issue list --label` / `gh issue list --label` call per Epic,
  or the labels in the manifest refresh) and merges them with `list format=json`: an Issue
  carrying another login's label is **held**, whatever this checkout's file says; a local active
  claim whose label is gone was released elsewhere — release it locally with `reason=tracker`;
  a local claim with no label (the mirror write failed) is re-mirrored. The file never overrules
  the tracker.
- **Skip what someone else holds.** A run never starts an Issue another person holds; it says
  who holds it and moves on. `--steal` (deliver-backlog) or `steal=true` (the tool) takes it:
  the holder's claim is released as `stolen` (an `ITEM_RELEASED` event naming the taker), the new
  claim records `stolen_from`, and the skill moves the tracker label and assignee to the taker —
  for a colleague who left the Issue half done, with their consent or their absence, never
  silently.
- **Release on merge, release on giving up, keep on pause.** `/architect:merge-issue` releases
  the claim after the merge (`release <item> reason=merged`, an `ITEM_RELEASED` event) and
  removes the `claim::` label (the assignee stays as history). A run that gives an Issue up —
  the user chooses *skip this Issue* or *abort* at a blocked review or a failed sub-skill —
  releases it with `reason=aborted` (or `blocked`) and removes the label, so a colleague can take
  it. A run the user merely **halts** between steps keeps the claim and says so in its summary
  ("I1.2.3 stays held by you; `/architect:deliver-backlog --issue=I1.2.3` resumes it"): an active
  claim with a worktree is work in progress, one with no worktree and no branch is a person who
  said they would and has not started.
- **A worktree is the holder's.** `worktree add` on an Issue another person holds exits 3 like
  `claim`, unless `steal=true`.

## Worktrees

`worktree add <item> [root=<path>] [branch=<name>] [base=<branch>]` creates
`<root>/<item>` (`root` defaults to `../<project>-worktrees`, `--worktree-root` on the skills)
on `feat/<item>` from the project's current branch — a new branch, or the existing one — and
records both on the claim. The Issue's code is written there; the project's `reports/` and
`work/` stay where they are (the shared-context pack, the manifest, the registry and the audit
log are read and written by absolute path from the main checkout, never copied into a worktree).
`worktree remove <item>` deletes the checkout and keeps the branch — and refuses (exit 3, the
files listed) while the checkout has modified or untracked files, so a run never discards work
that was not committed; `force=true` discards it, and only a person says so. A linked worktree
is inside the repository for the purposes of `implement-backlog`'s Output Location checks.

## Integration branch

With `--integration-branch=<name>` on `/architect:deliver-backlog`, every Issue's PR/MR of the
Epic targets that branch (`review-issue --base`, `merge-issue --integration-branch`), the per-Issue
approval gate stays as it is, and the Epic ends with **one more gate**: the integration branch's
PR/MR into the default branch, approved by a person (`GATE_APPROVED`), after which the claims of
the Epic are released. Without the flag, PR/MRs target the default branch as before.

## Parallel delivery

`--parallel=N` on `/architect:deliver-backlog` dispatches up to N Issues of the working set at
once — only Issues with no dependency between them per the manifest's `depends_on` and no shared
files per the export's dependency notes — each as a foreground sub-agent in its own worktree,
three at a time like the pipeline's parallel groups. Each Issue's approval gate is still a stop;
the orchestrator collects the open PR/MRs and asks for the approvals in one batch.
