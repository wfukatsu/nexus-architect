---
title: "UI 部品 — legacy-ui-shop"
schema_version: 1
phase: "Phase 1: Investigation"
skill: analyze-ui
generated_at: "2026-09-11T02:56:47Z"
input_files:
  - reports/before/legacy-ui-shop/ui-inventory.json
  - reports/before/legacy-ui-shop/ui-design-tokens.json
---

## 部品一覧（Component Inventory）

| ID | 名前 | 種別 | レベル | バリアント | 状態 | 使用画面 | 出典 |
|---|---|---|---|---|---|---|---|
| UIC-001 | header.jspf | include | template | extraCss=admin.css（管理画面用スタイルを追加） | ログイン中（ログアウトリンクと氏名を表示）, 未ログイン（ログアウトリンクなし） | UIS-002, UIS-003, UIS-004, UIS-005, UIS-006, UIS-007, UIS-009, UIS-010 | `src/main/webapp/WEB-INF/jspf/header.jspf` |
| UIC-002 | footer.jspf | include | template | - | - | UIS-002, UIS-003, UIS-004, UIS-005, UIS-006, UIS-007, UIS-009, UIS-010 | `src/main/webapp/WEB-INF/jspf/footer.jspf` |
| UIC-003 | button.tag | tag | atom | variant=primary, variant=secondary, type=submit（既定）\|button, name/value 指定あり | hover | UIS-001, UIS-003, UIS-004, UIS-005, UIS-006, UIS-007, UIS-009 | `src/main/webapp/WEB-INF/tags/button.tag` |
| UIC-004 | pager.tag | tag | atom | - | 非表示（1ページのみ）, 現在ページ, 前へ／次へ 無効 | UIS-003 | `src/main/webapp/WEB-INF/tags/pager.tag` |
| UIC-005 | breadcrumb | css-class | atom | - | - | UIS-003, UIS-004, UIS-005, UIS-006, UIS-007, UIS-009 | `src/main/webapp/css/common.css:50` |
| UIC-006 | list-table | css-class | atom | tfoot 合計行（common.css:102） | - | UIS-003, UIS-005, UIS-007 | `src/main/webapp/css/common.css:99-104` |
| UIC-007 | detail-table | css-class | atom | - | - | UIS-004, UIS-007 | `src/main/webapp/css/common.css:106-108` |
| UIC-008 | steps | css-class | atom | - | active（現在のステップ） | UIS-006, UIS-007, UIS-008 | `src/main/webapp/css/common.css:129-131` |
| UIC-009 | error-message | css-class | atom | - | - | UIS-001, UIS-004, UIS-009 | `src/main/webapp/css/common.css:91` |
| UIC-010 | form-row | css-class | atom | fieldset.form-row（ラジオグループ＋legend、common.css:75-76）, login-box 内でラベル幅 100px（common.css:146）, admin-panel 内でラベル幅 120px（admin.css:17） | - | UIS-001, UIS-006, UIS-009 | `src/main/webapp/css/common.css:66-76` |
| UIC-011 | インラインスタイルの保存ボタン | inline-style | atom | - | - | UIS-009 | `src/main/webapp/WEB-INF/jsp/admin/product-edit.jsp:54` |
| UIC-012 | 手作業で複製されたタイトルバー | copy | atom | - | - | UIS-008 | `src/main/webapp/WEB-INF/jsp/order/complete.jsp:11-13` |

## 手作りの重複（Hand-Built Duplicates）

| ID | 名前 | 種別 | 元の部品 | 出典 |
|---|---|---|---|---|
| UIC-011 | インラインスタイルの保存ボタン | inline-style | UIC-003 button.tag | `src/main/webapp/WEB-INF/jsp/admin/product-edit.jsp:54` |
| UIC-012 | 手作業で複製されたタイトルバー | copy | UIC-001 header.jspf | `src/main/webapp/WEB-INF/jsp/order/complete.jsp:11-13` |

## 未使用の部品（Unused Components）

なし。
