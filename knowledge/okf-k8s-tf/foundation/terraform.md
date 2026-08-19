---
type: Technology Guide
title: Terraform の設計・構築・運用
description: AIDD のマルチクラウド IaC に必要な state、module、provider、CI 運用の知識。
resource: "https://developer.hashicorp.com/terraform/docs"
tags: [terraform, iac, state, modules, security]
generated: { by: codex/gpt-5, at: "2026-08-19T00:00:00+09:00" }
verified: { by: "process:official-document-cross-check", at: "2026-08-19T00:00:00+09:00" }
status: stable
stale_after: 2026-11-19
sources:
  - { id: tf-state, resource: "https://developer.hashicorp.com/terraform/language/state", title: Terraform state, author: "team:hashicorp" }
  - { id: tf-locking, resource: "https://developer.hashicorp.com/terraform/language/state/locking", title: State locking, author: "team:hashicorp" }
  - { id: tf-dependency-lock, resource: "https://developer.hashicorp.com/terraform/language/files/dependency-lock", title: Dependency lock file, author: "team:hashicorp" }
  - { id: tf-modules, resource: "https://developer.hashicorp.com/terraform/language/modules/develop", title: Develop modules, author: "team:hashicorp" }
  - { id: tf-style, resource: "https://developer.hashicorp.com/terraform/language/style", title: Terraform style guide, author: "team:hashicorp" }
  - { id: infrastructure-repo, resource: "https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-infrastructure", title: aidd-infrastructure }
---

# 対象実装

- Terraform 1.14.8 と各 Provider を root module で厳密に固定する。
- `global`、`environments/<cloud>/<env>/{infra,kubernetes}`、`modules/{aws,azure,gcp,kubernetes}` に分離する。
- AWS、Azure、GCP の managed Kubernetes、network、database、storage と、共通 Helm release を管理する。
- GitLab OIDC の plan/apply role を分け、remote backend と環境別 state を使う。

# State 設計

Terraform は実リソースと configuration の対応を state に保存する。state には機密値が含まれ得るため、Git に入れず、暗号化・アクセス制御・locking を備えた remote backend を使う。[tf-state]

- state の境界は変更頻度、所有チーム、権限、blast radius に合わせる。
- global、cluster infra、Kubernetes add-on を分離すると、日常的な Helm 変更がネットワーク/DB の state をロックしない。
- state 間の共有は必要最小限の output に限定する。state 全体の読取権限は実質的に全機密情報への権限と考える。
- locking を無効化しない。`force-unlock` は保持中の writer が存在しないことを確認し、自分の失敗した lock にだけ使う。[tf-locking]
- backend の versioning/backup、復旧、lock timeout、同時 pipeline の `resource_group` 等を設計する。

# Module 設計

- module は「network」「database」「kubernetes-cluster」のような高水準の能力を表す。
- `variables.tf` に type、description、validation、`outputs.tf` に description を付ける。
- module tree は浅く保ち、小さな module の合成を優先する。過剰な抽象化は変更影響を読みにくくする。[tf-modules]
- クラウド共通概念の interface は揃え、provider 固有属性や語彙は無理に隠蔽しない。
- implicit dependency を基本にし、値の参照で表せない ordering にのみ `depends_on` を使う。

# バージョンと依存性

- root module では Terraform/Provider を固定し、変更を意図的な upgrade MR にする。
- `.terraform.lock.hcl` は root configuration ごとに commit する。これは Provider の選択と checksum を記録するが、remote module の選択は記録しない。[tf-dependency-lock]
- Provider 追加・更新後は対象 root で `terraform init` を実行し、lock file の version と hash をレビューする。
- 複数 OS/architecture で使う場合は `terraform providers lock -platform=...` で hash を事前登録する。

# CI ワークフロー

1. `terraform fmt -check -recursive`
2. root ごとに `terraform init -backend=false` と `terraform validate`
3. lint/security/policy test
4. 認証後に remote backend を使って plan を生成
5. plan artifact と code commit の同一性を保って apply
6. apply 後に output/health を検証

plan と apply は異なる最小権限 role にし、apply は保護 branch/tag と承認に限定する。長期 access key ではなく GitLab OIDC から短期 credential を取得する。

# セキュリティ

- `sensitive = true` は表示抑制であり、state から値を除去しない。
- secret を `.tfvars`、plan artifact、CI log、`local-exec` 引数へ露出させない。
- saved plan は機密情報を含み得る。短期保持、限定公開、暗号化を適用する。
- apply role の権限だけでなく、Provider が refresh/read に必要な権限も明示する。
- public module/Provider の source、version、checksum、release notes を検証する。

# 変更と復旧

- upgrade は lock file 更新、`plan`、非推奨警告、state migration、rollback 可否を1単位でレビューする。
- `moved` block を利用できる rename/refactor では、直接 `terraform state mv` に依存しない宣言的移行を優先する。
- `-target` は通常運用の依存関係を壊し得るため、障害復旧等に限定し、その後 full plan で収束を確認する。
- destroy、import、state surgery は対象 address と state backup を確定してから行う。

# 最小検証

```text
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
terraform plan -detailed-exitcode
```
