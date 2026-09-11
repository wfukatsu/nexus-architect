# Planted Defects (answer key)

The defects below are **intentional**. This sample exists so `/architect:analyze-ui` and
`/architect:evaluate-ux` can be scored against a known answer key; "fixing" any of them silently
breaks that measurement. If you change a file listed here, re-verify every `file:line` and update
`planted-defects.json` (the machine-readable source this table mirrors) in the same change. The
rest of the application is kept deliberately clean, so anything a skill reports that is not in this
list is a false positive worth looking at, not a known issue.

Line convention: for a logic block, `line` is the scriptlet opening line. For a role guard it is
the conditional, and for a markup defect it is the element. `route` is `null` when the defect lives
only in a stylesheet or script. `criterion` is `null` for the inventory-only categories
(`embedded-logic`, `role-guard`, `client-only-validation`).

| ID | Category | Location | Route | Criterion | Description |
|----|----------|----------|-------|-----------|-------------|
| PD-01 | embedded-logic | `WEB-INF/jsp/order/entry.jsp:10` | `/order/entry` | — | Members-only 10% discount computed in a scriptlet and stored in the session for the next step |
| PD-02 | embedded-logic | `WEB-INF/jsp/order/confirm.jsp:8` | `/order/confirm` | — | Tax and total computed in a scriptlet; the servlet persists them without recomputing |
| PD-03 | embedded-logic | `js/cart.js:13` | — | — | Line amount (price x quantity) calculated client-side, duplicating `CartLine.getLineTotal()` |
| PD-04 | role-guard | `WEB-INF/jsp/menu.jsp:18` | `/menu` | — | Scriptlet role check hides the admin link |
| PD-05 | role-guard | `WEB-INF/jsp/admin/product-edit.jsp:11` | `/admin/products/edit` | — | The only admin check is in the JSP; servlet and filter check login only |
| PD-06 | client-only-validation | `js/validation.js:16` | `/order/entry` | — | Postal code `NNN-NNNN` checked only in jQuery; `OrderEntryServlet.java:63` checks presence only |
| PD-07 | unlabeled-input | `WEB-INF/jsp/product/search.jsp:11` | `/products` | WCAG 1.3.1 | Keyword input with placeholder only |
| PD-08 | unlabeled-input | `WEB-INF/jsp/order/entry.jsp:62` | `/order/entry` | WCAG 1.3.1 | Phone input next to visible text, no `<label for>` |
| PD-09 | missing-alt | `WEB-INF/jsp/product/search.jsp:39` | `/products` | WCAG 1.1.1 | Product thumbnail without `alt` |
| PD-10 | low-contrast | `WEB-INF/jsp/cart.jsp:40` | `/cart` | WCAG 1.4.3 | Notes text `#aaaaaa` on white (`common.css:125`), about 2.3:1 |
| PD-11 | missing-lang | `WEB-INF/jsp/login.jsp:5` | `/login` | WCAG 3.1.1 | Standalone page, `<html>` without `lang` |
| PD-12 | destructive-without-confirmation | `WEB-INF/jsp/cart.jsp:30` | `/cart` | H5 | Remove-line button submits immediately, no confirmation or undo |
| PD-13 | destructive-without-confirmation | `WEB-INF/jsp/admin/product-edit.jsp:56` | `/admin/products/edit` | H5 | Delete product submits immediately |
| PD-14 | vague-error-message | `WEB-INF/jsp/admin/product-edit.jsp:25` | `/admin/products/edit` | H9 | Generic "エラーが発生しました" with no field or cause |
| PD-15 | inconsistent-button | `WEB-INF/jsp/admin/product-edit.jsp:54` | `/admin/products/edit` | H4 | Save button built with inline styles instead of `button.tag` |
| PD-16 | inconsistent-color | `css/admin.css:13` | — | H4 | Primary blue as `#0066cc`, `#06c`, `#0a66c2` and inline `#1a73e8` |
| PD-17 | inconsistent-color | `css/common.css:102` | — | H4 | Near-identical grays (`#eeeeee`/`#efefef`/`#f4f4f4`/`#f5f5f5`, `#dddddd`/`#ddd`/`#e0e0e0`, `#333`/`#444`) |
| PD-18 | label-drift | `WEB-INF/jsp/product/detail.jsp:26` | `/products/detail` | H4 | "カートに入れる" here vs "カートに追加" on search results (`messages_ja.properties:12`) |
| PD-19 | dead-end | `WEB-INF/jsp/order/complete.jsp:21` | `/order/complete` | H3 | No link or button anywhere on the page; browser back only |
| PD-20 | orphan-screen | `help.jsp:1` | `/help.jsp` | H10 | FAQ page nothing links to; reachable only by typing the URL |
| PD-21 | redundant-input | `WEB-INF/jsp/order/entry.jsp:66` | `/order/entry` | H7 | Email asked again although the logged-in user's email is known |

All locations are relative to `src/main/webapp/`.
