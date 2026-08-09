package com.example.orders;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.scalar.db.api.DistributedTransaction;
import com.scalar.db.api.DistributedTransactionManager;
import com.scalar.db.api.Get;
import com.scalar.db.api.Put;
import com.scalar.db.api.Result;
import com.scalar.db.exception.transaction.CommitConflictException;
import com.scalar.db.io.Key;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Runs the transaction design against a real ScalarDB instance (SQLite storage).
 * These assert runtime behaviour that static review cannot: what actually commits,
 * what a second caller can actually read, and what survives a conflict.
 */
class OrderTransactionIT {

    private static ScalarDbTestBackend backend;
    private static DistributedTransactionManager manager;
    private static OrderApplicationService serviceA;
    private static OrderApplicationService serviceB;

    private static final Caller ALICE = new Caller("alice", "tenant-1");
    private static final Caller BOB = new Caller("bob", "tenant-1");
    private static final Caller CARLA = new Caller("carla", "tenant-2");

    @BeforeAll
    static void boot() throws Exception {
        backend = new ScalarDbTestBackend();
        manager = backend.manager();
        serviceA = new ConformingOrderService(manager);
        serviceB = new NonConformingOrderService(manager);
    }

    @AfterAll
    static void shutdown() throws Exception {
        if (backend != null) {
            backend.close();
        }
    }

    // ---- helpers ----------------------------------------------------------

    private static void seedOrder(Caller owner, String orderId, String status, int total,
            String email) throws Exception {
        DistributedTransaction tx = manager.begin();
        tx.put(Put.newBuilder().namespace(ScalarDbTestBackend.NS).table(ScalarDbTestBackend.ORDERS)
                .partitionKey(Key.ofText("tenant_id", owner.tenantId()))
                .clusteringKey(Key.ofText("order_id", orderId))
                .textValue("customer_id", owner.subject())
                .textValue("customer_email", email)
                .textValue("status", status)
                .intValue("total_amount", total).build());
        tx.commit();
    }

    private static Optional<Result> readOrder(Caller owner, String orderId) throws Exception {
        DistributedTransaction tx = manager.begin();
        Optional<Result> r = tx.get(Get.newBuilder()
                .namespace(ScalarDbTestBackend.NS).table(ScalarDbTestBackend.ORDERS)
                .partitionKey(Key.ofText("tenant_id", owner.tenantId()))
                .clusteringKey(Key.ofText("order_id", orderId)).build());
        tx.commit();
        return r;
    }

    private static Optional<Result> readIdempotency(Caller owner, String key) throws Exception {
        DistributedTransaction tx = manager.begin();
        Optional<Result> r = tx.get(Get.newBuilder()
                .namespace(ScalarDbTestBackend.NS).table(ScalarDbTestBackend.IDEMPOTENCY)
                .partitionKey(Key.ofText("tenant_id", owner.tenantId()))
                .clusteringKey(Key.ofText("idempotency_key", key)).build());
        tx.commit();
        return r;
    }

    // ---- TX-001 / TX-002 --------------------------------------------------

    @Test
    @DisplayName("TX-001: createDraft commits a DRAFT order the owner can read back")
    void tx001_createDraft() throws Exception {
        OrderView created = serviceA.createDraft(
                new DraftOrderCommand(List.of(new DraftOrderCommand.Line("P-1001", 2))), ALICE);
        assertEquals("DRAFT", created.status());
        Optional<Result> row = readOrder(ALICE, created.orderId());
        assertTrue(row.isPresent(), "the draft was not committed");
        assertEquals("alice", row.get().getText("customer_id"));
    }

    @Test
    @DisplayName("TX-002: a read-only transaction commits and returns the order")
    void tx002_readOnlyCommits() throws Exception {
        seedOrder(ALICE, "O-2001", "CONFIRMED", 3980, "alice@example.com");
        OrderView v = serviceA.get("O-2001", ALICE);
        assertEquals("CONFIRMED", v.status());
        assertEquals(3980, v.totalAmount());
    }

    @Test
    @DisplayName("TX-002: another customer in the same tenant gets not-found, not the order")
    void tx002_ownershipEnforced() throws Exception {
        seedOrder(ALICE, "O-2002", "CONFIRMED", 100, "alice@example.com");
        assertThrows(OrderNotFoundException.class, () -> serviceA.get("O-2002", BOB));
    }

    @Test
    @DisplayName("TX-002: another tenant cannot reach the order at all")
    void tx002_tenantIsolation() throws Exception {
        seedOrder(ALICE, "O-2003", "CONFIRMED", 100, "alice@example.com");
        assertThrows(OrderNotFoundException.class, () -> serviceA.get("O-2003", CARLA));
    }

