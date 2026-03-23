# AQ Consumer Exception Handling Strategy

## The Problem

In an Oracle AQ consumer that writes to ScalarDB, the current pattern catches all exceptions and calls `session.rollback()`. This returns every failed message to the queue for redelivery, regardless of whether the failure is transient or permanent.

A message with corrupt data or an unknown `operation_type` will never succeed. Rolling it back wastes `max_retries` dequeue cycles (default: 5 retries = 6 total attempts) before it finally lands in the exception queue as a "failure" that was never going to work.

```java
// Current pattern — treats every failure the same
} catch (Exception e) {
    session.rollback();  // always retry, even for permanent failures
}
```

---

## The Dual-Transaction Context

The AQ consumer operates two independent transactions per message:

```
1. ScalarDB transaction:  tx.commit()      → writes data
2. AQ JMS session:        session.commit()  → removes message from queue
```

The exception handling decision is about what to do with the **AQ session** when the ScalarDB transaction (or any other step) fails. The two options are:

| Action | Effect on AQ | When to Use |
|--------|-------------|-------------|
| `session.rollback()` | Message returns to queue, `retry_count++` | Failure is transient — retry may succeed |
| `session.commit()` | Message removed from queue permanently | Failure is permanent — retry will never succeed |

---

## Exception Classification

Every exception in the consumer pipeline falls into one of three categories.

### Category 1: RETRIABLE

Transient failures that are likely to succeed on retry. The correct action is `session.rollback()` so AQ redelivers the message.

**ScalarDB exceptions:**

| Exception | Thrown By | Cause |
|-----------|----------|-------|
| `CrudConflictException` | `get()`, `scan()`, `put()`, `delete()`, `upsert()`, `mutate()` | Another transaction touched the same row |
| `CommitConflictException` | `commit()` | Serialization conflict at commit time |
| `TransactionNotFoundException` | `begin()` | Transaction not found or expired |
| `CrudException` (base) | CRUD operations | May be transient (network) or non-transient (schema). Retry is reasonable; `max_retries` limits wasted attempts. |
| `CommitException` (base) | `commit()` | May be transient or non-transient. Same reasoning. |
| `TransactionException` (base) | `begin()` | Base class catch-all. Retry is the safest default. |

**Infrastructure exceptions:**

| Exception | Cause |
|-----------|-------|
| `java.net.SocketTimeoutException` | Network timeout to ScalarDB |
| `java.sql.SQLTransientConnectionException` | Temporary database connectivity loss |

### Category 2: NON-RETRIABLE

Permanent failures where the same message will produce the same error on every attempt. The correct action is `session.commit()` to remove the poison message, combined with logging for manual review.

**ScalarDB exceptions:**

| Exception | Thrown By | Cause |
|-----------|----------|-------|
| `UnsatisfiedConditionException` | `put()`, `delete()`, `mutate()` | Conditional mutation not met — business logic issue |

**Message parse exceptions (from `parseAdtMessage()`):**

| Exception | Cause |
|-----------|-------|
| `ClassCastException` | Payload attribute is not the expected type (e.g., `attrs[0]` is not `BigDecimal`) |
| `NullPointerException` | Required payload attribute is null |
| `ArrayIndexOutOfBoundsException` | Fewer attributes than expected — object type mismatch |
| `NumberFormatException` | String-to-number conversion failed in payload data |

**Application/routing exceptions:**

| Exception | Cause |
|-----------|-------|
| `IllegalArgumentException` | Unknown `operation_type` — consumer has no handler for this routing key |

### Category 3: UNKNOWN TRANSACTION STATE

A special case where ScalarDB cannot determine whether the commit succeeded.

| Exception | Thrown By | Cause |
|-----------|----------|-------|
| `UnknownTransactionStatusException` | `commit()` | Network failure during commit — data may or may not be written |

**Handling:** Call `session.commit()` to remove the message from the queue. Because the consumer uses `Upsert` (not `Insert`), if AQ were to redeliver this message, the upsert would overwrite with identical data — so removing it is safe. Log prominently so an operator can verify the ScalarDB state.

**Why not rollback?** If the ScalarDB commit actually succeeded, redelivery would cause a redundant (but harmless) upsert. If it failed, the data is lost. Neither outcome is ideal, but `session.commit()` + operator alert is safer than silent retry which masks the unknown state.

---

## ScalarDB Exception Hierarchy

The `instanceof` check order matters because of inheritance:

```
TransactionException
├── TransactionNotFoundException            → RETRIABLE
├── CrudException
│   ├── CrudConflictException               → RETRIABLE
│   └── UnsatisfiedConditionException       → NON_RETRIABLE
├── CommitException
│   ├── CommitConflictException             → RETRIABLE
│   └── UnknownTransactionStatusException   → UNKNOWN_TX_STATE
└── RollbackException                       → (internal, not classified)
```

Always check the most specific subclass first. If `TransactionException` is checked before `UnsatisfiedConditionException`, the non-retriable exception is misclassified as retriable.

---

## Implementation

### ExceptionClassifier

