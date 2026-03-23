# ScalarDB API Reference

## Package Structure

- `com.scalar.db.api` — Core API interfaces and classes
- `com.scalar.db.io` — Key, Column, DataType
- `com.scalar.db.exception.transaction` — Transaction exceptions

## Transaction Managers

### DistributedTransactionManager

```java
// Creation
TransactionFactory factory = TransactionFactory.create("database.properties");
DistributedTransactionManager manager = factory.getTransactionManager();

// Transaction lifecycle
DistributedTransaction tx = manager.begin();
DistributedTransaction tx = manager.begin(String txId);
DistributedTransaction tx = manager.start();           // alias for begin
DistributedTransaction tx = manager.start(String txId); // alias for begin
DistributedTransaction tx = manager.beginReadOnly();
DistributedTransaction tx = manager.startReadOnly();
DistributedTransaction tx = manager.resume(String txId);
DistributedTransaction tx = manager.join(String txId);  // alias for resume

// State management
TransactionState state = manager.getState(String txId);
TransactionState state = manager.rollback(String txId);
TransactionState state = manager.abort(String txId);    // alias for rollback

// Cleanup (implements AutoCloseable)
manager.close();
```

### TwoPhaseCommitTransactionManager

```java
TwoPhaseCommitTransactionManager manager = factory.getTwoPhaseCommitTransactionManager();

// Coordinator begins
TwoPhaseCommitTransaction tx = manager.begin();
TwoPhaseCommitTransaction tx = manager.start();
TwoPhaseCommitTransaction tx = manager.begin(String txId);
TwoPhaseCommitTransaction tx = manager.start(String txId);

// Participant joins
TwoPhaseCommitTransaction tx = manager.join(String txId);

// Resume
TwoPhaseCommitTransaction tx = manager.resume(String txId);
```

## Transaction Objects

### DistributedTransaction

```java
String id = tx.getId();

// CRUD operations
Optional<Result> result = tx.get(Get get);
List<Result> results = tx.scan(Scan scan);
Scanner scanner = tx.getScanner(Scan scan);
tx.insert(Insert insert);
tx.upsert(Upsert upsert);
tx.update(Update update);
tx.delete(Delete delete);
tx.mutate(List<? extends Mutation> mutations);
List<BatchResult> results = tx.batch(List<? extends Operation> operations);

// Deprecated CRUD
tx.put(Put put);                          // @Deprecated since 3.13.0
tx.put(List<Put> puts);                   // @Deprecated
tx.delete(List<Delete> deletes);          // @Deprecated

// Lifecycle
tx.commit();    // throws CommitConflictException, CommitException, UnknownTransactionStatusException
tx.rollback();  // throws RollbackException
tx.abort();     // alias for rollback
```

### TwoPhaseCommitTransaction

Same CRUD operations as DistributedTransaction, plus:

```java
tx.prepare();   // throws PreparationConflictException, PreparationException
tx.validate();  // throws ValidationConflictException, ValidationException
tx.commit();    // throws CommitConflictException, CommitException, UnknownTransactionStatusException
tx.rollback();
tx.abort();
```

## CRUD Operations

### Get

```java
// By primary key
Get get = Get.newBuilder()
    .namespace("ns")
    .table("tbl")
    .partitionKey(Key.ofInt("id", 1))
    .clusteringKey(Key.ofInt("ck", 2))     // optional
    .projection("col1")                     // optional, repeatable
    .projections("col1", "col2")            // optional
    .consistency(Consistency.LINEARIZABLE)   // optional (ignored in transactions)
    .build();

// By secondary index
Get get = Get.newBuilder()
    .namespace("ns")
    .table("tbl")
    .indexKey(Key.ofText("indexed_col", "value"))
    .build();

// Copy builder
Get modified = Get.newBuilder(existingGet)
    .namespace("newNs")
    .build();
```

### Scan

