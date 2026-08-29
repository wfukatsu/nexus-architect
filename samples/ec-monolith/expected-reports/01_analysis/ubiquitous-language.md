---
title: "ユビキタス言語"
schema_version: 1
phase: "Phase 1: Analysis"
skill: analyze
generated_at: "2026-08-29T02:00:00Z"
input_files:
  - reports/before/ec-monolith/codebase-structure.md
  - reports/before/ec-monolith/ddd-readiness.md
  - samples/ec-monolith/src/main/java/com/example/ec/
---

## 概要

`com.example.ec` の 5 パッケージ（order / inventory / payment / catalog / user）と `OrderService.placeOrder()` の処理から抽出した用語集。現行コードは貧血ドメインモデル（D6）でビジネス語彙がサービスクラスの手続きに埋もれているため、各用語について「コード上の現在の名前」と「この用語が属するコンテキスト」を併記する。コンテキスト名は後続の `redesign` が `CTX-001`〜`CTX-006` として確定する候補である。

## 用語集

| Term (EN) | 日本語 | 定義 | Context | Code today |
|-----------|--------|------|---------|------------|
| Order | 注文 | 顧客が商品をまとめて購入する意思表示。明細（OrderLine）の集合と合計金額、ライフサイクル状態を持つ | Ordering | `order.Order`（`status`, `totalAmount`, `items`） |
| OrderLine | 注文明細 | 注文内の 1 商品分の行。商品スナップショット・数量・行番号を持ち、注文の外では意味を持たない | Ordering | `order.OrderItem`（`productId`, `productName`, `quantity`, `unitPrice`） |
| Draft | 下書き | 明細を編集できる、まだ確定していない注文 | Ordering | 存在しない（カートは `placeOrder` の引数 `cartItems` として渡される） |
| Placed | 発注済み | 顧客が確定操作を行い、在庫引当と決済の結果を待っている注文 | Ordering | `OrderStatus.PENDING` |
| Confirmed | 確定 | 決済が完了し、出荷を待つ注文 | Ordering | `OrderStatus.CONFIRMED` |
| Shipped | 出荷済み | 倉庫から発送された注文 | Ordering | `OrderStatus.SHIPPED`（遷移させるコードはない） |
| Delivered | 配達完了 | 配送業者が配達を完了した注文。ポイント付与の契機 | Ordering | `OrderStatus.DELIVERED`（遷移させるコードはない） |
| Cancelled | キャンセル | 顧客・決済拒否・タイムアウトのいずれかで取り消された注文 | Ordering | `OrderStatus.CANCELLED`（決済失敗時のみ設定） |
| Customer | 顧客 | 注文を行う主体。Ordering からは識別子 `customerId` でのみ参照される | Ordering / Identity | `user.User`（`role = CUSTOMER`）。`Order` が `@ManyToOne User` で直接参照 |
| StockItem | 在庫品目 | 1 商品に対する倉庫の在庫記録。手持ち数と引当数を持つ | Inventory | `inventory.Inventory`（`productId` で一意） |
| onHand | 手持ち数 | 倉庫に物理的に存在する数量。出荷（commit）と手動調整（adjust）でのみ変わる | Inventory | `Inventory.quantity` |
| reserved | 引当数 | 未出荷の注文のために確保済みの数量。`onHand - reserved` が販売可能数 | Inventory | `Inventory.reserved`、`getAvailable()` |
| Reservation | 引当 | 「この注文のこの商品」に対する引当の記録。数量は開設時に固定される | Inventory | 存在しない（`InventoryService.reserve(productId, quantity)` は数量のみ加算） |
| Payment | 決済 | 1 注文に対する PSP への課金の記録。金額・カード参照・状態を持つ | Payment | `payment.Payment`（`orderId`, `amount`, `cardLastFour`） |
| Authorize | 与信 | PSP がカードの有効性と与信枠を確認し、金額を確保すること | Payment | 存在しない（`PaymentGateway.charge()` が与信と売上を一度に行う） |
| Capture | 売上確定 | 与信済み金額を実際に請求すること。与信額と同額でなければならない | Payment | `PaymentGateway.charge()` → `PaymentStatus.SUCCESS` |
| Refund | 返金 | 売上確定済みの金額を顧客に戻すこと。注文ごとに高々 1 回 | Payment | `PaymentStatus.REFUNDED`（遷移させるコードはない） |
| IdempotencyKey | 冪等キー | 同じ課金要求の再送を PSP が同一要求と認識するためのキー（orderId + 試行番号） | Payment | 存在しない（再実行すると二重課金する） |
| CardReference | カード参照 | 下 4 桁と PSP トークンのみを保持するカードの参照。PAN は保持しない | Payment | `Payment.cardLastFour`。`charge()` は PAN をログ出力（S4） |
| Product | 商品 | カタログに登録された販売対象。名前・説明・価格・カテゴリ・掲載可否を持つ | Catalog | `catalog.Product` |
| ProductSnapshot | 商品スナップショット | 注文時点の商品 ID・名前・単価の写し。以後の商品変更の影響を受けない | Ordering | `OrderItem.productName` / `unitPrice`（スナップショットの意図はあるが型がない） |
| Money | 金額 | 0 以上・小数なし・通貨 JPY の値 | Ordering / Payment | `BigDecimal`（通貨・スケール制約なし） |
| LoyaltyPoint | ポイント | 配達完了した注文金額 100 円ごとに 1 ポイント顧客に付与される特典 | Identity | `placeOrder()` 内の `totalAmount / 100`（ログ出力のみ、永続化なし） |
| Notification | 通知 | 注文確定・キャンセル・出荷・返金を顧客に知らせるメール | Notification | `OrderService.sendOrderConfirmationEmail()`, `notifyAdmin()` |
| Warehouse operator | 倉庫担当者 | 在庫の手動調整と出荷を行う人 | Inventory / Ordering | 存在しない（`InventoryService.setStock()` は管理 API から呼ばれる） |
| Administrator | 管理者 | ユーザー管理と商品管理を行う人 | Identity / Catalog | `User.Role.ADMIN` |

