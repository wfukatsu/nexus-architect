package com.example.orders;

import static com.example.orders.OrderSchema.IDEMPOTENCY;
import static com.example.orders.OrderSchema.INVENTORY;
import static com.example.orders.OrderSchema.NS;
import static com.example.orders.OrderSchema.ORDERS;
import static com.example.orders.OrderSchema.SAGA_LOG;

import com.scalar.db.api.DistributedTransactionAdmin;
import com.scalar.db.api.DistributedTransactionManager;
import com.scalar.db.api.GlobalTransactionManager;
import com.scalar.db.api.TableMetadata;
import com.scalar.db.api.TwoPhaseCommitCoordinator;
import com.scalar.db.api.TwoPhaseCommitParticipant;
import com.scalar.db.common.ActiveTransactionManagedDistributedTransactionManager;
import com.scalar.db.common.DistributedTransactionBackedGlobalTransactionManager;
import com.scalar.db.common.TwoPhaseCommitBackedGlobalTransactionManager;
import com.scalar.db.io.DataType;
import com.scalar.db.service.TransactionFactory;
import com.scalar.db.service.TwoPhaseCommitFactory;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Properties;

/** A real ScalarDB instance over SQLite — in-process, no container. */
final class ScalarDbTestBackend implements AutoCloseable {

    /**
     * The two processes of a microservice transaction, each holding the {@link GlobalTransactionManager}
     * its own service would hold. The test code that drives them is the same for both topologies below;
     * only how the managers are wired differs — which is the claim the Microservice Transaction API makes.
     */
    record MicroserviceTopology(String name, GlobalTransactionManager orchestrator,
                                GlobalTransactionManager participant, AutoCloseable resources) {
        @Override public String toString() { return name; }
    }

    private final Path dir;
    private final Properties props;
    private final TransactionFactory factory;
    private final DistributedTransactionAdmin admin;
    private final DistributedTransactionManager manager;

    ScalarDbTestBackend() throws Exception {
        dir = Files.createTempDirectory("scalardb-it");
        props = new Properties();
        props.setProperty("scalar.db.storage", "jdbc");
        props.setProperty("scalar.db.contact_points", "jdbc:sqlite:" + dir.resolve("it.db") + "?busy_timeout=10000");
        props.setProperty("scalar.db.username", "");
        props.setProperty("scalar.db.password", "");
        factory = TransactionFactory.create(props);
        admin = factory.getTransactionAdmin();
        manager = factory.getTransactionManager();

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
        admin.createTable(NS, INVENTORY, TableMetadata.newBuilder()
                .addColumn("tenant_id", DataType.TEXT)
                .addColumn("product_id", DataType.TEXT)
                .addColumn("available", DataType.INT)
                .addColumn("reserved", DataType.INT)
                .addPartitionKey("tenant_id")
                .addClusteringKey("product_id")
                .build(), true, new HashMap<>());
        admin.createTable(NS, SAGA_LOG, TableMetadata.newBuilder()
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

    /** The {@code TransactionFactory} of the production wiring, for probing what Core itself provides. */
    TransactionFactory factory() {
        return factory;
    }

    /**
     * Shared-cluster shape: every service talks to one ScalarDB instance, so one single-phase manager backs
     * the whole global transaction and both services hold a handle onto it. This is the backing a
     * ScalarDB Cluster node uses for the Microservice Transaction API when the Transaction Coordinator
     * is disabled; Core's {@code TransactionFactory} does not wire it itself (see
     * {@link MicroserviceTransactionCoreProbeIT}), so the test wires the same public classes the
     * engine's own integration suite uses.
     */
    MicroserviceTopology sharedCluster() {
        DistributedTransactionManager underlying = TransactionFactory.create(props).getTransactionManager();
        // -1 / -1: no idle expiration and no cap on in-progress transactions, so the test controls lifetimes.
        GlobalTransactionManager shared = new DistributedTransactionBackedGlobalTransactionManager(
                new ActiveTransactionManagedDistributedTransactionManager(underlying, -1, -1));
        return new MicroserviceTopology("shared cluster (single-phase backing)", shared, shared, shared::close);
    }

    /**
     * Separated-cluster shape: each service has its own participant (its own ScalarDB instance in
     * production) and one coordinator drives two-phase commit across them underneath the one-phase
     * application code. Two factories, two participant IDs, one coordinator.
     */
    MicroserviceTopology separatedClusters() {
        TwoPhaseCommitFactory orderSide = TwoPhaseCommitFactory.create(withParticipant("order-service"));
        TwoPhaseCommitFactory inventorySide = TwoPhaseCommitFactory.create(withParticipant("inventory-service"));
        TwoPhaseCommitCoordinator coordinator = orderSide.getTwoPhaseCommitCoordinator();
        TwoPhaseCommitParticipant orderParticipant = orderSide.getTwoPhaseCommitParticipant();
        TwoPhaseCommitParticipant inventoryParticipant = inventorySide.getTwoPhaseCommitParticipant();
        GlobalTransactionManager orchestrator =
                new TwoPhaseCommitBackedGlobalTransactionManager(coordinator, orderParticipant);
        GlobalTransactionManager participant =
                new TwoPhaseCommitBackedGlobalTransactionManager(coordinator, inventoryParticipant);
        return new MicroserviceTopology("separated clusters (two-phase backing)", orchestrator, participant, () -> {
            orchestrator.close();
            participant.close();
        });
    }

    private Properties withParticipant(String participantId) {
        Properties p = new Properties();
        p.putAll(props);
        p.setProperty("scalar.db.consensus_commit.participant_id", participantId);
        return p;
    }

    @Override
    public void close() throws Exception {
        manager.close();
        admin.close();
    }
}
