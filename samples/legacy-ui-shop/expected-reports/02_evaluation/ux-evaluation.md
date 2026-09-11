---
title: "UX 評価 — legacy-ui-shop"
schema_version: 1
phase: "Phase 2: Evaluation"
skill: evaluate-ux
generated_at: "2026-09-11T03:30:26Z"
input_files:
  - reports/before/legacy-ui-shop/ui-inventory.json
  - reports/before/legacy-ui-shop/ui-design-tokens.json
  - reports/02_evaluation/ux-evaluation.json
---

## サマリー (Summary)

**UXI 53.0 — needs-improvement（要改善）**。影響を受けるフローは移植せず再設計する。

- 評価モード: `static`（コードからの静的エキスパートレビュー。実行時の証跡は取得していない）
- 所見: 26 件（critical 2 / major 9 / minor 15 / info 0）
- 対象: 10 画面・12 コンポーネント・9 機能・7 タスク（`reports/before/legacy-ui-shop/ui-inventory.json`）
- 計算式: `UXI = (0.30 × H + 0.25 × A + 0.20 × E + 0.15 × C + 0.10 × N) / 5 × 100`

| 軸 | スコア | メトリクス上限 (cap) | 重大度上限 (severity bound) | 重み | 所見数 |
|----|-------:|-----:|-----:|-----:|-----:|
| H ヒューリスティック（Heuristic usability） | 2 | 3 | 2 | 0.30 | 6 |
| A アクセシビリティ（Accessibility） | 2 | 3 | 2 | 0.25 | 5 |
| E タスク効率・入力負荷（Task efficiency） | 4 | 4 | 4 | 0.20 | 1 |
| C 一貫性（Consistency） | 3 | 3 | 4 | 0.15 | 11 |
| N ナビゲーション・情報設計（Navigation / IA） | 3 | 3 | 3 | 0.10 | 3 |

- **H**: 商品削除（DeleteProduct, UIS-009.A2）が確認なしに商品マスタを完全削除するため critical 欠陥があり（H5）、ログアウトとカート行削除も確認なしに実行される（H5, major）。管理画面の「エラーが発生しました」は原因を示さない汎用エラー文言（H9, major）であり、カート金額表示は JavaScript に依存し失敗すると表示されない（H1, minor）。注文完了画面の確認メール送信メッセージも実装が確認できていない（H1, minor, OQ-001）。critical 欠陥が1件あるため H は 2 点とする。
- **A**: ご注文情報の入力画面（UIS-006）の「電話番号」欄はlabel・aria-label・idのいずれも持たずアクセシブルネームが一切なく、チェックアウトという主要タスクの必須項目であるため致命的な欠陥と判定した。加えて、商品検索画面のキーワード欄がplaceholderのみでラベルが無く、商品サムネイル画像にalt属性が無く、ログイン画面のhtml要素にlang属性が欠落し、カート画面の注意書きテキストがコントラスト比2.32:1（基準4.5:1）しかない。1件のcriticalと4件のmajorにより、スコアはseverity boundの上限である2に抑えられる。
- **E**: 唯一の測定済み欠陥は注文情報入力画面（UIS-006）のメールアドレス欄で、ログイン済みユーザーが既に持つメールアドレスをシステムが再入力させている（metrics.input_burden.redundant_inputs = 1）。タスクの最長ステップ数は4（metrics.input_burden.max_task_steps = 4、しきい値5画面超）、画面あたりの最大可視入力数は7（metrics.input_burden.max_visible_inputs = 7、しきい値12件超）でいずれも上限に達していないため、minor 所見1件のみとなり、メトリクス上限（metrics.caps.E = 4）と重大度上限（minor のみ→4以下）の双方から4点とする。
- **C**: 同一コマンド（AddToCart）のボタンラベルが画面ごとに表記ゆれしており、共有パンくずコンポーネント（UIC-005）も商品検索画面だけ型を外れている。手作業で複製されたボタン・タイトルバーが2コンポーネントあり、トークンでは primary / border / surface-subtle / text の色と、本文サイズ・小文字サイズ・コントロール縦パディングの寸法が計7クラスタで断片化している（metrics.consistency.fragmented_clusters）。一方、カート/注文情報入力画面の遷移先ラベル差はカート空/非空や、パンくずと明示的な戻るリンクという別役割の分岐によるもので、文脈上妥当と判断し欠陥として扱わなかった。重大度は minor のみだが consistency の caps.C = 3 が上限となるためスコアは3。
- **N**: metrics.navigation.dead_ends に挙がる UIS-008（ご注文完了）は退出手段を一切持たないデッドエンドであり、UIS-010（よくあるご質問）は metrics.navigation.orphans / unreachable の双方に現れる、どの画面からも到達できない孤立画面である。加えて、既存商品の編集という能力（UIF-008）には入口となる導線が一つも無く、いずれも H3（利用者の主導権と自由度）を損なう major 相当の欠陥であるため、caps.N=3 とも整合する形でスコアは3に留まる。

