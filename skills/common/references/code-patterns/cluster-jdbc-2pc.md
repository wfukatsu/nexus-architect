# Cluster + JDBC/SQL + Two-Phase Commit

Multi-service transactions using ScalarDB Cluster with the SQL/JDBC interface.

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
```

## scalardb-sql.properties

```properties
scalar.db.sql.connection_mode=cluster
scalar.db.sql.cluster_mode.contact_points=indirect:localhost
```

## Service Class (Coordinator — SQL 2PC)

In JDBC/SQL mode, two-phase commit is managed via SQL transaction control statements:

```java
package sample.order;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.UUID;

public class OrderService {

  private static final String JDBC_URL = "jdbc:scalardb:scalardb-sql.properties";

  private Connection getConnection() throws SQLException {
    Connection conn = DriverManager.getConnection(JDBC_URL);
    conn.setAutoCommit(false);
    return conn;
  }

  /**
   * Place an order using SQL 2PC.
   * The SQL interface supports PREPARE, VALIDATE, and COMMIT statements.
   */
  public String placeOrder(int customerId, int itemId, int count) throws SQLException {
    try (Connection conn = getConnection()) {
      try {
        // Get item price
        int price;
        try (PreparedStatement ps = conn.prepareStatement(
            "SELECT price FROM order_service.items WHERE item_id = ?")) {
          ps.setInt(1, itemId);
          try (ResultSet rs = ps.executeQuery()) {
            if (!rs.next()) throw new RuntimeException("Item not found");
            price = rs.getInt("price");
          }
        }

        // Insert order
        String orderId = UUID.randomUUID().toString();
        try (PreparedStatement ps = conn.prepareStatement(
            "INSERT INTO order_service.orders (customer_id, \"timestamp\", order_id) VALUES (?, ?, ?)")) {
          ps.setInt(1, customerId);
          ps.setLong(2, System.currentTimeMillis());
          ps.setString(3, orderId);
          ps.executeUpdate();
        }

        // For 2PC with remote participant, you would:
        // 1. Send transaction ID to participant service
        // 2. Participant does its work (joins via its own connection)
        // 3. Coordinator executes PREPARE, VALIDATE, COMMIT via SQL

        // SQL 2PC protocol
        try (Statement stmt = conn.createStatement()) {
          stmt.execute("PREPARE");
        }
        try (Statement stmt = conn.createStatement()) {
          stmt.execute("VALIDATE");
        }

        conn.commit(); // Final commit

        return orderId;
      } catch (Exception e) {
        conn.rollback();
        throw e;
      }
    }
  }
}
```

## SQL Transaction Control Statements

```sql
-- Begin a transaction (implicit with setAutoCommit(false))
BEGIN;
-- or
START TRANSACTION;

-- Standard commit
COMMIT;

-- Standard rollback
ROLLBACK;
-- or
ABORT;

-- Two-phase commit protocol
PREPARE;
VALIDATE;
COMMIT;
```

## Key Notes for JDBC 2PC

1. **SQL 2PC** uses `PREPARE`, `VALIDATE`, `COMMIT` SQL statements
2. **Same connection routing**: All statements in a 2PC transaction must go to the same ScalarDB Cluster node
3. **Session affinity**: Required when using L7 load balancers
4. **Participant coordination**: Still requires RPC between services to coordinate the 2PC protocol
5. **VALIDATE** is only needed for `SERIALIZABLE` isolation with `EXTRA_READ` strategy

## Comparison with CRUD 2PC

| Aspect | CRUD 2PC | JDBC 2PC |
|--------|---------|---------|
| Prepare | `tx.prepare()` | `stmt.execute("PREPARE")` |
| Validate | `tx.validate()` | `stmt.execute("VALIDATE")` |
| Commit | `tx.commit()` | `conn.commit()` |
| Rollback | `tx.rollback()` | `conn.rollback()` |
| Transaction ID | `tx.getId()` | Managed by connection |
| Join participant | `manager.join(txId)` | Via SQL session |
