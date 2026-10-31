package com.example.orders;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.example.orders.ScalarDbTestBackend.MicroserviceTopology;
import com.scalar.db.api.BranchTransaction;
import com.scalar.db.api.DistributedTransaction;
import com.scalar.db.api.DistributedTransactionManager;
import com.scalar.db.api.Get;
import com.scalar.db.api.GlobalTransaction;
import com.scalar.db.api.Put;
import com.scalar.db.api.Result;
import com.scalar.db.exception.transaction.CommitConflictException;
import com.scalar.db.exception.transaction.CrudException;
import com.scalar.db.io.Key;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;

/**
 * The Microservice Transaction API (ScalarDB 3.19+, {@code GlobalTransactionManager} /
 * {@code GlobalTransaction} / {@code BranchTransaction}) across two services — order and inventory —
 * on a real engine, under both topologies the API serves: a shared cluster (single-phase backing) and
 * separated clusters (a coordinator driving two-phase commit underneath). Every test method runs once
 * per topology with the <em>same code</em>; only {@link ScalarDbTestBackend} wires the managers
 * differently. That is the claim of {@code rules/scalardb-2pc-patterns.md} § Microservice Transaction
 * API Pattern, and these are the behaviours the design's cross-service guarantees rest on.
 */
class MicroserviceTransactionIT {

    private static ScalarDbTestBackend backend;
    private static DistributedTransactionManager manager;
    private static List<MicroserviceTopology> topologies;
    private static final String TENANT = "tenant-1";
    private static final AtomicInteger seq = new AtomicInteger(7000);

    @BeforeAll static void boot() throws Exception {
        backend = new ScalarDbTestBackend();
        manager = backend.manager();
        topologies = List.of(backend.sharedCluster(), backend.separatedClusters());
    }

    @AfterAll static void down() throws Exception {
        for (MicroserviceTopology t : topologies) t.resources().close();
        if (backend != null) backend.close();
    }

    static List<MicroserviceTopology> topologies() {
        return topologies;
    }

    // ---- helpers ----------------------------------------------------------

    private static String next(String prefix) {
        return prefix + seq.incrementAndGet();
    }

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

    /** What the participant does on its side: reserve one unit, or refuse when nothing is left. */
    private static void reserveOne(BranchTransaction branch, String product) throws CrudException {
        Result stock = branch.get(stockGet(product)).orElseThrow();
        int available = stock.getInt("available");
        if (available < 1) {
            throw new IllegalStateException("out of stock: " + product);
        }
        branch.put(stockPut(product, available - 1, stock.getInt("reserved") + 1));
    }

    /** The orchestrator's cleanup, as the rule prescribes: end FAILURE (lenient), then roll back. */
    private static void fail(GlobalTransaction global, BranchTransaction own, Exception cause) throws Exception {
        try { own.end(BranchTransaction.Status.FAILURE); }
        catch (RuntimeException | CrudException suppressed) { cause.addSuppressed(suppressed); }
        global.rollback();
    }

    // ---- happy path -------------------------------------------------------

    @ParameterizedTest(name = "{0}")
    @MethodSource("topologies")
    @DisplayName("Both branches end SUCCESS, the orchestrator commits once, both services' writes persist")
    void happyPath(MicroserviceTopology t) throws Exception {
        String product = next("P-"), order = next("O-");
        seedStock(product, 10);

        // Orchestrating service: begins, runs its own branch, passes the ID on, commits.
        GlobalTransaction global = t.orchestrator().begin();
        BranchTransaction own = t.orchestrator().beginBranch(global.getId());
        own.put(orderPut(order, "CONFIRMED"));

        // Participant service: receives the ID, runs its branch, ends it, never commits.
        BranchTransaction theirs = t.participant().beginBranch(global.getId());
        reserveOne(theirs, product);
        theirs.end(BranchTransaction.Status.SUCCESS);

        own.end(BranchTransaction.Status.SUCCESS);
        global.commit();

        assertEquals("CONFIRMED", read(orderGet(order)).orElseThrow().getText("status"));
        assertEquals(9, read(stockGet(product)).orElseThrow().getInt("available"));
        assertEquals(1, read(stockGet(product)).orElseThrow().getInt("reserved"));
    }

    // ---- failure paths ----------------------------------------------------

