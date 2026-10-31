---
description: ScalarDB cross-service transaction rules — choosing between the shared-cluster one-phase interface, the Microservice Transaction API (Global Transaction API + Transaction Coordinator), the deprecated application-driven 2PC interface, and ScalarDB Saga; code patterns for each
globs:
  - "**/*.java"
---

# ScalarDB Cross-Service Transaction Rules

## Choose the Mechanism Before Writing 2PC Code

Hand-written two-phase commit is the most expensive of four options and, since ScalarDB 3.19,
**a deprecated interface**. The application interface for a transaction that spans services is
**one-phase in every supported topology**: the application begins, reads, writes and commits
exactly as for one database; when the services sit on separated ScalarDB Cluster instances, the
**Transaction Coordinator** node runs two-phase commit underneath, invisibly to the code. Decide in
this order:

| # | Mechanism | Use when | Application interface |
|---|-----------|----------|-----------------------|
| 1 | **Shared-cluster, one-phase commit** | Every service can talk to one ScalarDB Cluster instance. The documented recommendation "whenever possible": simplest deployment, no Coordinator, fewest resources | Ordinary one-phase code; one service calls `commit()`. On 3.19+ this is the **Microservice Transaction API** with `scalar.db.cluster.client.transaction_coordinator.enabled=false` — the same code as option 2 |
| 2 | **Microservice Transaction API on separated clusters** (3.19+, Cluster; the "Global Transaction API" of the 3.19 release notes) | Services need their own Cluster instances (resource isolation, per-team administration) | `GlobalTransactionManager` / `GlobalTransaction` / `BranchTransaction` — **one-phase application code**; the **Transaction Coordinator** node drives 2PC across the clusters underneath. "The code that begins a transaction, reads and writes records, and commits is the same in both patterns" — only configuration differs. CRUD interface on 3.19+; ScalarDB SQL gains the `GLOBAL_TRANSACTION` session mode (`BEGIN BRANCH` / `END BRANCH`) in 3.20 |
| 3 | **Application-driven 2PC interface** (`TwoPhaseCommitTransactionManager`) | Only where options 1–2 cannot apply: a release before 3.19, Core (Community) without Cluster, or Spring Data JDBC (which does not support the shared-cluster pattern) | **Deprecated as of ScalarDB 3.19** — the docs site states "The two-phase commit (2PC) interface is deprecated as of ScalarDB 3.19 and will be removed in a future release." Still shipped in 3.20, but 3.20 removes `join()` / `resume()` from `DistributedTransactionManager`, the SQL `JOIN` / `SUSPEND` / `RESUME` statements and GraphQL's `@twoPhaseCommit`, and deprecates the SQL `TWO_PHASE_COMMIT_TRANSACTION` mode. Choosing it is an **ADR-recorded deviation** (@rules/architecture-decision-records.md) with a migration path to option 1 or 2 |
| 4 | **ScalarDB Saga** (3.20 GA) | A single ACID transaction across the services is not possible or not wanted — long-running steps, external systems, eventual consistency acceptable | Saga/TCC definitions with compensations. See @rules/scalardb-saga-patterns.md |

Options 1–3 give strong consistency; option 4 trades it for compensation-based rollback and
eventual convergence. Record which option was chosen and why in the transaction design document.

**Two different things are called "one-phase commit".** Options 1–2 are one-phase at the
*application interface* — the Coordinator still runs 2PC across separated clusters. Consensus
Commit's `scalar.db.consensus_commit.one_phase_commit.enabled` is a *storage-level optimisation*
that skips the separate prepare-records and commit-state steps when all of a transaction's
mutations can be applied atomically in one storage operation (ScalarDB Saga's getting-started turns
it on). Do not describe the second as "no 2PC across clusters"; no upstream source claims that.

Grounding (bundle v1.3.0, `products/scalardb/3.20/`):
`scalardb-cluster/deployment-patterns-for-microservices.md` (both patterns on the Microservice
Transaction API; "currently supported only in the CRUD interface"), `scalardb-cluster/api-guide.md`
§ Microservice Transaction API, `scalardb-samples/microservice-transaction-sample-with-cluster/`
(shared and separated configurations, identical code), `releases/release-notes.md` (v3.19.0 for the
Transaction Coordinator; v3.20.0 for SQL `GLOBAL_TRANSACTION`, `join`/`resume` removal,
`BranchTransaction.end(Status)`), and `two-phase-commit-transactions.md`, whose 3.20 page opens
with the deprecation notice. A project pinned to **3.19** reads the 3.19 line, where the pattern
guide still shows the pre-3.19 choice and the 2PC page predates the notice — the lag described in
@rules/okf-knowledge-bundle.md §3. Confirm against the project's pinned release before designing on
option 2.

## Microservice Transaction API Pattern (Options 1 and 2)

