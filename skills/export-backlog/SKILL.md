---
description: |
  Turn the generated reports into a work-item backlog on GitLab or GitHub:
  Epics (What / Why), Sub-Epics (What / Key Results), and Issues (How).
  /architect:export-backlog [--target=gitlab|github] [--project=<path>|--repo=<owner/name>] [--group=<gitlab-group>] [--dry-run] [--update] [--lang=en|ja].
  Synthesizes a review-first plan from reports/, gates on explicit approval, then creates the
  hierarchy via glab / gh. Run after the design (and optionally review) phase, or after the
  product pipeline. Only runs when explicitly invoked.
model: opus
user_invocable: true
disable-model-invocation: true
---

# Backlog Export (Reports → GitLab / GitHub)

## Desired Outcome

Convert the artifacts under `reports/` into a three-level work-item hierarchy on the user's
issue tracker:

- **Epic — What / Why.** The initiative and the reason it exists (product/system + business
  rationale). Usually one Epic; several only when scope or a phased transformation defines
  distinct initiatives.
- **Sub-Epic — What / Key Results.** A coherent capability area (bounded context / domain /
  migration wave) plus the measurable results that prove it is done.
- **Issue — How.** A concrete, buildable unit of work with acceptance criteria and traceability
  back to the source report.

The export is **review-first and idempotent**: a human-readable plan is written and approved
before anything is created remotely, and re-runs update existing items instead of duplicating
them.

## Decision Criteria

- **Target platform** — GitLab or GitHub. Take from `--target`; otherwise infer from the git
  remote (`git remote -v`) and confirm with the user via AskUserQuestion. Never guess silently.
- **Epic granularity** — Default to **one Epic** for the whole initiative. Create multiple Epics
  only when `scope-definition.md` splits the product into distinct initiatives, or
  `transformation-plan.md` defines phased migration waves that each warrant their own Epic.
- **Sub-Epic axis** — Prefer **bounded contexts / domains** (`Core` → `Supporting` → `Generic`).
  Fall back to major feature groups when no domain map exists, or transformation phases on the
  legacy-refactoring path.
- **Issue sizing** — Each Issue must be independently buildable and reviewable. Split anything
  that mixes unrelated aggregates, spans multiple services, or has more than ~5 acceptance
  criteria.

## Prerequisites

At least one of the two report trees must exist. Read whatever is present; do not require all of it.

| File / directory | Level it feeds | Source pipeline |
|------------------|----------------|-----------------|
| `reports/00_core/vision-mission-value.md`, `pr-faq.md`, `scope-definition.md`, `success-metrics.md` | Epic (Why), Sub-Epic (KR) | product |
| `reports/00_requirements/requirements-definition.md` | Epic (What/Why) | architect (greenfield) |
| `reports/01_analysis/system-overview.md`, `reports/02_evaluation/unified-improvement-plan.md` | Epic (What/Why, legacy) | architect (legacy) |
| `reports/03_domain/bounded-contexts.md`, `domain-map.md` · `reports/03_design/bounded-contexts-redesign.md`, `context-map.md`, `domain-analysis.md` | Sub-Epic (What) | product / architect |
| `reports/04_quality/sla.md`, `nfr.md` · `reports/00_core/success-metrics.md` | Sub-Epic (Key Results) | product |
| `reports/02_spec/feature-list.md`, `reports/03_domain/api-design.md`, `reports/02_spec/data-model.md` | Issue (How) | product |
| `reports/06_implementation/`, `reports/03_design/api-specifications/`, `reports/03_design/scalardb-*.md`, `transformation-plan.md` | Issue (How) | architect |
| `reports/review/review-synthesis.md` (+ `review-synthesis.json`) | Issue (How — remediation) | architect review |

Read the output language from `work/pipeline-progress.json` (`options.output_language`, default
`en`); `--lang` overrides it. All generated issue titles/bodies use that language; label keys and
traceability IDs stay in English.

## Mapping Model

Build each node with these fields. Carry **traceability IDs** (`FEAT-`, `CTX-`, `API-`, `NFR-`,
`SLO-`, `JOB-`, `PER-`, `ENT-`, review finding IDs like `CON-`/`RSK-`) through every level so the
backlog stays linked to the design.

