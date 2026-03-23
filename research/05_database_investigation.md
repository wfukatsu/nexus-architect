# データベース調査

## ScalarDB とは

ScalarDB は、Scalar社が開発した **Universal HTAP (Hybrid Transactional/Analytical Processing) Engine** である。多様なデータベース上にミドルウェアとして動作し、**Consensus Commit** プロトコルを用いてデータベース横断のACIDトランザクションとリアルタイム分析を実現する。最新バージョンは **3.17** である。

ScalarDB は、ストレージ抽象化レイヤーとストレージに依存しないユニバーサルトランザクションマネージャーで構成され、各データベース固有のストレージアダプタを通じて多様なバックエンドに接続する。

---

## 1. RDBMS

ScalarDB は JDBC 対応のリレーショナルデータベースを広くサポートしている。ストレージタイプとして `scalar.db.storage=jdbc` を指定して利用する。

### 公式サポート一覧

| データベース | サポートバージョン | サポート区分 |
|---|---|---|
| **PostgreSQL** | 17, 16, 15, 14, 13 | 公式サポート |
| **MySQL** | 8.4, 8.0 | 公式サポート |
| **Oracle Database** | 23ai, 21c, 19c | 公式サポート |
| **Microsoft SQL Server** | 2022, 2019, 2017 | 公式サポート |
| **MariaDB** | 11.4, 10.11 | 公式サポート |
| **IBM Db2** | 12.1, 11.5 (Linux/UNIX/Windows版のみ。z/OS版は非対応) | 公式サポート |
| **SQLite** | 3 | 公式サポート |
| **Amazon Aurora MySQL** | 3, 2 | 公式サポート |
| **Amazon Aurora PostgreSQL** | 17, 16, 15, 14, 13 | 公式サポート |
| **Google AlloyDB** | 16, 15 | PostgreSQL互換DBとして公式サポート（PostgreSQL JDBCドライバ使用） |
| **TiDB** | 8.5, 7.5, 6.5 | 互換DB (MySQL Connector/J使用) |
| **YugabyteDB** | 2 | 互換DB (PostgreSQL JDBCドライバ使用) |

### 各データベースの特性

#### PostgreSQL

- **特長**: オープンソースの高機能RDBMS。拡張性が高く、JSON/GIS/全文検索等の機能が豊富
- **強み**: 標準SQL準拠度が高い、拡張機能(pgvector等)が豊富、コミュニティが活発
- **弱み**: 大規模書き込みワークロードではMySQLに劣る場合がある
- **ユースケース**: 汎用OLTP、地理空間データ、複雑なクエリが必要なシステム
- **ScalarDBとの親和性**: **非常に高い**。ScalarDB Analytics でも外部データソースとしてサポート。pgvector連携によりベクトル検索バックエンドとしても利用可能

#### MySQL

- **特長**: 世界で最も普及しているオープンソースRDBMS
- **強み**: 高速な読み取り性能、豊富なホスティングオプション、エコシステムの充実
- **弱み**: 標準SQL準拠度がPostgreSQLに劣る、ストアドプロシージャの機能制限
- **ユースケース**: Webアプリケーション、CMS、ECサイト
- **ScalarDBとの親和性**: **非常に高い**。ScalarDB Analytics でも外部データソースとしてサポート

#### Oracle Database

- **特長**: エンタープライズ向け商用RDBMS最大手
- **強み**: 高いパフォーマンスと信頼性、高度な機能(パーティショニング、RAC等)、強力なサポート
- **弱み**: ライセンスコストが高い、複雑な料金体系
- **ユースケース**: 基幹業務システム、金融システム、大規模エンタープライズ
- **ScalarDBとの親和性**: **高い**。ScalarDB Analytics でも外部データソースとしてサポート

#### Microsoft SQL Server

- **特長**: Microsoft製エンタープライズRDBMS
- **強み**: Windows/.NET環境との統合、BI機能(SSRS/SSIS/SSAS)、Azure連携
- **弱み**: Linux環境では一部機能制限、ライセンスコスト
- **ユースケース**: Microsoft中心のエンタープライズ環境、BIシステム
- **ScalarDBとの親和性**: **高い**。ScalarDB Analytics でも外部データソースとしてサポート

