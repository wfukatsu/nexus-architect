---
title: "デザインシステム抽出 — legacy-ui-shop"
schema_version: 1
phase: "Phase 1: Investigation"
skill: analyze-ui
generated_at: "2026-09-11T02:56:47Z"
input_files:
  - reports/before/legacy-ui-shop/ui-inventory.json
  - reports/before/legacy-ui-shop/ui-design-tokens.json
---

## カラーパレット（Palette）

| トークン | 値 | 使用数 | クラスタ | 出典 |
|---|---|---|---|---|
| `color.hex-0052a3` | `#0052a3` | 1 | primary-hover | src/main/webapp/css/common.css:61 |
| `color.hex-006600` | `#006600` | 1 | success | src/main/webapp/css/common.css:93 |
| `color.hex-0066cc` | `#0066cc` | 6 | primary | src/main/webapp/css/common.css:14, src/main/webapp/css/common.css:22, src/main/webapp/css/common.css:32 …+3 |
| `color.hex-0a66c2` | `#0a66c2` | 2 | primary | src/main/webapp/css/admin.css:13, src/main/webapp/css/admin.css:26 |
| `color.hex-1a73e8` | `#1a73e8` | 1 | primary | src/main/webapp/WEB-INF/jsp/admin/product-edit.jsp:54 |
| `color.hex-333333` | `#333333` | 4 | text | src/main/webapp/css/common.css:9, src/main/webapp/css/common.css:21, src/main/webapp/css/common.css:62 …+1 |
| `color.hex-444444` | `#444444` | 2 | text | src/main/webapp/css/common.css:27, src/main/webapp/css/common.css:100 |
| `color.hex-666666` | `#666666` | 6 | text-muted | src/main/webapp/css/common.css:45, src/main/webapp/css/common.css:50, src/main/webapp/css/common.css:89 …+3 |
| `color.hex-aaaaaa` | `#aaaaaa` | 1 | text-faint | src/main/webapp/css/common.css:125 |
| `color.hex-cc0000` | `#cc0000` | 5 | danger | src/main/webapp/css/common.css:83, src/main/webapp/css/common.css:90, src/main/webapp/css/common.css:91 …+1 |
| `color.hex-cccccc` | `#cccccc` | 2 | border | src/main/webapp/css/common.css:62, src/main/webapp/css/common.css:73 |
| `color.hex-d9d9d9` | `#d9d9d9` | 1 | border | src/main/webapp/css/admin.css:22 |
| `color.hex-dddddd` | `#dddddd` | 6 | border | src/main/webapp/css/common.css:44, src/main/webapp/css/common.css:100, src/main/webapp/css/common.css:101 …+3 |
| `color.hex-e0e0e0` | `#e0e0e0` | 4 | border | src/main/webapp/css/common.css:107, src/main/webapp/css/common.css:108, src/main/webapp/css/common.css:118 …+1 |
| `color.hex-e5e5e5` | `#e5e5e5` | 1 | border | src/main/webapp/css/admin.css:7 |
| `color.hex-e8e8e8` | `#e8e8e8` | 1 | secondary-hover | src/main/webapp/css/common.css:63 |
| `color.hex-eeeeee` | `#eeeeee` | 2 | surface-subtle | src/main/webapp/css/common.css:100, src/main/webapp/css/common.css:130 |
| `color.hex-efefef` | `#efefef` | 1 | surface-subtle | src/main/webapp/css/common.css:102 |
| `color.hex-f2f2f2` | `#f2f2f2` | 1 | surface-subtle | src/main/webapp/css/admin.css:6 |
| `color.hex-f4f4f4` | `#f4f4f4` | 2 | surface-subtle | src/main/webapp/css/common.css:107, src/main/webapp/css/common.css:127 |
| `color.hex-f5f5f5` | `#f5f5f5` | 2 | surface-subtle | src/main/webapp/css/common.css:62, src/main/webapp/css/common.css:144 |
| `color.hex-fff0f0` | `#fff0f0` | 1 | danger-surface | src/main/webapp/css/common.css:92 |
| `color.hex-ffffff` | `#ffffff` | 9 | surface | src/main/webapp/css/common.css:10, src/main/webapp/css/common.css:33, src/main/webapp/css/common.css:39 …+6 |

