package com.example.orders;

import com.scalar.db.api.DistributedTransaction;
import com.scalar.db.api.DistributedTransactionManager;
import com.scalar.db.api.Get;
import com.scalar.db.api.Put;
import com.scalar.db.api.Result;
import com.scalar.db.exception.transaction.CommitConflictException;
import com.scalar.db.exception.transaction.CrudConflictException;
import com.scalar.db.exception.transaction.RollbackException;
import com.scalar.db.exception.transaction.TransactionException;
import com.scalar.db.exception.transaction.UnknownTransactionStatusException;
import com.scalar.db.io.Key;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Implements TX-001..TX-004 of reports/03_design/scalardb-transaction.md.
 *
 * Invariants this class exists to hold, each traceable to the design:
 *  - Exactly ONE transaction per operation.
 *  - The ownership predicate is evaluated INSIDE the transaction that read the order.
 *  - The idempotency record and the business write land in the SAME transaction.
 *  - Conflict exceptions are retried here, so the API layer never sees one that a retry
 *    would have cleared.
 *  - UnknownTransactionStatusException is never rolled back and never retried.
 */
public class ConformingOrderService implements OrderApplicationService {

    private static final Logger log = LoggerFactory.getLogger(ConformingOrderService.class);

    private static final String NS = "order";
    private static final String ORDERS = "orders";
    private static final String IDEMPOTENCY = "idempotency";
    private static final int MAX_RETRIES = 3;

    private final DistributedTransactionManager manager;

    public ConformingOrderService(DistributedTransactionManager manager) {
        this.manager = manager;
    }

    // ---- TX-001 ------------------------------------------------------------

    @Override
    public OrderView createDraft(DraftOrderCommand command, Caller caller) throws TransactionException {
        return inOneTransaction(tx -> {
            String orderId = "O-" + Math.abs(command.hashCode() % 1_000_000 + 100_000);
            tx.put(orderPut(caller, orderId, "DRAFT", total(command)));
            return new OrderView(orderId, "DRAFT", total(command), lines(command), null);
        });
    }

    // ---- TX-002 (read-only, still commits) ---------------------------------

    @Override
    public OrderView get(String orderId, Caller caller) throws TransactionException {
        DistributedTransaction tx = manager.beginReadOnly();
        try {
            OrderView view = readOwnedOrder(tx, orderId, caller);
            tx.commit();   // a read-only transaction must still commit
            return view;
        } catch (UnknownTransactionStatusException e) {
            throw e;       // never roll back — the outcome is indeterminate
        } catch (Exception e) {
            rollbackQuietly(tx);
            throw e;
        }
    }

    // ---- TX-003 ------------------------------------------------------------

    @Override
    public OrderView confirm(String orderId, String idempotencyKey, Caller caller)
            throws TransactionException {
        return inOneTransaction(tx -> {
            // Ownership first: the replay branch is an authorization path too, and returning
            // early on a stored record would make it the one path with no check on it.
            OrderView current = readOwnedOrder(tx, orderId, caller);
            Optional<OrderView> replay = replayIfRecorded(tx, caller, idempotencyKey, orderId);
            if (replay.isPresent()) {
                return replay.get();
            }
            if (!"DRAFT".equals(current.status())) {
                throw new IllegalOrderStateException("order is " + current.status() + ", not DRAFT");
            }
            tx.put(orderPut(caller, orderId, "CONFIRMED", current.totalAmount()));
            // Same transaction as the business write — a separately committed record
            // reintroduces the duplicate the key exists to prevent.
            tx.put(idempotencyPut(caller, idempotencyKey, orderId));
            return new OrderView(orderId, "CONFIRMED", current.totalAmount(), current.items(), null);
        });
    }

    // ---- TX-004 ------------------------------------------------------------

    @Override
    public OrderView cancel(String orderId, String idempotencyKey, Caller caller)
            throws TransactionException {
        return inOneTransaction(tx -> {
            OrderView current = readOwnedOrder(tx, orderId, caller);
            Optional<OrderView> replay = replayIfRecorded(tx, caller, idempotencyKey, orderId);
            if (replay.isPresent()) {
                return replay.get();
            }
            if (!"CONFIRMED".equals(current.status())) {
                throw new IllegalOrderStateException("order is " + current.status() + ", not CONFIRMED");
            }
            tx.put(orderPut(caller, orderId, "CANCELLED", current.totalAmount()));
            tx.put(idempotencyPut(caller, idempotencyKey, orderId));
            return new OrderView(orderId, "CANCELLED", current.totalAmount(), current.items(), null);
        });
    }

    // ---- transaction plumbing ---------------------------------------------

    @FunctionalInterface
    private interface TxBody {
        OrderView run(DistributedTransaction tx) throws TransactionException;
    }

