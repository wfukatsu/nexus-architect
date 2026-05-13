---
date: 2026-05-13
topic: sample-ec-monolith
---

# サンプル EC モノリス — nexus-architect 検証用プロジェクト要件

## Summary

nexus-architect エージェントの全スキル（investigate → report）を検証するための、実際に動作する Spring Boot + JPA モノリス EC アプリケーションを `samples/ec-monolith/` に新規作成する。5 つのビジネスドメインを持ち、意図的な技術負債とセキュリティ課題を埋め込むことで、エージェントが何を検知・提案するかを検証可能にする。最終的に、エージェントが ScalarDB 2PC を用いたマイクロサービス移行設計を提案するデモシナリオとして機能する。

---

## Problem Frame

nexus-architect は legacy システムの分析・評価・再設計を行うエージェントだが、実際の顧客プロジェクトを使った検証は機密上困難であり、動作確認の標準シナリオが存在しない。スキルの出力品質を継続的に検証するためには、意図した問題を内包した既知のコードベースが必要である。

また、ScalarDB の価値を潜在顧客に示す際、「既存モノリスをマイクロサービスへ移行するとき、分散トランザクションをどう解決するか」というシナリオが最も説得力を持つが、そのためのデモ素材が現状存在しない。

---

## Actors

- A1. **Developer（nexus-architect ユーザー）** — サンプルプロジェクトを `/architect:pipeline` に渡し、エージェントの出力を評価する
- A2. **nexus-architect エージェント** — サンプルプロジェクトのコードを分析・評価・設計する対象システムとして扱う
- A3. **EC 顧客（サンプルアプリ内のユーザー）** — REST API を通じて商品閲覧・注文・決済を行う（サンプルアプリのドメイン主体）

---

## Key Flows

- F1. **エージェント検証フロー**
  - **Trigger:** Developer が `samples/ec-monolith/` に対して `/architect:pipeline` を実行する
  - **Actors:** A1, A2
  - **Steps:**
    1. `/architect:investigate` がプロジェクト構造・技術スタック・DDDレディネスを分析する
    2. `/architect:investigate-security` が OWASP Top 10 該当箇所を検出する
    3. `/architect:analyze` がユビキタス言語・ドメインマッピングを生成する
    4. `/architect:evaluate-mmi` と `/architect:evaluate-ddd` が並列実行され、スコアを算出する
    5. `/architect:redesign` → `/architect:design-microservices` → `/architect:design-scalardb` が設計を生成する
    6. レビュースキル群が並列実行され、`/architect:review-synthesizer` が統合する
    7. `/architect:report` が HTML レポートを生成する
  - **Outcome:** `reports/` 配下に全フェーズの成果物が生成され、Developer が品質を確認できる
  - **Covered by:** R20, R21

- F2. **注文確定フロー（ScalarDB デモ対象）**
  - **Trigger:** 顧客が「注文確定」を POST する
  - **Actors:** A3
  - **Steps:**
    1. OrderService が在庫確認を呼び出す（同一トランザクション内で InventoryRepository を直接呼ぶ — 意図的な設計問題）
    2. 在庫引き当て（Inventory テーブル UPDATE）
    3. 決済処理（Payment テーブル INSERT、外部決済 API はモック）
    4. 注文レコード作成（Order テーブル INSERT）
    5. メール通知（同一メソッド内で SMTP 送信 — 意図的な関心事の混在）
  - **Outcome:** 注文・在庫・決済が 1 つのモノリシック DB トランザクションで完結する（モノリス時点）
  - **Escape path:** 在庫不足時は例外をスローするが、ロールバック処理が不完全（意図的な技術負債）
  - **Covered by:** R6, R9, R17

---

## Requirements

**サンプルアプリケーション本体**

- R1. Java 17 / Spring Boot 3.x + Spring Data JPA + Hibernate を使用した Gradle プロジェクトとして `samples/ec-monolith/` に配置する
- R2. MySQL 8.0 を `samples/ec-monolith/docker-compose.yml` で起動し、`./gradlew bootRun` 一発でアプリが立ち上がる
- R3. REST API エンドポイントをすべて提供し、`springdoc-openapi` による Swagger UI（`/swagger-ui.html`）を有効にする
- R4. 5 つのバウンデッドコンテキスト（User/Auth、Catalog、Inventory、Order、Payment）が単一 Spring アプリ内に存在し、それぞれ独立したパッケージ階層（`com.example.ec.[domain]`）を持つ
- R5. `DataLoader`（`ApplicationRunner`）が起動時にサンプルデータ（商品 10 件、ユーザー 3 名、過去注文 5 件）を自動投入する

**検知可能な技術負債**

- R6. `OrderService` が在庫引き当て・決済処理・メール通知・ポイント付与のすべてを単一クラス内で実装する（God Service、実装 500 行以上）
- R7. 注文履歴取得 API（`GET /orders`）で JPA の lazy loading を意図的に使い、N+1 クエリ問題が発生するコードを含む
- R8. `@RestController` が Entity オブジェクトをそのまま JSON レスポンスとして返す（DTO パターン未使用、`@JsonIgnore` 漏れにより循環参照またはパスワードハッシュが露出するリスク）
- R9. `order` パッケージが `inventory` パッケージのリポジトリを直接 import し、`inventory` パッケージが `order` パッケージのエンティティを参照する（循環依存）
- R10. データベース接続 URL・管理者パスワード・メールサーバー認証情報が `application.properties` ではなくソースコード中に定数としてハードコードされている
- R11. Entity クラス（`User`、`Product`、`Order`）がすべてゲッター・セッターのみを持ち、ビジネスルールを一切含まない（貧血ドメインモデル）