## 主要な所見 (Top Findings)

critical と major の所見すべて。利用者への影響が大きい順に並べている。

### UX-001 商品削除が確認なしに商品マスタを完全削除する

- **軸・欠陥**: H / `destructive-without-confirmation` / H5 / critical（致命的）（Product（商品マスタ）を確認なしに完全削除し（entity_operations: Product: D）、元に戻す手段が見当たらないため、irreversibly deletes business data の基準に該当する。）
- **場所**: UIS-009 商品編集（`/admin/products/edit`） / アクション `UIS-009.A2` — `src/main/webapp/WEB-INF/jsp/admin/product-edit.jsp:55-57`
- **影響を受ける人**: ロール: admin
- **内容**: 商品編集画面の「削除」ボタン（UIS-009.A2、コマンド DeleteProduct）は destructive: true・confirmation: false のまま ShopData#deleteProduct を呼び出し、商品（Product）を完全に削除する。取り消し手段は確認できず、管理者の誤クリックがそのまま業務データの永久喪失につながる。
- **修正**: 削除前に商品名を明示した確認ダイアログ（例:「商品『○○』を削除します。よろしいですか？」）を必須にし、可能であれば論理削除・復元機能を設ける。

### UX-002 「電話番号」欄にアクセシブルネームが一切ない

- **軸・欠陥**: A / `unlabeled-input` / WCAG 1.3.1 / critical（致命的）（必須項目「電話番号」がチェックアウト（主要タスク「注文する（チェックアウト）」）の入力欄であり、label・aria-label・title・idのいずれも無くアクセシブルネームを一切持たないため、defect表が定める重大化条件（主要タスク上の必須入力にアクセシブルネームが全く無い場合）に該当する。）
- **場所**: UIS-006 ご注文情報の入力（`/order/entry`） / 入力 `phone` — `src/main/webapp/WEB-INF/jsp/order/entry.jsp:61-62`
- **影響を受ける人**: ロール: customer, admin。利用者グループ: スクリーンリーダー利用者・音声入力利用者
- **内容**: ご注文情報の入力画面（UIS-006）の電話番号欄は `<span class="form-label">電話番号...</span>` でラベル文字列を表示しているだけで、`<label for>` も `id` も `aria-label` も付与されていない（entry.jsp:61-62）。他の6項目（shippingName/postalCode/address/email/paymentMethod/notes）はすべて `label for` または `legend` で関連付けられているのに対し、phoneだけが無関係な `<span>` のままで、スクリーンリーダー利用者にはこの入力欄が何を尋ねているか一切伝わらない。metrics.per_screen.UIS-006.unlabeled_inputs は ["phone"] を示している。
- **修正**: `<input id="phone" name="phone" ...>` とし、`<label for="phone">電話番号<span class="required">必須</span></label>` を他の項目と同じ形で追加する。

### UX-003 カートからの商品削除に確認がない

- **軸・欠陥**: H / `destructive-without-confirmation` / H5 / major（重大）
- **場所**: UIS-005 ショッピングカート（`/cart`） / アクション `UIS-005.A1` — `src/main/webapp/WEB-INF/jsp/cart.jsp:27-31`
- **影響を受ける人**: ロール: customer, admin
- **内容**: ショッピングカート画面の「削除」ボタン（UIS-005.A1、コマンド RemoveCartLine）は destructive: true・confirmation: false で、押すと即座にカート行が削除される（POST /cart）。誤操作を防ぐ仕組みがない。
- **修正**: 削除前に確認ダイアログを表示するか、削除直後に「元に戻す」を提示する Undo パターンを導入する。

### UX-004 ログアウトが確認なしにカートを破棄する

- **軸・欠陥**: H / `destructive-without-confirmation` / H5 / major（重大）
- **場所**: 機能 UIF-002 ログアウトする（8 画面） — `src/main/webapp/WEB-INF/jspf/header.jspf:19-22`
- **影響を受ける人**: ロール: admin, customer
- **内容**: 「ログアウト」は共通ヘッダー（header.jspf）から全画面（UIS-002/003/004/005/006/007/009/010）に配置され、クリック一つで実行される。ui-inventory.json ではこのアクション（コマンド LogOut、機能 UIF-002）は destructive: true・confirmation: false と記録され、entity_operations は Cart: D（カートの破棄）である。買い物中に誤ってクリックすると、確認なしにカートの中身が失われる。
- **修正**: ログアウト前に「カートに商品が入っています。ログアウトしますか？」等の確認ダイアログを表示するか、カートを破棄せずセッションのみ終了する設計に変更する。