```java
import com.scalar.db.exception.transaction.*;

public final class ExceptionClassifier {

    public enum Verdict { RETRIABLE, NON_RETRIABLE, UNKNOWN_TX_STATE }

    private ExceptionClassifier() {}

    public static Verdict classify(Exception e) {
        // ScalarDB: definitely transient (most specific first)
        if (e instanceof CrudConflictException)         return Verdict.RETRIABLE;
        if (e instanceof CommitConflictException)        return Verdict.RETRIABLE;
        if (e instanceof TransactionNotFoundException)   return Verdict.RETRIABLE;

        // ScalarDB: unknown commit state
        if (e instanceof UnknownTransactionStatusException) return Verdict.UNKNOWN_TX_STATE;

        // ScalarDB: definitely non-retriable
        if (e instanceof UnsatisfiedConditionException)  return Verdict.NON_RETRIABLE;

        // ScalarDB: base classes (may be transient) — let max_retries decide
        if (e instanceof TransactionException)           return Verdict.RETRIABLE;

        // Parse/application: permanently broken data
        if (e instanceof ClassCastException)             return Verdict.NON_RETRIABLE;
        if (e instanceof NullPointerException)           return Verdict.NON_RETRIABLE;
        if (e instanceof ArrayIndexOutOfBoundsException) return Verdict.NON_RETRIABLE;
        if (e instanceof NumberFormatException)          return Verdict.NON_RETRIABLE;
        if (e instanceof IllegalArgumentException)       return Verdict.NON_RETRIABLE;

        // Default: assume transient, let max_retries be the safety net
        return Verdict.RETRIABLE;
    }
}
```

### Consumer Loop

Separate message parsing from message processing — they have different failure modes:

```java
while (!Thread.currentThread().isInterrupted()) {
    Message msg = receiver.receive(RECEIVE_TIMEOUT_MS);
    if (msg == null) continue;

    // PHASE 1: Parse — failure here means broken payload structure
    JobChangeMessage parsed;
    try {
        parsed = parseAdtMessage(msg);
    } catch (Exception e) {
        log.error("Parse failed (NON_RETRIABLE) — removing from queue: {}", e.getMessage(), e);
        session.commit();
        continue;
    }

    // PHASE 2: Process — classify the outcome
    try {
        writer.writeMessage(parsed);
        session.commit();

    } catch (Exception e) {
        switch (ExceptionClassifier.classify(e)) {
            case RETRIABLE -> {
                log.warn("Retriable failure: {} — rolling back for redelivery",
                        e.getClass().getSimpleName());
                session.rollback();
            }
            case NON_RETRIABLE -> {
                log.error("Non-retriable failure: {} — removing poison message",
                        e.getClass().getSimpleName(), e);
                session.commit();
            }
            case UNKNOWN_TX_STATE -> {
                log.error("Unknown TX state — removing from queue. VERIFY SCALARDB DATA. {}",
                        e.getMessage(), e);
                session.commit();
            }
        }
    }
}
```

### ScalarDbWriter — Preserve Exception Types

The writer must not wrap exceptions or call `tx.abort()` on unknown-state transactions:

```java
public void writeMessage(JobChangeMessage msg) throws Exception {
    DistributedTransaction tx = manager.begin();
    try {
        tx.upsert(/* ... build upsert ... */);
        tx.commit();

    } catch (UnknownTransactionStatusException e) {
        // DO NOT abort — TX may have committed successfully
        throw e;

    } catch (Exception e) {
        try { tx.abort(); } catch (RollbackException ignored) {}
        throw e;  // preserve original exception type for classifier
    }
}
```

---

## Interaction With Oracle AQ Retry Mechanics

From the Oracle AQ documentation (`DBMS_AQADM.CREATE_QUEUE`):

> RETRY_COUNT is incremented when the application issues a rollback after executing the dequeue. If a dequeue transaction fails because the server process dies (including ALTER SYSTEM KILL SESSION) or SHUTDOWN ABORT on the instance, then RETRY_COUNT is not incremented.

| Setting | Value | Purpose |
|---------|-------|---------|
| `max_retries` | 5 (recommended default) | Safety net — caps retries for failures the classifier deems retriable but that never recover |
| `retry_delay` | 0-5 seconds | Breathing room between attempts. 0 = immediate, useful for conflict-type retries. 5+ seconds useful for downstream outages. |

**With classification vs without:**

| Scenario | Without (current) | With classifier |
|----------|-------------------|-----------------|
| `CrudConflictException` (transient) | `rollback` → retries → succeeds | `rollback` → retries → succeeds (same) |
| Unknown `operation_type` (permanent) | `rollback` → 6 attempts → exception queue | `commit` → removed in 1 cycle |
| Corrupt payload (permanent) | `rollback` → 6 attempts → exception queue | `commit` → removed in 1 cycle |
| `UnknownTransactionStatusException` | `rollback` → redelivery → redundant upsert | `commit` → removed, operator alerted |
| Network timeout (transient) | `rollback` → retries → succeeds | `rollback` → retries → succeeds (same) |

---

## Summary

```
Exception occurs
       │
       ▼
  ┌─────────┐     YES     ┌──────────────────────┐
  │ Parsing │────────────→│ session.commit()      │  Remove poison message
  │ failed? │             │ Log error for review  │
  └────┬────┘             └──────────────────────┘
       │ NO
       ▼
  ┌──────────────┐
  │  Classify    │
  │  exception   │
  └──┬───┬───┬───┘
     │   │   │
     ▼   │   ▼
 RETRIABLE │  UNKNOWN_TX_STATE
     │     │        │
     ▼     │        ▼
 session   │    session.commit()
 .rollback │    Alert operator
     │     │
     ▼     ▼
 AQ retries  NON_RETRIABLE
 (capped by       │
  max_retries)    ▼
              session.commit()
              Log for review
```

---

*Version: 1.0*
*Based on: Oracle AQ (DBMS_AQ / DBMS_AQADM) + ScalarDB 3.17 Exception Handling API Guide*
