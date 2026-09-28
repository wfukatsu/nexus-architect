---
title: "okf-k8s-tf upstream report"
schema_version: 1
generated_at: "2026-09-28T06:00:00Z"
generator: tools/refresh-okf-k8s-tf.py
---

# okf-k8s-tf upstream report

What moved in the public sources of `knowledge/okf-k8s-tf/` since the previous recorded state.
Observed-implementation statements (対象実装) are facts about a private snapshot and are
**not** revised from these sources — only design guidance (設計指針), versions and freshness.

## Awaiting re-verification

Baseline run — the first recorded state. Page changes are reported from the next run.

Cumulative: a document leaves this list when it is re-verified
(`/architect:revise-knowledge`, which moves its `verified.at`).

| Document | Why |
|---|---|
| `architecture/technology-stack.md` | release Docker Engine 29.8.1: major behind stated 27 since 2026-09-15<br>release Kubernetes 1.37.1: minor behind stated 1.35 since 2026-09-23<br>release Terraform 1.16.4: minor behind stated 1.14.8 since 2026-09-23<br>release provider: aws 6.66.0: major behind stated 5.94.1 since 2026-09-21<br>release provider: azuread 3.10.0: minor behind stated 3.9.0 since 2026-09-24<br>release provider: azurerm 5.7.0: major behind stated 4.78.0 since 2026-09-24<br>release provider: google 8.4.0: major behind stated 6.44.0 since 2026-09-22<br>release provider: helm 3.3.0: major behind stated 2.17.0 since 2026-09-02<br>release provider: vault 5.12.0: major behind stated 4.8.0 since 2026-09-17 |
| `delivery/docker-cosign.md` | release Docker Engine 29.8.1: major behind stated 27 since 2026-09-15 |
| `foundation/kubernetes.md` | release Kubernetes 1.37.1: minor behind stated 1.35 since 2026-09-23 |
| `foundation/terraform.md` | release Terraform 1.16.4: minor behind stated 1.14.8 since 2026-09-23 |
| `security/kyverno.md` | release Kyverno 1.19.1: minor behind stated 1.18 since 2026-09-10 |

## Redirects applied

Rewritten in the documents' frontmatter `resource` (the source `id` is unchanged):

- `delivery/argocd.md`: https://argo-cd.readthedocs.io/ → https://argo-cd.readthedocs.io/en/stable/
- `foundation/kubernetes.md`: https://kubernetes.io/docs/ → https://kubernetes.io/docs/home/
- `foundation/kubernetes.md`: https://kubernetes.io/docs/concepts/security/overview/ → https://kubernetes.io/docs/concepts/security/
- `security/kyverno.md`: https://kyverno.io/docs/ → https://kyverno.io/docs/introduction/

## Pages

Checked 48 public pages.

## Releases

| Technology | Bundle states | Latest stable | Released | Behind | Source |
|---|---|---|---|---|---|
| Alertmanager | — | 0.34.1 | 2026-09-17 | — | https://github.com/prometheus/alertmanager/releases |
| Alloy | — | 1.20.0 | 2026-09-25 | — | https://github.com/grafana/alloy/releases |
| Argo CD | — | 3.5.3 | 2026-09-14 | — | https://github.com/argoproj/argo-cd/releases |
| Argo CD Image Updater | — | 1.3.0 | 2026-08-13 | — | https://github.com/argoproj-labs/argocd-image-updater/releases |
| Beyla | — | 3.36.0 | 2026-09-16 | — | https://github.com/grafana/beyla/releases |
| Cosign | 2.6.1 | 3.1.3 | 2026-08-06 | major | https://github.com/sigstore/cosign/releases |
| Docker Engine | 27 (EOL 2025-05-03) | 29.8.1 | 2026-09-15 | major | https://endoflife.date/docker-engine |
| External Secrets Operator | — | 2.11.0 | 2026-09-18 | — | https://github.com/external-secrets/external-secrets/releases |
| GitLab Runner | — | 19.4.1 | 2026-09-24 | — | https://gitlab.com/gitlab-org/gitlab-runner/-/releases |
| Grafana | — | 13.2.2 | 2026-09-15 | — | https://github.com/grafana/grafana/releases |
| Helm | — | 4.3.0 | 2026-09-09 | — | https://github.com/helm/helm/releases |
| Kubernetes | 1.35 (EOL 2027-02-28) | 1.37.1 | 2026-09-23 | minor | https://endoflife.date/kubernetes |
| Kustomize | — | 5.8.1 | 2026-02-09 | — | https://github.com/kubernetes-sigs/kustomize/releases |
| Kyverno | 1.18 | 1.19.1 | 2026-09-10 | minor | https://github.com/kyverno/kyverno/releases |
| Loki | — | 3.7.8 | 2026-09-17 | — | https://github.com/grafana/loki/releases |
| OpenCost | — | 1.121.3 | 2026-09-16 | — | https://github.com/opencost/opencost/releases |
| Prometheus | — | 3.15.0 | 2026-09-25 | — | https://github.com/prometheus/prometheus/releases |
| Pyrra | — | 0.10.2 | 2026-09-18 | — | https://github.com/pyrra-dev/pyrra/releases |
| Tempo | — | 3.0.3 | 2026-08-13 | — | https://github.com/grafana/tempo/releases |
| Terraform | 1.14.8 | 1.16.4 | 2026-09-23 | minor | https://github.com/hashicorp/terraform/releases |
| Vault | — | 2.1.1 | 2026-09-16 | — | https://github.com/hashicorp/vault/releases |
| provider: aws | 5.94.1 | 6.66.0 | 2026-09-21 | major | https://registry.terraform.io/providers/hashicorp/aws |
| provider: azuread | 3.9.0 | 3.10.0 | 2026-09-24 | minor | https://registry.terraform.io/providers/hashicorp/azuread |
| provider: azurerm | 4.78.0 | 5.7.0 | 2026-09-24 | major | https://registry.terraform.io/providers/hashicorp/azurerm |
| provider: google | 6.44.0 | 8.4.0 | 2026-09-22 | major | https://registry.terraform.io/providers/hashicorp/google |
| provider: helm | 2.17.0 | 3.3.0 | 2026-09-02 | major | https://registry.terraform.io/providers/hashicorp/helm |
| provider: kubectl | 1.14.0 | 1.19.0 | 2025-01-10 | minor | https://registry.terraform.io/providers/gavinbunney/kubectl |
| provider: kubernetes | 2.36.0 | 3.2.1 | 2026-07-01 | major | https://registry.terraform.io/providers/hashicorp/kubernetes |
| provider: vault | 4.8.0 | 5.12.0 | 2026-09-17 | major | https://registry.terraform.io/providers/hashicorp/vault |

Bold = changed since the previous run. *Behind* compares the version the bundle states
with the latest stable release; the stated version is an observation of the snapshot, so a
gap is a question for the platform, not an error in the bundle.

## Not fetched by design

- https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-ci-templates — private; cited by `architecture/platform-architecture.md`, `architecture/technology-stack.md`, `delivery/docker-cosign.md`, `delivery/gitlab-cicd.md`
- https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-infrastructure — private; cited by `architecture/platform-architecture.md`, `architecture/supporting-stack.md`, `architecture/technology-stack.md`, `delivery/argocd.md`, `foundation/helm.md`, `foundation/kubernetes.md`, `foundation/kustomize.md`, `foundation/terraform.md`, `operations/observability.md`, `secrets/external-secrets.md`, `secrets/vault.md`, `security/kyverno.md`
