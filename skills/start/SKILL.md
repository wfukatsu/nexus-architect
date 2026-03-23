---
name: start
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

## Workflow Selection Criteria

- User presents an existing codebase -> **Legacy refactoring path**
- User describes requirements only -> **Greenfield design path**
- Unclear -> Ask one clarifying question, then proceed with execution

## ScalarDB Usage Decision

- Multi-DB distributed transactions required -> Include ScalarDB skills
- User mentions ScalarDB / Scalar / distributed transactions -> Include
- Otherwise -> Use the design-data-layer alternative path

## Execution Flow

1. Evaluate project context (read provided materials, inspect codebase)
2. Determine the path and relevant phases
3. Run `/architect:init-output` to initialize the output directory
4. Execute skills in dependency order per `skill-dependencies.yaml`
5. Accumulate findings in `work/context.md` between phases
6. Determine which phases to skip if not applicable

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
- Unresolved questions

## Dependency Manifest

Read @skills/common/skill-dependencies.yaml to determine execution order.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:pipeline | Automated execution version |
| /architect:init-output | Initialization |
