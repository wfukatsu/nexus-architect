---
description: |
  Implement a backlog item (Issue / Sub-Epic / Epic) created by /architect:export-backlog, keeping
  everything consistent across the whole Epic. Reads the parent Epic and the sibling Sub-Epics /
  Issues under the same Epic, cross-checks a shared engineering-context pack (architecture, coding
  standards, ubiquitous language, NFR budgets), writes code into the target project's real source
  tree (never the git-ignored generated/), updates the README/docs for the changed surface via
  /architect:generate-docs, appends progress notes to the Epic / Sub-Epic / Issue, and runs a
  lightweight + on-demand consistency review for whole-Epic optimization.
  /architect:implement-backlog [item] [--epic=<id>] [--build-context] [--review-epic[=<id>]] [--out=<path>] [--confirm-versions|--no-confirm-versions] [--refresh-versions] [--dry-run] [--auto] [--lang=en|ja].
  With no item, picks the items flagged status::doing and confirms with the user before proceeding.
  Runs as a thin orchestrator that delegates heavy steps to model-tiered sub-agents
  (haiku/sonnet/opus) to minimize token cost. Only runs when explicitly invoked.
model: sonnet
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
- **Docs that ship with the code.** The README(s) and `docs/` pages covering the changed surface
  are updated on the same branch, so code and documentation are reviewed and merged together.
- **Whole-Epic optimization.** A lightweight consistency review runs after each item, and an
  on-demand roll-up review spans the whole Epic.
- **Shared source of truth.** Cross-cutting rules (architecture, coding standards, ubiquitous
  language, data contracts, NFR budgets) are assembled once into a referenceable pack and consulted
  on every item, with new cross-cutting decisions recorded so later items stay aligned.

Code lands in the target project's **source tree** (see Output Location); the tracker and
`reports/backlog/` hold the progress trail. This skill runs against the **target project** (the one
holding `reports/` and the backlog), the same way other architect skills operate — it never edits
nexus-architect itself.

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
- **Output location** — Code written here is a **deliverable**: it is committed, reviewed in a
  PR/MR, and merged. It therefore belongs in the target project's real source tree, **not** in
  `generated/`, which the output structure contract (@templates/output-structure.md) reserves for regenerable
  pipeline output and which target projects commonly git-ignore alongside `reports/` and `work/`.
  See Output Location for how the source root is resolved and verified.

## Output Location

Resolve the **source root** once per item, in this precedence:

1. `--out=<path>` — explicit override, always wins.
2. `source_root` recorded in `shared-context/decisions.md` by a previous item — reuse it so every
   item under the Epic writes to the same place.
3. The existing repo layout — an already-present service/module directory matching the item's
   service (e.g. `services/<service>/`, `apps/<service>/`, or a build-tool root such as
   `settings.gradle`/`pom.xml`/`pnpm-workspace.yaml` member).
4. Greenfield repo with no source yet — propose `services/{service}/` (service naming per
   `architecture-guardrails.md`) and confirm with the user via AskUserQuestion, unless `--auto`.

The resolved root must satisfy two checks before any code is written:

- **Not git-ignored** — `git check-ignore -q <source_root>` must exit **1** (no ignore rule
  matches). Exit 0 means the path is ignored, so `git add` would silently stage nothing and the
  downstream review → PR/MR → merge chain would break on an empty commit; stop and report the
  matching rule (`git check-ignore -v <source_root>`) rather than writing code into it. Any other
  exit status is a git error — surface it instead of assuming the path is safe.
- **Inside the repo** — the root resolves within the target project's git worktree.

Record the resolved root as a `source_root` decision in `shared-context/decisions.md` the first time
it is established. Pass `--out=generated/<service>/` explicitly when the intent genuinely is
throwaway scaffolding rather than merge-bound work.

The rules in this section are asserted as behaviour by
`skills/implement-backlog/output-location.test.sh` (the ignore gate, the working-branch commit, and
empty-commit detection, on a scratch repository) — run it after changing them.

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

## Sub-Agent Execution & Model Assignment

This skill runs as a **thin orchestrator (sonnet)** that delegates the heavy steps to sub-agents
(Agent/Task tool; see @skills/common/sub-agent-patterns.md), each pinned to the cheapest model tier
that can do the job. Two rules keep token cost minimal:

- **Context protection** — the orchestrator never bulk-reads design reports, sibling Issues, or
  the produced code itself. Sub-agents read them and return compact digests; the orchestrator holds
  only the manifest, the digests, the mini-plan, and the tracker state.
