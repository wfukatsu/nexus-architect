---
description: |
  Interactively start system analysis and design: refactoring a legacy application into services,
  or designing a new system from requirements. Assesses project context and determines the path.
  To move an existing database to ScalarDB, use migrate-database instead.
argument-hint: '[target_path]'
model: inherit
---

# Nexus Architect Orchestrator

Shared files: a path written `@rules/…`, `@skills/…`, `@templates/…` or `@docs/…` is relative to the
plugin root, `${CLAUDE_PLUGIN_ROOT}` — not to the project being worked on. Read it from there.

**Usage:** `/architect:start [target_path]`

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

## UI Analysis Option

After `/architect:investigate` completes, read the **Presentation Layer** section of
`reports/before/{project}/technology-stack.md`. When it names a UI — server-rendered templates or a
routed SPA — ask in one question:

> "The system has a UI (<technology>, about <N> screens). Should I analyze it — each screen's inputs,
> outputs, actions and role guards, the components, the features, the business logic in the view
> layer and the design tokens — and then evaluate its UX? A running instance lets the UX evaluation
> add screenshots and a rendered accessibility check; without one it is a static review of the code."

Offer: analyze and evaluate (recommended), analyze only, skip. When a running instance exists, ask for
its URL and, for screens behind a login, a Playwright storage-state file — never for credentials.

Run `/architect:analyze-ui` **before** `/architect:analyze`, which takes its role guards, labels and
screens as evidence (@rules/ui-analysis.md §9), and `/architect:evaluate-ux` — with `--base-url` /
`--storage-state` when given — alongside `evaluate-mmi` and `evaluate-ddd`, before
`integrate-evaluations`.

Skip both without asking when the technology stack reports no presentation layer (a pure API or
batch system), and say so.

## Domain Story Option

After `/architect:redesign` completes, ask the user:

> "Would you like to generate Domain Stories for specific bounded contexts? Domain Storytelling visualizes the business process of each domain as a narrative with actors, work items, and a sequence diagram."

If yes, ask which domains to cover (present the bounded context list from `bounded-contexts-redesign.md`), then run `/architect:create-domain-story --domain=<name>` for each selected domain before proceeding to `design-microservices`.

## Aggregate Design Option

After `/architect:redesign` completes — in the same breath as the Domain Story and State Transition
Model questions, so the user answers all three at once — ask:

> "Should I design the aggregates inside each bounded context? The aggregate is the unit one
> transaction writes: its root, what lives inside it, the invariants that must hold after every
> change, and the commands that may change it — which is what the schema's OCC scope, the
> repository interfaces and the invariant tests are derived from."

If yes, run `/architect:design-aggregate` (it selects the aggregates interactively from the
evidence, or pass `--aggregate=<name>` / `--context=<name>` to narrow). Run it **before**
`design-state-machine`, whose Stage 1 takes the aggregate list from it, and before
`design-scalardb` / `design-data-layer`, `design-api` and `design-implementation`, which consume it.

Skip it without asking when the redesign names no invariant that spans more than one attribute —
then every entity is a table, and there is no aggregate to design.

## State Transition Model Option

After `/architect:redesign` completes — in the same breath as the Domain Story and Aggregate Design
questions, so the user answers all three at once — ask:

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
4. Execute skills in dependency order per `skill-dependencies.yaml` — a dialogue-driven phase
   inline, every other phase as a sub-agent on its manifest model (see Phase Execution) —
   recording each phase
   in `work/pipeline-progress.json` **twice**: `status: "in_progress"` with
   `plugin: "architect"` and `started_at` *before* invoking the skill, then `completed` /
   `failed` with `completed_at`, `outputs` and `summary` after it returns
   (@skills/common/progress-registry.md). The pre-write is what makes
   `/architect:report-status` show the phase as running and what attributes its token cost
   to it; `plugin` is what keeps that attribution off the product pipeline's phase of the
   same name. On the handoff path this file already holds product's phases — add to it,
   never re-register it
