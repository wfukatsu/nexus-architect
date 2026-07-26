---
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

## Dependency Versions

IaC is almost entirely version pins — Kubernetes `apiVersion` and cluster version, Terraform
`required_version` and provider constraints, Helm chart versions, container image tags. Follow
@rules/dependency-versions.md: resolve each from its registry (Terraform registry, chart repo, image
registry, `endoflife.date` for the supported Kubernetes window), pin **stable, non-EOL, mutually
compatible** versions, never leave a moving `:latest`/`stable` image tag in a manifest, and honour
what the target environment already runs over what is newest. Confirm the version decision table per
`--confirm-versions` / `--no-confirm-versions` / `options.confirm_versions`, and record it with the
generated IaC plus `work/version-decisions.json`.

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
| /architect:generate-docs | Downstream — run after generation to write the README and the `operations` docs for the emitted IaC |
