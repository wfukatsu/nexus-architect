---
description: |
  Set RTO and RPO, and design backups, failover and recovery procedures.
model: sonnet
---

# Disaster Recovery Design

Shared files: a path written `@rules/…`, `@skills/…`, `@templates/…` or `@docs/…` is relative to the
plugin root, `${CLAUDE_PLUGIN_ROOT}` — not to the project being worked on. Read it from there.

## Desired Outcome

- RTO/RPO definitions by service tier
- Backup strategy (frequency, retention period, test plan)
- Failover design (cross-region, cross-AZ)
- Data recovery procedures (including ScalarDB Coordinator table)
- Runbooks (recovery procedures per failure scenario)
- Recovery test plan (including chaos engineering)

## Output

Output language and frontmatter: @rules/output-conventions.md.

| File | Content |
|------|---------|
| `reports/08_infrastructure/disaster-recovery-design.md` | Overall DR design |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-infrastructure | Related |
| /architect:review-operations | Referenced during review |
