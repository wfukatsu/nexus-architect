---
description: |
  Evaluate DDD principle conformance across 3 layers and 12 criteria.
  /architect:evaluate-ddd [target_path] to invoke.
  Requires analyze output as a prerequisite. Can run in parallel with evaluate-mmi.
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

## Execution

### Step 1: Collect Input File Paths

Glob for all analysis documents: `reports/01_analysis/**/*.md`

Record the full list of found file paths — these will be passed to all sub-agents.

### Step 2: Spawn Three Parallel Layer Evaluators

In a **single message**, issue all three Task() calls simultaneously so they run in parallel.
Each evaluator assesses its specific DDD layer independently.

**Task A — Strategic Design Layer (criteria 1-3)**
```
Task(
  subagent_type: "general-purpose",
  description: "DDD strategic design layer evaluation",
  prompt: """
You are a DDD expert evaluating the STRATEGIC DESIGN layer (30% of total DDD score).

Read all analysis documents using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate these 3 Strategic Design criteria, each scored 1-5:
(5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical)

1. **Ubiquitous Language**: Is domain terminology consistent between business and code? Are the same concepts named the same way everywhere?
2. **Bounded Context**: Are context boundaries clear with explicit responsibility separation? Is context mapping documented?
3. **Subdomain Classification**: Are Core/Supporting/Generic subdomains identified? Is investment level aligned with subdomain importance?

Return ONLY this JSON (no markdown fences, no explanation):
{
  "layer": "Strategic Design",
  "weight": 0.30,
  "criteria": [
    {
      "id": 1,
      "name": "Ubiquitous Language",
      "score": <integer 1-5>,
      "rationale": "<1-2 sentence explanation>",
      "findings": ["<specific issue or positive observation>"]
    },
    {
      "id": 2,
      "name": "Bounded Context",
      "score": <integer 1-5>,
      "rationale": "<1-2 sentence explanation>",
      "findings": ["<specific issue or positive observation>"]
    },
    {
      "id": 3,
      "name": "Subdomain Classification",
      "score": <integer 1-5>,
      "rationale": "<1-2 sentence explanation>",
      "findings": ["<specific issue or positive observation>"]
    }
  ],
  "layer_avg": <average of 3 scores, 1 decimal>,
  "layer_weighted_contribution": <layer_avg × 0.30, 2 decimals>
}
"""
)
```

**Task B — Tactical Design Layer (criteria 4-9)**
```
Task(
  subagent_type: "general-purpose",
  description: "DDD tactical design layer evaluation",
  prompt: """
You are a DDD expert evaluating the TACTICAL DESIGN layer (45% of total DDD score).

Read all analysis documents using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate these 6 Tactical Design criteria, each scored 1-5:
(5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical)

4. **Value Objects**: Are value objects immutable? Do they encapsulate domain rules? Are equality semantics value-based?
5. **Entities**: Do entities have stable identifiers? Is lifecycle management explicit?
6. **Aggregates**: Are transaction boundaries defined by aggregate roots? Are consistency invariants enforced within aggregates?
7. **Repositories**: Do repositories abstract persistence? Do they use collection semantics (not query-builder exposure)?
8. **Domain Services**: Are stateless cross-aggregate operations placed in domain services? Are they distinct from application services?
9. **Domain Events**: Are state changes published as domain events? Is event-driven design used for cross-context communication?

Return ONLY this JSON (no markdown fences, no explanation):
{
  "layer": "Tactical Design",
  "weight": 0.45,
  "criteria": [
    {
      "id": 4,
      "name": "Value Objects",
      "score": <integer 1-5>,
      "rationale": "<1-2 sentence explanation>",
      "findings": ["<specific issue or positive observation>"]
    },
    {
      "id": 5,
      "name": "Entities",
      "score": <integer 1-5>,
      "rationale": "<1-2 sentence explanation>",
      "findings": ["<specific issue or positive observation>"]
    },
    {
      "id": 6,
      "name": "Aggregates",
      "score": <integer 1-5>,
      "rationale": "<1-2 sentence explanation>",
      "findings": ["<specific issue or positive observation>"]
    },
    {
      "id": 7,
      "name": "Repositories",
      "score": <integer 1-5>,
      "rationale": "<1-2 sentence explanation>",
      "findings": ["<specific issue or positive observation>"]
    },
    {
      "id": 8,
      "name": "Domain Services",
      "score": <integer 1-5>,
      "rationale": "<1-2 sentence explanation>",
      "findings": ["<specific issue or positive observation>"]
    },
    {
      "id": 9,
      "name": "Domain Events",
      "score": <integer 1-5>,
      "rationale": "<1-2 sentence explanation>",
      "findings": ["<specific issue or positive observation>"]
    }
  ],
  "layer_avg": <average of 6 scores, 1 decimal>,
  "layer_weighted_contribution": <layer_avg × 0.45, 2 decimals>
}
"""
)
```

