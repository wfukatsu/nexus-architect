---
type: Architecture Guide
title: AIDD インフラ全体アーキテクチャ
description: 宣言の所有者、適用経路、環境差を中心に整理した全体設計。
tags: [architecture, gitops, terraform, kubernetes, cicd]
generated: { by: codex/gpt-5, at: "2026-08-19T00:00:00+09:00" }
verified: { by: "process:repository-inspection", at: "2026-08-19T00:00:00+09:00" }
status: stable
stale_after: 2026-11-19
sources:
  - { id: infrastructure-repo, resource: "https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-infrastructure", title: aidd-infrastructure }
  - { id: ci-repo, resource: "https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-ci-templates", title: aidd-ci-templates }
---

# 責任分界

| 対象 | 宣言の置き場 | 適用者 | 状態・履歴 |
|---|---|---|---|
| クラウド基盤 | `terraform/environments/*/infra` | GitLab CI の Terraform job | remote state |
| Kubernetes 共通基盤 | `terraform/environments/*/kubernetes` と `terraform/modules/kubernetes` | Terraform の Helm/Kubernetes Provider | Terraform state、Helm release |
| 上流 Helm values | `terraform/charts` | Terraform `helm_release` | Terraform state、Helm revision |
| staging のアプリ・自作 CR | `kubernetes/staging` | Argo CD app-of-apps | Git commit、Argo CD Application |
| test のマニフェスト | `kubernetes/test` またはアプリの `k8s/` | 手順または GitLab CI の `kubectl apply` | Git commit、Kubernetes live state |

# 適用フロー

1. Terraform がネットワーク、クラスター、DB、IAM、ストレージを作成する。
2. Kubernetes 用 Terraform root が remote state の出力を受け、共通コンポーネントを Helm 等で導入する。
3. アプリ CI がテスト、スキャン、Docker build、Registry push、Cosign 署名を行う。
4. test は `kubectl apply` で直接更新する。
5. staging は manifest の image tag を Git で更新し、Argo CD が同期する。
6. Prometheus/Grafana/Loki/Tempo が運用信号を集め、Kyverno が admission 時のポリシーを強制する。

# 重要な設計原則

- 1つのリソースを複数の適用者で管理しない。Terraform、Argo CD、CI の所有範囲を明示する。
- 環境差は可能な限り values、variables、Kustomize overlay に閉じ込め、共通定義を複製しない。
- test と staging の非対称性は現状の意図された設計である。staging は GitOps、test は直接適用である。
- クラウド基盤と Kubernetes 共通基盤は state と適用順を分離し、クラスター置換時の blast radius を限定する。
- GitLab OIDC、Kubernetes ServiceAccount、Vault policy を使い、長期静的認証情報を避ける。
- イメージは build 後の digest を同一成果物として scan、sign、verify、deploy する。

# 変更時の影響分析

| 変更 | 同時に確認する対象 |
|---|---|
| Kubernetes version | kubectl、Provider、Helm chart/CRD、managed service add-on |
| Provider version | `.terraform.lock.hcl`、plan 差分、非推奨属性、state migration |
| Helm chart version | CRD、values schema、hook、rollback 方法、孤児リソース |
| ServiceAccount/namespace | IAM workload identity、Vault role/policy、RBAC、NetworkPolicy |
| image repository/tag | CI matrix、scanner、Cosign identity、Kyverno rule、Kustomize image |
| Secret path | Vault policy、SecretStore、ExternalSecret、アプリ参照、rotation |
