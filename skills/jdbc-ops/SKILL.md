---
description: Show ScalarDB JDBC/SQL operation patterns — SELECT, INSERT, UPSERT, UPDATE, DELETE, JOIN, aggregates with examples.
user_invocable: true
---

# /scalardb:jdbc-ops — ScalarDB JDBC/SQL Operations Guide

## Instructions

You are a ScalarDB JDBC/SQL operations expert. Show the user how to perform specific SQL operations with the ScalarDB JDBC driver.

## Interactive Flow

### Step 1: Determine the operation
Ask: "What SQL operation do you need help with?" if not specified.

Options:
- **SELECT** — Query records (single record, range, all)
- **INSERT** — Insert new records (fails if exists)
- **UPSERT** — Insert or update records
- **UPDATE** — Update existing records
- **DELETE** — Delete records
- **JOIN** — Query across multiple tables (INNER, LEFT, RIGHT)
- **Aggregates** — COUNT, SUM, AVG, MIN, MAX with GROUP BY/HAVING
- **2PC** — Two-phase commit via SQL statements (PREPARE, VALIDATE, COMMIT)
- **Exception handling** — Correct JDBC exception handling pattern

### Step 2: Gather context
Ask about their schema:
- Namespace and table name(s)
- Column names and types
- Primary key and clustering key columns
- What conditions/filters they need

### Step 3: Generate code
Generate the complete code example including:
- Connection setup with `setAutoCommit(false)`
- PreparedStatement with parameter binding
- Proper try-with-resources for Connection, PreparedStatement, ResultSet
- Correct JDBC data type mapping
- Exception handling with error code 301 check
- Commit for all transactions (including read-only)
- Rollback in catch blocks (except error code 301)

## Reference

Read `.claude/docs/api-reference.md` and `.claude/docs/sql-reference.md` for the complete SQL reference.

## Quick Reference Examples

### SELECT by Primary Key
```java
try (Connection conn = getConnection()) {
    try {
        try (PreparedStatement ps = conn.prepareStatement(
            "SELECT * FROM ns.customers WHERE customer_id = ?")) {
            ps.setInt(1, customerId);
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) {
                    String name = rs.getString("name");
                    int age = rs.getInt("age");
                }
            }
        }
        conn.commit(); // Always commit, even for reads
    } catch (SQLException e) {
        if (e.getErrorCode() != 301) conn.rollback();
        throw e;
    }
}
```

### SELECT with ORDER BY and LIMIT
```java
try (PreparedStatement ps = conn.prepareStatement(
    "SELECT * FROM ns.orders WHERE customer_id = ? ORDER BY \"timestamp\" DESC LIMIT 10")) {
    ps.setInt(1, customerId);
    try (ResultSet rs = ps.executeQuery()) {
        while (rs.next()) {
            String orderId = rs.getString("order_id");
            long timestamp = rs.getLong("timestamp");
        }
    }
}
```

### INSERT
```java
try (PreparedStatement ps = conn.prepareStatement(
    "INSERT INTO ns.customers (customer_id, name, credit_limit) VALUES (?, ?, ?)")) {
    ps.setInt(1, 1);
    ps.setString(2, "Alice");
    ps.setInt(3, 10000);
    ps.executeUpdate();
}
```

### UPSERT
```java
try (PreparedStatement ps = conn.prepareStatement(
    "UPSERT INTO ns.customers (customer_id, name, credit_limit) VALUES (?, ?, ?)")) {
    ps.setInt(1, 1);
    ps.setString(2, "Alice");
    ps.setInt(3, 15000);
    ps.executeUpdate();
}
```

### UPDATE
```java
try (PreparedStatement ps = conn.prepareStatement(
    "UPDATE ns.customers SET credit_limit = ? WHERE customer_id = ?")) {
    ps.setInt(1, 20000);
    ps.setInt(2, 1);
    ps.executeUpdate();
}
```

### DELETE
```java
try (PreparedStatement ps = conn.prepareStatement(
    "DELETE FROM ns.orders WHERE customer_id = ? AND \"timestamp\" = ?")) {
    ps.setInt(1, 1);
    ps.setLong(2, timestamp);
    ps.executeUpdate();
}
```

