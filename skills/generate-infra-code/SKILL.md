---
name: generate-infra-code
description: |
  Generate Kubernetes manifests, Terraform modules, and Helm charts.
  Invoked via /generate-infra-code.
model: sonnet
user_invocable: true
---

# Infrastructure Code Generation

## Desired Outcome

Generate IaC code based on the infrastructure design:
- Kubernetes manifests (Kustomize base + overlays)
- Terraform modules (multi-cloud support)
- Helm values (for ScalarDB Cluster)
- NetworkPolicy and PodDisruptionBudget
- Multi-environment configuration (dev/staging/prod)

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/08_infrastructure/ | Required | /architect:design-infrastructure |
| reports/03_design/target-architecture.md | Recommended | /architect:design-microservices |

## Output

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

| File | Content |
|------|---------|
| `generated/infrastructure/k8s/` | Kubernetes manifests |
| `generated/infrastructure/terraform/` | Terraform modules |
| `generated/infrastructure/helm/` | Helm values |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-infrastructure | Input source |
