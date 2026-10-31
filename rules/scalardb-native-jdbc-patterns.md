---
description: ScalarDB Native JDBC rules — when to let an existing SQL application keep its native SQL on tables ScalarDB also manages, and how to configure and use the scalardb-native-jdbc driver safely beside Consensus Commit applications
globs:
  - "**/*.java"
  - "**/*.properties"
---

# ScalarDB Native JDBC Rules

Reference snapshot for **ScalarDB Native JDBC 3.20.0** (first release, 2026-10-30, Apache-2.0),
grounded on the upstream repository `scalar-labs/scalardb-native-jdbc` (`README.md`,
`docs/configuration.md`, `docs/transactions.md`, `docs/sql-support.md`). The OKF knowledge bundle
has **no concept for this driver yet** — cite the repository documents at the tag the project pins,
and say the answer is not bundle-pinned (@rules/okf-knowledge-bundle.md §5).

## What It Is — and Is Not

The driver **wraps the database's own JDBC driver**. The application keeps the database's native
SQL and native transactions. Statements on ordinary tables pass through unchanged; statements on
ScalarDB-managed tables are rewritten to read only committed data and to write the `tx_*` /
`before_*` transaction metadata that Consensus Commit checks. **The driver makes no call into
ScalarDB.**

| It is | It is not |
|-------|-----------|
| A way for a legacy SQL application to share tables with ScalarDB applications on **one database**, ACID across ordinary and ScalarDB tables in one native transaction | A ScalarDB client — it never talks to ScalarDB Core or Cluster |
| A driver that removes the ScalarDB SQL interface and its parsing/transaction hop for that application | A dialect translator — the SQL is the database's own, and `jdbc:scalardb-native:` adds no portability |
| Compatible with both metadata layouts (inline and decoupled `<table>_tx_metadata`) | A cross-database transaction manager — **one database per connection, a transaction never spans databases** |

Edition: none. It runs against any database a ScalarDB **Community** (Core) or Enterprise
deployment writes to, because it only reads and writes Consensus Commit's metadata.

## When To Choose It

Decide among the SQL-shaped paths before writing code (`skills/common/references/interface-matrix.md`
§ SQL Access Paths):

| Situation | Path |
|-----------|------|
| An existing JDBC/ORM application must keep running its native SQL on tables that ScalarDB applications also write, all on **one** database | **Native JDBC** (this document) |
| A new application wants ScalarDB's multi-database transactions through SQL | ScalarDB SQL (JDBC driver `jdbc:scalardb:`; Enterprise Premium) — @rules/scalardb-jdbc-patterns.md |
| SQL tools, BI, psql or non-Java PostgreSQL drivers must query ScalarDB-managed data | PostgreSQL wire protocol — @rules/scalardb-postgres-frontend-patterns.md |
| The transaction must span databases or services | Not this driver — @rules/scalardb-2pc-patterns.md |

Record the choice in the transaction design document, including the fact that the application
and every ScalarDB application sharing the tables **run at the same isolation level** (below).

## Dependency and URL

```groovy
implementation("com.scalar-labs:scalardb-native-jdbc:<VERSION>")   // Maven Central
implementation("org.postgresql:postgresql:<VERSION>")             // the vendor driver — supplied by the application
```

- Driver line `3.20.x` tracks the ScalarDB `3.20.x` line; 3.20.0 was tested against ScalarDB
  3.19.1 and ScalarDB 3.20 writes the same metadata columns and states. Java 11 or later.
- The POM pulls **JSQLParser 5.4**; an application that also uses JSQLParser must pin 5.4 or risk
  `NoSuchMethodError` at run time.
- The URL is the vendor URL with `scalardb-native:` inserted after `jdbc:`:

| Engine | URL |
|--------|-----|
| PostgreSQL | `jdbc:scalardb-native:postgresql://host:5432/db` |
| MySQL | `jdbc:scalardb-native:mysql://host:3306/db` |
| MariaDB | `jdbc:scalardb-native:mariadb://host:3306/db` |
| SQL Server | `jdbc:scalardb-native:sqlserver://host:1433;databaseName=db` |
| Oracle | `jdbc:scalardb-native:oracle:thin:@host:1521/db` |

Every ScalarDB dependency pin follows @rules/dependency-versions.md — look the version up, never
copy `<VERSION>` from an example.

## Driver Properties

