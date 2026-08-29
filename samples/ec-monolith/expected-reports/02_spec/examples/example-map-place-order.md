---
title: "Example Map: 注文を確定する"
schema_version: 1
phase: "Phase 3: UX -> Spec"
skill: example-map
generated_at: "2026-08-29T02:00:00Z"
feature: FEAT-001
mode: "auto"
input_files:
  - reports/02_spec/feature-list.md
  - reports/03_design/aggregates/aggregate-manifest.json
  - reports/04_stories/domain-story-ordering.md
  - work/context.md
---

## ストーリー

**FEAT-001** — 注文を確定する: 顧客がカートの内容を注文として確定し、在庫が引き当てられ、決済が完了すると注文が Confirmed になる。画面: カート / 注文確認。MoSCoW: Must。

ルールは `aggregate-manifest.json` の Order（AGG-001）・StockItem（AGG-002）・Reservation（AGG-003）・Payment（AGG-004）の不変条件から採取した。各例は不変条件の `examples` を given / when / then に展開したもので、集約側の例と 1 対 1 に対応する。

## ルール

| ID | Rule | Source | Examples |
|----|------|--------|----------|
| RULE-001 | 注文の合計金額は各明細の単価 × 数量の和に等しい | AGG-001 INV-1 | EX-001, EX-002 |
| RULE-002 | Draft を出た注文は明細を 1 行以上持つ | AGG-001 INV-2 | EX-003, EX-004 |
| RULE-003 | Placed 以降、明細は追加・削除・数量変更できない | AGG-001 INV-3 | EX-005, EX-006 |
| RULE-004 | Confirmed の注文は成功した決済をちょうど 1 つ参照する | AGG-001 INV-4 | EX-007, EX-008 |
| RULE-005 | 引当数は手持ち数を超えない（過剰引当しない） | AGG-002 INV-1, NFR-002 | EX-009, EX-010 |
| RULE-006 | 同じ注文の同じ商品に対する引当は高々 1 件（再配信で二重引当しない） | AGG-003 INV-1 | EX-011, EX-012 |
| RULE-007 | 注文ごとに売上確定済みの決済は高々 1 つ（再配信で二重課金しない） | AGG-004 INV-1 | EX-013, EX-014 |
| RULE-008 | 売上確定額は与信額に等しい | AGG-004 INV-2 | EX-015, EX-016 |

## 例

| ID | Rule | Kind | Given | When | Then |
|----|------|------|-------|------|------|
| EX-001 | RULE-001 | positive | 1,200 円 × 2 の明細 1 行を持つ Draft 注文 | 商品 7（800 円）× 1 を追加する | 合計 3,200 円、OrderLineAdded |
| EX-002 | RULE-001 | negative | 1,200 円 × 2 の明細 1 行を持つ Draft 注文 | 数量 0 の明細を追加する | 拒否: invalid-quantity、合計は変わらない |
| EX-003 | RULE-002 | positive | 明細 2 行の Draft 注文 | 明細 2 を削除する | 明細 1 行が残る、OrderLineRemoved |
| EX-004 | RULE-002 | negative | 明細 1 行の Draft 注文 | 明細 1 を削除する | 拒否: order-would-be-empty（確定自体は許される） |
| EX-005 | RULE-003 | positive | Draft 注文 | 商品 3 × 1 を追加する | 明細が追加される |
| EX-006 | RULE-003 | negative | Placed 注文 | 商品 3 × 1 を追加する | 拒否: order-not-editable |
| EX-007 | RULE-004 | positive | Placed 注文と、その注文に対する PaymentCaptured | confirm(paymentId) | Confirmed、paymentId が設定される、OrderConfirmed |
| EX-008 | RULE-004 | negative | 売上確定済み決済のない Placed 注文 | confirm(null) | 拒否: payment-required |
| EX-009 | RULE-005 | positive | onHand 50、reserved 48 の在庫品目 | 2 個引き当てる | reserved 50、StockReserved |
| EX-010 | RULE-005 | negative | onHand 50、reserved 49 の在庫品目 | 2 個引き当てる | 拒否: insufficient-stock、reserved は 49 のまま |
| EX-011 | RULE-006 | positive | (注文 9, 商品 3) の引当がない | open(注文 9, 商品 3, 2 個) | 引当が Pending で作られる |
| EX-012 | RULE-006 | negative | (注文 9, 商品 3) の Pending な引当がある | open(注文 9, 商品 3, 2 個) が再配信される | 無視: 既存の引当が返り、2 件目は作られない |
| EX-013 | RULE-007 | positive | 注文 9 の決済がない | authorize(注文 9, 3,200 円) | Authorized、PaymentAuthorized |
| EX-014 | RULE-007 | negative | 注文 9 の Captured な決済がある | authorize(注文 9, 3,200 円) が再配信される | 無視: 既存の決済が返り、PSP は呼ばれない |
| EX-015 | RULE-008 | positive | 3,200 円で Authorized | capture | Captured 3,200 円、PaymentCaptured |
| EX-016 | RULE-008 | negative | 3,200 円で Authorized | 3,000 円で capture | 拒否: amount-mismatch |

