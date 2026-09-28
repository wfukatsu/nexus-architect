---
type: Technology Inventory
title: AIDD インフラ技術スタック
description: 対象2リポジトリの実装から抽出した技術、役割、調査範囲。
tags: [aidd, inventory, infrastructure, kubernetes, terraform]
generated: { by: codex/gpt-5, at: "2026-08-19T00:00:00+09:00" }
verified: { by: "process:official-document-cross-check", at: "2026-09-28T00:00:00+09:00" }
status: stable
stale_after: 2026-12-28
sources:
  - id: infrastructure-repo
    resource: "https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-infrastructure"
    title: aidd-infrastructure
    author: "team:scalar-labs"
    last_modified: 2026-08-18
  - id: ci-repo
    resource: "https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-ci-templates"
    title: aidd-ci-templates
    author: "team:scalar-labs"
    last_modified: 2026-08-03
---

# 調査スナップショット

| リポジトリ | commit | 確認日 |
|---|---|---|
| `aidd-infrastructure` | `ed2689dc47ade5b5ae5c0529ad39eaba403de279` | 2026-08-19 |
| `aidd-ci-templates` | `44139cad79c8d8255ef81b0109e5b10f119b1612` | 2026-08-19 |

# 中核スタック

| 領域 | 採用技術 | リポジトリでの使われ方 | 詳細 |
|---|---|---|---|
| IaC | Terraform 1.14.8 | AWS、Azure、GCP、Kubernetes の環境・再利用モジュール | [Terraform](/foundation/terraform.md) |
| オーケストレーション | Kubernetes 1.35 系 | EKS、AKS、GKE。アプリと共通ミドルウェアを実行 | [Kubernetes](/foundation/kubernetes.md) |
| パッケージ | Helm | 共通ミドルウェアを `helm_release` で導入 | [Helm](/foundation/helm.md) |
| マニフェスト差分 | Kustomize | ScalarDB の base/DB/scale overlay、Argo CD app-of-apps | [Kustomize](/foundation/kustomize.md) |
| GitOps | Argo CD、Image Updater | staging の宣言的デプロイと同期 | [Argo CD](/delivery/argocd.md) |
| CI/CD | GitLab CI/CD、Runner | plan/apply、スキャン、ビルド、署名、test deploy、staging promote | [GitLab CI/CD](/delivery/gitlab-cicd.md) |
| コンテナ | Docker 27、DinD | イメージを build/push | [Docker と Cosign](/delivery/docker-cosign.md) |
| 署名 | Cosign 2.6.1 | GitLab OIDC による keyless signing と検証 | [Docker と Cosign](/delivery/docker-cosign.md) |
| シークレット | Vault | シークレットの保存、Kubernetes auth、ポリシー | [Vault](/secrets/vault.md) |
| Secret 同期 | External Secrets Operator | Vault から Kubernetes Secret へ同期 | [External Secrets](/secrets/external-secrets.md) |
| 監視 | Prometheus、Alertmanager、Grafana | メトリクス、ルール、通知、ダッシュボード | [可観測性](/operations/observability.md) |
| ログ・トレース | Loki、Tempo、Alloy、Beyla | ログ、トレース、収集、eBPF 計装 | [可観測性](/operations/observability.md) |
| SLO・コスト | Pyrra、OpenCost | SLO 定義、コスト可視化 | [可観測性](/operations/observability.md) |
| ポリシー | Kyverno | admission policy、署名済みイメージ強制 | [Kyverno](/security/kyverno.md) |

# Terraform Provider

ルートモジュールでは Provider と Terraform のバージョンを厳密に固定している。

| Provider | 確認できた固定バージョン |
|---|---:|
| AWS | 5.94.1 |
| AzureRM | 4.78.0 |
| AzureAD | 3.9.0 |
| Google | 6.44.0 |
| Helm | 2.17.0 |
| Kubernetes | 2.36.0 |
| Vault | 4.8.0 |
| kubectl | 1.14.0 |

# 周辺スタック

Kong Gateway Operator/Konnect、Gateway API、cert-manager、trust-manager、Keycloak、Falco、Velero、Karpenter、Descheduler、Chaos Mesh、およびクラウド固有サービスも利用する。今回の範囲では構成上の位置づけを[周辺スタック概要](/architecture/supporting-stack.md)にまとめ、個別製品の詳細調査は行っていない。

# 読み方

各技術文書は次を区別する。

- 「対象実装」: 調査した2リポジトリで確認できた事実。
- 「設計指針」: 公式ドキュメントを根拠とする推奨事項。
- 「確認事項」: 適用前に環境依存の判断が必要な項目。

# 確認事項

上表の version は調査スナップショット（2026-08-19）での固定値であり、そのまま事実として残す。2026-09-28 時点の各公開 release との差は次のとおりで、上げるかどうか・いつ上げるかは platform の判断である（`knowledge/okf-k8s-tf-upstream/REPORT.md`）。

| 対象 | 固定値 | 最新 stable | 差 | 備考 |
|---|---:|---:|---|---|
| Terraform | 1.14.8 | 1.16.4 | minor | [Terraform](/foundation/terraform.md) の確認事項 |
| Kubernetes | 1.35 系 | 1.37.1 | minor | 1.35 は EOL 2027-02-28。[Kubernetes](/foundation/kubernetes.md) の確認事項 |
| Docker | 27 | 29.8.1 | major | 27 は 2025-05-03 に EOL |
| Cosign | 2.6.1 | 3.1.3 | major | v3 で新 bundle 形式・trusted root・signing config が既定になり、v4 で旧機能は削除予定。[Docker と Cosign](/delivery/docker-cosign.md) の確認事項 |
| AWS Provider | 5.94.1 | 6.66.0 | major | |
| AzureRM Provider | 4.78.0 | 5.7.0 | major | |
| AzureAD Provider | 3.9.0 | 3.10.0 | minor | |
| Google Provider | 6.44.0 | 8.4.0 | major（2 つ） | |
| Helm Provider | 2.17.0 | 3.3.0 | major | |
| Kubernetes Provider | 2.36.0 | 3.2.1 | major | |
| Vault Provider | 4.8.0 | 5.12.0 | major | |
| kubectl Provider | 1.14.0 | 1.19.0 | minor | |

- major 差の Provider は、各 Provider の upgrade guide で破壊的変更を確認し、Terraform 本体を含めた upgrade 順序と root module ごとの MR 単位を決める。
- Kyverno の version はスナップショットの記述から特定できない。v1.20 で ClusterPolicy が removal されるため、[Kyverno](/security/kyverno.md) の確認事項を先に扱う。
