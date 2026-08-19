---
okf_version: "0.2"
---

# AIDD Infrastructure Knowledge Bundle

Open Knowledge Format (OKF) v0.2 に準拠した、AIDD プラットフォームのインフラ設計・構築・運用知識です。

## 最初に読む

- [調査対象と技術スタック](/architecture/technology-stack.md) — 対象リポジトリから確認した採用技術とバージョン
- [全体アーキテクチャ](/architecture/platform-architecture.md) — Terraform、Kubernetes、GitOps、CI/CD の責任分界
- [設計・構築チェックリスト](/architecture/design-build-checklist.md) — 実装前から運用移管までの確認項目

## IaC と Kubernetes

- [Terraform](/foundation/terraform.md)
- [Kubernetes](/foundation/kubernetes.md)
- [Helm](/foundation/helm.md)
- [Kustomize](/foundation/kustomize.md)

## デリバリーとソフトウェアサプライチェーン

- [Argo CD](/delivery/argocd.md)
- [GitLab CI/CD](/delivery/gitlab-cicd.md)
- [Docker と Cosign](/delivery/docker-cosign.md)

## シークレット管理

- [Vault](/secrets/vault.md)
- [External Secrets Operator](/secrets/external-secrets.md)

## 可観測性とポリシー

- [Prometheus と Grafana スタック](/operations/observability.md)
- [Kyverno](/security/kyverno.md)
- [周辺スタック概要](/architecture/supporting-stack.md)

## メタデータ

- [更新履歴](/log.md)
- OKF 仕様: [Open Knowledge Format v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
