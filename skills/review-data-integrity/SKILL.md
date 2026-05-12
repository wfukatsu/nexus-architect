---
description: |
  Review data integrity, transaction safety, and schema design quality independent of ScalarDB.
  For projects not using ScalarDB. Used as one perspective within the parallel review system.
model: sonnet
user_invocable: true
---

# Data Integrity Review

## Review Dimensions

### 1. Transaction Safety (weight: 0.40)
- Appropriateness of transaction boundaries
- ACID property guarantees
- Deadlock avoidance design

### 2. Data Consistency (weight: 0.35)
- Acceptable range for eventual consistency
- Conflict resolution strategies
- Referential integrity constraints

### 3. Schema Design Quality (weight: 0.25)
- Appropriateness of normalization level
- Index design
- Migration safety

## Execution

### Step 1: Collect Input File Paths

Glob for all available design documents:
- `reports/03_design/data-layer-design.md`
- `reports/03_design/target-architecture.md`
- `reports/03_design/transformation-plan.md`
- `reports/03_design/api-specifications/**/*.md` (if exists)
- `reports/01_analysis/data-model-analysis.md` (if exists)

Record the full list of found file paths — these will be passed to sub-agents.

### Step 2: Spawn Three Parallel Dimension Reviewers

In a **single message**, issue all three Task() calls simultaneously so they run in parallel:

**Task A — Transaction Safety (DIN-1xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Transaction safety dimension review",
  prompt: """
You are a database architect reviewing designs for TRANSACTION SAFETY.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate ONLY the Transaction Safety dimension:
- Are transaction boundaries appropriate (not too broad causing lock contention, not too narrow losing atomicity)?
- Are ACID properties (Atomicity, Consistency, Isolation, Durability) guaranteed for critical operations?
- Is deadlock avoidance addressed (consistent lock ordering, timeout strategies, retry logic)?

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Transaction Safety",
  "weight": 0.40,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "DIN-1<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<transaction issue and its data integrity impact>",
      "recommendation": "<specific remediation>"
    }
  ]
}
"""
)
```

**Task B — Data Consistency (DIN-2xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Data consistency dimension review",
  prompt: """
You are a database architect reviewing designs for DATA CONSISTENCY.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate ONLY the Data Consistency dimension:
- Is the acceptable range for eventual consistency defined and aligned with business requirements?
- Are conflict resolution strategies defined for concurrent updates (last-write-wins, merge, versioning)?
- Are referential integrity constraints enforced (foreign keys, cascade rules, orphan prevention)?

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Data Consistency",
  "weight": 0.35,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "DIN-2<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<consistency issue and its business impact>",
      "recommendation": "<specific remediation>"
    }
  ]
}
"""
)
```

**Task C — Schema Design Quality (DIN-3xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Schema design quality dimension review",
  prompt: """
You are a database architect reviewing designs for SCHEMA DESIGN QUALITY.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate ONLY the Schema Design Quality dimension:
- Is the normalization level appropriate (avoid over-normalization causing excessive joins; avoid under-normalization causing update anomalies)?
- Is index design sound (covering indexes for common queries, no redundant indexes, index selectivity)?
- Is migration safety addressed (backward-compatible migrations, no blocking ALTER TABLE on large tables)?

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Schema Design Quality",
  "weight": 0.25,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "DIN-3<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<schema issue and its operational impact>",
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
weighted_score = round(0.40 × scoreA + 0.35 × scoreB + 0.25 × scoreC, 2)
```

Write `reports/review/individual/review-data-integrity.json`:
```json
{
  "perspective": "data-integrity",
  "reviewer": "review-data-integrity",
  "timestamp": "<ISO-8601 now>",
  "dimensions": [<Task A result>, <Task B result>, <Task C result>],
  "weighted_score": <computed>,
  "summary": "<2-3 sentences synthesizing data integrity health and key risks>"
}
```

## Output Format

Finding ID prefix: **DIN-**
- DIN-1xx: Transaction Safety
- DIN-2xx: Data Consistency
- DIN-3xx: Schema Design Quality