## タイポグラフィ（Typography）

| トークン | 値 | 使用数 | クラスタ | 出典 |
|---|---|---|---|---|
| `font.family.hiragino-kaku-gothic-pron` | `['Hiragino Kaku Gothic ProN', 'Meiryo', 'sans-serif']` | 1 | base-font | src/main/webapp/css/common.css:7 |
| `font.size.px-11` | `11px` | 1 | small-text | src/main/webapp/css/common.css:85 |
| `font.size.px-12` | `12px` | 6 | small-text | src/main/webapp/css/common.css:46, src/main/webapp/css/common.css:50, src/main/webapp/css/common.css:89 …+3 |
| `font.size.px-13` | `13px` | 1 | body-text | src/main/webapp/WEB-INF/jsp/admin/product-edit.jsp:54 |
| `font.size.px-14` | `14px` | 2 | body-text | src/main/webapp/css/common.css:8, src/main/webapp/css/common.css:54 |
| `font.size.px-16` | `16px` | 3 | heading-2 | src/main/webapp/css/common.css:26, src/main/webapp/css/common.css:37, src/main/webapp/css/common.css:113 |
| `font.size.px-20` | `20px` | 1 | heading-1 | src/main/webapp/css/common.css:18 |
| `font.weight.w-700` | `700` | 7 | bold | src/main/webapp/css/common.css:37, src/main/webapp/css/common.css:68, src/main/webapp/css/common.css:76 …+4 |

## 余白・角丸・罫線・影（Spacing, Radius, Borders and Shadow）

| トークン | 値 | 使用数 | クラスタ | 出典 |
|---|---|---|---|---|
| `border.width.px-1` | `1px` | 15 | hairline | src/main/webapp/css/admin.css:7, src/main/webapp/css/admin.css:22, src/main/webapp/css/common.css:44 …+12 |
| `border.width.px-2` | `2px` | 2 | emphasis-rule | src/main/webapp/css/common.css:22, src/main/webapp/css/common.css:113 |
| `border.width.px-5` | `5px` | 1 | accent-bar | src/main/webapp/css/admin.css:13 |
| `radius.px-12` | `12px` | 1 | pill-radius | src/main/webapp/WEB-INF/jsp/admin/product-edit.jsp:54 |
| `radius.px-3` | `3px` | 1 | control-radius | src/main/webapp/css/common.css:57 |
| `space.px-1` | `1px` | 1 | space-1 | src/main/webapp/css/common.css:86 |
| `space.px-12` | `12px` | 11 | space-12 | src/main/webapp/css/admin.css:21, src/main/webapp/css/common.css:66, src/main/webapp/css/common.css:96 …+8 |
| `space.px-16` | `16px` | 21 | space-16 | src/main/webapp/css/admin.css:8, src/main/webapp/css/admin.css:27, src/main/webapp/css/common.css:19 …+15 |
| `space.px-2` | `2px` | 2 | space-2 | src/main/webapp/css/common.css:136 |
| `space.px-20` | `20px` | 3 | space-20 | src/main/webapp/css/admin.css:20, src/main/webapp/css/common.css:78, src/main/webapp/WEB-INF/jsp/admin/product-edit.jsp:54 |
| `space.px-24` | `24px` | 7 | space-24 | src/main/webapp/css/admin.css:8, src/main/webapp/css/common.css:41, src/main/webapp/css/common.css:47 …+4 |
| `space.px-32` | `32px` | 2 | space-32 | src/main/webapp/css/common.css:41, src/main/webapp/css/common.css:145 |
| `space.px-4` | `4px` | 8 | control-padding-y | src/main/webapp/css/common.css:20, src/main/webapp/css/common.css:73, src/main/webapp/css/common.css:86 …+4 |
| `space.px-6` | `6px` | 7 | control-padding-y | src/main/webapp/css/common.css:55, src/main/webapp/css/common.css:73, src/main/webapp/css/common.css:87 …+4 |
| `space.px-8` | `8px` | 16 | space-8 | src/main/webapp/css/admin.css:14, src/main/webapp/css/common.css:34, src/main/webapp/css/common.css:41 …+13 |
| `space.px-80` | `80px` | 1 | space-80 | src/main/webapp/css/common.css:145 |