### UX-005 商品保存時の汎用エラーメッセージ「エラーが発生しました」

- **軸・欠陥**: H / `vague-error-message` / H9 / major（重大）
- **場所**: UIS-009 商品編集（`/admin/products/edit`） — `src/main/webapp/WEB-INF/jsp/admin/product-edit.jsp:25`
- **影響を受ける人**: ロール: admin
- **内容**: 商品編集画面の保存／削除処理が失敗した際に表示されるメッセージは「エラーが発生しました」のみで、原因（入力値の不備かシステム障害か）も、利用者が次に何をすべきかも示されない。
- **修正**: 失敗理由ごとに具体的なメッセージ（例:「価格は数値で入力してください」「在庫数が不正です」）を出し分け、再入力すべき項目を明示する。

### UX-006 「キーワードを入力」欄がplaceholderのみでラベルが無い

- **軸・欠陥**: A / `unlabeled-input` / WCAG 1.3.1 / major（重大）
- **場所**: UIS-003 商品検索（`/products`） / 入力 `keyword` — `src/main/webapp/WEB-INF/jsp/product/search.jsp:11`
- **影響を受ける人**: ロール: customer, admin。利用者グループ: スクリーンリーダー利用者・音声入力利用者
- **内容**: 商品検索画面（UIS-003）のキーワード入力欄（search.jsp:11）は `placeholder` 属性のみで項目名を示しており、`<label>` 要素を持たない。placeholderは入力を始めると消え、支援技術によってはフォーム項目一覧に表示されないため、視覚的に空欄になった状態やスクリーンリーダーでの一覧表示時に何を入力する欄か分からなくなる。metrics.accessibility.unlabeled_inputs は 2、per_screen.UIS-003.unlabeled_inputs は ["keyword"] を示している。
- **修正**: 同じフォーム内の `category` セレクトと同様に `<label for="keyword">キーワード</label>` を可視ラベルとして追加し、placeholderは補助ヒントに留める。

### UX-007 ログイン画面の html 要素に lang 属性が無い

- **軸・欠陥**: A / `missing-lang` / WCAG 3.1.1 / major（重大）
- **場所**: UIS-001 ログイン（`/login`） — `src/main/webapp/WEB-INF/jsp/login.jsp:5`
- **影響を受ける人**: ロール: anonymous。利用者グループ: スクリーンリーダー利用者（読み上げ言語の誤判定）
- **内容**: ログイン画面（UIS-001, login.jsp:5）は唯一、共通ヘッダー（header.jspf の `<html lang="ja">`、他の全画面が経由）を使わず独自に `<html>` を出力しており、`lang` 属性が欠落している。metrics.accessibility.screens_without_lang は 1、per_screen.UIS-001.lang_missing は true を示す。支援技術がページの自然言語を判定できず、音声読み上げの発音言語切り替えや翻訳ツールの動作に支障が出る。
- **修正**: `<html lang="ja">` に修正する。他画面と同様 header.jspf を経由させるか、同じ属性を直接追加する。

### UX-008 検索結果の商品サムネイル画像に alt 属性が無い

- **軸・欠陥**: A / `missing-alt` / WCAG 1.1.1 / major（重大）
- **場所**: UIS-003 商品検索（`/products`） — `src/main/webapp/WEB-INF/jsp/product/search.jsp:39`
- **影響を受ける人**: ロール: customer, admin。利用者グループ: スクリーンリーダー利用者
- **内容**: 商品検索結果一覧（UIS-003, search.jsp:39）の商品サムネイル `<img src="...${p.image}" width="64" height="64">` は `alt` 属性を持たず、`decorative` として宣言されてもいない（実際に商品を識別する情報を運ぶ画像であり、装飾ではない）。商品詳細画面（UIS-004）の同種の画像は `alt="${product.name}"` を持っており、検索結果側だけが欠落している。metrics.accessibility.images_without_alt は 1、per_screen.UIS-003.images_without_alt も 1 を示す。
- **修正**: 商品詳細画面と同様に `alt="${p.name}"` を付与し、商品名を代替テキストとして提供する。

### UX-009 カート画面の注意書きテキストがコントラスト比不足

