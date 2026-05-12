---
description: |
  Qualitative evaluation of Modularity Maturity Index across 4 axes: cohesion, coupling, independence, reusability.
  /architect:evaluate-mmi [target_path] to invoke.
  Requires analyze output as a prerequisite. Can run in parallel with evaluate-ddd.
model: sonnet
user_invocable: true
---

# MMI Evaluation

## Desired Outcome

Evaluate each module of the target system across the 4 MMI axes and determine microservice readiness.

## Decision Criteria

For detailed scoring criteria and algorithms, refer to:
@rules/evaluation-frameworks.md

- 4 axes: Cohesion (30%), Coupling (30%), Independence (20%), Reusability (20%)
- Each axis scored 1-5
- MMI = (0.3 × C + 0.3 × K + 0.2 × I + 0.2 × R) / 5 × 100
- Maturity: 80-100 (Ready), 60-80 (Moderate), 40-60 (Needs Improvement), 0-40 (Immature)

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/01_analysis/ | Required | /architect:analyze |

## Execution

### Step 1: Identify Modules

Glob for `reports/before/**/codebase-structure.md` to find the investigate-phase output, then read the found file. Also read `reports/01_analysis/domain-code-mapping.md`. Extract the list of modules to evaluate and record module names — these will be passed to sub-agents.

### Step 2: Collect Input File Paths

Glob for all analysis documents: `reports/01_analysis/**/*.md`

Record the full list of found file paths — these will be passed to all sub-agents.

### Step 3: Spawn Four Parallel Axis Evaluators

In a **single message**, issue all four Task() calls simultaneously so they run in parallel.
Each evaluator scores ALL identified modules on its specific axis.

**Task A — Cohesion Axis**
```
Task(
  subagent_type: "general-purpose",
  description: "MMI cohesion axis evaluation for all modules",
  prompt: """
You are evaluating COHESION (functional coherence within a module) for each module in a software system.

Modules to evaluate:
<MODULE_LIST>
[Insert the module names identified in Step 1, one per line]
</MODULE_LIST>

Read all analysis documents using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 2, one per line]
</FILE_LIST>

For each module, score its Cohesion on a scale of 1-5:
- 5 (Exemplary): Single clear responsibility, all components tightly related, no leakage
- 4 (Good): Minor mixed concerns but mostly cohesive
- 3 (Acceptable): Some mixed responsibilities, identifiable but imperfect boundaries
- 2 (Concerning): Multiple unrelated responsibilities coexist
- 1 (Critical): No clear responsibility, god-class or utility-dumping-ground pattern

Return ONLY this JSON (no markdown fences, no explanation):
{
  "axis": "Cohesion",
  "weight": 0.30,
  "modules": [
    {
      "name": "<module name>",
      "score": <integer 1-5>,
      "rationale": "<1-2 sentence explanation>"
    }
  ]
}
"""
)
```

**Task B — Coupling Axis**
```
Task(
  subagent_type: "general-purpose",
  description: "MMI coupling axis evaluation for all modules",
  prompt: """
You are evaluating COUPLING (degree of inter-module dependencies) for each module in a software system.

Modules to evaluate:
<MODULE_LIST>
[Insert the module names identified in Step 1, one per line]
</MODULE_LIST>

Read all analysis documents using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 2, one per line]
</FILE_LIST>

For each module, score its Coupling (lower coupling = higher score) on a scale of 1-5:
- 5 (Exemplary): Minimal dependencies, well-defined interfaces, no circular dependencies
- 4 (Good): Few dependencies, mostly unidirectional
- 3 (Acceptable): Moderate dependencies, some bidirectional coupling
- 2 (Concerning): High fan-out or fan-in, implicit dependencies
- 1 (Critical): Circular dependencies, tight coupling, impossible to change in isolation

Return ONLY this JSON (no markdown fences, no explanation):
{
  "axis": "Coupling",
  "weight": 0.30,
  "modules": [
    {
      "name": "<module name>",
      "score": <integer 1-5>,
      "rationale": "<1-2 sentence explanation>"
    }
  ]
}
"""
)
```

