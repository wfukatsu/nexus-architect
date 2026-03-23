---
name: review-operations
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

## Output Format

JSON (same schema as review-consistency). Finding ID prefix: **OPS-**
