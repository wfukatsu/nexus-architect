# ScalarDB Exception Hierarchy

## Exception Tree

```
java.lang.Exception
  └── TransactionException                          [base class]
        ├── CrudException                           [CRUD operation failure]
        │     ├── CrudConflictException              [CRUD conflict — RETRYABLE]
        │     └── UnsatisfiedConditionException      [mutation condition not met]
        ├── CommitException                          [commit failure]
        │     └── CommitConflictException             [commit conflict — RETRYABLE]
        ├── PreparationException                     [2PC prepare failure]
        │     └── PreparationConflictException        [2PC prepare conflict — RETRYABLE]
        ├── ValidationException                      [2PC validate failure]
        │     └── ValidationConflictException         [2PC validate conflict — RETRYABLE]
        ├── RollbackException                        [rollback failure]
        ├── AbortException                           [abort failure]
        ├── UnknownTransactionStatusException        [commit status unknown — SPECIAL]
        └── TransactionNotFoundException             [transaction not found / begin failed]
```

All exception classes are in package: `com.scalar.db.exception.transaction`

## Key Base Class Methods

`TransactionException` provides:
- `getTransactionId()` → `Optional<String>` — Transaction ID for debugging
- `isAuthenticationError()` → `boolean`
- `isAuthorizationError()` → `boolean`

## Exception Handling Decision Flowchart

```
Exception caught?
├── Is it *ConflictException? (CrudConflict, CommitConflict, PreparationConflict, ValidationConflict)
│   └── YES → Abort/rollback → Retry the entire transaction from begin()
│
├── Is it UnsatisfiedConditionException?
│   └── YES → Abort/rollback → Application logic error (condition not met), do NOT retry
│
├── Is it UnknownTransactionStatusException?
│   └── YES → DO NOT retry blindly
│         → Log the transaction ID
│         → The transaction may have been committed or aborted
│         → Check application state / use idempotency
│         → If the transaction was actually committed, retrying would cause duplicate operations
│
├── Is it TransactionNotFoundException?
│   └── YES → The transaction expired or was not found
│         → Retry from begin()
│
├── Is it CrudException / CommitException / PreparationException / ValidationException?
│   └── YES → Abort/rollback
│         → These are parent classes; could be transient or non-transient
│         → Can attempt retry, but may fail again with same error
│
└── Is it RollbackException / AbortException?
    └── YES → The rollback/abort itself failed
          → Log and continue; the transaction will eventually time out
```

## Correct Catch Order (Critical!)

Catch specific conflict exceptions BEFORE their parent classes:

```java
// CORRECT order:
try {
    // ... transaction operations ...
    transaction.commit();
} catch (UnsatisfiedConditionException e) {
    transaction.rollback();
    // Handle condition not met — don't retry
} catch (CommitConflictException e) {
    transaction.rollback();
    // Retry the entire transaction
} catch (UnknownTransactionStatusException e) {
    // DO NOT rollback — status is unknown
    // Log transaction ID and handle carefully
} catch (CommitException e) {
    transaction.rollback();
    // May or may not be retriable
} catch (CrudConflictException e) {
    transaction.rollback();
    // Retry the entire transaction
} catch (CrudException e) {
    transaction.rollback();
    // May or may not be retriable
}

// WRONG order (conflict exceptions unreachable):
try {
    transaction.commit();
} catch (CrudException e) {        // Catches CrudConflictException too!
    // ...
} catch (CrudConflictException e) { // NEVER REACHED
    // ...
}
```

## Complete Retry Pattern (Recommended)

```java
int retryCount = 0;
TransactionException lastException = null;

while (true) {
    if (retryCount > 0) {
        if (retryCount >= MAX_RETRIES) {
            throw lastException;
        }
        TimeUnit.MILLISECONDS.sleep(100 * retryCount); // exponential backoff
    }
    retryCount++;

    DistributedTransaction transaction = null;
    try {
        transaction = transactionManager.begin();
        // Execute CRUD operations
        transaction.commit();
        return; // success
    } catch (UnsatisfiedConditionException e) {
        try { transaction.rollback(); } catch (RollbackException ex) { /* log */ }
        throw e; // don't retry — application logic error
    } catch (UnknownTransactionStatusException e) {
        // Don't rollback — status is unknown
        // Log transaction ID for investigation
        throw e;
    } catch (TransactionException e) {
        if (transaction != null) {
            try { transaction.rollback(); } catch (RollbackException ex) { /* log */ }
        }
        lastException = e;
        // Loop will retry
    }
}
```

## Two-Phase Commit Exception Handling

For 2PC, additional exceptions occur during `prepare()` and `validate()`:

