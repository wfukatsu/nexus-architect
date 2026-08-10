---
description: |
  Create and update the documentation for code that has been generated or implemented — the
  README(s) and the docs/ pages — so the docs describe the code that actually exists. Runs after
  the codegen skills (generate-scalardb-code, generate-infra-code, generate-frontend) and as the
  documentation step of /architect:implement-backlog, where the doc changes land in the same
  commit and PR/MR as the code.
  /architect:generate-docs [target] [--scope=changed|service|repo] [--source-root=<path>] [--readme-only] [--issue=<id>] [--dry-run] [--auto] [--lang=en|ja].
  Updates in place: regenerates only its own marked sections and never discards human-authored
  prose. Runs as a thin sonnet orchestrator delegating inventory and page writing to sub-agents.
  Only runs when explicitly invoked.
model: sonnet
user_invocable: true
disable-model-invocation: true
---

# Code Documentation (README + docs/)

## Desired Outcome

Documentation that a new engineer can follow to build, run, and change the code — derived from the
code as it exists, not from the design as it was imagined:

- **A README at every entry point.** The repo (or scaffold) root explains what the system is and
  how to get running; each service/module README covers its own responsibility, build/run/test
  commands, configuration, and layout.
- **Deeper docs where the README would bloat.** `docs/` carries the architecture overview,
  configuration reference, API usage, and operational notes, each linking back to the design
  reports that justify them.
- **Safe updates.** Re-running edits in place: only the sections this skill owns are regenerated,
  human-authored prose is preserved.
- **Docs shipped with the code.** In delivery mode the doc changes are committed to the same
  working branch as the implementation, so they are reviewed and merged in the same PR/MR.
- **Drift surfaced, not hidden.** Where the code and the design reports disagree, the gap is
  reported as a finding instead of being smoothed over in prose.

## Decision Criteria

- **Document what exists** — Content is derived by reading the actual code, build files, and
  configuration. The design reports supply the *why* (intent, constraints, decisions), never the
  *what*. If a designed feature is absent from the code, do not document it as if it were there.
- **No fabricated commands** — Every build/run/test/deploy command shown must be backed by
  something real (a Gradle/Maven task, an npm script, a Makefile target, a Compose service, a
  documented CLI). Verify before writing; omit what cannot be verified.
- **Update, don't overwrite** — This skill owns only the regions it marked (see Ownership Markers).
  Everything else in an existing file is preserved verbatim. Never delete a section this skill did
  not write; when an existing unmarked file needs restructuring, propose the change and confirm.
- **Scope follows the code** — `changed` (default in delivery mode) documents what the working
  branch touched; `service` documents one service/module; `repo` covers the whole tree. Do not
  rewrite the entire tree's docs to record a one-Issue change.
- **Consistency with the project vocabulary** — Terms come from
  `reports/backlog/shared-context/ubiquitous-language.md` (or `reports/01_analysis/`,
  `reports/03_domain/`) when present. Do not coin competing names in prose.

## Prerequisites

| File / source | Required/Recommended | Produced by |
|---------------|----------------------|-------------|
| Generated or implemented code in the target tree | Required | codegen skills / /architect:implement-backlog |
| `reports/03_design/target-architecture.md` | Recommended | /architect:design-microservices |
| `reports/backlog/shared-context/` (ubiquitous language, architecture guardrails, coding standards) | Recommended | /architect:implement-backlog |
| `reports/03_design/api-specifications/` | Recommended | /architect:design-api |
| `reports/08_infrastructure/` | Recommended (infra scaffolds) | /architect:design-infrastructure |

Read the output language from `work/pipeline-progress.json` (`options.output_language`, default
`en`); `--lang` overrides it. Prose uses that language; code identifiers, file paths, commands,
environment-variable names, and config keys stay verbatim in English.

## Modes

