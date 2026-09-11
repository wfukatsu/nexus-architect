# legacy-ui-shop

A small, runnable **legacy JSP + jQuery** web application (a domestic B2B office-supply shop, UI in
Japanese). It is a test fixture for the UI-analysis skills: `/architect:analyze-ui` extracts screens,
inputs/outputs, actions, transitions, role guards, UI-embedded business logic, components and design
tokens, and `/architect:evaluate-ux` scores Nielsen heuristics H1–H10, WCAG 2.2 AA, task efficiency,
consistency and navigation.

The code contains **deliberately planted defects**, and the answer key that lists them is
[`planted-defects.json`](planted-defects.json) (human-readable view:
[`planted-defects.md`](planted-defects.md)). Use it to check a skill's recall. The defects are
intentional, so do not fix them. They are not listed here, so that reading this README does not
give them away.

## Run

Requires Java 17+. No database or external service is needed. Everything is kept in memory and lost
on restart.

```bash
./gradlew run                 # serves http://localhost:8080/login
PORT=18080 ./gradlew run      # any other port
```

| User ID | Password | Role | Notes |
|---------|----------|------|-------|
| `customer1` | `pass1` | customer | premium member (member discount applies) |
| `admin1` | `pass1` | admin | product maintenance |

Stop it with Ctrl+C. `Main` starts an embedded Tomcat that serves `src/main/webapp` as the web
application root and mounts the compiled classes at `/WEB-INF/classes`, so `@WebServlet` /
`@WebFilter` are discovered the same way as in a WAR. Tomcat's work directory is `build/tomcat`.

## Screens

| # | URL | View | Title | Purpose |
|---|-----|------|-------|---------|
| 1 | `/login` | `WEB-INF/jsp/login.jsp` | ログイン | User ID and password form (standalone page, no common header) |
| 2 | `/menu` | `WEB-INF/jsp/menu.jsp` | メニュー | Links to product search and the cart, plus product maintenance for admins; account info |
| 3 | `/products` | `WEB-INF/jsp/product/search.jsp` | 商品検索 | Keyword and category search, results table, pager (labels from the resource bundle) |
| 4 | `/products/detail?id=` | `WEB-INF/jsp/product/detail.jsp` | 商品詳細 | Product info, quantity, add to cart |
| 5 | `/cart` | `WEB-INF/jsp/cart.jsp` | ショッピングカート | Cart lines, remove per line, proceed to order |
| 6 | `/order/entry` | `WEB-INF/jsp/order/entry.jsp` | ご注文情報の入力 | Shipping name, postal code, address, phone, email, payment method, notes; subtotal and discount |
| 7 | `/order/confirm` | `WEB-INF/jsp/order/confirm.jsp` | ご注文内容の確認 | Order lines, subtotal, discount, tax, total; confirm |
| 8 | `/order/complete` | `WEB-INF/jsp/order/complete.jsp` | ご注文完了 | Order number |
| 9 | `/admin/products/edit?id=` | `WEB-INF/jsp/admin/product-edit.jsp` | 商品編集 | Edit name, price, stock and category; save and delete (no `id` = register a new product) |
| 10 | `/help.jsp` | `help.jsp` (outside `WEB-INF`) | よくあるご質問 | FAQ |

Every URL except `/login` and static assets requires a logged-in session (`LoginFilter`).

## Layout

```
src/main/java/com/example/shop/
  Main.java                    embedded Tomcat bootstrap
  filter/LoginFilter.java      @WebFilter("/*"): redirects to /login without a session user
  web/*Servlet.java            one @WebServlet per URL above, plus /logout
  model/                       Product, User, Cart, CartLine, OrderForm, Order
  repo/ShopData.java           in-memory products, users and orders
src/main/resources/
  messages.properties          default (fallback) labels for the search screen
  messages_ja.properties       Japanese labels (UTF-8); the locale is fixed to ja in web.xml
src/main/webapp/
  WEB-INF/web.xml              encoding, JSTL fmt bundle/locale, session and JSP config
  WEB-INF/jsp/                 screen views (see table)
  WEB-INF/jspf/header.jspf     title bar, user name, logout link; opens <html lang="ja">
  WEB-INF/jspf/footer.jspf     footer; closes the document
  WEB-INF/tags/button.tag      standard button, variant="primary|secondary"
  WEB-INF/tags/pager.tag       previous / page numbers / next
  css/common.css               shared styles
  css/admin.css                maintenance screen styles
  js/validation.js             order entry form checks (jQuery)
  js/cart.js                   cart screen helpers (jQuery)
  js/lib/jquery-3.7.1.min.js   vendored jQuery (no CDN references)
  images/products/*.svg        placeholder product images
  help.jsp                     FAQ page
```

