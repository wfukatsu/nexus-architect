---
name: design-scalardb
description: |
  ScalarDBスキーマ設計、トランザクション境界、ストレージバックエンド設計を行う。
  /architect:design-scalardb で呼び出し。ScalarDB利用プロジェクト専用。
  Do NOT use for projects not using ScalarDB (use /architect:design-data-layer instead).
model: opus
user_invocable: true
---

# ScalarDB設計

## 達成すべき結果

ScalarDBを活用したデータアーキテクチャを設計する:
1. **スキーマ設計** — パーティションキー、クラスタリングキー、セカンダリインデックス
2. **トランザクション境界** — Consensus Commit/2PC/Saga の選択と境界定義
3. **マイグレーション計画** — 既存DBからScalarDBへの移行戦略

## 判断基準

- Context7 MCP で最新のScalarDB仕様を確認してから設計に着手する
- 2PCは最大2-3サービスに制限
- OCC競合率5%未満を目標としたキー設計
- ストレージバックエンドは要件に基づいて選択（JDBC/Cassandra/DynamoDB等）
- ScalarDB管理テーブルではDB固有機能を使用しない

詳細パターン: @.claude/rules/scalardb-coding-patterns.md
エディション比較: @.claude/rules/scalardb-edition-profiles.md

## 前提条件

| ファイル | 必須/推奨 | 生成元 |
|---------|----------|--------|
| reports/03_design/target-architecture.md | 必須 | /architect:design-microservices |
| reports/01_analysis/data-model-analysis.md | 推奨 | /architect:analyze-data-model |

## 利用可能なリソース

- **Context7 MCP** — ScalarDB最新ドキュメント取得（libraryId: /llmstxt/scalardb_scalar-labs_llms-full_txt）
- **research/** — 事前調査資料（16本）

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/03_design/scalardb-schema.md` | テーブル設計、キー戦略 |
| `reports/03_design/scalardb-transaction.md` | トランザクション境界、パターン選択 |
| `reports/03_design/scalardb-migration.md` | データ移行計画 |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /architect:design-microservices | 入力元 |
| /architect:review-scalardb | レビュー対象 |
| /architect:design-api | 関連 |