#### MariaDB

- **特長**: MySQLからフォークされたオープンソースRDBMS
- **強み**: MySQLとの高い互換性、追加機能(Aria/TokuDBストレージエンジン等)、真のオープンソース
- **弱み**: MySQL 8.0以降との互換性に差異が生じている
- **ユースケース**: MySQLの代替、Webアプリケーション
- **ScalarDBとの親和性**: **高い**

#### IBM Db2

- **特長**: IBMの伝統的なエンタープライズRDBMS
- **強み**: メインフレームとの親和性、AI統合(Watson連携)、高い信頼性
- **弱み**: 学習コスト、z/OS版はScalarDB非対応
- **ユースケース**: 銀行・保険等の既存基幹システム
- **ScalarDBとの親和性**: **高い**。Linux/UNIX/Windows版のみサポート

#### SQLite

- **特長**: 軽量な組み込み型RDBMS
- **強み**: サーバー不要、ゼロ構成、組み込みに最適
- **弱み**: 同時書き込み性能の制限、大規模データに不向き
- **ユースケース**: 開発・テスト環境、軽量アプリケーション

---

## 2. NoSQL

ScalarDB のNoSQLサポートは、専用のストレージアダプタを通じて実現されている。

### 公式サポート一覧

| データベース | サポートバージョン | ストレージ設定値 | サポート区分 |
|---|---|---|---|
| **Amazon DynamoDB** | 最新版 | `scalar.db.storage=dynamo` | 公式サポート (専用アダプタ) |
| **Azure Cosmos DB for NoSQL** | 最新版 | `scalar.db.storage=cosmos` | 公式サポート (専用アダプタ) |
| **Apache Cassandra** | 5.0, 4.1, 3.11, 3.0 | `scalar.db.storage=cassandra` | 公式サポート (専用アダプタ) |

### 各データベースの特性

#### Amazon DynamoDB

- **データモデル**: キー・バリュー型 / ドキュメント型
- **特長**: AWSフルマネージド、サーバーレス、自動スケーリング
- **スケーラビリティ**: 事実上無制限のスケーリング(On-Demandモード)
- **レイテンシ**: 一桁ミリ秒の一貫したパフォーマンス
- **可用性**: 99.999% SLA (Global Tables使用時)
- **CAP定理**: **AP型** (結果整合性がデフォルト、強い整合性オプションあり)
- **ScalarDBとの親和性**: **非常に高い**。専用アダプタで直接サポート。ScalarDB Analytics でも外部データソースとしてサポート
- **ユースケース**: 高スループットが必要なWebアプリ、セッション管理、IoTデータ

#### Azure Cosmos DB for NoSQL

- **データモデル**: マルチモデル(ドキュメント、キー・バリュー、グラフ、カラムファミリ)
- **特長**: グローバル分散、複数の整合性レベル選択可能
- **スケーラビリティ**: グローバルレベルでの自動スケーリング
- **レイテンシ**: 99パーセンタイルで10ミリ秒未満
- **可用性**: 99.999% SLA (マルチリージョン)
- **CAP定理**: **可変** (5段階の整合性レベル: Strong, Bounded Staleness, Session, Consistent Prefix, Eventual)
- **ScalarDBとの親和性**: **非常に高い**。専用アダプタで直接サポート。ベクトル検索のバックエンドとしても利用可能
- **ユースケース**: グローバル分散アプリ、マルチモデルが必要な場合

#### Apache Cassandra

- **データモデル**: ワイドカラム型
- **特長**: 高い可用性、線形スケーラビリティ、マスターレスアーキテクチャ
- **スケーラビリティ**: ノード追加による線形的なスケーリング
- **スループット**: ノード数に比例して向上
- **可用性**: マスターレスのため単一障害点なし
- **CAP定理**: **AP型** (整合性レベルはTunable Consistency)
- **ScalarDBとの親和性**: **非常に高い**。ScalarDBの初期から対応している主要バックエンド。Coordinatorテーブルをレプリケーションファクタ3で運用することで、Paxos Commit相当の高可用トランザクション調整が可能
- **ユースケース**: 大量書き込み、時系列データ、IoT

