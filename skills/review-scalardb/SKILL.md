---
name: review-scalardb
description: |
  ScalarDB固有の制約（2PCスコープ、OCC競合、スキーマ互換性）をレビューする。
  ScalarDB利用プロジェクト専用。並列レビューシステムの一視点。
model: sonnet
user_invocable: true
---

# ScalarDB制約レビュー

## レビュー次元

### 1. 2PCスコープ準拠 (weight: 0.40)
- 2PCトランザクションが最大2-3サービスに収まるか
- 4+サービスにまたがるトランザクションの検出
- Sagaパターンの適用箇所

### 2. OCC競合分析 (weight: 0.35)
- 書き込みホットスポットの識別
- OCC競合率5%未満を達成できる設計か
- 競合緩和策（パーティショニング、CQRS等）

### 3. スキーマ・API互換性 (weight: 0.25)
- パーティション/クラスタリングキー設計の妥当性
- セカンダリインデックスの必要性と性能影響
- ScalarDB v3.17+制約の遵守

## 出力形式

JSON（review-consistency と同一スキーマ）。Finding IDプレフィックス: **SDB-**
