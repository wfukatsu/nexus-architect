---
title: "境界づけられたコンテキストの再設計"
schema_version: 1
phase: "Phase 3: Design"
skill: redesign
generated_at: "2026-08-29T02:00:00Z"
input_files:
  - reports/02_evaluation/unified-improvement-plan.md
  - reports/01_analysis/ubiquitous-language.md
  - reports/03_design/adr/adr-001-inventory-split-from-ordering.md
  - reports/03_design/adr/adr-002-reservation-as-own-aggregate.md
---

## 概要

現行の 5 パッケージ（order / inventory / payment / catalog / user）を、`OrderService.placeOrder()` に埋め込まれた副作用（メール送信・ポイント付与）を分離したうえで 6 つの境界づけられたコンテキストに再編する。各コンテキストを Bounded Context Canvas（9 項目）で記述し、境界の判断のうち代替案があったものは ADR に記録している。コンテキスト間の関係の全体像は `context-map.md`。

| ID | Name | 分類 | 現行パッケージ | 主な変更 |
|----|------|------|----------------|----------|
| CTX-001 | Ordering | Core | `order` | 在庫・決済・通知・ポイントの直接呼び出しを除去し、イベント発行に置き換える |
| CTX-002 | Inventory | Core | `inventory` | Ordering から独立（ADR-001）。Reservation を追加（ADR-002） |
| CTX-003 | Payment | Supporting | `payment` | 与信と売上確定を分離し、冪等キーを導入 |
| CTX-004 | Catalog | Supporting | `catalog` | 変更なし。在庫表示を `StockAdjusted` からの読み取りモデルにする |
| CTX-005 | Identity | Generic | `user` | 認証・ロールに加え、ポイント付与を引き受ける（ADR-004） |
| CTX-006 | Notification | Generic | `OrderService` 内のメール送信 | 新設。Ordering / Payment のイベントに追従（ADR-004） |

## CTX-001 Ordering（注文）

| Part | Content |
|------|---------|
| **Name** | CTX-001 Ordering — 注文 |
| **Purpose** | 顧客の購入意思を Order として受け付け、そのライフサイクル（Draft → Placed → Confirmed → Shipped → Delivered / Cancelled）を管理する。在庫の数量、決済の可否、通知の送達には責任を持たない。それらの結果を受けて注文の状態を決めるだけである |
| **Strategic classification** | Core。売上を生む唯一の経路（revenue）。evolution: custom |
| **Domain roles** | execution（注文の状態遷移を実行する）、draft（Draft 状態の明細編集） |
| **Inbound communication** | Customer → `place` / `addLine` / `removeLine` / `cancel`（コマンド、API Gateway 経由）。Warehouse operator → `ship`。Carrier webhook → `deliver`。Inventory → `StockReserved`（Customer/Supplier、Ordering が customer）。Payment → `PaymentCaptured` / `PaymentDeclined`（Customer/Supplier、Ordering が customer） |
| **Outbound communication** | `OrderPlaced` → Inventory, Payment（Customer/Supplier、Ordering が supplier）。`OrderConfirmed` / `OrderCancelled` / `OrderShipped` → Inventory（Customer/Supplier）と Notification（Conformist）。`OrderDelivered` → Identity（Conformist）。同期呼び出しは行わない |
| **Ubiquitous language** | Order, OrderLine, ProductSnapshot, Placed（旧 PENDING）, Confirmed, CanBeShipped, totalAmount, customerId（識別子参照のみ） |
| **Business decisions** | INV-1 合計金額 = 明細の単価 × 数量の和。INV-2 Draft を出た注文は明細を 1 行以上持つ。INV-3 Placed 以降は明細を凍結する。INV-4 Confirmed は成功した決済をちょうど 1 つ参照する。出荷は全明細が引当済みのときに限る（CanBeShipped）。放置された Placed は `payment_timeout` で Cancelled にする（ADR-003） |
| **Assumptions and open questions** | 在庫引当を同期で待たず Placed で待つ前提（ADR-001）。OQ-003: Confirmed 後・出荷前のキャンセルを顧客に許すか、オペレータ限定か。OQ-004: `payment_timeout` の時間（候補: 15 分 / 1 時間 / 24 時間） |

## CTX-002 Inventory（在庫）