## コンテキストにより意味が異なる用語

同じ語が別のコンテキストで別の概念を指す。`redesign` はこれらを一つの語に統一せず、各コンテキストの言語として保つ。

| 用語 | Ordering での意味 | Inventory での意味 | Payment での意味 |
|------|-------------------|--------------------|------------------|
| quantity（数量） | 明細 1 行で顧客が購入する個数（`OrderLine.quantity`、1 以上） | 倉庫の手持ち数（`onHand`）または引当の個数（`Reservation.quantity`）。現行コードの `Inventory.quantity` は前者 | — |
| status（状態） | 注文のライフサイクル（Draft → Placed → Confirmed → Shipped → Delivered / Cancelled） | 引当の状態（Pending / Confirmed / Released / Committed） | 決済の状態（Requested / Authorized / Captured / Declined / Refunded） |
| confirm（確定） | 決済完了を受けて注文を Confirmed にする | 注文確定を受けて引当を Pending から Confirmed にする（数量は動かない）。現行の `InventoryService.confirm()` は「出荷＝手持ち減算」であり、目標設計では `commit` に改名する | — |
| amount（金額） | 明細の `unitPrice × quantity` の合計（`totalAmount`） | — | 与信額・売上額・返金額。与信額と売上額は一致しなければならない |
| Customer / User | 注文主の識別子（`customerId`） | — | — （Identity では認証情報・ロール・ポイント残高を持つ `User`） |
| Product | 注文時点のスナップショット（変わらない） | 在庫を持つ `productId`（Catalog の商品を識別子で参照） | — （Catalog では編集可能なマスタ） |

## 現行コードからの改名

| 現行の名前 | 新しい名前 | 理由 |
|------------|------------|------|
| `OrderStatus.PENDING` | Placed | 「保留」は何を待っているか言っていない。顧客が確定操作を終え、在庫引当と決済の結果を待つ状態であることを名前にする |
| `Inventory`（エンティティ） | StockItem | `inventory` は倉庫全体の総称であり 1 商品の記録の名前として不適切。集約ルートは 1 商品分の在庫品目である |
| `Inventory.quantity` | onHand | Ordering の `quantity`（購入個数）と衝突する。手持ち数であることを名前にする |
| `Inventory.getAvailable()` | HasAvailable（仕様） | 派生値ではなく引当可否の判定として、`reserve` と商品ページの在庫表示が共有する仕様にする |
| `InventoryService.reserve(productId, quantity)` | `StockItem.reserve` + `Reservation.open` | 数量だけを加算する現行は再配信で二重引当する。`(orderId, productId)` で識別できる Reservation を持つ |
| `InventoryService.confirm(productId, quantity)` | `StockItem.commit` | 現行の「confirm」は手持ち減算（出荷）を意味し、注文の Confirmed と紛らわしい |
| `InventoryService.setStock()` | `StockItem.adjust` | 「設定」ではなく倉庫担当者による棚卸し調整であり、`new onHand >= reserved` のガードを持つ |
| `OrderItem` | OrderLine | 「item」は Catalog の商品（StockItem の item）と衝突する。注文の中の「行」であることを名前にする |
| `OrderItem.productName` / `unitPrice` | ProductSnapshot（値オブジェクト） | 注文時点の写しであることを型で表す |
| `PaymentGateway.charge()` | `authorize` → `capture` | 与信と売上確定を分けることで、決済拒否（Declined）と金額不一致を別々に扱える |
| `PaymentStatus.SUCCESS` / `FAILED` | Captured / Declined | 成否ではなく決済のどの段階にあるかを名前にする。Requested / Authorized を追加する |
| `placeOrder()` 内の `pointsEarned` | LoyaltyPoint（Identity） | 注文サービスの中でログ出力されるだけの値を Identity の概念に昇格させ、配達完了を契機に付与する |
| `User` | Customer（Ordering 側の参照） | Ordering は認証情報を知る必要がない。`customerId` による識別子参照に置き換える |

## 用語の出典と未確定事項

- 現行コードには Draft / Reservation / Authorize / IdempotencyKey に対応する型がない。これらは `InventoryService.reserve()` と `PaymentGateway.charge()` の再実行で起きる二重引当・二重課金（`ddd-readiness.md`）から必要性が導かれた用語であり、`design-aggregate` が集約の要素として確定する。
- 「Warehouse operator」「Carrier（配送業者）」は現行コードにアクターとして現れない。出荷・配達の遷移が実装されていないためで、`actors-roles-permissions.md` で候補として記録する。