A **global transaction** is made up of **branches**, one per process. One process begins it and
later commits or rolls it back; every other process begins a branch with the transaction ID it
received (for example in an RPC call) and ends that branch exactly once.

```java
// Orchestrating service (begins and commits). It needs its own branch to read or write.
GlobalTransactionManager manager = factory.getGlobalTransactionManager();
GlobalTransaction global = manager.begin();
String txId = global.getId();
BranchTransaction own = manager.beginBranch(txId);
try {
    own.insert(...);                                // CRUD like DistributedTransaction
    paymentClient.charge(txId, request);            // the participant runs its branch
    own.end(BranchTransaction.Status.SUCCESS);      // every branch ends exactly once
    global.commit();                                // only after every branch ended SUCCESS
} catch (Exception e) {
    try { own.end(BranchTransaction.Status.FAILURE); }   // no-op after SUCCESS; lenient otherwise
    catch (RuntimeException | CrudException suppressed) { e.addSuppressed(suppressed); }
    global.rollback();                              // discards all branch writes; no-op after a commit
    throw e;
}

// Participant service (runs a branch, never commits)
BranchTransaction branch = manager.beginBranch(request.getTransactionId());
try {
    branch.get(...); branch.update(...);
    branch.end(BranchTransaction.Status.SUCCESS);
} catch (Exception e) {
    try { branch.end(BranchTransaction.Status.FAILURE); }   // lenient — safe in a catch clause
    catch (RuntimeException | CrudException suppressed) { e.addSuppressed(suppressed); }
    throw e;                                        // reaches the orchestrator, which rolls back
}
```

A branch handle is not thread-safe — `end()` from a timeout handler on another thread while CRUD
is in flight is a data race the implementation does not guard against (javadoc, 3.20.0).

Rules the upstream guide states (3.20 docs site, Java API Guide):

- `end(SUCCESS)` throws `IllegalStateException` if the branch already ended or a `Scanner` is
  still open; `end(FAILURE)` is lenient. **Ending a branch commits nothing.**
- Commit only after **every** branch ended with `SUCCESS`. ScalarDB does not detect a commit after
  a `FAILURE`, and a commit while a branch is still working can include partial writes — the
  orchestrator must know every participant finished.
- Rollback discards all branch writes but **does not end the branches**; each process still ends
  its branch with `FAILURE`. If ending a branch fails during cleanup, log it and continue the
  rollback.
- A retry re-runs the **whole global transaction from the beginning in every process** (upstream
  examples: three attempts, 100 ms apart). `BranchTransaction.getGlobalTransactionId()` (3.20)
  returns the global ID; `getId()` is the branch's own.
- Exceptions: `TransactionException` / `TransactionNotFoundException` on begin and `beginBranch`;
  `CrudException` / `CrudConflictException` on CRUD and `end`; `UnsatisfiedConditionException` on
  conditional mutations; `CommitException` / `CommitConflictException` /
  `UnknownTransactionStatusException` on commit; `RollbackException` / `AbortException` on
  rollback. Map them per @rules/api-error-standard.md; `UnknownTransactionStatusException` keeps its
  own rule (@rules/scalardb-exception-handling.md).

Configuration — from `microservice-transaction-sample-with-cluster`; keys verified against the
3.20 Cluster configuration reference. The application code is identical; only these files change:

```properties
# Every service, shared-cluster pattern
scalar.db.transaction_manager=cluster
scalar.db.contact_points=indirect:scalardb-cluster-node
scalar.db.cluster.client.transaction_coordinator.enabled=false

# Every service, separated-cluster pattern (its own cluster + the Coordinator)
scalar.db.transaction_manager=cluster
scalar.db.contact_points=indirect:order-cluster
scalar.db.cluster.id=order-cluster                      # must equal the cluster's own scalar.db.cluster.id
scalar.db.cluster.client.transaction_coordinator.enabled=true
scalar.db.cluster.client.transaction_coordinator.contact_points=indirect:transaction-coordinator
scalar.db.cluster.client.transaction_coordinator.contact_port=60055   # Coordinator port, not 60053

# Each ScalarDB Cluster node in the separated pattern
scalar.db.cluster.node.transaction_participant.enabled=true
scalar.db.cluster.id=order-cluster

# The Transaction Coordinator node (not licensed; must itself run consensus-commit)
scalar.db.cluster.transaction_coordinator.clusters=customer-cluster,order-cluster
scalar.db.cluster.transaction_coordinator.clusters.customer-cluster.contact_points=indirect:customer-cluster
scalar.db.cluster.transaction_coordinator.clusters.order-cluster.contact_points=indirect:order-cluster
scalar.db.cluster.transaction_coordinator.standalone_mode.enabled=true   # single node; omit for membership
# plus its own scalar.db.storage / contact_points to the database holding the Coordinator table
```

