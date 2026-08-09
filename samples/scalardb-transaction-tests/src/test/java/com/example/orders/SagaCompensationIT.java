package com.example.orders;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.scalar.db.api.DistributedTransaction;
import com.scalar.db.api.DistributedTransactionManager;
import com.scalar.db.api.Get;
import com.scalar.db.api.Put;
import com.scalar.db.api.Result;
import com.scalar.db.io.Key;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Saga shape: forward steps that each commit locally, with a compensation per step, and a
 * coordinator that unwinds in reverse when a later step fails.
 *
 * SCOPE: this exercises the saga PATTERN over ScalarDB local transactions. It is not ScalarDB Saga
 * the product (3.19.0-alpha.1), which is not a dependency here. What it establishes is what a
 * design review can check for: that every step has a compensation, that compensation is idempotent,
 * and that a partially-applied saga leaves no forward effect behind.
 */
class SagaCompensationIT {

    private static ScalarDbTestBackend backend;
    private static DistributedTransactionManager manager;
    private static final String TENANT = "tenant-1";

    @BeforeAll static void boot() throws Exception {
        backend = new ScalarDbTestBackend();
        manager = backend.manager();
    }

    @AfterAll static void down() throws Exception { if (backend != null) backend.close(); }

    // ---- saga engine ------------------------------------------------------

    interface Step {
        String name();
        void forward() throws Exception;
        void compensate() throws Exception;
    }

    /** Runs steps in order; on failure, compensates the applied ones in reverse. */
    private static void runSaga(String sagaId, List<Step> steps) throws Exception {
        Deque<Step> applied = new ArrayDeque<>();
        try {
            for (Step s : steps) {
                s.forward();
                recordStep(sagaId, s.name(), "APPLIED");
                applied.push(s);
            }
        } catch (Exception failure) {
            while (!applied.isEmpty()) {
                Step s = applied.pop();
                s.compensate();
                recordStep(sagaId, s.name(), "COMPENSATED");
            }
            throw failure;
        }
    }

    private static void recordStep(String sagaId, String step, String state) throws Exception {
        DistributedTransaction tx = manager.begin();
        tx.get(Get.newBuilder().namespace(ScalarDbTestBackend.NS).table(ScalarDbTestBackend.SAGA_LOG)
                .partitionKey(Key.ofText("tenant_id", TENANT))
                .clusteringKey(Key.newBuilder().addText("saga_id", sagaId)
                        .addText("step", step).build()).build());
        tx.put(Put.newBuilder().namespace(ScalarDbTestBackend.NS).table(ScalarDbTestBackend.SAGA_LOG)
                .partitionKey(Key.ofText("tenant_id", TENANT))
                .clusteringKey(Key.newBuilder().addText("saga_id", sagaId)
                        .addText("step", step).build())
                .textValue("state", state).build());
        tx.commit();
    }

    private static String stepState(String sagaId, String step) throws Exception {
        DistributedTransaction tx = manager.begin();
        Optional<Result> r = tx.get(Get.newBuilder()
                .namespace(ScalarDbTestBackend.NS).table(ScalarDbTestBackend.SAGA_LOG)
                .partitionKey(Key.ofText("tenant_id", TENANT))
                .clusteringKey(Key.newBuilder().addText("saga_id", sagaId)
                        .addText("step", step).build()).build());
        tx.commit();
        return r.map(x -> x.getText("state")).orElse("NONE");
    }

    // ---- domain operations -------------------------------------------------

    private static void seedStock(String product, int available, int reserved) throws Exception {
        DistributedTransaction tx = manager.begin();
        tx.get(stockGet(product));
        tx.put(Put.newBuilder().namespace(ScalarDbTestBackend.NS).table(ScalarDbTestBackend.INVENTORY)
                .partitionKey(Key.ofText("tenant_id", TENANT))
                .clusteringKey(Key.ofText("product_id", product))
                .intValue("available", available).intValue("reserved", reserved).build());
        tx.commit();
    }

    private static Get stockGet(String product) {
        return Get.newBuilder().namespace(ScalarDbTestBackend.NS).table(ScalarDbTestBackend.INVENTORY)
                .partitionKey(Key.ofText("tenant_id", TENANT))
                .clusteringKey(Key.ofText("product_id", product)).build();
    }

    private static int available(String product) throws Exception {
        DistributedTransaction tx = manager.begin();
        Optional<Result> r = tx.get(stockGet(product));
        tx.commit();
        return r.orElseThrow().getInt("available");
    }

    private static int reserved(String product) throws Exception {
        DistributedTransaction tx = manager.begin();
        Optional<Result> r = tx.get(stockGet(product));
        tx.commit();
        return r.orElseThrow().getInt("reserved");
    }