5. After `investigate`: when the technology stack reports a presentation layer, offer UI analysis
   and UX evaluation (see UI Analysis Option), then run `analyze-ui` before `analyze` and
   `evaluate-ux` alongside the other evaluations
6. After `redesign`: offer Domain Story generation, aggregate design and state transition
   modeling in one question (see the three Option sections above), then run what the user
   selected — `create-domain-story`, then `design-aggregate`, then `design-state-machine` —
   before `design-microservices` and the data/API design phases
7. Accumulate findings in `work/context.md` between phases
8. Determine which phases to skip if not applicable

After `design-api`, read canonical `reports/03_design/api-style-decisions.json`. Run
`design-graphql` when any surface selects GraphQL/hybrid and mark it conditionally skipped only when
the validated canonical document is REST-only. Invalid canonical JSON blocks progression; it is
never a REST default. A skipped conditional dependency is satisfied for the review phases.

## Phase Execution

A skill's own `model` takes effect only when the user types its command. Run from here with the
Skill tool, a phase runs on whatever this conversation runs on — which is why this skill declares
`model: inherit` rather than a tier of its own: it would otherwise pull every inline phase down to
it. Two ways of running a phase follow, and which one applies is read off the phase's signature.

**Dialogue-driven phases run inline**, with the Skill tool, on the session's model. These are the
phases whose `argument-hint` offers `--auto` — `define-requirements`, `analyze-ui`, `evaluate-ux`,
`create-domain-story`, `design-aggregate`, `design-state-machine` — because a phase that can be
told not to ask is a phase that otherwise does, and only the main conversation can ask the user.
All but two of them are assigned opus: say so once, before the first of them, when the session is
on a smaller model, and suggest `/model opus` — do not push a design dialogue through on less.

**Every other phase runs as a sub-agent on its manifest model**, so that `analyze`, `redesign` and
the `design-*` phases get opus and `report` gets haiku whatever the session is on:

```
Agent(
  subagent_type: "general-purpose",
  model: "{phase_model}",
  run_in_background: false,
  description: "{phase}",
  prompt: "Run the phase `{phase}` of the nexus-architect pipeline.
           Project directory: {project_dir} — every `reports/`, `work/` and `generated/` path is
           relative to it, not to the directory the skill file lives in.
           Invoke the skill `architect:{phase}` with the Skill tool, with these arguments:
           {arguments}, and follow it to completion.
           You cannot ask the user. Where the skill would ask, do what
           @rules/open-questions.md §5 says for an unasked question: record it in the store with
           status `unasked`, its question text and the options you would have offered, write
           `TBD (OQ-###)` at the placeholder, and continue.
           Where the skill has you spawn sub-agents of your own, pass `run_in_background: false`
           on each and do not finish until they have returned and the phase's outputs are written.
           Do not write this phase's entry in work/pipeline-progress.json — the orchestrator does.
           Reply with: the files you wrote, a two-line summary of what the phase concluded, and
           the `OQ-` IDs you recorded. If the phase could not complete, say so and why."
)
```

`{phase_model}` is the phase's `model` in @skills/common/skill-dependencies.yaml, read at the moment
of the call. Phases the manifest marks `parallel_with` each other start in one message.

Keep these sub-agents in the foreground — `run_in_background: false` on every call, the calls of a
parallel group included — and do not end the turn while one is running: the next step needs its
result, a non-interactive run stops background work ten minutes after the turn ends, and a phase
whose own sub-agents went to the background returns with nothing written
(@skills/pipeline/SKILL.md § Phase Execution has the measurements).

**Then ask what the phase could not.** This run is interactive even where a phase was not: when a
sub-agent returns `OQ-` IDs, put those questions to the user before the next phase starts — one
`AskUserQuestion` batch, reusing the recorded options (@rules/open-questions.md §7). Update each
entry in place in `work/context.md` § Open Questions, substitute the answer at every `TBD (OQ-###)`
the phase wrote, and re-render any view that shows it. What the user defers stays `deferred` with
its owner. A question left `unasked` at the end of an interactive run is a defect.

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