## 断片化（Fragmentation）

| クラスタ | 型 | メンバー | 提案 |
|---|---|---|---|
| border | color | #dddddd×6, #e0e0e0×4, #cccccc×2, #d9d9d9×1, #e5e5e5×1 | #dddddd（最多使用）に統合 |
| primary | color | #0066cc×6, #0a66c2×2, #1a73e8×1 | #0066cc（最多使用）に統合 |
| surface-subtle | color | #eeeeee×2, #f4f4f4×2, #f5f5f5×2, #efefef×1, #f2f2f2×1 | #eeeeee（最多使用）に統合 |
| text | color | #333333×4, #444444×2 | #333333（最多使用）に統合 |
| body-text | dimension | 14px×2, 13px×1 | 14px（最多使用）に統合 |
| control-padding-y | dimension | 4px×8, 6px×7 | 4px（最多使用）に統合 |
| small-text | dimension | 12px×6, 11px×1 | 12px（最多使用）に統合 |

## セマンティックトークン候補（Semantic Token Candidates）

| トークン | 参照先 | 値 | 説明 |
|---|---|---|---|
| `semantic.color.bg` | `color.hex-ffffff` | `#ffffff` | candidate — most-used member of cluster surface (1 member) |
| `semantic.color.border` | `color.hex-dddddd` | `#dddddd` | candidate — most-used member of cluster border (5 members) |
| `semantic.color.danger` | `color.hex-cc0000` | `#cc0000` | candidate — most-used member of cluster danger (1 member) |
| `semantic.color.danger-bg` | `color.hex-fff0f0` | `#fff0f0` | candidate — most-used member of cluster danger-surface (1 member) |
| `semantic.color.fg` | `color.hex-333333` | `#333333` | candidate — most-used member of cluster text (2 members) |
| `semantic.color.fg-faint` | `color.hex-aaaaaa` | `#aaaaaa` | candidate — most-used member of cluster text-faint (1 member) |
| `semantic.color.fg-muted` | `color.hex-666666` | `#666666` | candidate — most-used member of cluster text-muted (1 member) |
| `semantic.color.on-primary` | `color.hex-ffffff` | `#ffffff` | candidate — the second role of #ffffff (text on the primary blue: title bar, primary button, active step, current page); the raw token's cluster records its surface role only |
| `semantic.color.primary` | `color.hex-0066cc` | `#0066cc` | candidate — most-used member of cluster primary (3 members) |
| `semantic.color.primary-hover` | `color.hex-0052a3` | `#0052a3` | candidate — most-used member of cluster primary-hover (1 member) |
| `semantic.color.secondary-hover` | `color.hex-e8e8e8` | `#e8e8e8` | candidate — most-used member of cluster secondary-hover (1 member) |
| `semantic.color.success` | `color.hex-006600` | `#006600` | candidate — most-used member of cluster success (1 member) |
| `semantic.color.surface` | `color.hex-eeeeee` | `#eeeeee` | candidate — tie on usage broken by the shared component's use, then lexical order of cluster surface-subtle (5 members) |

## 部品のバリアント（Component Variants）

| ID | 名前 | バリアント | 状態 |
|---|---|---|---|
| UIC-001 | header.jspf | extraCss=admin.css（管理画面用スタイルを追加） | ログイン中（ログアウトリンクと氏名を表示）, 未ログイン（ログアウトリンクなし） |
| UIC-003 | button.tag | variant=primary, variant=secondary, type=submit（既定）\|button, name/value 指定あり | hover |
| UIC-006 | list-table | tfoot 合計行（common.css:102） | - |
| UIC-010 | form-row | fieldset.form-row（ラジオグループ＋legend、common.css:75-76）, login-box 内でラベル幅 100px（common.css:146）, admin-panel 内でラベル幅 120px（admin.css:17） | - |

## デザインシステムへの取り込み（Importing into a Design System）

```
/product:design-system --import=reports/before/legacy-ui-shop/ui-design-tokens.json --name=<name>
```

`/product:design-system` がこのファイルを DTCG スキーマに正規化する。`semantic.*` の候補はエイリアスに対応づけ、断片化したクラスタはそれぞれ統合の質問になる。
