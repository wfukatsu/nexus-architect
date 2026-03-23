# Cluster + CRUD API + Two-Phase Commit

Production multi-service transactions using ScalarDB Cluster with the CRUD API.

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
    implementation 'com.scalar-labs:scalardb-cluster-java-client-sdk:3.16.0'
    implementation 'info.picocli:picocli:4.7.1'
    runtimeOnly 'org.apache.logging.log4j:log4j-slf4j2-impl:2.20.0'
    runtimeOnly 'org.apache.logging.log4j:log4j-core:2.20.0'
}
```

## database.properties

```properties
scalar.db.transaction_manager=cluster
scalar.db.contact_points=indirect:localhost

# Auth (if enabled)
#scalar.db.cluster.auth.enabled=true
#scalar.db.username=admin
#scalar.db.password=admin
```

## Service Class (Coordinator)

```java
package sample.order;

import com.scalar.db.api.Get;
import com.scalar.db.api.Insert;
import com.scalar.db.api.Result;
import com.scalar.db.api.Scan;
import com.scalar.db.api.TwoPhaseCommitTransaction;
import com.scalar.db.api.TwoPhaseCommitTransactionManager;
import com.scalar.db.exception.transaction.RollbackException;
import com.scalar.db.exception.transaction.TransactionException;
import com.scalar.db.exception.transaction.UnknownTransactionStatusException;
import com.scalar.db.io.Key;
import com.scalar.db.service.TransactionFactory;
import java.io.Closeable;
import java.io.IOException;
import java.util.Optional;
import java.util.UUID;

public class OrderService implements Closeable {

  private final TwoPhaseCommitTransactionManager manager;
  private final CustomerServiceClient customerClient; // gRPC client to customer service

  public OrderService(String configFile, CustomerServiceClient customerClient)
      throws TransactionException {
    TransactionFactory factory = TransactionFactory.create(configFile);
    manager = factory.getTwoPhaseCommitTransactionManager();
    this.customerClient = customerClient;
  }

  public String placeOrder(int customerId, int itemId, int count)
      throws TransactionException {
    TwoPhaseCommitTransaction tx = null;
    try {
      // 1. Coordinator begins transaction
      tx = manager.begin();
      String txId = tx.getId();

      // 2. CRUD operations on local data
      Optional<Result> item = tx.get(
          Get.newBuilder()
              .namespace("order_service")
              .table("items")
              .partitionKey(Key.ofInt("item_id", itemId))
              .build());

      if (!item.isPresent()) {
        throw new RuntimeException("Item not found");
      }
      int amount = item.get().getInt("price") * count;

      String orderId = UUID.randomUUID().toString();
      tx.insert(
          Insert.newBuilder()
              .namespace("order_service")
              .table("orders")
              .partitionKey(Key.ofInt("customer_id", customerId))
              .clusteringKey(Key.ofBigInt("timestamp", System.currentTimeMillis()))
              .textValue("order_id", orderId)
              .build());

      // 3. Call participant via gRPC (participant calls join(txId) internally)
      customerClient.payment(txId, customerId, amount);

      // 4. Prepare ALL
      tx.prepare();
      customerClient.prepare(txId);

      // 5. Validate ALL
      tx.validate();
      customerClient.validate(txId);

      // 6. Commit ALL — if any succeeds, transaction is committed
      tx.commit();
      customerClient.commit(txId);

      return orderId;
    } catch (UnknownTransactionStatusException e) {
      throw e; // Don't rollback
    } catch (Exception e) {
      if (tx != null) {
        try { tx.rollback(); } catch (RollbackException ex) { /* log */ }
        try { customerClient.rollback(tx.getId()); } catch (Exception ex) { /* log */ }
      }
      if (e instanceof TransactionException) throw (TransactionException) e;
      throw new RuntimeException(e);
    }
  }

  @Override
  public void close() throws IOException {
    manager.close();
  }
}
```

## Service Class (Participant)

```java
package sample.customer;

import com.scalar.db.api.Get;
import com.scalar.db.api.Result;
import com.scalar.db.api.TwoPhaseCommitTransaction;
import com.scalar.db.api.TwoPhaseCommitTransactionManager;
import com.scalar.db.api.Update;
import com.scalar.db.exception.transaction.TransactionException;
import com.scalar.db.io.Key;
import com.scalar.db.service.TransactionFactory;
import java.io.Closeable;
import java.io.IOException;
import java.util.Optional;

public class CustomerService implements Closeable {

  private final TwoPhaseCommitTransactionManager manager;

  public CustomerService(String configFile) throws TransactionException {
    TransactionFactory factory = TransactionFactory.create(configFile);
    manager = factory.getTwoPhaseCommitTransactionManager();
  }

  // Called by coordinator via gRPC
  public void payment(String txId, int customerId, int amount)
      throws TransactionException {
    // Join the coordinator's transaction
    TwoPhaseCommitTransaction tx = manager.join(txId);

    Optional<Result> customer = tx.get(
        Get.newBuilder()
            .namespace("customer_service")
            .table("customers")
            .partitionKey(Key.ofInt("customer_id", customerId))
            .build());

    if (!customer.isPresent()) {
      throw new RuntimeException("Customer not found");
    }

    int creditLimit = customer.get().getInt("credit_limit");
    int creditTotal = customer.get().getInt("credit_total");

    if (creditTotal + amount > creditLimit) {
      throw new RuntimeException("Credit limit exceeded");
    }

    tx.update(
        Update.newBuilder()
            .namespace("customer_service")
            .table("customers")
            .partitionKey(Key.ofInt("customer_id", customerId))
            .intValue("credit_total", creditTotal + amount)
            .build());
    // Don't commit — coordinator drives the 2PC protocol
  }

  // 2PC lifecycle methods (called by coordinator via gRPC)
  public void prepare(String txId) throws TransactionException {
    TwoPhaseCommitTransaction tx = manager.resume(txId);
    tx.prepare();
  }

  public void validate(String txId) throws TransactionException {
    TwoPhaseCommitTransaction tx = manager.resume(txId);
    tx.validate();
  }

  public void commit(String txId) throws TransactionException {
    TwoPhaseCommitTransaction tx = manager.resume(txId);
    tx.commit();
  }

  public void rollback(String txId) throws TransactionException {
    TwoPhaseCommitTransaction tx = manager.resume(txId);
    tx.rollback();
  }

  @Override
  public void close() throws IOException {
    manager.close();
  }
}
```

## Key Differences from Core+CRUD+2PC

| Aspect | Core+CRUD+2PC | Cluster+CRUD+2PC |
|--------|--------------|------------------|
| Maven artifact | `scalardb` | `scalardb-cluster-java-client-sdk` |
| Config | `scalar.db.storage=<backend>` | `scalar.db.transaction_manager=cluster` |
| DB access | Direct | Via ScalarDB Cluster |
| Auth/TLS | N/A | Supported |
| Java 2PC code | Identical | Identical |

## 2PC Request Routing

For 2PC transactions, requests must route to the same ScalarDB Cluster node:
- **gRPC (same connection)**: Automatically routes correctly
- **L7 load balancer**: Must use session affinity
- **Direct-Kubernetes mode**: Client handles routing via consistent hashing
