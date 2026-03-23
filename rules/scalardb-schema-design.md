---
description: ScalarDB schema design rules — applies when writing or reviewing ScalarDB schema files (JSON or SQL)
globs:
  - "**/schema.json"
  - "**/schema.sql"
  - "**/*schema*.json"
  - "**/*schema*.sql"
---

# ScalarDB Schema Design Rules

## Transaction Flag

Set `"transaction": true` for tables that need ACID guarantees. This is the default but should be explicit:

```json
{
  "ns.table": {
    "transaction": true,
    "partition-key": ["id"],
    "columns": { "id": "INT", "name": "TEXT" }
  }
}
```

Mixing transactional and non-transactional tables in the same transaction is NOT supported.

## Partition Key Design

- **Even distribution**: Choose keys that distribute data evenly
- **Avoid hot partitions**: A single partition key value receiving most traffic causes bottlenecks
- **Common access patterns**: Partition keys should match the most common query patterns
- **Avoid monotonically increasing values** as the sole partition key (timestamps, auto-increment IDs)

Good:
```json
"partition-key": ["customer_id"]    // distributes by customer
```

Bad:
```json
"partition-key": ["created_at"]     // hot partition at current time
```

## Clustering Key Design

- Determines sort order within a partition
- Enables efficient range queries
- Specify direction with `ASC` or `DESC` suffix

```json
"clustering-key": ["timestamp DESC", "item_id ASC"]
```

## No JOIN in CRUD API

The CRUD API does not support JOINs. Design schemas for single-table access:

- **Denormalize**: Duplicate data across tables to avoid joins
- **Application-level joins**: Read from multiple tables in the same transaction
- **Design around access patterns**: Each table should serve specific query patterns

If JOINs are needed, use the SQL/JDBC interface (Cluster mode only).

## Secondary Index Guidelines

- Use for occasional lookups by non-key columns
- Each index adds write overhead
- Avoid indexing high-cardinality columns on some backends (Cassandra)
- Alternative: create a separate table with the indexed column as partition key

```json
"secondary-index": ["order_id"]     // enables Get by order_id
```

## Supported Data Types

`BOOLEAN`, `INT`, `BIGINT`, `FLOAT`, `DOUBLE`, `TEXT`, `BLOB`, `DATE`, `TIME`, `TIMESTAMP`, `TIMESTAMPTZ`

Choose the narrowest type that fits the data.

## SQL Reserved Words

When using SQL DDL, quote reserved words as column names:

```sql
CREATE TABLE ns.tbl (
  id INT PRIMARY KEY,
  "timestamp" BIGINT,    -- quoted
  "order" TEXT           -- quoted
);
```

## Schema JSON Required Fields

Every table definition MUST have:
- `partition-key` (array of column names)
- `columns` (object mapping column names to types)

Optional:
- `transaction` (default `true`)
- `clustering-key` (array with optional ASC/DESC)
- `secondary-index` (array of column names)

## Coordinator Tables

Coordinator tables are required for transactional operations. Create them with:
- Schema Loader: `--coordinator` flag
- SQL: `CREATE COORDINATOR TABLES IF NOT EXIST`
