# ScalarDB Interface Combinations Matrix

ScalarDB supports 6 interface combinations along three axes:

- **Deployment**: Core (direct DB connection) or Cluster (via ScalarDB Cluster)
- **API**: CRUD (Java native) or SQL/JDBC (standard SQL)
- **Transaction**: One-phase commit (1PC) or Two-phase commit (2PC)

## The 6 Combinations

| # | Name | Deployment | API | Transaction | Use Case |
|---|------|-----------|-----|-------------|----------|
| 1 | Core+CRUD+1PC | Core | CRUD | 1PC | Single-app, single-DB, development/testing. Multi-storage transactions from one app are 1PC too |
| 2 | Core+CRUD+2PC | Core | CRUD | 2PC — **deprecated interface (3.19+)** | Existing code only; cross-storage from one app needs no 2PC |
| 3 | Cluster+CRUD+1PC | Cluster | CRUD | 1PC | Production with ScalarDB Cluster — **including multi-service transactions** via the Microservice Transaction API (3.19+) |
| 4 | Cluster+CRUD+2PC | Cluster | CRUD | 2PC — **deprecated interface (3.19+)** | Existing multi-service code on the 2PC interface; ADR-recorded deviations |
| 5 | Cluster+JDBC+1PC | Cluster | JDBC/SQL | 1PC | Production with ScalarDB SQL — multi-service via the SQL `GLOBAL_TRANSACTION` mode (3.20+) |
| 6 | Cluster+JDBC+2PC | Cluster | JDBC/SQL | 2PC — **deprecated mode (3.19+)**; `JOIN`/`SUSPEND`/`RESUME` removed in 3.20 | Existing multi-service SQL code |

## Decision Guide

```
Do you need ScalarDB Cluster (production, auth, encryption)?
├── No → Core mode
│   ├── Single database? → Core+CRUD+1PC (#1) ← Most common for development
│   └── Multiple databases/services? → Core+CRUD+2PC (#2)
│
└── Yes → Cluster mode
    ├── Prefer Java native API?
    │   ├── Single transaction context? → Cluster+CRUD+1PC (#3)
    │   └── Multi-service transactions? → Cluster+CRUD+2PC (#4)
    │
    └── Prefer standard SQL?
        ├── Single transaction context? → Cluster+JDBC+1PC (#5)
        └── Multi-service transactions? → Cluster+JDBC+2PC (#6)
```

## Multi-Service Transactions Do Not Force 2PC