All driver properties start with `scalar.db.native_jdbc.`; anything else goes to the vendor driver
unchanged. Set them as connect properties (HikariCP: `addDataSourceProperty`). Only the first two
may also appear in the URL; an unknown `scalar.db.native_jdbc.` key, a malformed value, or any
other driver property in the URL refuses the connection with `08001`.

| Property | Default | Meaning |
|----------|---------|---------|
| `scalar.db.native_jdbc.catalog_ttl_millis` | `60000` | How long the driver trusts its copy of ScalarDB's catalog (max `3600000`). Lower it while DDL is being applied through ScalarDB |
| `scalar.db.native_jdbc.inflight_wait_millis` | `0` | At READ COMMITTED only: how long a write waits for an in-flight row before failing with `40001`. `0` fails immediately |
| `scalar.db.native_jdbc.metadata_schema` | `scalardb` | Schema holding ScalarDB's `metadata` (and `virtual_tables` for the decoupled layout) |
| `scalar.db.native_jdbc.coordinator_namespace` | `coordinator` | Must match `scalar.db.consensus_commit.coordinator.namespace` of the ScalarDB applications |
| `scalar.db.native_jdbc.allow_no_catalog` | `false` | Accept a database without ScalarDB's catalog; otherwise refused with `08004` |
| `scalar.db.native_jdbc.predicate_checks` | `false` | Experimental. Checks whether a `WHERE` actually matches an in-flight row before failing a read |

## Isolation Levels Must Agree

Driver transactions are the database's own (`setAutoCommit(false)`, `commit()`, `rollback()`), run
at the level set with `setTransactionIsolation`. That level also decides how they are isolated
from Consensus Commit transactions on the same tables, so **every ScalarDB application writing the
same tables must set the matching levels** — a weaker level on either side breaks what the other
side's level protects. The default is SNAPSHOT.

| Driver `setTransactionIsolation` | `scalar.db.consensus_commit.isolation_level` | `scalar.db.jdbc.isolation_level` |
|----------------------------------|----------------------------------------------|----------------------------------|
| `TRANSACTION_READ_COMMITTED` | `READ_COMMITTED` | `REPEATABLE_READ` |
| `TRANSACTION_REPEATABLE_READ` (= SNAPSHOT, driver default) | `SNAPSHOT` (ScalarDB default) | `REPEATABLE_READ` |
| `TRANSACTION_SERIALIZABLE` | `SERIALIZABLE` | `SERIALIZABLE` on PostgreSQL; `REPEATABLE_READ` on MySQL / MariaDB / SQL Server; **refused on Oracle** (`0AN01`) |

`TRANSACTION_READ_UNCOMMITTED` is refused. SERIALIZABLE is implemented per engine (SSI on
PostgreSQL, shared locks held to commit on MySQL / MariaDB / SQL Server); design the retry budget
accordingly. Put the agreed level in `work/version-decisions.json` next to the ScalarDB pin so a
later `scalardb:config` run does not silently diverge.

## Conflicts: `40001` Means Roll Back and Retry

An **in-flight row** is one a ScalarDB transaction has prepared but not yet committed or rolled
back. The driver fails rather than reads around it:

- At SNAPSHOT and SERIALIZABLE, a statement that reaches an in-flight row fails with `40001`.
- A write that would lose an update fails with `40001`, whether the other writer is ScalarDB or
  another driver transaction; at SNAPSHOT this includes a row changed after the snapshot.
- At READ COMMITTED, reads never fail on in-flight rows (they return the last committed value);
  writes to in-flight rows fail unless `inflight_wait_millis` makes them wait.
- After `40001` the transaction is **rollback-only** — roll back and retry the whole unit of work
  with a new transaction, the same way `CommitConflictException` is handled in
  @rules/scalardb-exception-handling.md. Engine errors that end the transaction (MySQL lock wait
  timeouts with `innodb_rollback_on_timeout`, SQL Server batch-aborting errors) leave it
  rollback-only too.
- Reads through subqueries, `GROUP BY`, `DISTINCT`, derived tables, CTEs or `UNION` are **not
  checked** for later changes: read the rows you will write with a direct `SELECT` (or
  `SELECT ... FOR UPDATE`) first.
- `setReadOnly(true)` transactions refuse writes to ScalarDB tables with `25006`.

## Statements Refused on ScalarDB Tables (`0AN01`)

