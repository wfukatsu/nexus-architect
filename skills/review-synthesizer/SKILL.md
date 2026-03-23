---
name: review-synthesizer
description: |
  並列レビュー結果を統合する。重複排除、優先度分類、品質ゲート判定を行う。
  2-5視点の可変入力数に対応。
model: sonnet
user_invocable: true
---

# レビュー統合

## 達成すべき結果

複数のレビュー視点からのJSON出力を受け取り、統合レビューレポートを生成する。

## Step 1: 重複排除

複数のレビューアが同じ根本原因の問題を異なる角度から指摘することがある。

- **同一ロケーション + 同一根本原因** → 1つに統合、全視点IDを記録（例: "CON-003, BIZ-007"）
- **同一根本原因 + 異なるロケーション** → 個別維持、`related_to` でリンク
- **異なる根本原因 + 同一ロケーション** → 個別維持
- 統合時は最も高い重大度を採用
- 推奨事項を1つの具体的なアクションに統合

## Step 2: 優先度分類

| 優先度 | 条件 |
|--------|------|
| **P0 - ブロッカー** | critical重大度、データ損失・セキュリティ侵害・システム障害を引き起こす |
| **P1 - 要修正** | 2+視点からのmajor、riskまたはscalardb視点のmajor |
| **P2 - 推奨修正** | 1視点のみのmajor、3+視点に共通するminor |
| **P3 - 検討** | minor/info重大度 |

## Step 3: 品質ゲート判定

`review-registry.json` の閾値に基づき判定:

- **PASS**: aggregate >= 3.5、critical: 0、major <= 3、全視点 >= 3.0
- **CONDITIONAL PASS**: aggregate >= 2.5、critical <= 2（緩和策あり）、major <= 8
- **FAIL**: 上記未満

## Step 4: レポート生成

### JSON出力 (`reports/review/review-synthesis.json`)

```json
{
  "review_id": "uuid",
  "verdict": "PASS|CONDITIONAL_PASS|FAIL",
  "aggregate_score": 3.8,
  "perspective_scores": {},
  "findings_summary": {"total": 0, "after_dedup": 0, "by_priority": {}, "by_severity": {}},
  "findings": [{"id": "SYN-001", "priority": "P1", "source_ids": [], "perspectives": []}],
  "conditional_items": []
}
```

### Markdown出力 (`reports/review/review-synthesis.md`)

見出し: Verdict → Score Summary → P0 Blockers → P1 Must Fix → P2 Should Fix → P3 Consider

## 可変入力対応

2-5視点のいずれの組み合わせでも動作する。
`review-registry.json` から有効化された視点の重みを読み込み、正規化して集計する。