```java
TwoPhaseCommitTransaction tx = null;
try {
    tx = twoPhaseCommitTransactionManager.begin();
    // CRUD operations...
    tx.prepare();
    tx.validate();
    tx.commit();
} catch (PreparationConflictException e) {
    if (tx != null) tx.rollback();
    // Retry — conflict during prepare
} catch (PreparationException e) {
    if (tx != null) tx.rollback();
    // Prepare failed — may or may not be retriable
} catch (ValidationConflictException e) {
    if (tx != null) tx.rollback();
    // Retry — conflict during validate
} catch (ValidationException e) {
    if (tx != null) tx.rollback();
    // Validate failed — may or may not be retriable
} catch (CommitConflictException e) {
    if (tx != null) tx.rollback();
    // Retry — conflict during commit
} catch (UnknownTransactionStatusException e) {
    // Don't rollback — status unknown
} catch (CommitException e) {
    if (tx != null) tx.rollback();
    // Commit failed
} catch (TransactionException e) {
    if (tx != null) tx.rollback();
    // Other failure
}
```

## Summary Table

| Exception | Retriable? | Action |
|-----------|-----------|--------|
| `CrudConflictException` | Yes | Rollback → Retry |
| `CommitConflictException` | Yes | Rollback → Retry |
| `PreparationConflictException` | Yes | Rollback → Retry |
| `ValidationConflictException` | Yes | Rollback → Retry |
| `UnsatisfiedConditionException` | No | Rollback → Handle app logic |
| `UnknownTransactionStatusException` | No | Do NOT rollback → Log + investigate |
| `TransactionNotFoundException` | Yes | Retry from begin() |
| `CrudException` | Maybe | Rollback → Try retry |
| `CommitException` | Maybe | Rollback → Try retry |
| `PreparationException` | Maybe | Rollback → Try retry |
| `ValidationException` | Maybe | Rollback → Try retry |
| `RollbackException` | N/A | Log → Transaction will time out |
| `AbortException` | N/A | Log → Transaction will time out |

## JDBC/SQL Exception Handling

When using the ScalarDB JDBC driver, all ScalarDB SQL exceptions are wrapped in `java.sql.SQLException`. The JDBC driver uses error codes to identify specific exception types.

### SQL API Exception Hierarchy (com.scalar.db.sql.exception)

```
java.lang.Exception
  └── SqlException                              [base class for SQL API]
        ├── TransactionRetryableException        [RETRYABLE — safe to retry]
        └── UnknownTransactionStatusException    [SPECIAL — do NOT retry blindly]
```

### JDBC Error Code Mapping

| JDBC Error Code | Original Exception | Action |
|----------------|-------------------|--------|
| 301 | `UnknownTransactionStatusException` | Do NOT rollback. Verify if committed, retry only if not. |
| Other | `TransactionRetryableException` (check cause) | Rollback → Retry |
| Other | Other `SqlException` | Rollback → Retry with limits (may be non-transient) |

### How JDBC Wraps SQL Exceptions

```
SqlException → java.sql.SQLException
├── UnknownTransactionStatusException → SQLException (errorCode = 301)
├── TransactionRetryableException     → SQLException (check getCause())
└── Other SqlException                → SQLException
```

To determine retryability for non-301 errors, check the cause:
```java
if (e.getCause() instanceof TransactionRetryableException) {
    // Safe to retry
}
```

### Complete JDBC Exception Handling Pattern

```java
connection.setAutoCommit(false);
try {
    // Execute SQL statements
    connection.commit();
} catch (SQLException e) {
    if (e.getErrorCode() == 301) {
        // UnknownTransactionStatusException
        // Do NOT rollback — status is unknown
        // Verify if the transaction committed, retry only if it did not
        logger.error("Unknown transaction status", e);
    } else {
        connection.rollback();
        // The cause can be TransactionRetryableException (retry)
        // or other exceptions (retry with limits — may be non-transient)
    }
}
```

### Key Differences from CRUD API Exception Handling

| Aspect | CRUD API | JDBC/SQL |
|--------|----------|----------|
| Exception class | `TransactionException` hierarchy | `java.sql.SQLException` |
| Conflict detection | Catch `*ConflictException` classes | Check `getCause()` for `TransactionRetryableException` |
| Unknown status | Catch `UnknownTransactionStatusException` | Check `e.getErrorCode() == 301` |
| Transaction ID | `e.getTransactionId()` | Not directly available from `SQLException` |
| Rollback call | `tx.rollback()` | `conn.rollback()` |
| Condition failure | `UnsatisfiedConditionException` | Check cause |
