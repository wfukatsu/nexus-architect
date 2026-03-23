---
name: map-domains
description: |
  Domain classification, bounded context mapping, and business structure identification.
  /architect:map-domains to invoke.
model: opus
user_invocable: true
---

# Domain Mapping

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

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:analyze | Input source |
| /architect:redesign | Output destination |
