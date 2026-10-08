---
title: "okf-k8s-tf upstream report"
schema_version: 1
generated_at: "2026-10-08T18:25:19Z"
generator: tools/refresh-okf-k8s-tf.py
---

# okf-k8s-tf upstream report

What moved in the public sources of `knowledge/okf-k8s-tf/` since the previous recorded state.
Observed-implementation statements (対象実装) are facts about a private snapshot and are
**not** revised from these sources — only design guidance (設計指針), versions and freshness.

## Awaiting re-verification

None.

## Pages

Checked 49 public pages.

## Releases

| Technology | Bundle states | Latest stable | Released | Behind | Source |
|---|---|---|---|---|---|
| Alertmanager | — | 0.34.1 | 2026-09-17 | — | https://github.com/prometheus/alertmanager/releases |
| Alloy | — | 1.20.1 | 2026-09-28 | — | https://github.com/grafana/alloy/releases |
| Argo CD | — | 3.5.4 | 2026-10-06 | — | https://github.com/argoproj/argo-cd/releases |
| Argo CD Image Updater | — | 1.3.1 | 2026-10-08 | — | https://github.com/argoproj-labs/argocd-image-updater/releases |
| Beyla | — | 3.38.0 | 2026-10-05 | — | https://github.com/grafana/beyla/releases |
| Cosign | 2.6.1 | 3.1.3 | 2026-08-06 | major | https://github.com/sigstore/cosign/releases |
| Docker Engine | 27 (EOL 2025-05-03) | 29.8.2 | 2026-09-30 | major | https://endoflife.date/docker-engine |
| External Secrets Operator | — | 2.12.0 | 2026-10-06 | — | https://github.com/external-secrets/external-secrets/releases |
| GitLab Runner | — | 19.4.1 | 2026-09-24 | — | https://gitlab.com/gitlab-org/gitlab-runner/-/releases |
| Grafana | — | 13.2.3 | 2026-09-29 | — | https://github.com/grafana/grafana/releases |
| Helm | — | 4.3.0 | 2026-09-09 | — | https://github.com/helm/helm/releases |
| Kubernetes | 1.35 (EOL 2027-02-28) | 1.37.1 | 2026-09-23 | minor | https://endoflife.date/kubernetes |
| Kustomize | — | 5.8.3 | 2026-10-08 | — | https://github.com/kubernetes-sigs/kustomize/releases |
| Kyverno | 1.18 | 1.19.1 | 2026-09-10 | minor | https://github.com/kyverno/kyverno/releases |
| Loki | — | 3.7.8 | 2026-09-17 | — | https://github.com/grafana/loki/releases |
| OpenCost | — | 1.121.3 | 2026-09-16 | — | https://github.com/opencost/opencost/releases |
| Prometheus | — | 3.15.0 | 2026-09-25 | — | https://github.com/prometheus/prometheus/releases |
| Pyrra | — | 0.10.2 | 2026-09-18 | — | https://github.com/pyrra-dev/pyrra/releases |
| Tempo | — | 3.1.0 | 2026-09-29 | — | https://github.com/grafana/tempo/releases |
| Terraform | 1.14.8 | 1.16.5 | 2026-10-02 | minor | https://github.com/hashicorp/terraform/releases |
| Vault | — | 2.1.2 | 2026-10-07 | — | https://github.com/hashicorp/vault/releases |
| provider: aws | 5.94.1 | 6.68.0 | 2026-10-07 | major | https://registry.terraform.io/providers/hashicorp/aws |
| provider: azuread | 3.9.0 | 3.10.0 | 2026-09-24 | minor | https://registry.terraform.io/providers/hashicorp/azuread |
| provider: azurerm | 4.78.0 | 5.9.0 | 2026-10-08 | major | https://registry.terraform.io/providers/hashicorp/azurerm |
| provider: google | 6.44.0 | 8.6.0 | 2026-10-06 | major | https://registry.terraform.io/providers/hashicorp/google |
| provider: helm | 2.17.0 | 3.3.0 | 2026-09-02 | major | https://registry.terraform.io/providers/hashicorp/helm |
| provider: kubectl | 1.14.0 | 1.19.0 | 2025-01-10 | minor | https://registry.terraform.io/providers/gavinbunney/kubectl |
| provider: kubernetes | 2.36.0 | 3.3.0 | 2026-10-01 | major | https://registry.terraform.io/providers/hashicorp/kubernetes |
| provider: vault | 4.8.0 | 5.12.0 | 2026-09-17 | major | https://registry.terraform.io/providers/hashicorp/vault |

Bold = changed since the previous run. *Behind* compares the version the bundle states
with the latest stable release; the stated version is an observation of the snapshot, so a
gap is a question for the platform, not an error in the bundle. Rows with no stated version
are context: a new release there alone is not recorded, so they are as fresh as the last run
that recorded something else.

## Not fetched by design

- https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-ci-templates — private; cited by `architecture/platform-architecture.md`, `architecture/technology-stack.md`, `delivery/docker-cosign.md`, `delivery/gitlab-cicd.md`
- https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-infrastructure — private; cited by `architecture/platform-architecture.md`, `architecture/supporting-stack.md`, `architecture/technology-stack.md`, `delivery/argocd.md`, `foundation/helm.md`, `foundation/kubernetes.md`, `foundation/kustomize.md`, `foundation/terraform.md`, `operations/observability.md`, `secrets/external-secrets.md`, `secrets/vault.md`, `security/kyverno.md`
