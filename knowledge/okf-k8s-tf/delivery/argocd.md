---
type: Technology Guide
title: Argo CD の GitOps 設計・運用
description: staging 環境を app-of-apps で安全に同期するための設計知識。
resource: "https://argo-cd.readthedocs.io/"
tags: [argocd, gitops, kubernetes, deployment]
generated: { by: codex/gpt-5, at: "2026-08-19T00:00:00+09:00" }
verified: { by: "process:official-document-cross-check", at: "2026-08-19T00:00:00+09:00" }
status: stable
stale_after: 2026-11-19
sources:
  - { id: argocd-auto-sync, resource: "https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/", title: Automated Sync Policy, author: "team:argoproj" }
  - { id: argocd-declarative, resource: "https://argo-cd.readthedocs.io/en/stable/operator-manual/declarative-setup/", title: Declarative Setup, author: "team:argoproj" }
  - { id: argocd-sync-waves, resource: "https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/", title: Sync Phases and Waves, author: "team:argoproj" }
  - { id: argocd-security, resource: "https://argo-cd.readthedocs.io/en/stable/operator-manual/security/", title: Security considerations, author: "team:argoproj" }
  - { id: infrastructure-repo, resource: "https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-infrastructure", title: aidd-infrastructure }
---

# 対象実装

staging は `kubernetes/staging/kustomization.yaml` を入口にした app-of-apps で管理する。Application CR、Kong、ScalarDB、自作 Alertmanager/Pyrra chart を Git から同期する。

# Git を desired state にする

- live cluster を直接編集せず、Git の宣言を変更する。
- CI は staging cluster へ直接 deploy せず、manifest repository の image reference を更新する。
- Application、Project、repository credential、RBAC も可能な限り宣言的に管理する。[argocd-declarative]
- secret は Git に置かず、外部 secret 管理へ委譲する。

# Application 境界

- ownership、権限、同期順、障害範囲が同じ resource を1 Application にまとめる。
- AppProject で source repository、destination cluster/namespace、許可 resource kind を制限する。
- cluster-scoped resource を扱う Application は通常アプリから分離し、強い権限を局所化する。
- app-of-apps root への書込権限は cluster 管理権限に近いものとして保護する。

# 自動同期

automated sync は CI が Argo CD API を直接呼ばず Git commit だけで deploy を完結できる。[argocd-auto-sync]

- `prune` は Git から消えた resource を削除する。意図しない大量削除を防ぐ review と orphan monitoring を用意する。
- `selfHeal` は live drift を Git に戻す。break-glass の手順と drift の監査を用意する。
- empty desired state に対する prune 保護を維持する。
- production は sync window、manual approval、protected branch 等を要件に応じて追加する。

# Ordering と Health

- namespace/CRD/controller/CR の依存は phase と wave で明示する。[argocd-sync-waves]
- PreSync migration は idempotent にし、失敗時に application 全体を止める条件を定義する。
- custom resource の health assessment がない場合、同期成功とサービス ready を混同しない。
- sync 後は revision、Sync status、Health status、主要 SLI を確認する。

# セキュリティ

- SSO/OIDC、最小権限 RBAC、AppProject、repository allowlist を使う。
- admin account、local account、API token、repository credential を定期棚卸しする。
- webhook と UI/API の TLS、NetworkPolicy、audit log を保護する。[argocd-security]
- Application が参照する Helm/Kustomize remote source を immutable revision に固定する。

# 復旧

- rollback は原則 Git revert/forward-fix で行い、desired state と live state を一致させる。
- Argo CD の一時 rollback 後に auto-sync が新 revision を再適用する挙動に注意する。
- Argo CD 自体の障害時も workload は動作を継続するが、新規同期と drift correction は停止する。
