# データベースマイグレーションガイド

このガイドでは、Oracle、MySQL、PostgreSQL データベースの ScalarDB へのマイグレーションを自動化する 4 つのデータベースマイグレーションスキルについて説明します。

## 概要

```
/architect:migrate-database          統合エントリポイント（DB タイプを自動検出）
        ↓
┌───────────────────┬───────────────────┬───────────────────┐
│  migrate-oracle   │  migrate-mysql    │ migrate-postgresql │
├───────────────────┼───────────────────┼───────────────────┤
│ 1. Connect & Test │ 1. Connect & Test │ 1. Connect & Test │
│ 2. Extract Schema │ 2. Extract Schema │ 2. Extract Schema │
│ 3. Generate Report│ 3. Generate Report│ 3. Generate Report│
│ 4. Migration Plan │ 4. Migration Plan │ 4. Migration Plan │
│ 5. AQ Integration │ 5. SP/Trigger→Java│ 5. SP/Trigger→Java│
│ 6. SP/Trigger→Java│                   │                   │
└───────────────────┴───────────────────┴───────────────────┘
```

## クイックスタート

```bash
# 統合エントリポイント（どのデータベースか質問されます）
/architect:migrate-database

# または、特定のデータベースに直接アクセス
/architect:migrate-oracle
/architect:migrate-mysql
/architect:migrate-postgresql
```

スキルは対話形式で接続情報を確認した後、サブエージェントを使用してマイグレーションパイプライン全体を自動的に実行します。

## 動作の仕組み

### 2 フェーズアーキテクチャ

**フェーズ A: 対話型設定（メインコンテキスト）**
- 設定ファイル（`.claude/configuration/databases.env`）を検出または作成
- 接続情報を確認: ホスト、ポート、データベース/サービス、ユーザー名、パスワード
- スキーマ名、出力ディレクトリ、オプションを確認
- 出力ディレクトリを作成

**フェーズ B: サブエージェント処理（独立したコンテキスト）**
各ステップはコンテキストウィンドウを保持するために独自のサブエージェントで実行されます:

| ステップ | サブエージェント | 処理内容 |
|------|----------|-------------|
| 1 | 接続テスター | DB に接続し、アクセスを検証し、バージョンを取得 |
| 2 | スキーマ抽出器 | Python スクリプトを実行してスキーマ全体を JSON として抽出 |
| 3 | レポート生成器 | 生の JSON を読みやすい Markdown レポートに変換 |
| 4 | マイグレーション分析器 | 互換性を分析し、複雑度を計算し、マイグレーション計画を生成 |
| 5 | AQ マイグレーター（Oracle のみ） | トリガー/SP を Oracle AQ + Java コンシューマに変換 |
| 6 | SP/トリガーマイグレーター | ストアドプロシージャ/トリガーを Java サービスクラスに変換 |

### エラーの連鎖

ステップが失敗した場合、依存する下流のステップのみがスキップされます:
- 接続失敗 → すべて停止
- 抽出失敗 → すべて停止（ただし接続は検証済み）
- レポート失敗 → 生の JSON はディスクに保持
- マイグレーション分析失敗 → AQ + SP マイグレーションは引き続き実行
- AQ 失敗 → SP マイグレーションは引き続き実行

## スキルの詳細

### `/architect:migrate-database`

マイグレーション対象のデータベースを確認し、適切なスキルに委譲する統合ルーターです。

```bash
/architect:migrate-database
# → "Which database are you migrating? Oracle / MySQL / PostgreSQL"
```

---

### `/architect:migrate-oracle`

6 つのサブエージェントを使用した Oracle から ScalarDB への完全なマイグレーションパイプラインです。

**スキーマ抽出**の対象:
- テーブル、カラム、パーティション、LOB カラム、制約
- インデックス（B-tree、ビットマップ、ファンクションベース）
- ビュー（標準およびマテリアライズド）
- PL/SQL オブジェクト（プロシージャ、ファンクション、パッケージ、トリガー）
- シーケンス、シノニム、データベースリンク、スケジューラジョブ
- オブジェクト型、コレクション、型依存関係
- Oracle AQ オブジェクト（キュー、キューテーブル、サブスクライバ）
- セキュリティ（オブジェクト/システム/ロール権限、VPD/FGA ポリシー）
- オブジェクト依存関係とマイグレーション順序