The "multi-service" branches above assume the application drives the two-phase commit protocol
itself. That interface is **deprecated as of ScalarDB 3.19** ("will be removed in a future
release"); the application interface for a transaction that spans services is one-phase:

| Topology | Combination to use |
|----------|--------------------|
| **Shared cluster** — all services use one ScalarDB Cluster instance | The **1PC** combination (#3 or #5): the Microservice Transaction API with `scalar.db.cluster.client.transaction_coordinator.enabled=false`. The documented recommendation whenever possible |
| **Separated clusters + Transaction Coordinator** (ScalarDB 3.19+) | The **1PC** combination (#3; #5 on 3.20+ via `GLOBAL_TRANSACTION`) — the **same code** as the row above; the Coordinator node drives 2PC underneath. See `code-patterns/cluster-crud-microservice-tx.md` |
| **Separated clusters, application-driven 2PC** | The **2PC** combination (#4 or #6) — deprecated interface; pre-3.19, or an ADR-recorded deviation |
| **Eventual consistency across services** | Not a combination here — ScalarDB Saga (3.20 GA); see `rules/scalardb-saga-patterns.md` |

Spring Data JDBC does not support the shared-cluster pattern; with it, multi-service still means the
(deprecated) 2PC combination — raise that as a finding. Full selection rules:
`rules/scalardb-2pc-patterns.md`.

Note on editions: combinations #5 and #6 (JDBC/SQL) require **Enterprise Premium**, and #3–#6 all
require an Enterprise edition for ScalarDB Cluster. See `rules/scalardb-edition-profiles.md`.

## SQL Access Paths Beyond the Java SDK (3.20)

Three further ways reach ScalarDB-managed data with SQL. None is a seventh "combination" — they are
access paths with their own semantics, chosen by who the client is:

| Path | Client | Talks to | Edition / licence | Transaction semantics | Main limitation | Choose when |
|------|--------|----------|-------------------|-----------------------|-----------------|-------------|
| **ScalarDB SQL JDBC** (`jdbc:scalardb:`, #5/#6) | Java via the ScalarDB JDBC driver | ScalarDB Cluster (gRPC) | Enterprise Premium | ScalarDB transaction per connection; ScalarDB SQL grammar (`sql-reference.md`) | Narrow grammar (no subqueries, DISTINCT, CTEs…) | A Java application wants ScalarDB transactions through SQL and holds a Premium contract |
| **PostgreSQL wire protocol** (Cluster 3.20+, `scalar.db.postgres.enabled`) | psql, any PostgreSQL driver, ORMs, BI tools | ScalarDB Cluster nodes on port 5432 | Enterprise (tier not stated) | Each statement / `BEGIN…COMMIT` block is one ScalarDB transaction; PostgreSQL dialect, rich grammar (joins, aggregates, window functions, CTEs run in the frontend) | Not PostgreSQL: constraints unenforced, `FOR UPDATE` takes no lock, DDL not rolled back, no `COPY`/cursors/views | Non-Java clients, SQL tooling, reporting; a Java app without the Premium SQL surface |
| **scalardb-postgres-frontend** (standalone, Apache-2.0) | Same | ScalarDB Core (or Cluster, not recommended) | None — but **no auth / TLS** on Core | Same as above | Trusted network only | Development, evaluation, Community projects |
| **ScalarDB Native JDBC** (`jdbc:scalardb-native:<vendor>:`, Apache-2.0) | A legacy SQL application with the vendor's JDBC driver | The database itself — **no ScalarDB call** | None | One native DB transaction, ACID across ordinary and ScalarDB tables; reads committed data, writes Consensus Commit metadata; **one database per connection** | Must share the isolation level with every ScalarDB app on the tables; refuses `INSERT…SELECT`, upserts, multi-table writes; needs `scalardb-native-tools setup` | An existing SQL application must keep its native SQL and share tables with ScalarDB applications on one database |

Rules: `rules/scalardb-jdbc-patterns.md` (first path), `rules/scalardb-postgres-frontend-patterns.md`,
`rules/scalardb-native-jdbc-patterns.md`.

## Dependency Matrix

| Combination | Maven Artifact | Artifact ID |
|-------------|---------------|-------------|
| Core+CRUD (1PC/2PC) | `com.scalar-labs:scalardb` | `scalardb` |
| Cluster+CRUD (1PC/2PC) | `com.scalar-labs:scalardb-cluster-java-client-sdk` | `scalardb-cluster-java-client-sdk` |
| Cluster+JDBC (1PC/2PC) | `com.scalar-labs:scalardb-sql-jdbc` + `com.scalar-labs:scalardb-cluster-java-client-sdk` | `scalardb-sql-jdbc` |
| Native JDBC (access path) | `com.scalar-labs:scalardb-native-jdbc` + the vendor driver (`org.postgresql:postgresql`, …) | `scalardb-native-jdbc` |
| PostgreSQL frontend, standalone (access path) | `com.scalar-labs:scalardb-postgres-frontend-engine` (or the server jar / image built from the repo) | `scalardb-postgres-frontend-engine` |
| ScalarDB Saga | `com.scalar-labs:scalardb-saga-bom` + one of `scalardb-saga-java-client-sdk` / `scalardb-saga-core` | see `rules/scalardb-saga-patterns.md` |

## Configuration Matrix

### Core+CRUD (1PC)

```properties
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:mysql://localhost:3306/
scalar.db.username=root
scalar.db.password=mysql
```

### Core+CRUD (2PC)

Same as 1PC, but use `TwoPhaseCommitTransactionManager` instead of `DistributedTransactionManager`.

### Cluster+CRUD (1PC/2PC)

```properties
scalar.db.transaction_manager=cluster
scalar.db.contact_points=indirect:<CLUSTER_HOST>
```

### Cluster+JDBC (1PC/2PC)

```properties
scalar.db.sql.connection_mode=cluster
scalar.db.sql.cluster_mode.contact_points=indirect:<CLUSTER_HOST>
```

JDBC URL: `jdbc:scalardb:<properties-file-path>`

## Code Pattern Matrix

### Core+CRUD — Transaction Initialization

```java
TransactionFactory factory = TransactionFactory.create("database.properties");
DistributedTransactionManager manager = factory.getTransactionManager();
DistributedTransaction tx = manager.begin();
```

### Core+CRUD+2PC — Transaction Initialization (deprecated interface)

```java
TransactionFactory factory = TransactionFactory.create("database.properties");
TwoPhaseCommitTransactionManager manager = factory.getTwoPhaseCommitTransactionManager();
TwoPhaseCommitTransaction tx = manager.begin();   // coordinator
TwoPhaseCommitTransaction tx = manager.join(txId); // participant
```

### Cluster+CRUD — Transaction Initialization

Same code as Core+CRUD, but config uses `scalar.db.transaction_manager=cluster`.

### Cluster+CRUD — Microservice Transaction (3.19+, one-phase across services)

```java
GlobalTransactionManager manager = factory.getGlobalTransactionManager();
GlobalTransaction global = manager.begin();                 // the orchestrating process
BranchTransaction branch = manager.beginBranch(global.getId()); // every process, incl. the orchestrator
branch.insert(...); branch.end(BranchTransaction.Status.SUCCESS);
global.commit();                                            // orchestrator, after every branch ended SUCCESS
```

Same code for shared and separated clusters; only the properties differ
(`code-patterns/cluster-crud-microservice-tx.md`, `rules/scalardb-2pc-patterns.md`).

### Cluster+JDBC — Connection

```java
Connection conn = DriverManager.getConnection("jdbc:scalardb:scalardb-sql.properties");
conn.setAutoCommit(false);
// Standard JDBC operations
conn.commit();
```

## Schema Loading

| Combination | Schema Format | Loader Tool |
|-------------|--------------|-------------|
| Core+CRUD | JSON (`schema.json`) | `scalardb-schema-loader` |
| Cluster+CRUD | JSON (`schema.json`) | `scalardb-cluster-schema-loader` |
| Cluster+JDBC | SQL (`schema.sql`) or JSON | `scalardb-cluster-sql-cli` or `scalardb-cluster-schema-loader` |

## CRUD API vs JDBC/SQL Comparison

| Feature | CRUD API | JDBC/SQL |
|---------|---------|---------|
| JOIN support | No (application-level only) | Yes (INNER, LEFT, RIGHT JOIN) |
| Aggregate functions | No | Yes (COUNT, SUM, AVG, MIN, MAX) |
| GROUP BY / HAVING | No | Yes |
| Standard SQL syntax | No | Yes |
| Builder pattern | Yes | N/A (SQL strings) |
| Type-safe operations | Yes | No (string-based SQL) |
| Direct column access | `result.getInt("col")` | `resultSet.getInt("col")` |
| Performance | Better (no SQL parsing) | Slightly lower (SQL parsing) |
| Learning curve | ScalarDB-specific | Standard JDBC knowledge |

The Native JDBC driver sits outside this comparison: it runs the vendor's SQL on the database with
no ScalarDB call, so the ScalarDB SQL parsing and Cluster hop are absent for that application. The
upstream repository publishes benchmark notes (`docs/benchmarks/`) but no headline overhead figure —
do not quote one.