```java
// Within partition (range scan)
Scan scan = Scan.newBuilder()
    .namespace("ns")
    .table("tbl")
    .partitionKey(Key.ofInt("pk", 1))
    .start(Key.ofInt("ck", 10))              // optional start bound
    .startInclusive(true)                     // default true
    .end(Key.ofInt("ck", 20))                // optional end bound
    .endInclusive(false)                      // default true
    .ordering(Scan.Ordering.asc("ck"))       // optional
    .limit(100)                               // optional
    .projection("col1")                       // optional
    .build();

// Scan all (cross-partition) — requires scalar.db.cross_partition_scan.enabled=true
Scan scanAll = Scan.newBuilder()
    .namespace("ns")
    .table("tbl")
    .all()
    .limit(100)
    .build();

// By secondary index
Scan scanIndex = Scan.newBuilder()
    .namespace("ns")
    .table("tbl")
    .indexKey(Key.ofText("indexed_col", "value"))
    .build();
```

**Scan.Ordering:**
```java
Scan.Ordering.asc("columnName")
Scan.Ordering.desc("columnName")
```

### Insert (new record only — fails if exists)

```java
Insert insert = Insert.newBuilder()
    .namespace("ns")
    .table("tbl")
    .partitionKey(Key.ofInt("id", 1))
    .clusteringKey(Key.ofInt("ck", 2))   // optional
    .intValue("col1", 100)
    .textValue("col2", "hello")
    .booleanValue("col3", true)
    .bigIntValue("col4", 9999L)
    .floatValue("col5", 1.5f)
    .doubleValue("col6", 3.14)
    .blobValue("col7", byteArray)
    .dateValue("col8", LocalDate.now())
    .timeValue("col9", LocalTime.now())
    .timestampValue("col10", LocalDateTime.now())
    .timestampTZValue("col11", Instant.now())
    .build();
```

### Upsert (insert if not exists, update if exists)

```java
Upsert upsert = Upsert.newBuilder()
    .namespace("ns")
    .table("tbl")
    .partitionKey(Key.ofInt("id", 1))
    .clusteringKey(Key.ofInt("ck", 2))
    .intValue("col1", 200)
    .textValue("col2", "world")
    .build();
```

### Update (existing record only — does nothing if not exists)

```java
Update update = Update.newBuilder()
    .namespace("ns")
    .table("tbl")
    .partitionKey(Key.ofInt("id", 1))
    .clusteringKey(Key.ofInt("ck", 2))
    .intValue("col1", 300)
    .condition(ConditionBuilder.updateIf(
        ConditionBuilder.column("col1").isGreaterThanInt(0)
    ).build())   // optional condition
    .build();
```

### Delete

```java
Delete delete = Delete.newBuilder()
    .namespace("ns")
    .table("tbl")
    .partitionKey(Key.ofInt("id", 1))
    .clusteringKey(Key.ofInt("ck", 2))
    .condition(ConditionBuilder.deleteIfExists())  // optional condition
    .build();
```

### Put (DEPRECATED since 3.13.0)

```java
// Use Insert, Upsert, or Update instead
Put put = Put.newBuilder()
    .namespace("ns")
    .table("tbl")
    .partitionKey(Key.ofInt("id", 1))
    .clusteringKey(Key.ofInt("ck", 2))
    .intValue("col1", 100)
    .textValue("col2", "hello")
    .condition(ConditionBuilder.putIfNotExists())  // optional
    .enableImplicitPreRead()                       // needed for updates without prior read
    .build();
```

## Value Setter Methods (all mutation builders)

| Method | Type |
|--------|------|
| `.booleanValue(String, boolean)` | BOOLEAN |
| `.booleanValue(String, @Nullable Boolean)` | BOOLEAN (nullable) |
| `.intValue(String, int)` | INT |
| `.intValue(String, @Nullable Integer)` | INT (nullable) |
| `.bigIntValue(String, long)` | BIGINT |
| `.bigIntValue(String, @Nullable Long)` | BIGINT (nullable) |
| `.floatValue(String, float)` | FLOAT |
| `.floatValue(String, @Nullable Float)` | FLOAT (nullable) |
| `.doubleValue(String, double)` | DOUBLE |
| `.doubleValue(String, @Nullable Double)` | DOUBLE (nullable) |
| `.textValue(String, @Nullable String)` | TEXT |
| `.blobValue(String, @Nullable byte[])` | BLOB |
| `.blobValue(String, @Nullable ByteBuffer)` | BLOB |
| `.dateValue(String, @Nullable LocalDate)` | DATE |
| `.timeValue(String, @Nullable LocalTime)` | TIME |
| `.timestampValue(String, @Nullable LocalDateTime)` | TIMESTAMP |
| `.timestampTZValue(String, @Nullable Instant)` | TIMESTAMPTZ |
| `.value(Column<?>)` | Any (generic) |

