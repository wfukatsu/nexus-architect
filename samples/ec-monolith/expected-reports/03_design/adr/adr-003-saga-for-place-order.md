---
id: ADR-003
title: "注文確定は分散トランザクションではなく Saga（イベント駆動の補償）で実現する"
status: accepted
skill: design-microservices
decided_at: "2026-08-29"
upstream: [ADR-001, STM-001, NFR-001, NFR-003]
supersedes: []
schema_version: 1
---

## Context

注文確定は Ordering・Inventory・Payment の 3 コンテキストと外部 PSP を跨ぐ。PSP 呼び出しは秒単位の遅延があり、ScalarDB のトランザクション内に外部 I/O を閉じ込めることはできない。NFR-001（注文 API p95 < 500 ms）と NFR-003（PSP 障害時も注文受付を継続）が同時に成り立つ必要がある。

## Decision

Ordering / Inventory / Payment は ScalarDB Cluster の共有クラスタ構成に載せるが、注文確定フローは one-phase commit で 3 集約を束ねず、`OrderPlaced` → (`StockReserved`, `PaymentCaptured` | `PaymentDeclined`) → `OrderConfirmed` | `OrderCancelled` の Saga とする。補償は `OrderCancelled` を契機に Inventory が release、Payment が refund を行う。各ステップは集約 ID を冪等キーとする。

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| 共有クラスタで Order + StockItem + Payment を 1 トランザクションに載せる | PSP 呼び出しをトランザクション内に含められず、含めなければ決済と注文確定の原子性が崩れる。かつ在庫行のロック保持時間が PSP 遅延に引きずられる |
| Global Transaction API（3.19）で 2PC | 同上。外部 I/O は 2PC でも解決しない。参加サービスが 3 つで、かつ全て ScalarDB なら共有クラスタで足りる |
| ScalarDB Saga（3.19.0-alpha.1）を Saga サーバとして採用 | alpha 版で API・設定キーが動く可能性がある。設計としては同型なので、GA 後に載せ替える判断を STM-001 の補償設計を変えずに行える |

## Consequences

- Order 集約の `confirm` / `cancel` は `consistency: saga`、Payment の全コマンドも `saga`（AGG-001, AGG-004）。
- `design-scalardb` は Saga の各ステップのローカルトランザクションと冪等テーブルを設計する（TX-003〜TX-006）。
- `payment_timeout` を Scheduler 起点のイベントとして STM-001 に持ち、放置された Placed 注文を Cancelled に落とす。
