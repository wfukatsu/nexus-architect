---
description: ScalarDB schema design rules — applies when writing or reviewing ScalarDB schema files (JSON or SQL)
globs:
  - "**/schema.json"
  - "**/schema.sql"
  - "**/*schema*.json"
  - "**/*schema*.sql"
---

# ScalarDB Schema Design Rules

How to choose keys, indexes and tables, and what a reviewer flags. The format itself — the
Schema Loader JSON fields, the data types with their Java mapping, the SQL DDL grammar, the
reserved-word quoting and the Schema Loader commands — is
`skills/common/references/schema-format.md`; write the file from that, decide its content from this.

## Transaction Flag

Set `"transaction": true` for tables that need ACID guarantees. It is the default, but make it
explicit. Mixing transactional and non-transactional tables in the same transaction is **not**
supported.

## Partition Key Design

- **Even distribution**: choose keys that distribute data evenly
- **Avoid hot partitions**: a single partition key value receiving most traffic is a bottleneck
- **Common access patterns**: the partition key matches the most common query
- **Avoid monotonically increasing values** as the sole partition key (timestamps, auto-increment IDs)
- **Avoid large partitions**: too many rows under one partition key

```json
"partition-key": ["customer_id"]    // good: distributes by customer
"partition-key": ["created_at"]     // bad: hot partition at the current time
```

## Clustering Key Design

The clustering key determines sort order within a partition and makes range queries along it
efficient; give each column its direction:

```json
"clustering-key": ["timestamp DESC", "item_id ASC"]
```

## No JOIN in CRUD API

The CRUD API has no JOIN. Design for single-table access: denormalize across tables, read several
tables in one transaction (an application-level join), and give each table the query pattern it
serves. Where a JOIN is unavoidable, that is the SQL/JDBC interface (Cluster mode only).

## Secondary Index Guidelines

- For occasional lookups by non-key columns; every index adds write overhead
- Avoid indexing high-cardinality columns on backends where that hurts (Cassandra)
- The alternative is a separate table with the indexed column as its partition key

```json
"secondary-index": ["order_id"]     // enables Get by order_id
```

## Data Types and Names

Choose the narrowest type that fits the data (the type list and its Java mapping are in the
reference). In SQL DDL, quote a reserved word used as a column name (`"timestamp"`, `"order"`).

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

Coordinator tables are required for transactional operations — the Schema Loader `--coordinator`
flag or `CREATE COORDINATOR TABLES IF NOT EXIST` (commands in the reference). A schema that creates
transactional tables and no coordinator tables is incomplete.
