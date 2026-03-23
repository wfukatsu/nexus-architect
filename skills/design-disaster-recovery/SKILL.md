---
name: design-disaster-recovery
description: |
  Define RTO/RPO, backup strategies, failover design, and recovery procedures.
  Invoked via /design-disaster-recovery.
model: sonnet
user_invocable: true
---

# Disaster Recovery Design

## Desired Outcome

- RTO/RPO definitions by service tier
- Backup strategy (frequency, retention period, test plan)
- Failover design (cross-region, cross-AZ)
- Data recovery procedures (including ScalarDB Coordinator table)
- Runbooks (recovery procedures per failure scenario)
- Recovery test plan (including chaos engineering)

## Output

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

| File | Content |
|------|---------|
| `reports/08_infrastructure/disaster-recovery-design.md` | Overall DR design |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-infrastructure | Related |
| /architect:review-operations | Referenced during review |
