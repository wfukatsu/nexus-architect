---
type: Technology Guide
title: Kyverno の Policy as Code 設計
description: Kubernetes admission、image verification、policy report を安全に段階導入する知識。
resource: "https://kyverno.io/docs/"
tags: [kyverno, kubernetes, policy, admission, cosign]
generated: { by: codex/gpt-5, at: "2026-08-19T00:00:00+09:00" }
verified: { by: "process:official-document-cross-check", at: "2026-08-19T00:00:00+09:00" }
status: stable
stale_after: 2026-10-19
sources:
  - { id: kyverno-overview, resource: "https://kyverno.io/docs/policy-types/overview/", title: Policy types overview, author: "team:kyverno", last_modified: 2026-08-01 }
  - { id: kyverno-validate, resource: "https://kyverno.io/docs/policy-types/cluster-policy/validate/", title: Validate rules, author: "team:kyverno" }
  - { id: kyverno-reports, resource: "https://kyverno.io/docs/guides/reports/", title: Policy reports, author: "team:kyverno" }
  - { id: infrastructure-repo, resource: "https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-infrastructure", title: aidd-infrastructure }
---

# 対象実装

Terraform の Kyverno module が chart と ClusterPolicy 群を導入し、registry credential と Cosign 署名済み image の検証等を行う。CI の image inventory と Kyverno の許可 repository/identity を一致させる必要がある。

# 重要な非推奨情報

Kyverno v1.18 では新しい `policies.kyverno.io/v1` の ValidatingPolicy、MutatingPolicy、GeneratingPolicy、ImageValidatingPolicy が stable になり、従来の `kyverno.io/v1 ClusterPolicy` は deprecated で critical fix only となった。v1.20（2026年10月予定）で removal が計画されている。[kyverno-overview]

対象リポジトリは現時点で `ClusterPolicy` を使用しているため、以下を早急に行う。

1. 利用 chart/Kyverno version と実際の removal schedule を再確認。
2. policy inventory と対応する新 policy type を作成。
3. test cluster で evaluation/report/admission behavior を比較。
4. Audit で並行観測してから切替。
5. Terraform state/resource と CRD の移行順を定義。

# Policy 設計

- validate: 必須 label、resource limit、Pod security、禁止 field 等を検証。
- mutate: default を補完する。ただし入力が暗黙に変わるため、重要 security field は validate を優先。
- generate: namespace ごとの NetworkPolicy/RBAC 等を配布。ownership と同期/削除を設計。
- image verification: Cosign identity、issuer、attestation、repository を検証。

policy は小さく単一目的にし、対象 kind/namespace/user/service account と例外を明示する。

# Audit から Enforce

validate failure action は Audit なら resource を許可し report、Enforce なら admission を拒否する。[kyverno-validate]

1. Audit で既存違反と false positive を収集。
2. policy report を owner/severity/期限付き backlog に変換。
3. CI の `kyverno test` 等で新 manifest を事前検査。
4. namespace/workload 単位で Enforce。
5. rejection metric、Event、admission latency を監視。

# PolicyReport

PolicyReport は現在の resource に対する評価結果であり、過去の拒否履歴ではない。blocked admission の調査には Event、execution metric、audit log を併用する。[kyverno-reports]

- report の pass/fail/error/skip を収集し、policy/namespace/owner で可視化する。
- background scan の権限と対象を確認する。
- report 消失を historical compliance の消失と理解し、必要なら外部保存する。

# Image verification

- tag でなく digest を検証対象にする。
- GitLab の OIDC issuer と許可 project/ref identity を明示する。
- CI verify と admission verify の policy を同一 source から管理する。
- private registry の credential scope、rotation、failure mode を検証する。
- registry/Sigstore endpoint 障害時の fail-open/fail-closed と availability impact を決める。

# Kyverno 自体の可用性

- admission controller replica、PDB、anti-affinity、resource、webhook timeout/failurePolicy を設計する。
- policy error が cluster-wide deploy outage になり得るため、canary namespace と rollback path を用意する。
- controller image/chart/CRD を固定し、Kubernetes upgrade 前に互換性を確認する。
- policy/exception 変更を protected MR と approval で管理し、break-glass に期限を付ける。