- **軸・欠陥**: A / `low-contrast` / WCAG 1.4.3 / major（重大）
- **場所**: UIS-005 ショッピングカート（`/cart`） — `src/main/webapp/css/common.css:125`
- **影響を受ける人**: ロール: customer, admin。利用者グループ: ロービジョン・高齢の利用者
- **内容**: ショッピングカート画面（UIS-005）の `.cart-notes`（税抜表示・在庫状況に関する注意書き、common.css:125）は前景 #aaaaaa / 背景 #ffffff の通常サイズテキストで、metrics.per_screen.UIS-005.low_contrast_pairs が示すコントラスト比は 2.32:1 であり、WCAG 1.4.3 の通常テキスト基準 4.5:1 を大きく下回る。会員割引や消費税の扱いなど注文に影響する重要な注意事項が読み取りにくい。
- **修正**: 前景色を4.5:1以上を満たす濃さ（例: #666666以上、common.css内の他の補助テキストで使われている色）に変更する。

### UX-010 既存商品を編集する画面への導線が存在しない

- **軸・欠陥**: N / `missing-path` / H3 / major（重大）
- **場所**: UIS-002 メニュー（`/menu`）— 既存商品の編集（UIF-008 商品を登録・更新する）への入口があるべき画面 — `src/main/webapp/WEB-INF/jsp/menu.jsp:21`
- **影響を受ける人**: ロール: admin
- **内容**: UIF-008（商品を登録・更新する）が扱う画面 UIS-009（商品編集）は、新規登録時は空、編集時は既存商品の id を hidden で受け取って商品名・価格・在庫・カテゴリを事前表示する作りになっているが（admin/product-edit.jsp:28, 33-52）、この id 付き遷移を発生させるリンクがどの画面にも見当たらない。メニュー画面の「商品メンテナンス」（menu.jsp:21、UIS-002.A3）は UIS-009 へ id なしで遷移するのみで新規登録用の導線であり、商品検索（UIS-003）・商品詳細（UIS-004）の各画面にも編集へのリンクは無い。管理者が既存商品を編集する手段が UI 上に存在しない（OQ-002 として未解決）。
- **修正**: 商品検索結果一覧または商品詳細画面に、管理者ロールが見えるときのみ「編集」リンク（GET /admin/products/edit?id=…）を追加し、既存商品編集への到達経路を確保する。OQ-002 の回答と合わせて導線を確定する。

### UX-011 注文完了画面に離脱手段が一つもない

- **軸・欠陥**: N / `dead-end` / H3 / major（重大）
- **場所**: UIS-008 ご注文完了（`/order/complete`） — `src/main/webapp/WEB-INF/jsp/order/complete.jsp:11-24`
- **影響を受ける人**: ロール: customer, admin
- **内容**: metrics.navigation.dead_ends (value ["UIS-008"]) の通り、UIS-008（ご注文完了）は actions が0件で、メニューやショッピングカートへ戻るリンクは元よりログアウト以外の共通ナビゲーションすら持たない。header.jspf を使わず手作業で複製されたタイトルバー（UIC-012、order/complete.jsp:11-13）に置き換えられており、そこにログアウトリンクや氏名表示も含まれていないため、注文完了後に利用者が次の行動（買い物を続ける・メニューに戻る）へ進む手段が画面内に存在しない。
- **修正**: 「メニューへ戻る」「引き続き買い物をする」等の次の行動へのリンクを注文完了画面に追加し、他画面と同じ header.jspf / footer.jspf を使ってナビゲーションの一貫性も回復する。

## 軸別の所見 (Findings by Axis)

minor / info の所見を軸と欠陥ごとにまとめる（critical・major は前節）。

### H ヒューリスティック（Heuristic usability）

| ID | 欠陥 | 基準 | 重大度 | 場所 | 所見 | 修正 |
|----|------|------|--------|------|------|------|
| UX-013 | `other` | H1 | minor | UIS-008 ご注文完了（`/order/complete`）（`src/main/webapp/WEB-INF/jsp/order/complete.jsp:24`） | 注文完了画面の「確認メールをお送りしました」の実態が確認できない | メール送信の実装有無を確認し（OQ-001 の解消）、送信していないなら文言を削除するか、送信を実装したうえで実際の送信結果に応じたメッセージ（成功/失敗）に改める。 |
| UX-012 | `script-dependent-content` | H1 | minor | UIS-005 ショッピングカート（`/cart`）（`src/main/webapp/js/cart.js:5-16`） | カート行の金額表示が JavaScript 依存 | 金額計算をサーバー側（例: CartLine#getLineTotal）で行い、初期 HTML に確定値を出力する。JavaScript は装飾・補助的な再計算にとどめる。 |

### A アクセシビリティ（Accessibility）

minor / info の所見はない。

### E タスク効率・入力負荷（Task efficiency）

