---
name: review-consistency
description: |
  設計ドキュメントの構造的一貫性、トレーサビリティ、用語統一をレビューする。
  並列レビューシステムの一視点として使用。
model: sonnet
user_invocable: true
---

# 一貫性レビュー

## 達成すべき結果

設計ドキュメント群の構造的な一貫性を検証し、JSON形式で指摘事項を出力する。

## レビュー次元

### 1. 構造的整合性 (weight: 0.35)
- ドキュメント間の構造・見出しレベルの一貫性
- 孤立セクションや参照切れの検出
- 階層構造の論理性

### 2. トレーサビリティ (weight: 0.35)
- 要件→設計→実装の追跡可能性
- 前方・後方参照の存在
- ギャップの文書化有無

### 3. 用語統一 (weight: 0.30)
- ユビキタス言語の一貫使用
- 同一概念への異なる名称の検出
- 略語の初出時定義と一貫使用

## スコアリング

各次元1-5スコア（5:模範的、4:良好、3:許容可、2:懸念あり、1:重大問題）

## 出力形式

```json
{
  "perspective": "consistency",
  "reviewer": "review-consistency",
  "timestamp": "ISO-8601",
  "dimensions": [
    {
      "name": "Structural Coherence",
      "weight": 0.35,
      "score": 4,
      "findings": [
        {
          "id": "CON-001",
          "severity": "critical|major|minor|info",
          "location": "file:section",
          "title": "指摘タイトル",
          "description": "問題の説明と影響",
          "recommendation": "具体的な修正案"
        }
      ]
    }
  ],
  "weighted_score": 3.8,
  "summary": "レビューサマリー"
}
```

Finding IDプレフィックス: **CON-**