### Epic — What / Why
- **What**: one sentence naming the product/system and the outcome it delivers.
- **Why**: the problem, business rationale, and target success metrics / North Star.
- **Body sections**: `## What`, `## Why`, `## Success Metrics` (from `success-metrics.md` or
  requirements NFR), `## Sub-Epics` (task list of children), `## Source reports`.

### Sub-Epic — What / Key Results
- **What**: the capability area / bounded context and its responsibility.
- **Key Results**: 2–4 measurable outcomes, each tied to an SLO/NFR/input-metric with a target
  value (e.g. "p95 latency < 200ms (NFR-03)", "checkout conversion +5pt (MET-02)"). Never invent
  numbers — if the reports give none, write the KR as a `TBD` to be filled, and say so.
- **Body sections**: `## What`, `## Key Results`, `## Issues` (task list of children),
  `## Traceability`, `## Source reports`.

### Issue — How
- **How**: the implementation approach — components/classes/endpoints/schema to build or change.
- **Acceptance Criteria**: a checklist or Given/When/Then; must be verifiable.
- **Body sections**: `## How`, `## Acceptance Criteria`, `## References` (source report path +
  traceability IDs), and suggested `size` (S/M/L).
- - **Bake in past lessons**: when a `review-knowledge.md` rule applies to an Issue's area, fold it
  into that Issue's acceptance criteria or a `## Known pitfalls` note (cite the `KN-` id), so the
  next implementation avoids the finding up front.
- **Issue seams** (one Issue each): a feature/Command from `feature-list.md`; an endpoint from
  `api-design.md` / `api-specifications/`; a schema or migration unit from `data-model.md` /
  `scalardb-*.md`; a service/repository/value-object spec from `reports/06_implementation/`; a
  transformation step; each **High/Critical** review finding from `review-synthesis.md`.

## Steps

