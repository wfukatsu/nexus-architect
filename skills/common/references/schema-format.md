# ScalarDB Schema Format Reference

The format facts: Schema Loader JSON fields, data types with their Java mapping, SQL DDL grammar
and the Schema Loader commands. How to choose the keys, indexes and tables that go into the file is
`rules/scalardb-schema-design.md`.

## JSON Format (Schema Loader)

### Structure

```json
{
  "<namespace>.<table_name>": {
    "transaction": true,
    "partition-key": ["<column_name>"],
    "clustering-key": ["<column_name> ASC", "<column_name> DESC"],
    "columns": {
      "<column_name>": "<DATA_TYPE>"
    },
    "secondary-index": ["<column_name>"],
    "compaction-strategy": "LCS",
    "ru": 5000
  }
}
```

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `transaction` | boolean | No | `true` | Include transaction metadata columns |
| `partition-key` | string[] | Yes | — | Partition key column names |
| `clustering-key` | string[] | No | — | Clustering key columns with optional `ASC`/`DESC` |
| `columns` | object | Yes | — | Column name → data type mapping |
| `secondary-index` | string[] | No | — | Columns to create indexes on |
| `compaction-strategy` | string | No | — | Cassandra only: `LCS`, `STCS`, `TWCS` |
| `ru` | number | No | — | DynamoDB/Cosmos DB: Request Units |
| `transaction-metadata-decoupling` | boolean | No | `false` | Separate metadata into `_data` and `_tx_metadata` tables |

### Data Types

| Type | Java Type | Description |
|------|-----------|-------------|
| `BOOLEAN` | `boolean` | true/false |
| `INT` | `int` | 32-bit integer |
| `BIGINT` | `long` | 64-bit integer |
| `FLOAT` | `float` | 32-bit floating point |
| `DOUBLE` | `double` | 64-bit floating point |
| `TEXT` | `String` | Variable-length string |
| `BLOB` | `byte[]`/`ByteBuffer` | Binary data |
| `DATE` | `LocalDate` | Date without time |
| `TIME` | `LocalTime` | Time without date |
| `TIMESTAMP` | `LocalDateTime` | Date and time without timezone |
| `TIMESTAMPTZ` | `Instant` | Date and time with timezone |

### Complete Example

```json
{
  "sample.customers": {
    "transaction": true,
    "partition-key": ["customer_id"],
    "columns": {
      "customer_id": "INT",
      "name": "TEXT",
      "credit_limit": "INT",
      "credit_total": "INT"
    }
  },
  "sample.orders": {
    "transaction": true,
    "partition-key": ["customer_id"],
    "clustering-key": ["timestamp"],
    "columns": {
      "customer_id": "INT",
      "timestamp": "BIGINT",
      "order_id": "TEXT"
    },
    "secondary-index": ["order_id"]
  },
  "sample.statements": {
    "transaction": true,
    "partition-key": ["order_id"],
    "clustering-key": ["item_id"],
    "columns": {
      "order_id": "TEXT",
      "item_id": "INT",
      "count": "INT"
    }
  },
  "sample.items": {
    "transaction": true,
    "partition-key": ["item_id"],
    "columns": {
      "item_id": "INT",
      "name": "TEXT",
      "price": "INT"
    }
  }
}
```

## SQL DDL Format (ScalarDB SQL)

### Equivalent SQL

```sql
CREATE COORDINATOR TABLES IF NOT EXIST;

CREATE NAMESPACE IF NOT EXISTS sample;

CREATE TABLE IF NOT EXISTS sample.customers (
  customer_id INT PRIMARY KEY,
  name TEXT,
  credit_limit INT,
  credit_total INT
);

CREATE TABLE IF NOT EXISTS sample.orders (
  customer_id INT,
  "timestamp" BIGINT,
  order_id TEXT,
  PRIMARY KEY (customer_id, "timestamp")
);

CREATE INDEX IF NOT EXISTS ON sample.orders (order_id);

CREATE TABLE IF NOT EXISTS sample.statements (
  order_id TEXT,
  item_id INT,
  count INT,
  PRIMARY KEY (order_id, item_id)
);

CREATE TABLE IF NOT EXISTS sample.items (
  item_id INT PRIMARY KEY,
  name TEXT,
  price INT
);
```

### SQL DDL Syntax

```sql
-- Namespace
CREATE NAMESPACE [IF NOT EXISTS] <namespace> [WITH creation_options];
DROP NAMESPACE [IF EXISTS] <namespace> [CASCADE];

-- Table
CREATE TABLE [IF NOT EXISTS] [<namespace>.]<table> (
  <column> <data_type> [PRIMARY KEY | ENCRYPTED],
  ...
  PRIMARY KEY (<partition_keys> [, <clustering_keys>])
) [WITH [CLUSTERING ORDER BY (<column> ASC|DESC, ...)] [AND options]];

ALTER TABLE [<namespace>.]<table> ADD [COLUMN] [IF NOT EXISTS] <column> <type>;
ALTER TABLE [<namespace>.]<table> DROP [COLUMN] [IF EXISTS] <column>;
ALTER TABLE [<namespace>.]<table> RENAME COLUMN <old> TO <new>;
ALTER TABLE [<namespace>.]<table> RENAME TO <new_table>;
DROP TABLE [IF EXISTS] [<namespace>.]<table>;
TRUNCATE TABLE [<namespace>.]<table>;

-- Index
CREATE INDEX [IF NOT EXISTS] ON [<namespace>.]<table> (<column>);
DROP INDEX [IF EXISTS] ON [<namespace>.]<table> (<column>);

-- Coordinator tables
CREATE COORDINATOR TABLES [IF NOT EXIST];
TRUNCATE COORDINATOR TABLES;
DROP COORDINATOR TABLES [IF EXIST];
```

### Important SQL Notes

- Reserved words as column names must be quoted: `"timestamp"`, `"order"`, `"key"`
- `CREATE COORDINATOR TABLES` is ScalarDB-specific — creates the transaction coordinator metadata table
- Tables created via SQL DDL are transactional by default
- A partition key may be composite (several columns); a clustering key column takes `ASC` or `DESC`

## Schema Loader Commands

```bash
# Create tables
java -jar scalardb-schema-loader-<VERSION>.jar \
  --config database.properties -f schema.json --coordinator

# Alter tables (add columns, indexes)
java -jar scalardb-schema-loader-<VERSION>.jar \
  --config database.properties -f schema.json --alter

# Delete tables
java -jar scalardb-schema-loader-<VERSION>.jar \
  --config database.properties -f schema.json -D --coordinator

# Repair metadata
java -jar scalardb-schema-loader-<VERSION>.jar \
  --config database.properties -f schema.json --repair-all --coordinator

# Import existing tables
java -jar scalardb-schema-loader-<VERSION>.jar \
  --config database.properties -f schema.json -I
```
