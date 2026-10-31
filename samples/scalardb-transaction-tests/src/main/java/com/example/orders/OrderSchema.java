package com.example.orders;

/**
 * The namespace and tables of the transaction design (reports/03_design/scalardb-transaction.md).
 * The services name them, the test backend creates them, and the tests read and seed them — from
 * this one place.
 */
public final class OrderSchema {

    public static final String NS = "order";
    public static final String ORDERS = "orders";
    public static final String IDEMPOTENCY = "idempotency";
    public static final String INVENTORY = "inventory";
    public static final String SAGA_LOG = "saga_log";

    private OrderSchema() {
    }
}