| Part | Content |
|------|---------|
| **Name** | CTX-002 Inventory — 在庫 |
| **Purpose** | 商品ごとの手持ち数（onHand）と引当数（reserved）を管理し、過剰引当を防ぐ。注文が誰のものか、いくらかは知らない。倉庫担当者による棚卸し調整は注文を経由しない |
| **Strategic classification** | Core。過剰引当ゼロ（NFR-002）は顧客体験と信用に直結する。evolution: custom |
| **Domain roles** | execution（引当・解放・確定）、specification（HasAvailable） |
| **Inbound communication** | Ordering → `OrderPlaced`（reserve）/ `OrderConfirmed`（confirmReservation）/ `OrderCancelled`（release）/ `OrderShipped`（commit）— Customer/Supplier、Inventory が supplier。Catalog → `ProductRegistered`（register）。Warehouse operator → `adjust`（コマンド） |
| **Outbound communication** | `StockReserved` → Ordering（Customer/Supplier）。`StockAdjusted` → Catalog（Open Host Service: 在庫表示の読み取りモデル向けに公開） |
| **Ubiquitous language** | StockItem（旧 `Inventory`）, onHand（旧 `quantity`）, reserved, Reservation, HasAvailable, commit（旧 `confirm`）, adjust（旧 `setStock`） |
| **Business decisions** | StockItem INV-1 reserved は onHand を超えない。INV-2 reserved は Pending / Confirmed な引当の数量の和に等しい。Reservation INV-1 (orderId, productId) ごとに高々 1 件（再配信で二重引当しない）。INV-2 数量は開設時に固定 |
| **Assumptions and open questions** | StockItem と Reservation は同一ローカルトランザクションで書く（ADR-002）。OQ-005: 引当の有効期限（Placed の `payment_timeout` と同じ値にするか） |

## CTX-003 Payment（決済）

| Part | Content |
|------|---------|
| **Name** | CTX-003 Payment — 決済 |
| **Purpose** | 注文 1 件の代金を外部 PSP で与信し、売上確定し、必要なら返金する。カード番号（PAN）は保持せず、PSP への呼び出しを冪等にする。注文の内容や在庫は知らない |
| **Strategic classification** | Supporting。PSP が本体で、当コンテキストはその境界（compliance: PCI DSS）。evolution: product |
| **Domain roles** | gateway（PSP との境界）、execution |
| **Inbound communication** | Ordering → `OrderPlaced`（authorize）/ `OrderCancelled`（refund）— Customer/Supplier、Payment が supplier。PSP → 与信・売上・拒否の応答（Anticorruption Layer 経由で `capture` / `decline` に変換） |
| **Outbound communication** | `PaymentCaptured` / `PaymentDeclined` → Ordering（Customer/Supplier）。`PaymentRefunded` → Notification（Conformist） |
| **Ubiquitous language** | Payment, Authorize, Capture, Refund, Declined, IdempotencyKey, CardReference, Money |
| **Business decisions** | INV-1 orderId ごとに Captured な決済は高々 1 つ。INV-2 売上額は与信額と等しい。INV-3 返金は売上額を超えず高々 1 回。PSP への呼び出しは全て IdempotencyKey を伴う |
| **Assumptions and open questions** | 与信→売上確定の二段階を PSP が提供する前提。OQ-006: 部分返金（返品 1 行分）を将来サポートするか — 現時点では INV-3 で全額 1 回に限定 |

## CTX-004 Catalog（商品カタログ）

| Part | Content |
|------|---------|
| **Name** | CTX-004 Catalog — 商品カタログ |
| **Purpose** | 販売対象の商品（名前・説明・価格・カテゴリ・掲載可否）を管理し、商品ページの検索と表示を提供する。在庫数は持たず、Inventory から公開された手持ち数を読み取りモデルとして表示する |
| **Strategic classification** | Supporting（engagement）。evolution: product |
| **Domain roles** | specification（商品マスタ）、analysis（検索・表示の読み取りモデル） |
| **Inbound communication** | Administrator → 商品の登録・更新・掲載切替（コマンド）。Customer → 検索・閲覧（クエリ）。Inventory → `StockAdjusted`（Open Host Service を購読） |
| **Outbound communication** | `ProductRegistered` → Inventory（StockItem の register）。Ordering は注文時に商品情報を ProductSnapshot として写す（クエリ、同期） |
| **Ubiquitous language** | Product, price, category, active, availability（表示用の派生値。Inventory の onHand とは別物） |
| **Business decisions** | 価格は 0 以上。掲載停止（active = false）の商品は検索に出ないが、既存注文のスナップショットには影響しない |
| **Assumptions and open questions** | 検索は native query（S1: SQL インジェクション）を廃し、パラメータ化する。OQ-007: 商品ページの在庫表示を「在庫あり / 残りわずか / 在庫なし」の 3 段階にするか数量にするか |

## CTX-005 Identity（認証・顧客）