**Task C — Independence Axis**
```
Task(
  subagent_type: "general-purpose",
  description: "MMI independence axis evaluation for all modules",
  prompt: """
You are evaluating INDEPENDENCE (ability to deploy and test in isolation) for each module in a software system.

Modules to evaluate:
<MODULE_LIST>
[Insert the module names identified in Step 1, one per line]
</MODULE_LIST>

Read all analysis documents using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 2, one per line]
</FILE_LIST>

For each module, score its Independence on a scale of 1-5:
- 5 (Exemplary): Can be deployed, tested, and versioned completely independently
- 4 (Good): Mostly independent with minor coordination needed
- 3 (Acceptable): Requires some coordination but deployable separately
- 2 (Concerning): Frequent coordination required; shared DB or shared runtime
- 1 (Critical): Cannot be deployed or tested independently; monolithic entanglement

Return ONLY this JSON (no markdown fences, no explanation):
{
  "axis": "Independence",
  "weight": 0.20,
  "modules": [
    {
      "name": "<module name>",
      "score": <integer 1-5>,
      "rationale": "<1-2 sentence explanation>"
    }
  ]
}
"""
)
```

**Task D — Reusability Axis**
```
Task(
  subagent_type: "general-purpose",
  description: "MMI reusability axis evaluation for all modules",
  prompt: """
You are evaluating REUSABILITY (component reusability across contexts) for each module in a software system.

Modules to evaluate:
<MODULE_LIST>
[Insert the module names identified in Step 1, one per line]
</MODULE_LIST>

Read all analysis documents using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 2, one per line]
</FILE_LIST>

For each module, score its Reusability on a scale of 1-5:
- 5 (Exemplary): Generic interfaces, well-documented contracts, reused in multiple contexts
- 4 (Good): Reusable with minor adaptation, clear interfaces
- 3 (Acceptable): Partially reusable but context-specific assumptions present
- 2 (Concerning): Highly context-specific, hard to reuse without modification
- 1 (Critical): Single-use implementation, no abstraction, not reusable

Return ONLY this JSON (no markdown fences, no explanation):
{
  "axis": "Reusability",
  "weight": 0.20,
  "modules": [
    {
      "name": "<module name>",
      "score": <integer 1-5>,
      "rationale": "<1-2 sentence explanation>"
    }
  ]
}
"""
)
```

### Step 4: Compute MMI Per Module and Write Outputs

After all four Tasks complete, for each module compute:

```
MMI = (0.3 × cohesion + 0.3 × coupling + 0.2 × independence + 0.2 × reusability) / 5 × 100
```

Maturity classification:
- 80-100 → Mature (Ready for microservices migration)
- 60-80  → Moderate (Migration possible after partial refactoring)
- 40-60  → Needs Improvement (Major refactoring required)
- 0-40   → Immature (Fundamental redesign required)

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

**`reports/02_evaluation/mmi-by-module.md`** — Per-module 4-axis score table:

```markdown
---
title: "MMI Evaluation: Per-Module Details"
schema_version: 1
phase: "Phase 2: Evaluation"
skill: evaluate-mmi
generated_at: "<ISO-8601>"
input_files:
  - reports/01_analysis/
---

# MMI Per-Module Evaluation

| Module | Cohesion | Coupling | Independence | Reusability | MMI | Maturity |
|--------|----------|----------|--------------|-------------|-----|----------|
| <module> | <score>/5 | <score>/5 | <score>/5 | <score>/5 | <MMI>% | <level> |
...

## Module Details

### <Module Name>
- **Cohesion (x/5)**: <rationale>
- **Coupling (x/5)**: <rationale>
- **Independence (x/5)**: <rationale>
- **Reusability (x/5)**: <rationale>
- **MMI**: <score>% (<maturity level>)
```

**`reports/02_evaluation/mmi-overview.md`** — Overall MMI scores, maturity assessment, improvement priorities:

```markdown
---
title: "MMI Evaluation: Overview"
schema_version: 1
phase: "Phase 2: Evaluation"
skill: evaluate-mmi
generated_at: "<ISO-8601>"
input_files:
  - reports/01_analysis/
---

# MMI Evaluation Overview

## Summary

| Metric | Value |
|--------|-------|
| System Average MMI | <avg>% |
| Maturity Level | <level> |
| Modules Evaluated | <count> |
| Ready for Migration | <count> |

## Per-Module MMI Scores

[bar chart using ASCII or Mermaid pie/gantt]

## Improvement Priorities

[Top 3-5 modules or axes requiring most improvement, with specific recommendations]

## Migration Readiness Verdict

[Overall assessment of readiness for microservices migration]
```

## Output

| File | Content |
|------|---------|
| `reports/02_evaluation/mmi-overview.md` | Overall MMI score, maturity assessment, improvement priorities |
| `reports/02_evaluation/mmi-by-module.md` | Per-module 4-axis score details |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:analyze | Input source |
| /architect:evaluate-ddd | Parallel execution |
| /architect:integrate-evaluations | Output destination |