The Coordinator table's database must be reachable from the Coordinator **and from every
cluster**: an instance that meets a record left by an unfinished transaction looks the state up
there to recover it. Request routing within a cluster is the Cluster SDK's job (gRPC connection,
or session affinity behind an L7 balancer, or `direct-kubernetes`).

Everything below applies to **option 3** — the deprecated interface — and is kept for existing
code and for the ADR-recorded cases above.

## Protocol Order

The 2PC protocol MUST follow this order:

```
Coordinator: begin() → CRUD → prepare() → validate() → commit()
Participant: join(txId) → CRUD → (wait) → prepare() → validate() → commit()
```

## One Manager Per Participant

`join(txId)` resolves the transaction **within the manager instance it is called on**. Calling it on
the same manager that began the transaction returns **that same transaction object**, not a second
participant — the next `prepare()` then fails with
`IllegalStateException: DB-CORE-10043: The transaction is not active. Status: PREPARED`.

In production this is invisible, because each service owns its own manager. It bites in **tests and
single-process prototypes**, where the natural thing to write is one manager and two variables:

```java
// WRONG — participant IS coordinator; the second prepare() throws
TwoPhaseCommitTransaction coordinator = manager.begin();
TwoPhaseCommitTransaction participant  = manager.join(coordinator.getId());

// RIGHT — one manager per participating service, even in a test
TwoPhaseCommitTransaction coordinator = orderManager.begin();
TwoPhaseCommitTransaction participant  = inventoryManager.join(coordinator.getId());
```

A 2PC integration test built on one manager does not exercise 2PC. Build a second
`TransactionFactory` over the same configuration and take its manager (verified on ScalarDB 3.19.0).

## Protocol Misuse Is Unchecked

`commit()` before `prepare()` — and the other out-of-order calls — throw **`IllegalStateException`**,
not a `TransactionException`. It is unchecked, so the compiler does not demand it and a handler
written as `catch (TransactionException e)` never sees it: it escapes the transaction layer entirely
and surfaces as an unhandled 500.

This matters for the API layer's exception mapping (@rules/api-error-standard.md §3): the
`@RestControllerAdvice` needs a branch for it, and it is **not** `transaction-failed` — a protocol
misuse is a server defect, not a transaction outcome. Treat it as an unhandled internal error and
alert on it, rather than folding it into the retryable family.

## Coordinator vs Participant

- **Coordinator** calls `begin()` or `start()` — initiates the transaction
- **Participant** calls `join(txId)` — joins an existing transaction by ID
- **Resume** (`resume(txId)`) — reconnects to an existing transaction for prepare/validate/commit

## All Participants Must Prepare

If ANY prepare fails, ALL participants MUST rollback:

```java
try {
    tx1.prepare();
    tx2.prepare();
} catch (PreparationException e) {
    tx1.rollback();
    tx2.rollback();
    throw e;
}
```

## Commit Is Best-Effort

If ANY commit succeeds, the transaction is considered committed. Other commits should succeed but are not strictly required:

```java
tx1.commit();
tx2.commit(); // Should succeed; if it fails, the data will eventually be reconciled
```

## Rollback ALL on Failure

On any exception (except `UnknownTransactionStatusException`), rollback ALL participants:

```java
} catch (TransactionException e) {
    rollbackAll(tx1, tx2, tx3);
    throw e;
}

private void rollbackAll(TwoPhaseCommitTransaction... txs) {
    for (TwoPhaseCommitTransaction tx : txs) {
        if (tx != null) {
            try { tx.rollback(); } catch (RollbackException e) { /* log */ }
        }
    }
}
```

## Validate Is Version-Dependent — Verify Against the Pinned Release

Whether `validate()` may be skipped **changed across releases**, and getting it wrong under
SERIALIZABLE silently weakens isolation (the 2PC interface only runs the validation phase when the
application calls `validate()`):

- **ScalarDB 3.19+**: the `serializable_strategy` key no longer exists. The consensus-commit
  documentation requires the validate-records phase **whenever `isolation_level=SERIALIZABLE`** —
  so in application-driven 2PC, `validate()` MUST be called on every participant. There is no
  skippable combination.
- **Older lines (≤3.13 Community, and where `serializable_strategy` is documented)**: `validate()`
  was required only for `SERIALIZABLE` + `EXTRA_READ`.

Any design that omits `validate()` MUST cite the pinned release's `consensus-commit.md` from the
OKF bundle (@rules/okf-knowledge-bundle.md) as evidence — a design document claiming "validate is
optional" without a version-pinned citation is a review finding (this exact defect shipped once as
SDB-101). When in doubt, call `validate()` unconditionally: it is correct on every release.

## Don't Reuse Transaction IDs

