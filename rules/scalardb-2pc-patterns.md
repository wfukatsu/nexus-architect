---
description: ScalarDB cross-service transaction rules — choosing between the one-phase interface, the Global Transaction API, application-driven 2PC, and ScalarDB Saga, and writing Java code that uses TwoPhaseCommitTransactionManager
globs:
  - "**/*.java"
---

# ScalarDB Cross-Service Transaction Rules

## Choose the Mechanism Before Writing 2PC Code

Hand-written two-phase commit is the most expensive of four options and, since ScalarDB 3.19, no
longer the default answer for microservice transactions. Decide in this order:

| # | Mechanism | Use when | Application interface |
|---|-----------|----------|-----------------------|
| 1 | **Shared-cluster, one-phase commit** | Every service can talk to one ScalarDB Cluster instance. The documented recommendation "whenever possible" | Ordinary one-phase `DistributedTransactionManager`; one service calls `commit()` |
| 2 | **Global Transaction API** (3.19+, Cluster) | Services need their own Cluster instances (isolation, per-team administration) but you do not want the application sequencing the protocol | `GlobalTransactionManager` — one-phase code; the **Transaction Coordinator** node drives 2PC underneath. The same code also runs single-Cluster; only configuration selects which |
| 3 | **Application-driven 2PC** (this document) | Pre-3.19, no Transaction Coordinator deployed, Core (Community) without Cluster, or Spring Data JDBC (which does not support the shared-cluster pattern) | `TwoPhaseCommitTransactionManager` — the application sequences `prepare`/`validate`/`commit` and handles partial failure. **Supported, not deprecated**: on 3.19 `two-phase-commit-transactions.md` is `status: stable` across Community / Enterprise Standard / Enterprise Premium, and `scalardb-samples/microservice-transaction-sample` still uses it. It is no longer the *recommended default* — options 1 and 2 come first — so record why it was chosen in the transaction design document |
| 4 | **ScalarDB Saga** | A single ACID transaction across the services is not possible or not wanted — long-running steps, external systems, eventual consistency acceptable | Saga/TCC definitions with compensations. See @rules/scalardb-saga-patterns.md |

Options 1–3 give strong consistency; option 4 trades it for compensation-based rollback and
eventual convergence. Record which option was chosen and why in the transaction design document.

Grounding: `products/scalardb/<version>/scalardb-cluster/deployment-patterns-for-microservices.md`
for options 1 and 3, `products/scalardb/<version>/two-phase-commit-transactions.md` for option 3's
support status and API, and `products/scalardb/3.19/releases/release-notes.md` (v3.19.0) for option 2 —
the Global Transaction API and Transaction Coordinator are described in the release notes, and the
deployment-pattern guide has not yet been updated to cover them. Confirm against the project's
pinned release before designing on option 2, per @rules/okf-knowledge-bundle.md.

Everything below applies to **option 3**.

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

## Microservice Pattern

This is the hand-written orchestration of option 3. On ScalarDB 3.19 with a Transaction Coordinator
node deployed, option 2 replaces every step below with ordinary one-phase code — reach for this
pattern only when option 2 is unavailable.

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

## JDBC/SQL Two-Phase Commit

When using the JDBC/SQL interface, 2PC is managed via SQL transaction control statements instead of Java method calls.

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