### Step 0 — Resolve target and destination
1. Determine platform (see Decision Criteria) and the destination:
   - GitLab: project path (`glab repo view` or the remote) and, for native Epics, the group
     (`--group`, else the project's top-level group).
   - GitHub: `owner/name` (`gh repo view --json nameWithOwner`).
2. Verify auth non-destructively: `glab auth status` / `gh auth status`. If not authenticated,
   stop and ask the user to run `! glab auth login` / `! gh auth login`.
3. Probe capability once, read-only, and record it for Step 5:
   - GitLab Epics need a group and a Premium/Ultimate tier. Probe with
     `glab api "groups/<group>/epics?per_page=1"`; a 403/404 means fall back to the label scheme.
   - GitHub has no native Epics; default to the label + task-list scheme (native sub-issues are an
     optional enhancement, attempted only if the first `addSubIssue` GraphQL call succeeds).

### Step 1 — Ingest reports
Read every present Prerequisites file. Extract the initiative summary, the domain/bounded-context
list with their tiers, the measurable targets (metrics/SLO/NFR), the feature/API/data units, and
the High/Critical review findings. If **no** report tree exists, stop and tell the user to run the
product or architect pipeline first.

Also read the project review knowledge base if it exists
(`reports/backlog/shared-context/review-knowledge.md`, maintained by `/architect:review-issue`): its
accumulated lessons from past reviews feed the next round of planning — recurring findings should be
pre-empted in the Issues you synthesize (see Step 2).

### Step 2 — Synthesize the hierarchy
Apply the Mapping Model. Assign stable local IDs: `E1`, `SE1.1`, `I1.1.1` … (Epic → Sub-Epic →
Issue). Attach labels: `type:epic|sub-epic|issue`, a domain label per Sub-Epic
(`domain:<context>`), `tier:core|supporting|generic` where known, and an initial **status label**
`status::todo` (GitHub form: `status:todo`) on every node so the downstream
`/architect:implement-backlog` skill can select in-progress work. Keep every node traceable to at
least one source report path.

**Status taxonomy (shared with `/architect:implement-backlog`).** Use scoped labels on GitLab and
plain labels on GitHub, seeded here at `todo` and advanced by the implement skill:
`status::todo` · `status::doing` · `status::review` · `status::done` · `status::blocked`
(GitHub: `status:todo` …). Create the labels once if they do not exist.

### Step 3 — Write the review-first plan (immediate output)
Write two files under `reports/backlog/` **before creating anything remotely**:
- `reports/backlog/backlog-plan.md` — human-readable, in the output language, with the full tree,
  each node's What/Why/KR/How and acceptance criteria, and a Mermaid diagram of the hierarchy.
  Include the required YAML frontmatter (`title`, `schema_version: 1`, `phase`, `skill:
  export-backlog`, `generated_at`, `input_files`).
- `reports/backlog/backlog-manifest.json` — machine-readable array of nodes:
  `{ local_id, level, title, body, labels, parent_local_id, source_reports, traceability,
  remote: null }`. This is the source of truth for creation and idempotency.

### Step 4 — Confirmation gate (required — do not skip)
Creating remote work items is outward-facing and hard to reverse. Present a concise summary
(counts per level, target project, whether native Epics or the label fallback will be used) and
**ask for explicit approval** via AskUserQuestion before any create call. On `--dry-run`, stop
here after writing the plan and report what *would* be created. Never create items the user has
not approved.

### Step 5 — Create the hierarchy (idempotent)
Process the manifest top-down (Epics → Sub-Epics → Issues). For each node, if
`remote.url` is already set (or an item with the same title + `type:` label already exists on the
target), **skip creation** and, with `--update`, sync title/body/labels instead. Write
`remote: { id, iid, url, created_at }` back into `backlog-manifest.json` immediately after each
successful create so an interrupted run resumes cleanly.

**GitLab**
- Native path (Epics available):
  - Epic: `glab api --method POST "groups/<group>/epics" -f title=… -f description=… -f labels=…`
  - Child Sub-Epic: create it as an Epic, then link via the Epic Links API
    `glab api --method POST "groups/<group>/epics/<parent_iid>/epics" -f child_epic_id=<child_id>`.
  - Issue: `glab issue create -R <project> -t "…" -d "…" -l "…"`, then attach to its Sub-Epic with
    `glab api --method POST "groups/<group>/epics/<subepic_iid>/issues/<issue_id>"`.
- Fallback path (no group / not Premium): create **every** level as an issue with scoped labels
  (`type::epic`, `type::sub-epic`, `type::issue`, `Epic::<name>`); after children exist, edit each
  parent's description to list them as a task list (`- [ ] #<iid>`).

**GitHub**
- Default (label + task-list): `gh issue create -R <owner/name> -t "…" -b "…" -l "type:epic"`
  (then `type:sub-epic`, `type:issue`). After children are created, `gh issue edit <parent> --body`
  to append the child task list (`- [ ] #<num>`). Optionally group Sub-Epics under a milestone
  (`gh api repos/<owner>/<name>/milestones`).
- Native sub-issues (enhancement): if the org supports them, link child→parent with the
  `addSubIssue` GraphQL mutation; on any error, silently fall back to the task-list scheme.

### Step 6 — Write the result report (immediate output)
Write `reports/backlog/backlog-export-result.md` (frontmatter required): a table of every created
item with its level, title, URL, and source traceability, plus any nodes skipped/failed and why.
Print the Epic URL(s) to the user.

## Acceptance Criteria

- A `backlog-plan.md` + `backlog-manifest.json` are written and approved **before** any remote
  create call.
- Every Issue has at least one verifiable acceptance criterion and a source-report reference.
- Every node traces to a source report; Key Results cite a metric/SLO/NFR ID (or are marked `TBD`).
- Re-running does not create duplicates; created URLs are recorded in the manifest.
- No fabricated numbers, endpoints, or requirements — everything derives from the reports.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-microservices | Input source (target architecture) |
| /architect:design-implementation | Input source (How → Issues) |
| /architect:review-synthesizer | Input source (remediation Issues) |
| /product:map-domains | Input source (Sub-Epic axis) |
| /product:define-features | Input source (feature Issues) |
| /product:design-sla, /product:define-nfr | Input source (Key Results) |
