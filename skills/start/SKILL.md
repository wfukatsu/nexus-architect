---
description: |
  Interactively start system analysis and design. Assesses project context and determines the optimal path.
  /architect:start [target_path].
model: sonnet
user_invocable: true
---

# Nexus Architect Orchestrator

## Your Role

As the main orchestrator of nexus-architect, evaluate the project and its objectives, then determine and execute the appropriate analysis and design path.

## Language Selection

Ask the user which language to use for output documents:
- English (default)
- Japanese

Record the selection in work/pipeline-progress.json under options.output_language.

Ask one more project-level preference at the same time — **dependency version confirmation**: when a
codegen skill resolves the versions it is about to pin (see @rules/dependency-versions.md), should it
present the version decision table for approval, or adopt the resolved stable versions on its own?
Record the answer as `options.confirm_versions` (`true` = ask, `false` = adopt silently). Default to
`true` if the user has no preference; a per-run `--confirm-versions` / `--no-confirm-versions`
overrides it.

## Product Handoff Detection

Before selecting a path, check whether the **product** plugin already ran in this project:
glob the same set `/architect:define-requirements` ingests — `reports/00_core/`,
`reports/01_ux/`, `reports/02_spec/`, `reports/03_domain/`, `reports/04_quality/` and
`work/traceability.json` (non-empty `nodes`). Keep the two sets identical: a run that stopped
early (`--profile=mvp` writes only `reports/00_core/`) is still a handoff, and detecting less
than the consuming skill reads means announcing "no product artifacts" over reports it is
about to use. **Match files, not directories** — `/product:init-output` creates
`reports/01_ux/domain-stories/` and `reports/02_spec/ui-mocks/` empty, so a directory-existence
test passes on any initialized product project whether or not a phase ever ran. If any product artifacts exist, this is a **product→architect handoff** (see
@docs/design.md §1.1–1.5).
Announce it and route to the greenfield path with the product reports fed in — do **not** re-elicit
what they already answer:

> "Detected product-direction artifacts (vision, scope, features, bounded contexts, NFRs).
> I'll use them as the requirements baseline via `/architect:define-requirements`."

`define-requirements` auto-detects these reports, but pass them explicitly anyway so the handoff is
visible and survives a non-co-located layout. The §1.4 designed gaps (per-process transaction
consistency, physical DB inventory, actor/role/permission) are what `define-requirements` still
elicits — everything else is confirm-or-correct.

## Workflow Selection Criteria

- Product artifacts detected (above) -> **Product handoff → greenfield path**: run `/architect:define-requirements` with the product reports as inputs, then proceed with the design phases
- User presents an existing codebase -> **Legacy refactoring path**
- User describes requirements only -> **Greenfield design path**: run `/architect:define-requirements` first to fix the requirements baseline (pass any user-provided documents via `--input`), then proceed with the design phases
- Unclear -> Ask one clarifying question, then proceed with execution

## ScalarDB Usage Decision

- `reports/00_requirements/scalardb-applicability.md` exists -> Use its verdicts as the primary
  basis. The verdicts are per business process and may name ScalarDB, ScalarDB Saga, or neither:
  **any** process reaching ScalarDB *or* ScalarDB Saga enables the ScalarDB skills (a Saga adoption
  still stores its saga state through ScalarDB); only when no process reaches either does the
  design-data-layer alternative path apply
- Otherwise, fall back to heuristics:
  - Multi-DB distributed transactions required -> Include ScalarDB skills
  - User mentions ScalarDB / ScalarDB Saga / Scalar / distributed transactions -> Include
  - Otherwise -> Use the design-data-layer alternative path

## Domain Story Option

After `/architect:redesign` completes, ask the user:

> "Would you like to generate Domain Stories for specific bounded contexts? Domain Storytelling visualizes the business process of each domain as a narrative with actors, work items, and a sequence diagram."

If yes, ask which domains to cover (present the bounded context list from `bounded-contexts-redesign.md`), then run `/architect:create-domain-story --domain=<name>` for each selected domain before proceeding to `design-microservices`.

## State Transition Model Option

After `/architect:redesign` completes — and in the same breath as the Domain Story question, so the
user answers both at once — ask:

> "Should I build state transition models for the aggregates with a lifecycle? The model fixes which
> changes are legal in each state, who may make them, and what happens to the attempts that are not —
> which is what the schema, the API errors and the test specs are derived from."

If yes, run `/architect:design-state-machine` (it selects the aggregates interactively from the
evidence, or pass `--aggregate=<name>` to model one). Run it **before** `design-scalardb` /
`design-data-layer` and `design-api`, which consume it: the state column and its OCC scope, the
per-transition consistency class, the rejected transitions that become registered problem types, and
the idempotent no-ops that become the idempotency contract.

Skip it without asking when no aggregate shows evidence of a lifecycle (no status column, no
condition-shaped term in the ubiquitous language, no rejected path in any domain story) — and say so
rather than leaving the omission silent.

## Execution Flow

1. Evaluate project context (read provided materials, inspect codebase, **run Product Handoff Detection**)
2. Determine the path and relevant phases (product handoff → greenfield)
3. Run `/architect:init-output` to initialize the output directory
4. Execute skills in dependency order per `skill-dependencies.yaml`, recording each phase
   in `work/pipeline-progress.json` **twice**: `status: "in_progress"` with
   `plugin: "architect"` and `started_at` *before* invoking the skill, then `completed` /
   `failed` with `completed_at`, `outputs` and `summary` after it returns
   (@skills/common/progress-registry.md). The pre-write is what makes
   `/architect:report-status` show the phase as running and what attributes its token cost
   to it; `plugin` is what keeps that attribution off the product pipeline's phase of the
   same name. On the handoff path this file already holds product's phases — add to it,
   never re-register it
5. After `redesign`: offer Domain Story generation and state transition modeling (see the two
   Option sections above), then run what the user selected before `design-microservices` and the
   data/API design phases
6. Accumulate findings in `work/context.md` between phases
7. Determine which phases to skip if not applicable

After `design-api`, read canonical `reports/03_design/api-style-decisions.json`. Run
`design-graphql` when any surface selects GraphQL/hybrid and mark it conditionally skipped only when
the validated canonical document is REST-only. Invalid canonical JSON blocks progression; it is
never a REST default. A skipped conditional dependency is satisfied for the review phases.

## Error Handling

On phase failure, present choices to the user via AskUserQuestion:
1. Retry
2. Skip and continue
3. Abort workflow

## Context Management

For long pipelines, periodically update `work/context.md`:
- Key findings from investigation
- Domain insights from analysis
- Important decisions made during design
- Open Questions — carried across phases under stable `OQ-` IDs, re-asked by the phase that needs
  the answer rather than restated (@rules/open-questions.md §7)

## Dependency Manifest

Read @skills/common/skill-dependencies.yaml to determine execution order.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:pipeline | Automated execution version |
| /architect:init-output | Initialization |
| /architect:define-requirements | Greenfield entry point — requirements baseline and ScalarDB applicability |
| /product:start | Upstream — when product ran first, its reports are detected and handed off (@docs/design.md §1) |
