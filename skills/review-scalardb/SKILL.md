---
description: |
  Review ScalarDB-specific constraints (2PC scope, OCC contention, schema compatibility).
  For ScalarDB-enabled projects only. Used as one perspective within the parallel review system.
model: sonnet
user_invocable: true
---

# ScalarDB Constraint Review

## Review Dimensions

### 1. 2PC Scope Compliance (weight: 0.40)
- Whether 2PC transactions are contained within a maximum of 2-3 services
- Detection of transactions spanning 4+ services
- Application points for the Saga pattern

### 2. OCC Contention Analysis (weight: 0.35)
- Identification of write hotspots
- Whether the design can achieve an OCC conflict rate below 5%
- Contention mitigation strategies (partitioning, CQRS, etc.)

### 3. Schema and API Compatibility (weight: 0.25)
- Validity of partition/clustering key design
- Necessity of secondary indexes and their performance impact
- Compliance with ScalarDB v3.17+ constraints

## Execution

### Step 1: Collect Input File Paths

Glob for all available ScalarDB design documents:
- `reports/03_design/scalardb-*.md`
- `reports/03_design/target-architecture.md`
- `reports/03_design/transformation-plan.md`
- `reports/03_design/api-specifications/**/*.md` (if exists)

Record the full list of found file paths — these will be passed to sub-agents.

### Step 2: Spawn Three Parallel Dimension Reviewers

In a **single message**, issue all three Task() calls simultaneously so they run in parallel:

**Task A — 2PC Scope Compliance (SDB-1xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "2PC scope compliance dimension review",
  prompt: """
You are a ScalarDB architect reviewing designs for 2PC SCOPE COMPLIANCE.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Also refer to ScalarDB 2PC best practices: ScalarDB recommends 2PC transactions span at most 2-3 services.
Transactions spanning 4+ services should use the Saga pattern instead.

Evaluate ONLY the 2PC Scope Compliance dimension:
- Are all 2PC transactions contained within 2-3 services maximum?
- Are there transactions spanning 4+ services that should use Saga instead?
- Where should the Saga pattern be applied as an alternative to 2PC?

Score 1-5: 5=Exemplary (all 2PC within 3-service limit), 4=Good, 3=Acceptable, 2=Concerning, 1=Critical (wide 2PC scope)

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "2PC Scope Compliance",
  "weight": 0.40,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "SDB-1<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<2PC scope issue and its impact on transaction reliability>",
      "recommendation": "<refactoring to Saga or scope reduction>"
    }
  ]
}
"""
)
```

**Task B — OCC Contention Analysis (SDB-2xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "OCC contention analysis dimension review",
  prompt: """
You are a ScalarDB architect reviewing designs for OCC CONTENTION ANALYSIS.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

ScalarDB uses Optimistic Concurrency Control (OCC). Conflict rates above 5% degrade performance significantly.

Evaluate ONLY the OCC Contention Analysis dimension:
- Which tables/partitions are write hotspots (multiple concurrent writes to the same partition key)?
- Can the design achieve an OCC conflict rate below 5% under expected load?
- Are contention mitigation strategies applied (partitioning, CQRS, event sourcing, etc.)?

Score 1-5: 5=Exemplary (minimal hotspots, clear mitigation), 4=Good, 3=Acceptable, 2=Concerning, 1=Critical (high contention)

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "OCC Contention Analysis",
  "weight": 0.35,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "SDB-2<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<hotspot or contention pattern and its performance impact>",
      "recommendation": "<specific partitioning or design change>"
    }
  ]
}
"""
)
```

**Task C — Schema and API Compatibility (SDB-3xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Schema and API compatibility dimension review",
  prompt: """
You are a ScalarDB architect reviewing designs for SCHEMA AND API COMPATIBILITY.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate ONLY the Schema and API Compatibility dimension against ScalarDB v3.17+ constraints:
- Partition key design (even distribution, no hot partitions, no monotonically increasing sole partition keys)
- Clustering key design (appropriate sort order for access patterns)
- Secondary indexes (only where necessary; avoid high-cardinality indexes on some backends)
- API usage (Put is deprecated since 3.13; use Insert/Upsert/Update instead)
- Exception handling (specific conflict exceptions caught before parent classes)

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Schema and API Compatibility",
  "weight": 0.25,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "SDB-3<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<schema or API issue and its constraint violation>",
      "recommendation": "<specific fix per ScalarDB constraints>"
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

Write `reports/review/individual/review-scalardb.json`:
```json
{
  "perspective": "scalardb",
  "reviewer": "review-scalardb",
  "timestamp": "<ISO-8601 now>",
  "dimensions": [<Task A result>, <Task B result>, <Task C result>],
  "weighted_score": <computed>,
  "summary": "<2-3 sentences synthesizing ScalarDB constraint compliance and key risks>"
}
```

## Output Format

Finding ID prefix: **SDB-**
- SDB-1xx: 2PC Scope Compliance
- SDB-2xx: OCC Contention Analysis
- SDB-3xx: Schema and API Compatibility
