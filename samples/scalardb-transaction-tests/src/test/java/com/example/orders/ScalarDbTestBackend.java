package com.example.orders;

import com.scalar.db.api.DistributedTransactionAdmin;
import com.scalar.db.api.DistributedTransactionManager;
import com.scalar.db.api.TableMetadata;
import com.scalar.db.api.TwoPhaseCommitTransactionManager;
import com.scalar.db.io.DataType;
import com.scalar.db.service.TransactionFactory;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Properties;

/** A real ScalarDB instance over SQLite — in-process, no container. */
final class ScalarDbTestBackend implements AutoCloseable {

    static final String NS = "order";
    static final String ORDERS = "orders";
    static final String IDEMPOTENCY = "idempotency";
    static final String INVENTORY = "inventory";
    static final String SAGA_LOG = "saga_log";

    private final Path dir;
    private final TransactionFactory factory;
    private final DistributedTransactionAdmin admin;
    private final DistributedTransactionManager manager;
    private final TwoPhaseCommitTransactionManager twoPc;
    /** A SECOND manager over the same database: join() on one manager returns the same
     *  transaction, so two 2PC participants need two managers — one per service in production. */
    private final TwoPhaseCommitTransactionManager twoPcParticipant;
    private final TransactionFactory participantFactory;

    ScalarDbTestBackend() throws Exception {
        dir = Files.createTempDirectory("scalardb-it");
        Properties props = new Properties();
        props.setProperty("scalar.db.storage", "jdbc");
        props.setProperty("scalar.db.contact_points", "jdbc:sqlite:" + dir.resolve("it.db") + "?busy_timeout=10000");
        props.setProperty("scalar.db.username", "");
        props.setProperty("scalar.db.password", "");
        factory = TransactionFactory.create(props);
        admin = factory.getTransactionAdmin();
        manager = factory.getTransactionManager();
        twoPc = factory.getTwoPhaseCommitTransactionManager();
        participantFactory = TransactionFactory.create(props);
        twoPcParticipant = participantFactory.getTwoPhaseCommitTransactionManager();

        admin.createCoordinatorTables(true);
        admin.createNamespace(NS, true);
        admin.createTable(NS, ORDERS, TableMetadata.newBuilder()
                .addColumn("tenant_id", DataType.TEXT)
                .addColumn("order_id", DataType.TEXT)
                .addColumn("customer_id", DataType.TEXT)
                .addColumn("customer_email", DataType.TEXT)
                .addColumn("status", DataType.TEXT)
                .addColumn("total_amount", DataType.INT)
                .addPartitionKey("tenant_id")
                .addClusteringKey("order_id")
                .build(), true, new HashMap<>());
        admin.createTable(NS, "inventory", TableMetadata.newBuilder()
                .addColumn("tenant_id", DataType.TEXT)
                .addColumn("product_id", DataType.TEXT)
                .addColumn("available", DataType.INT)
                .addColumn("reserved", DataType.INT)
                .addPartitionKey("tenant_id")
                .addClusteringKey("product_id")
                .build(), true, new HashMap<>());
        admin.createTable(NS, "saga_log", TableMetadata.newBuilder()
                .addColumn("tenant_id", DataType.TEXT)
                .addColumn("saga_id", DataType.TEXT)
                .addColumn("step", DataType.TEXT)
                .addColumn("state", DataType.TEXT)
                .addPartitionKey("tenant_id")
                .addClusteringKey("saga_id")
                .addClusteringKey("step")
                .build(), true, new HashMap<>());
        admin.createTable(NS, IDEMPOTENCY, TableMetadata.newBuilder()
                .addColumn("tenant_id", DataType.TEXT)
                .addColumn("idempotency_key", DataType.TEXT)
                .addColumn("order_id", DataType.TEXT)
                .addColumn("customer_id", DataType.TEXT)
                .addColumn("result_status", DataType.TEXT)
                .addColumn("result_total", DataType.INT)
                .addPartitionKey("tenant_id")
                .addClusteringKey("idempotency_key")
                .build(), true, new HashMap<>());
    }

    DistributedTransactionManager manager() {
        return manager;
    }

    TwoPhaseCommitTransactionManager twoPhaseCommit() {
        return twoPc;
    }

    TwoPhaseCommitTransactionManager twoPhaseCommitParticipant() {
        return twoPcParticipant;
    }

    @Override
    public void close() throws Exception {
        manager.close();
        twoPc.close();
        twoPcParticipant.close();
        admin.close();
    }
}
