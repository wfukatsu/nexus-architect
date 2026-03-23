# Core + CRUD API + One-Phase Commit

The most common pattern for development and single-database applications.

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
    implementation 'com.scalar-labs:scalardb:3.16.0'
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

## database.properties

```properties
# MySQL
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:mysql://localhost:3306/
scalar.db.username=root
scalar.db.password=mysql

# PostgreSQL (alternative)
#scalar.db.storage=jdbc
#scalar.db.contact_points=jdbc:postgresql://localhost:5432/
#scalar.db.username=postgres
#scalar.db.password=postgres

# Cassandra (alternative)
#scalar.db.storage=cassandra
#scalar.db.contact_points=localhost
#scalar.db.username=cassandra
#scalar.db.password=cassandra

# DynamoDB Local (alternative)
#scalar.db.storage=dynamo
#scalar.db.contact_points=sample
#scalar.db.username=sample
#scalar.db.password=sample
#scalar.db.dynamo.endpoint_override=http://localhost:8000
```

## schema.json

```json
{
  "sample.customers": {
    "transaction": true,
    "partition-key": ["customer_id"],
    "columns": {
      "customer_id": "INT",
      "name": "TEXT",
      "credit_limit": "INT",
      "credit_total": "INT"
    }
  },
  "sample.orders": {
    "transaction": true,
    "partition-key": ["customer_id"],
    "clustering-key": ["timestamp"],
    "columns": {
      "customer_id": "INT",
      "timestamp": "BIGINT",
      "order_id": "TEXT"
    },
    "secondary-index": ["order_id"]
  },
  "sample.items": {
    "transaction": true,
    "partition-key": ["item_id"],
    "columns": {
      "item_id": "INT",
      "name": "TEXT",
      "price": "INT"
    }
  }
}
```

## Service Class