    /**
     * One transaction, retried as a whole on conflict. Catch order is specific-before-parent:
     * the conflict types must precede TransactionException or their branch is unreachable.
     */
    private OrderView inOneTransaction(TxBody body) throws TransactionException {
        TransactionException last = null;
        for (int attempt = 0; attempt < MAX_RETRIES; attempt++) {
            DistributedTransaction tx = manager.begin();
            try {
                OrderView result = body.run(tx);
                tx.commit();
                return result;
            } catch (CrudConflictException | CommitConflictException e) {
                rollbackQuietly(tx);
                last = e;
                backoff(attempt);
            } catch (UnknownTransactionStatusException e) {
                // The commit may have succeeded. Do not roll back. Do not retry.
                log.error("transaction status unknown; not rolling back. txId={}",
                        e.getUnknownTransactionId().orElse("unknown"), e);
                throw e;
            } catch (TransactionException e) {
                rollbackQuietly(tx);
                throw e;
            } catch (RuntimeException e) {
                rollbackQuietly(tx);
                throw e;
            }
        }
        throw last;   // retries exhausted — the API layer renders this as 409
    }

    private static void backoff(int attempt) {
        try {
            Thread.sleep(50L << attempt);
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
        }
    }

    private static void rollbackQuietly(DistributedTransaction tx) {
        try {
            tx.rollback();
        } catch (RollbackException ignored) {
            log.warn("rollback failed", ignored);
        }
    }

    // ---- data access -------------------------------------------------------

    /** Ownership is evaluated here, inside the transaction that read the row. */
    private OrderView readOwnedOrder(DistributedTransaction tx, String orderId, Caller caller)
            throws TransactionException {
        Get get = Get.newBuilder().namespace(NS).table(ORDERS)
                .partitionKey(Key.ofText("tenant_id", caller.tenantId()))
                .clusteringKey(Key.ofText("order_id", orderId))
                .build();
        Optional<Result> row = tx.get(get);
        if (row.isEmpty()) {
            throw new OrderNotFoundException(orderId);
        }
        String customerId = row.get().getText("customer_id");
        if (!caller.subject().equals(customerId)) {
            // Existence is confidential: not-owned is indistinguishable from not-found.
            throw new OrderNotFoundException(orderId);
        }
        return new OrderView(orderId, row.get().getText("status"),
                row.get().getInt("total_amount"), List.of(), null);
    }

    private Optional<OrderView> replayIfRecorded(DistributedTransaction tx, Caller caller,
            String idempotencyKey, String orderId) throws TransactionException {
        Get get = Get.newBuilder().namespace(NS).table(IDEMPOTENCY)
                .partitionKey(Key.ofText("tenant_id", caller.tenantId()))
                .clusteringKey(Key.ofText("idempotency_key", idempotencyKey))
                .build();
        Optional<Result> row = tx.get(get);
        if (row.isEmpty()) {
            return Optional.empty();
        }
        if (!caller.subject().equals(row.get().getText("customer_id"))) {
            // A record keyed only on (tenant_id, key) is readable by every caller in the tenant.
            throw new OrderNotFoundException(orderId);
        }
        String recordedOrderId = row.get().getText("order_id");
        if (!orderId.equals(recordedOrderId)) {
            throw new IdempotencyKeyReuseException("key already used for order " + recordedOrderId);
        }
        return Optional.of(new OrderView(orderId, row.get().getText("result_status"),
                row.get().getInt("result_total"), List.of(), null));
    }

    private Put orderPut(Caller caller, String orderId, String status, int totalAmount) {
        return Put.newBuilder().namespace(NS).table(ORDERS)
                .partitionKey(Key.ofText("tenant_id", caller.tenantId()))
                .clusteringKey(Key.ofText("order_id", orderId))
                .textValue("customer_id", caller.subject())
                .textValue("status", status)
                .intValue("total_amount", totalAmount)
                .build();
    }

    private Put idempotencyPut(Caller caller, String idempotencyKey, String orderId) {
        return Put.newBuilder().namespace(NS).table(IDEMPOTENCY)
                .partitionKey(Key.ofText("tenant_id", caller.tenantId()))
                .clusteringKey(Key.ofText("idempotency_key", idempotencyKey))
                .textValue("order_id", orderId)
                .textValue("customer_id", caller.subject())
                .textValue("result_status", "CONFIRMED")
                .intValue("result_total", 0)
                .build();
    }

    private static int total(DraftOrderCommand c) {
        return c.items().stream().mapToInt(l -> l.quantity() * 1990).sum();
    }

    private static List<OrderView.Line> lines(DraftOrderCommand c) {
        List<OrderView.Line> out = new ArrayList<>();
        c.items().forEach(l -> out.add(new OrderView.Line(l.productId(), l.quantity())));
        return out;
    }
}
