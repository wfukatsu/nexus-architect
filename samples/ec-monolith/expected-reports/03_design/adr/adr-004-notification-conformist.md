---
id: ADR-004
title: "通知（Notification）と ポイント（Identity）は Ordering のイベントに Conformist で追従する"
status: accepted
skill: design-microservices
decided_at: "2026-08-29"
upstream: [ADR-003, CTX-001, CTX-005]
supersedes: []
schema_version: 1
---

## Context

現行の `placeOrder()` はメール送信とポイント付与を同期で実行し、SMTP 障害が注文確定を失敗させる（D1）。どちらも注文の業務ルールを変えない副作用であり、Ordering 側の言語を変えてまで合意すべき契約はない。

## Decision

Notification と Identity（ポイント）は `OrderConfirmed` / `OrderCancelled` / `OrderShipped` / `PaymentRefunded` / `OrderDelivered` を Conformist として購読する。Ordering は両者の存在を知らず、イベントのペイロードは Ordering の都合で additive-only に進化する。ポイント付与は `OrderDelivered` を契機にする（配達前キャンセルで付与取消が要らない）。

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Ordering から同期 REST で通知・ポイント API を呼ぶ | SMTP / ポイント API の障害が注文確定に波及する（現行の欠陥をそのまま持ち込む） |
| Notification 向けに Open Host Service を別途定義する | 購読者が 1 つしかない段階で公開契約を切るのは過剰。購読者が増えた時点で OHS/PL に昇格させる |
| `OrderConfirmed` でポイント付与し、キャンセル時に取消 | 取消経路が増え、ポイント残高の不変条件が Ordering の状態に依存する |

## Consequences

- ドメインイベントカタログの Notification / Identity 行は `relationship: conformist`。
- 通知・ポイントの遅延は NFR ではなく運用指標（`design-observability`）で扱う。