**Task C — Architecture Layer (criteria 10-12)**
```
Task(
  subagent_type: "general-purpose",
  description: "DDD architecture layer evaluation",
  prompt: """
You are a DDD expert evaluating the ARCHITECTURE layer (25% of total DDD score).

Read all analysis documents using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate these 3 Architecture criteria, each scored 1-5:
(5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical)

10. **Layering**: Is the layer structure (Domain / Application / Infrastructure / Presentation) clear and consistently applied?
11. **Dependency Direction**: Do dependencies point inward (toward domain)? Is the Dependency Inversion Principle applied?
12. **Ports & Adapters**: Are external system connections abstracted via interfaces (ports)? Are concrete adapters kept in the infrastructure layer?

Return ONLY this JSON (no markdown fences, no explanation):
{
  "layer": "Architecture",
  "weight": 0.25,
  "criteria": [
    {
      "id": 10,
      "name": "Layering",
      "score": <integer 1-5>,
      "rationale": "<1-2 sentence explanation>",
      "findings": ["<specific issue or positive observation>"]
    },
    {
      "id": 11,
      "name": "Dependency Direction",
      "score": <integer 1-5>,
      "rationale": "<1-2 sentence explanation>",
      "findings": ["<specific issue or positive observation>"]
    },
    {
      "id": 12,
      "name": "Ports & Adapters",
      "score": <integer 1-5>,
      "rationale": "<1-2 sentence explanation>",
      "findings": ["<specific issue or positive observation>"]
    }
  ],
  "layer_avg": <average of 3 scores, 1 decimal>,
  "layer_weighted_contribution": <layer_avg × 0.25, 2 decimals>
}
"""
)
```

### Step 3: Compute DDD Score and Write Outputs

After all three Tasks complete, compute the composite DDD score:

```
DDD Score = (Task A layer_weighted_contribution + Task B layer_weighted_contribution + Task C layer_weighted_contribution) / 5 × 100
```

DDD maturity levels:
- 80-100 → Strong DDD alignment
- 60-80  → Moderate alignment, targeted improvements needed
- 40-60  → Weak alignment, significant refactoring required
- 0-40   → Minimal DDD adoption

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

**`reports/02_evaluation/ddd-strategic-evaluation.md`** — Strategic design evaluation (Task A result):

```markdown
---
title: "DDD Evaluation: Strategic Design"
schema_version: 1
phase: "Phase 2: Evaluation"
skill: evaluate-ddd
generated_at: "<ISO-8601>"
input_files:
  - reports/01_analysis/
---

# DDD Strategic Design Evaluation

## Layer Score: <layer_avg>/5 (weighted contribution: <layer_weighted_contribution × 100>%)

## Criteria Scores

| # | Criterion | Score | Rationale |
|---|-----------|-------|-----------|
| 1 | Ubiquitous Language | <score>/5 | <rationale> |
| 2 | Bounded Context | <score>/5 | <rationale> |
| 3 | Subdomain Classification | <score>/5 | <rationale> |

## Findings

[Detailed findings from Task A, organized by criterion]

## Improvement Recommendations

[Top 3 actionable improvements for the strategic design layer]
```

**`reports/02_evaluation/ddd-tactical-architecture-evaluation.md`** — Tactical design + architecture evaluation (Task B + Task C results):

```markdown
---
title: "DDD Evaluation: Tactical Design and Architecture"
schema_version: 1
phase: "Phase 2: Evaluation"
skill: evaluate-ddd
generated_at: "<ISO-8601>"
input_files:
  - reports/01_analysis/
---

# DDD Tactical Design and Architecture Evaluation

## Overall DDD Score: <DDD Score>% (<maturity level>)

## Tactical Design Layer: <layer_avg>/5 (weight: 45%)

| # | Criterion | Score | Rationale |
|---|-----------|-------|-----------|
| 4 | Value Objects | <score>/5 | <rationale> |
| 5 | Entities | <score>/5 | <rationale> |
| 6 | Aggregates | <score>/5 | <rationale> |
| 7 | Repositories | <score>/5 | <rationale> |
| 8 | Domain Services | <score>/5 | <rationale> |
| 9 | Domain Events | <score>/5 | <rationale> |

## Architecture Layer: <layer_avg>/5 (weight: 25%)

| # | Criterion | Score | Rationale |
|---|-----------|-------|-----------|
| 10 | Layering | <score>/5 | <rationale> |
| 11 | Dependency Direction | <score>/5 | <rationale> |
| 12 | Ports & Adapters | <score>/5 | <rationale> |

## Findings

[Detailed findings from Tasks B and C, organized by criterion]

## Improvement Recommendations

[Top 5 actionable improvements for tactical design and architecture layers]
```

## Output

| File | Content |
|------|---------|
| `reports/02_evaluation/ddd-strategic-evaluation.md` | Strategic design evaluation |
| `reports/02_evaluation/ddd-tactical-architecture-evaluation.md` | Tactical design + architecture evaluation |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:analyze | Input source |
| /architect:evaluate-mmi | Parallel execution |
| /architect:integrate-evaluations | Output destination |
