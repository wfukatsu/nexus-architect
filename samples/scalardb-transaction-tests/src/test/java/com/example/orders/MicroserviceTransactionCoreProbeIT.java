package com.example.orders;

import static org.junit.jupiter.api.Assertions.assertAll;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.scalar.db.api.DistributedTransactionManager;
import java.lang.reflect.Method;
import java.util.Arrays;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * What the ScalarDB <em>Core</em> library (Community edition) does and does not ship for cross-service
 * transactions at the pinned version. These are the facts behind the edition and version statements in
 * {@code rules/scalardb-2pc-patterns.md} and {@code rules/scalardb-edition-profiles.md}; when a bump
 * changes one of them, a test here fails and the rule is corrected instead of going stale.
 */
class MicroserviceTransactionCoreProbeIT {

    private static ScalarDbTestBackend backend;

    @BeforeAll static void boot() throws Exception { backend = new ScalarDbTestBackend(); }

    @AfterAll static void down() throws Exception { if (backend != null) backend.close(); }

    @Test
    @DisplayName("Core's TransactionFactory does not wire a GlobalTransactionManager — the production wiring is ScalarDB Cluster")
    void coreDoesNotProvideTheGlobalTransactionManager() {
        // The API's classes are in the Core jar (MicroserviceTransactionIT wires them by hand, as the
        // engine's own integration suite does), but Consensus Commit's provider refuses to create the
        // manager: an application on Core cannot obtain it, and a design that assumes the Microservice
        // Transaction API on the Community edition does not run.
        assertThrows(UnsupportedOperationException.class, () -> backend.factory().getGlobalTransactionManager());
    }

    @Test
    @DisplayName("3.20 removed join()/resume() from DistributedTransactionManager")
    void joinAndResumeAreGone() {
        assertAll(
                () -> assertTrue(Arrays.stream(DistributedTransactionManager.class.getMethods())
                        .map(Method::getName).noneMatch("join"::equals), "join(String) still present"),
                () -> assertTrue(Arrays.stream(DistributedTransactionManager.class.getMethods())
                        .map(Method::getName).noneMatch("resume"::equals), "resume(String) still present"));
    }

    @Test
    @DisplayName("3.20 removed the application-driven two-phase commit interface from the Core library")
    void twoPhaseCommitTransactionManagerIsGone() {
        // Deprecated as of 3.19 per the documentation; absent from the 3.20.0 Core jar. A design that still
        // names it on 3.20 does not compile — the earlier TwoPhaseCommitIT of this suite went with it.
        assertThrows(ClassNotFoundException.class,
                () -> Class.forName("com.scalar.db.api.TwoPhaseCommitTransactionManager"));
        assertThrows(ClassNotFoundException.class,
                () -> Class.forName("com.scalar.db.api.TwoPhaseCommitTransaction"));
    }
}