Labels are hard-coded in the JSPs except on the product search screen, which reads them from the
resource bundle through JSTL `<fmt:message>`. Views use scriptlets, JSTL 3.0 (`jakarta.tags.*`)
and EL, the way a long-lived application accumulates them.

## Version decisions

Resolved on 2026-09-11 per `rules/dependency-versions.md`. Nothing was recalled from memory.

| Dependency | Chosen | Latest stable | Released | Source | Why this one | Rejected |
|------------|--------|---------------|----------|--------|--------------|----------|
| `org.apache.tomcat.embed:tomcat-embed-core` | 11.0.25 | 11.0.25 (on Maven Central) | 2026-08-12 | https://repo1.maven.org/maven2/org/apache/tomcat/embed/tomcat-embed-core/maven-metadata.xml | Newest release published to Central on the 11.0 line (supported, not EOL, minimum Java 17 per https://endoflife.date/api/tomcat.json). Servlet 6.1 / JSP 4.0 / EL 6.0 (Jakarta EE 11) | 11.0.26 (announced 2026-09-09 but not yet on Central, where the artifact returns 404); 10.1.x (older spec line; 11.0 fits Java 17) |
| `org.apache.tomcat.embed:tomcat-embed-jasper` | 11.0.25 | 11.0.25 | 2026-08-12 | https://repo1.maven.org/maven2/org/apache/tomcat/embed/tomcat-embed-jasper/maven-metadata.xml | Must match tomcat-embed-core exactly. Brings tomcat-embed-el and ECJ | none |
| `jakarta.servlet.jsp.jstl:jakarta.servlet.jsp.jstl-api` | 3.0.2 | 3.0.2 | 2024-08-22 | https://repo1.maven.org/maven2/jakarta/servlet/jsp/jstl/jakarta.servlet.jsp.jstl-api/maven-metadata.xml | Jakarta Standard Tag Library 3.0, the version in Jakarta EE 11. Its transitive `jakarta.servlet-api` 6.0 / `jakarta.el-api` 5.0 are excluded in `build.gradle` because Tomcat 11 ships 6.1 / 6.0 | 3.1.0-M2, 3.1.0-M1 (prereleases; `<release>` in the metadata points at the milestone) |
| `org.glassfish.web:jakarta.servlet.jsp.jstl` | 3.0.1 | 3.0.1 | 2022-09-29 | https://repo1.maven.org/maven2/org/glassfish/web/jakarta.servlet.jsp.jstl/maven-metadata.xml | Reference implementation of JSTL 3.0 (`jakarta.tags.*` URIs). Newest release, and its API dependencies are `provided` | none |
| jQuery | 3.7.1 | 3.7.1 (3.x line) | 2023-08-28 | https://code.jquery.com/jquery-3.7.1.min.js (downloaded and vendored). Version list from `https://registry.npmjs.org/jquery` (npm `dist-tags`) | Newest stable 3.x, as the fixture calls for a jQuery 3 codebase. `jquery-3.7.2.min.js` returns 404 on code.jquery.com | 4.0.0 (npm `latest`, but a different major); 4.0.0-rc.2 (prerelease) |
| Gradle wrapper | 8.6 | not re-resolved | — | copied from `samples/scalardb-transaction-tests/gradle/wrapper/` | Reuses the repository's existing wrapper so both samples build the same way. Supports Java 17 | none |

## Verifying the sample still works

Start it with `PORT=18080 ./gradlew run`, log in with curl (keep the cookie jar), fetch every URL in
the table, and walk the order flow with POSTs: `/cart` (`action=add`), then `/order/entry`, then
`/order/confirm`, then `/order/complete`. Every screen returns HTTP 200 with its title above. After
editing any file listed in `planted-defects.json`, re-check that each `line` still points at its
construct.
