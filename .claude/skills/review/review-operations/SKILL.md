---
name: review-operations
description: |
  運用準備状態をレビューする。監視、DR、セキュリティ、デプロイ安全性。
  並列レビューシステムの一視点。
model: sonnet
user_invocable: true
---

# 運用準備レビュー

## レビュー次元

### 1. 監視・可観測性 (weight: 0.30)
- SLI/SLO定義、分散トレーシング、アラート閾値、ヘルスチェック

### 2. 災害復旧 (weight: 0.30)
- RTO/RPO定義、バックアップ戦略、フェイルオーバー設計、リカバリ手順

### 3. セキュリティ態勢 (weight: 0.20)
- 認証・認可設計、シークレット管理、ネットワーク分離、監査ログ

### 4. デプロイ安全性 (weight: 0.20)
- デプロイ戦略（blue-green/canary）、ロールバック手順、DB migration安全性

## 出力形式

JSON（review-consistency と同一スキーマ）。Finding IDプレフィックス: **OPS-**
