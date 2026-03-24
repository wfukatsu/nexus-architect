# ScalarDB アプリケーション開発ガイド

本ガイドでは、ScalarDB アプリケーションの構築、レビュー、保守を支援する 11 の ScalarDB 開発スキルについて説明します。

## 概要

```
/scalardb:model        スキーマを設計する
        ↓
/scalardb:config       設定ファイルを生成する
        ↓
/scalardb:scaffold     スタータープロジェクトを生成する
        ↓
/scalardb:build-app    完全なアプリケーションを構築する
        ↓
/scalardb:review-code  正確性をレビューする
```

## スキル

### スキーマ設計: `/scalardb:model`

ScalarDB スキーマの設計をステップバイステップで案内するインタラクティブウィザードです。

**機能:**
1. ドメインエンティティと属性を収集する
2. アクセスパターンと一般的なクエリを特定する
3. パーティションキーを推奨する（均等分散のガイダンス付き）
4. クラスタリングキーとソート方向を推奨する
5. セカンダリインデックスを提案する（オーバーヘッドの警告付き）
6. `schema.json` と、オプションで `schema.sql` を生成する

**使い方:**
```bash
/scalardb:model
```

**出力:** `schema.json`（Schema Loader 形式）および/または `schema.sql`（DDL 形式）

**提供される主なガイダンス:**
- パーティションキーのアンチパターン（ホットパーティション、単調増加する値）
- CRUD API は JOIN をサポートしない — シングルテーブルアクセス向けにスキーマを設計する必要がある
- JOIN を使わないクエリのための非正規化戦略
- データ型の選択（BOOLEAN, INT, BIGINT, FLOAT, DOUBLE, TEXT, BLOB, DATE, TIME, TIMESTAMP, TIMESTAMPTZ）

---

### 設定: `/scalardb:config`

任意のデプロイメント/API/トランザクションモードの組み合わせに対して正しい設定ファイルを生成します。

**機能:**
1. デプロイメントモードを確認する: Core または Cluster
2. API スタイルを確認する: CRUD または JDBC/SQL
3. トランザクションモードを確認する: 1PC または 2PC
4. データベースバックエンドを確認する: MySQL, PostgreSQL, Cassandra, DynamoDB, Cosmos DB, Oracle, SQL Server
5. `database.properties` または `scalardb-sql.properties` と `build.gradle` の依存関係を生成する

**使い方:**
```bash
/scalardb:config
```

**6 つのインターフェースの組み合わせ:**

| # | デプロイメント | API | トランザクション | ユースケース |
|---|-----------|-----|-------------|----------|
| 1 | Core | CRUD | 1PC | 開発、単一 DB |
| 2 | Core | CRUD | 2PC | 単一アプリからの複数 DB |
| 3 | Cluster | CRUD | 1PC | 本番環境、単一 DB |
| 4 | Cluster | CRUD | 2PC | 本番環境、複数サービス |
| 5 | Cluster | JDBC | 1PC | 本番環境、SQL 使用 |
| 6 | Cluster | JDBC | 2PC | 本番環境、複数サービス SQL |

---

### プロジェクトスキャフォールド: `/scalardb:scaffold`

6 つのインターフェースの組み合わせのいずれかに対応した、完全に実行可能なスタータープロジェクトを生成します。

**機能:**
開発を開始するために必要なすべてのファイルを生成します:
- `build.gradle` — 依存関係とプラグイン
- `database.properties` — 設定
- `schema.json` / `schema.sql` — スキーマ定義
- `src/main/java/sample/Sample.java` — CRUD 操作を含むサービスクラス
- `docker-compose.yml` — ローカルデータベースのセットアップ
- `README.md` — セットアップと実行手順

**使い方:**
```bash
/scalardb:scaffold
```

**コード品質の強制事項:**
- Insert/Upsert/Update を使用する（非推奨の Put は使わない）
- すべての操作でビルダーパターンを使用する
- すべての操作で明示的にネームスペースとテーブルを指定する
- 正しい例外キャッチ順序
- 指数バックオフによるリトライロジック
- 読み取り専用トランザクションでもコミットする

