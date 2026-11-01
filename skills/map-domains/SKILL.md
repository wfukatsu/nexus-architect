---
description: |
  Classify an existing system's domains (core, supporting, generic), its business structure and
  service boundary types, and map the relationships between bounded contexts.
model: opus
---

# Domain Mapping

Shared files: a path written `@rules/…`, `@skills/…`, `@templates/…` or `@docs/…` is relative to the
plugin root, `${CLAUDE_PLUGIN_ROOT}` — not to the project being worked on. Read it from there.

## Desired Outcome

- Domain classification (Core/Supporting/Generic subdomains)
- Business structure type identification (Pipeline/Blackboard/Dialogue/Hybrid)
- Microservice boundary classification (Process/Master/Integration/Supporting)
- Relationship map between bounded contexts

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/01_analysis/ | Recommended | /architect:analyze |

## Output

| File | Content |
|------|---------|
| `reports/03_design/domain-analysis.md` | Domain classification, structure types, boundary map |

Output language and frontmatter: @rules/output-conventions.md.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:analyze | Input source |
| /architect:redesign | Output destination |
