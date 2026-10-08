---
description: |
  Design Kubernetes, IaC (Terraform), networking, and multi-environment configuration.
model: opus
---

# Infrastructure Design

Shared files: a path written `@rules/…`, `@skills/…`, `@templates/…` or `@docs/…` is relative to the
plugin root, `${CLAUDE_PLUGIN_ROOT}` — not to the project being worked on. Read it from there.

## Desired Outcome

Design a production-grade infrastructure configuration:
- Kubernetes cluster configuration (node pools, resource quotas, namespace strategy)
- Container orchestration (deployment strategy, HPA, PDB)
- Network design (mTLS, NetworkPolicy, Ingress/Gateway)
- IaC configuration (Terraform modules, state management)
- Multi-environment strategy (dev/staging/prod, Kustomize overlays)
- When using ScalarDB Cluster: Helm chart configuration, Coordinator placement

## Platform Versions

Where the design names a version — Kubernetes, the Helm chart, ScalarDB Cluster, a managed database
engine — look it up rather than recalling it, and choose a **stable, non-EOL** release per
@rules/dependency-versions.md (`endoflife.date` for support windows, the chart/registry APIs for what
is published). State the version *and* its support horizon in the design, so
`/architect:generate-infra-code` pins the same set and the reader knows when it expires.

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/03_design/target-architecture.md | Required | /architect:design-microservices |

## Output

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

| File | Content |
|------|---------|
| `reports/08_infrastructure/infrastructure-architecture.md` | Overall infrastructure design |
| `reports/08_infrastructure/deployment-guide.md` | Deployment procedures |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-microservices | Input source |
| /design-security | Related |
| /generate-infra-code | Output consumer |
