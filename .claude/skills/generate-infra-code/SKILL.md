---
name: generate-infra-code
description: |
  Kubernetes manifests、Terraform modules、Helm chartsなどのインフラコードを生成する。
  /generate-infra-code で呼び出し。
model: sonnet
user_invocable: true
---

# インフラコード生成

## 達成すべき結果

インフラ設計に基づきIaCコードを生成する:
- Kubernetes manifests（Kustomize base + overlays）
- Terraform modules（マルチクラウド対応）
- Helm values（ScalarDB Cluster用）
- NetworkPolicy、PodDisruptionBudget
- マルチ環境設定（dev/staging/prod）

## 前提条件

| ファイル | 必須/推奨 | 生成元 |
|---------|----------|--------|
| reports/08_infrastructure/ | 必須 | /architect:design-infrastructure |
| reports/03_design/target-architecture.md | 推奨 | /architect:design-microservices |

## 出力

| ファイル | 内容 |
|---------|------|
| `generated/infrastructure/k8s/` | Kubernetes manifests |
| `generated/infrastructure/terraform/` | Terraform modules |
| `generated/infrastructure/helm/` | Helm values |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /architect:design-infrastructure | 入力元 |