- **Cheapest-capable tier** — haiku for mechanical transforms, sonnet for structured generation and
  analysis, opus **only** for judgment (planning against Epic-wide contracts, consistency
  verdicts). Escalate a delegated step one tier only when the item is judgment-heavy (ambiguous
  contracts, distributed-transaction/2PC design, cross-service data ownership); never use opus for
  work a cheaper tier can do.

| Step | Delegated work | Sub-agent (model) | Returns to orchestrator |
|------|----------------|-------------------|-------------------------|
| 1 | Derive each shared-context file from its source reports | one **sonnet** agent per file, in parallel | file written + 1-line summary |
| 3 | Read parent Epic, siblings, and referenced design reports | Explore (**haiku**) | consistency digest: contracts, naming, prior decisions, guardrails |
| 4 | Draft the mini-plan against the digest + `review-knowledge.md` | **opus** | mini-plan (files, interface/contract, tests) |
| 5 | Implement code + tests per the approved mini-plan | **sonnet**, one per coherent unit | changed-file list + self-review notes |
| 5b | Update README/`docs/` for the implemented code (`/architect:generate-docs`) | **sonnet** (its own orchestrator; delegates internally) | doc files written + drift findings |
| 6-2 | Epic-consistency verdict on the resulting diff | **opus** | pass / findings list |
| 6-4 | Whole-Epic roll-up review (`--review-epic`) | **opus** | `epic-review-<epic>.md` |
| 7 | Draft progress comments + mirror to `impl-log/` | **haiku** | drafted comment/log text |

The orchestrator itself keeps only the cheap, stateful work: manifest/platform resolution, item
selection dialogue (AskUserQuestion), branch and label operations, `glab`/`gh` writes, and gating
(user confirmations, `--dry-run`). Each sub-agent prompt must include only the digest and the
specific inputs its step needs — never the full shared-context pack or full report bodies.

## Steps

### Step 0 — Load the backlog and resolve the platform
Read `reports/backlog/backlog-manifest.json`. If it is missing, stop and tell the user to run
`/architect:export-backlog` first. From the manifest, take the platform (`gitlab`/`github`), the
project (`owner/name` or GitLab path), the group (for GitLab epics), and each node's `remote` URL.
Verify auth non-destructively (`glab auth status` / `gh auth status`); if unauthenticated, stop and
ask the user to run `! glab auth login` / `! gh auth login`.

