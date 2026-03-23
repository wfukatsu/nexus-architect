---
name: evaluate-ddd
description: |
  DDD原則への適合度を戦略・戦術・アーキテクチャの3レイヤー12基準で評価する。
  /architect:evaluate-ddd [target_path] で呼び出し。
  analyze-system の出力を前提条件とする。evaluate-mmi と並行実行可能。
model: sonnet
user_invocable: true
---

# DDD評価

## 達成すべき結果

対象システムのDDD原則への適合度を3レイヤー12基準で定量評価する。

## 判断基準

評価の詳細な基準は以下を参照:
@.claude/rules/evaluation-frameworks.md

- 戦略的設計(30%): ユビキタス言語、境界コンテキスト、サブドメイン分類
- 戦術的設計(45%): 値オブジェクト、エンティティ、集約、リポジトリ、ドメインサービス、ドメインイベント
- アーキテクチャ(25%): レイヤリング、依存方向、ポート&アダプター

## 前提条件

| ファイル | 必須/推奨 | 生成元 |
|---------|----------|--------|
| reports/01_analysis/ | 必須 | /architect:analyze |

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/02_evaluation/ddd-strategic-evaluation.md` | 戦略的設計評価 |
| `reports/02_evaluation/ddd-tactical-evaluation.md` | 戦術的設計 + アーキテクチャ評価 |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /architect:analyze | 入力元 |
| /architect:evaluate-mmi | 並行実行 |
| /architect:integrate-evaluations | 出力先 |