## Key Construction

### Single-Column Keys

```java
Key.ofBoolean("col", true)
Key.ofInt("col", 42)
Key.ofBigInt("col", 9999L)
Key.ofFloat("col", 1.5f)
Key.ofDouble("col", 3.14)
Key.ofText("col", "hello")
Key.ofBlob("col", byteArray)
Key.ofBlob("col", byteBuffer)
Key.ofDate("col", LocalDate.of(2024, 1, 1))
Key.ofTime("col", LocalTime.of(12, 0))
Key.ofTimestamp("col", LocalDateTime.now())
Key.ofTimestampTZ("col", Instant.now())
```

### Multi-Column Keys

```java
// Convenience methods (up to 5 columns)
Key.of("col1", 1, "col2", "text")
Key.of("col1", 1, "col2", "text", "col3", 3L)

// Builder (any number of columns)
Key key = Key.newBuilder()
    .addInt("col1", 1)
    .addText("col2", "hello")
    .addBigInt("col3", 999L)
    .build();
```

### Builder Methods

`addBoolean`, `addInt`, `addBigInt`, `addFloat`, `addDouble`, `addText`, `addBlob(byte[])`, `addBlob(ByteBuffer)`, `addDate`, `addTime`, `addTimestamp`, `addTimestampTZ`

## Result Interface

```java
// Null check
boolean isNull = result.isNull("col");
boolean hasCol = result.contains("col");
Set<String> colNames = result.getContainedColumnNames();

// Value getters (return default value if NULL for primitives)
boolean b = result.getBoolean("col");       // false if NULL
int i = result.getInt("col");               // 0 if NULL
long l = result.getBigInt("col");           // 0L if NULL
float f = result.getFloat("col");           // 0.0f if NULL
double d = result.getDouble("col");         // 0.0 if NULL

// Value getters (return null if NULL for objects)
@Nullable String s = result.getText("col");
@Nullable ByteBuffer bb = result.getBlob("col");
@Nullable ByteBuffer bb = result.getBlobAsByteBuffer("col");
@Nullable byte[] bytes = result.getBlobAsBytes("col");
@Nullable LocalDate date = result.getDate("col");
@Nullable LocalTime time = result.getTime("col");
@Nullable LocalDateTime ts = result.getTimestamp("col");
@Nullable Instant tstz = result.getTimestampTZ("col");
@Nullable Object obj = result.getAsObject("col");
```

## Mutation Conditions (ConditionBuilder)

```java
// Put conditions (deprecated with Put)
ConditionBuilder.putIf(ConditionBuilder.column("col").isEqualToInt(1))
    .and(ConditionBuilder.column("col2").isGreaterThanText("a"))
    .build();
ConditionBuilder.putIfExists();
ConditionBuilder.putIfNotExists();

// Update conditions
ConditionBuilder.updateIf(ConditionBuilder.column("col").isGreaterThanInt(0))
    .and(ConditionBuilder.column("col2").isNotNullText())
    .build();
ConditionBuilder.updateIfExists();

// Delete conditions
ConditionBuilder.deleteIf(ConditionBuilder.column("col").isEqualToInt(1)).build();
ConditionBuilder.deleteIfExists();
```

## Data Types (com.scalar.db.io.DataType)

`BOOLEAN`, `INT`, `BIGINT`, `FLOAT`, `DOUBLE`, `TEXT`, `BLOB`, `DATE`, `TIME`, `TIMESTAMP`, `TIMESTAMPTZ`

## TransactionState Enum

`PREPARED` (1), `DELETED` (2), `COMMITTED` (3), `ABORTED` (4), `UNKNOWN` (5)

## Consistency Enum

`SEQUENTIAL`, `EVENTUAL`, `LINEARIZABLE` — Note: ignored in transactional operations (always LINEARIZABLE)

---

## JDBC/SQL API Reference

### JDBC Connection

```java
// JDBC URL format: jdbc:scalardb:<config-file-path>[?property=value&...]
Connection conn = DriverManager.getConnection("jdbc:scalardb:scalardb-sql.properties");
conn.setAutoCommit(false); // CRITICAL: always disable auto-commit

// Or with inline properties:
Connection conn = DriverManager.getConnection(
    "jdbc:scalardb:?scalar.db.sql.connection_mode=cluster"
    + "&scalar.db.sql.cluster_mode.contact_points=indirect:localhost");
```

