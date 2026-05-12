---
description: |
  Review distributed system risks, failure modes, and Saga design adequacy.
  Adopts an adversarial perspective to discover risks overlooked by the designer. Deepest analysis perspective.
model: opus
user_invocable: true
---

# Distributed System Risk Review

## Your Role

As a distributed systems architect, discover risks that only manifest at scale or during failures.
Adversarial perspective: find failure modes the designer did not consider.

## Review Dimensions

### 1. Distributed System Risks (weight: 0.30)
- Behavior during network partitions (documented CAP theorem tradeoffs)
- Clock skew sensitivity
- Split-brain scenarios
- Cascading failure paths

### 2. Failure Mode Analysis (weight: 0.30)
- Behavior on timeout/error in inter-service calls
- Circuit breaker patterns
- Bulkhead isolation
- Graceful degradation

### 3. Saga Design Adequacy (weight: 0.25)
- Definition of compensating transactions
- Rationale for orchestration vs. choreography choice
- Handling of partial failures (failure of compensation itself)
- Idempotency guarantees

### 4. Data Consistency Risks (weight: 0.15)
- Business impact of eventual consistency windows
- Read-your-write consistency guarantees
- Conflict resolution strategies

## Execution

### Step 1: Collect Input File Paths

Glob for all available design documents:
- `reports/03_design/**/*.md`
- `reports/01_analysis/**/*.md`

Record the full list of found file paths — these will be passed to sub-agents.

### Step 2: Spawn Four Parallel Dimension Reviewers

In a **single message**, issue all four Task() calls simultaneously so they run in parallel:

**Task A — Distributed System Risks (RSK-1xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Distributed system risks dimension review",
  prompt: """
You are an adversarial distributed systems architect reviewing for DISTRIBUTED SYSTEM RISKS.
Find risks the designer did not consider.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate ONLY the Distributed System Risks dimension:
- Behavior during network partitions (documented CAP theorem tradeoffs)
- Clock skew sensitivity
- Split-brain scenarios
- Cascading failure paths

Score 1-5: 5=Exemplary (all risks addressed), 4=Good, 3=Acceptable, 2=Concerning, 1=Critical (major risks unaddressed)

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Distributed System Risks",
  "weight": 0.30,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "RSK-1<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<risk and its potential impact>",
      "recommendation": "<specific mitigation>"
    }
  ]
}
"""
)
```

**Task B — Failure Mode Analysis (RSK-2xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Failure mode analysis dimension review",
  prompt: """
You are an adversarial distributed systems architect reviewing FAILURE MODE ANALYSIS.
Find failure paths the designer overlooked.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate ONLY the Failure Mode Analysis dimension:
- Behavior on timeout/error in inter-service calls
- Circuit breaker patterns
- Bulkhead isolation
- Graceful degradation

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Failure Mode Analysis",
  "weight": 0.30,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "RSK-2<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<failure mode and its impact>",
      "recommendation": "<specific mitigation>"
    }
  ]
}
"""
)
```

**Task C — Saga Design Adequacy (RSK-3xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Saga design adequacy dimension review",
  prompt: """
You are an adversarial distributed systems architect reviewing SAGA DESIGN ADEQUACY.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate ONLY the Saga Design Adequacy dimension:
- Definition of compensating transactions
- Rationale for orchestration vs. choreography choice
- Handling of partial failures (failure of compensation itself)
- Idempotency guarantees

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Saga Design Adequacy",
  "weight": 0.25,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "RSK-3<NN>",
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

**Task D — Data Consistency Risks (RSK-4xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Data consistency risks dimension review",
  prompt: """
You are an adversarial distributed systems architect reviewing DATA CONSISTENCY RISKS.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate ONLY the Data Consistency Risks dimension:
- Business impact of eventual consistency windows
- Read-your-write consistency guarantees
- Conflict resolution strategies

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Data Consistency Risks",
  "weight": 0.15,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "RSK-4<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<consistency risk and its business impact>",
      "recommendation": "<specific mitigation>"
    }
  ]
}
"""
)
```

### Step 3: Merge and Write Output

After all four Tasks complete, compute the weighted score and write output:

```
weighted_score = round(0.30 × scoreA + 0.30 × scoreB + 0.25 × scoreC + 0.15 × scoreD, 2)
```

Write `reports/review/individual/review-risk.json`:
```json
{
  "perspective": "risk",
  "reviewer": "review-risk",
  "timestamp": "<ISO-8601 now>",
  "dimensions": [<Task A result>, <Task B result>, <Task C result>, <Task D result>],
  "weighted_score": <computed>,
  "summary": "<2-3 sentences synthesizing the most critical risks discovered and overall risk posture>"
}
```

## Output Format

Finding ID prefix: **RSK-**
- RSK-1xx: Distributed System Risks
- RSK-2xx: Failure Mode Analysis
- RSK-3xx: Saga Design Adequacy
- RSK-4xx: Data Consistency Risks
