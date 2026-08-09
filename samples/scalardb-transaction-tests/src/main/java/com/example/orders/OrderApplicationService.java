package com.example.orders;

import com.scalar.db.exception.transaction.TransactionException;

/**
 * The transaction boundary. Each method opens exactly one ScalarDB transaction, per
 * reports/03_design/scalardb-transaction.md (TX-001..TX-004). The ownership predicate is
 * evaluated INSIDE the transaction that reads the order.
 */
public interface OrderApplicationService {

    /** TX-001 */
    OrderView createDraft(DraftOrderCommand command, Caller caller) throws TransactionException;

    /** TX-002 — read-only, still commits */
    OrderView get(String orderId, Caller caller) throws TransactionException;

    /** TX-003 — idempotency record written inside this transaction */
    OrderView confirm(String orderId, String idempotencyKey, Caller caller) throws TransactionException;

    /** TX-004 — idempotency record written inside this transaction */
    OrderView cancel(String orderId, String idempotencyKey, Caller caller) throws TransactionException;

}