When retrying a failed 2PC transaction, use a NEW transaction ID (call `begin()` again, not `begin(oldTxId)`).

## Group Commit Incompatibility

Group commit (`scalar.db.consensus_commit.coordinator.group_commit.enabled=true`) CANNOT be used with the 2PC interface.

## Request Routing

All operations in a 2PC transaction MUST route to the same ScalarDB Cluster node:
- Use gRPC with same connection (automatic)
- With L7 load balancer: use session affinity
- With `direct-kubernetes` mode: handled automatically via consistent hashing

## Microservice Pattern (Deprecated Interface)

This is the hand-written orchestration of option 3. On ScalarDB 3.19+ the Microservice Transaction
API replaces every step below with ordinary one-phase code (§ above) — reach for this pattern
only when options 1 and 2 are unavailable, and record the deviation. Note that 3.20 removed
`join()` / `resume()` from `DistributedTransactionManager`; the `TwoPhaseCommitTransactionManager`
methods remain, deprecated.

In a microservice architecture with gRPC:
1. Coordinator calls `begin()`, gets `txId`
2. Coordinator sends `txId` to participants via gRPC
3. Each participant calls `join(txId)`, performs CRUD, returns
4. Coordinator calls `prepare()` on itself, then tells participants to `prepare()`
5. Coordinator calls `validate()` on itself, then tells participants to `validate()`
6. Coordinator calls `commit()` on itself, then tells participants to `commit()`
7. On failure at any step, coordinator tells ALL to `rollback()`

Participants expose gRPC endpoints for: `prepare(txId)`, `validate(txId)`, `commit(txId)`, `rollback(txId)`.
Each of these endpoints calls `resume(txId)` then the corresponding operation.

## JDBC/SQL Two-Phase Commit (Deprecated Interface)

When using the JDBC/SQL interface, 2PC is managed via SQL transaction control statements instead of Java method calls.
The SQL `TWO_PHASE_COMMIT_TRANSACTION` mode is **deprecated as of 3.19**, and 3.20 removed the
`JOIN`, `SUSPEND` and `RESUME` statements. On 3.20+ a SQL transaction that spans processes uses the
`GLOBAL_TRANSACTION` session mode instead: one process begins the transaction, each other process
runs `BEGIN BRANCH` ... `END BRANCH` with the ID, and the Transaction Coordinator drives 2PC when
`scalar.db.sql.enabled=true` on it. Ground the exact statement grammar on the pinned 3.20 line
(`releases/release-notes.md`, `scalardb-sql/grammar.md`) — the 3.19 grammar predates it.

### SQL 2PC Statements

```sql
BEGIN;                -- or START TRANSACTION;
-- SQL operations (SELECT, INSERT, UPDATE, DELETE)
PREPARE;              -- Prepare the transaction
VALIDATE;             -- Only if SERIALIZABLE + EXTRA_READ
COMMIT;               -- Final commit
-- On failure:
ROLLBACK;             -- or ABORT;
```

### JDBC 2PC Java Code Pattern

```java
try (Connection conn = getConnection()) {
    conn.setAutoCommit(false);
    try {
        // SQL operations via PreparedStatement
        try (PreparedStatement ps = conn.prepareStatement("INSERT INTO ...")) {
            ps.executeUpdate();
        }

        // 2PC protocol via SQL statements
        try (Statement stmt = conn.createStatement()) {
            stmt.execute("PREPARE");
        }
        try (Statement stmt = conn.createStatement()) {
            stmt.execute("VALIDATE"); // Only if SERIALIZABLE + EXTRA_READ
        }

        conn.commit(); // Final commit
    } catch (SQLException e) {
        if (e.getErrorCode() == 301) {
            // UnknownTransactionStatusException — do NOT rollback
            logger.error("Unknown transaction status in 2PC", e);
        } else {
            conn.rollback();
            throw e;
        }
    }
}
```

### CRUD 2PC vs JDBC 2PC Mapping

| CRUD 2PC | JDBC 2PC |
|----------|----------|
| `manager.begin()` | `conn.setAutoCommit(false)` (implicit begin) |
| `tx.prepare()` | `stmt.execute("PREPARE")` |
| `tx.validate()` | `stmt.execute("VALIDATE")` |
| `tx.commit()` | `conn.commit()` |
| `tx.rollback()` | `conn.rollback()` |
| `tx.getId()` | Managed internally by the connection |
| `manager.join(txId)` | Via SQL session (connection-based) |

### JDBC 2PC Limitations

- Transaction ID is managed internally by the connection — you cannot directly access it like `tx.getId()`
- Participant coordination between microservices still requires an RPC mechanism (gRPC, REST)
- All statements in a 2PC transaction MUST route to the same ScalarDB Cluster node (use session affinity with L7 load balancers)