### 未サポートのNoSQL

- **Apache HBase**: 最新版 (3.17) では公式サポートリストに含まれていない
- **MongoDB**: 未サポート
- **Google Cloud Bigtable**: 未サポート

---

## 3. オブジェクトストレージ

ScalarDB 3.17 で **Private Preview** として新たにオブジェクトストレージのサポートが追加された。

| ストレージ | ステータス | 必要な権限/ロール |
|---|---|---|
| **Amazon S3** | Private Preview | `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`, `s3:ListBucket` |
| **Azure Blob Storage** | Private Preview | フルアクセスキー認証 |
| **Google Cloud Storage** | Private Preview | `Storage Object Admin (roles/storage.objectAdmin)` |

### データレイク活用パターン

ScalarDB Analytics は Apache Spark プラグインを介してデータレイク的な活用が可能である。

- **ScalarDB Analytics** は多様なデータソースを統一的なカタログとして管理し、Sparkを通じてクロスデータベース分析クエリを実行可能
- 外部分析プラットフォームとして **Databricks** および **Snowflake** との連携もサポート
- オブジェクトストレージへの直接的なデータ永続化はPrivate Previewの段階であり、本格的なデータレイク構築にはまだ機能の成熟が必要

---

## 4. Vector Index (ベクトル検索)

ScalarDB Cluster は **ベクトルストア抽象化レイヤー** を提供しており、内部で LangChain4j を活用している。現在 **Private Preview** のステータスである。

### 対応ベクトルストア (Embedding Store)

| ベクトルストア | 説明 | 用途 |
|---|---|---|
| **pgvector** (PostgreSQL拡張) | PostgreSQLベースのベクトル類似検索 | PostgreSQL環境でのベクトル検索 |
| **OpenSearch** | ローカルクラスタ/AWSマネージドサービス対応 | 大規模ベクトル検索 |
| **Azure Cosmos DB for NoSQL** | Azureネイティブのベクトル検索 | Azure環境でのベクトル検索 |
| **Azure AI Search** | Azureの検索サービスを活用 | Azure環境での高度な検索 |
| **In-Memory** | 基本的なメモリ内実装 | プロトタイピング用途 |

### 対応Embeddingモデル

| モデル | プロバイダ | 説明 |
|---|---|---|
| **In-Process (ONNX Runtime)** | ローカル実行 | ScalarDB Clusterプロセス内で実行 |
| **Amazon Bedrock** | AWS | Titanモデル等 |
| **Azure OpenAI** | Microsoft | Azure経由でのOpenAIモデル利用 |
| **Google Vertex AI** | GCP | Google CloudのAIプラットフォーム |
| **OpenAI** | OpenAI | OpenAI API直接接続 |

### AI/MLユースケースとの統合

- **RAG (Retrieval-Augmented Generation)**: ScalarDB Cluster のデータベース抽象化とベクトルストア抽象化を組み合わせることで、データ抽出→ベクトル化→ベクトル格納→検索の全プロセスを統一的に実装可能
- 複数の名前付きインスタンスを設定でき、用途に応じてベクトルストアとEmbeddingモデルを切り替え可能
- 設定は `scalar.db.embedding.enabled=true` で有効化し、`scalar.db.embedding.stores` と `scalar.db.embedding.models` でインスタンスを定義

### 未サポートの専用ベクトルデータベース

Pinecone、Weaviate、Milvus、Chroma、Qdrant などの専用ベクトルデータベースは現時点でScalarDBの公式サポートには含まれていない。ただし、LangChain4j ベースの設計であるため、将来的な拡張の余地はある。

---

## 5. Search Index (検索インデックス)

### OpenSearch