| Mode | Trigger | Code location | Commits? |
|------|---------|---------------|----------|
| **Scaffold** | After `generate-scalardb-code` / `generate-infra-code` / `generate-frontend` | `generated/{service}/`, `generated/infrastructure/`, `generated/frontend/` | No — the tree is regenerable pipeline output |
| **Delivery** | Step 5b of `/architect:implement-backlog`, or `--issue=<id>` | The resolved `source_root` (see that skill's Output Location) on the working branch | Yes — with the code, referencing the Issue |

Resolve the root in this precedence: `--source-root=<path>` → the `source_root` recorded in
`reports/backlog/shared-context/decisions.md` → the tree named by the invoking skill → the
repository root. In delivery mode the root must pass the same checks `implement-backlog` applies
(`git check-ignore -q <root>` exits 1; the root is inside the target worktree) — documentation that
git ignores cannot reach the PR/MR. If the target is not a git worktree at all, delivery mode cannot
commit: say so plainly (rather than surfacing a raw git error) and offer to continue in scaffold
mode, which needs no repository.

## Ownership Markers

Generated regions are delimited so re-runs are safe and reviewable:

```markdown
<!-- nexus:begin:build-and-run -->
...generated content...
<!-- nexus:end:build-and-run -->
```

- A **new** file is written entirely inside markers, section by section.
- An **existing marked** file has only its marked regions replaced; text outside them is untouched.
- An **existing unmarked** file (hand-written README) is never rewritten in place. Present the
  proposed additions and, on confirmation, insert them as newly marked sections in the right
  position, leaving the original prose intact. On `--auto`, append them at the end rather than
  guessing where the author wanted them.

Section keys are stable (`overview`, `build-and-run`, `configuration`, `layout`, `api`,
`operations`, `traceability`, `findings`) so a later run updates the same region. Never invent a key
outside this list — an unrecognized key makes the region unfindable on the next run.

**Removing a section.** When a run no longer justifies a section it previously wrote — the drift
recorded in `findings` is resolved, the documented surface is gone, the service was deleted —
remove the whole marked region *including its markers*, and list the removal in the run report. A
stale generated section is worse than a missing one. Only regions whose key is in the stable list
may be removed: anything else was not written by this skill and is left alone.

**Whitespace around a region.** Insert and remove must be exact inverses, or repeated runs produce
whitespace-only diff noise in a file whose whole point is being reviewable:

- a marked region is separated from its neighbours by **exactly one blank line**, or sits flush
  against the start/end of the file
- removing a region takes the region *and* the single blank line that follows it — or, at end of
  file, the one that precedes it
- the file ends with exactly one newline, and no run of two or more blank lines is ever introduced

Verified by round-trip: under this rule, remove → re-insert reproduces the file byte-for-byte, and
repeated cycles do not drift. The whole marker contract above is asserted as behaviour by
`skills/generate-docs/marker-mechanics.test.py` — run it after changing these rules.

## Sub-Agent Execution & Model Assignment

A **thin orchestrator (sonnet)** delegating to sub-agents (Agent/Task tool; see
@skills/common/sub-agent-patterns.md). The orchestrator holds the inventory digest and the page
plan — never full source files or full report bodies.

| Step | Delegated work | Sub-agent (model) | Returns to orchestrator |
|------|----------------|-------------------|-------------------------|
| 1 | Inventory the code in scope (entry points, build targets, config keys, endpoints, env vars, scripts, tests) | Explore (**haiku**) | inventory digest |
| 2 | Extract the *why* from design reports for the code in scope | Explore (**haiku**) | intent digest + report paths to link |
| 4 | Write/update one README or docs page | **sonnet**, one per page, in parallel | file written + section keys touched |
| 5 | Verify commands, links, and design-vs-code drift | **haiku** | verification report: unverified commands, broken links, drift findings |

Escalate a page to **opus** only when it must explain a judgment-heavy design (2PC boundaries,
consistency model, failure/recovery semantics) that the reports state but do not explain in usable
terms. Never use opus for routine README assembly.

## Steps

### Step 0 — Resolve mode, root, and scope
Determine the mode and the root per Modes (running the git checks in delivery mode; stop and report
the matching ignore rule if the root is ignored). When invoked standalone — no `--issue` and not as
a step of another skill — the resolved root decides the mode: a root under `generated/` is
**scaffold**, anything else is **delivery** (with `--issue` required before any tracker write; if
the run has no Issue to reference, commits still land on the working branch and the drift findings
go to the user only). Resolve the scope: `--scope` if given, else
`changed` when a working branch with commits is present, else `repo`. In `changed` scope, take the
touched paths from `git diff --name-only <base>...HEAD` and map them to the owning services/modules.
Report the resolved mode, root, scope, and target files before doing work.

### Step 1 — Inventory the code (delegated)
**Delegate to an Explore sub-agent (haiku)** that reads the code in scope and returns a compact
**inventory digest**, not file contents:
- services/modules and their entry points (`main` classes, `index.ts`, Compose services, chart names)
- build/run/test commands actually defined (Gradle/Maven tasks, npm scripts, Makefile targets)
- configuration surface: config files, keys, environment variables, and their defaults
- public interfaces: HTTP routes, gRPC services, CLI commands, exported components
- dependencies and required runtimes/versions
- existing docs: which READMEs and `docs/` pages exist, and which carry nexus ownership markers

**Observed vs inferred.** The digest must mark any value the sub-agent derived rather than read —
`inferred: <value> (<basis>)`, e.g. `inferred: Node 18+ (Vite 5 requires it)` when `package.json`
declares no `engines`. A digest that presents inference as inventory defeats the skill's central
discipline: the orchestrator cannot tell the two apart afterwards, so the inference reaches the
README as fact. Inferred values may be documented, but only with their basis stated or hedged —
never asserted flat as if read from the code.

### Step 2 — Gather design intent (delegated)
**Delegate to an Explore sub-agent (haiku)** that reads the design reports relevant to the code in
scope and returns an **intent digest**: what each service is for, the constraints and decisions
behind it, the ubiquitous-language terms to use, and the report paths worth linking. Prefer
`reports/backlog/shared-context/` when it exists — it is already the distilled form.

### Step 3 — Plan the doc set (confirm)
From the two digests, produce the page plan: for each target file, whether it is created or
updated, which section keys it will own, and a one-line summary of each section. Include the root
README, per-service READMEs, and only the `docs/` pages the content justifies — do not create empty
scaffolding pages. `--readme-only` restricts the plan to README files. Present the plan and confirm,
unless `--auto`. On `--dry-run`, stop here and report the plan.

### Step 4 — Write the documentation (delegated, parallel)
**Delegate one sonnet sub-agent per page**, each receiving the inventory digest, the relevant slice
of the intent digest, the ownership rules, and the target file's current marked regions. Standard
section content:

| Section key | Content |
|-------------|---------|
| `overview` | What this service/system is, its responsibility, and its place in the architecture (one diagram at most, Mermaid) |
| `build-and-run` | Prerequisites, build, run, test — verified commands only, in copy-pasteable blocks |
| `configuration` | Config keys and environment variables: name, purpose, default, required/optional |
| `layout` | Directory map with a line per significant directory |
| `api` | Public interface summary: REST routes/operationIds and GraphQL schema fields/operations, linking to the API specs for detail; include GraphQL transport, authentication, query limits, pagination, error extensions and deprecation policy when applicable |
| `operations` | Deploy/rollback, health checks, logs/metrics, common failure modes (infra and service scaffolds) |
| `traceability` | Links to the design reports and, in delivery mode, the Issue/Epic this work came from |
| `findings` | Design-vs-code drift and documentation gaps recorded rather than resolved (scaffold mode — see Step 5). Written only when Step 5 produced findings; removed once they are resolved |

Each sub-agent returns the file path and the section keys it touched — not the file body. Mermaid
must follow @rules/mermaid-best-practices.md (non-ASCII labels quoted).

### Step 5 — Verify (delegated)
**Delegate to a haiku sub-agent** that checks the written docs and returns a verification report:
- every command in `build-and-run` exists in a build file, script, or Compose/Makefile target
- every relative link and file path resolves
- every documented config key and route appears in the inventory digest (no fabricated surface)
- design-vs-code drift: designed elements in the intent digest with no counterpart in the inventory

Fix what is fixable (wrong path, stale command) by routing the page back to its Step 4 sub-agent.
Drift is **never** resolved in prose — the docs must not assert a reconciliation the code has not
made. Always report the findings to the user, and record them where the mode has a place for them:

| Mode | Where drift findings go |
|------|-------------------------|
| **Delivery** | Appended to the Issue as a comment — the tracker is the record, so no `findings` section is written into the docs |
| **Scaffold** | Written into the `findings` section of the root README of the documented tree, since there is no tracker to carry them |

In scaffold mode the `findings` region is written **here, after verification** — by this step (or by
routing one last write to the root README's Step 4 sub-agent), not during the Step 4 page pass,
because the findings do not exist until verification has run. Its listing in the Step 4 section
table covers re-runs, where prior findings already exist to carry.

When a later run finds the recorded drift resolved, remove the `findings` region per Ownership
Markers rather than leaving a stale list behind.

### Step 6 — Commit or report
- **Delivery mode** — Stage the doc changes and commit them to the working branch, message
  referencing the Issue (e.g. `docs: … (#<iid>)`), so they reach the same PR/MR as the code. Verify
  the commit staged the intended files (`git show --stat`); an empty commit means the root is
  ignored or misresolved — stop and re-check Step 0.
- **Scaffold mode** — Leave the files in the generated tree and print the written paths.
- On `--dry-run`, no writes and no commits: report the plan and the intended changes only.

## Acceptance Criteria

- Every service/module in scope has a README whose build/run/test commands were verified against
  real build targets; nothing unverifiable was documented.
- Re-running the skill preserves all human-authored prose — only marked regions changed, and no
  unmarked file was rewritten in place without confirmation.
- Documented configuration keys, routes, and env vars all appear in the inventory digest; no
  invented surface. Anything the digest marked `inferred:` is documented with its basis or hedged,
  never asserted as read from the code.
- Design-vs-code drift was reported to the user and recorded where the mode keeps it (the Issue in
  delivery mode, the `findings` section in scaffold mode), never papered over in prose.
- Every region this skill wrote is inside markers with a key from the stable list, and any section
  it previously wrote that is no longer justified was removed with its markers and reported.
- The written file carries no whitespace-only churn: one blank line around each region, one newline
  at end of file, no run of two or more blank lines.
- In delivery mode the doc changes are committed on the same working branch as the code, staged
  files verified, so they land in the same PR/MR.
- `--dry-run` performs no writes and no commits.
- Heavy steps ran as sub-agents per the assignment table; the orchestrator held digests, not full
  source or report bodies.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:generate-scalardb-code | Upstream — documents the service scaffolds it emits |
| /architect:generate-infra-code | Upstream — documents the K8s/Terraform/Helm output (`operations` section) |
| /product:generate-frontend | Upstream — documents the React/Storybook scaffold |
| /architect:implement-backlog | Invokes this as Step 5b so docs ship with the implementation |
| /architect:review-issue | Downstream — reviews the doc changes as part of the Issue's diff |
| /architect:design-api | Input source — API specs linked from the `api` section |
| /architect:report | Different audience — consulting-style HTML report, not developer docs |
