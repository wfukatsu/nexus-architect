---
type: Technology Guide
title: Vault の設計・構築・運用
description: Kubernetes 上の Vault を高可用・最小権限・監査可能に運用する知識。
resource: "https://developer.hashicorp.com/vault/docs"
tags: [vault, secrets, kubernetes, security, operations]
generated: { by: codex/gpt-5, at: "2026-08-19T00:00:00+09:00" }
verified: { by: "process:official-document-cross-check", at: "2026-11-01T00:00:00+09:00" }
status: stable
stale_after: 2027-02-01
sources:
  - { id: vault-k8s, resource: "https://developer.hashicorp.com/vault/docs/deploy/kubernetes", title: Run Vault on Kubernetes, author: "team:hashicorp" }
  - { id: vault-ha, resource: "https://developer.hashicorp.com/vault/docs/concepts/ha", title: High availability, author: "team:hashicorp" }
  - { id: vault-hardening, resource: "https://developer.hashicorp.com/vault/docs/concepts/production-hardening", title: Production hardening, author: "team:hashicorp" }
  - { id: vault-policies, resource: "https://developer.hashicorp.com/vault/docs/concepts/policies", title: Policies, author: "team:hashicorp" }
  - { id: vault-audit, resource: "https://developer.hashicorp.com/vault/docs/audit", title: Audit logging, author: "team:hashicorp" }
  - { id: infrastructure-repo, resource: "https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-infrastructure", title: aidd-infrastructure }
---

# 対象実装

公式 Helm chart で Vault を Kubernetes に配置し、クラウド KMS auto-unseal、Kubernetes auth、namespace/ServiceAccount に紐づく policy、External Secrets Operator からの読取を構成する。

# Availability と Storage

本番は dev/standalone でなく HA を使う。Vault HA は複数 server を動かすが active は1台で、主目的は可用性であり水平性能向上ではない。[vault-ha]

- Integrated Storage 等の HA backend、3台以上、zone 分散、PDB、anti-affinity を設計する。
- storage の snapshot/backup と restore を試験する。暗号化済みでも改ざん・削除権限はデータ損失を起こせる。
- auto-unseal KMS の権限、可用性、key deletion protection、rotation を設計する。
- seal、leader、raft peer、storage latency、request/error、token/lease を監視する。

# Authentication と Policy

Vault policy は path と capability に対して deny-by-default である。[vault-policies]

- Kubernetes auth role を namespace と ServiceAccount に厳密に bind する。
- application、External Secrets、operator、administrator の policy を分離する。
- wildcard/glob を抑え、environment/application ごとの secret path に最小権限を与える。
- short TTL と renewable token を使い、offboarding 時は entity だけでなく active lease/token を revoke する。
- root token は初期設定後に revoke し、通常運用に使わない。

# Production hardening

公式 hardening の基準は defense in depth である。[vault-hardening]

- end-to-end TLS、non-root、swap/core dump 無効化、最小 filesystem write、network 制限。
- audit device を複数（公式は 2 つ以上を推奨）用意し、ログ停止時の挙動、rotation、中央転送、アクセス制御を設計する。有効な audit device のどれにも書き込めない要求を Vault は拒否するため、全 device の停止は Vault の停止に等しい。[vault-audit]
- clock synchronization を維持する。TTL と証明書は時刻ずれの影響を受ける。
- Vault binary/chart を定期更新し、security release を追跡する。
- cleartext cloud credential を seal stanza に書かず、cloud workload identity を使う。

# Kubernetes 固有

Vault 公式 chart は dev、standalone、HA、external mode を提供する。[vault-k8s]

- unseal、upgrade、raft peer replacement、Pod disruption の runbook を用意する。
- Vault が利用不能な場合の ExternalSecret refresh と既存 Kubernetes Secret の挙動を確認する。
- UI/API を不用意に public 公開しない。NetworkPolicy と認証を適用する。
- chart values、Vault configuration、policy、auth role を code review 可能な宣言として管理する。

# 障害復旧

- quorum loss、KMS failure、expired certificate、storage full、audit device blocked を演習する。
- snapshot の存在だけでなく、隔離環境で restore し auth/policy/secret の読取まで検証する。
- break-glass root generation は複数人統制、監査、使用後 revoke を必須にする。

# 確認事項

- 対象実装で有効化している audit device の数と種類（file / syslog / socket）を確認する。Vault は有効な audit device のどれにも書き込めない API 要求を拒否するため、device が 1 つなら、その停止（disk full、syslog 不達）が Vault 全体の停止になる。公式が推奨する 2 つ以上の device にするか、1 つのままなら blocked 時の alert と復旧手順をどう用意するかを決める。audit log では文字列値が既定で HMAC-SHA256 化され、整数や boolean は化されないため、sensitive な値を文字列で扱っているかも併せて確認する。[vault-audit]
