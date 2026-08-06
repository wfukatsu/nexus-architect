---
description: |
  Capture follow-up work discovered during backlog delivery — deferred tasks, out-of-scope
  findings, doc drift, split-off scope, waived acceptance criteria — into a reviewable local
  queue, then register the approved entries as tracker Issues linked to the in-flight
  Sub-Epic / Epic and appended to backlog-manifest.json, so deferred work enters the
  /architect:deliver-backlog loop as status::todo instead of dying in prose.
  /architect:capture-followup [title] [--parent=<local_id|#iid>] [--from=<file|issue-ref>] [--queue-only] [--flush] [--dry-run] [--auto] [--lang=en|ja].
  With a title/--from, appends to the queue (and offers a flush); --queue-only stops after the
  append (the form the feeder skills use mid-run); --flush (or no args with a non-empty queue)
  reviews the queue and creates the Issues after an approval gate. Only runs when explicitly
  invoked.
model: sonnet
user_invocable: true
disable-model-invocation: true
---

# Follow-up Capture (Deferred Work → Backlog)

## Desired Outcome

Work discovered mid-delivery that cannot be done now stops disappearing into comments and review
prose. Instead it flows through three states, each durable:

- **Queued.** A `reports/backlog/followup-queue.md` entry records the task, its proposed parent,
  and where it was discovered — appendable at any point during `/architect:implement-backlog`,
  `/architect:review-issue`, or `/architect:merge-issue` without a remote write or an approval
  interruption.
- **Created.** After an explicit approval gate, each queued entry becomes a tracker Issue
  (`glab` / `gh`) labeled `status::todo`, linked to its parent Sub-Epic (or, explicitly, Epic),
  and appended to `reports/backlog/backlog-manifest.json` as a node the rest of the backlog
  family understands.
- **Delivered.** The new Issues are ordinary backlog Issues: `/architect:deliver-backlog` picks
  them up as `status::todo` with no special handling.

Runs against the **target project** (the one holding `reports/backlog/backlog-manifest.json` and
the tracked repository). It never edits nexus-architect itself.

## Decision Criteria

- **Parent selection precedence** — (1) `--parent=<local_id|#iid>` always wins. (2) Otherwise
  default to the parent Sub-Epic of the Issue currently in flight: the single `status::doing`
  Issue, resolved from the manifest's `impl.status` — when the tracker label and `impl.status`
  disagree, the tracker wins (same rule as `/architect:deliver-backlog`). (3) When zero or
  multiple Issues are `doing`, ask via AskUserQuestion. **Epic-direct attachment is allowed only
  explicitly** (`--parent=E<n>` or chosen in the dialog) — a cross-cutting follow-up may
  legitimately have no Sub-Epic home, but the default never silently picks the Epic.
- **Queue vs create** — Feeder skills always append with `--queue-only`; remote creation happens
  only past the Step 3 gate. Never create an Issue the user has not approved (unless `--auto`).
- **Fabrication ban** — The Issue body derives from the recorded finding (the queue entry, the
  `--from` source, or the user's words). Do not invent acceptance criteria, endpoints, or
  numbers; a follow-up whose "done" condition is unknown gets a single criterion restating the
  finding to resolve, marked `TBD`.
- **Follow-ups are not an escape hatch** — A `[B]` blocker, a failing preflight check, or an
  unmet criterion needed for the *current* Issue's merge is handled by the owning skill's own
  loop; only genuinely deferrable work belongs here.

## Prerequisites

| File / source | Required/Recommended | Produced by |
|---------------|----------------------|-------------|
| `reports/backlog/backlog-manifest.json` | Required | /architect:export-backlog |
| `glab` / `gh` authenticated for the target project | Required (flush only) | user |
| `reports/backlog/followup-queue.md` | Optional (created on first capture) | this skill + feeder skills |

Read the output language from `work/pipeline-progress.json` (`options.output_language`, default
`en`); `--lang` overrides. Queue entries, Issue titles/bodies, and reports use that language;
label keys, local IDs, and traceability IDs stay in English.

## Follow-up ID & Manifest Contract

Follow-up Issues live in their **own local-ID namespace** so they can never collide with the
positional IDs `/architect:export-backlog` synthesizes from reports:

- **Format**: `<parent_local_id>.F<n>` — e.g. `SE1.2` → `I1.2.F1`, `I1.2.F2`; an Epic-direct
  follow-up under `E1` is `I1.F1`. The `I` prefix marks the level (always `issue`); the `F<n>`
  suffix marks the namespace.
- **Allocation at create time** (Step 4, not at queueing): `n` = max existing `F` index among the
  parent's children in the manifest, plus 1. Queued-but-not-created entries reserve nothing, so
  dropping one leaves no gap.
- **Collision rule** — `export-backlog --update` re-synthesizes only positional IDs
  (`I1.2.1 … I1.2.n`); it must never assign, renumber, or reassign a `*.F<n>` node or any node
  carrying `origin` (stated on its side too). The two namespaces are disjoint by construction.

The manifest node uses the exact shape `export-backlog` defines, plus one new field, `origin`:

```json
{
  "local_id": "I1.2.F1",
  "level": "issue",
  "title": "Extract retry policy into shared config",
  "body": "## How\n…\n## Acceptance Criteria\n- [ ] …\n## References\n…",
  "labels": ["type:issue", "status::todo", "followup", "domain:payments"],
  "parent_local_id": "SE1.2",
  "source_reports": ["reports/backlog/impl-log/I1.2.3.md"],
  "traceability": ["NFR-03"],
  "origin": {
    "discovered_in": "I1.2.3",
    "source": "implement",
    "reference": "reports/backlog/impl-log/I1.2.3.md#finding-2",
    "queued_at": "2026-08-06T02:00:00Z"
  },
  "remote": { "id": 401, "iid": 57, "url": "…", "created_at": "…" }
}
```

- `origin.source` ∈ `implement | review | merge | manual`; `origin.discovered_in` is the local ID
  (or `#<iid>`) of the item being worked when the task surfaced; `origin.reference` points at the
  recorded finding (impl-log anchor, review doc, comment URL).
- `labels` is the **creation seed, not live state** (the standing manifest rule): seeded with
  `type:issue` (GitLab fallback: `type::issue`), `status::todo`, `followup`, and the `domain:` /
  `tier:` labels inherited from the parent Sub-Epic. Status advances on the tracker and in
  `impl.status`, never here.
- The node is appended to the manifest **immediately after each successful create**, with
  `remote` filled in, so an interrupted flush resumes cleanly.

This contract is asserted as behaviour by `skills/capture-followup/followup-contract.test.py`
(F-index allocation, namespace disjointness, node shape, parent resolution) — run it after
changing this section.

## Queue File Contract

`reports/backlog/followup-queue.md` — markdown (not JSON) so the user can hand-edit entries
before a flush. Created on first capture with the required YAML frontmatter (`title`,
`schema_version: 1`, `phase`, `skill: capture-followup`, `generated_at`, `input_files`). One
section per entry:

```markdown
## FQ-3: Extract retry policy into shared config

- status: queued            <!-- queued | created | dropped -->
- proposed_parent: SE1.2
- origin: implement · I1.2.3 · reports/backlog/impl-log/I1.2.3.md#finding-2
- queued_at: 2026-08-06T02:00:00Z

### Draft body

## How
…
## Acceptance Criteria
- [ ] …
## References
…
```

- `FQ-<n>` is a queue-local sequence number (max + 1 on append); it is **not** the backlog local
  ID — that is allocated at create time.
- Appended by this skill and by the feeder skills (via `--queue-only`); a feeder appends and
  moves on — it never flushes.
- **Edited in place, never regenerated**: a flush updates only the touched entries' `status`
  (`queued` → `created`, with the created URL and local ID on the entry; user-dropped entries →
  `dropped` with the reason). Hand edits to other entries survive.
- Entries with `status: created` or `dropped` are inert history; only `queued` entries
  participate in a flush.

## Sub-Agent Execution & Model Assignment

Thin sonnet orchestrator; one delegated step:

| Step | Delegated work | Sub-agent (model) | Returns to orchestrator |
|------|----------------|-------------------|-------------------------|
| 1 | Draft the Issue body (How / criteria / References) from the recorded finding | **haiku** | drafted body text |

The orchestrator keeps everything stateful and outward-facing: manifest and platform resolution,
parent-selection dialogue (AskUserQuestion), queue-file edits, the approval gate, all
`glab`/`gh` writes, and the manifest write-back. No opus: the only judgment call (parent choice)
is user-gated.

## Steps

### Step 0 — Load the backlog and resolve the platform
Read `reports/backlog/backlog-manifest.json`; if absent, stop and tell the user to run
`/architect:export-backlog` first. Take the platform (`gitlab`/`github`), project, group, and
node `remote` URLs. When the invocation will (or may) flush, verify auth non-destructively
(`glab auth status` / `gh auth status`); if unauthenticated, stop and ask the user to run
`! glab auth login` / `! gh auth login`. A pure `--queue-only` capture needs no auth — do not
block it on a missing login.

### Step 1 — Capture (append to the queue)
Skip when there is no new task to capture (bare `--flush`). Otherwise:
1. **Normalize the input** — the `title` argument, the content of `--from=<file|issue-ref>`
   (e.g. an impl-log finding, a review doc section, a tracker comment), or a short interactive
   dialogue when neither is given.
2. **Resolve the proposed parent** per Decision Criteria (record it on the entry; the flush
   re-confirms it).
3. **Draft the body** — delegate to a **haiku sub-agent**: `## How` (the approach, from the
   finding), `## Acceptance Criteria` (unticked `- [ ]` boxes, one per verifiable criterion —
   derived from the finding, `TBD` when unknown, never invented), `## References` (the
   `origin.reference` plus any traceability IDs carried by the finding).
4. **Append** the `FQ-<n>` entry to `reports/backlog/followup-queue.md` (creating the file with
   frontmatter on first use).

With `--queue-only`, stop here and report the entry. Otherwise offer to continue to the flush.

### Step 2 — Review the queue
List the `queued` entries (FQ id, title, proposed parent, origin). Let the user drop or amend
entries via AskUserQuestion (amendments can also be made by hand-editing the file and re-running).
Under `--auto`, skip the dialogue and take the queue as-is. If nothing is `queued`, say so and
stop.

### Step 3 — Approval gate (required — do not skip)
Creating remote work items is outward-facing and hard to reverse. Present a concise summary —
each entry's title, target parent (with its remote URL), and the labels to be attached — and
**ask for explicit approval** via AskUserQuestion before any create call (`--auto` adopts the
queue without asking). On `--dry-run`, stop here and report what *would* be created; the queue
file keeps any Step 1 append, but no remote write and no manifest change happens.

### Step 4 — Create and link (idempotent)
For each approved `queued` entry (skip any that already carries a created URL):
1. **Allocate the local ID** per the Follow-up ID contract (`<parent>.F<max+1>`).
2. **Create the Issue** — GitLab: `glab issue create -R <project> -t "…" -d "…" -l "…"`;
   GitHub: `gh issue create -R <owner/name> -t "…" -b "…" -l "…"`. Labels per the manifest
   contract (`type:issue` / `type::issue`, `status::todo` / `status:todo`, `followup`,
   inherited `domain:` / `tier:`). Create missing labels once, as `export-backlog` does.
3. **Link to the parent**, matching the hierarchy scheme `export-backlog` used:
   - GitLab native Epics: `glab api --method POST
     "groups/<group>/epics/<parent_epic_iid>/issues/<issue_id>"` — the link is the hierarchy;
     no task-list edit.
   - GitLab label fallback / GitHub task-list scheme: append an **unticked** `- [ ] #<iid>
     <title>` box to the parent's `## Issues` (or `## Sub-Epics` for an Epic-direct follow-up)
     via the in-place edit mechanics of @skills/common/backlog-checklists.md — read the body,
     append the one line, write it back; skip if `#<iid>` is already listed; never regenerate
     the body from the manifest. Ticking the box remains `/architect:merge-issue`'s.
   - GitHub native sub-issues (enhancement): attempt `addSubIssue` GraphQL only if
     `export-backlog` recorded that it works; on any error, silently fall back to the task list.
4. **Write back immediately** — append the node (with `origin` and `remote`) to
   `backlog-manifest.json`, and update the queue entry to `status: created` with the URL and
   local ID, before moving to the next entry.

### Step 5 — Result (immediate output)
Write `reports/backlog/followup-result.md` (required frontmatter): a table of the created
Issues — local ID, title, URL, parent, origin — plus entries skipped/dropped/failed and why.
Print the created URLs and note that `/architect:deliver-backlog` will pick the new Issues up as
`status::todo` in its next working set.

## Acceptance Criteria

- Every captured task has a durable `FQ-<n>` queue entry with a proposed parent and an `origin`
  trail; `--queue-only` performs no remote write and requires no auth.
- No remote write happens before the Step 3 gate, under `--dry-run`, or for an entry the user
  dropped.
- Every created Issue is linked to its parent (native link or an unticked child box appended in
  place), labeled `status::todo` + `followup`, and appended to `backlog-manifest.json` with
  `origin` and `remote` — immediately per create, so an interrupted flush resumes.
- Local IDs use the `F` namespace and collide with nothing: positional IDs are untouched, and
  allocation is max-F-plus-1 under the parent (asserted by `followup-contract.test.py`).
- Parent bodies are edited in place only — one appended box, no regeneration, no ticking.
- Issue bodies derive from the recorded finding — no fabricated criteria, endpoints, or numbers.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:export-backlog | Namespace peer — owns positional IDs and the manifest schema this skill extends |
| /architect:implement-backlog | Feeder — queues out-of-scope stops, doc drift, larger inconsistencies |
| /architect:review-issue | Feeder — queues split-off scope and remaining `[S]`/`[Q]` findings |
| /architect:merge-issue | Feeder — queues acceptance criteria waived at the merge gate |
| /architect:deliver-backlog | Consumer — delivers the created Issues as ordinary `status::todo` work |
