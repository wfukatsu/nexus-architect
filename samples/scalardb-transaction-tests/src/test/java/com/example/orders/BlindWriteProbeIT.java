package com.example.orders;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.scalar.db.api.DistributedTransaction;
import com.scalar.db.api.DistributedTransactionManager;
import com.scalar.db.api.Get;
import com.scalar.db.api.Put;
import com.scalar.db.exception.transaction.CommitConflictException;
import com.scalar.db.io.Key;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/** Establishes, against a real instance, what Consensus Commit does with a Put that has no Get. */
class BlindWriteProbeIT {

    private static ScalarDbTestBackend backend;
    private static DistributedTransactionManager manager;

    @BeforeAll static void boot() throws Exception {
        backend = new ScalarDbTestBackend();
        manager = backend.manager();
    }

    @AfterAll static void down() throws Exception { if (backend != null) backend.close(); }

    private static Put put(String id, String status) {
        return Put.newBuilder().namespace(ScalarDbTestBackend.NS).table(ScalarDbTestBackend.ORDERS)
                .partitionKey(Key.ofText("tenant_id", "t"))
                .clusteringKey(Key.ofText("order_id", id))
                .textValue("status", status).build();
    }

    private static Get get(String id) {
        return Get.newBuilder().namespace(ScalarDbTestBackend.NS).table(ScalarDbTestBackend.ORDERS)
                .partitionKey(Key.ofText("tenant_id", "t"))
                .clusteringKey(Key.ofText("order_id", id)).build();
    }

    @Test
    @DisplayName("Put with no preceding Get INSERTS — it succeeds only when the record is absent")
    void blindPutOnNewRecordSucceeds() throws Exception {
        DistributedTransaction tx = manager.begin();
        tx.put(put("B-1", "DRAFT"));
        assertDoesNotThrow(tx::commit);
    }

    @Test
    @DisplayName("Put with no preceding Get on an EXISTING record fails at commit")
    void blindPutOnExistingRecordFails() throws Exception {
        DistributedTransaction seed = manager.begin();
        seed.put(put("B-2", "DRAFT"));
        seed.commit();

        DistributedTransaction tx = manager.begin();
        tx.put(put("B-2", "CONFIRMED"));
        assertThrows(CommitConflictException.class, tx::commit);
    }

    @Test
    @DisplayName("Get then Put on the same record in one transaction updates it")
    void readThenWriteSucceeds() throws Exception {
        DistributedTransaction seed = manager.begin();
        seed.put(put("B-3", "DRAFT"));
        seed.commit();

        DistributedTransaction tx = manager.begin();
        tx.get(get("B-3"));
        tx.put(put("B-3", "CONFIRMED"));
        assertDoesNotThrow(tx::commit);
    }
}
