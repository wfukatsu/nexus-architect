---
name: pipeline
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

Complete a comprehensive architecture analysis and design for the target project.
The final deliverables are a complete set of reports under reports/.

## Available Skills

All skills defined in @skills/common/skill-dependencies.yaml can be executed in dependency order.

## Execution Strategy

1. Load the dependency graph from `skill-dependencies.yaml`
2. Initialize output directories with `/architect:init-output`
3. Execute each skill and verify its output before proceeding to the next
4. Execute skills with `parallel_with` in parallel via Task
5. Enable or disable ScalarDB-related skills based on the `conditions` field
6. Record progress in `work/pipeline-progress.json`
7. Accumulate findings in `work/context.md` between phases

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
- **Dependency phase failure**: Automatically skip downstream phases

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
2. `reports/00_summary/executive-summary.md` has been generated
3. pipeline-progress.json status is "completed"

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect | Interactive version |
| /architect:init-output | Initialization |
| /architect:report | Final report |
