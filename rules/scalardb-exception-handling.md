---
description: ScalarDB exception handling rules — applies when writing or reviewing Java code that uses ScalarDB transaction APIs
globs:
  - "**/*.java"
---

# ScalarDB Exception Handling Rules

## Catch Order (CRITICAL)

Always catch specific conflict exceptions BEFORE their parent classes. Catching the parent first makes the conflict catch block unreachable:

```java
// CORRECT:
catch (CrudConflictException e) { ... }   // specific first
catch (CrudException e) { ... }           // parent second

// WRONG — CrudConflictException is unreachable:
catch (CrudException e) { ... }
catch (CrudConflictException e) { ... }   // NEVER REACHED
```

This applies to all exception pairs:
- `CrudConflictException` before `CrudException`
- `CommitConflictException` before `CommitException`
- `PreparationConflictException` before `PreparationException`
- `ValidationConflictException` before `ValidationException`

## Rollback/Abort in Catch Blocks

Always abort/rollback the transaction in catch blocks:

```java
} catch (TransactionException e) {
    if (transaction != null) {
        try { transaction.rollback(); } catch (RollbackException ex) { /* log */ }
    }
}
```

Exception: Do NOT rollback for `UnknownTransactionStatusException` — the status is unknown and rollback may interfere.

## UnknownTransactionStatusException

This is the most critical exception to handle correctly:
- The commit may have succeeded OR failed — you don't know
- Do NOT retry blindly — you may create duplicate data
- Log the transaction ID for investigation
- Use idempotency patterns to handle this safely

## Always Commit (Even Read-Only)

Read-only transactions MUST call `commit()`. Forgetting to commit leaves the transaction open and wastes resources.

## Log Transaction ID

All ScalarDB exceptions provide `getTransactionId()`. Always log it for debugging:

```java
} catch (TransactionException e) {
    logger.error("Transaction failed. txId={}", e.getTransactionId().orElse("unknown"), e);
}
```

## Conflict Exceptions Are Retriable

`*ConflictException` types are transient — retry the entire transaction from `begin()`:
- `CrudConflictException`
- `CommitConflictException`
- `PreparationConflictException`
- `ValidationConflictException`

## UnsatisfiedConditionException Is NOT Retriable

This means a mutation condition (e.g., `updateIfExists()`) was not met. This is an application logic issue, not a transient error.

## JDBC/SQL Exception Handling

When using the ScalarDB JDBC driver, all ScalarDB SQL exceptions are wrapped in `java.sql.SQLException`. The JDBC driver uses error codes and exception causes to distinguish exception types.

### Error Code 301: UnknownTransactionStatusException

The most critical JDBC error code. When `e.getErrorCode() == 301`:
- Do NOT rollback — the transaction status is unknown
- Do NOT retry blindly — the transaction may have already committed
- Must manually verify whether the transaction committed, and retry only if it did not

### Retryable vs Non-Retryable SQLExceptions

For SQLExceptions other than error code 301:
- Always rollback first
- Check if `e.getCause()` is `TransactionRetryableException` — if so, retry the transaction
- For other causes, the error may be non-transient — retry with a maximum limit

### Correct JDBC Exception Handling Pattern

```java
connection.setAutoCommit(false);
try {
    // Execute statements (SELECT/INSERT/UPDATE/DELETE)
    connection.commit();
} catch (SQLException e) {
    if (e.getErrorCode() == 301) {
        // UnknownTransactionStatusException — do NOT rollback
        // Must verify if the transaction committed, then retry if it did not
        logger.error("Unknown transaction status", e);
    } else {
        connection.rollback();
        // The cause can be TransactionRetryableException or other exceptions.
        // For TransactionRetryableException, you can basically retry.
        // For other exceptions, the cause may be non-transient — limit retries.
    }
}
```

### SQL API Exception Hierarchy

The ScalarDB SQL API (non-JDBC) has its own exception hierarchy in `com.scalar.db.sql.exception`:
- `SqlException` — base exception class
- `TransactionRetryableException` — retryable; safe to retry the entire transaction
- `UnknownTransactionStatusException` — commit status unknown; do NOT retry blindly

When using the SQL API directly (via `SqlSession`):
```java
try {
    sqlSession.begin();
    // Execute statements
    sqlSession.commit();
} catch (UnknownTransactionStatusException e) {
    // Do NOT rollback — status unknown; verify and retry if needed
} catch (SqlException e) {
    sqlSession.rollback();
    // Retry with limits
}
```

### Always Commit Read-Only JDBC Transactions

Just like the CRUD API, read-only JDBC transactions MUST call `conn.commit()`.

### Always Rollback in JDBC Catch Blocks

Always call `conn.rollback()` in catch blocks (except for error code 301).

## Recovery APIs Are Not Error Handling (3.19+)

ScalarDB 3.19 added three recovery capabilities to the Consensus Commit transaction manager. They
are **low-level operational APIs**, not part of an application's exception-handling path — do not
call them from a catch block, and do not generate code that does.

| Capability | What it is | Who calls it |
|------------|-----------|--------------|
| `scalar.db.consensus_commit.coordinator.write_set_logging.enabled` | Opt-in; adds a `tx_write_set` column to the Coordinator table and populates it on commit/abort, laying the groundwork for proactive recovery. Existing Coordinator tables migrate by enabling it and running `Admin.repairCoordinatorTables()` | Operator, at deployment |
| `DistributedTransactionManager#finishTransaction(String)` | Completes per-record post-commit recovery for a committed transaction and removes its Coordinator state row. Returns `true` when finished (or already finished), `false` when the transaction carries no write set (e.g. it was `rollback()`/`abort()`ed rather than committed); throws `TransactionException` on failure | Operational tooling |
| `DistributedTransactionManager#recoverRecord` | Recovers a single record left uncommitted by a crashed transaction | Operational tooling |

The documented guidance is explicit: most applications should not call these directly, and callers
are expected to understand the transaction lifecycle and the implications. Normal applications rely
on lazy recovery, which happens automatically.

Source: `products/scalardb/3.19/releases/release-notes.md` (v3.19.0). Verify against the project's
pinned release per @rules/okf-knowledge-bundle.md.

## ScalarDB Cluster Pause Failures (3.19+)

For operational tooling that pauses a Cluster (backup workflows, `scalar-admin`): every pause
failure used to be `FAILED_PRECONDITION`. From 3.19, a failure caused by losing a race with another
admin request is `ABORTED` and can simply be retried. Every pause failure also carries a
`google.rpc.ErrorInfo` detail in the status trailers with `domain=com.scalar.db.cluster.admin` and
`reason` set to the outcome — match on `reason`, never on the status code or description text.

**A caller that unpauses to recover from a failed pause must skip that unpause when the reason is
`TIMED_OUT_STILL_PAUSED`**, because the server is still paused by an earlier request.