**検知可能なセキュリティ課題（OWASP Top 10 対応）**

- R12. 商品検索エンドポイント（`GET /products?keyword=`）で `@Query` native query に文字列結合を使用し、SQL インジェクションが可能な実装とする（A03:2021）
- R13. 注文詳細エンドポイント（`GET /orders/{id}`）がログイン中ユーザーの所有権を確認せず、任意の注文 ID でアクセスできる（IDOR、A01:2021）
- R14. ユーザーパスワードを salt なし MD5 でハッシュ化して保存する（弱い暗号、A02:2021）
- R15. 決済処理のログに `カード番号末尾4桁` + `注文金額` + `ユーザーID` を INFO レベルで出力する（機密情報ログ、A09:2021）
- R16. 管理者用エンドポイント（`/admin/**`）が Spring Security の設定ミスにより、未認証でアクセスできる（A07:2021）

**ドメイン分割可能性（移行設計の前提）**

- R17. 各ドメインのデータが同一 MySQL スキーマ内の別テーブルに格納されるが、ドメイン間の JOIN は `OrderService` のロジックのみが行い、テーブルレベルでは外部キーを最小限に抑える
- R18. `README.md` に「モノリスとしての現状」と「マイクロサービス移行後の想定構成（Order:MySQL + Inventory:Cassandra + Payment:PostgreSQL → ScalarDB 2PC）」のアーキテクチャ図（Mermaid）を記載する

---

## Acceptance Examples

- AE1. **Covers R12.** `GET /products?keyword=' OR '1'='1` を送信したとき、全商品が返却される（SQL インジェクション成功を意図的に示す）。
- AE2. **Covers R13.** ユーザー A でログインし、ユーザー B が作成した注文 ID を `GET /orders/{B_order_id}` でリクエストしたとき、403 ではなく注文内容が返却される。
- AE3. **Covers R7.** `GET /orders`（10 件）のリクエスト時、JPA が発行する SQL クエリが 11 件以上（1 + N）になることをログで確認できる。
- AE4. **Covers R6.** `OrderService.placeOrder()` メソッドが 500 行以上存在し、在庫・決済・メール・ポイントの処理を同一メソッドチェーンで呼ぶ。

---

## Success Criteria

- `/architect:pipeline samples/ec-monolith/` が最後まで正常完了し、`reports/00_summary/full-report.html` が生成される
- `investigate-security` の出力に R12〜R16 の 5 項目のうち少なくとも 4 項目が「重大」または「高」として記録される
- `evaluate-ddd` の出力が「戦術的設計」スコアで 3.0 以下（貧血モデル・God Service を問題として検出する）を示す
- `design-scalardb` の出力が Order（MySQL）・Inventory（Cassandra 相当）・Payment（PostgreSQL 相当）を ScalarDB 2PC で統合する設計を含む
- Developer が `README.md` の手順だけを見てサンプルアプリを 10 分以内に起動できる

---

## Scope Boundaries

- フロントエンド UI は含めない（REST API + Swagger UI のみ）
- 実際の外部決済ゲートウェイ（Stripe 等）との連携は含めない（ダミーの PaymentGateway クラスで代替）
- Kubernetes マニフェスト・本番インフラ設定は含めない
- ScalarDB を用いたマイクロサービス後の実装コードは含めない（エージェントの「設計出力」の検証が目的であり、移行後コードの生成は別タスク）
- テストコード（JUnit）は最小限（DataLoader とメイン実装のみ。エージェントが「テスト不足」を技術負債として検知できる状態にする）

---

## Key Decisions

- **Spring Boot + JPA を採用**: エージェントの出力（Spring Boot + ScalarDB）と技術スタックを揃えることで、移行前後の対応関係が明確になる
- **5 ドメイン構成**: Order + Inventory + Payment の 3 ドメインが ScalarDB 2PC の恩恵を受ける構図を作るため、最低限この 3 ドメインを分離した
- **意図的な技術負債の種類**: God Service・N+1・IDOR を必須とした。これらは nexus-architect が investigate/evaluate スキルで明確に検知すべき最重要パターンであるため
- **README に移行アーキテクチャ図を記載**: Developer が Agent 出力と手動で比較できるよう、期待される移行先構成を事前に文書化する

---

## Dependencies / Assumptions

- `samples/` ディレクトリが nexus-architect リポジトリ直下に新設される（git-ignored ではなくリポジトリに含める）
- Java 17 と Docker が Developer の実行環境にインストール済みであることを前提とする
- ScalarDB バージョンは 3.16.x（2026年5月時点の最新安定版）を Migration 設計の参照バージョンとする

---

## Outstanding Questions

### Resolve Before Planning

- なし（全主要決定事項はブレインストームで確定済み）

### Deferred to Planning

- [Affects R4][Technical] 5 ドメインのパッケージ構成の詳細（例：`com.example.ec.order.domain`・`com.example.ec.order.application` のような DDD 的サブパッケージを持つか、シンプルな `com.example.ec.order` フラットにするか）
- [Affects R6][Technical] God Service の実装密度をどう調整するか（500行の閾値を `OrderService` の一クラスで達成するか、複数の問題あるサービスに分散させるか）
- [Affects R12][Needs research] Spring Boot 3.x + `@Query` native query で文字列結合 SQL インジェクション脆弱性を意図的に作る最も自然な実装方法
