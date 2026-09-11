# Project Context — legacy-ui-shop

## Decisions

- 2026-09-11 analyze-ui (--auto): the UI is JSP/Servlet + JSTL + vendored jQuery 3.7.1; 10 screens, analysed in two extraction batches.

## Open Questions

| ID | Question | Status | Answer | Options offered | Owner | Impact | Asked at |
|----|----------|--------|--------|-----------------|-------|--------|----------|
| OQ-001 | ご注文完了画面は「ご入力いただいたメールアドレスに注文確認メールをお送りしました。」と表示する（src/main/webapp/WEB-INF/jsp/order/complete.jsp:24）が、注文確定処理（OrderConfirmServlet.java:35-58、ShopData.java:114-123）にメール送信のコードはない。注文確認メールは送られているのか、どのシステムが送るのか？ | unasked | | (1) 本コードベース外の別システムが注文データから送信している — その連携を要件に含める / (2) 送信されていない — 完了画面・入力画面の文言が誤りで、削除または修正する / (3) 送信すべきだが未実装 — PlaceOrder の要件として新規に実装する / (4) Defer — record as TBD | 業務オーナー（受注業務） | UIF-006 PlaceOrder の要件、UIS-008 の表示文言、UIS-006 のメールアドレス入力欄（hint: entry.jsp:67）の目的 | |
| OQ-002 | 既存商品の編集画面（/admin/products/edit?id=…）へはどの画面からも遷移できない（メニューは新規登録 menu.jsp:21 のみ、商品検索・商品詳細は編集へリンクしない）。管理者は既存商品の価格・在庫をどうやって変更しているのか？ | unasked | | (1) 管理者が URL を直接入力・ブックマークしている（現行運用） — 導線は不要 / (2) 商品一覧または商品詳細から編集へのリンクがあるべき — 再設計で導線を追加する / (3) 既存商品の編集は画面機能の対象外（別の手段で更新） / (4) Defer — record as TBD | 業務オーナー（商品管理） | UIF-008 SaveProduct / UIF-009 DeleteProduct への導線、UIS-009 の到達性、再設計の管理画面構成 | |
| OQ-003 | よくあるご質問（/help.jsp, src/main/webapp/help.jsp）はどの画面からもリンクされていない（孤立画面）。この画面は利用者に提供する想定か？ | unasked | | (1) メニューまたはヘッダーからリンクする想定だった — 再設計で導線を追加する / (2) 外部（マニュアル・メール等）からの直リンク専用 — 現状どおり / (3) 廃止済み — 再設計の対象外 / (4) Defer — record as TBD | 業務オーナー（顧客サポート） | UIS-010 の扱い（孤立画面の解消 or 削除）、FAQ 記載の会員割引ルール（help.jsp:10）を要件の根拠として扱うか | |