- ScalarDB Cluster のベクトルストアバックエンドとして **OpenSearch がサポートされている**
- ローカルクラスタおよび **AWS OpenSearch Service** の両方に対応
- 設定項目: サーバーURL、APIキー、ユーザー名、パスワード、インデックス名
- 用途: ベクトル類似検索のバックエンドとして利用 (Embedding Store として)

### Elasticsearch

- 現時点でScalarDBの公式サポートには含まれていない
- OpenSearch はElasticsearchからフォークされたプロジェクトであるが、ScalarDB は OpenSearch のみを明示的にサポートしている

---

## 6. クラウド別対応状況

### AWS

| サービス | 種類 | ScalarDBサポート | 備考 |
|---|---|---|---|
| **Amazon Aurora MySQL** | マネージドRDBMS | **公式サポート** | v3, v2 |
| **Amazon Aurora PostgreSQL** | マネージドRDBMS | **公式サポート** | v17, 16, 15, 14, 13 |
| **Amazon RDS (MySQL/PostgreSQL等)** | マネージドRDBMS | JDBC経由で利用可能 | ベースDBと同じドライバを使用 |
| **Amazon DynamoDB** | NoSQL | **公式サポート (専用アダプタ)** | |
| **Amazon S3** | オブジェクトストレージ | **Private Preview** | v3.17~ |
| **Amazon EKS** | Kubernetes | **公式サポート** (デプロイ先) | |
| **AWS OpenSearch Service** | 検索/ベクトル | **公式サポート** (Embedding Store) | |
| **Amazon Bedrock** | AI/ML | **公式サポート** (Embeddingモデル) | |
| **Databricks on AWS** | 分析 | **公式サポート** (Analytics連携) | |

### Azure

| サービス | 種類 | ScalarDBサポート | 備考 |
|---|---|---|---|
| **Azure Cosmos DB for NoSQL** | NoSQL | **公式サポート (専用アダプタ)** | トランザクション + ベクトル検索 |
| **Azure SQL Database** | マネージドRDBMS | JDBC経由で利用可能 | SQL Serverドライバ使用 |
| **Azure Database for MySQL** | マネージドRDBMS | JDBC経由で利用可能 | MySQLドライバ使用 |
| **Azure Database for PostgreSQL** | マネージドRDBMS | JDBC経由で利用可能 | PostgreSQLドライバ使用 |
| **Azure Blob Storage** | オブジェクトストレージ | **Private Preview** | v3.17~ |
| **Azure AKS** | Kubernetes | **公式サポート** (デプロイ先) | |
| **Azure AI Search** | 検索/ベクトル | **公式サポート** (Embedding Store) | |
| **Azure OpenAI** | AI/ML | **公式サポート** (Embeddingモデル) | |

### GCP

| サービス | 種類 | ScalarDBサポート | 備考 |
|---|---|---|---|
| **Google AlloyDB** | マネージドRDBMS | **PostgreSQL互換DBとして公式サポート** | v16, v15 (PostgreSQL JDBCドライバ使用) |
| **Google Cloud SQL (MySQL/PostgreSQL)** | マネージドRDBMS | JDBC経由で利用可能 | 各DBドライバ使用 |
| **Google Cloud Storage** | オブジェクトストレージ | **Private Preview** | v3.17~ |
| **Google Vertex AI** | AI/ML | **公式サポート** (Embeddingモデル) | |
| **Cloud Spanner** | NewSQL | **未サポート** | |
| **Cloud Bigtable** | NoSQL | **未サポート** | |

### オンプレミス

| データベース | 種類 | ScalarDBサポート | 備考 |
|---|---|---|---|
| **PostgreSQL** | RDBMS | **公式サポート** | |
| **MySQL** | RDBMS | **公式サポート** | |
| **Oracle Database** | RDBMS | **公式サポート** | |
| **SQL Server** | RDBMS | **公式サポート** | |
| **MariaDB** | RDBMS | **公式サポート** | |
| **IBM Db2** | RDBMS | **公式サポート** | Linux/UNIX/Windows版のみ |
| **SQLite** | RDBMS | **公式サポート** | 開発・テスト用途 |
| **Apache Cassandra** | NoSQL | **公式サポート** | |
| **YugabyteDB** | NewSQL | **互換サポート** | PostgreSQLドライバ使用 |
| **TiDB** | NewSQL | **互換サポート** | MySQLドライバ使用 |
| **OpenSearch** | 検索/ベクトル | **公式サポート** (Embedding Store) | |

