---
description: |
  Implement a backlog item (Issue / Sub-Epic / Epic) created by /architect:export-backlog, keeping
  everything consistent across the whole Epic. Reads the parent Epic and the sibling Sub-Epics /
  Issues under the same Epic, cross-checks a shared engineering-context pack (architecture, coding
  standards, ubiquitous language, NFR budgets), writes code under generated/, appends progress
  notes to the Epic / Sub-Epic / Issue, and runs a lightweight + on-demand consistency review for
  whole-Epic optimization.
  /architect:implement-backlog [item] [--epic=<id>] [--build-context] [--review-epic[=<id>]] [--out=<path>] [--dry-run] [--auto] [--lang=en|ja].
  With no item, picks the items flagged status::doing and confirms with the user before proceeding.
  Only runs when explicitly invoked.
model: opus
user_invocable: true
disable-model-invocation: true
---

# Backlog Implementation (Epic-Consistent)

## Desired Outcome

Implement a selected backlog item while keeping the whole Epic coherent:

- **Consistency across the Epic.** Every change is made with the parent Epic (What / Why / Key
  Results) and all sibling Sub-Epics and Issues in view, reusing their contracts and avoiding
  conflicts (naming, API shapes, data model, ubiquitous language, NFR budgets).
- **Visible progress.** The executed work is appended back onto the Epic / Sub-Epic / Issue on the
  tracker (comments + status labels), and mirrored to a local implementation log.
- **Whole-Epic optimization.** A lightweight consistency review runs after each item, and an
  on-demand roll-up review spans the whole Epic.
- **Shared source of truth.** Cross-cutting rules (architecture, coding standards, ubiquitous
  language, data contracts, NFR budgets) are assembled once into a referenceable pack and consulted
  on every item, with new cross-cutting decisions recorded so later items stay aligned.

Code lands under `generated/{service}/`; the tracker and `reports/backlog/` hold the progress trail.
This skill runs against the **target project** (the one holding `reports/` and the backlog), the same
way other architect skills operate — it never edits nexus-architect itself.

## Decision Criteria

- **Item selection** — Use the item given as an argument (local id like `I1.2.3`, `#<iid>`, or a
  URL). With no argument, list items labeled `status::doing`, and confirm the pick with the user via
  AskUserQuestion. If none are `doing`, offer `status::todo` / ready items under the active Epic.
  Never start implementing an item the user has not confirmed (unless `--auto`).
- **Scope** — An **Issue** is implemented directly. A **Sub-Epic** drives its Issues in dependency
  order, confirming each. An **Epic** drives its Sub-Epics. Default focus is Issue-level.
- **Consistency over local speed** — When a sibling already defines a contract, interface, or naming
  the item depends on, reuse it. Do not introduce a competing pattern; if the existing one is wrong,
  raise it as a finding rather than silently diverging.
- **Fabrication ban** — Implement only what the item's acceptance criteria and the referenced design
  reports specify. Do not invent requirements, endpoints, or numbers.

## Prerequisites

| File / source | Required/Recommended | Produced by |
|---------------|----------------------|-------------|
| `reports/backlog/backlog-manifest.json` | Required | /architect:export-backlog |
| The tracker (GitLab/GitHub) with the Epic/Sub-Epic/Issue items | Required | /architect:export-backlog |
| `reports/` design & product artifacts (referenced by item traceability IDs) | Required | product / architect pipelines |
| `glab` / `gh` authenticated for the target project | Required | user |

Read the output language from `work/pipeline-progress.json` (`options.output_language`, default
`en`); `--lang` overrides it. Generated report/comment text uses that language; code identifiers,
label keys, and traceability IDs stay in English (per the repo language rule).

## Status Taxonomy (shared with export-backlog)

Scoped labels on GitLab, plain labels on GitHub:
`status::todo` · `status::doing` · `status::review` · `status::done` · `status::blocked`
(GitHub form: `status:todo` …). If the labels do not exist, create them once. Default selection
target is `doing`.

## Steps

