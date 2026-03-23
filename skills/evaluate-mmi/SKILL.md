---
name: evaluate-mmi
description: |
  モジュラリティ成熟度指標（MMI）を4軸で定性評価する。凝集度、結合度、独立性、再利用性。
  /architect:evaluate-mmi [target_path] で呼び出し。
  analyze-system の出力を前提条件とする。evaluate-ddd と並行実行可能。
model: sonnet
user_invocable: true
---

# MMI評価

## 達成すべき結果

対象システムの各モジュールをMMI 4軸で評価し、マイクロサービス化の準備度を判定する。

## 判断基準

評価の詳細な基準とスコアリングアルゴリズムは以下を参照:
@rules/evaluation-frameworks.md

- 4軸: 凝集度(30%), 結合度(30%), 独立性(20%), 再利用性(20%)
- 各軸1-5スコア
- MMI = (0.3×C + 0.3×K + 0.2×I + 0.2×R) / 5 × 100
- 成熟度: 80-100(準備完了), 60-80(中程度), 40-60(要改善), 0-40(未成熟)

## 前提条件

| ファイル | 必須/推奨 | 生成元 |
|---------|----------|--------|
| reports/01_analysis/ | 必須 | /architect:analyze |

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/02_evaluation/mmi-overview.md` | 全体MMIスコア、成熟度判定、改善優先度 |
| `reports/02_evaluation/mmi-by-module.md` | モジュール別4軸スコア詳細 |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /architect:analyze | 入力元 |
| /architect:evaluate-ddd | 並行実行 |
| /architect:integrate-evaluations | 出力先 |
