---
name: evaluate-ddd
description: |
  Evaluate DDD principle conformance across 3 layers and 12 criteria.
  /architect:evaluate-ddd [target_path] to invoke.
  Requires analyze-system output as a prerequisite. Can run in parallel with evaluate-mmi.
model: sonnet
user_invocable: true
---

# DDD Evaluation

## Desired Outcome

Quantitatively evaluate the target system's conformance to DDD principles across 3 layers and 12 criteria.

## Decision Criteria

For detailed scoring criteria, refer to:
@rules/evaluation-frameworks.md

- Strategic Design (30%): Ubiquitous language, bounded contexts, subdomain classification
- Tactical Design (45%): Value objects, entities, aggregates, repositories, domain services, domain events
- Architecture (25%): Layering, dependency direction, ports & adapters

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/01_analysis/ | Required | /architect:analyze |

## Output

| File | Content |
|------|---------|
| `reports/02_evaluation/ddd-strategic-evaluation.md` | Strategic design evaluation |
| `reports/02_evaluation/ddd-tactical-evaluation.md` | Tactical design + architecture evaluation |

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:analyze | Input source |
| /architect:evaluate-mmi | Parallel execution |
| /architect:integrate-evaluations | Output destination |