### Step 0 — Load the backlog and resolve the platform
Read `reports/backlog/backlog-manifest.json`. If it is missing, stop and tell the user to run
`/architect:export-backlog` first. From the manifest, take the platform (`gitlab`/`github`), the
project (`owner/name` or GitLab path), the group (for GitLab epics), and each node's `remote` URL.
Verify auth non-destructively (`glab auth status` / `gh auth status`); if unauthenticated, stop and
ask the user to run `! glab auth login` / `! gh auth login`.

### Step 1 — Ensure the shared engineering-context pack (bundled)
The referenceable location is `reports/backlog/shared-context/`. (Re)build it when it is absent,
when `--build-context` is passed, or when a source report is newer than the pack. Derive each file
from the product/architect reports (skip inputs that don't exist), with the required YAML
frontmatter:

| File | Derived from |
|------|--------------|
| `architecture-guardrails.md` | `reports/03_domain/architecture.md`, `reports/03_design/target-architecture.md`, `tech-stack-fitness.md`, `context-map.md` |
| `coding-standards.md` | language/framework decisions; ScalarDB projects add `@rules/scalardb-coding-patterns.md`, `@rules/scalardb-java-best-practices.md`, `@rules/spring-boot-integration.md`; naming (kebab-case files), exception/retry policy |
| `ubiquitous-language.md` | `reports/03_domain/ubiquitous-language.md` or `reports/01_analysis/ubiquitous-language.md` |
| `data-contracts.md` | `reports/02_spec/data-model.md`, `reports/03_design/scalardb-schema.md` |
| `nfr-budgets.md` | `reports/04_quality/nfr.md`, `sla.md` |
| `decisions.md` | running **ADR-lite log** of cross-cutting decisions made during implementation (appended over time — starts empty) |
| `review-knowledge.md` | project-wide **review knowledge base** (recurring findings → guardrails), maintained by `/architect:review-issue` — consulted here, **not regenerated** |

`decisions.md` and `review-knowledge.md` are append-only logs (the latter is written by
`/architect:review-issue`); the (re)build only regenerates the derived files above them. This pack is
what every item is cross-checked against — in particular, `review-knowledge.md` carries the lessons
from previous reviews so the same problems are not implemented again.

### Step 2 — Select the work item (confirm with the user)
1. If an item argument is present, resolve it in the manifest.
2. Otherwise query `status::doing` items (`glab issue list -l "status::doing"` / `gh issue list -l "status:doing"`),
   filtered to `--epic` when given, and present them via AskUserQuestion for the user to choose.
   If none are `doing`, offer `status::todo` / ready items under the active Epic.
3. Confirm the selection before proceeding, unless `--auto`.
4. Determine scope (Issue / Sub-Epic / Epic per Decision Criteria) and, for a Sub-Epic/Epic, the
   ordered list of child items to work through (confirming each in turn).

### Step 3 — Assemble the consistency context for the item
Gather, and keep in view for the rest of the run:
- **Parent Epic** — What / Why / Success Metrics / Key Results.
- **Same-Epic siblings** — every Sub-Epic and Issue under the same Epic: titles, status, acceptance
  criteria, and any decisions already recorded in their tracker comments and `impl-log/`. Use these
  to reuse interfaces and avoid conflicts.
- **Shared-context pack** from Step 1 — including `review-knowledge.md`, the accumulated review
  findings; treat its rules as guardrails so past mistakes are not repeated.
- **Source design reports** referenced by the item's traceability IDs (`FEAT-`, `CTX-`, `API-`,
  `NFR-`, …).

### Step 4 — Mark start and plan the item
Create (or reuse, if it already exists) the working branch **`feature/<issue-id>-<slug>`** from the
base branch — this branch name is the **shared contract** with `/architect:review-issue` and
`/architect:merge-issue`, which resolve the same name to review and merge the work. Then set the
item's status to `status::doing` and append a progress comment ("Implementation started")
containing a mini-plan: the files to add/change under `generated/`, the interface/contract (aligned
to siblings + ubiquitous language + `coding-standards.md`), and the tests. Check the mini-plan
against `review-knowledge.md` so a lesson from a previous review is not re-implemented as a fresh
finding. Present the mini-plan and confirm, unless `--auto`. On `--dry-run`, do not write the
label/comment — report what would change.