    @ParameterizedTest(name = "{0}")
    @MethodSource("topologies")
    @DisplayName("A participant's failure reaches the orchestrator, which rolls back; no service's write survives")
    void participantFailureRollsBackEverything(MicroserviceTopology t) throws Exception {
        String product = next("P-"), order = next("O-");
        seedStock(product, 0);                      // nothing to reserve

        GlobalTransaction global = t.orchestrator().begin();
        BranchTransaction own = t.orchestrator().beginBranch(global.getId());
        own.put(orderPut(order, "CONFIRMED"));
        own.end(BranchTransaction.Status.SUCCESS);  // the orchestrator finished its part first

        BranchTransaction theirs = t.participant().beginBranch(global.getId());
        Exception failure = assertThrows(IllegalStateException.class, () -> {
            try {
                reserveOne(theirs, product);
                theirs.end(BranchTransaction.Status.SUCCESS);
            } catch (Exception e) {
                theirs.end(BranchTransaction.Status.FAILURE);   // lenient — safe in a catch clause
                throw e;
            }
        });
        fail(global, own, failure);                 // FAILURE after SUCCESS is a no-op; rollback discards all

        assertTrue(read(orderGet(order)).isEmpty(), "the order must not exist — its participant failed");
        assertEquals(0, read(stockGet(product)).orElseThrow().getInt("available"), "stock untouched");
    }

    @ParameterizedTest(name = "{0}")
    @MethodSource("topologies")
    @DisplayName("Ending a branch commits nothing: two SUCCESS ends followed by a rollback leave no trace")
    void endingABranchCommitsNothing(MicroserviceTopology t) throws Exception {
        String product = next("P-"), order = next("O-");
        seedStock(product, 10);

        GlobalTransaction global = t.orchestrator().begin();
        BranchTransaction own = t.orchestrator().beginBranch(global.getId());
        BranchTransaction theirs = t.participant().beginBranch(global.getId());
        own.put(orderPut(order, "CONFIRMED"));
        reserveOne(theirs, product);
        own.end(BranchTransaction.Status.SUCCESS);
        theirs.end(BranchTransaction.Status.SUCCESS);

        global.rollback();                          // the orchestrator decided against it after all

        assertTrue(read(orderGet(order)).isEmpty());
        assertEquals(10, read(stockGet(product)).orElseThrow().getInt("available"));
    }

    @ParameterizedTest(name = "{0}")
    @MethodSource("topologies")
    @DisplayName("Ending a branch twice with SUCCESS is unchecked protocol misuse; FAILURE afterwards is a no-op")
    void endTwiceIsUncheckedMisuse(MicroserviceTopology t) throws Exception {
        GlobalTransaction global = t.orchestrator().begin();
        BranchTransaction own = t.orchestrator().beginBranch(global.getId());
        own.put(orderPut(next("O-"), "DRAFT"));
        own.end(BranchTransaction.Status.SUCCESS);

        // An IllegalStateException, not a TransactionException — a handler that catches only
        // TransactionException never sees it (api-error-standard.md: 500 internal-error, not retryable).
        assertThrows(IllegalStateException.class, () -> own.end(BranchTransaction.Status.SUCCESS));
        assertDoesNotThrow(() -> own.end(BranchTransaction.Status.FAILURE), "FAILURE is lenient by design");
        assertThrows(IllegalStateException.class, () -> own.put(orderPut(next("O-"), "DRAFT")),
                "CRUD on an ended branch is refused");
        global.rollback();
    }

    @ParameterizedTest(name = "{0}")
    @MethodSource("topologies")
    @DisplayName("A write invalidated by a committed competitor fails at commit as a conflict; retry means the whole global transaction")
    void conflictSurfacesAtCommitAndNothingPersists(MicroserviceTopology t) throws Exception {
        String product = next("P-"), order = next("O-");
        seedStock(product, 10);

        GlobalTransaction global = t.orchestrator().begin();
        BranchTransaction own = t.orchestrator().beginBranch(global.getId());
        BranchTransaction theirs = t.participant().beginBranch(global.getId());
        own.put(orderPut(order, "CONFIRMED"));
        reserveOne(theirs, product);                // read 10, will write 9

        DistributedTransaction competitor = manager.begin();   // another request takes five units first
        competitor.get(stockGet(product));
        competitor.put(stockPut(product, 5, 5));
        competitor.commit();

        theirs.end(BranchTransaction.Status.SUCCESS);
        own.end(BranchTransaction.Status.SUCCESS);
        CommitConflictException conflict = assertThrows(CommitConflictException.class, global::commit,
                "the participant's read is stale — the commit must not apply a lost update");
        fail(global, own, conflict);                // rollback after a failed commit is a no-op, and harmless

        assertTrue(read(orderGet(order)).isEmpty(), "no order against a reservation that did not happen");
        assertEquals(5, read(stockGet(product)).orElseThrow().getInt("available"), "the competitor's value stands");
    }
}
