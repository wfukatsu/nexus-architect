---
description: ScalarDB JDBC/SQL usage rules — applies when writing Java code that uses ScalarDB SQL JDBC driver
globs:
  - "**/*.java"
---

# ScalarDB JDBC/SQL Rules

## Always setAutoCommit(false)

ScalarDB requires explicit transaction management:

```java
Connection conn = DriverManager.getConnection("jdbc:scalardb:config.properties");
conn.setAutoCommit(false); // CRITICAL
```

## Always Commit Even for Read-Only

```java
try (Connection conn = getConnection()) {
    try {
        // Read-only query
        try (PreparedStatement ps = conn.prepareStatement("SELECT * FROM ns.tbl WHERE id = ?")) {
            ps.setInt(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                // process results
            }
        }
        conn.commit(); // REQUIRED even for reads
    } catch (Exception e) {
        conn.rollback();
        throw e;
    }
}
```

## Always Rollback in Catch Blocks

```java
try {
    // operations
    conn.commit();
} catch (Exception e) {
    conn.rollback();
    throw e;
}
```

## Use PreparedStatement with Parameters

Never concatenate values into SQL strings:

```java
// CORRECT:
PreparedStatement ps = conn.prepareStatement("SELECT * FROM ns.tbl WHERE id = ?");
ps.setInt(1, customerId);

// WRONG — SQL injection risk:
Statement stmt = conn.createStatement();
stmt.executeQuery("SELECT * FROM ns.tbl WHERE id = " + customerId);
```

## Use try-with-resources

Always close Connection, PreparedStatement, and ResultSet:

```java
try (Connection conn = getConnection()) {
    try (PreparedStatement ps = conn.prepareStatement(sql)) {
        ps.setInt(1, id);
        try (ResultSet rs = ps.executeQuery()) {
            while (rs.next()) {
                // process
            }
        }
    }
    conn.commit();
}
```

## JDBC URL Format

```
jdbc:scalardb:<config-file-path>[?property=value&...]
```

Examples:
- `jdbc:scalardb:scalardb-sql.properties`
- `jdbc:scalardb:/path/to/config.properties`
- `jdbc:scalardb:?scalar.db.sql.connection_mode=cluster&scalar.db.sql.cluster_mode.contact_points=indirect:localhost`

## Quote Reserved Words

SQL reserved words used as column names must be quoted:

```sql
-- CORRECT:
INSERT INTO ns.orders (customer_id, "timestamp", order_id) VALUES (?, ?, ?)

-- WRONG — timestamp is a reserved word:
INSERT INTO ns.orders (customer_id, timestamp, order_id) VALUES (?, ?, ?)
```

Common reserved words in ScalarDB schemas: `timestamp`, `order`, `key`, `index`, `table`, `column`

## Use namespace.table Format

Always qualify table names with namespace:

```sql
SELECT * FROM sample.customers WHERE customer_id = ?
INSERT INTO sample.orders (customer_id, "timestamp") VALUES (?, ?)
```

## JDBC Data Type Mapping

| ScalarDB | Java setter | Java getter |
|----------|-------------|-------------|
| BOOLEAN | `setBoolean()` | `getBoolean()` |
| INT | `setInt()` | `getInt()` |
| BIGINT | `setLong()` | `getLong()` |
| FLOAT | `setFloat()` | `getFloat()` |
| DOUBLE | `setDouble()` | `getDouble()` |
| TEXT | `setString()` | `getString()` |
| BLOB | `setBytes()` | `getBytes()` |
| DATE | `setObject(LocalDate)` | `getObject(LocalDate.class)` |
| TIME | `setObject(LocalTime)` | `getObject(LocalTime.class)` |
| TIMESTAMP | `setObject(LocalDateTime)` | `getObject(LocalDateTime.class)` |
| TIMESTAMPTZ | `setObject(Instant)` | `getObject(Instant.class)` |

**Important**: For DATE, TIME, TIMESTAMP, TIMESTAMPTZ — you MUST use `setObject()`/`getObject()`, NOT the legacy JDBC methods (`setDate()`, `setTimestamp()`, `getDate()`, `getTimestamp()`).

## JDBC Exception Handling

All ScalarDB SQL exceptions are wrapped in `java.sql.SQLException` with error codes:

```java
try {
    conn.commit();
} catch (SQLException e) {
    if (e.getErrorCode() == 301) {
        // UnknownTransactionStatusException — do NOT rollback
        // Verify if committed, retry only if not
    } else {
        conn.rollback();
        // Check e.getCause() for TransactionRetryableException (safe to retry)
        // Other causes may be non-transient — limit retries
    }
}
```

## JOIN Syntax

ScalarDB SQL supports INNER, LEFT OUTER, and RIGHT OUTER JOINs (Cluster mode only):

```sql
-- INNER JOIN
SELECT o.order_id, c.name
FROM ns.orders o
INNER JOIN ns.customers c ON o.customer_id = c.customer_id
WHERE o.customer_id = ?

-- LEFT OUTER JOIN
SELECT c.name, o.order_id
FROM ns.customers c
LEFT JOIN ns.orders o ON c.customer_id = o.customer_id

-- RIGHT OUTER JOIN (must be the first join)
SELECT c.name, o.order_id
FROM ns.orders o
RIGHT JOIN ns.customers c ON o.customer_id = c.customer_id
```

**JOIN constraints**: JOIN predicates must include either all primary-key columns OR a secondary-index column from the joined table. FULL OUTER JOIN is NOT supported.

## Aggregate Functions

Supported aggregate functions: `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`

```sql
SELECT COUNT(*) FROM ns.orders WHERE customer_id = ?
SELECT customer_id, SUM(amount) FROM ns.orders GROUP BY customer_id
SELECT customer_id, AVG(amount) FROM ns.orders GROUP BY customer_id HAVING AVG(amount) > 100
```

Only `COUNT` supports `*`. All other aggregates require a column name.

## SQL Limitations

- **No DISTINCT** keyword
- **No subqueries**
- **No CTEs** (Common Table Expressions / WITH clause)
- **No window functions**
- **No FULL OUTER JOIN**
- **No UNION / INTERSECT / EXCEPT**
- JOIN predicates must reference primary key or secondary index columns
- WHERE clause must be in disjunctive normal form (OR of ANDs) or conjunctive normal form (AND of ORs)

## 2PC via SQL Statements

For two-phase commit in JDBC, use SQL transaction control statements:

```java
try (Statement stmt = conn.createStatement()) {
    stmt.execute("PREPARE");
}
try (Statement stmt = conn.createStatement()) {
    stmt.execute("VALIDATE"); // Only if SERIALIZABLE + EXTRA_READ
}
conn.commit();
```

See the 2PC patterns rule for complete details.
