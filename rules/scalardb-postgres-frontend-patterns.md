---
description: ScalarDB PostgreSQL wire protocol rules — the ScalarDB Cluster 3.20 PostgreSQL interface and the Apache-2.0 scalardb-postgres-frontend; when to offer SQL tools and PostgreSQL drivers access to ScalarDB-managed data, and what differs from PostgreSQL
globs:
  - "**/*.properties"
  - "**/*.sql"
---

# ScalarDB PostgreSQL Wire Protocol Rules

Reference snapshot for **ScalarDB Cluster 3.20.0** (PostgreSQL wire protocol support, Enterprise,
released 2026-10-30) and **scalardb-postgres-frontend 3.20.0** (Apache-2.0, released 2026-10-29).
Grounded on the ScalarDB 3.20.0 release notes and the upstream repository
`scalar-labs/scalardb-postgres-frontend` (`README.md`, `LIMITATIONS.md`). The OKF knowledge bundle
has **no 3.20 concept yet** — cite those sources and say the answer is not bundle-pinned
(@rules/okf-knowledge-bundle.md §5).

## What It Is

A PostgreSQL-compatible SQL interface in front of ScalarDB. Clients speak the PostgreSQL wire
protocol — `psql`, the PostgreSQL JDBC driver, ORMs, BI tools, any language's PostgreSQL driver —
and **each statement (or each `BEGIN ... COMMIT` block) runs as one ScalarDB transaction** on the
databases ScalarDB manages. SQL is parsed (JSQLParser) and planned into ScalarDB `Get` / `Scan` /
mutations; keys, conditions, ordering and limits are pushed down. Joins, aggregates, window
functions, subqueries, CTEs (including recursive) and set operations run in an in-memory operator
tree inside the frontend. Enough of `pg_catalog` is emulated for psql meta-commands.

The database name a client connects with is the **ScalarDB namespace**.

## Two Deployment Forms

| Form | Where it runs | Edition / licence | Security | Use |
|------|---------------|-------------------|----------|-----|
| **Inside ScalarDB Cluster nodes** (recommended) | Each node listens when `scalar.db.postgres.enabled=true`; port `scalar.db.postgres.port` (default `5432`) | ScalarDB Cluster 3.20+, **Enterprise** (the release notes do not say Standard or Premium — confirm against the contract before promising it) | Cluster users, privileges, encryption and ABAC apply. With authentication on, login is by password or OIDC token in the password field; `scalar.db.postgres.auth` restricts to `userpass` or `oidc_jwt`; **TLS is required by default when authentication is enabled** | Production access for SQL tools and non-Java clients |
| **Standalone `scalardb-postgres-frontend`** | `java -jar scalardb-postgres-frontend.jar scalardb.properties 15432` (Java 17+; engine artifact `com.scalar-labs:scalardb-postgres-frontend-engine`; container built from `server/src/docker`) | Apache-2.0. In front of ScalarDB Cluster it works but is **not recommended for production** (one extra network hop per ScalarDB call); on ScalarDB Core there is **no authentication and no TLS** | None on Core: whoever reaches the port has the configured ScalarDB user's full access. Bind `scalar.db.postgres.listen_address=127.0.0.1` or keep it on a trusted network | Development, evaluation, Community-edition projects on a trusted network |

Config keys named upstream: `scalar.db.postgres.enabled`, `scalar.db.postgres.port`,
`scalar.db.postgres.auth`, `scalar.db.postgres.listen_address`,
`scalar.db.postgres.backend_collation_check` (`false` bypasses the startup collation check on
PostgreSQL / MySQL backends). Verify each against the project's pinned release before writing it
into a properties file; the key list is not in the bundle.

## When To Offer It — and When Not

| Need | Answer |
|------|--------|
| psql / BI / reporting / a non-Java service must read or write ScalarDB-managed data with SQL | PostgreSQL wire protocol (Cluster form in production) |
| A Java application wants ScalarDB transactions through JDBC | ScalarDB SQL JDBC driver (Premium) — @rules/scalardb-jdbc-patterns.md; the PostgreSQL JDBC driver through this frontend is the alternative when the Premium SQL surface is not contracted but Cluster 3.20 with the wire protocol is |
| A legacy SQL application must keep native SQL on one database shared with ScalarDB | Native JDBC — @rules/scalardb-native-jdbc-patterns.md |
| The application relies on PostgreSQL semantics the frontend does not enforce (constraints, locks, transactional DDL, `COPY`) | Not this interface, or redesign those parts first (next section) |

It is an **access path**, not a database: the data model is still ScalarDB's (partition key,
clustering key, secondary indexes — @rules/scalardb-schema-design.md), and the transaction model
is still Consensus Commit (OCC, conflicts at commit).

## It Is Not PostgreSQL — Design Around These

Rule upstream: an unsupported request raises an error; an accepted request the frontend cannot
fully honour emits a `NOTICE`; a short list of results differ silently.

