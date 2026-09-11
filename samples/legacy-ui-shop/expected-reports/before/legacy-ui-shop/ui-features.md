---
title: "UI 機能とタスク — legacy-ui-shop"
schema_version: 1
phase: "Phase 1: Investigation"
skill: analyze-ui
generated_at: "2026-09-11T02:56:47Z"
input_files:
  - reports/before/legacy-ui-shop/ui-inventory.json
  - reports/before/legacy-ui-shop/ui-design-tokens.json
---

## 機能一覧（Feature List）

| ID | 名前 | コマンド | 画面 | アクター | エンティティ |
|---|---|---|---|---|---|
| UIF-001 | ログインする | `LogIn` | UIS-001 | anonymous | User |
| UIF-002 | ログアウトする | `LogOut` | UIS-002, UIS-003, UIS-004, UIS-005, UIS-006, UIS-007, UIS-009, UIS-010 | admin, customer | Cart |
| UIF-003 | 商品を検索する | `SearchProducts` | UIS-003 | admin, customer | Product |
| UIF-004 | カートに商品を追加する | `AddToCart` | UIS-003, UIS-004 | admin, customer | Cart, Product |
| UIF-005 | カートから商品を削除する | `RemoveCartLine` | UIS-005 | admin, customer | Cart |
| UIF-006 | 注文情報（お届け先・支払い方法）を入力する | `EnterOrderDetails` | UIS-006 | admin, customer | Cart, OrderForm |
| UIF-007 | 注文を確定する | `PlaceOrder` | UIS-007 | admin, customer | Cart, Order, OrderForm, User |
| UIF-008 | 商品を登録・更新する | `SaveProduct` | UIS-009 | admin | Product |
| UIF-009 | 商品を削除する | `DeleteProduct` | UIS-009 | admin | Product |

## タスク（Tasks）

| 名前 | 目的 | 経路 | ステップ | 入力 | 必須入力 |
|---|---|---|---|---|---|
| ログインする | 認証してメニューに到達する | UIS-001 → UIS-002 | 2 | 2 | 2 |
| 商品を探してカートに入れる | 欲しい商品を見つけ、数量を指定してカートに入れる | UIS-002 → UIS-003 → UIS-004 → UIS-005 | 4 | 3 | 0 |
| カートの中身を整理する | 不要になった商品をカートから外す | UIS-005 | 1 | 0 | 0 |
| 注文する（チェックアウト） | カートの商品をお届け先・支払い方法を指定して注文する | UIS-005 → UIS-006 → UIS-007 → UIS-008 | 4 | 7 | 6 |
| 商品を登録・更新する | 管理者が商品名・価格・在庫・カテゴリを登録または変更する | UIS-009 | 1 | 4 | 4 |
| 商品を削除する | 管理者が商品を取り扱いから外す | UIS-009 | 1 | 0 | 0 |
| 利用を終了する | ログアウトしてセッションを終える | UIS-002 → UIS-001 | 2 | 0 | 0 |

## アクター × 機能（Actor × Feature）

| アクター | UIF-001 | UIF-002 | UIF-003 | UIF-004 | UIF-005 | UIF-006 | UIF-007 | UIF-008 | UIF-009 |
|---|---|---|---|---|---|---|---|---|---|
| admin | - | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| anonymous | ✓ | - | - | - | - | - | - | - | - |
| customer | - | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | - | - |

## 機能 × エンティティ（Feature × Entity）

| ID | 機能 | エンティティ | CRUD |
|---|---|---|---|
| UIF-001 | ログインする | User | R |
| UIF-002 | ログアウトする | Cart | D |
| UIF-003 | 商品を検索する | Product | R |
| UIF-004 | カートに商品を追加する | Cart | CU |
| UIF-004 | カートに商品を追加する | Product | R |
| UIF-005 | カートから商品を削除する | Cart | U |
| UIF-006 | 注文情報（お届け先・支払い方法）を入力する | Cart | R |
| UIF-006 | 注文情報（お届け先・支払い方法）を入力する | OrderForm | C |
| UIF-007 | 注文を確定する | Cart | RD |
| UIF-007 | 注文を確定する | Order | C |
| UIF-007 | 注文を確定する | OrderForm | RD |
| UIF-007 | 注文を確定する | User | R |
| UIF-008 | 商品を登録・更新する | Product | CU |
| UIF-009 | 商品を削除する | Product | D |

## 受入基準候補としての検証ルール（Validation Rules as Acceptance-Criteria Candidates）

| 機能 | 入力 | ルール | 実施場所 |
|---|---|---|---|
| UIF-001 | ユーザーID | required=True | server |
| UIF-001 | パスワード | required=True | server |
| UIF-004 | 数量 | min=1 | both |
| UIF-004 | 数量 | max=99 | both |
| UIF-006 | お届け先氏名 | required | server |
| UIF-006 | 郵便番号 | required | server |
| UIF-006 | 郵便番号 | pattern=^\d{3}-\d{4}$ | client — クライアントのみ — サーバーは受け付けてしまう |
| UIF-006 | 郵便番号 | maxLength=8 | client — クライアントのみ — サーバーは受け付けてしまう |
| UIF-006 | 住所 | required | server |
| UIF-006 | 電話番号 | required | server |
| UIF-006 | メールアドレス | required | server |
| UIF-006 | メールアドレス | format=contains '@' | server |
| UIF-006 | お支払い方法 | required | server |
| UIF-006 | お支払い方法 | enum=['CARD', 'BANK', 'COD'] | server |
| UIF-008 | 商品名 | required | server |
| UIF-008 | 価格（税抜） | format=integer | server |
| UIF-008 | 価格（税抜） | min=0 | server |
| UIF-008 | 在庫数 | format=integer | server |
| UIF-008 | 在庫数 | min=0 | server |
| UIF-008 | カテゴリ | enum=['文房具', '事務用品', 'オフィス家具'] | server |