---

### アプリケーションビルダー: `/scalardb:build-app`

ドメインの説明から完全な ScalarDB アプリケーションを構築します。

**機能:**
1. 要件を理解する（エンティティ、リレーション、アクセスパターン）
2. 適切なキーとインデックスを持つデータモデルを設計する
3. 設定ファイルとビルドファイルを生成する
4. 完全な CRUD、例外処理、リトライロジックを持つサービスレイヤーを作成する
5. ローカル開発環境をセットアップする
6. 統合ポイントを提供する（CLI または REST コントローラー）

**使い方:**
```bash
/scalardb:build-app
# ドメインを説明してください: 「注文、顧客、在庫を持つ EC システムが必要です」
```

---

### CRUD 操作ガイド: `/scalardb:crud-ops`

すべての CRUD API 操作のクイックリファレンスとコード例です。

**対象:**
- **Get** — プライマリキーまたはセカンダリインデックスによる取得
- **Scan** — パーティションスキャン、範囲スキャン、全スキャン、インデックススキャン
- **Insert** — 新規レコードのみ（既存の場合は失敗）
- **Upsert** — 挿入または更新
- **Update** — 既存レコードのみ、オプションの条件付き
- **Delete** — プライマリキーによる削除
- **Batch** — `mutate()` による複数操作の原子的実行
- **キー構築** — 単一キーと複合キー

**使い方:**
```bash
/scalardb:crud-ops
# 質問例: 「範囲条件付きスキャンはどうやりますか?」
```

---

### JDBC/SQL 操作ガイド: `/scalardb:jdbc-ops`

JDBC/SQL 操作のクイックリファレンスとコード例です。

**対象:**
- WHERE, ORDER BY, LIMIT 付き SELECT
- INSERT, UPSERT, UPDATE, DELETE
- JOIN（INNER, LEFT, RIGHT — FULL は不可）
- 集約関数（COUNT, SUM, AVG, MIN, MAX）
- GROUP BY / HAVING
- SQL 文による 2PC（PREPARE, VALIDATE, COMMIT）
- エラーコード 301（UnknownTransactionStatusException）の処理

**ドキュメント化された SQL の制限事項:**
- DISTINCT、サブクエリ、CTE、ウィンドウ関数は非対応
- FULL OUTER JOIN、UNION、INTERSECT、EXCEPT は非対応
- JOIN 述語はプライマリキーまたはセカンダリインデックスを参照する必要がある
- WHERE は DNF または CNF でなければならない

**使い方:**
```bash
/scalardb:jdbc-ops
# 質問例: 「集約付き LEFT JOIN はどうやりますか?」
```

---

### 例外処理: `/scalardb:error-handler`

例外処理コードの生成と、既存コードの正確性レビューを行います。

**2 つのモード:**
1. **生成** — 任意のインターフェースの組み合わせに対して、リトライロジック付きの完全な try/catch パターンを生成する
2. **レビュー** — 16 カテゴリの例外処理の問題点について既存コードを検証する

**強制される重要なパターン:**
- キャッチ順序: `CrudConflictException` を `CrudException` の前に（具体的な例外を親より先に）
- `UnknownTransactionStatusException`: リトライやロールバックをしない
- 読み取り専用トランザクションでも必ずコミットする
- catch ブロックでは必ずロールバックする（エラーコード 301 を除く）
- 指数バックオフによるリトライ（最大 3〜5 回）
- すべての例外からトランザクション ID をログに記録する

**使い方:**
```bash
/scalardb:error-handler
# 選択: 「例外処理コードを生成する」または「既存のコードをレビューする」
```

---

### コードレビュー: `/scalardb:review-code`

16 のチェックカテゴリにわたって Java コードの ScalarDB 正確性をレビューします。

**チェックカテゴリ:**