**マイグレーション分析**の内容:
- データ型マッピング（Oracle → ScalarDB）
- 複雑度スコアリング（4 次元にわたる 0-10 スケール）
- ステップバイステップのマイグレーション計画
- ScalarDB SQL 制約の影響評価

**Oracle AQ 統合**（Oracle 固有）:
- トリガーとストアドプロシージャをイベント駆動アーキテクチャに変換
- Oracle AQ SQL を生成: ペイロード型、キューテーブル、キュー、エンキュー SP、新規トリガー
- ScalarDB Transaction API を使用した Java コンシューマを生成
- 例外分類（RETRIABLE / NON_RETRIABLE / UNKNOWN_TX_STATE）
- Upsert パターンを使用したべき等コンシューマ設計

**SP/トリガーから Java への変換**（17 の機能カテゴリ）:
- 変数、カーソル、制御フロー、例外処理
- OLD/NEW 行アクセス、CRUD 操作、条件付き書き込み
- サブクエリ、JOIN、集計、SQL 関数
- シーケンス → UUID、一時テーブル → Java コレクション
- 動的 SQL → ビルダーパターン、バッチ操作

**出力ファイル:**
```
<output-dir>/
├── connection_test_response.json
├── raw_schema_data.json
├── oracle_schema_report.md
├── scalardb_migration_analysis.md
├── scalardb_migration_steps.md
├── aq_setup.sql                    # Oracle AQ インフラストラクチャ
├── scalardb_aq_migration_report.md
├── scalardb_sp_migration_report.md
└── generated-java/
    ├── *Consumer.java              # AQ コンシューマ
    ├── *Message.java               # メッセージ POJO
    ├── AqStructHolder.java         # ojdbc11 互換性
    ├── ExceptionClassifier.java    # 例外 → 判定マッピング
    └── *Service.java               # SP/トリガー実装
```

---

### `/architect:migrate-mysql`

5 つのサブエージェントを使用した MySQL から ScalarDB へのマイグレーションパイプラインです。

**スキーマ抽出**の対象:
- テーブル、カラム（auto_increment、generated）、パーティション
- インデックス（B-tree、ハッシュ、全文検索、空間、複合、関数）
- ビュー、ストアドプロシージャ/ファンクション、トリガー、イベント
- JSON カラム、空間/ジオメトリカラム、ENUM/SET カラム
- ユーザー権限、文字セット、照合順序、ストレージエンジン
- 依存関係（FK、ビュー、トリガー、ルーチン）

**データ型マッピングのポイント:**
- `tinyint(1)` → BOOLEAN
- `int unsigned` → BIGINT
- `decimal/numeric` → DOUBLE（精度損失の警告付き）
- `json` → TEXT（アプリケーションでシリアライズ/デシリアライズ）
- `enum/set` → TEXT（アプリケーションでバリデーション）
- `bigint` → BIGINT（-2^53 ～ 2^53 の範囲警告付き）

**出力ファイル:**
```
<output-dir>/
├── mysql_connection_test_response.json
├── raw_mysql_schema_data.json
├── mysql_schema_report.md
├── scalardb_mysql_migration_analysis.md
├── scalardb_mysql_migration_steps.md
├── scalardb_mysql_sp_migration_report.md
└── generated-java/
    └── *Service.java
```

---

### `/architect:migrate-postgresql`

5 つのサブエージェントを使用した PostgreSQL から ScalarDB へのマイグレーションパイプラインです。

**スキーマ抽出**の対象:
- テーブル（通常、パーティション、一時、外部）、継承
- インデックス（B-tree、ハッシュ、GiST、GIN、BRIN）、部分/ユニークインデックス
- カスタム型（ENUM、複合、ドメイン、範囲）
- PL/pgSQL ファンクション/プロシージャ、トリガー、イベントトリガー
- シーケンス、拡張機能、外部テーブル（FDW）
- RLS ポリシー、パブリケーション/サブスクリプション、全文検索
- JSON/JSONB、XML、幾何/ネットワーク型