### JDBC Configuration Properties

| Property | Default | Description |
|----------|---------|-------------|
| `scalar.db.sql.jdbc.default_auto_commit` | `true` | Default auto-commit mode |
| `scalar.db.sql.jdbc.default_read_only` | `false` | Default read-only state |
| `scalar.db.sql.jdbc.sql_session_factory_cache.expiration_time_millis` | `10000` | Session factory cache TTL |

### Supported SQL Statements

**DDL**: `CREATE NAMESPACE`, `CREATE TABLE`, `ALTER TABLE`, `DROP TABLE`, `TRUNCATE TABLE`, `DROP NAMESPACE`, `CREATE INDEX`, `DROP INDEX`, `CREATE COORDINATOR TABLES`, `DROP COORDINATOR TABLES`

**DML**: `SELECT` (with JOIN, GROUP BY, HAVING, ORDER BY, LIMIT), `INSERT`, `UPSERT`, `UPDATE`, `DELETE`

**TCL**: `BEGIN`, `START TRANSACTION`, `COMMIT`, `ROLLBACK`, `ABORT`, `PREPARE`, `VALIDATE`, `SUSPEND`, `RESUME`

**DCL**: `CREATE USER`, `ALTER USER`, `DROP USER`, `GRANT`, `REVOKE`, `CREATE ROLE`, `DROP ROLE`

**Utility**: `USE`, `SHOW NAMESPACES`, `SHOW TABLES`, `DESCRIBE`

### SQL DML Details

**SELECT**:
```sql
SELECT projection [, ...]
FROM [ns.]table [AS alias]
  [JOIN [ns.]table [AS alias] ON predicates] ...
[WHERE conditions]
[GROUP BY columns]
[HAVING conditions]
[ORDER BY column [ASC|DESC] [, ...]]
[LIMIT n]
```

Aggregates: `COUNT(*)`, `COUNT(col)`, `SUM(col)`, `AVG(col)`, `MIN(col)`, `MAX(col)`

JOINs: `INNER JOIN`, `LEFT [OUTER] JOIN`, `RIGHT [OUTER] JOIN` (no FULL OUTER JOIN)

WHERE operators: `=`, `<>`, `!=`, `>`, `>=`, `<`, `<=`, `BETWEEN`, `LIKE`, `IS [NOT] NULL`

**INSERT** (fails if record exists):
```sql
INSERT INTO [ns.]table [(columns)] VALUES (values) [, (values)] ...
```

**UPSERT** (insert or update):
```sql
UPSERT INTO [ns.]table [(columns)] VALUES (values) [, (values)] ...
```

**UPDATE**:
```sql
UPDATE [ns.]table SET col = value [, ...] [WHERE conditions]
```

**DELETE**:
```sql
DELETE FROM [ns.]table [WHERE conditions]
```

### SQL Limitations

- No `DISTINCT`, no subqueries, no CTEs, no window functions
- No `FULL OUTER JOIN`, no `UNION`/`INTERSECT`/`EXCEPT`
- JOIN predicates must reference primary key or secondary index columns
- `RIGHT OUTER JOIN` must be the first join
- WHERE must be in DNF (OR of ANDs) or CNF (AND of ORs)

### JDBC Exception Handling

```java
try {
    conn.commit();
} catch (SQLException e) {
    if (e.getErrorCode() == 301) {
        // UnknownTransactionStatusException — do NOT rollback
        // Verify if committed, retry only if not
    } else {
        conn.rollback();
        // Check e.getCause() for TransactionRetryableException (retry)
        // Other causes may be non-transient — limit retries
    }
}
```

### SQL API (Non-JDBC)

The SQL API uses `SqlSession` instead of JDBC Connection:

```java
SqlSessionFactory factory = SqlSessionFactory.builder()
    .withPropertiesFile("scalardb-sql.properties")
    .build();

SqlSession session = factory.createSqlSession();
session.begin();
// Execute SQL via session.execute("SQL") or session.prepareStatement("SQL")
session.commit();
session.close();
```

SQL API exceptions (`com.scalar.db.sql.exception`):
- `UnknownTransactionStatusException` — do NOT retry blindly
- `TransactionRetryableException` — safe to retry
- `SqlException` — base exception class
