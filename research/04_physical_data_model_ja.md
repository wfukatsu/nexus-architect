# データモデル（物理モデル）調査

## 1. Partition Key（PT）の設計

### 1.1 Partition Key の役割と重要性

ScalarDB のデータモデルは「Bigtable にインスピレーションを受けた拡張キー値モデル」であり、データの階層は **名前空間 > テーブル > パーティション > レコード > 列** で構成される。Partition Key はこの中で **パーティションを一意に識別し、データの分散単位を決定する** 最も重要な設計要素である。

ScalarDB はデータをハッシュベースで分散するため、Partition Key の値によってレコードがどのノード（パーティション）に配置されるかが決まる。結果として、Partition Key の設計は以下に直結する。

- **読み書きの効率**: 単一パーティション検索（single partition lookup）が最も効率的
- **負荷分散**: Partition Key の選択が不適切だとホットスポットが発生
- **スケーラビリティ**: パーティション単位でスケールアウトするため、均等分散が不可欠

参考: [Model Your Data | ScalarDB Documentation](https://scalardb.scalar-labs.com/docs/latest/data-modeling/)

### 1.2 設計のベストプラクティス

**原則: クエリ駆動型設計（Query-Driven Modeling）**

ScalarDB ではリレーショナルモデルのような正規化ではなく、アプリケーションのアクセスパターンに基づいてテーブル構造を決定する。

**具体例: 銀行アプリケーション**

| 設計パターン | Partition Key | Clustering Key | 評価 |
|---|---|---|---|
| 良い設計 | `account_id` | `transaction_date` | アカウント単位でアクセスが分散される |
| 悪い設計 | `branch_id` | `account_id` | 支店の全アカウントが1パーティションに集中 |

```json
{
  "banking.account_transactions": {
    "transaction": true,
    "partition-key": ["account_id"],
    "clustering-key": ["transaction_date DESC"],
    "columns": {
      "account_id": "TEXT",
      "transaction_date": "BIGINT",
      "amount": "INT",
      "description": "TEXT"
    }
  }
}
```

### 1.3 ホットスポットの回避

ホットスポットとは、特定のパーティションにアクセスが集中し、そのノードがボトルネックとなる現象である。

**回避策:**

| 手法 | 説明 | 適用場面 |
|---|---|---|
| 高カーディナリティ列の選択 | ユーザーID、注文IDなど一意性の高い列を使う | 一般的なOLTPワークロード |
| 複合 Partition Key | 複数列の組み合わせで分散性を高める | 単一列では偏りが大きい場合 |
| バケッティング（人工的分割） | 元の値にハッシュ suffix を付与して分散 | 時系列データなど特定キーへの集中が避けられない場合 |

**バケッティングの例:**
```
# 元の設計: sensor_id が Partition Key だが、特定センサーに集中
# 改善: sensor_id + bucket_id(0-9) で10分割
partition-key: ["sensor_id", "bucket_id"]
```

### 1.4 カーディナリティの考慮

| カーディナリティ | 例 | リスク | 推奨度 |
|---|---|---|---|
| 非常に高い（数百万以上） | UUID、ユーザーID | パーティション数が膨大になるが均等分散される | 最適 |
| 中程度（数千〜数万） | 店舗ID、商品カテゴリID | 適度な分散が得られる | 適切 |
| 低い（数十以下） | 都道府県コード、ステータス値 | 少数の大きなパーティションが生じ、負荷集中 | 避けるべき |
| 極端に低い（1〜数個） | boolean値、固定区分値 | 事実上の単一パーティション。スケーラビリティ喪失 | 不可 |

**判断基準の目安:**
- パーティション数がノード数の10倍以上あることが望ましい
- 1パーティションあたりのレコード数が数万件以下に収まるよう設計

---

## 2. Clustering Key（CK）の設計

### 2.1 Clustering Key の役割

Clustering Key は**パーティション内でレコードを一意に識別し、かつソート順を決定する**キーである。ScalarDB では、パーティション内のレコードは Clustering Key の列によってソートされた状態で格納される（論理的に）。

主な役割:
- パーティション内のレコード一意性の保証（Partition Key + Clustering Key = Primary Key）
- 範囲スキャン（Range Scan）の効率化
- パーティション内でのソート順の制御

### 2.2 ソート順の決定

スキーマ定義時に `ASC`（昇順）または `DESC`（降順）を指定できる。

```json
{
  "order.order_items": {
    "transaction": true,
    "partition-key": ["order_id"],
    "clustering-key": ["item_seq ASC"],
    "columns": {
      "order_id": "TEXT",
      "item_seq": "INT",
      "product_id": "TEXT",
      "quantity": "INT",
      "price": "INT"
    }
  }
}
```

**ソート順決定の指針:**

| アクセスパターン | 推奨ソート順 | 理由 |
|---|---|---|
| 最新データ優先取得 | `DESC` | 最新レコードが先頭に来るため Limit 指定で効率的 |
| 時系列順のスキャン | `ASC` | 時間順の走査が自然 |
| ページネーション | アクセス頻度の高い方向 | スキャンの開始位置を効率化 |

### 2.3 範囲スキャンの最適化

ScalarDB の範囲スキャン（Scan）は **パーティション内でのみ効率的に実行可能** である。パーティションキーを指定せずにスキャンを行うと、クロスパーティションスキャンとなり、非効率かつ低い分離レベル（非JDBCデータベースの場合は `SNAPSHOT`）で実行される。

**効率的なスキャンの条件:**
1. Partition Key の完全一致指定が必須
2. Clustering Key の境界値（start/end）を指定して範囲を絞り込む
3. inclusive/exclusive の指定で境界の扱いを制御

```java
// 効率的なパーティション内スキャン
Scan scan = Scan.newBuilder()
    .namespace("ns")
    .table("order_items")
    .partitionKey(Key.ofText("order_id", "ORD-001"))
    .start(Key.ofInt("item_seq", 1), true)   // inclusive
    .end(Key.ofInt("item_seq", 100), true)    // inclusive
    .orderings(Scan.Ordering.asc("item_seq"))
    .limit(50)
    .build();
```

### 2.4 複合 Clustering Key の使い方

複合 Clustering Key を使う場合、**列の宣言順序が重要** であり、スキャン時にはその順序に従って先頭から連続した列のみ指定できる。

```json
{
  "log.access_logs": {
    "transaction": true,
    "partition-key": ["user_id"],
    "clustering-key": ["access_date DESC", "access_time DESC", "log_seq ASC"],
    "columns": {
      "user_id": "TEXT",
      "access_date": "TEXT",
      "access_time": "TEXT",
      "log_seq": "INT",
      "action": "TEXT",
      "resource": "TEXT"
    }
  }
}
```

**指定可能なスキャン条件:**
- `user_id` + `access_date` の範囲指定 --> 有効
- `user_id` + `access_date` + `access_time` の範囲指定 --> 有効
- `user_id` + `access_time` のみ（`access_date` をスキップ）--> 無効（先頭列を飛ばせない）

**複合 CK の設計指針:**
- 最も頻繁にフィルタリングする列を先頭に配置
- 時系列データでは日付 > 時刻 > 連番の順が一般的
- 列数は2〜3列を目安とし、過度に増やさない

---

## 3. Secondary Index（SI）の設計

### 3.1 Secondary Index の用途と制限

ScalarDB の Secondary Index は、Partition Key 以外の列で検索を可能にする機能である。ただし、以下の重要な制限がある。

**制限事項:**
| 制限 | 詳細 |
|---|---|
| 単一列のみ | 複数列のインデックス（複合インデックス）は未サポート |
| 全パーティションスキャン | インデックスキーの検索は全パーティションに跨るため非効率 |
| 低選択性での性能劣化 | 選択性が低い（多くのレコードにヒットする）場合、特に非効率 |

参考: [ScalarDB Java API Guide](https://scalardb.scalar-labs.com/docs/3.16/api-guide/)

### 3.2 パフォーマンスへの影響

**読み取りへの影響:**
- Secondary Index を使った検索は全パーティションをスキャンするため、パーティション数に比例してコストが増大
- Partition Key 指定のスキャンに比べて桁違いに遅い可能性がある

**書き込みへの影響:**
- インデックスの維持コストにより、書き込み性能が低下
- 基盤データベース側でのインデックス更新オーバーヘッドも加わる

**Consensus Commit のメタデータオーバーヘッド:**
- ScalarDB は各レコードにトランザクションメタデータ（`tx_id`, `tx_state`, `tx_version`, 前バージョンデータ等）を付与する
- 読み書きで基盤データベースへのアクセスが約2倍になる
- Secondary Index と組み合わせると更にオーバーヘッドが増大

### 3.3 使用すべき場面と避けるべき場面

**使用すべき場面:**
- 低頻度のルックアップ（管理画面での検索など）
- 高い選択性（検索結果が全レコードの0.1%以下程度）
- Partition Key を事前に知り得ない検索

**避けるべき場面:**
- 高頻度のクエリパス（メインのAPIエンドポイントなど）
- 低い選択性の列（ステータスフラグ、boolean 値など）
- 大量のレコードを返す可能性がある検索

**推奨される代替案: インデックステーブルパターン**

Secondary Index の代わりに、検索したい列を Partition Key に持つ別テーブルを作成する。

```
# ベーステーブル: ユーザーID で検索
user_table(user_id[PK], email, name, status)

# インデックステーブル: メールアドレスで検索
user_by_email(email[PK], user_id, name, status)
```

このパターンのトレードオフ:
- 読み取りは効率的（単一パーティション検索）
- 書き込みは2テーブルへの更新が必要（ScalarDB トランザクションで一貫性担保可能）
- データの重複によるストレージ消費の増加

---

## 4. データベース選定基準

### 4.1 機能要件からの選定

ScalarDB は複数のデータベースを抽象化して統一的にアクセスする「ユニバーサルトランザクションマネージャ」であるため、基盤データベースの選定は依然として重要である。

参考: [ScalarDB Overview](https://scalardb.scalar-labs.com/docs/3.13/overview/), [ScalarDB Configurations](https://scalardb.scalar-labs.com/docs/latest/configurations/)

#### トランザクション要件

| 要件 | ScalarDB での対応 | 基盤DB選定の考慮 |
|---|---|---|
| ACID 必須（厳密直列化可能性） | Consensus Commit で `SERIALIZABLE` を設定 | 基盤DBのトランザクション機能は不要（ScalarDB が管理） |
| Snapshot Isolation で十分 | Consensus Commit で `SNAPSHOT`（デフォルト） | 性能優先の場合は NoSQL 系も適切 |
| 単一レコード操作のみ | `single-crud-operation` モードも選択可能 | 基盤DB固有のトランザクションを活用 |
| クロスデータベーストランザクション | Multi-storage 構成で実現 | 名前空間ごとに最適なDBを選択可能 |

#### データ構造

| データ特性 | 推奨基盤DB | 理由 |
|---|---|---|
| リレーショナル（正規化、JOIN 多用） | PostgreSQL, MySQL, Aurora | ScalarDB SQL で JOIN 可能。JDBC 経由で最も機能が充実 |
| ワイドカラム（大量カラム、スパースデータ） | Cassandra | ScalarDB のデータモデルと親和性が高い |
| 大規模キーバリュー | DynamoDB | マネージドサービスとしてのスケーラビリティ |
| グローバル分散 | Cosmos DB | マルチリージョン配置の容易さ |

#### クエリパターン

| クエリパターン | 必要な機能 | 推奨構成 |
|---|---|---|
| PK 完全一致 Get | 基本 Get 操作 | どの基盤 DB でも OK |
| パーティション内範囲スキャン | Scan with CK range | どの基盤 DB でも OK |
| クロスパーティションスキャン | `cross_partition_scan.enabled=true` | JDBC 系が望ましい（フィルタリング・ソート対応） |
| 複雑な JOIN | ScalarDB SQL | JDBC 系 DB 必須 |
| フルテキスト検索 | ScalarDB 外の仕組みが必要 | Elasticsearch 等と併用 |

### 4.2 非機能要件からの選定

#### 読み書きの比率

| 比率 | 推奨基盤DB | 理由 |
|---|---|---|
| 読み取り重視（Read 80%+） | PostgreSQL, Aurora Reader, DynamoDB（DAX付き） | 読み取りレプリカ、キャッシュ活用 |
| 書き込み重視（Write 50%+） | Cassandra, DynamoDB | 書き込みに最適化されたアーキテクチャ |
| 読み書き均等 | PostgreSQL, MySQL | バランスの取れた性能 |

#### レイテンシ要件

| 要件レベル | 目標値 | 推奨構成 |
|---|---|---|
| 超低レイテンシ | p99 < 10ms | DynamoDB（同一リージョン）、ローカルキャッシュ併用 |
| 低レイテンシ | p99 < 50ms | PostgreSQL/MySQL（同一AZ）、Cassandra（LOCAL_QUORUM） |
| 中程度 | p99 < 200ms | 一般的な JDBC 系 DB |
| 緩い | p99 < 1s | クロスリージョン構成も許容 |

**注意:** ScalarDB の Consensus Commit は基盤DB への約2倍のアクセスを必要とするため、基盤DB単体のレイテンシから約2〜3倍のオーバーヘッドを見込む必要がある。

#### スケーラビリティ要件

VLDB 2023 の論文によると、ScalarDB は15ノード環境で3ノード環境に対して **4.6倍のスループット** を達成し、**92%のスケーラビリティ効率** を実現している。

| 規模 | 推奨基盤DB | 理由 |
|---|---|---|
| 小規模（〜100万レコード） | PostgreSQL, MySQL, SQLite | 運用の簡潔さ |
| 中規模（〜10億レコード） | PostgreSQL（パーティショニング）、Aurora、Cassandra | 水平分散の開始点 |
| 大規模（10億レコード超） | Cassandra, DynamoDB | ほぼ無限のスケーラビリティ |
| マルチリージョン | DynamoDB Global Tables, Cosmos DB | グローバル分散のネイティブサポート |

参考: [ScalarDB: Universal Transaction Manager for Polystores (VLDB'23)](https://dl.acm.org/doi/10.14778/3611540.3611563)

#### データサイズ

| データサイズ | 推奨 | 注意点 |
|---|---|---|
| 〜100GB | 単一 JDBC DB | 運用コスト最小 |
| 100GB〜1TB | Aurora, Cassandra 小クラスタ | オートスケーリング活用 |
| 1TB〜10TB | Cassandra 中クラスタ, DynamoDB | パーティション設計が重要 |
| 10TB 超 | DynamoDB, Cassandra 大クラスタ + S3（コールドデータ） | ScalarDB のオブジェクトストレージ対応も活用 |

#### 可用性要件（RPO/RTO）

| SLA | RPO | RTO | 推奨構成 |
|---|---|---|---|
| 99.9% | < 1時間 | < 1時間 | 単一リージョン、マルチAZ 冗長 |
| 99.95% | < 15分 | < 30分 | Aurora マルチAZ、Cassandra RF=3 |
| 99.99% | < 1分 | < 5分 | マルチリージョン構成、DynamoDB Global Tables |
| 99.999% | 0（ゼロデータロス） | < 1分 | Cosmos DB マルチリージョン + 同期レプリケーション |

---

## 5. Consensus Commit メタデータオーバーヘッド

ScalarDB の Consensus Commit プロトコルは、各レコードにトランザクションメタデータを付与する。

**付与されるメタデータ:**
- `tx_id`: トランザクションID
- `tx_state`: トランザクション状態
- `tx_version`: バージョン番号
- `tx_prepared_at`: Prepare時刻
- `tx_committed_at`: Commit時刻
- `before_*` カラム: 前バージョンデータ（ロールバック用）

**オーバーヘッドの影響:**
- 読み書きで基盤データベースへのアクセスが約2倍になる
- Coordinator テーブルにトランザクション状態を記録するための追加アクセスが発生
- Secondary Index と組み合わせると更にオーバーヘッドが増大

**性能最適化のための設定:**

| 設定 | デフォルト | 効果 |
|---|---|---|
| `parallel_executor_count` | 128 | 並列実行スレッド数。CPU コア数の2〜4倍が目安 |
| `async_commit.enabled` | false | 非同期コミットで書き込みレイテンシを削減 |
| `async_rollback.enabled` | false | 非同期ロールバックでエラー時のレイテンシを削減 |
| `coordinator.group_commit.enabled` | false | グループコミットで書き込みスループット向上 |
| `scan_fetch_size` | 10 | スキャン時のバッチ取得件数。大量読み取り時は増加を検討 |

参考: [Consensus Commit Protocol | ScalarDB Documentation](https://scalardb.scalar-labs.com/docs/latest/consensus-commit/), [ScalarDB Configurations](https://scalardb.scalar-labs.com/docs/latest/configurations/)

### ストレージオーバーヘッド（Consensus Commitメタデータ）

ScalarDBのConsensus Commitは各レコードにトランザクション管理用のメタデータカラムを付加する。容量計画時にはこのオーバーヘッドを考慮すること。

#### メタデータカラム構成

| カラム | 型 | サイズ目安 | 用途 |
|--------|-----|----------|------|
| `tx_id` | VARCHAR | ~40-60 bytes | トランザクションID |
| `tx_state` | INT | 4 bytes | トランザクション状態 |
| `tx_version` | INT | 4 bytes | バージョン番号 |
| `tx_prepared_at` | BIGINT | 8 bytes | Prepare時刻 |
| `tx_committed_at` | BIGINT | 8 bytes | Commit時刻 |
| `before_*` カラム | 各カラムと同型 | アプリデータと同サイズ | 更新前イメージ |

**固定メタデータオーバーヘッド**: ~80-100 bytes/record
**before-imageオーバーヘッド**: アプリデータサイズ × 1.0（全カラム分）

#### ストレージ増加率の目安

| アプリデータサイズ/record | メタデータ込み | 増加率 |
|--------------------------|---------------|--------|
| 100 bytes | ~300 bytes | 約3倍 |
| 500 bytes | ~1,100 bytes | 約2.2倍 |
| 2,000 bytes | ~4,100 bytes | 約2倍 |

#### Coordinatorテーブルのストレージ

Coordinatorテーブルにはコミット済みトランザクションの状態が記録される。

- 1レコード/トランザクション: ~100 bytes
- 例: 100万Tx/日 = ~100MB/日 = ~3GB/月
- **TTL設定またはアーカイブ戦略の策定が必要**（現時点で自動パージ機能は未提供）

#### 3.17 Transaction Metadata Decoupling使用時

メタデータが別テーブルに分離されるため、アプリケーションデータテーブル自体はクリーンに保たれる。ただし:
- 合計ストレージ使用量は同等
- Read時にVIEW経由のJOINが発生するため、I/O量が増加する可能性がある

---

## 6. 性能・可用性要件の整理

### 6.1 レイテンシ（p50, p95, p99）

ScalarDB の Consensus Commit プロトコルでは、1回のトランザクションで基盤DB へ複数回アクセスが発生する。以下は一般的な目安値である。

**単一レコード Get 操作（Partition Key 指定）:**

| パーセンタイル | JDBC (PostgreSQL, 同一AZ) | Cassandra (LOCAL_QUORUM) | DynamoDB (同一リージョン) |
|---|---|---|---|
| p50 | 3〜8ms | 3〜10ms | 5〜15ms |
| p95 | 10〜30ms | 15〜40ms | 15〜50ms |
| p99 | 20〜80ms | 30〜100ms | 30〜100ms |

**単一レコード Write 操作（Insert/Update）:**

| パーセンタイル | JDBC (PostgreSQL) | Cassandra | DynamoDB |
|---|---|---|---|
| p50 | 10〜30ms | 10〜25ms | 15〜40ms |
| p95 | 30〜80ms | 30〜70ms | 40〜100ms |
| p99 | 50〜200ms | 50〜150ms | 60〜200ms |

**注意:** 上記はあくまで一般的な目安であり、実際の値はハードウェア構成、ネットワーク、データサイズ、同時実行数に大きく依存する。公式のベンチマーク結果は [TPC-C による ScalarDB のベンチマーク方法について](https://medium.com/scalar-engineering/tpc-c%E3%81%AB%E3%82%88%E3%82%8Bscalardb%E3%81%AE%E3%83%99%E3%83%B3%E3%83%81%E3%83%9E%E3%83%BC%E3%82%AF%E6%96%B9%E6%B3%95%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6-263b660ba028) を参照。

### 6.2 スループット（TPS/QPS）

VLDB 2023 論文のベンチマーク結果に基づく指標:

| 構成 | ワークロード | 参考スループット | スケーラビリティ |
|---|---|---|---|
| 3ノード Cassandra | TPC-C | ベースライン | - |
| 15ノード Cassandra | TPC-C | 約4.6倍（92%効率） | ほぼ線形スケール |
| 最適化適用後 | MariaDB | 最大87%性能向上 | - |
| 最適化適用後 | PostgreSQL | 最大48%性能向上 | - |

### OCC競合率のモデリング

ScalarDBのConsensus Commitは楽観的並行性制御（OCC）を採用している。競合率が高い環境ではリトライが増加し、スループットが急激に低下する。

#### 競合確率の近似式

```
P(conflict) ≈ 1 - (1 - k/N)^(C-1)

k: 1トランザクションの書き込みレコード数
N: 競合対象となるレコードの総数（ホットレコード数）
C: 同時実行トランザクション数
```

#### 実用的な閾値

| 競合率 | 状態 | アクション |
|--------|------|-----------|
| < 5% | 良好 | リトライによるオーバーヘッドは無視できる |
| 5% - 15% | 注意 | リトライ頻発によるレイテンシ増加が顕在化。PK設計の見直しを検討 |
| 15% - 30% | 危険 | スループットが急激に低下。パーティション分割、トランザクションスコープ縮小を検討 |
| > 30% | 設計変更必須 | ホットスポットの解消、バケッティング、アクセスパターンの根本的見直し |

#### 監視メトリクス

- `TransactionConflictException`の発生頻度を監視
- 閾値アラート: 10%超でWarning、20%超でCritical（バッチ処理の一時停止を検討）

### Consensus Commitレイテンシの内訳（目安）

1トランザクション（1 Read + 1 Write）の典型的なレイテンシ分解:

| フェーズ | 処理内容 | 目安 |
|---------|---------|------|
| Begin | トランザクションID生成 | ~0.1ms（Piggyback Begin有効時: 0ms） |
| Read | gRPC RTT + DB Read + メタデータ検証 | ~6-14ms |
| Write | ローカルワークスペース記録 | ~0.1ms（Write Buffering有効時: バッファ蓄積のみ） |
| Prepare | 条件付き書き込み + 前バージョンバックアップ | ~8-23ms |
| Validate | Read Setの再検証（Serializable時のみ） | ~3-10ms |
| Commit | Coordinatorテーブル記録 + レコード状態更新 | ~6-16ms |
| **合計（SI, 最適化なし）** | | **~20-53ms** |
| **合計（SI, 全最適化あり）** | | **~14-35ms** |
| **合計（Serializable, 全最適化あり）** | | **~17-45ms** |

※ 同一AZ内、基盤DBがRDBMS（PostgreSQL/MySQL）の場合の目安

### 6.3 可用性（99.9%, 99.99% 等）

| SLA目標 | 年間許容ダウンタイム | 推奨構成 |
|---|---|---|
| 99.9% | 約8.76時間 | 単一リージョン、マルチAZ。Cassandra RF=3 or Aurora マルチAZ |
| 99.95% | 約4.38時間 | マルチAZ + 自動フェイルオーバー |
| 99.99% | 約52.6分 | マルチリージョン構成。DynamoDB Global Tables or Cosmos DB |
| 99.999% | 約5.26分 | マルチリージョン + アクティブ-アクティブ。運用の成熟度も必要 |

**ScalarDB Cluster のデプロイ:**
- Kubernetes 1.31〜1.34 上で動作（EKS, AKS, OpenShift 対応）
- ポート: 60053（API）、8080（GraphQL）、9080（メトリクス）
- Pod の水平スケーリングによるスループット向上が可能

参考: [Requirements | ScalarDB Documentation](https://scalardb.scalar-labs.com/docs/latest/requirements/)

### 6.4 データ耐久性

| 要件 | 対応方法 | 目標 |
|---|---|---|
| ノード障害耐性 | Cassandra RF=3, PostgreSQL ストリーミングレプリケーション | ノード1台喪失でもデータ損失なし |
| AZ 障害耐性 | マルチAZ 配置、Aurora マルチAZ | AZ 障害でもデータ損失なし |
| リージョン障害耐性 | クロスリージョンレプリケーション | RPO に応じた設定 |
| 論理的破壊への耐性 | ポイントインタイムリカバリ（PITR） | 任意の時点への復元 |

**Consensus Commit のデータ整合性保証:**
- Coordinator テーブルにトランザクション状態を記録
- 障害時にはトランザクション状態から自動リカバリ
- Serializable を保証（`SERIALIZABLE` 設定時）

> **注意**: ScalarDBがStrict Serializabilityを達成するかどうかは、基盤となるストレージのクロック同期精度に依存する。Strict Serializabilityはリアルタイム順序の保証を要求するため、ノード間のクロックスキューが大きい環境では保証されない場合がある。

### 6.5 リカバリ時間

| シナリオ | 一般的な RTO | 推奨対策 |
|---|---|---|
| 単一ノード障害 | 数秒〜数分 | Cassandra: 自動修復、JDBC: フェイルオーバー |
| AZ 障害 | 数分〜数十分 | マルチAZ レプリカへの自動切り替え |
| リージョン障害 | 数十分〜数時間 | DNS ベースの切り替え、マルチリージョン構成 |
| データ破損 | 数時間 | PITR からの復元 |
| ScalarDB Cluster Pod 障害 | 数秒〜数十秒 | Kubernetes の自動 Pod 再起動 |

---

## 7. Virtual Tables（ScalarDB 3.17新機能）

ScalarDB 3.17で導入された**Virtual Tables**は、ストレージ抽象化レイヤーにおいて、プライマリキーによる2テーブルの論理的結合をサポートする機能である。

### 概要

Virtual Tablesは、物理的には異なるテーブル（場合によっては異なるデータベース上）に存在するデータを、論理的に1つのテーブルとして扱えるようにする。これにより、以下のようなユースケースが効率化される。

**適用場面:**
- マイクロサービス間で共有する必要があるマスタデータの論理統合
- インデックステーブルパターンにおけるベーステーブルとインデックステーブルの統合ビュー
- 段階的なデータ移行時の旧テーブルと新テーブルの透過的アクセス

**制約事項:**
- 結合条件はプライマリキーに限定される
- 現時点では2テーブルの結合のみサポート
- 書き込み操作は元テーブルに対して行う

---

## 8. 設計判断フローチャート

ScalarDB でのデータモデル設計は以下の順序で進めることを推奨する。

1. **アクセスパターンの洗い出し** -- どのクエリが最も頻繁に実行されるかを特定
2. **Partition Key の決定** -- 最頻出クエリの検索条件を Partition Key に選定。カーディナリティの高い列を選ぶ
3. **Clustering Key の決定** -- パーティション内での範囲検索やソートの要件に基づいて決定
4. **インデックステーブルの検討** -- Secondary Index ではなく、代替テーブル方式を優先的に検討
5. **基盤データベースの選定** -- 非機能要件（レイテンシ、スケーラビリティ、可用性）に基づいて決定
6. **マルチストレージ構成の検討** -- 異なる特性のデータは異なる基盤DB に配置

**キーポイント:**
- ScalarDB は NoSQL 的なクエリ駆動型の設計哲学を採用している
- 単一パーティション検索を最優先に設計する
- Secondary Index は最終手段とし、インデックステーブルパターンを優先する
- Consensus Commit のメタデータオーバーヘッド（約2倍のDB アクセス）を性能見積もりに組み込む
- VLDB 2023 論文の通り、ほぼ線形なスケーラビリティが実現可能だが、パーティション設計が前提条件

---

## 想定される機能要件の整理

### CRUD 操作

ScalarDB は以下の CRUD API を提供する（Java API Guide 参照）。

| 操作 | ScalarDB API | 説明 | 性能特性 |
|---|---|---|---|
| Create | `Insert`, `Put` | レコード挿入。`Insert` は既存レコードがあればエラー | Partition Key 指定で O(1) |
| Read (単一) | `Get` | Primary Key 指定で1レコード取得 | 最も効率的。p50 < 数ms |
| Read (複数) | `Scan` | パーティション内の範囲検索 | CK 範囲指定で効率的 |
| Update | `Update`, `Upsert` | レコード更新。`Upsert` は存在しなければ挿入 | 事前 Get が必要（Put の場合） |
| Delete | `Delete` | Primary Key 指定で削除 | 暗黙的な事前読み取りが有効 |

**重要:** `Put` 操作は **ScalarDB 3.13 で非推奨（deprecated）** となった。新規開発では以下の使い分けが必須である:
- `Insert`: 新規レコード作成（既存レコードがあればエラー）
- `Update`: 既存レコード更新（存在しなければエラー）
- `Upsert`: 存在すれば更新、存在しなければ挿入

既存コードで `Put` を使用している場合は、段階的に上記APIへの移行を推奨する。

参考: [ScalarDB Java API Guide](https://scalardb.scalar-labs.com/docs/3.16/api-guide/)

### 検索・フィルタリング

| 検索パターン | 実装方法 | 効率性 | 推奨度 |
|---|---|---|---|
| PK 完全一致 | `Get` | 最高 | 常に推奨 |
| PK + CK 範囲 | `Scan` with boundaries | 高い | パーティション内では推奨 |
| Secondary Index | `Get`/`Scan` with indexKey | 中〜低 | 低頻度のみ |
| クロスパーティションスキャン + フィルタ | `Scan.all()` + `where()` | 低い | 最終手段 |
| 複合条件フィルタリング | `ConditionBuilder`（CNF/DNF 形式） | DB依存 | JDBC 系で有効 |

フィルタリング条件は **論理積標準形（CNF: AND of ORs）** または **論理和標準形（DNF: OR of ANDs）** で指定する必要がある。

### 集計・分析

ScalarDB 単体ではリアルタイム集計の直接的なサポートは限定的であるが、以下のアプローチが可能。

| 手法 | 説明 | 適用場面 |
|---|---|---|
| ScalarDB Analytics（Spark 連携） | Spark 3.4/3.5 との統合で分析クエリを実行 | 大規模バッチ集計 |
| ScalarDB SQL | SQL の集約関数を活用 | 中小規模の集計 |
| アプリケーション側集計 | Scan で取得後、アプリケーションで集計 | シンプルな集計 |
| マテリアライズドビュー（手動） | 集計結果を別テーブルに格納 | リアルタイム集計が必要な場合 |

### バッチ処理

| 手法 | 説明 | スループット目安 |
|---|---|---|
| トランザクションバッチ | 1トランザクション内で複数操作を実行 | 数百〜数千 ops/tx |
| ScalarDB Analytics | Spark ジョブによる大規模バッチ処理 | 数百万レコード/ジョブ |
| 並列トランザクション | 複数スレッドから独立したトランザクションを並列実行 | `parallel_executor_count`（デフォルト128）で制御 |

### リアルタイム処理

| 要件 | ScalarDB での対応 | 注意点 |
|---|---|---|
| OLTP（単一レコード操作） | Get/Put/Insert/Update/Delete | 最も得意な領域 |
| イベント駆動処理 | ScalarDB 単体では非対応。外部キューとの連携が必要 | Kafka + ScalarDB の組み合わせ |
| ストリーム処理 | ScalarDB は永続化レイヤーとして使用 | Flink/Spark Streaming と組み合わせ |

---

## 主要参考文献

- [Model Your Data | ScalarDB Documentation](https://scalardb.scalar-labs.com/docs/latest/data-modeling/)
- [データをモデル化する | ScalarDB Documentation（日本語）](https://scalardb.scalar-labs.com/ja-jp/docs/3.14/data-modeling/)
- [ScalarDB Java API Guide](https://scalardb.scalar-labs.com/docs/3.16/api-guide/)
- [Consensus Commit Protocol | ScalarDB Documentation](https://scalardb.scalar-labs.com/docs/latest/consensus-commit/)
- [ScalarDB Configurations](https://scalardb.scalar-labs.com/docs/latest/configurations/)
- [ScalarDB Schema Loader](https://scalardb.scalar-labs.com/docs/3.13/schema-loader/)
- [ScalarDB Overview](https://scalardb.scalar-labs.com/docs/3.13/overview/)
- [Multi-Storage Transactions](https://scalardb.scalar-labs.com/docs/latest/multi-storage-transactions/)
- [Requirements | ScalarDB Documentation](https://scalardb.scalar-labs.com/docs/latest/requirements/)
- [ScalarDB: Universal Transaction Manager for Polystores (VLDB'23)](https://dl.acm.org/doi/10.14778/3611540.3611563)
- [TPC-C による ScalarDB のベンチマーク方法について](https://medium.com/scalar-engineering/tpc-c%E3%81%AB%E3%82%88%E3%82%8Bscalardb%E3%81%AE%E3%83%99%E3%83%B3%E3%83%81%E3%83%9E%E3%83%BC%E3%82%AF%E6%96%B9%E6%B3%95%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6-263b660ba028)
- [ScalarDB Benchmark Tools (GitHub)](https://github.com/scalar-labs/scalardb-benchmarks)
