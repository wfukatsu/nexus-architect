# ScalarDB Coding Patterns

## Entity Class

```java
public class Order {
    private final String orderId;        // Partition Key
    private final String customerId;     // Clustering Key
    private String status;
    private int totalAmount;
    private Instant createdAt;

    // Construct from ScalarDB Get result
    public static Order fromResult(Result result) {
        return new Order(
            result.getText("order_id"),
            result.getText("customer_id"),
            result.getText("status"),
            result.getInt("total_amount"),
            result.getTimestampTZ("created_at")
        );
    }
}
```

## Repository Pattern

```java
public class OrderRepository {
    private static final String NAMESPACE = "order_service";
    private static final String TABLE = "orders";

    public Optional<Order> findById(DistributedTransaction tx, String orderId)
            throws CrudException {
        Get get = Get.newBuilder()
            .namespace(NAMESPACE)
            .table(TABLE)
            .partitionKey(Key.ofText("order_id", orderId))
            .build();
        return tx.get(get).map(Order::fromResult);
    }

    public void save(DistributedTransaction tx, Order order) throws CrudException {
        Put put = Put.newBuilder()
            .namespace(NAMESPACE)
            .table(TABLE)
            .partitionKey(Key.ofText("order_id", order.getOrderId()))
            .clusteringKey(Key.ofText("customer_id", order.getCustomerId()))
            .textValue("status", order.getStatus())
            .intValue("total_amount", order.getTotalAmount())
            .build();
        tx.put(put);
    }
}
```

## Transaction Management

### Consensus Commit (Single Service)

```java
DistributedTransaction tx = manager.begin();
try {
    // CRUD operations
    Order order = orderRepo.findById(tx, orderId).orElseThrow();
    order.updateStatus("CONFIRMED");
    orderRepo.save(tx, order);
    tx.commit();
} catch (CommitConflictException e) {
    tx.rollback();
    // Retry with exponential backoff, max 3-5 attempts
} catch (UnknownTransactionStatusException e) {
    // Commit status unknown - manual verification required
} catch (TransactionException e) {
    tx.rollback();
    throw e;
}
```

### Two-Phase Commit (Cross-Microservice)

```java
// Coordinator
TwoPhaseCommitTransaction tx = manager.begin();
String txId = tx.getId();
// Send txId to participants

// Participant
TwoPhaseCommitTransaction tx = manager.join(txId);
// CRUD operations
tx.prepare();

// Coordinator
tx.prepare();
tx.validate();
tx.commit();
```

## Constraints

- 2PC: Limit to a maximum of 2-3 services
- OCC conflict rate: Target below 5%
- Coordinator table: Must be protected (direct manipulation prohibited)
- Metadata overhead: Approximately 200 bytes per record
- DB-specific features: Cannot be used on ScalarDB-managed tables