| 重要度 | チェック内容 |
|----------|--------|
| **クリティカル** | 例外キャッチ順序、トランザクションライフサイクル、UnknownTransactionStatusException の処理 |
| **メジャー** | 非推奨 API の使用（Put）、ビルダーパターンの準拠、Result の処理、リトライロジック |
| **マイナー** | 設定の完全性、スキーマの妥当性、Java ベストプラクティス |
| **JDBC 固有** | setAutoCommit、リソース管理、SQL インジェクション、エラーコード 301、2PC プロトコル |

**使い方:**
```bash
/scalardb:review-code
# Java ファイルを指定するか、コードを貼り付けてください
```

---

### ローカル環境: `/scalardb:local-env`

Docker Compose を使用してローカル開発環境をセットアップします。

**対応バックエンド:** MySQL, PostgreSQL, Cassandra, DynamoDB Local, マルチストレージ（MySQL + Cassandra）

**使い方:**
```bash
/scalardb:local-env
# データベースバックエンドを選択してください
```

**出力:** ヘルスチェック、ボリューム管理、スキーマロードコマンドを含む `docker-compose.yml`

---

### ドキュメント検索: `/scalardb:docs`

ScalarDB ドキュメントを検索し、コード例付きの回答を提供します。

**使い方:**
```bash
/scalardb:docs
# 質問例: 「クロスパーティションスキャンの設定方法は?」
```

**ソース:** 公式ドキュメント（scalardb.scalar-labs.com）+ ローカル参照ファイル

---

### マイグレーションアドバイザー: `/scalardb:migrate`

インターフェースの組み合わせ間のマイグレーションを具体的な差分付きでガイドします。

**対応パス:**
- Core → Cluster（依存関係、設定、スキーマローダーの変更）
- CRUD → JDBC/SQL（完全なコード書き換えガイド）
- 1PC → 2PC（新しい例外タイプ、prepare/validate/commit）

**使い方:**
```bash
/scalardb:migrate
# 説明例: 「Core+CRUD+1PC から Cluster+JDBC+2PC へ移行する必要があります」
```

---

## ルール（常時有効なガイダンス）

これらのルールは自動的に読み込まれ、ScalarDB コードを操作するたびにガイダンスを提供します:

| ルール | 主な内容 |
|------|-------------|
| `scalardb-exception-handling` | キャッチ順序、リトライロジック、UnknownTransactionStatusException |
| `scalardb-crud-patterns` | ビルダーパターン、非推奨の Put、キー構築、Result の処理 |
| `scalardb-jdbc-patterns` | setAutoCommit、PreparedStatement、エラーコード 301、JOIN/集約構文 |
| `scalardb-2pc-patterns` | コーディネーター/パーティシパントプロトコル、リクエストルーティング、グループコミット |
| `scalardb-config-validation` | ストレージ別の必須プロパティ、contact points 形式、クロスパーティションスキャン |
| `scalardb-schema-design` | パーティションキー設計、クラスタリングキー、アンチパターン、データ型 |
| `scalardb-java-best-practices` | スレッドセーフティ、トランザクションライフサイクル、SLF4J、try-with-resources |

## 参照ドキュメント

`skills/common/references/` に配置:

| ドキュメント | 内容 |
|----------|---------|
| `api-reference.md` | 完全な ScalarDB API（TransactionManager、CRUD 操作、Result、Key、Conditions） |
| `interface-matrix.md` | 6 つのインターフェースの組み合わせと意思決定ガイド、依存関係、設定、コードパターン |
| `exception-hierarchy.md` | 例外ツリー、判断フローチャート、リトライパターン、JDBC エラーコードマッピング |
| `sql-reference.md` | SQL 文法（DDL、DML、TCL、DCL）、JOIN ルール、集約関数、制限事項 |
| `schema-format.md` | JSON および SQL スキーマ形式、データ型、Schema Loader コマンド |
| `code-patterns/` | 6 つのインターフェースの組み合わせすべての完全な動作サンプル |
