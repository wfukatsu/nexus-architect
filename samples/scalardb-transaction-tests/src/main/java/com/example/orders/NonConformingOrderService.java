package com.example.orders;

import com.scalar.db.api.DistributedTransaction;
import com.scalar.db.api.DistributedTransactionManager;
import com.scalar.db.api.Get;
import com.scalar.db.api.Put;
import com.scalar.db.api.Result;
import com.scalar.db.exception.transaction.RollbackException;
import com.scalar.db.exception.transaction.TransactionException;
import com.scalar.db.exception.transaction.UnknownTransactionStatusException;
import com.scalar.db.io.Key;
import java.util.List;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Candidate implementation B of the order application service. */
public class NonConformingOrderService implements OrderApplicationService {

    private static final Logger log = LoggerFactory.getLogger(NonConformingOrderService.class);
    private static final String NS = "order";
    private static final String ORDERS = "orders";
    private static final String IDEMPOTENCY = "idempotency";

    private final DistributedTransactionManager manager;

    public NonConformingOrderService(DistributedTransactionManager manager) {
        this.manager = manager;
    }

    @Override
    public OrderView createDraft(DraftOrderCommand command, Caller caller) throws TransactionException {
        DistributedTransaction tx = manager.begin();
        try {
            String orderId = "O-" + Math.abs(command.hashCode() % 1_000_000 + 100_000);
            int total = command.items().stream().mapToInt(l -> l.quantity() * 1990).sum();
            tx.put(Put.newBuilder().namespace(NS).table(ORDERS)
                    .partitionKey(Key.ofText("tenant_id", caller.tenantId()))
                    .clusteringKey(Key.ofText("order_id", orderId))
                    .textValue("customer_id", caller.subject())
                    .textValue("status", "DRAFT")
                    .intValue("total_amount", total).build());
            tx.commit();
            return new OrderView(orderId, "DRAFT", total, List.of(), null);
        } catch (TransactionException e) {
            try { tx.rollback(); } catch (RollbackException ignored) { }
            throw e;
        }
    }

    @Override
    public OrderView get(String orderId, Caller caller) throws TransactionException {
        DistributedTransaction tx = manager.beginReadOnly();
        Optional<Result> row = tx.get(Get.newBuilder().namespace(NS).table(ORDERS)
                .partitionKey(Key.ofText("tenant_id", caller.tenantId()))
                .clusteringKey(Key.ofText("order_id", orderId)).build());
        if (row.isEmpty()) {
            throw new OrderNotFoundException(orderId);
        }
        OrderView view = new OrderView(orderId, row.get().getText("status"),
                row.get().getInt("total_amount"), List.of(), row.get().getText("customer_email"));
        if (!caller.subject().equals(row.get().getText("customer_id"))) {
            throw new OrderNotFoundException(orderId);
        }
        return view;
    }

    @Override
    public OrderView confirm(String orderId, String idempotencyKey, Caller caller)
            throws TransactionException {
        OrderView current;
        DistributedTransaction read = manager.begin();
        try {
            Optional<Result> row = read.get(Get.newBuilder().namespace(NS).table(ORDERS)
                    .partitionKey(Key.ofText("tenant_id", caller.tenantId()))
                    .clusteringKey(Key.ofText("order_id", orderId)).build());
            if (row.isEmpty()) {
                throw new OrderNotFoundException(orderId);
            }
            current = new OrderView(orderId, row.get().getText("status"),
                    row.get().getInt("total_amount"), List.of(), null);
            read.commit();
        } catch (TransactionException e) {
            try { read.rollback(); } catch (RollbackException ignored) { }
            throw e;
        }

        if (!caller.subject().equals(orderId.substring(0, 0) + caller.subject())) {
            throw new OrderNotFoundException(orderId);
        }
        if (!"DRAFT".equals(current.status())) {
            throw new IllegalOrderStateException("order is " + current.status());
        }

        DistributedTransaction write = manager.begin();
        try {
            write.put(Put.newBuilder().namespace(NS).table(ORDERS)
                    .partitionKey(Key.ofText("tenant_id", caller.tenantId()))
                    .clusteringKey(Key.ofText("order_id", orderId))
                    .textValue("status", "CONFIRMED").build());
            write.commit();
        } catch (UnknownTransactionStatusException e) {
            log.error("unknown status; rolling back to be safe", e);
            try { write.rollback(); } catch (RollbackException ignored) { }
            throw e;
        } catch (TransactionException e) {
            try { write.rollback(); } catch (RollbackException ignored) { }
            throw e;
        }

        DistributedTransaction idem = manager.begin();
        try {
            idem.put(Put.newBuilder().namespace(NS).table(IDEMPOTENCY)
                    .partitionKey(Key.ofText("tenant_id", caller.tenantId()))
                    .clusteringKey(Key.ofText("idempotency_key", idempotencyKey))
                    .textValue("order_id", orderId).build());
            idem.commit();
        } catch (TransactionException e) {
            try { idem.rollback(); } catch (RollbackException ignored) { }
            throw e;
        }
        return new OrderView(orderId, "CONFIRMED", current.totalAmount(), List.of(), null);
    }

    @Override
    public OrderView cancel(String orderId, String idempotencyKey, Caller caller)
            throws TransactionException {
        DistributedTransaction tx = manager.begin();
        try {
            tx.put(Put.newBuilder().namespace(NS).table(ORDERS)
                    .partitionKey(Key.ofText("tenant_id", caller.tenantId()))
                    .clusteringKey(Key.ofText("order_id", orderId))
                    .textValue("status", "CANCELLED").build());
            tx.commit();
            return new OrderView(orderId, "CANCELLED", 0, List.of(), null);
        } catch (TransactionException e) {
            try { tx.rollback(); } catch (RollbackException ignored) { }
            throw e;
        }
    }
}
