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

## Workflow Selection Criteria

- User presents an existing codebase -> **Legacy refactoring path**
- User describes requirements only -> **Greenfield design path**: run `/architect:define-requirements` first to fix the requirements baseline (pass any user-provided documents via `--input`), then proceed with the design phases
- Unclear -> Ask one clarifying question, then proceed with execution

## ScalarDB Usage Decision

- `reports/00_requirements/scalardb-applicability.md` exists -> Use its verdict as the primary basis
- Otherwise, fall back to heuristics:
  - Multi-DB distributed transactions required -> Include ScalarDB skills
  - User mentions ScalarDB / Scalar / distributed transactions -> Include
  - Otherwise -> Use the design-data-layer alternative path

## Domain Story Option

After `/architect:redesign` completes, ask the user:

> "Would you like to generate Domain Stories for specific bounded contexts? Domain Storytelling visualizes the business process of each domain as a narrative with actors, work items, and a sequence diagram."

If yes, ask which domains to cover (present the bounded context list from `bounded-contexts-redesign.md`), then run `/architect:create-domain-story --domain=<name>` for each selected domain before proceeding to `design-microservices`.

## Execution Flow

1. Evaluate project context (read provided materials, inspect codebase)
2. Determine the path and relevant phases
3. Run `/architect:init-output` to initialize the output directory
4. Execute skills in dependency order per `skill-dependencies.yaml`
5. After `redesign`: offer Domain Story generation (see Domain Story Option above)
6. Accumulate findings in `work/context.md` between phases
7. Determine which phases to skip if not applicable

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
| /architect:define-requirements | Greenfield entry point — requirements baseline and ScalarDB applicability |
