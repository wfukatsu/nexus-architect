package com.example.orders;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.scalar.db.api.DistributedTransaction;
import com.scalar.db.api.DistributedTransactionManager;
import com.scalar.db.api.Get;
import com.scalar.db.api.Put;
import com.scalar.db.api.Result;
import com.scalar.db.api.TwoPhaseCommitTransaction;
import com.scalar.db.api.TwoPhaseCommitTransactionManager;
import com.scalar.db.exception.transaction.PreparationConflictException;
import com.scalar.db.exception.transaction.TransactionException;
import com.scalar.db.io.Key;
import java.util.Optional;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Two-phase commit across two participants (order + inventory), on a real engine.
 * These assert the protocol's failure behaviour, which is what the design's 2PC claims rest on.
 */
class TwoPhaseCommitIT {

    private static ScalarDbTestBackend backend;
    private static TwoPhaseCommitTransactionManager twoPc;
    private static TwoPhaseCommitTransactionManager twoPcParticipant;
    private static DistributedTransactionManager manager;
    private static final String TENANT = "tenant-1";

    @BeforeAll static void boot() throws Exception {
        backend = new ScalarDbTestBackend();
        twoPc = backend.twoPhaseCommit();
        twoPcParticipant = backend.twoPhaseCommitParticipant();
        manager = backend.manager();
    }

    @AfterAll static void down() throws Exception { if (backend != null) backend.close(); }

    // ---- helpers ----------------------------------------------------------

    private static Put orderPut(String id, String status) {
        return Put.newBuilder().namespace(ScalarDbTestBackend.NS).table(ScalarDbTestBackend.ORDERS)
                .partitionKey(Key.ofText("tenant_id", TENANT))
                .clusteringKey(Key.ofText("order_id", id))
                .textValue("customer_id", "alice").textValue("status", status)
                .intValue("total_amount", 100).build();
    }

    private static Get orderGet(String id) {
        return Get.newBuilder().namespace(ScalarDbTestBackend.NS).table(ScalarDbTestBackend.ORDERS)
                .partitionKey(Key.ofText("tenant_id", TENANT))
                .clusteringKey(Key.ofText("order_id", id)).build();
    }

    private static Put stockPut(String product, int available, int reserved) {
        return Put.newBuilder().namespace(ScalarDbTestBackend.NS).table(ScalarDbTestBackend.INVENTORY)
                .partitionKey(Key.ofText("tenant_id", TENANT))
                .clusteringKey(Key.ofText("product_id", product))
                .intValue("available", available).intValue("reserved", reserved).build();
    }

    private static Get stockGet(String product) {
        return Get.newBuilder().namespace(ScalarDbTestBackend.NS).table(ScalarDbTestBackend.INVENTORY)
                .partitionKey(Key.ofText("tenant_id", TENANT))
                .clusteringKey(Key.ofText("product_id", product)).build();
    }

    private static void seedStock(String product, int available) throws Exception {
        DistributedTransaction tx = manager.begin();
        tx.put(stockPut(product, available, 0));
        tx.commit();
    }

    private static Optional<Result> read(Get g) throws Exception {
        DistributedTransaction tx = manager.begin();
        Optional<Result> r = tx.get(g);
        tx.commit();
        return r;
    }

    // ---- happy path -------------------------------------------------------

    @Test
    @DisplayName("2PC happy path: both participants prepare, validate, then commit")
    void happyPath() throws Exception {
        seedStock("P-6001", 10);

        TwoPhaseCommitTransaction coordinator = twoPc.begin();
        TwoPhaseCommitTransaction participant = twoPcParticipant.join(coordinator.getId());

        coordinator.put(orderPut("O-6001", "CONFIRMED"));
        participant.get(stockGet("P-6001"));
        participant.put(stockPut("P-6001", 9, 1));

        coordinator.prepare();
        participant.prepare();      // ALL prepare before ANY commits
        coordinator.validate();
        participant.validate();
        coordinator.commit();
        participant.commit();

        assertEquals("CONFIRMED", read(orderGet("O-6001")).orElseThrow().getText("status"));
        assertEquals(9, read(stockGet("P-6001")).orElseThrow().getInt("available"));
    }

    // ---- failure paths ----------------------------------------------------

    @Test
    @DisplayName("A participant whose prepare conflicts forces the whole transaction to roll back")
    void participantPrepareConflictRollsBackEveryone() throws Exception {
        seedStock("P-6002", 10);

        // A competing writer takes the stock row first.
        DistributedTransaction competitor = manager.begin();
        competitor.get(stockGet("P-6002"));
        competitor.put(stockPut("P-6002", 5, 5));
        competitor.commit();

        TwoPhaseCommitTransaction coordinator = twoPc.begin();
        TwoPhaseCommitTransaction participant = twoPcParticipant.join(coordinator.getId());
        coordinator.get(orderGet("O-6002"));
        coordinator.put(orderPut("O-6002", "CONFIRMED"));
        participant.get(stockGet("P-6002"));

        DistributedTransaction sneak = manager.begin();
        sneak.get(stockGet("P-6002"));
        sneak.put(stockPut("P-6002", 4, 6));
        sneak.commit();                            // invalidates what the participant read

        participant.put(stockPut("P-6002", 9, 1));
        coordinator.prepare();
        assertThrows(PreparationConflictException.class, participant::prepare);

        // The coordinator prepared successfully; it MUST still roll back, or the order commits
        // against stock that was never reserved.
        coordinator.rollback();
        participant.rollback();

        assertTrue(read(orderGet("O-6002")).isEmpty(),
                "the order must not exist — its participant could not prepare");
        assertEquals(4, read(stockGet("P-6002")).orElseThrow().getInt("available"),
                "the competitor's value must stand");
    }

    @Test
    @DisplayName("Committing without preparing is rejected — the protocol is not optional")
    void commitWithoutPrepareIsRejected() throws Exception {
        TwoPhaseCommitTransaction coordinator = twoPc.begin();
        coordinator.put(orderPut("O-6003", "CONFIRMED"));
        // Protocol misuse is an UNCHECKED IllegalStateException, not a TransactionException —
        // a handler that catches only TransactionException will not see it.
        assertThrows(IllegalStateException.class, coordinator::commit,
                "commit before prepare must not be accepted");
        assertDoesNotThrow(coordinator::rollback);
        assertTrue(read(orderGet("O-6003")).isEmpty());
    }

    @Test
    @DisplayName("Rollback after a partial prepare leaves no partial state")
    void rollbackAfterPartialPrepare() throws Exception {
        seedStock("P-6004", 10);
        TwoPhaseCommitTransaction coordinator = twoPc.begin();
        TwoPhaseCommitTransaction participant = twoPcParticipant.join(coordinator.getId());

        coordinator.put(orderPut("O-6004", "CONFIRMED"));
        participant.get(stockGet("P-6004"));
        participant.put(stockPut("P-6004", 9, 1));

        coordinator.prepare();          // one side prepared, the other never does
        coordinator.rollback();
        participant.rollback();

        assertTrue(read(orderGet("O-6004")).isEmpty(), "no half-committed order");
        assertEquals(10, read(stockGet("P-6004")).orElseThrow().getInt("available"),
                "stock untouched");
    }
}
