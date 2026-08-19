---
type: Technology Guide
title: Docker と Cosign のサプライチェーン設計
description: 再現性のあるコンテナ build と OIDC keyless signing、検証、admission を結ぶ知識。
tags: [docker, cosign, sigstore, containers, supply-chain]
generated: { by: codex/gpt-5, at: "2026-08-19T00:00:00+09:00" }
verified: { by: "process:official-document-cross-check", at: "2026-08-19T00:00:00+09:00" }
status: stable
stale_after: 2026-11-19
sources:
  - { id: docker-build, resource: "https://docs.docker.com/build/building/best-practices/", title: Building best practices, author: "team:docker" }
  - { id: cosign-overview, resource: "https://docs.sigstore.dev/cosign/signing/overview/", title: Keyless signing overview, author: "team:sigstore" }
  - { id: cosign-verify, resource: "https://docs.sigstore.dev/cosign/verifying/verify/", title: Verifying signatures, author: "team:sigstore" }
  - { id: ci-repo, resource: "https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-ci-templates", title: aidd-ci-templates }
---

# 対象実装

- Docker 27 + DinD で GitLab Registry に build/push する。
- Cosign 2.6.1 を checksum 検証して導入する。
- GitLab OIDC による keyless signing と identity/issuer を指定した verify を行う。
- Kyverno が未署名イメージを admission で拒否できる。

# Docker build

- multi-stage build で build toolchain を runtime image から除き、攻撃面と容量を減らす。[docker-build]
- `.dockerignore` で `.git`、credential、build artifact、不要な context を除外する。
- base image は信頼できる配布元を選び、version/digest を固定する。digest 固定は再現性を上げる一方、更新を自動追随しないため update process が必要である。
- package install と cache cleanup を同一 layer で行い、不要 package を入れない。
- non-root user、read-only root filesystem、明示 port、health semantics を設計する。
- secret を `ARG`/`ENV`/layer に残さず BuildKit secret mount 等を使う。

# 成果物 identity

tag は可変なので、build 後に registry digest を取得し、次のすべてへ同じ digest を渡す。

- vulnerability scan
- SBOM/provenance（導入する場合）
- Cosign signature
- deploy manifest
- incident/rollback record

# Keyless signing

Cosign keyless signing は OIDC identity に ephemeral key と短期証明書を結び付け、signing event を transparency log に記録する。[cosign-overview]

- GitLab token の issuer、subject/identity、audience、protected ref を制限する。
- `cosign verify` は issuer と certificate identity を必ず指定する。署名が存在するだけでは信頼主体を限定できない。[cosign-verify]
- sign job と deploy/admission policy の identity pattern を同じ設計資料で管理する。
- Cosign binary、checksum、download source の version を固定する。

# Admission

- CI 内 verify は早期フィードバック、Kyverno verify は cluster 境界の最終強制であり、両方を使う。
- 最初は Audit で既存 image と例外を棚卸しし、対象 repository/namespace ごとに Enforce へ移行する。
- emergency image の break-glass は期限、承認、監査、事後署名を定義する。

# 現状への改善候補

- build image の `docker:27` を patch/digest 固定する。
- build 直後に digest を artifact 化し、tag からの再解決を避ける。
- SBOM と build provenance/attestation を同じ digest に関連付ける。
