---
name: investigate
description: |
  Comprehensive investigation of the target system covering technology stack, codebase structure, technical debt, and DDD readiness.
  /architect:investigate [target_path] to invoke.
  Used as the first step in legacy system analysis.
model: sonnet
user_invocable: true
---

# System Investigation

## Outcome

Gain a comprehensive understanding of the target system and generate the following four investigation reports:
1. **Technology Stack Analysis** — Languages, frameworks, libraries, external services
2. **Codebase Structure** — Directory layout, module structure, entry points
3. **Issues and Technical Debt** — Problem identification and severity classification (CRITICAL/High/Medium/Low)
4. **DDD Readiness** — Assessment of readiness for migration to domain-driven design

## Judgment Criteria

- Prioritize deep-diving into areas where technical debt is most concentrated
- Especially flag coupling issues that hinder domain decomposition
- Evaluate DDD readiness based on evidence (not speculation)
- Record any security concerns found

## Prerequisites

| File | Required/Recommended | Description |
|------|---------------------|-------------|
| target_path (argument) | Required | Path to the codebase under investigation |

## Available Resources

- **Serena MCP** — AST analysis via `get_symbols_overview`, `find_symbol` (preferred)
- **Glob/Grep** — File pattern search, keyword search within code
- **Read** — Reading configuration files and dependency definition files
- **Task(Explore)** — Parallel investigation of large codebases

## Output

Write output files immediately upon completing each section:

| File | Content |
|------|---------|
| `reports/before/{project}/technology-stack.md` | Technology stack inventory and assessment |
| `reports/before/{project}/codebase-structure.md` | Directory and module structure |
| `reports/before/{project}/issues-and-debt.md` | Technical debt and issues list |
| `reports/before/{project}/ddd-readiness.md` | DDD readiness assessment |

All output files must include YAML frontmatter (title, schema_version: 1, phase, skill, generated_at).

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

## Completion

1. All four output files have been written
2. Update investigate-system in pipeline-progress.json to "completed"
3. Report a summary of findings and any unresolved concerns

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:analyze | Downstream (uses these investigation results as input) |
| /architect:investigate-security | Related (detailed security investigation) |
