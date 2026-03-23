---
name: analyze
description: |
  Extract ubiquitous language, actor-role-permission matrix, and domain-code mapping.
  /architect:analyze [target_path] to invoke.
  Requires investigate-system output as a prerequisite.
model: opus
user_invocable: true
---

# System Analysis

## Outcome

Structure the domain knowledge of the target system and generate the following four analysis documents:
1. **System Overview** — Business context, key features, system boundaries
2. **Ubiquitous Language** — Domain term dictionary (term, definition, code correspondence, usage context)
3. **Actors, Roles, and Permissions** — User types, role definitions, permission matrix
4. **Domain-Code Mapping** — Correspondence between domain concepts and code implementations

## Judgment Criteria

- Cross-reference ubiquitous language with actual naming in the code
- Detect cases where the same concept uses different names
- Identify gaps in domain-code mapping (domain concepts not reflected in code)
- Track where business rules are implemented in the code

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/before/{project}/ | Required | /architect:investigate |

## Available Resources

- **Serena MCP** — Symbol relationship analysis via `find_symbol`, `find_referencing_symbols` (preferred)
- **Glob/Grep** — Search for domain terms within code
- **Read** — Extract domain knowledge from documentation, comments, and test cases
- **Task(Explore)** — Parallel entity extraction across large codebases

## Output

| File | Content |
|------|---------|
| `reports/01_analysis/system-overview.md` | Business context, feature list |
| `reports/01_analysis/ubiquitous-language.md` | Domain term dictionary |
| `reports/01_analysis/actors-roles-permissions.md` | Actor, role, and permission matrix |
| `reports/01_analysis/domain-code-mapping.md` | Domain-code correspondence table |

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

## Completion

1. All four output files have been written
2. Ubiquitous language contains at least 20 domain terms
3. Update pipeline-progress.json

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:investigate | Upstream (input source) |
| /architect:evaluate-mmi | Downstream |
| /architect:evaluate-ddd | Downstream |
| /architect:analyze-data-model | Downstream |
