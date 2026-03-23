# ScalarDB Interface Combinations Matrix

ScalarDB supports 6 interface combinations along three axes:

- **Deployment**: Core (direct DB connection) or Cluster (via ScalarDB Cluster)
- **API**: CRUD (Java native) or SQL/JDBC (standard SQL)
- **Transaction**: One-phase commit (1PC) or Two-phase commit (2PC)

## The 6 Combinations

| # | Name | Deployment | API | Transaction | Use Case |
|---|------|-----------|-----|-------------|----------|
| 1 | Core+CRUD+1PC | Core | CRUD | 1PC | Single-app, single-DB, development/testing |
| 2 | Core+CRUD+2PC | Core | CRUD | 2PC | Multi-DB from single app, cross-storage transactions |
| 3 | Cluster+CRUD+1PC | Cluster | CRUD | 1PC | Production single-DB with ScalarDB Cluster |
| 4 | Cluster+CRUD+2PC | Cluster | CRUD | 2PC | Production multi-service with CRUD API |
| 5 | Cluster+JDBC+1PC | Cluster | JDBC/SQL | 1PC | Production with standard SQL interface |
| 6 | Cluster+JDBC+2PC | Cluster | JDBC/SQL | 2PC | Production multi-service with SQL interface |

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

## Dependency Matrix

| Combination | Maven Artifact | Artifact ID |
|-------------|---------------|-------------|
| Core+CRUD (1PC/2PC) | `com.scalar-labs:scalardb` | `scalardb` |
| Cluster+CRUD (1PC/2PC) | `com.scalar-labs:scalardb-cluster-java-client-sdk` | `scalardb-cluster-java-client-sdk` |
| Cluster+JDBC (1PC/2PC) | `com.scalar-labs:scalardb-sql-jdbc` + `com.scalar-labs:scalardb-cluster-java-client-sdk` | `scalardb-sql-jdbc` |

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

### Core+CRUD+2PC — Transaction Initialization

```java
TransactionFactory factory = TransactionFactory.create("database.properties");
TwoPhaseCommitTransactionManager manager = factory.getTwoPhaseCommitTransactionManager();
TwoPhaseCommitTransaction tx = manager.begin();   // coordinator
TwoPhaseCommitTransaction tx = manager.join(txId); // participant
```

### Cluster+CRUD — Transaction Initialization

Same code as Core+CRUD, but config uses `scalar.db.transaction_manager=cluster`.

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
