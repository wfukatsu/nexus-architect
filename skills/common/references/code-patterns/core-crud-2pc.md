# Core + CRUD API + Two-Phase Commit

For applications that need ACID transactions across multiple databases or microservices.

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
```

## Configuration (Two Databases)

### database-customer.properties

```properties
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:mysql://localhost:3306/
scalar.db.username=root
scalar.db.password=mysql
```

### database-order.properties

```properties
scalar.db.storage=cassandra
scalar.db.contact_points=localhost
scalar.db.username=cassandra
scalar.db.password=cassandra
```

## schema-customer.json

```json
{
  "customer_service.customers": {
    "transaction": true,
    "partition-key": ["customer_id"],
    "columns": {
      "customer_id": "INT",
      "name": "TEXT",
      "credit_limit": "INT",
      "credit_total": "INT"
    }
  }
}
```

## schema-order.json

```json
{
  "order_service.orders": {
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
  "order_service.items": {
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

## Service Class (Coordinator Pattern)

```java
package sample;

import com.scalar.db.api.Get;
import com.scalar.db.api.Insert;
import com.scalar.db.api.Result;
import com.scalar.db.api.TwoPhaseCommitTransaction;
import com.scalar.db.api.TwoPhaseCommitTransactionManager;
import com.scalar.db.api.Update;
import com.scalar.db.exception.transaction.PreparationConflictException;
import com.scalar.db.exception.transaction.PreparationException;
import com.scalar.db.exception.transaction.RollbackException;
import com.scalar.db.exception.transaction.TransactionException;
import com.scalar.db.exception.transaction.UnknownTransactionStatusException;
import com.scalar.db.exception.transaction.ValidationConflictException;
import com.scalar.db.exception.transaction.ValidationException;
import com.scalar.db.io.Key;
import com.scalar.db.service.TransactionFactory;
import java.io.Closeable;
import java.io.IOException;
import java.util.Optional;
import java.util.UUID;

public class TwoPhaseCommitSample implements Closeable {

  private final TwoPhaseCommitTransactionManager customerManager;
  private final TwoPhaseCommitTransactionManager orderManager;

  public TwoPhaseCommitSample(String customerConfig, String orderConfig)
      throws TransactionException {
    TransactionFactory customerFactory = TransactionFactory.create(customerConfig);
    customerManager = customerFactory.getTwoPhaseCommitTransactionManager();

    TransactionFactory orderFactory = TransactionFactory.create(orderConfig);
    orderManager = orderFactory.getTwoPhaseCommitTransactionManager();
  }

  /**
   * Place an order across two databases using two-phase commit.
   * The order manager acts as coordinator, customer manager as participant.
   */
  public String placeOrder(int customerId, int itemId, int count)
      throws TransactionException, InterruptedException {
    int retryCount = 0;
    TransactionException lastException = null;

    while (true) {
      if (retryCount > 0) {
        if (retryCount >= 3) throw lastException;
        java.util.concurrent.TimeUnit.MILLISECONDS.sleep(100 * retryCount);
      }
      retryCount++;

      TwoPhaseCommitTransaction orderTx = null;
      TwoPhaseCommitTransaction customerTx = null;

      try {
        // Step 1: Coordinator begins transaction
        orderTx = orderManager.begin();
        String txId = orderTx.getId();

        // Step 2: Participant joins with same transaction ID
        customerTx = customerManager.join(txId);

        // Step 3: CRUD operations on both participants
        // Get item price
        Optional<Result> item = orderTx.get(
            Get.newBuilder()
                .namespace("order_service")
                .table("items")
                .partitionKey(Key.ofInt("item_id", itemId))
                .build());
        if (!item.isPresent()) {
          throw new RuntimeException("Item not found: " + itemId);
        }
        int price = item.get().getInt("price");

        // Check customer credit
        Optional<Result> customer = customerTx.get(
            Get.newBuilder()
                .namespace("customer_service")
                .table("customers")
                .partitionKey(Key.ofInt("customer_id", customerId))
                .build());
        if (!customer.isPresent()) {
          throw new RuntimeException("Customer not found: " + customerId);
        }

        int creditLimit = customer.get().getInt("credit_limit");
        int creditTotal = customer.get().getInt("credit_total");
        int orderTotal = price * count;

        if (creditTotal + orderTotal > creditLimit) {
          throw new RuntimeException("Credit limit exceeded");
        }

        // Insert order
        String orderId = UUID.randomUUID().toString();
        orderTx.insert(
            Insert.newBuilder()
                .namespace("order_service")
                .table("orders")
                .partitionKey(Key.ofInt("customer_id", customerId))
                .clusteringKey(Key.ofBigInt("timestamp", System.currentTimeMillis()))
                .textValue("order_id", orderId)
                .build());

        // Update customer credit
        customerTx.update(
            Update.newBuilder()
                .namespace("customer_service")
                .table("customers")
                .partitionKey(Key.ofInt("customer_id", customerId))
                .intValue("credit_total", creditTotal + orderTotal)
                .build());

        // Step 4: Prepare ALL participants
        orderTx.prepare();
        customerTx.prepare();

        // Step 5: Validate ALL participants
        orderTx.validate();
        customerTx.validate();

        // Step 6: Commit ALL participants
        // If ANY commit succeeds, the transaction is considered committed
        orderTx.commit();
        customerTx.commit();

        return orderId;

      } catch (PreparationConflictException | ValidationConflictException e) {
        // Conflict during prepare/validate — retry
        rollbackAll(orderTx, customerTx);
        lastException = e;
      } catch (UnknownTransactionStatusException e) {
        // Don't rollback — status unknown
        throw e;
      } catch (TransactionException e) {
        rollbackAll(orderTx, customerTx);
        lastException = e;
      } catch (RuntimeException e) {
        rollbackAll(orderTx, customerTx);
        throw e;
      }
    }
  }

  private void rollbackAll(TwoPhaseCommitTransaction... transactions) {
    for (TwoPhaseCommitTransaction tx : transactions) {
      if (tx != null) {
        try { tx.rollback(); } catch (RollbackException e) { /* log */ }
      }
    }
  }

  @Override
  public void close() throws IOException {
    customerManager.close();
    orderManager.close();
  }
}
```

## Microservice Pattern (gRPC)

In a real microservice architecture, each service has its own `TwoPhaseCommitTransactionManager`. The coordinator sends the transaction ID to participants via RPC:

```
Coordinator (OrderService):
  1. tm.begin()          → get txId
  2. CRUD on local DB
  3. Send txId to participant via gRPC
  4. tm.resume(txId).prepare()
  5. Tell participant to prepare
  6. tm.resume(txId).validate()
  7. Tell participant to validate
  8. tm.resume(txId).commit()
  9. Tell participant to commit

Participant (CustomerService):
  1. tm.join(txId)       → join transaction
  2. CRUD on local DB
  3. (return to coordinator)
  4. tm.resume(txId).prepare()
  5. tm.resume(txId).validate()
  6. tm.resume(txId).commit()
```

## docker-compose.yml

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

  cassandra:
    image: cassandra:3.11
    ports:
      - "9042:9042"
    environment:
      CASSANDRA_CLUSTER_NAME: test
    healthcheck:
      test: cqlsh -e 'describe cluster'
      interval: 10s
      timeout: 10s
      retries: 20

networks:
  default:
    name: sample-network
```

## Key 2PC Rules

1. **Coordinator** calls `begin()`, participants call `join(txId)`
2. **All** participants must be prepared before committing
3. If **any** prepare fails, **all** must rollback
4. If **any** commit succeeds, the transaction is considered committed
5. `validate()` is only needed for `SERIALIZABLE` isolation with `EXTRA_READ` strategy
6. Use different transaction IDs on retry (never reuse)
7. Group commit cannot be used with 2PC
