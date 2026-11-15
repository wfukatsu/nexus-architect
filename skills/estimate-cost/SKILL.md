---
description: |
  Estimate cloud infrastructure, ScalarDB licensing and operating costs, with sizing.
model: sonnet
---

# Cost Estimation

Shared files: a path written `@rules/…`, `@skills/…`, `@templates/…` or `@docs/…` is relative to the
plugin root, `${CLAUDE_PLUGIN_ROOT}` — not to the project being worked on. Read it from there.

## Desired Outcome

Produce a multi-dimensional cost estimate for the project:
- Cloud infrastructure costs (AWS/Azure/GCP: compute, storage, network)
- ScalarDB licensing costs (by edition, direct contract vs. AWS Marketplace)
- Operational costs (monitoring tools, support, personnel)
- ScalarDB sizing (pod count, cluster configuration, DB capacity)

## Progress Registry

Before the first step, record `estimate-cost` in the project's `work/pipeline-progress.json` as
`in_progress` (`plugin: architect`, `started_at`); at the end, `completed` (or `failed`) with
`outputs` and a one-line `summary` (@skills/common/progress-registry.md § The `in_progress`
Contract). The status dashboard, the token-usage ledger and the audit log read nothing else: a
phase that skips the first write has its spend recorded as `_unassigned` and never shows as
running. A project without the registry (`/architect:init-output` never ran) gets none from this
skill; the hooks are inert there.

## Acceptance Criteria

Confirm the following via AskUserQuestion:
- Environment type (dev/staging/prod)
- Expected TPS, data volume, availability targets
- Currency (USD/JPY)

## Output

Output language and frontmatter: @rules/output-conventions.md.

| File | Content |
|------|---------|
| `reports/05_estimate/cost-summary.md` | Cost overview |
| `reports/05_estimate/infrastructure-detail.md` | Detailed infrastructure estimate |
| `reports/05_estimate/scalardb-sizing.md` | ScalarDB sizing |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-infrastructure | Input source |
| /architect:design-scalardb | Input source (sizing information) |