| ID | 欠陥 | 基準 | 重大度 | 場所 | 所見 | 修正 |
|----|------|------|--------|------|------|------|
| UX-014 | `redundant-input` | WCAG 3.3.7 | minor | UIS-006 ご注文情報の入力（`/order/entry`） / 入力 `email`（`src/main/webapp/WEB-INF/jsp/order/entry.jsp:64-68`） | 注文情報入力画面でログイン済みユーザーのメールアドレスを再入力させている | OrderEntryServlet#doGet で shippingName と同様に、注文フォーム未作成時はログインユーザーの User.email を email フィールドの初期値として設定する。ユーザーが別の受取用アドレスを使いたい場合は上書きできるようにし、初期値はあくまで既知の値の再提示に留める。 |

### C 一貫性（Consistency）

| ID | 欠陥 | 基準 | 重大度 | 場所 | 所見 | 修正 |
|----|------|------|--------|------|------|------|
| UX-016 | `hand-built-duplicate` | H4 | minor | UIS-009 商品編集（`/admin/products/edit`） / コンポーネント UIC-011（インラインスタイルの保存ボタン）（`src/main/webapp/WEB-INF/jsp/admin/product-edit.jsp:54`） | 商品編集画面の保存ボタンがインラインスタイルで共通ボタンを複製している | インラインスタイルを廃し、共通の button.tag（variant=primary）を使うよう置き換える。 |
| UX-017 | `hand-built-duplicate` | H4 | minor | UIS-008 ご注文完了（`/order/complete`） / コンポーネント UIC-012（手作業で複製されたタイトルバー）（`src/main/webapp/WEB-INF/jsp/order/complete.jsp:11-13`） | ご注文完了画面のタイトルバーが共通ヘッダーを手作業で複製している | 手作業コピーをやめ、共通の header.jspf をインクルードする形に戻す。 |
| UX-015 | `navigation-label-variant` | H4 | minor | UIS-003 商品検索（`/products`） / コンポーネント UIC-005（breadcrumb）（`src/main/webapp/WEB-INF/jsp/product/search.jsp:8`） | 商品検索画面だけパンくずが「メニュー > 現在ページ」の型を外れている | 商品検索画面のパンくずも他画面と同じ「メニュー > 商品検索」の型に揃え、専用の search.backToMenu メッセージキーを廃止する。 |
| UX-018 | `label-drift` | H4 | minor | 機能 UIF-004 カートに商品を追加する（2 画面）（`src/main/webapp/WEB-INF/jsp/product/detail.jsp:21-27`） | 「カートに追加」コマンドのボタンラベルが画面ごとに異なる | AddToCart の表示ラベルをどちらか一方（例:「カートに入れる」）に統一し、共有コンポーネント（button.tag等）またはメッセージリソースで一元管理する。 |
| UX-019 | `token-fragmentation` | H4 | minor | トークン `color.hex-0066cc`（`src/main/webapp/css/common.css:60`） | プライマリカラーが3種類の色値に断片化している（color:primary クラスタ） | 3値を1つの semantic トークン（例: semantic.color.primary）に統合し、admin.css とインラインスタイルをそのトークン参照に置き換える。 |
| UX-020 | `token-fragmentation` | H4 | minor | トークン `color.hex-333333`（`src/main/webapp/css/common.css:9`） | 本文テキスト色が2種類の色値に断片化している（color:text クラスタ） | 本文テキスト色を semantic.color.text の1トークンに統一する。 |
| UX-021 | `token-fragmentation` | H4 | minor | トークン `color.hex-dddddd`（`src/main/webapp/css/common.css:44`） | 境界線色が5種類の色値に断片化している（color:border クラスタ） | 境界線色を semantic.color.border 系の1〜2トークンに集約する。 |
| UX-022 | `token-fragmentation` | H4 | minor | トークン `color.hex-eeeeee`（`src/main/webapp/css/common.css:100`） | 淡色サーフェス背景が5種類の色値に断片化している（color:surface-subtle クラスタ） | 淡色サーフェス背景を semantic.color.surface-subtle の1トークンに統合する。 |
| UX-023 | `token-fragmentation` | H4 | minor | トークン `font.size.px-12`（`src/main/webapp/css/common.css:46`） | 小文字サイズが11pxと12pxに断片化している（dimension:small-text クラスタ） | 必須バッジの11pxを共通の12pxトークンに合わせる。 |
| UX-024 | `token-fragmentation` | H4 | minor | トークン `font.size.px-14`（`src/main/webapp/css/common.css:8`） | 本文フォントサイズが13pxと14pxに断片化している（dimension:body-text クラスタ） | インラインスタイルの13pxを廃し、共通の本文サイズトークン（14px）に合わせる。 |
| UX-025 | `token-fragmentation` | H4 | minor | トークン `space.px-4`（`src/main/webapp/css/common.css:20`） | コントロールの縦パディングが4pxと6pxに断片化している（dimension:control-padding-y クラスタ） | コントロール縦パディングを1つのトークン（例: space.control-padding-y）に統一するか、用途別に明示的な2トークンとして命名し直す。 |

