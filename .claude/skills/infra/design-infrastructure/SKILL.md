---
name: design-infrastructure
description: |
  Kubernetes、IaC（Terraform）、ネットワーク、マルチ環境構成を設計する。
  /design-infrastructure で呼び出し。
model: opus
user_invocable: true
---

# インフラ設計

## 達成すべき結果

本番運用に耐えるインフラ構成を設計する:
- Kubernetesクラスタ構成（ノードプール、リソースクォータ、名前空間戦略）
- コンテナオーケストレーション（デプロイ戦略、HPA、PDB）
- ネットワーク設計（mTLS、NetworkPolicy、Ingress/Gateway）
- IaC構成（Terraform modules、状態管理）
- マルチ環境戦略（dev/staging/prod、Kustomize overlays）
- ScalarDB Cluster利用時: Helm chart設定、Coordinator配置

## 前提条件

| ファイル | 必須/推奨 | 生成元 |
|---------|----------|--------|
| reports/03_design/target-architecture.md | 必須 | /design-microservices |

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/08_infrastructure/infrastructure-architecture.md` | インフラ全体設計 |
| `reports/08_infrastructure/deployment-guide.md` | デプロイ手順 |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /design-microservices | 入力元 |
| /design-security | 関連 |
| /generate-infra-code | 出力先 |
