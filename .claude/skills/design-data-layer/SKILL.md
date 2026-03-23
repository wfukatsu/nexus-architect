---
name: design-data-layer
description: |
  ScalarDB非依存の汎用データベース設計を行う。
  /architect:design-data-layer で呼び出し。ScalarDB不使用プロジェクト向け。
  Do NOT use for ScalarDB projects (use /architect:design-scalardb instead).
model: opus
user_invocable: true
---

# データ層設計

## 達成すべき結果

ScalarDBを使用しないプロジェクト向けの汎用データ層設計:
- DB選定と構成（RDB/NoSQL/ハイブリッド）
- コネクションプール設計
- マイグレーション戦略
- トランザクション管理パターン
- ORM/データアクセスパターン

## 前提条件

| ファイル | 必須/推奨 | 生成元 |
|---------|----------|--------|
| reports/03_design/target-architecture.md | 必須 | /architect:design-microservices |

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/03_design/data-layer-design.md` | DB設計、トランザクション管理、マイグレーション |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /architect:design-microservices | 入力元 |
| /architect:review-data-integrity | レビュー対象 |
