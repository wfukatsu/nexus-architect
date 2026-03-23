# Cluster + JDBC/SQL + One-Phase Commit

Standard SQL interface via ScalarDB Cluster with JDBC driver.

## build.gradle

```groovy
plugins {
    id 'java'
    id 'application'
}

repositories {
    mavenCentral()
}

dependencies {
    implementation 'com.scalar-labs:scalardb-sql-jdbc:3.16.0'
    implementation 'com.scalar-labs:scalardb-cluster-java-client-sdk:3.16.0'
    implementation 'info.picocli:picocli:4.7.1'
    runtimeOnly 'org.apache.logging.log4j:log4j-slf4j2-impl:2.20.0'
    runtimeOnly 'org.apache.logging.log4j:log4j-core:2.20.0'
}

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(8)
    }
}

application {
    mainClass = 'sample.command.SampleCommand'
}
```

## scalardb-sql.properties

```properties
scalar.db.sql.connection_mode=cluster
scalar.db.sql.cluster_mode.contact_points=indirect:localhost

# Auth (if enabled)
#scalar.db.cluster.auth.enabled=true
#scalar.db.sql.cluster_mode.username=admin
#scalar.db.sql.cluster_mode.password=admin
```

## schema.sql

```sql
CREATE COORDINATOR TABLES IF NOT EXIST;

CREATE NAMESPACE IF NOT EXISTS sample;

CREATE TABLE IF NOT EXISTS sample.customers (
  customer_id INT PRIMARY KEY,
  name TEXT,
  credit_limit INT,
  credit_total INT
);

CREATE TABLE IF NOT EXISTS sample.orders (
  customer_id INT,
  "timestamp" BIGINT,
  order_id TEXT,
  PRIMARY KEY (customer_id, "timestamp")
);

CREATE INDEX IF NOT EXISTS ON sample.orders (order_id);

CREATE TABLE IF NOT EXISTS sample.items (
  item_id INT PRIMARY KEY,
  name TEXT,
  price INT
);
```

## Service Class