```java
package sample;

import com.scalar.db.api.DistributedTransaction;
import com.scalar.db.api.DistributedTransactionManager;
import com.scalar.db.api.Get;
import com.scalar.db.api.Insert;
import com.scalar.db.api.Result;
import com.scalar.db.api.Scan;
import com.scalar.db.api.Update;
import com.scalar.db.api.Delete;
import com.scalar.db.exception.transaction.CommitConflictException;
import com.scalar.db.exception.transaction.CrudConflictException;
import com.scalar.db.exception.transaction.RollbackException;
import com.scalar.db.exception.transaction.TransactionException;
import com.scalar.db.exception.transaction.UnknownTransactionStatusException;
import com.scalar.db.exception.transaction.UnsatisfiedConditionException;
import com.scalar.db.io.Key;
import com.scalar.db.service.TransactionFactory;
import java.io.Closeable;
import java.io.IOException;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public class Sample implements Closeable {

  private final DistributedTransactionManager manager;

  public Sample(String configFile) throws TransactionException {
    TransactionFactory factory = TransactionFactory.create(configFile);
    manager = factory.getTransactionManager();
  }

  // READ: Get a customer by ID
  public String getCustomerInfo(int customerId) throws TransactionException {
    DistributedTransaction tx = null;
    try {
      tx = manager.begin();

      Optional<Result> result = tx.get(
          Get.newBuilder()
              .namespace("sample")
              .table("customers")
              .partitionKey(Key.ofInt("customer_id", customerId))
              .build());

      if (!result.isPresent()) {
        tx.commit();
        throw new RuntimeException("Customer not found: " + customerId);
      }

      String name = result.get().getText("name");
      int creditLimit = result.get().getInt("credit_limit");
      int creditTotal = result.get().getInt("credit_total");

      tx.commit();
      return String.format("%s (limit=%d, total=%d)", name, creditLimit, creditTotal);
    } catch (Exception e) {
      if (tx != null) {
        try { tx.abort(); } catch (Exception ex) { /* log */ }
      }
      throw e;
    }
  }

  // WRITE: Place an order with retry
  public String placeOrder(int customerId, int[] itemIds, int[] itemCounts)
      throws TransactionException, InterruptedException {
    int retryCount = 0;
    TransactionException lastException = null;

    while (true) {
      if (retryCount > 0) {
        if (retryCount >= 3) throw lastException;
        java.util.concurrent.TimeUnit.MILLISECONDS.sleep(100 * retryCount);
      }
      retryCount++;

      DistributedTransaction tx = null;
      try {
        tx = manager.begin();
        String orderId = UUID.randomUUID().toString();

        // Check customer exists and has credit
        Optional<Result> customer = tx.get(
            Get.newBuilder()
                .namespace("sample")
                .table("customers")
                .partitionKey(Key.ofInt("customer_id", customerId))
                .build());

        if (!customer.isPresent()) {
          tx.commit();
          throw new RuntimeException("Customer not found");
        }

        // Calculate total
        int total = 0;
        for (int i = 0; i < itemIds.length; i++) {
          Optional<Result> item = tx.get(
              Get.newBuilder()
                  .namespace("sample")
                  .table("items")
                  .partitionKey(Key.ofInt("item_id", itemIds[i]))
                  .build());

          if (!item.isPresent()) {
            tx.commit();
            throw new RuntimeException("Item not found: " + itemIds[i]);
          }
          total += item.get().getInt("price") * itemCounts[i];
        }

        // Check credit
        int creditLimit = customer.get().getInt("credit_limit");
        int creditTotal = customer.get().getInt("credit_total");
        if (creditTotal + total > creditLimit) {
          tx.commit();
          throw new RuntimeException("Credit limit exceeded");
        }

        // Insert order
        tx.insert(
            Insert.newBuilder()
                .namespace("sample")
                .table("orders")
                .partitionKey(Key.ofInt("customer_id", customerId))
                .clusteringKey(Key.ofBigInt("timestamp", System.currentTimeMillis()))
                .textValue("order_id", orderId)
                .build());

        // Update credit total
        tx.update(
            Update.newBuilder()
                .namespace("sample")
                .table("customers")
                .partitionKey(Key.ofInt("customer_id", customerId))
                .intValue("credit_total", creditTotal + total)
                .build());

        tx.commit();
        return orderId;

      } catch (UnsatisfiedConditionException e) {
        if (tx != null) {
          try { tx.rollback(); } catch (RollbackException ex) { /* log */ }
        }
        throw e;
      } catch (UnknownTransactionStatusException e) {
        throw e;
      } catch (TransactionException e) {
        if (tx != null) {
          try { tx.rollback(); } catch (RollbackException ex) { /* log */ }
        }
        lastException = e;
      }
    }
  }

  // SCAN: Get orders by customer
  public List<Result> getOrdersByCustomer(int customerId) throws TransactionException {
    DistributedTransaction tx = null;
    try {
      tx = manager.begin();

      List<Result> orders = tx.scan(
          Scan.newBuilder()
              .namespace("sample")
              .table("orders")
              .partitionKey(Key.ofInt("customer_id", customerId))
              .ordering(Scan.Ordering.desc("timestamp"))
              .build());

      tx.commit();
      return orders;
    } catch (Exception e) {
      if (tx != null) {
        try { tx.abort(); } catch (Exception ex) { /* log */ }
      }
      throw e;
    }
  }

  // GET BY INDEX
  public Optional<Result> getOrderById(String orderId) throws TransactionException {
    DistributedTransaction tx = null;
    try {
      tx = manager.begin();

      Optional<Result> order = tx.get(
          Get.newBuilder()
              .namespace("sample")
              .table("orders")
              .indexKey(Key.ofText("order_id", orderId))
              .build());

      tx.commit();
      return order;
    } catch (Exception e) {
      if (tx != null) {
        try { tx.abort(); } catch (Exception ex) { /* log */ }
      }
      throw e;
    }
  }

  // DELETE
  public void deleteOrder(int customerId, long timestamp) throws TransactionException {
    DistributedTransaction tx = null;
    try {
      tx = manager.begin();

      tx.delete(
          Delete.newBuilder()
              .namespace("sample")
              .table("orders")
              .partitionKey(Key.ofInt("customer_id", customerId))
              .clusteringKey(Key.ofBigInt("timestamp", timestamp))
              .build());

      tx.commit();
    } catch (Exception e) {
      if (tx != null) {
        try { tx.abort(); } catch (Exception ex) { /* log */ }
      }
      throw e;
    }
  }

  @Override
  public void close() throws IOException {
    manager.close();
  }
}
```

## docker-compose.yml (MySQL)

```yaml
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: mysql
    ports:
      - "3306:3306"
    healthcheck:
      test: mysqladmin ping -h localhost -u root -pmysql
      interval: 5s
      timeout: 10s
      retries: 10
```

## Schema Loading

```bash
# Download schema loader
curl -OL https://github.com/scalar-labs/scalardb/releases/download/v3.16.0/scalardb-schema-loader-3.16.0.jar

# Create tables
java -jar scalardb-schema-loader-3.16.0.jar --config database.properties -f schema.json --coordinator

# Delete tables
java -jar scalardb-schema-loader-3.16.0.jar --config database.properties -f schema.json -D --coordinator
```