### Step 5 — Implement
On the working branch, write code to `generated/{service}/` (override with `--out`), following
`coding-standards.md`, reusing/aligning sibling contracts, and satisfying the item's acceptance
criteria. Generate tests following the `/architect:generate-test-specs` conventions when the item
warrants them. Apply the relevant `@rules/*` (e.g. ScalarDB patterns) when the project uses them.
Reuse existing generated code rather than duplicating it. **Commit the changes to the working
branch** in coherent units, each commit message referencing the Issue (e.g. `feat: … (#<iid>)`) —
uncommitted work cannot be reviewed or merged downstream.

### Step 6 — Review (lightweight + on-demand)
1. **Self-review** — against the item's acceptance criteria and the shared guardrails.
2. **Epic-consistency check** — confirm the change does not conflict with sibling Issues' contracts
   or recorded decisions (naming, API shapes, data model, ubiquitous language, NFR budgets). Fix
   small inconsistencies; surface larger ones as findings on the item and, if needed, on the Epic.
3. **Record cross-cutting decisions** — any new decision that affects other items is appended to
   `shared-context/decisions.md`, closing the consistency loop.
4. **On-demand Epic roll-up** — `--review-epic[=<id>]` runs a consolidated review across all Issues
   under the Epic (coherence, gaps, duplicated work, contract drift) and writes
   `reports/backlog/epic-review-<epic>.md`. The **automatic** trigger for this review lives in
   `/architect:merge-issue`: it invokes (or recommends) `--review-epic` when the last Issue of a
   Sub-Epic is merged — a single trigger authority, so it does not also fire from here.

### Step 7 — Record progress (append to the items)
Append the executed work back onto the tracker and mirror it locally. On `--dry-run`, stop before
any remote write and report the intended changes.
- **Issue** — comment with what was implemented (files, key decisions, deviations), the
  acceptance-criteria checklist status, and the review result; transition status to
  **`status::review` at most**. `status::done` is owned by `/architect:merge-issue` — an Issue is
  done only when its PR/MR has merged, so this skill never sets `done` (that would silently drop the
  Issue out of the review → PR/MR → merge flow).
- **Sub-Epic** — comment with a roll-up (progress and notable decisions). Sub-Epic `status::done`
  is likewise set by `/architect:merge-issue` when its last Issue merges.
- **Epic** — comment with a progress roll-up and any cross-cutting decisions.
- Mirror the appended notes to `reports/backlog/impl-log/<item>.md` (with frontmatter), and update
  the node in `backlog-manifest.json` with `impl: { status, files, decisions, updated_at }`.

### Step 8 — Continue
Offer the next `doing` / `todo` item under the same Epic (confirm before starting) or stop.

## Acceptance Criteria

- The item is implemented against the parent Epic and its siblings; no contract conflict is left
  unaddressed (fixed or surfaced as a finding).
- Every implemented item ends with a progress comment on its Issue and a status-label transition,
  mirrored in `reports/backlog/impl-log/`.
- The shared-context pack exists and was consulted — including `review-knowledge.md`, so known
  review findings are not reintroduced; any new cross-cutting decision is recorded in `decisions.md`.
- No fabricated requirements/endpoints/numbers — everything traces to acceptance criteria or a
  referenced report.
- `--dry-run` performs no remote writes and no code output; it only reports intended changes.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:export-backlog | Upstream — creates the backlog + manifest this skill consumes |
| /architect:design-implementation | Input source (How specs for Issues) |
| /architect:generate-scalardb-code | Reference for `generated/{service}/` output conventions |
| /architect:generate-test-specs | Reference for test generation |
| /architect:review-consistency, /architect:review-synthesizer | Review lenses reused by the Epic roll-up |
