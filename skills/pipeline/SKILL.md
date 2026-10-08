---
description: |
  Automated pipeline that executes all phases in dependency order.
argument-hint: '[target_path] [--skip-{phase}] [--resume-from=phase-N] [--rerun-from=phase-N] [--analyze-only] [--no-scalardb] [--lang=en|ja]'
model: sonnet
disable-model-invocation: true
---

# Full Pipeline Execution

Shared files: a path written `@rules/…`, `@skills/…`, `@templates/…` or `@docs/…` is relative to the
plugin root, `${CLAUDE_PLUGIN_ROOT}` — not to the project being worked on. Read it from there.

**Usage:** `/architect:pipeline [target_path] [--skip-{phase}] [--resume-from=phase-N] [--rerun-from=phase-N] [--analyze-only] [--no-scalardb] [--lang=en|ja]`

## Expected Outcome

Complete the core architecture analysis and design pipeline for the target project:
investigation through evaluation, redesign, target architecture, data/API design, the
5-perspective review, and the consolidated HTML report. The final deliverables are the
reports under reports/ produced by the phases in the dependency manifest.

## Available Skills

The pipeline executes the phases defined in @skills/common/skill-dependencies.yaml in
dependency order. Skills outside the manifest (infrastructure, security, observability,
disaster recovery, implementation specs, test specs, code generation, cost estimation)
are a **manual extension tier**: run them individually after the pipeline completes, or
via `/architect:start`, which can sequence them interactively. They are intentionally not
part of the automated run.

## Execution Strategy

1. Load the dependency graph from `skill-dependencies.yaml`
2. Initialize output directories with `/architect:init-output`
3. **Product handoff detection** — glob the same set `define-requirements` ingests: `reports/00_core/`, `reports/01_ux/`, `reports/02_spec/`, `reports/03_domain/`, `reports/04_quality/` and `work/traceability.json`. Keep the two sets identical — a run that stopped early (`--profile=mvp` writes only `reports/00_core/`) is still a handoff. Match **files**, not directories: `/product:init-output` creates `reports/01_ux/domain-stories/` and `reports/02_spec/ui-mocks/` empty, so a directory test passes on any initialized product project. If product artifacts exist, run `define-requirements` first with them as inputs (the product→architect handoff, @docs/design.md §1); it auto-detects and carries product IDs forward. Otherwise run the standard greenfield/legacy entry.
4. Execute each phase **as a sub-agent**, never inline, and verify its output before proceeding to
   the next — see Phase Execution below for the call and for why
5. Start the phases of a `parallel_with` group in one message, one sub-agent each, and wait for all
   of them before the next phase
6. Enable or disable conditional skills based on the `conditions` field: ScalarDB/data-layer from
   `scalardb_enabled`, and `design-graphql` directly from GraphQL/hybrid surfaces in canonical
   `reports/03_design/api-style-decisions.json`. Before that artifact exists, a legacy
   `options.api_style_graphql` is only a compatibility fallback. Invalid canonical JSON is a
   blocking error and must never be interpreted as REST-only.
7. Phases the manifest marks `optional: true` may be skipped without failing the run. Three of them
   are dialogue-driven (`create-domain-story`, `design-aggregate`, `design-state-machine`) and an automated run has
   nobody to facilitate with: invoke those with `--auto` and record what that mode had to assume. `analyze-ui` and
   `evaluate-ux` run with `--auto` too, and `evaluate-ux` never with `--base-url`: an automated run
   evaluates the UI statically.
   When the inputs show no evidence for an optional phase — no domain to narrate, no invariant
   spanning more than one attribute (nothing to make an aggregate of), no aggregate with a
   lifecycle, no data model to analyze, no presentation layer (the technology stack reports none and
   no templates or routed views exist), no UI inventory to evaluate — record it `skipped` with the reason in `summary`
   rather than emitting a document derived from nothing. An optional phase that was skipped or
   never ran does not block its dependents: `design-state-machine` depends on `design-aggregate`
   for ordering, not for existence, and runs from `redesign` alone when there is no aggregate
   manifest (the dashboard applies the same rule).
8. Record progress in `work/pipeline-progress.json` **twice per phase**: set
   `status: "in_progress"` with `plugin: "architect"` and `started_at` *before* invoking
   the skill (all of them at once for a parallel group), then `completed` / `failed` /
   `skipped` with `completed_at`, `outputs` and `summary` once it returns. The pre-write
   is the only signal that a phase is running while it runs — `/architect:report-status`
   renders it, and the token-usage hook attributes cost to whatever is `in_progress`,
   using `plugin` to keep the two pipelines' spend separable under the four phase names
   both manifests define. The product pipeline writes this same file, so never re-register
   or reset an entry that is not this manifest's — including under `--rerun-from`
   (@skills/common/progress-registry.md § One Registry, Two Pipelines)
