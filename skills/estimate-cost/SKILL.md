---
description: |
  Estimate cloud infrastructure, ScalarDB licensing and operational costs, including sizing
  estimates.
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
