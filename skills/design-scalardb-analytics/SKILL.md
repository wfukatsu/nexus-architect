---
description: |
  Design an HTAP analytics platform on ScalarDB Analytics with Apache Spark, a separately contracted
  Enterprise Option that Premium does not include.
model: sonnet
---

# ScalarDB Analytics Design

Shared files: a path written `@rules/…`, `@skills/…`, `@templates/…` or `@docs/…` is relative to the
plugin root, `${CLAUDE_PLUGIN_ROOT}` — not to the project being worked on. Read it from there.

## Desired Outcome

- HTAP (Hybrid Transactional/Analytical Processing) architecture design
- Apache Spark integration configuration
- Cross-database analytical query design across heterogeneous DBs
- Data catalog (logical-to-physical mapping)
- Timeline-consistent read configuration

## Decision Criteria

- Ground the design in the version-pinned OKF knowledge bundle (@rules/okf-knowledge-bundle.md):
  read the Analytics concepts of the pinned ScalarDB release only, and confirm the feature's
  `editions` / `feature_status` for that release before designing around it
- **Confirm the licensing before designing.** Analytics concepts carry `editions: [Enterprise
  Option]` — a separately contracted add-on. A project on Enterprise Premium does **not**
  automatically have it. If the contract is unconfirmed, say so and ask rather than assuming
  availability (@rules/scalardb-edition-profiles.md)

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/03_design/scalardb-schema.md | Required | /architect:design-scalardb |

## Progress Registry

Before the first step, record `design-scalardb-analytics` in the project's `work/pipeline-progress.json` as
`in_progress` (`plugin: architect`, `started_at`); at the end, `completed` (or `failed`) with
`outputs` and a one-line `summary` (@skills/common/progress-registry.md § The `in_progress`
Contract). The status dashboard, the token-usage ledger and the audit log read nothing else: a
phase that skips the first write has its spend recorded as `_unassigned` and never shows as
running. A project without the registry (`/architect:init-output` never ran) gets none from this
skill; the hooks are inert there.

## Output

| File | Content |
|------|---------|
| `reports/03_design/scalardb-analytics-design.md` | Overall Analytics design |

Output language and frontmatter: @rules/output-conventions.md.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-scalardb | Input source |