### N ナビゲーション・情報設計（Navigation / IA）

| ID | 欠陥 | 基準 | 重大度 | 場所 | 所見 | 修正 |
|----|------|------|--------|------|------|------|
| UX-026 | `orphan-screen` | H10 | minor | UIS-010 よくあるご質問（`/help.jsp`）（`src/main/webapp/help.jsp:6-15`） | よくあるご質問画面がどの画面からもリンクされていない | OQ-003 の回答に応じて、提供するならメニュー画面またはヘッダーに「よくあるご質問」へのリンクを追加し、不要であれば画面を削除する。 |

## 画面ヒートマップ (Screen Heatmap)

画面 × 軸の所見数。画面を持たない所見（トークン・コンポーネント・機能のみに位置づくもの）は最終行にまとめる。

| 画面 | H | A | E | C | N | 計 |
|------|--:|--:|--:|--:|--:|--:|
| UIS-001 ログイン | 0 | 1 | 0 | 0 | 0 | 1 |
| UIS-002 メニュー | 0 | 0 | 0 | 0 | 1 | 1 |
| UIS-003 商品検索 | 0 | 2 | 0 | 1 | 0 | 3 |
| UIS-004 商品詳細 | 0 | 0 | 0 | 0 | 0 | 0 |
| UIS-005 ショッピングカート | 2 | 1 | 0 | 0 | 0 | 3 |
| UIS-006 ご注文情報の入力 | 0 | 1 | 1 | 0 | 0 | 2 |
| UIS-007 ご注文内容の確認 | 0 | 0 | 0 | 0 | 0 | 0 |
| UIS-008 ご注文完了 | 1 | 0 | 0 | 1 | 1 | 3 |
| UIS-009 商品編集 | 2 | 0 | 0 | 1 | 0 | 3 |
| UIS-010 よくあるご質問 | 0 | 0 | 0 | 0 | 1 | 1 |
| トークン／コンポーネント／機能のみ | 1 | 0 | 0 | 8 | 0 | 9 |

## 主要メトリクス (Key Metrics)

すべて `tools/lib/ui_metrics.py` の出力（`ux-evaluation.json` の `metrics` に同一内容を収録）。

| 指標 | 値 | 関係する軸 |
|------|----|-----------|
| `metrics.caps` | H=3, A=3, E=4, C=3, N=3 | 全軸 |
| `metrics.per_screen.*.destructive_without_confirmation` | 10 件（UIS-002.A4, UIS-003.A4, UIS-004.A4, UIS-005.A1, UIS-005.A6, UIS-006.A5, UIS-007.A5, UIS-009.A2, UIS-009.A6, UIS-010.A2） | H |
| `metrics.accessibility.screens_with_violations` | 4 / 10 画面（UIS-001, UIS-003, UIS-005, UIS-006） | A |
| `metrics.accessibility.unlabeled_inputs` | 2 | A |
| `metrics.accessibility.images_without_alt` | 1 | A |
| `metrics.accessibility.screens_without_lang` | 1 | A |
| `metrics.per_screen.UIS-005.low_contrast_pairs` | #aaaaaa / #ffffff = 2.32:1（基準 4.5:1） | A |
| `metrics.input_burden.redundant_inputs` | 1（UIS-006 `email`） | E |
| `metrics.input_burden.max_task_steps` | 4（上限 5） | E |
| `metrics.input_burden.max_visible_inputs` | 7（上限 12） | E |
| `metrics.input_burden.max_task_inputs` | 7 | E |
| `metrics.consistency.fragmented_clusters` | 7（color:border, color:primary, color:surface-subtle, color:text, dimension:body-text, dimension:control-padding-y, dimension:small-text） | C |
| `metrics.consistency.label_drift` | AddToCart: カートに入れる / カートに追加 | C |
| `metrics.consistency.components_with_duplicates` | UIC-011, UIC-012 | C |
| `metrics.consistency.colors` | 23 | C |
| `metrics.navigation.dead_ends` | UIS-008 | N |
| `metrics.navigation.orphans` / `unreachable` | UIS-010 / UIS-010 | N |
| `metrics.navigation.max_depth` | 5 | N |

## 改善の優先順位 (Improvement Priorities)

`/architect:integrate-evaluations` が統合する区分に合わせ、短期（クイックウィン）と中長期（構造的改善）に分ける。帯が `needs-improvement` であるため、チェックアウトと商品メンテナンスの 2 フローは移植せず再設計の対象とする。

