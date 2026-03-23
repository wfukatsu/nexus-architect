# データモデル定義書テンプレート

> 本テンプレートは、ScalarDB 管理対象テーブルごとに作成してください。
> `[...]` の箇所をプロジェクト固有の情報で埋めてください。

---

## 1. テーブル概要

| 項目 | 内容 |
|------|------|
| テーブル名 | [namespace.table_name] |
| 所属サービス | [サービス名] |
| バックエンドDB | [MySQL / PostgreSQL / Cassandra / DynamoDB] |
| ScalarDB管理 | [Yes / No] |
| 想定レコード数 | [件数] |
| 想定成長率 | [月間: +X件 / 年間: +X件] |

---

## 2. カラム定義

| カラム名 | ScalarDB型 | NULL許可 | デフォルト | 説明 |
|---------|-----------|---------|-----------|------|
| [カラム名] | [型] | [Yes / No] | [値 / なし] | [...] |
| [カラム名] | [型] | [Yes / No] | [値 / なし] | [...] |
| [カラム名] | [型] | [Yes / No] | [値 / なし] | [...] |
| [カラム名] | [型] | [Yes / No] | [値 / なし] | [...] |

> **ScalarDB サポート型一覧:** INT, BIGINT, FLOAT, DOUBLE, TEXT, BOOLEAN, BLOB
>
> - `INT`: 32ビット整数
> - `BIGINT`: 64ビット整数
> - `FLOAT`: 単精度浮動小数点
> - `DOUBLE`: 倍精度浮動小数点
> - `TEXT`: 文字列（サイズ制限はバックエンドDBに依存）
> - `BOOLEAN`: 真偽値
> - `BLOB`: バイナリデータ

---

## 3. キー設計

| キー種別 | カラム名 | 選定理由 |
|---------|---------|---------|
| Partition Key | [カラム名] | [...] |
| Clustering Key | [カラム名 ASC/DESC] | [...] |
| Secondary Index | [カラム名] | 用途: [...] |

---

## 4. キー設計チェックリスト

- [ ] Partition Keyのカーディナリティは十分か（ホットスポット回避）
- [ ] Clustering Keyの順序は主要クエリパターンに合致しているか
- [ ] Secondary Indexはスキャン範囲が限定されるか（フルスキャン回避）
- [ ] Partition Key + Clustering Keyでレコードを一意に特定できるか

---

## 5. アクセスパターン

| パターン名 | 操作(CRUD) | 条件(WHERE) | 頻度 | レイテンシ要件 |
|-----------|-----------|------------|------|-------------|
| [パターン名] | [Create / Read / Update / Delete] | [条件式] | [高 / 中 / 低 または req/sec] | [ms] |
| [パターン名] | [Create / Read / Update / Delete] | [条件式] | [高 / 中 / 低 または req/sec] | [ms] |
| [パターン名] | [Create / Read / Update / Delete] | [条件式] | [高 / 中 / 低 または req/sec] | [ms] |

---

## 6. メタデータオーバーヘッド見積もり

| 項目 | 値 |
|------|-----|
| 1レコードあたりのユーザーデータサイズ | [バイト] |
| Consensus Commitメタデータサイズ | 約200-300バイト（tx_id, tx_version, tx_state, tx_prepared_at, before_*カラム） |
| オーバーヘッド率 | [メタデータサイズ / ユーザーデータサイズ × 100]% |

> **Transaction Metadata Decoupling 使用時:**
> メタデータは別テーブルに分離されるため、本テーブルのオーバーヘッドは削減されます。
> ただし、READオペレーションで追加のテーブル参照が発生するため、READレイテンシへの影響を評価してください。

---

## 7. ScalarDBスキーマ定義（出力）

```json
{
  "namespace": "[namespace]",
  "table": "[table_name]",
  "partition_key": ["[column]"],
  "clustering_key": ["[column]"],
  "columns": {
    "[column_name]": "[type]",
    "[column_name]": "[type]",
    "[column_name]": "[type]"
  },
  "secondary_index": ["[column]"]
}
```

---

## 8. バックエンドDB固有の最適化

### Cassandra

| 項目 | 設定値 | 理由 |
|------|--------|------|
| Compaction Strategy | [SizeTiered / Leveled / TimeWindow] | [...] |
| TTL | [秒数 / 無効] | [...] |
| Bucketing | [バケット戦略] | [...] |

### DynamoDB

| 項目 | 設定値 | 理由 |
|------|--------|------|
| GSI (Global Secondary Index) | [GSI定義] | [...] |
| Capacity Mode | [On-Demand / Provisioned] | [...] |
| TTL | [属性名 / 無効] | [...] |

### MySQL / PostgreSQL

| 項目 | 設定値 | 理由 |
|------|--------|------|
| 追加インデックス（ScalarDB SI以外） | [インデックス定義] | [...] |
| パーティショニング | [RANGE / HASH / LIST / なし] | [...] |
| その他の最適化 | [...] | [...] |
