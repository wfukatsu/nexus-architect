---
description: |
  Automated pipeline that executes all phases in dependency order.
  /architect:pipeline [target_path] [--skip-{phase}] [--resume-from=phase-N] [--rerun-from=phase-N]
  [--analyze-only] [--no-scalardb] [--lang=en|ja] to invoke.
model: sonnet
user_invocable: true
disable-model-invocation: true
---

# Full Pipeline Execution

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
4. Execute each skill and verify its output before proceeding to the next
5. Execute skills with `parallel_with` in parallel via Task
6. Enable or disable conditional skills based on the `conditions` field: ScalarDB/data-layer from
   `scalardb_enabled`, and `design-graphql` directly from GraphQL/hybrid surfaces in canonical
   `reports/03_design/api-style-decisions.json`. Before that artifact exists, a legacy
   `options.api_style_graphql` is only a compatibility fallback. Invalid canonical JSON is a
   blocking error and must never be interpreted as REST-only.
7. Phases the manifest marks `optional: true` may be skipped without failing the run. Three of them
   are dialogue-driven (`create-domain-story`, `design-aggregate`, `design-state-machine`) and an automated run has
   nobody to facilitate with: invoke those with `--auto` and record what that mode had to assume.
   When the inputs show no evidence for an optional phase — no domain to narrate, no invariant
   spanning more than one attribute (nothing to make an aggregate of), no aggregate with a
   lifecycle, no data model to analyze — record it `skipped` with the reason in `summary`
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
| /architect | Interactive version |
| /architect:init-output | Initialization |
| /architect:report | Final report |
| /product:start | Upstream — product reports are detected at step 3 and handed off via define-requirements (@docs/design.md §1) |
