package com.example.orders;

import static com.example.orders.OrderSchema.IDEMPOTENCY;
import static com.example.orders.OrderSchema.INVENTORY;
import static com.example.orders.OrderSchema.NS;
import static com.example.orders.OrderSchema.ORDERS;
import static com.example.orders.OrderSchema.SAGA_LOG;

import com.scalar.db.api.DistributedTransaction;
import com.scalar.db.api.DistributedTransactionManager;
import com.scalar.db.api.Get;
import com.scalar.db.api.Put;
import com.scalar.db.api.PutBuilder;
import com.scalar.db.api.Result;
import com.scalar.db.exception.transaction.TransactionException;
import com.scalar.db.io.Key;
import java.util.Optional;

/**
 * Row addressing for the scenario suites: one builder per table of {@link OrderSchema}, keyed the
 * way the schema is keyed, so a test states only the values it cares about. The {@code Put}
 * builders stop at the keys because what a scenario writes is the scenario.
 */
final class Rows {

    private Rows() {
    }

    // ---- orders (tenant_id, order_id) -------------------------------------

    static Get orderGet(String tenant, String orderId) {
        return Get.newBuilder().namespace(NS).table(ORDERS)
                .partitionKey(Key.ofText("tenant_id", tenant))
                .clusteringKey(Key.ofText("order_id", orderId)).build();
    }

    static PutBuilder.Buildable order(String tenant, String orderId) {
        return Put.newBuilder().namespace(NS).table(ORDERS)
                .partitionKey(Key.ofText("tenant_id", tenant))
                .clusteringKey(Key.ofText("order_id", orderId));
    }

    // ---- inventory (tenant_id, product_id) --------------------------------

    static Get stockGet(String tenant, String product) {
        return Get.newBuilder().namespace(NS).table(INVENTORY)
                .partitionKey(Key.ofText("tenant_id", tenant))
                .clusteringKey(Key.ofText("product_id", product)).build();
    }

    static Put stockPut(String tenant, String product, int available, int reserved) {
        return Put.newBuilder().namespace(NS).table(INVENTORY)
                .partitionKey(Key.ofText("tenant_id", tenant))
                .clusteringKey(Key.ofText("product_id", product))
                .intValue("available", available).intValue("reserved", reserved).build();
    }

    // ---- idempotency (tenant_id, idempotency_key) -------------------------

    static Get idempotencyGet(String tenant, String key) {
        return Get.newBuilder().namespace(NS).table(IDEMPOTENCY)
                .partitionKey(Key.ofText("tenant_id", tenant))
                .clusteringKey(Key.ofText("idempotency_key", key)).build();
    }

    // ---- saga_log (tenant_id, (saga_id, step)) ----------------------------

    /** The composite clustering key is ONE {@code Key} (rules/scalardb-crud-patterns.md). */
    private static Key sagaStepKey(String sagaId, String step) {
        return Key.newBuilder().addText("saga_id", sagaId).addText("step", step).build();
    }

    static Get sagaStepGet(String tenant, String sagaId, String step) {
        return Get.newBuilder().namespace(NS).table(SAGA_LOG)
                .partitionKey(Key.ofText("tenant_id", tenant))
                .clusteringKey(sagaStepKey(sagaId, step)).build();
    }

    static Put sagaStepPut(String tenant, String sagaId, String step, String state) {
        return Put.newBuilder().namespace(NS).table(SAGA_LOG)
                .partitionKey(Key.ofText("tenant_id", tenant))
                .clusteringKey(sagaStepKey(sagaId, step))
                .textValue("state", state).build();
    }

    // ---- one committed read -----------------------------------------------

    /** What a later request would see: one transaction, one {@code Get}, committed. */
    static Optional<Result> readOnce(DistributedTransactionManager manager, Get get)
            throws TransactionException {
        DistributedTransaction tx = manager.begin();
        Optional<Result> r = tx.get(get);
        tx.commit();
        return r;
    }
}
