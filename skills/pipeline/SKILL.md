---
description: |
  Automated pipeline that executes all phases in dependency order.
  /architect:pipeline [target_path].
  Supports --skip-*, --resume-from, --rerun-from, --lang flags.
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
3. **Product handoff detection** — glob `reports/03_domain/`, `reports/04_quality/`, `reports/02_spec/` and `work/traceability.json`. If product artifacts exist, run `define-requirements` first with them as inputs (the product→architect handoff, @docs/design.md §1); it auto-detects and carries product IDs forward. Otherwise run the standard greenfield/legacy entry.
4. Execute each skill and verify its output before proceeding to the next
5. Execute skills with `parallel_with` in parallel via Task
6. Enable or disable ScalarDB-related skills based on the `conditions` field
7. Record progress in `work/pipeline-progress.json`
8. Accumulate findings in `work/context.md` between phases

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
- Unresolved issues
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
