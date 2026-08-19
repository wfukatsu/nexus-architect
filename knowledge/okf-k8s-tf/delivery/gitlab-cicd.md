---
type: Technology Guide
title: GitLab CI/CD のインフラ・アプリ配信設計
description: 再利用テンプレート、OIDC、Runner、セキュリティ検査、環境保護の設計知識。
resource: "https://docs.gitlab.com/ci/"
tags: [gitlab, cicd, runner, oidc, devsecops]
generated: { by: codex/gpt-5, at: "2026-08-19T00:00:00+09:00" }
verified: { by: "process:official-document-cross-check", at: "2026-08-19T00:00:00+09:00" }
status: stable
stale_after: 2026-11-19
sources:
  - { id: gitlab-yaml, resource: "https://docs.gitlab.com/ci/yaml/", title: CI/CD YAML syntax, author: "team:gitlab" }
  - { id: gitlab-components, resource: "https://docs.gitlab.com/ci/components/", title: CI/CD components, author: "team:gitlab" }
  - { id: gitlab-oidc, resource: "https://docs.gitlab.com/ci/secrets/id_token_authentication/", title: ID token authentication, author: "team:gitlab" }
  - { id: gitlab-dind, resource: "https://docs.gitlab.com/ci/docker/docker_in_docker/", title: Docker-in-Docker, author: "team:gitlab" }
  - { id: ci-repo, resource: "https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-ci-templates", title: aidd-ci-templates }
---

# 対象実装

共通 `microservice.yml` が security、build、test、deploy、promote、smoke、DAST、notify を組み立てる。Dockerfile や `k8s/` の有無と変数に応じて job を段階的に有効化する。

主な流れは次のとおり。

1. Secret Detection、SAST、Dependency Scanning
2. unit test と Docker build/push
3. Container Scanning、Cosign sign/verify
4. main から test へ `kubectl apply`
5. E2E 後に manifest を更新し staging を Argo CD で同期
6. smoke test、失敗通知
7. schedule で DAST/API/Coverage Fuzzing

# Template 設計

- consumer は template を release tag または commit SHA に固定する。`main`/`latest` は予告なく挙動を変える。
- job 名の衝突は GitLab の merge semantics により意図しない上書きを生む。公開 interface と hidden job 名を定義する。[gitlab-components]
- 入力、必要変数、権限、生成される job、override 方法、破壊的変更を README と release note に記録する。
- template 自体を sample repository/Dockerfile に対して test する。
- 将来は `include:project` template から versioned CI/CD component への移行を評価できる。

# Pipeline の完全性

- scan、sign、verify は build job と同一の immutable image digest を受け取る。
- matrix は1か所の image inventory を共有し、複数 Dockerfile の scan/sign 漏れを防ぐ。
- `allow_failure` の security job は、pipeline 緑色と安全性を同義にしない。結果収集と severity gate を別途定義する。
- artifact、cache、dotenv の機密性、保持期間、downstream job への伝播を限定する。
- `rules` の branch、MR、schedule、tag、fork 条件を test する。

# 認証

GitLab ID token は job ごとに OIDC JWT を発行し、cloud/Vault/Sigstore の短期 credential と交換できる。[gitlab-oidc]

- audience、project path、ref type、protected ref 等の claim を trust policy で絞る。
- plan、apply、deploy、sign の role を分ける。
- CI variable の長期 cloud key を廃止し、job token の allowlist と scope も最小化する。

# Runner と DinD

DinD は privileged mode を必要とし、container の security mechanism を実質的に弱める。GitLab 公式も container breakout/権限昇格リスクを明記する。[gitlab-dind]

- DinD runner を専用・ephemeral・信頼済み project 限定にする。
- untrusted fork/MR と secret/production credential を同じ runner に置かない。
- `docker:27` のような major tag だけでなく、可能なら patch または digest まで固定する。
- TLS を有効にし、daemon socket/volume の job 間共有を避ける。
- rootless BuildKit/Kaniko 等への移行は互換性、cache、署名フローと合わせて評価する。

# Environment 保護

- protected branch/tag、protected environment、approval、resource group で apply/deploy の主体と直列化を制御する。
- staging/production は manifest repository への変更を監査可能な MR/commit として残す。
- rollback、retry、cancel が外部状態に与える影響を job ごとに定義する。