### 短期（クイックウィン）

テンプレートやサーブレットの局所的な修正で解消でき、新 UI でも同じ誤りを繰り返さないために先に潰す項目。

1. **商品削除の確認ステップ**（UX-001）— 商品名を明示した確認を必須にする。唯一の critical な業務データ喪失経路。
2. **「電話番号」欄のラベル関連付け**（UX-002）— `<label for="phone">` と `id` を付けるだけで、チェックアウトの必須入力がスクリーンリーダーで識別できるようになる。
3. **残りの静的アクセシビリティ違反** — キーワード欄のラベル（UX-006）、検索結果サムネイルの `alt`（UX-008）、ログイン画面の `lang`（UX-007）、カート注意書きのコントラスト（UX-009）。
4. **注文完了画面の出口** — 共通ヘッダー・フッターをインクルードして次の行動へのリンクを置く（UX-011）。手作業で複製したタイトルバー（UX-017）も同時に解消する。
5. **商品編集画面のエラー文言** — 汎用の「エラーが発生しました」を項目別のメッセージに置き換える（UX-005）。
6. **カート行削除の確認または取り消し**（UX-003）と、**メールアドレスの初期表示**（UX-014）。
7. **AddToCart のラベル統一**（UX-018）。

### 中長期（構造的改善）

1. **デザイントークンの統合** — 断片化した 7 クラスタ（UX-019〜UX-025）とインラインスタイルの保存ボタン（UX-016）を、`/product:design-system --import` の統合リストとして扱う。C 軸の所見がそのまま入力になる。
2. **ログアウトとカートの扱い** — ログアウトがセッションのカートを確認なしに破棄する（UX-004）。確認を挟むか、カートをセッションから切り離して保持するかを新 UI の設計判断として決める。
3. **カート金額のサーバー側描画** — JavaScript に依存した金額表示（UX-012）は、`/architect:redesign` に回付したビュー層の金額計算をドメインへ移すことと同時に解消する。
4. **管理画面の情報設計** — 既存商品の編集への導線がない（UX-010、OQ-002）。OQ-002 の回答を得たうえで、商品一覧・詳細から編集へ入る管理フローを再設計する。
5. **ヘルプと完了通知の扱い** — 孤立した FAQ 画面（UX-026、OQ-003）と、送信実装が確認できない確認メールの文言（UX-013、OQ-001）は、業務オーナーの回答を待って導線追加・文言修正・廃止のいずれかを決める。

## 手法と限界 (Method and Limits)