Supported: `SELECT` (including joins with ordinary tables, subqueries, aggregates, CTEs, window
functions), multi-row `INSERT ... VALUES`, single-table `UPDATE` / `DELETE` by key or by any
`WHERE`, locking reads, batches, generated keys, `RETURNING` on `INSERT` (PostgreSQL, MariaDB).

Refused, so the application must be rewritten before the driver is adopted:

- `INSERT ... SELECT` into or out of a ScalarDB table; `SELECT INTO`; `CREATE TABLE AS SELECT`
- Upserts: `ON CONFLICT`, `MERGE`, `ON DUPLICATE KEY UPDATE`, `INSERT IGNORE`
- `UPDATE` / `DELETE` that reads another table (`FROM`, `USING`, joins, subqueries), statements
  that write several tables, writable CTEs — **read the keys first, then write by key in the same
  transaction**
- `UPDATE` of a key column; `RETURNING` on `UPDATE` / `DELETE`
- DDL and `TRUNCATE` on a ScalarDB table (including views and indexes); `CALL` / `EXEC`;
  functions that run SQL given as text (`dblink`, `OPENQUERY`, ...)
- Writes naming `tx_*` / `before_*` columns; statements the driver cannot parse

Reading a `tx_*` / `before_*` column fails as a missing column; naming ScalarDB's own metadata
tables returns `42000`. `SELECT *` on an inline-layout table returns only the data columns.

**Passthrough** (`setClientInfo("scalar.db.native_jdbc.passthrough", "true")` in autocommit mode)
sends statements unchanged — for tables ScalarDB does not manage only. Anything naming a ScalarDB
table, ScalarDB's schema or the coordinator namespace is still refused, even inside comments.

## Setup, Grants and Database Settings

- Run `scalardb-native-tools setup` once per database before the first connection (it creates the
  read views the driver needs); `check` verifies, `teardown` undoes, `add` registers a table while
  applications run. `--backfill` writes metadata for tables **imported** into ScalarDB (off by
  default); `backfill` repairs rows whose metadata is NULL. Treat the tools run as a migration
  step with an owner, not as a developer convenience.
- The application user needs `SELECT` on `scalardb.metadata` (and `scalardb.virtual_tables` for
  decoupled tables), its normal privileges on each ScalarDB table (and `<table>_tx_metadata` when
  decoupled), and `SELECT` on each read view — `scalardb-native-tools setup --grant <user>`.
  Missing catalog access refuses the connection with `42501`; a missing view grant fails
  statements with `55000`.
- On PostgreSQL before 15, SQL Server and Oracle the read view runs with its **owner's** rights, so
  column privileges on the base table do not apply through it — grant the view only to users who
  may read every column. Row-level security still applies.
- Never create views, triggers, procedures, functions or cascading foreign keys over ScalarDB
  tables: they reach the rows without ScalarDB's protocol. `check` reports the ones it finds.

| Engine | Required setting | If wrong |
|--------|------------------|----------|
| MySQL | Strict `sql_mode` (`STRICT_TRANS_TABLES` or `STRICT_ALL_TABLES`) | `INSERT` refused (`0AN01`) |
| MySQL, MariaDB | Vendor driver `useAffectedRows` left `false` | Connection refused (`08004`) |
| SQL Server | `READ_COMMITTED_SNAPSHOT ON`, `ALLOW_SNAPSHOT_ISOLATION ON`, `XACT_ABORT` off | Connection refused (`08004`) |
| SQL Server | `QUOTED_IDENTIFIER`, `ANSI_NULLS`, `ANSI_PADDING`, `ANSI_WARNINGS` on | Writes fail |

Known driver issues at 3.20.0: pgjdbc before 42.7 fails `Connection.abort()` on Java 24+; MariaDB
Connector/J 3.4 is outside the supported range.

## Review Checklist

A design or code review that meets this driver asks:

1. Is every ScalarDB application on the same tables pinned to the **same isolation level** (table
   above), and is that recorded?
2. Does the application retry on `40001` with a new transaction, and never swallow it?
3. Are the refused statement shapes absent, or rewritten as read-keys-then-write-by-key?
4. Is `scalardb-native-tools setup` (and the grants) part of the deployment runbook, with the
   catalog TTL lowered during ScalarDB DDL?
5. Is there exactly one database per connection — no cross-database transaction expectation?
6. Does nothing (view, trigger, FK cascade, passthrough) reach a ScalarDB table around the driver?