9. Accumulate findings in `work/context.md` between phases

## Phase Execution

Every phase of the manifest runs in its own sub-agent, on the manifest's `model` for that phase:

```
Task(
  subagent_type: "general-purpose",
  model: "{phase_model}",
  description: "{phase}",
  prompt: "Run the phase `{phase}` of the nexus-architect pipeline.
           Project directory: {project_dir} — every `reports/`, `work/` and `generated/` path is
           relative to it, not to the directory the skill file lives in.
           Invoke the skill `architect:{phase}` with the Skill tool, with these arguments:
           {arguments}, and follow it to completion.
           This is a non-interactive run and you cannot ask the user. Where the skill would ask,
           do what @rules/open-questions.md §5 says for an unasked question: record it in the
           store with status `unasked`, its question text and the options you would have offered,
           write `TBD (OQ-###)` at the placeholder, and continue.
           Do not write this phase's entry in work/pipeline-progress.json — the orchestrator does.
           Reply with: the files you wrote, a two-line summary of what the phase concluded, and
           the `OQ-` IDs you recorded. If the phase could not complete, say so and why."
)
```

`{phase_model}` is the phase's `model` in @skills/common/skill-dependencies.yaml, read at the moment
of the call — never a value remembered from this file. `{arguments}` are the target path and the
options this run was given that the phase's own signature accepts, plus `--auto` for every phase
whose signature offers it (step 7).

Why a sub-agent and not the Skill tool directly: a skill's `model` takes effect only when the user
types its command. Invoked from here it would run on this orchestrator's `sonnet`, whatever tier it
is assigned — the opus phases (`analyze`, `redesign`, every `design-*`, `review-risk`,
`review-api-security`) downgraded, `report` upgraded. A sub-agent runs on the `model` passed on the
call (measured: @skills/common/sub-agent-patterns.md § Always pass `model`), and a phase run this
way may still spawn the sub-agents its own skill describes. It also keeps each phase's working
context out of this one, which is what lets a long run finish.

What stays with the orchestrator, inline: reading the manifest, `/architect:init-output`, the
handoff detection of step 3, deciding which phases run (steps 6–7), every write to
`work/pipeline-progress.json` (step 8), and checking that the outputs a phase declared exist before
the next phase starts. A phase whose sub-agent reports failure, or whose declared outputs are
missing, is `failed`.

The cost of this is that no phase can ask the user anything, which is what an automated run means:
the questions are in `work/context.md` § Open Questions as `unasked` when it ends, and
`/architect:start` is the orchestrator for a run that should stop and ask.

## Command-Line Options

- `--skip-{phase}`: Skip the specified phase
- `--resume-from=phase-N`: Resume from the specified phase (completed phases are skipped)
- `--rerun-from=phase-N`: Reset all phases from the specified phase onward to "pending" and re-execute
- `--analyze-only`: Execute analysis phases only
- `--no-scalardb`: Skip all ScalarDB-related skills
- `--lang=en|ja`: Set the output language (default: en). Stored in pipeline-progress.json options.output_language

## Error Handling

- **Missing required prerequisite files**: Log the error and automatically skip downstream phases
- **Skill execution failure**: Record status: "failed" in pipeline-progress.json
- **Dependency phase failure** (status: "failed"): Automatically skip downstream phases

## Conditional Dependency Resolution

A phase listed in another phase's `depends_on` may be marked `status: "skipped"`
because its `conditions:` did not match the current project (e.g. `review-data-integrity`
when `scalardb_enabled` is true). When resolving `depends_on`:

- Treat conditional `skipped` dependencies as **satisfied** (filter them out).
- Only `failed` dependencies cascade as downstream skips.
- This is what enables `review-synthesizer` to run after exactly one of
  `review-scalardb` / `review-data-integrity` (the other is conditionally skipped).

## Context Management

Long pipelines may exceed context window limits.
Update `work/context.md` upon each phase completion and read it at the start of the next phase.

```
work/context.md structure:
- Investigation results summary
- Domain knowledge extracted from analysis
- Evaluation scores and improvement priorities
- Important decisions made during design
- Open Questions (`OQ-` ID, status, owner) — carried across phases; the phase that needs an answer
  re-asks it and updates the entry in place (@rules/open-questions.md)
```

## Progress Registry

Conforms to the schema defined in @skills/common/progress-registry.md.

## Completion Criteria

1. All phases are either completed or skipped
2. `reports/00_summary/full-report.html` has been generated
3. pipeline-progress.json status is "completed"

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:start | Interactive version — phases that ask the user run there, not here |
| /architect:init-output | Initialization |
| /architect:report | Final report |
| /product:start | Upstream — product reports are detected at step 3 and handed off via define-requirements (@docs/design.md §1) |
