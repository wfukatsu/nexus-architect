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

## Event Store Pattern (only when event sourcing is adopted)

Adopted per aggregate in the design's Read Model / CQRS / Event Sourcing decision, never by
default. Three tables and one procedure:

| Table | Partition key | Clustering key | Notes |
|-------|---------------|----------------|-------|
| `{aggregate}_events` | aggregate id | `sequence` (ascending) | Append-only: `event_type`, `payload` (JSON, IDs and values), `occurred_at`, `actor`, `correlation_id`. The aggregate's OCC scope is the *next* sequence: the writer reads the last row and inserts `sequence + 1` in the same transaction, so two concurrent commands conflict instead of interleaving |
| `{aggregate}_snapshots` | aggregate id | `sequence` (descending) | One row per snapshot, written every N events (record N) so a rebuild reads one snapshot plus at most N events — never the whole history on the request path |
| `{aggregate}_view` and projections | as the query needs | — | Ordinary ScalarDB tables written by a projector that stores its `last_sequence` per aggregate and is idempotent under redelivery; projection lag is a stated SLO, not a surprise |

- **Rebuild** is a documented procedure — snapshot + events → aggregate — and its time for the
  largest aggregate is measured, not estimated.
- **The state column of a state machine** (@rules/state-modeling.md §6) lives on the snapshot /
  view, and the transition history *is* the event table; do not keep a second history. The same holds for an **outbox** a state machine declares as its `history.store`: rows are then retained with a `published_at` marker (and a retention rule), never deleted after publish — a deleted outbox row is a lost history entry.
- **Never query the event table by anything but aggregate id** — secondary indexes on an
  append-only table are a contention source; that is what projections are for.

## Coordinator Tables

Coordinator tables are required for transactional operations. Create them with:
- Schema Loader: `--coordinator` flag
- SQL: `CREATE COORDINATOR TABLES IF NOT EXIST`