---

## 7. データベース選定のためのティアランキング

### Tier 1: 最も親和性が高い (専用アダプタ / 公式フルサポート)

| データベース | 理由 |
|---|---|
| **Apache Cassandra** | ScalarDB初期からの主要バックエンド。専用アダプタあり |
| **Amazon DynamoDB** | 専用アダプタ (dynamo)。高スケーラビリティ |
| **Azure Cosmos DB for NoSQL** | 専用アダプタ (cosmos) + ベクトルストア対応 |
| **PostgreSQL / MySQL** | JDBCアダプタ + Analytics対応 + pgvector連携 |
| **Amazon Aurora (MySQL/PostgreSQL)** | 公式テスト済みのマネージドサービス |

### Tier 2: 公式サポートあり (JDBC経由)

> **注意**: 本ドキュメントのTier分類はアダプタ種別に基づく独自分類です。Tier 1は専用アダプタを持つデータベース、Tier 2はJDBCアダプタ経由のデータベースとして分類しています。Oracle、SQL ServerはJDBC経由ですが、ScalarDBの公式サポート対象データベースであり、本番環境での利用が完全にサポートされています。

| データベース | 理由 |
|---|---|
| **Oracle Database** | JDBCアダプタ経由、公式テスト済み。Analytics対応 |
| **SQL Server** | JDBCアダプタ経由、公式テスト済み。Analytics対応 |
| **MariaDB** | JDBCアダプタ経由、公式テスト済み |
| **IBM Db2** | JDBCアダプタ経由、公式テスト済み |
| **Google AlloyDB** | 互換DBとして公式記載。PostgreSQLドライバ使用 |
| **TiDB** | 互換DBとして公式記載。MySQLドライバ使用 |
| **YugabyteDB** | 互換DBとして公式記載。PostgreSQLドライバ使用 |

### Tier 3: 新機能 (Private Preview)

| データベース/サービス | 理由 |
|---|---|
| **Amazon S3** | オブジェクトストレージ (v3.17~) |
| **Azure Blob Storage** | オブジェクトストレージ (v3.17~) |
| **Google Cloud Storage** | オブジェクトストレージ (v3.17~) |
| **pgvector / OpenSearch / Azure AI Search / Cosmos DB** | ベクトル検索バックエンド (Private Preview) |

### Tier 4: 間接的な連携のみ / 未サポート

| データベース/サービス | 状況 |
|---|---|
| **Elasticsearch** | 直接サポートなし (OpenSearchのみ) |
| **Pinecone, Weaviate, Milvus, Chroma** | 未サポート |
| **Google Cloud Spanner** | 未サポート |
| **Google Cloud Bigtable** | 未サポート |
| **Apache HBase** | 最新版では未サポート |
| **MongoDB** | 未サポート |

---

## 8. 各DBの特性比較

### RDBMS比較

| 指標 | PostgreSQL | MySQL | Oracle | SQL Server | MariaDB | Db2 |
|---|---|---|---|---|---|---|
| **スループット** | 高 | 高 (読み取り特化) | 非常に高 | 高 | 高 | 高 |
| **レイテンシ** | 低 | 非常に低 | 低 | 低 | 非常に低 | 低 |
| **スケーラビリティ** | 中～高 | 中～高 | 非常に高 | 高 | 中～高 | 高 |
| **可用性** | 高 (レプリケーション) | 高 | 非常に高 (RAC) | 高 (Always On) | 高 | 非常に高 |
| **コスト** | 無料 (OSS) | 無料 (OSS) | 高 (商用) | 中～高 (商用) | 無料 (OSS) | 中～高 (商用) |
| **ScalarDB親和性** | 非常に高 | 非常に高 | 高 | 高 | 高 | 高 |

