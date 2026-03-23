---
name: design-scalardb-analytics
description: |
  ScalarDB Analyticsを使用したHTAP分析基盤を設計する。Apache Sparkベースの分析クエリ設計。
  /design-scalardb-analytics で呼び出し。Enterprise Premium専用。
model: sonnet
user_invocable: true
---

# ScalarDB Analytics設計

## 達成すべき結果

- HTAP（Hybrid Transactional/Analytical Processing）アーキテクチャ設計
- Apache Spark統合設定
- 異種DB横断の分析クエリ設計
- データカタログ（論理-物理マッピング）
- タイムライン一貫性読み取り設定

## 前提条件

| ファイル | 必須/推奨 | 生成元 |
|---------|----------|--------|
| reports/03_design/scalardb-schema.md | 必須 | /design-scalardb |

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/03_design/scalardb-analytics-design.md` | Analytics全体設計 |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /design-scalardb | 入力元 |