    @Test
    @DisplayName("TX-002: the confidential customer_email never reaches the domain view")
    void tx002_confidentialFieldNotCarried() throws Exception {
        seedOrder(ALICE, "O-2004", "CONFIRMED", 100, "secret@example.com");
        OrderView v = serviceA.get("O-2004", ALICE);
        assertNull(v.customerEmail(), "customer_email escaped into the domain view");
    }

    // ---- TX-003 -----------------------------------------------------------

    @Test
    @DisplayName("TX-003: confirm writes the order and its idempotency record atomically")
    void tx003_confirmIsAtomic() throws Exception {
        seedOrder(ALICE, "O-3001", "DRAFT", 500, "alice@example.com");
        serviceA.confirm("O-3001", "idem-key-3001", ALICE);
        assertEquals("CONFIRMED", readOrder(ALICE, "O-3001").orElseThrow().getText("status"));
        assertTrue(readIdempotency(ALICE, "idem-key-3001").isPresent(),
                "the idempotency record did not land with the business write");
    }

    @Test
    @DisplayName("TX-003: replay with the same key does not re-run the operation")
    void tx003_replay() throws Exception {
        seedOrder(ALICE, "O-3002", "DRAFT", 500, "alice@example.com");
        serviceA.confirm("O-3002", "idem-key-3002", ALICE);
        OrderView replay = serviceA.confirm("O-3002", "idem-key-3002", ALICE);
        assertEquals("CONFIRMED", replay.status());
    }

    /**
     * The defect the independent review found: the replay branch returns before the ownership
     * predicate runs, and the record is keyed on (tenant_id, key) only. This test asserts the
     * FIXED behaviour, so it fails against the implementation as written.
     */
    @Test
    @DisplayName("TX-003: a same-tenant caller holding another customer's key is refused")
    void tx003_replayPathEnforcesOwnership() throws Exception {
        seedOrder(ALICE, "O-3003", "DRAFT", 500, "alice@example.com");
        serviceA.confirm("O-3003", "idem-key-3003", ALICE);
        assertThrows(OrderNotFoundException.class,
                () -> serviceA.confirm("O-3003", "idem-key-3003", BOB),
                "the replay path returned another customer's order outcome");
    }

    // ---- Non-conforming: the seeded-wrong implementation -----------------------

    /**
     * Static review of Variant B reported a missing ownership check and split transactions, and was
     * right about both. Runtime reports something neither the review nor the contract suite saw:
     * the write cannot commit at all. Its Put never reads the record first, so Consensus Commit
     * treats it as an insert and rejects it on an existing order — a CONFLICT error that no retry
     * can clear (rules/scalardb-crud-patterns.md). The authorization defect is real in the code and
     * unreachable at runtime, because a different defect fails first.
     */
    @Test
    @DisplayName("Non-conforming: confirm cannot commit — its blind Put is treated as an insert")
    void variantB_confirmBlindPutCannotCommit() throws Exception {
        seedOrder(ALICE, "O-4001", "DRAFT", 500, "alice@example.com");
        CommitConflictException e = assertThrows(CommitConflictException.class,
                () -> serviceB.confirm("O-4001", "idem-key-4001", ALICE));
        assertTrue(e.getMessage().contains("already exists"), e.getMessage());
        assertEquals("DRAFT", readOrder(ALICE, "O-4001").orElseThrow().getText("status"),
                "the order should be untouched");
    }

    @Test
    @DisplayName("Non-conforming: cancel cannot commit either — same blind-Put cause")
    void variantB_cancelBlindPutCannotCommit() throws Exception {
        seedOrder(ALICE, "O-4002", "CONFIRMED", 500, "alice@example.com");
        assertThrows(CommitConflictException.class,
                () -> serviceB.cancel("O-4002", "idem-key-4002", BOB));
        assertEquals("CONFIRMED", readOrder(ALICE, "O-4002").orElseThrow().getText("status"),
                "Alice's order should be untouched");
    }

    @Test
    @DisplayName("Non-conforming: the confidential customer_email is carried into the domain view")
    void variantB_leaksConfidentialField() throws Exception {
        seedOrder(ALICE, "O-4003", "CONFIRMED", 100, "secret@example.com");
        OrderView v = serviceB.get("O-4003", ALICE);
        assertNotEquals(null, v.customerEmail(), "expected the defect to be live");
        assertEquals("secret@example.com", v.customerEmail());
    }
}
