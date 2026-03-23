---
name: select-scalardb-edition
description: |
  対話形式で最適なScalarDBエディション（OSS/Enterprise Standard/Premium）を選定する。
  /select-scalardb-edition で呼び出し。
model: sonnet
user_invocable: true
---

# ScalarDBエディション選定

## 達成すべき結果

プロジェクト要件に基づき、最適なScalarDBエディションとデプロイモードを選定する。

## 判断基準

AskUserQuestion で以下を段階的に確認:
1. マルチDB分散トランザクションの必要性
2. SQLインターフェースの要否
3. 分析クエリ（HTAP）の要否
4. SLA要件（99.9% vs 99.99%）
5. サポートレベル要件

エディション比較: @rules/scalardb-edition-profiles.md

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/03_design/scalardb-edition-selection.md` | 選定結果と根拠 |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /architect:design-scalardb | 出力先（エディション情報を入力として使用） |
