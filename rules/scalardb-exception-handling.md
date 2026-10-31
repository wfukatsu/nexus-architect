---
description: ScalarDB exception handling rules — applies when writing or reviewing Java code that uses ScalarDB transaction APIs
globs:
  - "**/*.java"
---

# ScalarDB Exception Handling Rules

What transaction code must do when a ScalarDB exception is caught, and what a reviewer flags. The
facts these rules rest on — the exception tree, the decision flowchart, the JDBC error-code
mapping and the complete catch-block patterns for the CRUD, 2PC, JDBC and SQL APIs — are
`skills/common/references/exception-hierarchy.md`; read it when writing the code, this file when
deciding what the code has to do.

## Catch Order (CRITICAL)

Catch specific conflict exceptions **before** their parent classes. Catching the parent first makes
the conflict catch block unreachable:

```java
// CORRECT:
catch (CrudConflictException e) { ... }   // specific first
catch (CrudException e) { ... }           // parent second

// WRONG — CrudConflictException is unreachable:
catch (CrudException e) { ... }
catch (CrudConflictException e) { ... }   // NEVER REACHED
```

This applies to every pair: `CrudConflictException` / `CrudException`, `CommitConflictException` /
`CommitException`, `PreparationConflictException` / `PreparationException`,
`ValidationConflictException` / `ValidationException`.

## Rollback/Abort in Catch Blocks

Always abort/rollback the transaction in a catch block, guarding the rollback itself:

```java
} catch (TransactionException e) {
    if (transaction != null) {
        try { transaction.rollback(); } catch (RollbackException ex) { /* log */ }
    }
}
```

Exception: do **not** rollback for `UnknownTransactionStatusException` — the status is unknown and
a rollback may interfere.

## UnknownTransactionStatusException

The most critical exception to handle correctly:
- The commit may have succeeded **or** failed — the code does not know
- Do not retry blindly — a retry may create duplicate data
- Log the transaction ID for investigation
- Use an idempotency pattern to make the retry safe, or verify the outcome before retrying

How this surfaces at the HTTP boundary (503 with `Retry-After` only under an idempotency key,
otherwise 500 with a reconcile-don't-retry `detail`) is `rules/api-error-standard.md`.

## Always Commit (Even Read-Only)

Read-only transactions call `commit()` too. An uncommitted transaction stays open and wastes
resources.

## Log Transaction ID

Every `TransactionException` carries `getTransactionId()`. Log it:

```java
} catch (TransactionException e) {
    logger.error("Transaction failed. txId={}", e.getTransactionId().orElse("unknown"), e);
}
```

## Conflict Exceptions Are Retriable; UnsatisfiedConditionException Is Not

`*ConflictException` types (`CrudConflict`, `CommitConflict`, `PreparationConflict`,
`ValidationConflict`) are transient: rollback, then retry the **entire** transaction from `begin()`,
with backoff and a maximum (the retry loop is in the reference).

`UnsatisfiedConditionException` means a mutation condition (`updateIfExists()` and the like) was not
met. That is an application-logic outcome, not a transient error: rollback, do not retry.

## JDBC/SQL Exception Handling

Through the ScalarDB JDBC driver every ScalarDB SQL exception arrives as `java.sql.SQLException`,
distinguished by error code and cause (mapping in the reference). The rules carry over:

- **Error code 301 is `UnknownTransactionStatusException`**: do not rollback, do not retry blindly;
  verify whether the transaction committed and retry only if it did not.
- **Any other code**: rollback first; retry when `e.getCause()` is `TransactionRetryableException`,
  otherwise retry with a limit — the cause may be non-transient.
- Read-only JDBC transactions call `conn.commit()`; every non-301 catch block calls `conn.rollback()`.
- The SQL API used directly (`SqlSession`) throws the `com.scalar.db.sql.exception` classes
  unwrapped: `UnknownTransactionStatusException` is the no-rollback branch, every other
  `SqlException` is rollback-then-retry-with-limits.

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