### Step 1 — Ensure the shared engineering-context pack (bundled)
The referenceable location is `reports/backlog/shared-context/`. (Re)build it when it is absent,
when `--build-context` is passed, or when a source report is newer than the pack. **Delegate each
derived file to a parallel sonnet sub-agent** (one per file; the sub-agent reads the source reports
and writes the file, returning only a 1-line summary). Derive each file from the product/architect
reports (skip inputs that don't exist), with the required YAML frontmatter:

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
**Delegate the gathering to an Explore sub-agent (haiku)** that reads the sources below and returns
a compact **consistency digest** (contracts and interfaces already defined, naming, prior
decisions, applicable guardrails, acceptance criteria). The orchestrator keeps the digest — not the
source documents — in view for the rest of the run:
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
`/architect:merge-issue`, which resolve the same name to review and merge the work.

Then **resolve and verify the source root** per Output Location, before drafting the plan: apply the
precedence, run the `git check-ignore` and in-worktree checks, and stop with the offending ignore
rule if the root is ignored — the plan must not name files the downstream chain cannot commit. On
first resolution, record it as a `source_root` decision in `shared-context/decisions.md`.

Then set the item's status to `status::doing` — also rewriting the `Status:` line of its
`## Delivery Status` section to match (appending the section first, initialized from live state,
if the item predates it; per @skills/common/backlog-checklists.md) — and append a progress comment
("Implementation started") containing a mini-plan: the files to add/change under the resolved source root, the
interface/contract (aligned to siblings + ubiquitous language + `coding-standards.md`), and the
tests — listed **per unit and before the code that will satisfy them**, since Step 5 commits them
first (@rules/tdd-workflow.md §2), together with which acceptance-level test carries the outer loop
(§3) and which units the rule exempts (§5). **Delegate the drafting
of the mini-plan to an opus sub-agent**, giving it the Step 3 digest, the item's acceptance
criteria, and `review-knowledge.md` — planning against Epic-wide contracts is the judgment step
this skill reserves opus for. The sub-agent must check the plan against `review-knowledge.md` so a
lesson from a previous review is not re-implemented as a fresh finding. Present the mini-plan and
confirm, unless `--auto`. On `--dry-run`, do not write the label/comment — report what would
change.

### Step 5 — Implement

When the item touches a GraphQL surface, read the approved SDL, resolver contracts and
@rules/graphql-contract-fidelity.md before editing code. Update the SDL/design contract first for a
behavior change, bind handlers by field coordinate, and apply @rules/graphql-security-checks.md.
Do not add a resolver, field, argument, error kind or query limit only in code. Preserve REST/GraphQL
authorization, transaction, error and idempotency parity in hybrid services.

**Any new dependency this item introduces is version-resolved first**, per
@rules/dependency-versions.md: look the version up in its registry (never recall it, never copy a
number out of a skill/rules example), pick the stable, non-EOL release that is compatible with what
the project already pins, and reuse `work/version-decisions.json` when it is fresh so parallel
sub-agents cannot pin two different versions of the same library. The existing lockfile/BOM in the
source tree is binding — this Issue's scope is what it introduces, not an ambient upgrade of
everything else. Confirm the version decision table per `--confirm-versions` /
`--no-confirm-versions` / `options.confirm_versions` (default: ask, except under `--auto`), record it
in `shared-context/decisions.md` as a cross-cutting decision, and name the versions in the Step 7
progress comment. Sub-agents receive the resolved versions — they do not each decide their own.

**Delegate the implementation to sonnet sub-agents** — one per coherent unit of the mini-plan
(e.g. per service or per module), run in parallel when units don't share files. Each sub-agent
receives the approved mini-plan slice, the Step 3 digest, the **source root resolved in Step 4**,
and the relevant `coding-standards.md` excerpts, and writes code under that root on the working
branch, following `coding-standards.md`, reusing/aligning sibling contracts, and satisfying the
item's acceptance criteria — returning the changed-file list and self-review notes, not file
contents. Sub-agents write only inside the resolved root; a unit that needs to write elsewhere
stops and reports it instead of widening the scope on its own. When such a stop is genuinely
deferrable work (not a blocker for this Issue), the orchestrator queues it via
`/architect:capture-followup <title> --queue-only` so it becomes a tracked follow-up Issue
instead of a dead-end note.
Escalate a unit to opus only when it involves judgment-heavy design (2PC boundaries, cross-service
data ownership, ambiguous contracts). Apply the relevant
`@rules/*` (e.g. ScalarDB patterns) when the project uses them. Reuse existing code in the source
tree rather than duplicating it.

**Each unit is written test-first, as the Red → Green → Refactor commit series of
@rules/tdd-workflow.md §2** — this is the order, not a style preference:

1. **Red** — the sub-agent derives the unit's tests from the specification (the item's acceptance
   criteria, `reports/07_test-specs/` where it exists, the aggregate manifest's examples, the
   state × event matrix), commits them as `test: … (#<iid>)` with only what they need to compile,
   and **runs them to see them fail**. The failing test names and the command go in the commit body.
   A test that passes before any behaviour exists is asserting nothing — rewrite it, do not proceed.
2. **Green** — the smallest change that makes them pass, committed as `feat: … (#<iid>)`.
3. **Refactor** — structure only (duplication, ubiquitous-language names, layer placement),
   committed as `refactor: … (#<iid>)` with no test edited. A design defect surfaced here (an
   invariant the manifest lacks, a missing state) is recorded on the Issue and queued via
   `/architect:capture-followup --queue-only` for the owning design skill — code never becomes the
   only place a rule lives.

The outer loop is the item's acceptance-level test (§3 of the rule): its Gherkin scenarios when a
BDD runner is configured, otherwise its contract test or invariant example — red before the first
unit, green after the last, and named in the Step 7 comment. A port the item introduces gets its
in-memory Fake under `src/test/java/**/fakes/` in the same Red commit (§4); a unit that the rule
exempts (§5 — wiring, DTOs, adapters, refactor-only) says so in its commit body. The first item of a
new service is the walking skeleton and is implemented before any other.

**Commit the changes to the working branch** in these units,
each commit message referencing the Issue — uncommitted work cannot be
reviewed or merged downstream. Verify each commit actually staged the intended files
(`git show --stat`); an empty or short commit means the output path is ignored or misresolved —
stop and re-check Output Location rather than proceeding to review.

### Step 5b — Document the implemented code
Run `/architect:generate-docs --scope=changed --source-root=<resolved root> --issue=<iid>
[--auto] [--dry-run]` so the README(s) and `docs/` pages describe what this item actually added or
changed. It updates in place (only its own marked sections; human prose is preserved), verifies the
commands it documents against real build targets, and commits the doc changes to the **same working
branch** — so they reach the same PR/MR as the code and are reviewed together in Step 6. Any
design-vs-code drift it reports is appended to the Issue as a finding, not resolved in prose —
and, when fixing the drift is out of this Issue's scope, also queued via
`/architect:capture-followup --queue-only` so it stays deliverable. Skip
only when the item changes no documented surface (e.g. an internal-only refactor with no behaviour,
config, interface, or command change) — say so in the Step 7 comment when skipped.

