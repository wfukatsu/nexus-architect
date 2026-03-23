---
description: Java best practices for ScalarDB applications — applies when writing Java code that uses ScalarDB
globs:
  - "**/*.java"
---

# ScalarDB Java Best Practices

## Use try-with-resources for TransactionManager

`DistributedTransactionManager` and `TwoPhaseCommitTransactionManager` implement `AutoCloseable`:

```java
try (DistributedTransactionManager manager = factory.getTransactionManager()) {
    // use manager
}
```

Or manage lifecycle explicitly in a service class that implements `Closeable`:

```java
public class MyService implements Closeable {
    private final DistributedTransactionManager manager;

    public MyService(String configFile) throws TransactionException {
        TransactionFactory factory = TransactionFactory.create(configFile);
        manager = factory.getTransactionManager();
    }

    @Override
    public void close() throws IOException {
        manager.close();
    }
}
```

## Initialize TransactionFactory Once

`TransactionFactory.create()` is expensive. Create it once and reuse:

```java
// CORRECT — create once:
TransactionFactory factory = TransactionFactory.create("database.properties");
DistributedTransactionManager manager = factory.getTransactionManager();

// WRONG — creating factory per operation:
public void doSomething() {
    TransactionFactory factory = TransactionFactory.create("database.properties"); // expensive!
    // ...
}
```

## Don't Share Transaction Objects Across Threads

`DistributedTransaction` and `TwoPhaseCommitTransaction` are `@NotThreadSafe`. Each thread should use its own transaction:

```java
// WRONG:
DistributedTransaction tx = manager.begin();
executor.submit(() -> tx.get(...));  // unsafe
executor.submit(() -> tx.insert(...)); // unsafe

// CORRECT:
executor.submit(() -> {
    DistributedTransaction tx = manager.begin();
    tx.get(...);
    tx.commit();
});
```

## Keep Transactions Short

Long-running transactions increase conflict probability and resource usage:
- Do all computation before starting the transaction
- Only include database operations inside the transaction
- Avoid external API calls within transactions

```java
// CORRECT — compute first, then transact:
int newTotal = computeNewTotal(items);
DistributedTransaction tx = manager.begin();
tx.update(...);
tx.commit();

// WRONG — computation inside transaction:
DistributedTransaction tx = manager.begin();
int newTotal = computeNewTotal(items); // slow computation holds transaction open
tx.update(...);
tx.commit();
```

## Use SLF4J for Logging

ScalarDB uses SLF4J internally. Use the same for consistency:

```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class MyService {
    private static final Logger logger = LoggerFactory.getLogger(MyService.class);

    public void doSomething() {
        logger.info("Processing order: {}", orderId);
    }
}
```

Add SLF4J binding in build.gradle:
```groovy
runtimeOnly 'org.apache.logging.log4j:log4j-slf4j2-impl:2.20.0'
runtimeOnly 'org.apache.logging.log4j:log4j-core:2.20.0'
```

## Use picocli for CLI Applications

ScalarDB samples use picocli for command-line argument parsing:

```groovy
dependencies {
    implementation 'info.picocli:picocli:4.7.1'
}
```

## Avoid Operation Object Reuse

Operation objects (Get, Scan, Insert, etc.) are `@NotThreadSafe`. Build new instances for each use:

```java
// CORRECT — new builder each time:
for (int id : ids) {
    Optional<Result> result = tx.get(
        Get.newBuilder().namespace("ns").table("tbl")
            .partitionKey(Key.ofInt("id", id)).build());
}
```

## Handle Nullable Result Values

Object-type getters from `Result` can return null:
```java
// Safe pattern:
String name = result.getText("name");
if (name != null) {
    // use name
}

// Or check first:
if (!result.isNull("name")) {
    String name = result.getText("name");
}
```

## Use UUID for Order/Entity IDs

```java
String orderId = UUID.randomUUID().toString();
```

ScalarDB also recommends UUID v4 format for custom transaction IDs.

## JDBC-Specific Best Practices

### Use a Connection Helper Method

Centralize `DriverManager.getConnection()` + `setAutoCommit(false)` in a helper:

```java
private static final String JDBC_URL = "jdbc:scalardb:scalardb-sql.properties";

private Connection getConnection() throws SQLException {
    Connection conn = DriverManager.getConnection(JDBC_URL);
    conn.setAutoCommit(false);
    return conn;
}
```

### Get a New Connection Per Transaction

JDBC connections should not be shared across threads. Get a new connection per transaction:

```java
// CORRECT — one connection per transaction:
public void doWork() throws SQLException {
    try (Connection conn = getConnection()) {
        // ... operations ...
        conn.commit();
    }
}

// WRONG — sharing a connection across threads:
private Connection sharedConn; // unsafe for concurrent use
```

### Close All JDBC Resources

Always use try-with-resources for Connection, PreparedStatement, and ResultSet:

```java
try (Connection conn = getConnection()) {
    try (PreparedStatement ps = conn.prepareStatement(sql)) {
        try (ResultSet rs = ps.executeQuery()) {
            while (rs.next()) { /* process */ }
        }
    }
    conn.commit();
}
```

### Use PreparedStatement, Never String Concatenation

Always use parameterized queries to prevent SQL injection:

```java
// CORRECT:
PreparedStatement ps = conn.prepareStatement("SELECT * FROM ns.tbl WHERE id = ?");
ps.setInt(1, id);

// WRONG — SQL injection risk:
Statement stmt = conn.createStatement();
stmt.executeQuery("SELECT * FROM ns.tbl WHERE id = " + id);
```

### Keep JDBC Transactions Short

Do computation outside the transaction, same as the CRUD API.

### JDBC Driver Class Name

The ScalarDB JDBC driver is auto-loaded via SPI. You do NOT need to call `Class.forName()`:

```java
// NOT needed — driver is loaded automatically:
// Class.forName("com.scalar.db.sql.jdbc.SqlJdbcDriver");

// Just use DriverManager directly:
Connection conn = DriverManager.getConnection("jdbc:scalardb:config.properties");
```
