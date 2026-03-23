---
name: review-data-integrity
description: |
  ScalarDB非依存のデータ整合性、トランザクション安全性、スキーマ設計品質をレビューする。
  ScalarDB不使用プロジェクト向け。並列レビューシステムの一視点。
model: sonnet
user_invocable: true
---

# データ整合性レビュー

## レビュー次元

### 1. トランザクション安全性 (weight: 0.40)
- トランザクション境界の適切さ
- ACID特性の保証
- デッドロック回避設計

### 2. データ一貫性 (weight: 0.35)
- 結果整合性の許容範囲
- 競合解決戦略
- 参照整合性制約

### 3. スキーマ設計品質 (weight: 0.25)
- 正規化レベルの妥当性
- インデックス設計
- マイグレーション安全性

## 出力形式

JSON（review-consistency と同一スキーマ）。Finding IDプレフィックス: **DIN-**