### NoSQL比較

| 指標 | DynamoDB | Cosmos DB | Cassandra |
|---|---|---|---|
| **スループット** | 非常に高 (自動) | 非常に高 (RU制御) | 非常に高 (線形スケール) |
| **レイテンシ** | 一桁ms | 10ms未満 (99%ile) | 低 (設定次第) |
| **スケーラビリティ** | 事実上無制限 | グローバル自動 | 線形スケーリング |
| **可用性** | 99.999% SLA | 99.999% SLA | マスターレス (SPOFなし) |
| **CAP定理** | AP (デフォルト) | 可変 (5段階) | AP (Tunable) |
| **コスト** | 従量課金 | RU課金 | 無料 (OSS) / 運用コスト |
| **ScalarDB親和性** | 非常に高 | 非常に高 | 非常に高 |

---

## 9. ScalarDB 3.17 の新機能 (データベース関連)

- **AlloyDB**: バージョン 15, 16 のサポート追加 (PostgreSQL JDBCドライバ使用)
- **TiDB**: バージョン 6.5, 7.5, 8.5 のサポート追加 (MySQL Connector/J使用)
- **Cassandra**: バージョン 4, 5 の統合テスト追加
- **オブジェクトストレージ**: Amazon S3、Azure Blob Storage、Google Cloud Storage のサポート追加 (Private Preview)
- **ベクトル検索**: 複数の名前付きインスタンスによるEmbedding Store/Modelの設定に対応
- **Virtual Tables**: Storage抽象化レイヤーにバーチャルテーブルを導入。プライマリキーによる2テーブルの論理結合をサポート
- **RBAC**: ロールベースアクセス制御の追加 (ScalarDB Cluster)
- **集約機能**: SUM, MIN, MAX, AVG および HAVING句 (ScalarDB SQL)

---

## 10. Kubernetes / デプロイ要件

### ScalarDB Cluster

- **Kubernetes**: 1.31 - 1.34 (EKS, AKS サポート)
- **Red Hat OpenShift**: 4.18 - 4.20
- **Helm**: 3.5+
- **主要ポート**: 60053 (API), 8080 (GraphQL), 9080 (メトリクス)

### ScalarDB Analytics Server

- **Kubernetes**: 1.31 - 1.34 (EKS, AKS サポート)
- **Red Hat OpenShift**: サポート「TBD」
- **Helm**: 3.5+
- **主要ポート**: 11051, 11052

---

## ソース

- [ScalarDB Overview](https://scalardb.scalar-labs.com/docs/latest/overview/)
- [ScalarDB Requirements (3.13)](https://scalardb.scalar-labs.com/docs/3.13/requirements/)
- [ScalarDB Requirements (latest/3.17)](https://scalardb.scalar-labs.com/docs/latest/requirements/)
- [ScalarDB Supported Databases (GitHub)](https://github.com/scalar-labs/scalardb/blob/master/docs/scalardb-supported-databases.md)
- [ScalarDB 3.17 Release Notes](https://scalardb.scalar-labs.com/docs/latest/releases/release-notes/)
- [Multi-Storage Transactions](https://scalardb.scalar-labs.com/docs/latest/multi-storage-transactions/)
- [ScalarDB Analytics Design](https://scalardb.scalar-labs.com/docs/latest/scalardb-analytics/design/)
- [Getting Started with Vector Search](https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/getting-started-with-vector-search/)
- [Consensus Commit Protocol](https://scalardb.scalar-labs.com/docs/latest/consensus-commit/)
- [ScalarDB GitHub Repository](https://github.com/scalar-labs/scalardb)
- [Scalar, Inc. ScalarDB Product Page](https://www.scalar-labs.com/scalardb)
- [Getting Started with ScalarDB](https://scalardb.scalar-labs.com/docs/latest/getting-started-with-scalardb/)
