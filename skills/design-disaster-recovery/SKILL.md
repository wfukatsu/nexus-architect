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

## Progress Registry

Before the first step, record `design-disaster-recovery` in the project's `work/pipeline-progress.json` as
`in_progress` (`plugin: architect`, `started_at`); at the end, `completed` (or `failed`) with
`outputs` and a one-line `summary` (@skills/common/progress-registry.md § The `in_progress`
Contract). The status dashboard, the token-usage ledger and the audit log read nothing else: a
phase that skips the first write has its spend recorded as `_unassigned` and never shows as
running. A project without the registry (`/architect:init-output` never ran) gets none from this
skill; the hooks are inert there.

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
