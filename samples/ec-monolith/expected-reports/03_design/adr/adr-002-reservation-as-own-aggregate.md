---
id: ADR-002
title: "引当（Reservation）を StockItem とは別集約にし、同一トランザクションで書く"
status: accepted
skill: redesign
decided_at: "2026-08-29"
upstream: [ADR-001, CTX-002, NFR-002]
supersedes: []
schema_version: 1
---

## Context

`OrderPlaced` は at-least-once で配信されるため、同じ注文の引当要求が二度届く。現行実装の `inventoryService.reserve(productId, quantity)` は数量だけを受け取り、再配信で二重引当する（技術負債）。引当を冪等にするには「この注文のこの商品の引当」を識別できる行が要る。

## Decision

`Reservation`（identity = orderId + productId）を StockItem とは別のルートを持つ集約とし、`StockItem.reserve` / `release` / `commit` が `also_writes: ["Reservation"]` で同一ローカルトランザクション内に書く。イベントは StockItem のみが発行し、Reservation のコマンドは `none` を返す。Reservation は数量を開設時に固定し、release / commit は数量引数を持たない。

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| StockItem の内部エンティティとして reservations リストを持つ | 1 商品の全引当が 1 集約に載り、人気商品では集約が肥大化して OCC 競合が集中する |
| Reservation を Ordering 側に置く | 在庫の不変条件（INV-2: reserved = 引当合計）を跨コンテキストでしか検証できない |
| 引当行を持たず、注文 ID をキーにした冪等テーブルだけ置く | 引当数量の解放時に数量をもう一度伝える必要があり、再配信で二重解放する |

## Consequences

- この決定の集約側の実体は `design-aggregate` が後から採番する AGG-002（StockItem）と AGG-003（Reservation）であり、両ノードの `upstream` がこの ADR を指す（ADR が集約を指すのではない — 採番順序の都合）。

- `rules/aggregate-design.md` §4 の第 3 ケース（`local` + `also_writes`）を適用する。二集約・一トランザクションの唯一の例外であり、`scalardb-transaction.md` TX-002 に記録する。
- `design-scalardb` は StockItem と Reservation を同一パーティションキー（productId）に置く。
