---
type: Checklist
title: インフラ設計・構築チェックリスト
description: AIDD スタックで設計、実装、検証、運用移管する際の横断チェックリスト。
tags: [checklist, design, build, operations, security]
generated: { by: codex/gpt-5, at: "2026-08-19T00:00:00+09:00" }
status: stable
stale_after: 2026-11-19
sources:
  - { id: terraform-style, resource: "https://developer.hashicorp.com/terraform/language/style", title: Terraform style guide }
  - { id: kubernetes-prod, resource: "https://kubernetes.io/docs/setup/production-environment/", title: Production environment }
  - { id: gitlab-components, resource: "https://docs.gitlab.com/ci/components/", title: GitLab CI/CD components }
---

# 要件・境界

- [ ] 可用性、RTO/RPO、性能、保持期間、予算、法令・データ所在を数値化した。
- [ ] test/staging/production の目的、データ、アクセス、変更承認を分離した。
- [ ] Terraform、Argo CD、CI、手動運用の所有リソースが重複していない。
- [ ] namespace、クラウドアカウント/サブスクリプション/プロジェクト、state の障害境界を定義した。

# IaC

- [ ] Terraform/Provider/module/chart のバージョンを固定し、lock file をレビューした。
- [ ] remote state は暗号化、アクセス制御、locking、versioning/backup を備える。
- [ ] `fmt`、`validate`、plan、静的検査を CI で行い、apply は保護された ref に限定する。
- [ ] plan と apply の主体、認証、承認、同時実行制御を定義した。
- [ ] destroy、import、state move、Provider upgrade の手順を準備した。

# Kubernetes

- [ ] requests/limits、probe、PDB、複数 replica、topology spread を要件に応じて設定した。
- [ ] RBAC と workload identity は namespace と ServiceAccount 単位の最小権限である。
- [ ] Pod Security、NetworkPolicy、Kyverno admission policy の段階導入を設計した。
- [ ] Secret を Git や平文 values に置かず、rotation 後の再読込方法を決めた。
- [ ] CRD を含む upgrade/rollback と Kubernetes version skew を検証した。

# デリバリー

- [ ] CI template と job image は commit/tag/version または digest で固定した。
- [ ] runner を信頼境界別に分離し、DinD privileged runner に無関係な job を置かない。
- [ ] build、scan、sign、verify、deploy が同じ image digest を参照する。
- [ ] staging/production は Git の宣言を変更し、Argo CD の差分と health を確認する。
- [ ] GitOps の prune/self-heal、自動同期、sync wave の失敗条件を決めた。

# 運用

- [ ] SLI/SLO、recording rule、alert、dashboard、runbook がサービス単位で結び付いている。
- [ ] symptom-based alert とインフラ自身の dead-man/availability alert がある。
- [ ] メトリクス・ログ・トレースの label cardinality と保持コストを見積もった。
- [ ] backup だけでなく restore を定期試験し、RTO/RPO を測定する。
- [ ] Provider、chart、Kubernetes、CI template の定期更新担当と期限を決めた。
