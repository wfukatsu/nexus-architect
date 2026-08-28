---
description: |
  Review design documents for structural coherence, traceability, and terminology consistency.
  Used as one perspective within the parallel review system.
model: sonnet
user_invocable: true
---

# Consistency Review

## Expected Outcome

Verify the structural consistency of design documents and output findings in JSON format.

## Review Dimensions

### 1. Structural Coherence (weight: 0.35)
- Consistency of structure and heading levels across documents
- Detection of orphaned sections and broken references
- Logical soundness of the hierarchical structure

### 2. Traceability (weight: 0.35)
- Ability to trace from requirements to design to implementation
- Presence of forward and backward references
- Whether gaps are documented

### 3. Terminology Consistency (weight: 0.30)
- Consistent use of ubiquitous language
- Detection of different names for the same concept
- Abbreviations defined at first occurrence and used consistently

## Scoring

Each dimension scored 1-5 (5: Exemplary, 4: Good, 3: Acceptable, 2: Concerning, 1: Critical)

## Execution

### Step 1: Collect Input File Paths

Glob for all available design and analysis documents:
- `reports/03_design/**/*.md`
- `reports/01_analysis/**/*.md`

Record the full list of found file paths — these will be passed to sub-agents.

When `reports/03_design/aggregates/aggregate-manifest.json` exists, run
`python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/aggregate_manifest.py" <project_dir>` first and pass its output to Task B.
It mechanically checks the seven well-formedness rules of @rules/aggregate-design.md §3; each
violation is a CON-2xx finding unless the model's Open Items already records it with an owner, and
the reviewers check that the schema's tables and the transaction design's TX- entries still follow
the aggregate boundaries (one aggregate per `local` transaction, cross-aggregate writes classified).

When `reports/03_design/state-machines/state-machine-manifest.json` exists, run
`python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/state_machine_manifest.py" <project_dir>` first and pass its output to Task B.
It mechanically checks the seven well-formedness rules of @rules/state-modeling.md §3, so the
reviewers spend their judgment on whether the *design documents* still agree with the model rather
than on re-deriving reachability by hand. Each violation it reports is a CON-2xx finding unless the
model's Open Items already records it with an owner.

### Step 2: Spawn Three Parallel Dimension Reviewers

In a **single message**, issue all three Task() calls simultaneously so they run in parallel:

**Task A — Structural Coherence (CON-1xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Structural coherence dimension review",
  prompt: """
You are a technical reviewer evaluating design document STRUCTURAL COHERENCE.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate ONLY the Structural Coherence dimension:
- Consistency of structure and heading levels across documents
- Detection of orphaned sections and broken references
- Logical soundness of the hierarchical structure

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Structural Coherence",
  "weight": 0.35,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "CON-1<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<issue and its impact>",
      "recommendation": "<specific remediation>"
    }
  ]
}
"""
)
```

**Task B — Traceability (CON-2xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Traceability dimension review",
  prompt: """
You are a technical reviewer evaluating design document TRACEABILITY.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate ONLY the Traceability dimension:
- Ability to trace from requirements to design to implementation
- Presence of forward and backward references
- Whether gaps are documented
- Cross-plugin continuity (when `work/traceability.json` exists from a product handoff, per docs/design.md §1.5): every `FR-` is reachable from a `FEAT-` or explicitly flagged as elicited-fresh; no product `NFR-` was silently re-numbered; no `upstream` ID dangles across the product→architect boundary
- State transition models (when `reports/03_design/state-machines/` exists, per rules/state-modeling.md §8): every state the schema's state column permits is a state in the model and vice versa; every `reject` matrix cell has a corresponding error response in the API design; every `ignore` cell has an idempotency contract; every transition classified `saga` appears in the transaction design's saga steps with a compensating transition. A model that no downstream document reflects is a traceability break, not a stylistic one

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Traceability",
  "weight": 0.35,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "CON-2<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<issue and its impact>",
      "recommendation": "<specific remediation>"
    }
  ]
}
"""
)
```

**Task C — Terminology Consistency (CON-3xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Terminology consistency dimension review",
  prompt: """
You are a technical reviewer evaluating design document TERMINOLOGY CONSISTENCY.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate ONLY the Terminology Consistency dimension:
- Consistent use of ubiquitous language
- Detection of different names for the same concept
- Abbreviations defined at first occurrence and used consistently
- State and event names in any state transition model appear in `ubiquitous-language.md` with the same spelling, and no state is renamed between the model, the schema and the API design

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Terminology Consistency",
  "weight": 0.30,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "CON-3<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<issue and its impact>",
      "recommendation": "<specific remediation>"
    }
  ]
}
"""
)
```

### Step 3: Merge and Write Output

After all three Tasks complete, compute the weighted score and write output:

```
weighted_score = round(0.35 × scoreA + 0.35 × scoreB + 0.30 × scoreC, 2)
```

Write `reports/review/individual/review-consistency.json`:
```json
{
  "perspective": "consistency",
  "reviewer": "review-consistency",
  "timestamp": "<ISO-8601 now>",
  "dimensions": [<Task A result>, <Task B result>, <Task C result>],
  "weighted_score": <computed>,
  "summary": "<2-3 sentences synthesizing the key findings and overall structural health>"
}
```

## Output Format

Finding ID prefix: **CON-**
- CON-1xx: Structural Coherence
- CON-2xx: Traceability
- CON-3xx: Terminology Consistency
