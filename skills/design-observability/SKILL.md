---
name: design-observability
description: |
  Design monitoring, distributed tracing, log aggregation, and alerting.
  Invoked via /design-observability.
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
- ScalarDB-specific metrics (transaction success rate, OCC conflict rate)

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
