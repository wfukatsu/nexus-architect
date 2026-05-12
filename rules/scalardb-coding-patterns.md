# ScalarDB Coding Patterns

This file is a consolidated index for ScalarDB coding patterns. Each topic is covered in detail by its dedicated rule file.

## Rule Files

| Topic | File | When to Read |
|-------|------|--------------|
| CRUD API operations (Get, Scan, Insert, Upsert, Update, Delete) | @rules/scalardb-crud-patterns.md | Writing CRUD operations |
| JDBC/SQL operations (SELECT, INSERT, JOIN, aggregates) | @rules/scalardb-jdbc-patterns.md | Writing SQL-based operations |
| Exception handling and retry logic | @rules/scalardb-exception-handling.md | Catching and handling exceptions |
| Two-phase commit protocol | @rules/scalardb-2pc-patterns.md | Implementing 2PC across services |
| Java best practices (transaction lifecycle, threading, logging) | @rules/scalardb-java-best-practices.md | Writing Java application code |
| Schema design (partition keys, clustering keys, indexes) | @rules/scalardb-schema-design.md | Designing table schemas |
| Configuration validation (storage, cluster, contact points) | @rules/scalardb-config-validation.md | Writing configuration files |

## Quick Reference

### Transaction Lifecycle (CRUD API)

```java
DistributedTransaction tx = manager.begin();
try {
    // CRUD operations
    tx.commit();
} catch (CommitConflictException | CrudConflictException e) {
    tx.rollback();
    // retry
} catch (UnknownTransactionStatusException e) {
    // DO NOT rollback — status unknown
} catch (TransactionException e) {
    tx.rollback();
}
```

### Transaction Lifecycle (JDBC)

```java
connection.setAutoCommit(false);
try {
    // SQL operations
    connection.commit();
} catch (SQLException e) {
    if (e.getErrorCode() == 301) {
        // UnknownTransactionStatusException — DO NOT rollback
    } else {
        connection.rollback();
    }
}
```

### Key Rules

- Always catch `*ConflictException` **before** its parent `*Exception`
- Always call `commit()` even for read-only transactions
- Never rollback on `UnknownTransactionStatusException`
- Use builder pattern (`Get.newBuilder()...`) — never deprecated constructors
- Use `Insert`/`Upsert`/`Update` — never deprecated `Put`
