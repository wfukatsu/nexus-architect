# Backlog Claims and Worktrees — the multi-team contract

One Epic, several people (or several agents) at once. Two Issues of one Epic delivered from one
checkout step on each other's branch; two people starting the same Issue waste a day. This
contract keeps both from happening: a **claim** says who holds an Issue, a **worktree** gives
each Issue its own checkout, an **integration branch** collects an Epic's merges before the
default branch sees them. The tool is `tools/lib/backlog_claims.py`; the file is
`reports/backlog/claims.json` (local, like the manifest; never a remote write).

## Claims

| Field | Meaning |
|-------|---------|
| `item` | The Issue's local id (`I1.2.3`) or `#<iid>` |
| `claimed_by` | `git config user.name` of whoever claimed, or `by=` |
| `claimed_at`, `updated_at` | ISO8601 |
| `branch`, `worktree` | Where the work is — set by `worktree add`, or passed on the claim |
| `integration_branch` | The branch the Issue's PR/MR targets when the Epic uses one |
| `stolen_from` | The previous holder when the claim was taken with `steal=true` |
| `released_at`, `released_by`, `reason` | Set when the claim ends: `merged`, `stolen`, or the reason given |

Rules:

- **Claim before starting.** `/architect:deliver-backlog` claims each Issue as it selects it
  (`claim <item> integration=<branch>`); `/architect:implement-backlog` run by hand claims the
  Issue it is given. A claim is a `ITEM_CLAIMED` audit event.
- **Skip what someone else holds.** A run never starts an Issue another person holds; it says
  who holds it and moves on. `--steal` (deliver-backlog) or `steal=true` (the tool) takes it,
  recording the previous holder — for a colleague who left the Issue half done, with their
  consent or their absence, never silently.
- **Release on merge.** `/architect:merge-issue` releases the claim after the merge
  (`release <item> reason=merged`, an `ITEM_RELEASED` event); a run that gives an Issue up
  releases it with the reason. An active claim with no worktree and no branch is a person who
  said they would and has not started.
- **The claims file is state, not the tracker.** The tracker's assignee is the public fact; the
  claim is the working fact — the two are reconciled by the person, not by a tool.

## Worktrees

`worktree add <item> [root=<path>] [branch=<name>] [base=<branch>]` creates
`<root>/<item>` (`root` defaults to `../<project>-worktrees`, `--worktree-root` on the skills)
on `feat/<item>` from the project's current branch — a new branch, or the existing one — and
records both on the claim. The Issue's code is written there; the project's `reports/` and
`work/` stay where they are (the shared-context pack, the manifest, the registry and the audit
log are read and written by absolute path from the main checkout, never copied into a worktree).
`worktree remove <item>` deletes the checkout and keeps the branch. A linked worktree is inside
the repository for the purposes of `implement-backlog`'s Output Location checks.

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
