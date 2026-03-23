# ScalarDB コーディングパターン

## エンティティクラス

```java
public class Order {
    private final String orderId;        // Partition Key
    private final String customerId;     // Clustering Key
    private String status;
    private int totalAmount;
    private Instant createdAt;

    // ScalarDB Get結果からの構築
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

## リポジトリパターン

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

## トランザクション管理

### Consensus Commit（単一サービス）

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
    // リトライ（指数バックオフ、最大3-5回）
} catch (UnknownTransactionStatusException e) {
    // コミット状態不明 - 手動確認が必要
} catch (TransactionException e) {
    tx.rollback();
    throw e;
}
```

### Two-Phase Commit（マイクロサービス間）

```java
// Coordinator
TwoPhaseCommitTransaction tx = manager.begin();
String txId = tx.getId();
// Participantに txId を送信

// Participant
TwoPhaseCommitTransaction tx = manager.join(txId);
// CRUD operations
tx.prepare();

// Coordinator
tx.prepare();
tx.validate();
tx.commit();
```

## 制約事項

- 2PC: 最大2-3サービスに制限
- OCC競合率: 5%未満を目標
- Coordinatorテーブル: 保護必須（直接操作禁止）
- メタデータオーバーヘッド: レコードあたり約200バイト
- DB固有機能: ScalarDB管理テーブルでは使用不可
