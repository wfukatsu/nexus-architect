---
name: integrate-evaluations
description: |
  MMI評価とDDD評価の結果を統合し、優先度付き改善計画を策定する。
  /integrate-evaluations で呼び出し。
model: sonnet
user_invocable: true
---

# 評価統合

## 達成すべき結果

MMIとDDDの評価結果を統合し、マイクロサービス化に向けた統一的な改善計画を策定する。

## 判断基準

- 両評価で共通して低スコアの領域を最優先改善対象とする
- 改善項目はビジネスインパクトと技術的実現性の両面で優先度付けする
- 短期（クイックウイン）と中長期（構造改善）に分類する

## 前提条件

| ファイル | 必須/推奨 | 生成元 |
|---------|----------|--------|
| reports/02_evaluation/mmi-overview.md | 必須 | /evaluate-mmi |
| reports/02_evaluation/ddd-strategic-evaluation.md | 必須 | /evaluate-ddd |

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/02_evaluation/integrated-evaluation.md` | 統合評価結果 |
| `reports/02_evaluation/unified-improvement-plan.md` | 優先度付き改善計画 |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /evaluate-mmi | 入力元 |
| /evaluate-ddd | 入力元 |
| /ddd-redesign | 出力先 |