### Step 5c — Quality gate (before a human is asked to look)
Run the eight-stage gate of @rules/ai-code-quality-gate.md over the item's change, via
`/architect:verify-implementation --gate --scope=changed --source-root=<resolved root>
--item=<local_id> [--auto]`. It builds, runs the unit / contract / integration suites, runs SAST and
the dependency scan, delegates the API-security stage to `/architect:review-api-security --mode=code`,
and checks the change against the design on all four conformance axes.

Two rules make this a gate rather than a report:

1. **Evidence, not judgment.** A stage passes when a command ran and exited zero, or when a skill
   returned findings. "It looks correct" is not a stage result, and a stage that did not run is
   recorded with its reason (`not-applicable` / `not-configured` / `skipped-by-user`) — never omitted,
   because an omitted stage reads as a passed one.
2. **FAIL blocks the handoff.** On FAIL, route the blocking `VER-`/`ASEC-` findings back to the Step 5
   implementer sub-agents and re-run the gate. Do not proceed to Step 6 with an unresolved FAIL and do
   not open a PR/MR from a failing item — the whole point is that a human is never asked to review
   code that has not passed. If it will not converge, stop and take it to the user, the same way
   `review-issue` handles a non-converging fix loop.

CONDITIONAL requires an explicit decision recorded on the Issue naming what was accepted and why; it
never becomes a PASS by default. Attach `reports/09_verification/quality-gate.md` to the Step 7 comment.

Skip only when the item ships no code (a docs-only or config-only item) — and say so in Step 7.

### Step 6 — Review (lightweight + on-demand)
1. **Self-review** — done by each Step 5 implementer sub-agent against the item's acceptance
   criteria and the shared guardrails; the orchestrator only collates the notes.
2. **Epic-consistency check** — **delegate to an opus sub-agent** that receives the diff summary
   and the Step 3 digest, and returns a pass/findings verdict: does the change conflict with
   sibling Issues' contracts or recorded decisions (naming, API shapes, data model, ubiquitous
   language, NFR budgets)? Fix small inconsistencies (route them back to the Step 5 implementer);
   surface larger ones as findings on the item and, if needed, on the Epic — and queue the ones
   that warrant their own work item via `/architect:capture-followup --queue-only`, so a finding
   too big for this Issue becomes a follow-up Issue rather than prose.
3. **Record cross-cutting decisions** — any new decision that affects other items is appended to
   `shared-context/decisions.md`, closing the consistency loop.
4. **On-demand Epic roll-up** — `--review-epic[=<id>]` **delegates to an opus sub-agent** a
   consolidated review across all Issues under the Epic (coherence, gaps, duplicated work, contract
   drift), writing `reports/backlog/epic-review-<epic>.md`. The **automatic** trigger for this review lives in
   `/architect:merge-issue`: it invokes (or recommends) `--review-epic` when the last Issue of a
   Sub-Epic is merged — a single trigger authority, so it does not also fire from here.

### Step 7 — Record progress (append to the items)
Append the executed work back onto the tracker and mirror it locally. **Delegate the drafting of
the comments and the `impl-log/` mirror to a haiku sub-agent** (mechanical summarization of the
collected results); the orchestrator executes the actual `glab`/`gh` writes. On `--dry-run`, stop
before any remote write and report the intended changes.
- **Issue** — comment with what was implemented (files, key decisions, deviations), the
  test-first record (per unit: `test-first` / `test-after` / `refactor-only` / `exempt` with the
  reason, and the acceptance-level test that carried the outer loop — @rules/tdd-workflow.md §6),
  the acceptance-criteria checklist status, any follow-ups queued during this item (their
  `followup-queue.md` entries, so the deferral is visible on the tracker), and the review result;
  transition status to
  **`status::review` at most**. **Tick the acceptance-criteria checkboxes** this item's committed
  code actually satisfies — edit the Issue body in place per @skills/common/backlog-checklists.md,
  flipping only `[ ]` → `[x]` on the criteria you can point at a commit/test/doc for, and list every
  box left unticked (with what is missing) in the same comment. Never tick a criterion because it is
  planned, and never rewrite the body wholesale. In the Issue's `## Delivery Status` section
  (retrofit it first if missing), rewrite the `Status:` line to the new label and **tick the
  `Implemented` stage** when every acceptance criterion is ticked with test evidence.
  `status::done` is owned by
  `/architect:merge-issue` — an Issue is done only when its PR/MR has merged, so this skill never
  sets `done` (that would silently drop the Issue out of the review → PR/MR → merge flow).