**Accepted with a NOTICE and then ignored — the design must not depend on them:**
- `UNIQUE`, `CHECK`, `REFERENCES`, `DEFAULT` (other than `DEFAULT NULL`) and non-key `NOT NULL` in
  `CREATE TABLE` — violating rows are stored; `serial` generates nothing.
- `CREATE UNIQUE INDEX` and partial indexes become plain indexes.
- Timestamps finer than milliseconds lose precision; `lock_timeout` has no effect.

**Refused (error):**
- `COPY`, cursors, views, `CREATE TEMP TABLE`, `SELECT ... INTO`, `TABLESAMPLE`, expression
  indexes, ordered-set aggregates, array column types in DDL, data-modifying statements nested in
  `WITH`.
- Changing a column's type; adding an encrypted column with `ALTER TABLE`; updating a key column to
  a value another row holds (`23505`); `ON CONFLICT DO UPDATE` on a key column; empty-string
  partition keys.
- A scan of rows the same transaction already wrote (`DB-CORE-10106`) — the ScalarDB rule, surfaced
  through SQL.
- Requesting a stronger isolation level than the engine runs at (`0A000`).
- Sort / aggregate / window / join state above one million rows per side (`54000`); prepared
  statements above 64 MiB per session; regex longer than 5 s.
- With `auth=none`: user and role DDL, `GRANT` / `REVOKE`.

**Different without an error:**
- `SNAPSHOT` reads are per record, not per statement — a multi-row read concurrent with a write can
  mix before and after states.
- A batch that contains reads commits its earlier writes separately; inside `BEGIN ... COMMIT` the
  batch stays atomic but the scan fails.
- Text comparison follows ScalarDB's byte order; on MySQL, or PostgreSQL databases not using the
  `C` collation, pushed-down and frontend-evaluated comparisons can disagree. The frontend checks
  JDBC backends at startup unless `backend_collation_check=false`; **ScalarDB Cluster backends are
  not checked** — configure the backing database to match.
- `NUMERIC` is exact up to 18 digits (filtered in the frontend beyond that); columns created before
  3.20 are `double precision`. `DATE` / `TIMESTAMP` must fall in years 1000–9999; `TIME` cannot be
  `24:00:00`.
- Column order for tables created by other ScalarDB clients is key-first (affects `SELECT *` and
  positional `INSERT`).
- Result sets do not report their source table, so some tools treat them as read-only.

## Transactions and Isolation

- Outside `BEGIN`, every statement is its own transaction; `BEGIN ... COMMIT` is one transaction.
- `READ_COMMITTED` and `SNAPSHOT` report as `read committed`; `SERIALIZABLE` reports as
  `serializable` and validates reads at commit, failing the transaction rather than returning
  inconsistent data.
- `SELECT ... FOR UPDATE` / `FOR SHARE` **take no lock**; conflicts surface at commit as `40001`.
  The application retries the whole transaction, exactly as for `CommitConflictException`
  (@rules/scalardb-exception-handling.md).
- DDL inside a transaction takes effect immediately and is **not undone by `ROLLBACK`**; after a
  write, `ROLLBACK TO SAVEPOINT` aborts the whole transaction.
- While a backing database is unreachable, `COMMIT` waits 60–150 s and then fails with `40003`
  (outcome unknown) — handle it as `UnknownTransactionStatusException`, never as a plain failure.
- `statement_timeout` and cancel requests stop a statement with `57014`.

## DDL Through the Frontend

- DDL on an existing table is visible only when ScalarDB's metadata cache expires
  (`scalar.db.metadata.cache_expiration_time_secs`, default 60 s); until then statements use the
  old definition and an insert into a new column fails with `DB-CORE-10017`. Migration tools need
  the cache at 5 s or less, which raises metadata load.
- **Every ScalarDB Cluster node must use the same cache expiry as the frontend**, or nodes fail
  with `DB-CORE-30040` after `ALTER TABLE`.
- `RENAME COLUMN` runs in two steps; an interruption leaves an extra `before_<old>` column.
- Two concurrent `CREATE TABLE` for one name can briefly expose the winner's table with the
  loser's declared types. Serialize schema changes through one owner (`Schema Loader` or one
  frontend session), never from application code.
- Declared PostgreSQL types live in a frontend-kept metadata table that must exist first (`55000`).

## Review Checklist

1. Is the deployment form stated, and is the unauthenticated standalone form confined to a trusted
   network or localhost?
2. Does any invariant rely on `UNIQUE` / `CHECK` / `REFERENCES` / `NOT NULL` being enforced? Move
   it into the application or the aggregate (@rules/aggregate-design.md).
3. Does any flow rely on `FOR UPDATE` locking, transactional DDL, savepoints after writes, or
   `COPY`?
4. Is `40001` retried and `40003` treated as unknown status?
5. Is the backing database's collation aligned with ScalarDB's byte order, and are Cluster nodes
   and the frontend on the same metadata cache expiry?
6. Is the edition confirmed for the Cluster form (Enterprise; tier to be verified) rather than
   assumed?