**PostgreSQL 固有の注意事項:**
- ScalarDB が公式にサポートするデータ型は 14 種類のみ
- `serial/bigserial` → INT/BIGINT（アプリケーションでシーケンスを管理）
- `numeric/money` → 未サポート（DOUBLE を使用、精度損失あり）
- `json/jsonb` → TEXT（シリアライズ/デシリアライズ）
- `uuid` → TEXT
- `inet/cidr` → TEXT
- 配列、範囲、幾何型 → 未サポート

**出力ファイル:**
```
<output-dir>/
├── postgres_connection_test_response.json
├── raw_schema_data.json
├── postgresql_schema_report.md
├── scalardb_migration_analysis.md
├── scalardb_migration_steps.md
├── scalardb_sp_migration_report.md
└── generated-java/
    └── *Service.java
```

## 複雑度スコアリング

各マイグレーションは、4 つの重み付き次元に基づいて複雑度スコア（0-10）を受け取ります:

| 次元 | 重み | 低（0-2） | 中（3-6） | 高（7-10） |
|-----------|--------|-----------|--------------|-------------|
| データ型 | 20% | 標準的な型 | LOB、一部のカスタム型 | オブジェクト型、ネスト |
| スキーマ | 25% | シンプルなテーブル | FK、ビュー | パーティション、マテリアライズドビュー |
| 手続きコード | 25% | なし、または少数 | 10-50 オブジェクト | 50 以上、複雑なロジック |
| アプリケーションへの影響 | 30% | シンプルな CRUD | JOIN、トランザクション | ウィンドウ関数、DB ロジック多用 |

**評価:**
- 0-2: LOW（低）複雑度
- 3-4: MEDIUM（中）
- 5-7: HIGH（高）
- 8-10: VERY HIGH（非常に高い）

## 設定

すべてのデータベース接続は `.claude/configuration/databases.env` に保存されます。マイグレーションスキルは対話型プロンプトを通じてこのファイルを自動的に作成・管理します。

```properties
# Shared
ACTIVE_DATABASE=oracle|mysql|postgresql
OUTPUT_DIR=/absolute/path/to/output

# Oracle
ORACLE_HOST=localhost
ORACLE_PORT=1521
ORACLE_SERVICE=ORCL
ORACLE_USER=scott
ORACLE_PASSWORD=tiger
ORACLE_SCHEMA=SCOTT

# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=myapp
MYSQL_USER=root
MYSQL_PASSWORD=mysql

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=myapp
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_SCHEMA=public
```

## 前提条件

| データベース | 必要なツール |
|----------|---------------|
| Oracle | Python 3.9+、SQL*Plus、`python-dotenv` |
| MySQL | Python 3.9+、`mysql-connector-python`、`python-dotenv` |
| PostgreSQL | Python 3.9+、`psycopg2`、`python-dotenv` |

Python 依存パッケージのインストール:
```bash
pip install python-dotenv mysql-connector-python psycopg2-binary
```

## 内部アーキテクチャ

### Python 抽出スクリプト

各データベースには専用の Python 抽出スクリプトがあります:
- `skills/migrate-oracle/analyze-oracle-schema/scripts/oracle_db_extractor.py`
- `skills/migrate-mysql/analyze-mysql-schema/scripts/mysql_db_extractor.py`
- `skills/migrate-postgresql/analyze-postgresql-schema/scripts/postgresql_db_extractor.py`

### サブエージェントテンプレート

各パイプラインステップ用の再利用可能なプロンプトテンプレート:
- `skills/common/subagents/oracle/`（6 テンプレート: test、extract、report、analysis、AQ、SP）
- `skills/common/subagents/mysql/`（5 テンプレート）
- `skills/common/subagents/postgresql/`（5 テンプレート）

### リファレンスドキュメント

各マイグレーションスキルにはデータベース固有のリファレンスが含まれています:
- データ型マッピングテーブル
- ScalarDB SQL の制約事項
- 複雑度スコアリングモデル
- マイグレーション戦略ガイド（AQ、SP/トリガー変換）