- **Sub-Epic** — comment with a roll-up (progress and notable decisions). **When every acceptance
  criterion of this Issue is ticked with test evidence, tick this Issue's box** in the Sub-Epic's
  `## Issues` task list (in place, per @skills/common/backlog-checklists.md) — the child box renders
  implementation state (implemented + tests passing), so it flips here, not at merge. If any
  criterion is still open, leave the box unticked and name what is missing. When this tick was the
  Sub-Epic's last, also tick the `Implemented` stage in the Sub-Epic's `## Delivery Status`
  (retrofit the section if missing). Sub-Epic
  `status::done` remains `/architect:merge-issue`'s (set when its last Issue merges).
- **Epic** — comment with a progress roll-up and any cross-cutting decisions. When this Issue
  completed the Sub-Epic's implementation (every sibling Issue's box now ticked), also tick the
  Sub-Epic's box in the Epic's `## Sub-Epics` task list — and, when that completed the Epic's
  implementation, the `Implemented` stage in the Epic's `## Delivery Status`.
- Mirror the appended notes to `reports/backlog/impl-log/<item>.md` (with frontmatter), and update
  the node in `backlog-manifest.json` with `impl: { status, files, decisions, updated_at }`.

### Step 8 — Continue
If this item queued follow-ups, offer to flush them now (`/architect:capture-followup --flush` —
its approval gate applies) so the deferred work becomes tracker Issues while the context is fresh.
Then offer the next `doing` / `todo` item under the same Epic (confirm before starting) or stop.

## Acceptance Criteria

- The item is implemented against the parent Epic and its siblings; no contract conflict is left
  unaddressed (fixed or surfaced as a finding).
- Every implemented item ends with a progress comment on its Issue and a status-label transition,
  mirrored in `reports/backlog/impl-log/`.
- The Issue's acceptance-criteria checkboxes reflect reality: each satisfied criterion is `[x]` with
  evidence, each unsatisfied one is still `[ ]` and named in the comment; the Issue's box in the
  parent's child task list is ticked **iff** implementation and tests are complete (all criteria
  ticked), so the parents' progress counters render implementation state. The touched items'
  `## Delivery Status` sections match: `Status:` line rewritten on every label transition, the
  `Implemented` stage ticked on completion, and the section retrofitted onto items that predate it.
- The shared-context pack exists and was consulted — including `review-knowledge.md`, so known
  review findings are not reintroduced; any new cross-cutting decision is recorded in `decisions.md`.
- No fabricated requirements/endpoints/numbers — everything traces to acceptance criteria or a
  referenced report. **Version numbers included**: every dependency this item introduced was looked
  up, is stable and compatible with the project's existing pins, and is recorded in
  `decisions.md` + `work/version-decisions.json`.
- Every behavioural unit was committed test-first — a `test:` commit whose body names the tests
  that failed, before the `feat:` commit that made them pass — or its exemption is named in the
  commit body and the Step 7 comment; no unit's tests were written after its code without saying so
  (@rules/tdd-workflow.md). Every repository port the item introduced has an in-memory Fake.
- Documentation for the changed surface was updated in the same commit range (Step 5b) — or the
  skip was justified and recorded — so the PR/MR carries code and docs together.
- Code was written under a source root that passed the `git check-ignore` and in-worktree checks,
  recorded as `source_root` in `decisions.md`, and every commit staged the intended files — no
  merge-bound code was written into `generated/` unless `--out` explicitly asked for it.
- `--dry-run` performs no remote writes and no code output; it only reports intended changes.
- Heavy steps ran as model-tiered sub-agents per the assignment table (opus only for planning and
  consistency verdicts); the orchestrator held digests, not full report/source bodies.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:export-backlog | Upstream — creates the backlog + manifest this skill consumes |
| /architect:design-implementation | Input source (How specs for Issues) |
| /architect:generate-scalardb-code | Reference for code layout/conventions — note it emits regenerable scaffolding to `generated/{service}/`, whereas this skill writes merge-bound code to the source tree |
| /architect:generate-test-specs | Reference for test generation |
| /architect:generate-docs | Step 5b — documents the implemented code onto the same branch/PR |
| /architect:capture-followup | Sink for deferrable work discovered in Steps 5/5b/6 — queues it, then turns it into linked follow-up Issues |
| /architect:review-consistency, /architect:review-synthesizer | Review lenses reused by the Epic roll-up |
