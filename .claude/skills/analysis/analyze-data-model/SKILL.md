---
name: analyze-data-model
description: |
  データモデル分析、DB設計分析、ER図生成を統合的に行う。
  /analyze-data-model [target_path] で呼び出し。
  analyze-system の出力を前提条件とする。
model: sonnet
user_invocable: true
---

# データモデル分析

## 達成すべき結果

対象システムのデータ層を包括的に分析し、以下を生成する:
1. **データモデル分析** — エンティティ、リレーションシップ、ドメインルール、正規化状態
2. **ER図（現状）** — Mermaid erDiagram 形式の現行ER図

## 判断基準

- エンティティの識別はドメイン用語と照合する
- 正規化の逸脱がある場合、意図的なものか問題かを判断する
- インデックス設計の妥当性を評価する
- データ整合性制約（FK、UNIQUE、CHECK）の網羅性を確認する

## 前提条件

| ファイル | 必須/推奨 | 生成元 |
|---------|----------|--------|
| reports/01_analysis/ | 推奨 | /analyze-system |

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/01_analysis/data-model-analysis.md` | エンティティ一覧、リレーション、正規化評価、インデックス分析 |
| `reports/01_analysis/er-diagram-current.md` | Mermaid ER図 |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /analyze-system | 入力元 |
| /ddd-redesign | 出力先 |
| /design-scalardb | 出力先 |
