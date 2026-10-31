---
type: Technology Guide
title: Helm の設計・構築・運用
description: Kubernetes 共通コンポーネントを chart と release で安全に管理する知識。
resource: "https://helm.sh/docs/"
tags: [helm, kubernetes, charts, releases]
generated: { by: codex/gpt-5, at: "2026-08-19T00:00:00+09:00" }
verified: { by: "process:official-document-cross-check", at: "2026-11-01T00:00:00+09:00" }
status: stable
stale_after: 2027-02-01
sources:
  - { id: helm-intro, resource: "https://helm.sh/docs/intro/introduction/", title: Introduction to Helm, author: "team:helm" }
  - { id: helm-use, resource: "https://helm.sh/docs/intro/using_helm/", title: Using Helm, author: "team:helm" }
  - { id: helm-best-practices, resource: "https://helm.sh/docs/chart_best_practices/", title: Chart best practices, author: "team:helm" }
  - { id: helm-hooks, resource: "https://helm.sh/docs/topics/charts_hooks/", title: Chart hooks, author: "team:helm" }
  - { id: helm-upgrade, resource: "https://helm.sh/docs/helm/helm_upgrade/", title: Helm Upgrade, author: "team:helm" }
  - { id: infrastructure-repo, resource: "https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-infrastructure", title: aidd-infrastructure }
---

# 対象実装

Terraform `helm_release` で Argo CD、Vault、External Secrets、Kyverno、Prometheus/Grafana、Loki、Tempo、Kong、Keycloak、Velero 等を導入する。環境別 values は `terraform/charts` に置く。

# Chart と Release

Chart は Kubernetes resource の versioned package、Release は特定 cluster/namespace への installation である。values により同一 chart の環境差を表し、upgrade/rollback の revision history を持つ。[helm-intro]

- chart version、app version、container image version を別概念として記録する。
- repository/chart/version を固定し、upgrade MR で release notes と values schema を確認する。
- `values.yaml` は既定値、環境差は別 values、secret は外部 secret store に分離する。
- `helm template` と schema validation で render 結果を CI 検証する。

# Terraform との組み合わせ

- release の所有者を Terraform に統一し、同じ release を Argo CD や手動 Helm で変更しない。
- `set_sensitive` でも state に値が残り得るため、機密値自体を Terraform/Helm に渡さない設計を優先する。
- Provider timeout、`atomic`、`wait`、cleanup-on-fail を workload の起動時間と rollback 特性に合わせる。
- Terraform state と Helm release history の双方を障害調査に利用する。

# CRD

- CRD と controller/chart の upgrade ordering、変換 webhook、stored version、削除影響を事前確認する。
- CRD は通常の release resource と lifecycle が異なる場合がある。chart uninstall が CRD/CR を残すかを確認する。
- rollback で古い controller が新しい CR schema を読めるとは限らないため、DB/schema migration と同様に扱う。

# Hooks

hook は install/upgrade/rollback の特定時点で Job 等を実行できるが、失敗、再実行、削除 policy を設計する必要がある。[helm-hooks]

- migration/backup hook は idempotent にする。
- hook resource が孤児化しない cleanup policy と TTL を設定する。
- 外部サービス変更を hook に隠すと Terraform/Argo CD から見えにくくなるため、使用を限定する。

# Upgrade と rollback

1. release notes、breaking change、CRD、values 差分を確認。
2. `helm lint`、`helm template`、server-side dry-run 相当を実施。
3. test cluster で upgrade と failure/rollback を試験。
4. `helm get values`、`helm history`、workload health を確認。[helm-use]
5. orphan cluster-scoped resource と古い CRD を確認。

# 確認事項

- Helm 4 の `helm upgrade` には `--atomic` が無い。失敗時の rollback は `--rollback-on-failure`（指定すると `--wait` の既定が `watcher` になる）、置換による強制更新は `--force-replace`、`--wait` は strategy を取る（省略時 `hookOnly`、指定時 `watcher`）、`--cleanup-on-fail` は従来どおり（Helm 4.3.1 版の CLI reference）。対象実装の Terraform helm provider 2.17.0 の `atomic`・`force_update`・`wait` 属性が、provider 3.x（2026-11-01 時点の最新は 2026-09-02 リリースの 3.3.0）で Helm 4 のどの挙動に対応するかを確認してから、「Terraform との組み合わせ」の `atomic` の項を読み替える。[helm-upgrade]
