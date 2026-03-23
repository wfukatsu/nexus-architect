---
name: design-infrastructure
description: |
  Design Kubernetes, IaC (Terraform), networking, and multi-environment configuration.
  Invoked via /architect:design-infrastructure.
model: opus
user_invocable: true
---

# Infrastructure Design

## Desired Outcome

Design a production-grade infrastructure configuration:
- Kubernetes cluster configuration (node pools, resource quotas, namespace strategy)
- Container orchestration (deployment strategy, HPA, PDB)
- Network design (mTLS, NetworkPolicy, Ingress/Gateway)
- IaC configuration (Terraform modules, state management)
- Multi-environment strategy (dev/staging/prod, Kustomize overlays)
- When using ScalarDB Cluster: Helm chart configuration, Coordinator placement

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
