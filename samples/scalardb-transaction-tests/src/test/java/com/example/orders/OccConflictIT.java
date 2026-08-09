package com.example.orders;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.scalar.db.api.DistributedTransaction;
import com.scalar.db.api.DistributedTransactionManager;
import com.scalar.db.api.Get;
import com.scalar.db.api.Put;
import com.scalar.db.api.Result;
import com.scalar.db.exception.transaction.CommitConflictException;
import com.scalar.db.exception.transaction.TransactionException;
import com.scalar.db.io.Key;
import java.util.Optional;
import java.util.concurrent.Callable;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/** OCC conflict behaviour, on a real engine. */
class OccConflictIT {

    private static ScalarDbTestBackend backend;
    private static DistributedTransactionManager manager;
    private static OrderApplicationService service;
    private static final Caller ALICE = new Caller("alice", "tenant-1");

    @BeforeAll static void boot() throws Exception {
        backend = new ScalarDbTestBackend();
        manager = backend.manager();
        service = new ConformingOrderService(manager);
    }

    @AfterAll static void down() throws Exception { if (backend != null) backend.close(); }

    private static void seed(String orderId, String status) throws Exception {
        DistributedTransaction tx = manager.begin();
        tx.put(Put.newBuilder().namespace(ScalarDbTestBackend.NS).table(ScalarDbTestBackend.ORDERS)
                .partitionKey(Key.ofText("tenant_id", ALICE.tenantId()))
                .clusteringKey(Key.ofText("order_id", orderId))
                .textValue("customer_id", ALICE.subject())
                .textValue("status", status)
                .intValue("total_amount", 500).build());
        tx.commit();
    }

    private static Get get(String orderId) {
        return Get.newBuilder().namespace(ScalarDbTestBackend.NS).table(ScalarDbTestBackend.ORDERS)
                .partitionKey(Key.ofText("tenant_id", ALICE.tenantId()))
                .clusteringKey(Key.ofText("order_id", orderId)).build();
    }

    private static Put statusPut(String orderId, String status) {
        return Put.newBuilder().namespace(ScalarDbTestBackend.NS).table(ScalarDbTestBackend.ORDERS)
                .partitionKey(Key.ofText("tenant_id", ALICE.tenantId()))
                .clusteringKey(Key.ofText("order_id", orderId))
                .textValue("status", status).build();
    }

    private static String statusOf(String orderId) throws Exception {
        DistributedTransaction tx = manager.begin();
        Optional<Result> r = tx.get(get(orderId));
        tx.commit();
        return r.orElseThrow().getText("status");
    }

    @Test
    @DisplayName("Deterministic OCC: the transaction that reads first and commits second loses")
    void deterministicConflict() throws Exception {
        seed("O-5001", "DRAFT");

        DistributedTransaction slow = manager.begin();
        slow.get(get("O-5001"));                    // slow reads the pre-image

        DistributedTransaction fast = manager.begin();
        fast.get(get("O-5001"));
        fast.put(statusPut("O-5001", "CONFIRMED"));
        fast.commit();                              // fast wins

        slow.put(statusPut("O-5001", "CANCELLED"));
        assertThrows(CommitConflictException.class, slow::commit,
                "the stale writer must be rejected, not silently overwrite");
        assertEquals("CONFIRMED", statusOf("O-5001"), "the winner's write must survive");
    }

    @Test
    @DisplayName("Concurrent confirm: exactly one succeeds, the loser never double-applies")
    void concurrentConfirmIsSerialized() throws Exception {
        seed("O-5002", "DRAFT");

        ExecutorService pool = Executors.newFixedThreadPool(2);
        CyclicBarrier gate = new CyclicBarrier(2);
        AtomicInteger confirmed = new AtomicInteger();
        AtomicInteger stateConflicts = new AtomicInteger();
        AtomicInteger occFailures = new AtomicInteger();

        Callable<Void> attempt = () -> {
            gate.await(10, TimeUnit.SECONDS);
            try {
                service.confirm("O-5002", "idem-" + Thread.currentThread().getId(), ALICE);
                confirmed.incrementAndGet();
            } catch (IllegalOrderStateException e) {
                stateConflicts.incrementAndGet();   // lost the race, saw CONFIRMED, refused
            } catch (TransactionException e) {
                occFailures.incrementAndGet();      // retries exhausted -> 409 at the API layer
            }
            return null;
        };

        Future<Void> a = pool.submit(attempt);
        Future<Void> b = pool.submit(attempt);
        a.get(30, TimeUnit.SECONDS);
        b.get(30, TimeUnit.SECONDS);
        pool.shutdownNow();

        assertEquals("CONFIRMED", statusOf("O-5002"));
        assertEquals(1, confirmed.get(), "exactly one confirm may succeed");
        assertEquals(1, stateConflicts.get() + occFailures.get(),
                "the loser must fail cleanly, not silently succeed");
        assertTrue(stateConflicts.get() + occFailures.get() == 1);
    }

    @Test
    @DisplayName("The service's retry absorbs a conflict that clears — no conflict reaches the caller")
    void retryAbsorbsTransientConflict() throws Exception {
        seed("O-5003", "DRAFT");
        // A conflicting writer that commits once, before the service's first attempt commits.
        DistributedTransaction interference = manager.begin();
        interference.get(get("O-5003"));
        interference.put(statusPut("O-5003", "DRAFT"));   // same value, still a version bump
        interference.commit();

        service.confirm("O-5003", "idem-5003", ALICE);    // must succeed on a retry
        assertEquals("CONFIRMED", statusOf("O-5003"));
    }
}
