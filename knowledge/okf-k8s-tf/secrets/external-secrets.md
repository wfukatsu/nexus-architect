---
type: Technology Guide
title: External Secrets Operator の設計・運用
description: Vault の secret を Kubernetes Secret に同期する際の store、lifecycle、権限、rotation の知識。
resource: "https://external-secrets.io/latest/"
tags: [external-secrets, vault, kubernetes, secrets]
generated: { by: codex/gpt-5, at: "2026-08-19T00:00:00+09:00" }
verified: { by: "process:official-document-cross-check", at: "2026-08-19T00:00:00+09:00" }
status: stable
stale_after: 2026-11-19
sources:
  - { id: eso-api, resource: "https://external-secrets.io/latest/api/externalsecret/", title: ExternalSecret API, author: "team:external-secrets" }
  - { id: eso-lifecycle, resource: "https://external-secrets.io/latest/guides/ownership-deletion-policy/", title: Lifecycle ownership and deletion, author: "team:external-secrets" }
  - { id: eso-security, resource: "https://external-secrets.io/latest/guides/security-best-practices/", title: Security best practices, author: "team:external-secrets" }
  - { id: infrastructure-repo, resource: "https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-infrastructure", title: aidd-infrastructure }
---

# 対象実装

External Secrets Operator（ESO）が Vault の値を Kubernetes Secret として同期する。Terraform module で operator、Vault auth、Store、policy を構成し、アプリ側は ExternalSecret を宣言する。

# リソースモデル

- `SecretStore`: namespace-scoped。アプリ/tenant 境界では原則こちらを優先する。
- `ClusterSecretStore`: cluster-wide。共有する場合は namespace 制限と controller class、RBAC を設計する。
- `ExternalSecret`: 取得 key、変換、target Secret、refresh/lifecycle を宣言する。[eso-api]

# Refresh policy

- `Periodic`: 既定。`refreshInterval` ごと、または spec 変更時に同期する。
- `OnChange`: ExternalSecret の metadata/spec 変更時だけ同期する。
- `CreatedOnce`: ExternalSecret object ごとに初回同期する。ただし object の再作成で再同期され得る。[eso-api]

アプリが初回 secret を DB 等へ永続化し、その後 Vault 値を変えてはいけない場合は、`CreatedOnce` だけでなく target の `immutable: true` と ownership を検討する。

# Lifecycle

`creationPolicy`、`deletionPolicy`、`refreshPolicy` の組合せで target Secret の生成、更新、削除が変わる。[eso-lifecycle]

- GitOps prune/recreate が ExternalSecret status をリセットする影響を確認する。
- `Orphan` は削除時に Secret を残すが、再作成時の上書きを防ぐものではない。
- source secret 削除時に target を削除するか保持するかを、availability と revocation の要件で決める。
- 手動で target Secret を編集しても、次の reconcile で戻ることを前提にする。

# Security

- operator の Vault policy は必要 path の read/list のみにする。
- namespace ごとに Vault role、ServiceAccount、Store を分離し、cross-namespace 参照を抑止する。
- ESO controller は多くの Secret を読める高権限 workload として、node、RBAC、NetworkPolicy、image、audit を保護する。[eso-security]
- template function や `dataFrom` で意図せず広範囲の値を Kubernetes Secret に複製しない。
- Kubernetes Secret は最終的に etcd と Pod/node に現れるため、Vault を使うだけで露出が消えるわけではない。

# Rotation

1. Vault の source を更新。
2. ESO Ready condition と refresh time を確認。
3. target Secret の resource version/hash を確認。
4. アプリが volume/env の変更を再読込できるか確認。
5. 必要なら controlled rollout。
6. 古い credential を grace period 後に revoke。

監視対象は reconcile error、provider latency/auth failure、SecretSynced condition、長時間 refresh されない ExternalSecret である。
