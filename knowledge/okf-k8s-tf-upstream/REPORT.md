---
title: "okf-k8s-tf upstream report"
schema_version: 1
generated_at: "2026-11-24T01:29:18Z"
generator: tools/refresh-okf-k8s-tf.py
---

# okf-k8s-tf upstream report

What moved in the public sources of `knowledge/okf-k8s-tf/` since the previous recorded state.
Observed-implementation statements (対象実装) are facts about a private snapshot and are
**not** revised from these sources — only design guidance (設計指針), versions and freshness.

## Awaiting re-verification

Cumulative: a document leaves this list when it is re-verified
(`/architect:revise-knowledge`, which moves its `verified.at`).

| Document | Why |
|---|---|
| `architecture/platform-architecture.md` | past stale_after 2026-11-19 |
| `architecture/supporting-stack.md` | past stale_after 2026-11-19 |
| `delivery/docker-cosign.md` | page changed 2026-11-24: https://docs.docker.com/build/building/best-practices/ |
| `delivery/gitlab-cicd.md` | page changed 2026-11-24: https://docs.gitlab.com/ci/secrets/id_token_authentication/<br>page changed 2026-11-24: https://docs.gitlab.com/ci/yaml/ |
| `foundation/kustomize.md` | past stale_after 2026-11-19 |
| `operations/observability.md` | past stale_after 2026-11-19 |
| `secrets/external-secrets.md` | past stale_after 2026-11-19 |
| `secrets/vault.md` | page changed 2026-11-24: https://developer.hashicorp.com/vault/docs/concepts/policies |

## Pages

Checked 53 public pages.

### Content changed

- https://developer.hashicorp.com/vault/docs/concepts/policies — cited by `secrets/vault.md`
- https://docs.docker.com/build/building/best-practices/ — cited by `delivery/docker-cosign.md`
- https://docs.gitlab.com/ci/secrets/id_token_authentication/ — cited by `delivery/gitlab-cicd.md`
- https://docs.gitlab.com/ci/yaml/ — cited by `delivery/gitlab-cicd.md`

## Releases

| Technology | Bundle states | Latest stable | Released | Behind | Source |
|---|---|---|---|---|---|
| Alertmanager | — | 0.35.0 | 2026-11-09 | — | https://github.com/prometheus/alertmanager/releases |
| Alloy | — | **1.22.0** | 2026-11-13 | — | https://github.com/grafana/alloy/releases |
| Argo CD | — | **3.6.2** | 2026-11-18 | — | https://github.com/argoproj/argo-cd/releases |
| Argo CD Image Updater | — | **1.5.0** | 2026-11-12 | — | https://github.com/argoproj-labs/argocd-image-updater/releases |
| Beyla | — | **3.43.0** | 2026-11-19 | — | https://github.com/grafana/beyla/releases |
| Cosign | 2.6.1 | 3.1.4 | 2026-10-20 | major | https://github.com/sigstore/cosign/releases |
| Docker Engine | 27 (EOL 2025-05-03) | **29.10.0** | 2026-11-13 | major | https://endoflife.date/docker-engine |
| External Secrets Operator | — | 2.15.0 | 2026-11-10 | — | https://github.com/external-secrets/external-secrets/releases |
| GitLab Runner | — | **19.6.0** | 2026-11-19 | — | https://gitlab.com/gitlab-org/gitlab-runner/-/releases |
| Grafana | — | 13.3.1 | 2026-11-10 | — | https://github.com/grafana/grafana/releases |
| Helm | — | **4.3.2** | 2026-11-13 | — | https://github.com/helm/helm/releases |
| Kubernetes | 1.35 (EOL 2027-02-28) | 1.37.2 | 2026-10-27 | minor | https://endoflife.date/kubernetes |
| Kustomize | — | 5.8.3 | 2026-10-08 | — | https://github.com/kubernetes-sigs/kustomize/releases |
| Kyverno | 1.18 | **1.20.0** | 2026-11-12 | minor | https://github.com/kyverno/kyverno/releases |
| Loki | — | **3.7.10** | 2026-11-13 | — | https://github.com/grafana/loki/releases |
| OpenCost | — | 1.121.4 | 2026-11-10 | — | https://github.com/opencost/opencost/releases |
| Prometheus | — | 3.16.0 | 2026-11-05 | — | https://github.com/prometheus/prometheus/releases |
| Pyrra | — | 0.10.2 | 2026-09-18 | — | https://github.com/pyrra-dev/pyrra/releases |
| Tempo | — | 3.1.1 | 2026-10-21 | — | https://github.com/grafana/tempo/releases |
| Terraform | 1.14.8 | 1.17.2 | 2026-11-11 | minor | https://github.com/hashicorp/terraform/releases |
| Vault | — | **2.2.2** | 2026-11-12 | — | https://github.com/hashicorp/vault/releases |
| provider: aws | 5.94.1 | **6.74.0** | 2026-11-23 | major | https://registry.terraform.io/providers/hashicorp/aws |
| provider: azuread | 3.9.0 | 3.10.0 | 2026-09-24 | minor | https://registry.terraform.io/providers/hashicorp/azuread |
| provider: azurerm | 4.78.0 | **5.15.0** | 2026-11-24 | major | https://registry.terraform.io/providers/hashicorp/azurerm |
| provider: google | 6.44.0 | **8.12.0** | 2026-11-17 | major | https://registry.terraform.io/providers/hashicorp/google |
| provider: helm | 2.17.0 | 3.3.0 | 2026-09-02 | major | https://registry.terraform.io/providers/hashicorp/helm |
| provider: kubectl | 1.14.0 | 1.19.0 | 2025-01-10 | minor | https://registry.terraform.io/providers/gavinbunney/kubectl |
| provider: kubernetes | 2.36.0 | 3.5.0 | 2026-11-05 | major | https://registry.terraform.io/providers/hashicorp/kubernetes |
| provider: vault | 4.8.0 | 5.13.0 | 2026-10-14 | major | https://registry.terraform.io/providers/hashicorp/vault |

Bold = changed since the previous run. *Behind* compares the version the bundle states
with the latest stable release; the stated version is an observation of the snapshot, so a
gap is a question for the platform, not an error in the bundle. Rows with no stated version
are context: a new release there alone is not recorded, so they are as fresh as the last run
that recorded something else.

## Not fetched by design

- https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-ci-templates — private; cited by `architecture/platform-architecture.md`, `architecture/technology-stack.md`, `delivery/docker-cosign.md`, `delivery/gitlab-cicd.md`
- https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-infrastructure — private; cited by `architecture/platform-architecture.md`, `architecture/supporting-stack.md`, `architecture/technology-stack.md`, `delivery/argocd.md`, `foundation/helm.md`, `foundation/kubernetes.md`, `foundation/kustomize.md`, `foundation/terraform.md`, `operations/observability.md`, `secrets/external-secrets.md`, `secrets/vault.md`, `security/kyverno.md`
