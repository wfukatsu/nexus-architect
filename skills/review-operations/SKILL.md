---
description: |
  Review operational readiness: monitoring, disaster recovery, security posture, and deployment safety.
  Used as one perspective within the parallel review system.
model: sonnet
user_invocable: true
---

# Operational Readiness Review

## Review Dimensions

### 1. Monitoring and Observability (weight: 0.30)
- SLI/SLO definitions, distributed tracing, alert thresholds, health checks

### 2. Disaster Recovery (weight: 0.30)
- RTO/RPO definitions, backup strategy, failover design, recovery procedures

### 3. Security Posture (weight: 0.20)
- Authentication and authorization design, secret management, network isolation, audit logging

### 4. Deployment Safety (weight: 0.20)
- Deployment strategy (blue-green/canary), rollback procedures, DB migration safety

## Execution

### Step 1: Collect Input File Paths

Glob for all available design documents:
- `reports/03_design/**/*.md`
- `reports/01_analysis/**/*.md`

Record the full list of found file paths — these will be passed to sub-agents.

### Step 2: Spawn Four Parallel Dimension Reviewers

In a **single message**, issue all four Task() calls simultaneously so they run in parallel:

**Task A — Monitoring and Observability (OPS-1xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Monitoring and observability dimension review",
  prompt: """
You are an SRE reviewing design documents for MONITORING AND OBSERVABILITY readiness.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate ONLY the Monitoring and Observability dimension:
- SLI/SLO definitions present and measurable
- Distributed tracing design (span propagation, sampling strategy)
- Alert thresholds defined with runbook references
- Health check endpoints for all services

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Monitoring and Observability",
  "weight": 0.30,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "OPS-1<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<issue and its operational impact>",
      "recommendation": "<specific remediation>"
    }
  ]
}
"""
)
```

**Task B — Disaster Recovery (OPS-2xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Disaster recovery dimension review",
  prompt: """
You are an SRE reviewing design documents for DISASTER RECOVERY readiness.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate ONLY the Disaster Recovery dimension:
- RTO/RPO targets defined and achievable with the proposed design
- Backup strategy (frequency, retention, tested restoration)
- Failover design (automatic vs. manual, detection time)
- Recovery procedures documented with ownership

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Disaster Recovery",
  "weight": 0.30,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "OPS-2<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<issue and its recovery impact>",
      "recommendation": "<specific remediation>"
    }
  ]
}
"""
)
```

**Task C — Security Posture (OPS-3xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Security posture dimension review",
  prompt: """
You are a security engineer reviewing design documents for SECURITY POSTURE.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate ONLY the Security Posture dimension:
- Authentication and authorization design (least privilege, RBAC/ABAC)
- Secret management (no hardcoded credentials, rotation strategy)
- Network isolation (segmentation, mTLS between services)
- Audit logging (who did what, when, tamper-evident)

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Security Posture",
  "weight": 0.20,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "OPS-3<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<security issue and its risk>",
      "recommendation": "<specific remediation>"
    }
  ]
}
"""
)
```

**Task D — Deployment Safety (OPS-4xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Deployment safety dimension review",
  prompt: """
You are an SRE reviewing design documents for DEPLOYMENT SAFETY.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate ONLY the Deployment Safety dimension:
- Deployment strategy (blue-green/canary defined with traffic shift plan)
- Rollback procedures (automated triggers, estimated time)
- DB migration safety (backward-compatible migrations, no locking operations)
- Feature flags for gradual rollout

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Deployment Safety",
  "weight": 0.20,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "OPS-4<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<deployment risk and its impact>",
      "recommendation": "<specific remediation>"
    }
  ]
}
"""
)
```

### Step 3: Merge and Write Output

After all four Tasks complete, compute the weighted score and write output:

```
weighted_score = round(0.30 × scoreA + 0.30 × scoreB + 0.20 × scoreC + 0.20 × scoreD, 2)
```

Write `reports/review/individual/review-operations.json`:
```json
{
  "perspective": "operations",
  "reviewer": "review-operations",
  "timestamp": "<ISO-8601 now>",
  "dimensions": [<Task A result>, <Task B result>, <Task C result>, <Task D result>],
  "weighted_score": <computed>,
  "summary": "<2-3 sentences synthesizing operational readiness gaps and overall verdict>"
}
```

## Output Format

Finding ID prefix: **OPS-**
- OPS-1xx: Monitoring and Observability
- OPS-2xx: Disaster Recovery
- OPS-3xx: Security Posture
- OPS-4xx: Deployment Safety