```java
package sample;

import java.io.Closeable;
import java.io.IOException;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

public class Sample implements Closeable {

  // JDBC URL format: jdbc:scalardb:<config-file-path>
  private static final String JDBC_URL = "jdbc:scalardb:scalardb-sql.properties";

  private Connection getConnection() throws SQLException {
    Connection connection = DriverManager.getConnection(JDBC_URL);
    connection.setAutoCommit(false); // CRITICAL: always disable auto-commit
    return connection;
  }

  // READ: Get customer info
  public String getCustomerInfo(int customerId) throws SQLException {
    try (Connection conn = getConnection()) {
      try {
        String info;
        try (PreparedStatement ps = conn.prepareStatement(
            "SELECT * FROM sample.customers WHERE customer_id = ?")) {
          ps.setInt(1, customerId);
          try (ResultSet rs = ps.executeQuery()) {
            if (!rs.next()) {
              conn.commit(); // Always commit, even read-only
              throw new RuntimeException("Customer not found: " + customerId);
            }
            String name = rs.getString("name");
            int creditLimit = rs.getInt("credit_limit");
            int creditTotal = rs.getInt("credit_total");
            info = String.format("%s (limit=%d, total=%d)", name, creditLimit, creditTotal);
          }
        }
        conn.commit(); // Always commit, even read-only
        return info;
      } catch (Exception e) {
        conn.rollback();
        throw e;
      }
    }
  }

  // WRITE: Place an order
  public String placeOrder(int customerId, int itemId, int count) throws SQLException {
    try (Connection conn = getConnection()) {
      try {
        // Get item price
        int price;
        try (PreparedStatement ps = conn.prepareStatement(
            "SELECT price FROM sample.items WHERE item_id = ?")) {
          ps.setInt(1, itemId);
          try (ResultSet rs = ps.executeQuery()) {
            if (!rs.next()) throw new RuntimeException("Item not found");
            price = rs.getInt("price");
          }
        }

        // Check customer credit
        int creditLimit, creditTotal;
        try (PreparedStatement ps = conn.prepareStatement(
            "SELECT credit_limit, credit_total FROM sample.customers WHERE customer_id = ?")) {
          ps.setInt(1, customerId);
          try (ResultSet rs = ps.executeQuery()) {
            if (!rs.next()) throw new RuntimeException("Customer not found");
            creditLimit = rs.getInt("credit_limit");
            creditTotal = rs.getInt("credit_total");
          }
        }

        int orderTotal = price * count;
        if (creditTotal + orderTotal > creditLimit) {
          throw new RuntimeException("Credit limit exceeded");
        }

        // Insert order
        String orderId = UUID.randomUUID().toString();
        try (PreparedStatement ps = conn.prepareStatement(
            "INSERT INTO sample.orders (customer_id, \"timestamp\", order_id) VALUES (?, ?, ?)")) {
          ps.setInt(1, customerId);
          ps.setLong(2, System.currentTimeMillis());
          ps.setString(3, orderId);
          ps.executeUpdate();
        }

        // Update customer credit
        try (PreparedStatement ps = conn.prepareStatement(
            "UPDATE sample.customers SET credit_total = ? WHERE customer_id = ?")) {
          ps.setInt(1, creditTotal + orderTotal);
          ps.setInt(2, customerId);
          ps.executeUpdate();
        }

        conn.commit();
        return orderId;
      } catch (Exception e) {
        conn.rollback();
        throw e;
      }
    }
  }

  // SCAN: Get orders with JOIN
  public List<String> getOrdersWithCustomerName(int customerId) throws SQLException {
    try (Connection conn = getConnection()) {
      try {
        List<String> results = new ArrayList<>();
        try (PreparedStatement ps = conn.prepareStatement(
            "SELECT o.order_id, o.\"timestamp\", c.name " +
            "FROM sample.orders o " +
            "INNER JOIN sample.customers c ON o.customer_id = c.customer_id " +
            "WHERE o.customer_id = ? " +
            "ORDER BY o.\"timestamp\" DESC")) {
          ps.setInt(1, customerId);
          try (ResultSet rs = ps.executeQuery()) {
            while (rs.next()) {
              results.add(String.format("Order %s by %s at %d",
                  rs.getString("order_id"),
                  rs.getString("name"),
                  rs.getLong("timestamp")));
            }
          }
        }
        conn.commit();
        return results;
      } catch (Exception e) {
        conn.rollback();
        throw e;
      }
    }
  }

  // Aggregate example
  public int getTotalSpending(int customerId) throws SQLException {
    try (Connection conn = getConnection()) {
      try {
        int total;
        try (PreparedStatement ps = conn.prepareStatement(
            "SELECT credit_total FROM sample.customers WHERE customer_id = ?")) {
          ps.setInt(1, customerId);
          try (ResultSet rs = ps.executeQuery()) {
            if (!rs.next()) throw new RuntimeException("Customer not found");
            total = rs.getInt("credit_total");
          }
        }
        conn.commit();
        return total;
      } catch (Exception e) {
        conn.rollback();
        throw e;
      }
    }
  }

  @Override
  public void close() throws IOException {
    // Connections are obtained per operation; no persistent state to close
  }
}
```

## Schema Loading

```bash
# Using ScalarDB Cluster SQL CLI
java -jar scalardb-cluster-sql-cli-<VERSION>-all.jar \
  --config scalardb-sql.properties \
  -f schema.sql

# Or using Schema Loader with JSON
java -jar scalardb-cluster-schema-loader-<VERSION>-all.jar \
  --config database.properties -f schema.json --coordinator
```

## JDBC SQL vs CRUD API Comparison

| Feature | JDBC/SQL | CRUD API |
|---------|---------|---------|
| JOINs | Supported | Not supported |
| Aggregates | COUNT, SUM, AVG, MIN, MAX | Not supported |
| GROUP BY/HAVING | Supported | Not supported |
| Syntax | Standard SQL | Builder pattern |
| Reserved words | Must quote (`"timestamp"`) | N/A |
| Connection | `DriverManager.getConnection()` | `TransactionFactory.create()` |
| Auto-commit | Must set to `false` | N/A |

## Important JDBC Notes

1. **Always `setAutoCommit(false)`** — ScalarDB requires explicit transaction management
2. **Always commit** even for read-only transactions
3. **Always rollback** in catch blocks
4. **Use try-with-resources** for Connection, PreparedStatement, ResultSet
5. **Quote reserved words** in SQL: `"timestamp"`, `"order"`, `"key"`, etc.
6. **Use `PreparedStatement`** with parameter binding (never concatenate values)
7. **Use `namespace.table` format** in SQL statements