- **評価の性質** — `ui-inventory.json`・`ui-design-tokens.json` と、それらが引用する JSP / CSS / JavaScript / Servlet のソースに基づく**静的エキスパートレビュー**である。利用者は一人も観察しておらず、ユーザビリティテストではない。所見はコードに現れる構造上の事実であり、実際の利用者の所要時間や離脱箇所を示すものではない。
- **実行時の証跡** — `--base-url` の指定がないため取得していない（モード `static`、`runtime.captured` は空）。このため、WCAG 2.5.8（ターゲットサイズ）、計算後のコントラスト、送信後のエラー表示（WCAG 3.3.1 / 3.3.3 の実表示）、スクリプトが挿入する内容は評価していない。コントラストは宣言されたスタイルのみから `ui_metrics.py` が算出した値である。
- **主要タスク** — `--auto` で実行したため、インベントリの 7 タスクすべてを主要タスクとして扱った。この扱いにより、必須入力「電話番号」のラベル欠落は「主要タスク上の必須入力」に該当し critical と判定されている。
- **ペルソナ・アクター** — `reports/01_ux/personas.md` / `journey-maps.md` は存在せず、ペルソナによる重み付けは行っていない。`/architect:analyze` のアクターマトリクスもないため、影響を受けるロールは各画面の `access.roles` のみから判断した。
- **ベースライン** — 以前の `ux-evaluation.json` はなく、すべての所見を新規に判定した。
- **未解決の質問** — OQ-001（確認メール送信の有無）、OQ-002（既存商品編集への導線）、OQ-003（FAQ 画面の提供意図）は `--auto` のため質問せず `unasked` のまま残した。これらに依拠する所見は本文で OQ 番号を示し、未確定の事柄を事実として述べていない。
- **評価体制** — 5 軸それぞれを独立した評価エージェントが採点し、所見の統合・所有軸の確認・重複排除・重大度の較正・ID 付与・スコアの上限適用・UXI の計算は親スキルが行った。統合時にソースと照合した結果、C 軸が当初「同一遷移先への異なるラベルの並存」として挙げた 3 件（UIS-009 の `product-edit.jsp:14` と `:18`、UIS-005 の `cart.jsp:12` と `:42`、UIS-006 の `entry.jsp:23` と `:80`）は、前 2 件が相互に排他的な描画分岐（権限なし／あり、カート空／非空）にあって同時には表示されず、後 1 件はパンくずと戻るリンクという役割の異なる通常のパターンであったため、C 軸の評価エージェントに再検証を依頼し、3 件とも取り下げた。代わりに、共有パンくず（UIC-005）の表記が商品検索画面だけ異なる点を 1 件として採用している。遷移先ラベルの揺れ（`metrics.consistency.destination_label_variants`）はメトリクス上限に影響しない判断材料であり、その他の揺れは文脈上妥当と判断した。
- **範囲外として回付した事項**（スコアには含めない。`ux_evaluation.py --routed` がインベントリから集めた 12 件）:
  - `/architect:investigate-security` ← メニュー（UIS-002）の「商品メンテナンス」リンクの表示可否をスクリプトレットがセッションのロール文字列比較で決めている（action guard kind: view）。表示制御がアクセス制御の代わりになっていないかを確認する。（`src/main/webapp/WEB-INF/jsp/menu.jsp:16-25`）
  - `/architect:redesign` ← authorization in the view of UIS-002: 「商品メンテナンス」メニュー項目の表示可否を、スクリプトレットがセッションの loginUser の getRole() を文字列 "admin" と比較して決めている。共通のアクセス制御ではなくビュー内の判定。（`src/main/webapp/WEB-INF/jsp/menu.jsp:16-25`）
  - `/architect:redesign` ← 注文可否（在庫数 > 0）を商品検索・商品詳細テンプレートの EL で判定してフォームと在庫切れ表示を切り替えている。ルールがドメイン（例: Product#isOrderable）にない。（`src/main/webapp/WEB-INF/jsp/product/search.jsp:43-51`）
  - `/architect:redesign` ← 商品詳細でも同じ注文可否判定（在庫数 > 0）をテンプレートの EL で行っている（商品検索と重複）。（`src/main/webapp/WEB-INF/jsp/product/detail.jsp:16-31`）
  - `/architect:redesign` ← カート各行の金額（単価 × 数量）を cart.js が計算しており、ドメインの CartLine#getLineTotal() と重複している。計算をサーバー側に一本化する（UX 上の帰結＝JavaScript 無効時に金額が出ない点は H 軸の所見として別に扱う）。（`src/main/webapp/js/cart.js:5-16`）
  - `/architect:investigate-security` ← client-only pattern on UIS-006.postalCode（`src/main/webapp/js/validation.js:15-19`）
  - `/architect:investigate-security` ← client-only maxLength on UIS-006.postalCode（`src/main/webapp/WEB-INF/jsp/order/entry.jsp:53`）
  - `/architect:redesign` ← 会員割引（会員かつ小計 10,000 円以上で 10%）を注文入力画面のスクリプトレットで計算してセッションに書き込み、注文確定がその値をそのまま使っている。ドメインへ移す。（`src/main/webapp/WEB-INF/jsp/order/entry.jsp:10-19`）
  - `/architect:redesign` ← validation in the view of UIS-006: 郵便番号の形式（^\d{3}-\d{4}$）はクライアントの JavaScript だけで検査している。サーバー（OrderEntryServlet.java:63）は必須チェックのみのため、直接 POST すれば形式ルールを回避できる。（`src/main/webapp/js/validation.js:5-19`）
  - `/architect:redesign` ← calculation in the view of UIS-007: 消費税（(小計 − 割引) × 10% の切り捨て）と支払合計をスクリプトレットで計算している。税率 10% はハードコード。（`src/main/webapp/WEB-INF/jsp/order/confirm.jsp:8-15`）
  - `/architect:redesign` ← workflow in the view of UIS-007: 計算した消費税・合計をビューがセッション属性 orderTax / orderTotal に書き込み、OrderConfirmServlet#doPost（OrderConfirmServlet.java:40-41, 48-49）がそれを読んで注文を登録する。確認画面を経由しないと注文できず、金額の正はビューにある。（`src/main/webapp/WEB-INF/jsp/order/confirm.jsp:16-17`）
  - `/architect:redesign` ← authorization in the view of UIS-009: 管理者のみの制限をスクリプトレット（loginUser.role == "admin"）だけで行っている。AdminProductEditServlet の doGet / doPost にロールチェックはなく、ログイン済みの一般会員が /admin/products/edit に直接 POST すれば商品を保存・削除できる。（`src/main/webapp/WEB-INF/jsp/admin/product-edit.jsp:9-17`）

