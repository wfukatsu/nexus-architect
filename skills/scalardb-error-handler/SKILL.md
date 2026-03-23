---
description: Generate correct ScalarDB exception handling code with retry logic. Can also review existing code for exception handling correctness.
user_invocable: true
---

# /scalardb-error-handler — ScalarDB Exception Handling Guide

## Instructions

You are a ScalarDB exception handling expert. You can either generate correct exception handling code or review existing code.

## Modes

### Mode 1: Generate Exception Handling Code
Ask: "Which interface combination are you using?"
- CRUD API + 1PC (DistributedTransactionManager)
- CRUD API + 2PC (TwoPhaseCommitTransactionManager)
- JDBC/SQL

Then generate the complete try/catch pattern with:
- Correct catch order (specific before general)
- Retry logic with exponential backoff
- Proper rollback in catch blocks
- UnknownTransactionStatusException handling
- Transaction ID logging

### Mode 2: Review Existing Code
If the user provides code or points to a file, review it for:
- Incorrect catch order (parent caught before child)
- Missing rollback in catch blocks
- Missing commit for read-only transactions
- Incorrect handling of UnknownTransactionStatusException
- Missing retry logic for conflict exceptions
- Missing transaction ID logging

## Reference

Read `.claude/docs/exception-hierarchy.md` for the complete exception hierarchy and decision flowchart.

## Exception Hierarchy

```
TransactionException
├── CrudException
│   ├── CrudConflictException          ← RETRYABLE
│   └── UnsatisfiedConditionException  ← NOT retryable
├── CommitException
│   └── CommitConflictException        ← RETRYABLE
├── PreparationException               (2PC only)
│   └── PreparationConflictException   ← RETRYABLE
├── ValidationException                (2PC only)
│   └── ValidationConflictException    ← RETRYABLE
├── UnknownTransactionStatusException  ← SPECIAL (don't retry blindly)
├── TransactionNotFoundException       ← RETRYABLE
├── RollbackException
└── AbortException
```

## Correct Pattern: CRUD API + 1PC

```java
private static final int MAX_RETRIES = 3;

public void executeWithRetry() throws TransactionException, InterruptedException {
    int retryCount = 0;
    TransactionException lastException = null;

    while (true) {
        if (retryCount > 0) {
            if (retryCount >= MAX_RETRIES) throw lastException;
            TimeUnit.MILLISECONDS.sleep(100 * retryCount); // exponential backoff
        }
        retryCount++;

        DistributedTransaction tx = null;
        try {
            tx = manager.begin();
            // ... CRUD operations ...
            tx.commit();
            return; // success
        } catch (UnsatisfiedConditionException e) {
            try { tx.rollback(); } catch (RollbackException ex) {
                logger.warn("Rollback failed", ex);
            }
            throw e; // don't retry
        } catch (UnknownTransactionStatusException e) {
            // Don't rollback — status unknown
            logger.error("Unknown transaction status. txId={}",
                e.getTransactionId().orElse("unknown"), e);
            throw e;
        } catch (TransactionException e) {
            if (tx != null) {
                try { tx.rollback(); } catch (RollbackException ex) {
                    logger.warn("Rollback failed", ex);
                }
            }
            logger.warn("Transaction failed, retrying. txId={}",
                e.getTransactionId().orElse("unknown"), e);
            lastException = e;
        }
    }
}
```

## Correct Pattern: CRUD API + 2PC

```java
public void executeTwoPhaseCommitWithRetry() throws TransactionException, InterruptedException {
    int retryCount = 0;
    TransactionException lastException = null;

    while (true) {
        if (retryCount > 0) {
            if (retryCount >= MAX_RETRIES) throw lastException;
            TimeUnit.MILLISECONDS.sleep(100 * retryCount);
        }
        retryCount++;

        TwoPhaseCommitTransaction tx = null;
        try {
            tx = manager.begin();
            // ... CRUD operations ...
            tx.prepare();
            tx.validate();
            tx.commit();
            return;
        } catch (UnsatisfiedConditionException e) {
            if (tx != null) try { tx.rollback(); } catch (RollbackException ex) { }
            throw e;
        } catch (UnknownTransactionStatusException e) {
            throw e;
        } catch (TransactionException e) {
            if (tx != null) try { tx.rollback(); } catch (RollbackException ex) { }
            lastException = e;
        }
    }
}
```

