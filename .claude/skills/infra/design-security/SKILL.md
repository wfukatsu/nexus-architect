---
name: design-security
description: |
  認証・認可、シークレット管理、ネットワークセキュリティ、監査ログを設計する。
  /design-security で呼び出し。
model: sonnet
user_invocable: true
---

# セキュリティ設計

## 達成すべき結果

- 認証基盤設計（OAuth2/OIDC、サービス間mTLS）
- 認可モデル（RBAC/ABAC、ポリシーエンジン）
- シークレット管理（Vault/KMS、ローテーション戦略）
- ネットワークセキュリティ（ゼロトラスト、セグメンテーション）
- 監査ログ設計（誰が、何を、いつ）
- コンプライアンス対応チェックリスト

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/08_infrastructure/security-design.md` | セキュリティ全体設計 |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /security-analysis | 入力元（既存システムの脆弱性情報） |
| /design-infrastructure | 関連 |