## シナリオ横断の例

ルール単独では表せない、確定フロー全体の例。`design-state-machine`（STM-001）の遷移と `generate-test-specs` の受け入れシナリオの入力になる。

| ID | Rules | Given | When | Then |
|----|-------|-------|------|------|
| EX-017 | RULE-002, RULE-005, RULE-007, RULE-004 | 明細 2 行のカート、全商品に在庫あり、有効なカード | 注文を確定する | Placed で応答 → StockReserved × 2 → PaymentCaptured → Confirmed、確認メール |
| EX-018 | RULE-005 | 明細 2 行のカート、商品 3 の在庫が 0 | 注文を確定する | Placed で応答、商品 3 は insufficient-stock、注文は Placed のまま（OQ-017） |
| EX-019 | RULE-007 | Placed 注文、PSP がカードを拒否 | PaymentDeclined を受ける | Cancelled、OrderCancelled → 引当が解放される |
| EX-020 | RULE-004 | Placed 注文、PSP から応答が来ない | payment_timeout（OQ-004 の時間） | Cancelled、引当が解放される |

## 質問

| OQ | Question | Status | Owner | Options offered |
|----|----------|--------|-------|-----------------|
| OQ-003 | Confirmed の注文を出荷前に顧客自身がキャンセルできるか、オペレータ限定か | unasked | プロダクトオーナー | 顧客が可能（推奨）/ オペレータ限定 / 決済から N 分以内のみ顧客が可能 |
| OQ-004 | Placed 注文が決済応答を待つ上限（payment_timeout）は何分か | unasked | プロダクトオーナー | 15 分 / 1 時間（推奨）/ 24 時間 |
| OQ-017 | 引当不能（insufficient-stock）を Ordering に即時通知するイベントを追加するか、timeout まで Placed で待つか | unasked | アーキテクト | StockReservationFailed を追加（推奨）/ timeout まで待つ |
| OQ-010 | 一部の明細だけ引当できた注文をどう扱うか（部分出荷 / 全体キャンセル / 顧客に選ばせる） | unasked | プロダクトオーナー | 全体キャンセル（推奨、現行と同じ）/ 部分出荷 / 顧客に選ばせる |
| OQ-011 | 与信のみ成功し売上確定が失敗した場合、与信を取り消すか再試行するか | unasked | 決済担当 | PSP の与信取消を呼ぶ（推奨）/ 与信の自動失効を待つ |

`OQ-` は `work/context.md` § Open Questions に記録済み。`--auto` 実行のため全て `unasked`。

## サイズ判定

ルール 8 件、例 20 件。境界の上限（6〜8 件）にあるが、RULE-005〜008 は Inventory / Payment が守るルールを Ordering 側の受け入れ条件として引用しているものであり、FEAT-001 のストーリーは分割しない。もし OQ-010（部分出荷）が「部分出荷」で決まれば、出荷は別フィーチャー（FEAT-004 出荷する）に切り出す。

## 上流への指摘

- `feature-list.md` の FEAT-001 は「注文を確定し、決済が完了したら確認メールを送る」と述べているが、確認メールは Notification（CTX-006）が Conformist で送るものであり（ADR-004）、FEAT-001 の受け入れ条件からは外す。メール送達は NFR ではなく運用指標で扱う。
- 現行の `placeOrder()` はカード番号を注文 API の引数で受け取る。RULE-007 / RULE-008 は PSP トークン（CardReference）を前提としており、カード番号を Ordering の API が受け取らない設計に `design-api` で改める必要がある。
