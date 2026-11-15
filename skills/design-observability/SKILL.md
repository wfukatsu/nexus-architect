---
description: |
  Design SLIs and SLOs, monitoring, alerting, distributed tracing and log aggregation.
model: sonnet
---

# Observability Design

Shared files: a path written `@rules/…`, `@skills/…`, `@templates/…` or `@docs/…` is relative to the
plugin root, `${CLAUDE_PLUGIN_ROOT}` — not to the project being worked on. Read it from there.

## Desired Outcome

- SLI/SLO definitions (per service, linked to business KPIs)
- Distributed tracing design (OpenTelemetry, correlation ID propagation)
- Log aggregation strategy (structured logging, centralized management)
- Metrics design (RED/USE methods)
- Alerting design (thresholds, escalation, dashboards)
- ScalarDB-specific metrics (transaction success rate, OCC conflict rate). On ScalarDB Cluster
  3.19+, prefer its native **OpenTelemetry support** over a bespoke exporter; verify availability
  against the project's pinned release and edition per @rules/okf-knowledge-bundle.md. When
  ScalarDB Saga is in the architecture, add saga-level signals — sagas by status, `ESCALATED` count
  (an operator queue, not a transient error), compensation failure rate — per
  @rules/scalardb-saga-patterns.md

## Progress Registry

Before the first step, record `design-observability` in the project's `work/pipeline-progress.json` as
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
| `reports/08_infrastructure/observability-design.md` | Overall observability design |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-infrastructure | Related |
| /architect:review-operations | Referenced during review |
