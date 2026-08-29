---
id: ADR-001
title: "在庫（Inventory）を Ordering から独立した境界づけられたコンテキストにする"
status: accepted
skill: redesign
decided_at: "2026-08-29"
upstream: [CTX-002, CTX-003, NFR-002]
supersedes: []
schema_version: 1
---

## Context

現行の `OrderService.placeOrder()` は在庫引当・決済・メール送信・ポイント付与を 1 メソッドで直接呼び出す God Service（技術負債 D1）であり、`order` ↔ `inventory` は相互 import している（D4）。在庫の整合性（reserved ≤ onHand）は注文とは独立に守るべき不変条件で、倉庫の手動調整（adjust）は注文を経由しない。NFR-002（在庫の過剰引当ゼロ）は注文フローの外でも守られなければならない。

## Decision

Inventory を独自のユビキタス言語（StockItem / Reservation / onHand / reserved）を持つ境界づけられたコンテキストとして切り出し、Ordering とは `OrderPlaced` / `OrderCancelled` / `OrderShipped` イベントによる Customer/Supplier 関係で結ぶ。Ordering は在庫数量を保持せず、`StockReserved` を受けて行を「引当済み」とマークするだけにする。

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Ordering の集約内に在庫数量を持つ（現行の直接呼び出しを保つ） | 倉庫の手動調整と注文が同一集約を奪い合い、OCC 競合率が注文量に比例する。NFR-002 を注文以外の経路で守れない |
| Shared Kernel として在庫テーブルを共有 | 二つのチーム／サービスが同一スキーマを書き換える。分離の意味がない |
| Inventory を Catalog の一部にする | 商品マスタ（変更頻度: 低・読み中心）と在庫（変更頻度: 高・書き中心）は一貫性クラスが異なる |

## Consequences

- `design-aggregate` は StockItem と Reservation を Inventory 側の集約として設計する（ADR-002）。
- `design-microservices` は Ordering → Inventory のイベント経路と、`StockReserved` の返送を定義する。
- 注文確定は在庫引当を同期で待たず、Placed 状態で引当完了を待つ（STM-001 の `defer:awaiting-reservation`）。
