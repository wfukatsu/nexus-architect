---
type: Technology Guide
title: Kubernetes の設計・構築・運用
description: managed Kubernetes 上で安全で可用性のあるワークロードと共通基盤を設計する知識。
resource: "https://kubernetes.io/docs/"
tags: [kubernetes, workloads, networking, security, operations]
generated: { by: codex/gpt-5, at: "2026-08-19T00:00:00+09:00" }
verified: { by: "process:official-document-cross-check", at: "2026-08-19T00:00:00+09:00" }
status: stable
stale_after: 2026-11-19
sources:
  - { id: k8s-workloads, resource: "https://kubernetes.io/docs/concepts/workloads/", title: Workloads, author: "team:kubernetes" }
  - { id: k8s-prod, resource: "https://kubernetes.io/docs/setup/production-environment/", title: Production environment, author: "team:kubernetes" }
  - { id: k8s-security, resource: "https://kubernetes.io/docs/concepts/security/overview/", title: Cloud native security overview, author: "team:kubernetes" }
  - { id: k8s-version-skew, resource: "https://kubernetes.io/releases/version-skew-policy/", title: Version skew policy, author: "team:kubernetes" }
  - { id: infrastructure-repo, resource: "https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-infrastructure", title: aidd-infrastructure }
---

# 対象実装

- EKS、AKS、GKE の managed control plane を Terraform で作成する。
- Kubernetes 共通コンポーネントは主に Terraform `helm_release`、staging アプリは Argo CD、test は `kubectl apply` で管理する。
- Kubernetes 1.35 系に合わせた kubectl を CI で利用する。

# Workload 設計

Pod を直接運用せず、Deployment、StatefulSet、DaemonSet、Job 等の controller を利用して desired state を維持する。[k8s-workloads]

- stateless service は複数 replica、readiness/liveness/startup probe、requests/limits を定義する。
- PDB は voluntary disruption に対する可用性を表す。replica 数、rollout strategy、node upgrade と整合させる。
- topology spread/anti-affinity で zone/node failure domain に分散する。
- stateful workload は storage class、backup、restore、volume expansion、zone constraint を設計する。
- Job は retry、deadline、idempotency、cleanup を明示する。

# Namespace と権限境界

- namespace は環境、チーム、ワークロードの信頼境界として使い、命名、quota、limit、default deny policy をセットで提供する。
- 人と workload の権限を分離し、ServiceAccount ごとに RBAC とクラウド workload identity を割り当てる。
- `cluster-admin`、wildcard verb/resource、default ServiceAccount token の使用を避ける。
- namespace-scoped RBAC と cloud IAM の両方が必要な操作では、片側だけ広くしない。

# Network と公開

- Service は安定した service discovery を、Gateway API/Kong は north-south routing を担当する。
- ingress/egress は default deny から必要通信を許可する NetworkPolicy を設計する。
- TLS の終端位置、再暗号化、certificate ownership、DNS ownership を明示する。
- control plane endpoint、node、DB、Vault、observability endpoint の到達元を制限する。

# Configuration と Secret

- ConfigMap は非機密設定、Secret は機密値の参照に使う。ただし Secret の base64 は暗号化ではない。
- Git に平文 Secret を置かず、Vault と [External Secrets Operator](/secrets/external-secrets.md) で同期する。
- secret rotation 時に Pod が volume/env を再読込する挙動を確認し、必要なら rollout automation を設ける。
- CRD と Custom Resource の lifecycle owner、upgrade ordering、backup 対象を明記する。

# Security

Kubernetes の security は cloud、cluster、container、code の複数層で考える。[k8s-security]

- Pod Security Standards を基準に non-root、capability drop、seccomp、read-only filesystem を適用する。
- admission policy は [Kyverno](/security/kyverno.md) で Audit から Enforce へ段階導入する。
- image tag ではなく digest と署名 identity を検証する。
- node pool と runner を workload の信頼度に応じて分離する。
- audit log、admission rejection、RBAC change、privileged workload を監視する。

# Upgrade

- control plane、node、kubectl、Provider、add-on、CRD/chart の互換表を作る。
- Kubernetes は component ごとに許容 version skew が異なるため公式 policy を確認する。[k8s-version-skew]
- deprecated API を事前スキャンし、Pod disruption と capacity headroom を検証する。
- managed cluster の upgrade 前に backup/restore と rollback/forward-fix 方針を確認する。

# 運用信号

- API server、scheduler、node、CNI、DNS、storage、admission webhook の health を監視する。
- workload は availability、latency、error、saturation を SLI として持つ。
- Events は短期診断、metrics/logs/traces は長期分析として保持設計を分ける。