| Part | Content |
|------|---------|
| **Name** | CTX-005 Identity — 認証・顧客 |
| **Purpose** | ユーザーの登録・認証・ロール（CUSTOMER / ADMIN）と、顧客のポイント残高を管理する。注文の内容は知らず、`OrderDelivered` の金額からポイントを計算するだけである |
| **Strategic classification** | Generic（認証は買い物のどの製品にもある）。ポイントは engagement。evolution: commodity（認証）/ product（ポイント） |
| **Domain roles** | gateway（認証）、execution（ポイント付与） |
| **Inbound communication** | Customer → 登録・ログイン（コマンド）。Ordering → `OrderDelivered`（Conformist: Identity が Ordering のイベント形式にそのまま従う、ADR-004） |
| **Outbound communication** | API Gateway へ認証結果（principal, role）。ドメインイベントは公開しない |
| **Ubiquitous language** | User, Customer, Role, LoyaltyPoint, passwordHash（BCrypt。MD5 は廃止: S3） |
| **Business decisions** | ポイントは配達完了した注文金額 100 円ごとに 1 ポイント（現行 `totalAmount / 100` を踏襲）。付与は `OrderDelivered` を契機とし、配達前のキャンセルでは付与も取消も発生しない（ADR-004） |
| **Assumptions and open questions** | `OrderDelivered` のペイロードに `totalAmount` が含まれる（OQ-008: Identity が Ordering に金額を照会するか、ペイロードに載せるか — additive-only 進化としてペイロードに載せる方を採用、answered）。ポイントは配達後に付与し、取消経路を持たない（ADR-004） |

## CTX-006 Notification（通知）

| Part | Content |
|------|---------|
| **Name** | CTX-006 Notification — 通知 |
| **Purpose** | 注文確定・キャンセル・出荷・返金を顧客にメールで知らせる。送達の失敗は注文にも決済にも影響させない |
| **Strategic classification** | Generic（cost reduction: SMTP 障害と注文確定の切り離し）。evolution: commodity |
| **Domain roles** | gateway（SMTP / メール配信サービスとの境界） |
| **Inbound communication** | Ordering → `OrderConfirmed` / `OrderCancelled` / `OrderShipped`、Payment → `PaymentRefunded`。いずれも Conformist（ADR-004） |
| **Outbound communication** | メール配信サービスへの送信要求のみ。ドメインイベントは公開しない |
| **Ubiquitous language** | Notification, template, recipient, delivery attempt |
| **Business decisions** | 同一イベントの再配信で同じメールを二度送らない（イベントの `idempotency_key` = orderId / paymentId で送信記録を持つ） |
| **Assumptions and open questions** | 宛先メールアドレスは Identity に照会する前提。OQ-009: 管理者向け通知（現行 `notifyAdmin()`）を残すか |

## 集約一覧

Canvas がコンテキストの契約であるのに対し、集約はその内部である。詳細は `aggregates/aggregate-manifest.json` と各集約文書。

| Context | Aggregate | ID | Root | 主な不変条件 | 状態機械 |
|---------|-----------|----|------|--------------|----------|
| CTX-001 Ordering | Order | AGG-001 | Order（OrderLine, Money, ProductSnapshot を内包） | 合計金額整合、明細 1 行以上、Placed 以降は明細凍結、Confirmed は決済をちょうど 1 つ参照 | STM-001 |
| CTX-002 Inventory | StockItem | AGG-002 | StockItem（Quantity を内包） | reserved ≤ onHand、reserved = 有効な引当の和 | — |
| CTX-002 Inventory | Reservation | AGG-003 | Reservation（identity = orderId + productId） | (orderId, productId) ごとに高々 1 件、数量は開設時に固定 | — |
| CTX-003 Payment | Payment | AGG-004 | Payment（Money, CardReference, IdempotencyKey を内包） | orderId ごとに Captured は高々 1 つ、売上額 = 与信額、返金は 1 回まで | — |

CTX-004 Catalog（Product）、CTX-005 Identity（User）、CTX-006 Notification は現時点では集約を設計していない。Product と User は不変条件が単一エンティティに閉じるため、`design-aggregate` の対象外（エンティティ + リポジトリで足りる）と判断した。

## 現行コードとの差分

| 現行 | 目標 | 根拠 |
|------|------|------|
| `OrderService.placeOrder()` が在庫・決済・メール・ポイントを同期呼び出し（D1） | Ordering は `OrderPlaced` を発行するだけ。以降は Saga | ADR-001, ADR-003, ADR-004 |
| `order` ↔ `inventory` の相互 import（D4） | イベント経由の Customer/Supplier。Ordering は在庫数量を持たない | ADR-001 |
| `InventoryService.reserve(productId, quantity)` が数量のみ加算 | StockItem + Reservation を同一トランザクションで書く | ADR-002 |
| `Order` が `User` エンティティを直接参照 | `customerId` による識別子参照 | rules/aggregate-design.md §3 |
| メール送信・ポイント付与が `placeOrder()` 内 | Notification / Identity が Conformist で追従 | ADR-004 |
