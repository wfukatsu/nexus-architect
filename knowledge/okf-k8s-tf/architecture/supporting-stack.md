---
type: Reference
title: 周辺技術スタック概要
description: 今回の詳細調査外だが対象実装を構成する技術の役割と依存関係。
tags: [inventory, supporting-stack, kubernetes]
generated: { by: codex/gpt-5, at: "2026-08-19T00:00:00+09:00" }
verified: { by: "process:repository-inspection", at: "2026-08-19T00:00:00+09:00" }
status: stable
stale_after: 2026-11-19
sources:
  - { id: infrastructure-repo, resource: "https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-infrastructure", title: aidd-infrastructure }
---

# Kubernetes 周辺

| 技術 | 役割 | 中核との接続 |
|---|---|---|
| Kong Gateway Operator / Konnect | API gateway の control/data plane | Gateway API、Kubernetes、OIDC、Prometheus |
| Gateway API | HTTPRoute 等の標準的な L4/L7 routing API | Kong Operator、cert-manager |
| cert-manager / trust-manager | 証明書発行と trust bundle 配布 | Kubernetes Secret、Gateway、Vault |
| Keycloak | OIDC/OAuth 2.0 の認証・認可 | Kong、Grafana、DB、External Secrets |
| Falco | runtime threat detection | Kubernetes audit/runtime signal、監視通知 |
| Velero | Kubernetes resource/PV backup | object storage、snapshot controller |
| Karpenter | AWS の node provisioning | EKS、IAM、SQS/EventBridge |
| Descheduler | placement policy に基づく再配置 | scheduler、PDB、node topology |
| Chaos Mesh / AWS FIS | 障害注入 | Kubernetes、AWS、SLO/alert |

# クラウドサービス

- AWS: EKS、VPC、RDS、DynamoDB、S3、EMR Serverless、IAM/OIDC、CloudTrail、GuardDuty、FIS。
- Azure: AKS、VNet、PostgreSQL Flexible Server、Key Vault、Storage、Synapse、Managed Identity。
- GCP: GKE、VPC、Cloud SQL、Cloud Storage、KMS、Dataproc、Workload Identity。

# 製品固有

ScalarDB Cluster、ScalarDB Analytics、Scalar Manager は ScalarDB プラットフォームを構成する。一般基盤の設計変更時には chart/CRD、DB、object storage、認証、監視との互換性を製品ドキュメントで追加確認する。