### INNER JOIN
```java
try (PreparedStatement ps = conn.prepareStatement(
    "SELECT o.order_id, c.name, o.\"timestamp\" " +
    "FROM ns.orders o " +
    "INNER JOIN ns.customers c ON o.customer_id = c.customer_id " +
    "WHERE o.customer_id = ? " +
    "ORDER BY o.\"timestamp\" DESC")) {
    ps.setInt(1, customerId);
    try (ResultSet rs = ps.executeQuery()) {
        while (rs.next()) {
            String orderId = rs.getString("order_id");
            String name = rs.getString("name");
        }
    }
}
```

### LEFT JOIN
```java
try (PreparedStatement ps = conn.prepareStatement(
    "SELECT c.name, o.order_id " +
    "FROM ns.customers c " +
    "LEFT JOIN ns.orders o ON c.customer_id = o.customer_id " +
    "WHERE c.customer_id = ?")) {
    ps.setInt(1, customerId);
    try (ResultSet rs = ps.executeQuery()) {
        while (rs.next()) {
            String name = rs.getString("name");
            String orderId = rs.getString("order_id"); // may be null
        }
    }
}
```

### Aggregates with GROUP BY / HAVING
```java
try (PreparedStatement ps = conn.prepareStatement(
    "SELECT customer_id, COUNT(*) AS order_count, SUM(amount) AS total " +
    "FROM ns.orders " +
    "GROUP BY customer_id " +
    "HAVING COUNT(*) > ?")) {
    ps.setInt(1, 5);
    try (ResultSet rs = ps.executeQuery()) {
        while (rs.next()) {
            int custId = rs.getInt("customer_id");
            int count = rs.getInt("order_count");
            long total = rs.getLong("total");
        }
    }
}
```

### Temporal Data Types
```java
// DATE
ps.setObject(1, LocalDate.of(2024, 1, 15));
LocalDate date = rs.getObject("col", LocalDate.class);

// TIME
ps.setObject(1, LocalTime.of(14, 30, 0));
LocalTime time = rs.getObject("col", LocalTime.class);

// TIMESTAMP
ps.setObject(1, LocalDateTime.of(2024, 1, 15, 14, 30));
LocalDateTime ts = rs.getObject("col", LocalDateTime.class);

// TIMESTAMPTZ
ps.setObject(1, Instant.now());
Instant tstz = rs.getObject("col", Instant.class);
```

### 2PC via SQL
```java
// After SQL operations, before conn.commit():
try (Statement stmt = conn.createStatement()) {
    stmt.execute("PREPARE");
}
try (Statement stmt = conn.createStatement()) {
    stmt.execute("VALIDATE"); // Only if SERIALIZABLE + EXTRA_READ
}
conn.commit();
```

### Complete Transaction Pattern with Retry
```java
private static final int MAX_RETRIES = 3;

public void executeWithRetry() throws SQLException, InterruptedException {
    int retryCount = 0;
    SQLException lastException = null;

    while (true) {
        if (retryCount > 0) {
            if (retryCount >= MAX_RETRIES) throw lastException;
            TimeUnit.MILLISECONDS.sleep(100 * retryCount);
        }
        retryCount++;

        try (Connection conn = getConnection()) {
            conn.setAutoCommit(false);
            try {
                // ... SQL operations ...
                conn.commit();
                return;
            } catch (SQLException e) {
                if (e.getErrorCode() == 301) {
                    // UnknownTransactionStatusException — do NOT rollback
                    // Verify if committed, retry only if not
                    throw e;
                }
                conn.rollback();
                lastException = e;
            }
        } catch (SQLException e) {
            lastException = e;
        }
    }
}
```

## SQL Limitations

- No `DISTINCT`, no subqueries, no CTEs, no window functions
- No `FULL OUTER JOIN`, no `UNION`/`INTERSECT`/`EXCEPT`
- JOIN predicates must reference primary key or secondary index columns
- `RIGHT OUTER JOIN` must be the first join
- WHERE must be in DNF (OR of ANDs) or CNF (AND of ORs)
- `UPSERT` is a ScalarDB-specific SQL extension (not standard SQL)
- For DATE/TIME/TIMESTAMP/TIMESTAMPTZ, use `setObject()`/`getObject()`, NOT legacy JDBC methods

## Output Format

Provide complete, runnable code examples with proper imports, try-with-resources, and exception handling. Tailor examples to the user's specific schema.
