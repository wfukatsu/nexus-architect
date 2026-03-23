---
description: ScalarDB two-phase commit transaction rules — applies when writing Java code that uses TwoPhaseCommitTransactionManager
globs:
  - "**/*.java"
---

# ScalarDB Two-Phase Commit Rules

## Protocol Order

The 2PC protocol MUST follow this order:

```
Coordinator: begin() → CRUD → prepare() → validate() → commit()
Participant: join(txId) → CRUD → (wait) → prepare() → validate() → commit()
```

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

## Validate Is Conditional

`validate()` is only required when BOTH conditions are true:
- `scalar.db.consensus_commit.isolation_level=SERIALIZABLE`
- `scalar.db.consensus_commit.serializable_strategy=EXTRA_READ`

If not using this combination, `validate()` can be skipped.

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