    /** Move n units available -> reserved, in one local transaction. */
    private static void reserve(String product, int n) throws Exception {
        DistributedTransaction tx = manager.begin();
        Result row = tx.get(stockGet(product)).orElseThrow();
        int a = row.getInt("available");
        int r = row.getInt("reserved");
        if (a < n) {
            tx.rollback();
            throw new IllegalStateException("insufficient stock");
        }
        tx.put(Put.newBuilder().namespace(ScalarDbTestBackend.NS).table(ScalarDbTestBackend.INVENTORY)
                .partitionKey(Key.ofText("tenant_id", TENANT))
                .clusteringKey(Key.ofText("product_id", product))
                .intValue("available", a - n).intValue("reserved", r + n).build());
        tx.commit();
    }

    /**
     * Compensation for reserve. Idempotent: it releases only what is still reserved, so running
     * it twice does not inflate available stock.
     */
    private static void releaseReservation(String product, int n) throws Exception {
        DistributedTransaction tx = manager.begin();
        Result row = tx.get(stockGet(product)).orElseThrow();
        int a = row.getInt("available");
        int r = row.getInt("reserved");
        int release = Math.min(n, r);
        tx.put(Put.newBuilder().namespace(ScalarDbTestBackend.NS).table(ScalarDbTestBackend.INVENTORY)
                .partitionKey(Key.ofText("tenant_id", TENANT))
                .clusteringKey(Key.ofText("product_id", product))
                .intValue("available", a + release).intValue("reserved", r - release).build());
        tx.commit();
    }

    // ---- tests -------------------------------------------------------------

    @Test
    @DisplayName("Saga happy path: every step applies and stock reflects the reservation")
    void sagaHappyPath() throws Exception {
        seedStock("P-7001", 10, 0);
        runSaga("S-7001", List.of(step("reserve-stock",
                () -> reserve("P-7001", 3), () -> releaseReservation("P-7001", 3))));
        assertEquals(7, available("P-7001"));
        assertEquals(3, reserved("P-7001"));
        assertEquals("APPLIED", stepState("S-7001", "reserve-stock"));
    }

    @Test
    @DisplayName("A failing later step compensates the earlier one — no forward effect survives")
    void laterStepFailureCompensatesEarlier() throws Exception {
        seedStock("P-7002", 10, 0);

        Step reserveStep = step("reserve-stock",
                () -> reserve("P-7002", 4), () -> releaseReservation("P-7002", 4));
        Step payStep = step("authorize-payment",
                () -> { throw new IllegalStateException("payment declined"); },
                () -> { /* nothing was applied */ });

        assertThrows(IllegalStateException.class,
                () -> runSaga("S-7002", List.of(reserveStep, payStep)));

        assertEquals(10, available("P-7002"), "the reservation must have been released");
        assertEquals(0, reserved("P-7002"));
        assertEquals("COMPENSATED", stepState("S-7002", "reserve-stock"));
        assertEquals("NONE", stepState("S-7002", "authorize-payment"),
                "a step that never applied must not be logged as applied");
    }

    @Test
    @DisplayName("Compensation is idempotent — running it twice does not inflate stock")
    void compensationIsIdempotent() throws Exception {
        seedStock("P-7003", 10, 0);
        reserve("P-7003", 5);
        assertEquals(5, available("P-7003"));

        releaseReservation("P-7003", 5);
        releaseReservation("P-7003", 5);   // redelivery of the same compensation

        assertEquals(10, available("P-7003"), "a replayed compensation created stock");
        assertEquals(0, reserved("P-7003"));
    }

    @Test
    @DisplayName("A step with no compensation leaves its effect behind — the defect to detect")
    void stepWithoutCompensationLeaksState() throws Exception {
        seedStock("P-7004", 10, 0);

        Step uncompensated = step("reserve-stock",
                () -> reserve("P-7004", 6), () -> { /* MISSING compensation */ });
        Step failing = step("authorize-payment",
                () -> { throw new IllegalStateException("payment declined"); }, () -> { });

        assertThrows(IllegalStateException.class,
                () -> runSaga("S-7004", List.of(uncompensated, failing)));

        assertEquals(4, available("P-7004"),
                "expected the defect: stock stays reserved after the saga failed");
        assertTrue(reserved("P-7004") == 6);
    }

    // ---- step helper -------------------------------------------------------

    private interface Action { void run() throws Exception; }

    private static Step step(String name, Action forward, Action compensate) {
        return new Step() {
            public String name() { return name; }
            public void forward() throws Exception { forward.run(); }
            public void compensate() throws Exception { compensate.run(); }
        };
    }
}