## Correct Pattern: JDBC/SQL (1PC)

```java
public void executeJdbcWithRetry() throws SQLException, InterruptedException {
    int retryCount = 0;
    SQLException lastException = null;

    while (true) {
        if (retryCount > 0) {
            if (retryCount >= MAX_RETRIES) throw lastException;
            TimeUnit.MILLISECONDS.sleep(100 * retryCount);
        }
        retryCount++;

        try (Connection conn = DriverManager.getConnection(JDBC_URL)) {
            conn.setAutoCommit(false);
            try {
                // ... SQL operations using PreparedStatement ...
                conn.commit();
                return; // success
            } catch (SQLException e) {
                if (e.getErrorCode() == 301) {
                    // UnknownTransactionStatusException — do NOT rollback
                    // Must verify if the transaction committed, retry only if not
                    logger.error("Unknown transaction status", e);
                    throw e;
                }
                conn.rollback();
                // The cause can be TransactionRetryableException (retry)
                // or other exceptions (retry with limits — may be non-transient)
                logger.warn("JDBC transaction failed, retrying: {}", e.getMessage(), e);
                lastException = e;
            }
        } catch (SQLException e) {
            // Connection failure
            logger.warn("JDBC connection failed, retrying: {}", e.getMessage(), e);
            lastException = e;
        }
    }
}
```

## Correct Pattern: JDBC/SQL (2PC)

```java
public void executeJdbc2pcWithRetry() throws SQLException, InterruptedException {
    int retryCount = 0;
    SQLException lastException = null;

    while (true) {
        if (retryCount > 0) {
            if (retryCount >= MAX_RETRIES) throw lastException;
            TimeUnit.MILLISECONDS.sleep(100 * retryCount);
        }
        retryCount++;

        try (Connection conn = DriverManager.getConnection(JDBC_URL)) {
            conn.setAutoCommit(false);
            try {
                // ... SQL operations using PreparedStatement ...

                // 2PC protocol via SQL statements
                try (Statement stmt = conn.createStatement()) {
                    stmt.execute("PREPARE");
                }
                try (Statement stmt = conn.createStatement()) {
                    stmt.execute("VALIDATE"); // Only if SERIALIZABLE + EXTRA_READ
                }

                conn.commit(); // Final commit
                return; // success
            } catch (SQLException e) {
                if (e.getErrorCode() == 301) {
                    logger.error("Unknown transaction status in 2PC", e);
                    throw e;
                }
                conn.rollback();
                logger.warn("JDBC 2PC transaction failed, retrying: {}", e.getMessage(), e);
                lastException = e;
            }
        } catch (SQLException e) {
            logger.warn("JDBC connection failed, retrying: {}", e.getMessage(), e);
            lastException = e;
        }
    }
}
```

## Common Mistakes to Flag

### CRUD API
1. Catching parent before child: `catch (CrudException)` before `catch (CrudConflictException)`
2. Missing rollback in catch blocks
3. Rollback on `UnknownTransactionStatusException`
4. No retry for conflict exceptions
5. Not committing read-only transactions
6. Not logging transaction ID from exceptions

### JDBC/SQL
7. Missing `setAutoCommit(false)` on Connection
8. Not checking error code 301 for `UnknownTransactionStatusException`
9. Calling `rollback()` when error code is 301 (should NOT rollback)
10. Not committing read-only JDBC transactions
11. Missing try-with-resources for Connection/PreparedStatement/ResultSet
12. String concatenation in SQL (SQL injection risk)
13. No retry logic for JDBC transactions
