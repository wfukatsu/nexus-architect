---
description: |
  Design monitoring, distributed tracing, log aggregation, and alerting.
  Invoked via /architect:design-observability.
model: sonnet
user_invocable: true
---

# Observability Design

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

## Output

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

| File | Content |
|------|---------|
| `reports/08_infrastructure/observability-design.md` | Overall observability design |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-infrastructure | Related |
| /architect:review-operations | Referenced during review |
