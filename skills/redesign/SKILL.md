---
name: redesign
description: |
  Redesign bounded contexts, define aggregates, and generate context maps.
  /architect:redesign to invoke. Requires integrate-evaluations output as a prerequisite.
model: opus
user_invocable: true
---

# DDD Redesign

## Desired Outcome

Based on evaluation results, formulate a new bounded context design:
1. **Bounded Context Redesign** -- Responsibilities of each BC, contained aggregates, public interfaces
2. **Context Map** -- Relationship patterns between BCs (ACL, OHS, Conformist, etc.) as Mermaid diagrams

## Decision Criteria

- Each BC must have a single, clear responsibility
- Minimize dependencies between BCs
- Reflect subdomain classification that invests most in the core domain
- Consider incremental migration paths from the existing system

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/02_evaluation/unified-improvement-plan.md | Required | /architect:integrate-evaluations |
| reports/01_analysis/ubiquitous-language.md | Recommended | /architect:analyze |

## Output

| File | Content |
|------|---------|
| `reports/03_design/bounded-contexts-redesign.md` | BC definitions, aggregate list, responsibilities |
| `reports/03_design/context-map.md` | Context map (Mermaid diagram) |

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:integrate-evaluations | Input source |
| /architect:design-microservices | Output destination |
| /architect:map-domains | Related |
