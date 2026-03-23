# Migration Strategy Guide: PostgreSQL Stored Procedures & Triggers to ScalarDB Application Layer

## Stored Procedures & Triggers: Not Currently Supported

Neither ScalarDB 3.16 nor 3.17 supports user-defined stored procedures or triggers as a feature. There is no documentation, API, or guidance on how to create, migrate, or use stored procedures and triggers within ScalarDB — whether through ScalarDB SQL, the Java API, or any other interface.

All stored procedure and trigger logic must be migrated to **application-layer Java code**.

---

## Migration Approach

This guide uses the **ScalarDB Java Transaction API** exclusively. All stored procedure and trigger logic is migrated to application-layer Java code using ScalarDB's Get/Scan/Insert/Update/Delete builder APIs with `DistributedTransaction` for ACID-compliant operations.

---

## ScalarDB Transaction API Constraints Affecting Stored Procedure Migration

Each limitation below directly shapes how the original stored procedure logic must be rewritten using the Transaction API.

| Feature | ScalarDB Transaction API Status | Migration Workaround |
|---------|--------------------------------|---------------------|
| Get / Scan / Insert / Update / Delete | Fully supported within transactions | Direct mapping using builder APIs |
| JOINs | Not available | Multiple `tx.get()` / `tx.scan()` calls + Java-side merging |
| Aggregation (SUM, COUNT, AVG) | Not available | `tx.scan()` + Java stream aggregation |
| Subqueries (nested SELECT) | Not available | Sequential `tx.scan()` + Java Set/filter |
| IF / CASE / COALESCE | Not in API | Read data with `tx.get()`, evaluate in Java, then write |
| Cursors (DECLARE CURSOR / FETCH) | Not available | `tx.scan()` + Java iteration |
| Sequences / SERIAL / BIGSERIAL | Not available | `UUID.randomUUID()` or counter table pattern |
| Stored Procedures / Triggers | Not supported | Application-layer methods using Transaction API (this document) |
| Cross-Partition Scan (non-PK WHERE) | Supported if enabled | `Scan.newBuilder().all()` with `.where()` filtering |

---

## Core ScalarDB Transaction API Pattern

All migrated stored procedure and trigger logic follows this foundational Transaction API pattern. Every example in this document is built on this template:

```java
DistributedTransactionManager manager = TransactionFactory.create(config)
    .getTransactionManager();

DistributedTransaction tx = manager.begin();
try {
    // Execute operations (Get / Scan / Insert / Update / Delete)
    Optional<Result> result = tx.get(getOp);
    tx.insert(insertOp);
    tx.update(updateOp);

    // Commit the transaction
    tx.commit();
} catch (CommitConflictException | CrudConflictException e) {
    tx.rollback();
    // Conflict: retry the whole transaction
} catch (UnknownTransactionStatusException e) {
    // Commit status unknown — do NOT retry blindly
} catch (TransactionException e) {
    if (tx != null) tx.rollback();
    throw e;
}
```

**Key Points:** `manager.begin()` starts a ScalarDB distributed transaction. All operations within that transaction are ACID-compliant. On `tx.commit()`, ScalarDB Consensus Commit ensures atomicity across all underlying databases.

---

## Trigger Types

PostgreSQL triggers use separate **trigger functions** — a trigger is created in two parts: first you define a function with `RETURNS TRIGGER`, then you attach it to a table with `CREATE TRIGGER`. The trigger function contains the logic and accesses `NEW` and `OLD` record variables. This is different from other databases where the trigger body is inline.

| # | Type | PostgreSQL Behavior |
|---|------|---------------------|
| 1 | BEFORE INSERT | Fires before row insert — defaults, ID gen, validation. Function can modify `NEW` record. |
| 2 | AFTER INSERT | Fires after insert — audit log, counters (same tx). `NEW` is read-only. |
| 3 | BEFORE UPDATE | Fires before update — validate `OLD` → `NEW` transitions. Function can modify `NEW`. |
| 4 | AFTER UPDATE | Fires after update — audit trail. Both `OLD` and `NEW` are read-only. |
| 5 | BEFORE DELETE | Fires before delete — check dependencies, archive. `OLD` is available. |
| 6 | AFTER DELETE | Fires after delete — cascade, audit, counter decrement. `OLD` is read-only. |
| 7 | INSTEAD OF | Replaces DML on a view — multi-table custom logic; the trigger defines what should happen when DML is attempted on a view, inserting/updating/deleting across multiple underlying tables with custom business rules. Only valid on views. |

> **Note:** PostgreSQL trigger functions are standalone `CREATE OR REPLACE FUNCTION` definitions with `RETURNS TRIGGER`. The function is then referenced by one or more `CREATE TRIGGER` statements. A single trigger function can be reused across multiple triggers and tables. When migrating, each trigger function maps to a Java method, and each `CREATE TRIGGER` attachment becomes a call site in the corresponding service method.

---

## Stored Procedure Types

| # | Type | Example |
|---|------|---------|
| 1 | Simple CRUD | Direct INSERT/UPDATE/DELETE on one table |
| 2 | Business logic | `calculate_order_total` — arithmetic + conditionals |
| 3 | Multi-table transaction | `fund_transfer` — writes across multiple tables |
| 4 | Cursor / batch processing | `process_pending_orders` — loop through rows |
| 5 | Aggregation | `monthly_summary` — SUM/COUNT/AVG |
| 6 | Subquery-based | Nested SELECT used to feed INTO or WHERE |

---

# SP/Trigger Features Needing Mapping

These are the PL/pgSQL constructs found inside stored procedures, functions, and triggers that need equivalent ScalarDB Java API patterns:

| # | Feature Category | PL/pgSQL Constructs |
|---|------------------|---------------------|
| 1 | Variables | DECLARE, :=, INTO, %TYPE, %ROWTYPE |
| 2 | Cursors | DECLARE CURSOR, OPEN, FETCH, CLOSE, FOR rec IN query LOOP |
| 3 | Control flow | IF/ELSIF/ELSE, WHILE, LOOP, FOR, CASE/WHEN, EXIT, CONTINUE |
| 4 | Exception handling | EXCEPTION WHEN condition THEN, RAISE EXCEPTION, RAISE NOTICE |
| 5 | OLD/NEW row access | OLD.column, NEW.column (trigger functions) |
| 6 | CRUD operations | SELECT, INSERT, UPDATE, DELETE, PERFORM |
| 7 | Conditional writes | INSERT ON CONFLICT, UPDATE ... WHERE condition |
| 8 | Subqueries | SELECT ... WHERE col IN (SELECT ...) |
| 9 | JOINs | INNER JOIN, LEFT JOIN |
| 10 | Aggregations | SUM, COUNT, AVG, MIN, MAX, GROUP BY |
| 11 | Functions | COALESCE, NULLIF, NOW(), gen_random_uuid(), string_agg() |
| 12 | Sequences | nextval('seq'), SERIAL, BIGSERIAL, currval() |
| 13 | Temp tables | CREATE TEMP TABLE, CREATE TEMPORARY TABLE |
| 14 | Dynamic SQL | EXECUTE format('...', var), EXECUTE '...' USING var |
| 15 | Output params | OUT parameters, RETURNS type, RETURNS TABLE, RETURNS SETOF |
| 16 | Transactions | BEGIN/COMMIT/ROLLBACK within procedure, SAVEPOINT |
| 17 | Batch operations | Multiple DML in one procedure call |

---

# Feature Mapping Summary

| Section | Feature | ScalarDB API (with Java) |
|---------|---------|--------------------------|
| 1 | Variables (DECLARE/:=/INTO) | Java variables + `tx.get()` → `result.getText()` |
| 2 | Cursors | `tx.scan()` + for loop, or `tx.getScanner()` for lazy |
| 3 | Control flow (IF/WHILE/CASE) | Plain Java — no API needed |
| 4 | Exception handling | ScalarDB exception types (`CrudConflictException`, etc.) |
| 5 | OLD/NEW row access | `tx.get()` = OLD, method params = NEW |
| 6 | CRUD operations | Get / Scan / Insert / Upsert / Update / Delete |
| 7 | Conditional writes | `ConditionBuilder.updateIf()` / `deleteIf()` on mutations |
| 8 | Subqueries | Sequential `tx.scan()` + Java Set/filter |
| 9 | JOINs | Multiple `tx.get()` / `tx.scan()` + Java merge |
| 10 | Aggregations | `tx.scan()` + Java stream (sum, collect, groupingBy) |
| 11 | SQL functions | Java equivalents (UUID, Instant, Math, String, Collectors.joining) |
| 12 | Sequences/SERIAL/BIGSERIAL | `UUID.randomUUID()` or counter table pattern |
| 13 | Temp tables | Java List / Map / Set |
| 14 | Dynamic SQL | Builder pattern — already dynamic and type-safe |
| 15 | Output params / RETURN | Java return values and result objects |
| 16 | Transactions in SP | `tx.begin()` / `tx.commit()` / `tx.rollback()` (no SAVEPOINT) |
| 17 | Batch operations | `tx.mutate(List)` or `tx.batch(List)` |

---

# Detailed Feature Mappings

## 2. Feature Mapping: Variables (DECLARE, :=, INTO)

**PL/pgSQL Constructs:** `DECLARE var type`, `var := value`, `SELECT ... INTO var`
**ScalarDB Mapping:** Standard Java variables. No API needed — use Java's type system directly.

### 2.1 DECLARE and Assignment

**PostgreSQL Stored Procedure:**
```sql
CREATE OR REPLACE FUNCTION create_order()
RETURNS void AS $$
DECLARE
    v_order_id VARCHAR(36);
    v_total NUMERIC(10,2);
    v_status VARCHAR(20);
BEGIN
    v_order_id := gen_random_uuid()::TEXT;
    v_total := 0.00;
    v_status := 'PENDING';
END;
$$ LANGUAGE plpgsql;
```

**ScalarDB Java API:**
```java
// Java variables replace DECLARE + :=
String orderId = UUID.randomUUID().toString();
double total = 0.00;
String status = "PENDING";
```

### 2.2 SELECT INTO

**PostgreSQL Stored Procedure:**
```sql
CREATE OR REPLACE FUNCTION get_account_info(p_acc_id VARCHAR)
RETURNS void AS $$
DECLARE
    v_balance NUMERIC(10,2);
    v_name VARCHAR(100);
BEGIN
    SELECT balance, name INTO v_balance, v_name
    FROM accounts WHERE account_id = p_acc_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Account not found: %', p_acc_id;
    END IF;
END;
$$ LANGUAGE plpgsql;
```

**ScalarDB Java API:**
```java
// Build a Get operation for the primary key
Key partitionKey = Key.ofText("account_id", accId);

Get get = Get.newBuilder()
    .namespace("ns")
    .table("accounts")
    .partitionKey(partitionKey)
    .projections("balance", "name")
    .build();

Optional<Result> result = tx.get(get);
if (!result.isPresent()) {
    throw new NotFoundException("Account not found: " + accId);
}

// SELECT INTO equivalent: read columns into Java variables
double balance = result.get().getDouble("balance");
String name = result.get().getText("name");
```

> **Note:** Get always requires a full primary key (partition key + clustering key if defined). You cannot Get by arbitrary WHERE clauses — use Scan for that.

---

## 3. Feature Mapping: Cursors (DECLARE CURSOR, FETCH, FOR ... LOOP)

**PL/pgSQL Constructs:** `DECLARE CURSOR`, `OPEN`, `FETCH`, `CLOSE`, `FOR rec IN query LOOP`
**ScalarDB Mapping:** `Scan` + `List<Result>` iteration, or `Scan` + `Scanner` for lazy iteration.

### 3.1 Simple Cursor (all rows in partition)

**PostgreSQL Stored Procedure:**
```sql
CREATE OR REPLACE FUNCTION process_orders(p_cust_id VARCHAR)
RETURNS void AS $$
DECLARE
    order_cursor CURSOR FOR
        SELECT order_id, total_amount FROM orders
        WHERE customer_id = p_cust_id;
    v_oid VARCHAR(36);
    v_amt NUMERIC(10,2);
BEGIN
    OPEN order_cursor;
    LOOP
        FETCH order_cursor INTO v_oid, v_amt;
        EXIT WHEN NOT FOUND;
        -- process each row
        UPDATE orders SET processed = 1 WHERE order_id = v_oid;
    END LOOP;
    CLOSE order_cursor;
END;
$$ LANGUAGE plpgsql;
```

**ScalarDB Java API (Scan + List):**
```java
// Build Scan for the partition
Key partitionKey = Key.ofText("customer_id", custId);

Scan scan = Scan.newBuilder()
    .namespace("ns")
    .table("orders")
    .partitionKey(partitionKey)
    .projections("order_id", "total_amount")
    .build();

// Execute scan (replaces OPEN + FETCH ALL)
List<Result> results = tx.scan(scan);

// Iterate (replaces FETCH + LOOP)
for (Result row : results) {
    String oid = row.getText("order_id");
    double amt = row.getDouble("total_amount");

    // Process each row (replaces cursor body)
    Key pk = Key.ofText("order_id", oid);
    Update update = Update.newBuilder()
        .namespace("ns")
        .table("orders")
        .partitionKey(Key.ofText("customer_id", custId))
        .clusteringKey(pk)
        .intValue("processed", 1)
        .build();
    tx.update(update);
}
// No CLOSE needed
```

### 3.2 FOR ... IN Query LOOP (PL/pgSQL shorthand)

**PostgreSQL Stored Procedure:**
```sql
CREATE OR REPLACE FUNCTION process_orders_v2(p_cust_id VARCHAR)
RETURNS void AS $$
DECLARE
    rec RECORD;
BEGIN
    FOR rec IN SELECT order_id, total_amount FROM orders
               WHERE customer_id = p_cust_id
    LOOP
        UPDATE orders SET processed = 1 WHERE order_id = rec.order_id;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
```

**ScalarDB Java API (same as cursor — Scan + List):**
```java
// PL/pgSQL FOR ... IN ... LOOP maps identically to Scan + for-each
List<Result> results = tx.scan(scan);
for (Result row : results) {
    String oid = row.getText("order_id");
    // ... process row ...
}
```

### 3.3 Lazy Cursor (large result sets)

**ScalarDB Java API (Scanner for lazy iteration):**
```java
// Use getScanner() for large result sets to avoid OOM
try (TransactionCrudOperable.Scanner scanner = tx.getScanner(scan)) {
    Optional<Result> row;
    while ((row = scanner.one()).isPresent()) {
        String oid = row.get().getText("order_id");
        // ... process row ...
    }
}
```

> **Note:** Large batch updates within a single transaction may hit ScalarDB transaction timeout limits. For very large batches, use a progress table with LIMIT and process in chunks across separate transactions.

---

## 4. Feature Mapping: Control Flow (IF/ELSIF/ELSE, WHILE, CASE)

**PL/pgSQL Constructs:** `IF/ELSIF/ELSE`, `WHILE`, `LOOP`, `FOR`, `CASE/WHEN`, `EXIT`, `CONTINUE`
**ScalarDB Mapping:** Standard Java control flow. No special API needed.

### 4.1 IF/ELSIF/ELSE

**PostgreSQL:**
```sql
CREATE OR REPLACE FUNCTION update_account(p_id VARCHAR, p_amount NUMERIC)
RETURNS void AS $$
DECLARE
    v_status VARCHAR(20);
BEGIN
    SELECT status INTO v_status FROM accounts WHERE id = p_id;

    IF v_status = 'ACTIVE' THEN
        UPDATE accounts SET balance = balance + p_amount WHERE id = p_id;
    ELSIF v_status = 'SUSPENDED' THEN
        RAISE NOTICE 'Account % is suspended', p_id;
    ELSE
        RAISE EXCEPTION 'Account inactive: %', p_id;
    END IF;
END;
$$ LANGUAGE plpgsql;
```

**ScalarDB Java API:**
```java
// Read current state with Get
Optional<Result> result = tx.get(getAccount);
String status = result.get().getText("status");

if ("ACTIVE".equals(status)) {
    double currentBalance = result.get().getDouble("balance");
    Update update = Update.newBuilder()
        .namespace("ns").table("accounts")
        .partitionKey(Key.ofText("id", id))
        .doubleValue("balance", currentBalance + amount)
        .build();
    tx.update(update);
} else if ("SUSPENDED".equals(status)) {
    log.info("Account {} is suspended", id);
} else {
    throw new BusinessException("Account inactive: " + id);
}
```

### 4.2 WHILE Loop

**PostgreSQL:**
```sql
CREATE OR REPLACE FUNCTION insert_batch(p_batch_id VARCHAR)
RETURNS void AS $$
DECLARE
    v_i INTEGER := 1;
BEGIN
    WHILE v_i <= 10 LOOP
        INSERT INTO batch_items(seq, batch_id) VALUES (v_i, p_batch_id);
        v_i := v_i + 1;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
```

**ScalarDB Java API:**
```java
for (int i = 1; i <= 10; i++) {
    Insert insert = Insert.newBuilder()
        .namespace("ns").table("batch_items")
        .partitionKey(Key.ofText("batch_id", batchId))
        .clusteringKey(Key.ofInt("seq", i))
        .build();
    tx.insert(insert);
}
```

### 4.3 CASE/WHEN

**PostgreSQL:**
```sql
CREATE OR REPLACE FUNCTION get_discount(p_tier VARCHAR)
RETURNS NUMERIC AS $$
DECLARE
    v_discount NUMERIC(5,2);
BEGIN
    v_discount := CASE
        WHEN p_tier = 'GOLD' THEN 0.20
        WHEN p_tier = 'SILVER' THEN 0.10
        ELSE 0.00
    END;
    RETURN v_discount;
END;
$$ LANGUAGE plpgsql;
```

**ScalarDB Java API:**
```java
double discount;
switch (tier) {
    case "GOLD":   discount = 0.20; break;
    case "SILVER": discount = 0.10; break;
    default:       discount = 0.00; break;
}
```

---

## 5. Feature Mapping: Exception Handling

**PL/pgSQL Constructs:** `EXCEPTION WHEN condition THEN`, `RAISE EXCEPTION`, `RAISE NOTICE`, `RAISE WARNING`
**ScalarDB Mapping:** Java try/catch with ScalarDB-specific exception types.

### 5.1 Exception Type Mapping

| PL/pgSQL Construct | ScalarDB Exception | Handling |
|-------------------|-------------------|----------|
| `RAISE EXCEPTION 'message'` | `throw new BusinessException(...)` | Custom exception for validation failures |
| `RAISE EXCEPTION USING ERRCODE = 'P0001'` | `throw new BusinessException(...)` | Custom exception for business rule violations |
| `EXCEPTION WHEN unique_violation` | `CrudConflictException` | Retry or use Upsert instead of Insert |
| `EXCEPTION WHEN foreign_key_violation` | `throw new BusinessException(...)` | Validate references with `tx.get()` before write |
| `EXCEPTION WHEN check_violation` | `throw new BusinessException(...)` | Validate constraints in Java before write |
| `EXCEPTION WHEN not_null_violation` | `throw new IllegalArgumentException(...)` | Validate required fields in Java |
| `EXCEPTION WHEN deadlock_detected` | `CrudConflictException` | Retry the entire transaction from `begin()` |
| `EXCEPTION WHEN serialization_failure` | `CommitConflictException` | Retry from `begin()` for conflict |
| Commit failure | `CommitException` / `CommitConflictException` | Retry from `begin()` for conflict; investigate for others |
| Unknown commit state | `UnknownTransactionStatusException` | Check tx status externally; decide retry |
| `NOT FOUND` (after SELECT INTO) | `Optional.empty()` / empty List | Check `result.isPresent()` or `results.isEmpty()` |
| `RAISE NOTICE 'message'` | `log.info(...)` | Use SLF4J or java.util.logging |
| `EXCEPTION WHEN OTHERS THEN` | `catch (TransactionException e)` | Catch-all; always rollback before retry or throw |

### 5.2 Full Exception Handling Pattern

**PostgreSQL:**
```sql
CREATE OR REPLACE FUNCTION safe_transfer(p_from VARCHAR, p_to VARCHAR, p_amount NUMERIC)
RETURNS void AS $$
BEGIN
    UPDATE accounts SET balance = balance - p_amount WHERE id = p_from;
    UPDATE accounts SET balance = balance + p_amount WHERE id = p_to;
EXCEPTION
    WHEN check_violation THEN
        RAISE EXCEPTION 'Insufficient funds for account %', p_from;
    WHEN serialization_failure THEN
        RAISE EXCEPTION 'Transaction conflict, please retry';
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Unexpected error: %', SQLERRM;
END;
$$ LANGUAGE plpgsql;
```

**ScalarDB Java API:**
```java
try {
    tx = manager.begin();

    // ... SP logic ...

    tx.commit();
} catch (UnsatisfiedConditionException e) {
    // Conditional write (putIf/deleteIf/updateIf) failed
    tx.rollback();
    // Handle: condition not met (e.g., balance < 0)
} catch (UnknownTransactionStatusException e) {
    // Commit status unknown - DO NOT retry blindly
    // Check if committed, then decide
} catch (CommitConflictException | CrudConflictException e) {
    tx.rollback();
    // Conflict: retry the whole transaction
} catch (TransactionException e) {
    if (tx != null) tx.rollback();
    // Other error: may retry, but might be non-transient
}
```

---

## 6. Feature Mapping: OLD/NEW Row Access (Triggers)

**PL/pgSQL Constructs:** `OLD.column`, `NEW.column` (in trigger function body), `RETURN NEW`, `RETURN OLD`
**ScalarDB Mapping:** `Get` (read current row = OLD), Java method parameters = NEW values.

### 6.1 Pattern

**PostgreSQL Trigger Function:**
```sql
CREATE OR REPLACE FUNCTION trg_before_update_order()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status = 'CANCELLED' THEN
        RAISE EXCEPTION 'Cannot update cancelled order';
    END IF;

    IF NOT is_valid_transition(OLD.status, NEW.status) THEN
        RAISE EXCEPTION 'Invalid transition: % -> %', OLD.status, NEW.status;
    END IF;

    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER order_before_update
    BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION trg_before_update_order();
```

**ScalarDB Java API:**
```java
// OLD values: Read the current record with Get
Get get = Get.newBuilder()
    .namespace("ns").table("orders")
    .partitionKey(Key.ofText("order_id", orderId))
    .build();

Optional<Result> old = tx.get(get);
String oldStatus = old.get().getText("status");        // OLD.status
double oldAmount = old.get().getDouble("total_amount"); // OLD.total_amount

// NEW values: come from method parameters
String newStatus = request.getStatus();    // NEW.status
double newAmount = request.getAmount();    // NEW.total_amount

// BEFORE UPDATE validation using OLD + NEW
if ("CANCELLED".equals(oldStatus)) {
    throw new BusinessException("Cannot update cancelled order");
}
if (!isValidTransition(oldStatus, newStatus)) {
    throw new BusinessException("Invalid: " + oldStatus + " -> " + newStatus);
}

// Execute the UPDATE with NEW values
Update update = Update.newBuilder()
    .namespace("ns").table("orders")
    .partitionKey(Key.ofText("order_id", orderId))
    .textValue("status", newStatus)
    .doubleValue("total_amount", newAmount)
    .bigIntValue("updated_at", System.currentTimeMillis())
    .build();
tx.update(update);

// AFTER UPDATE: audit using both OLD and NEW
Insert audit = Insert.newBuilder()
    .namespace("ns").table("order_audit")
    .partitionKey(Key.ofText("order_id", orderId))
    .clusteringKey(Key.ofText("audit_id", UUID.randomUUID().toString()))
    .textValue("old_status", oldStatus)
    .textValue("new_status", newStatus)
    .textValue("changed_by", currentUser)
    .bigIntValue("changed_at", System.currentTimeMillis())
    .build();
tx.insert(audit);
```

> **Key insight:** ScalarDB Consensus Commit already requires a read before write for conflict detection. So this Get (for OLD values) is not extra overhead — it's naturally required.

---

## 7. Feature Mapping: CRUD Operations

**PL/pgSQL Constructs:** `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `PERFORM`
**ScalarDB Mapping:** `Get`/`Scan` for reads, `Insert`/`Upsert`/`Update`/`Delete` for writes. PL/pgSQL `PERFORM` (execute a query and discard the result) maps to a void Java method call.

### 7.1 SELECT → Get (single row by PK)

```java
// SQL: SELECT * FROM orders WHERE order_id = 'ORD001'

Get get = Get.newBuilder()
    .namespace("ns").table("orders")
    .partitionKey(Key.ofText("order_id", "ORD001"))
    .build();
Optional<Result> result = tx.get(get);
```

### 7.2 SELECT with range → Scan

```java
// SQL: SELECT * FROM orders WHERE customer_id = 'C001'
//      AND order_date >= '2025-01-01' AND order_date < '2025-02-01'
//      ORDER BY order_date DESC LIMIT 10

Scan scan = Scan.newBuilder()
    .namespace("ns").table("orders")
    .partitionKey(Key.ofText("customer_id", "C001"))
    .start(Key.ofBigInt("order_date", startTs), true)
    .end(Key.ofBigInt("order_date", endTs), false)
    .orderings(Scan.Ordering.desc("order_date"))
    .limit(10)
    .build();
List<Result> results = tx.scan(scan);
```

### 7.3 SELECT across all partitions → Cross-partition Scan

```java
// SQL: SELECT * FROM orders WHERE status = 'PENDING'
// Requires: scalar.db.cross_partition_scan.enabled=true
//           scalar.db.cross_partition_scan.filtering.enabled=true

Scan scan = Scan.newBuilder()
    .namespace("ns").table("orders")
    .all()  // cross-partition scan
    .where(ConditionBuilder.column("status").isEqualToText("PENDING"))
    .limit(100)
    .build();
List<Result> results = tx.scan(scan);
```

### 7.4 INSERT → Insert

```java
// SQL: INSERT INTO orders (order_id, customer_id, status, total)
//      VALUES ('ORD001', 'C001', 'PENDING', 99.50)

Insert insert = Insert.newBuilder()
    .namespace("ns").table("orders")
    .partitionKey(Key.ofText("order_id", "ORD001"))
    .textValue("customer_id", "C001")
    .textValue("status", "PENDING")
    .doubleValue("total", 99.50)
    .build();
tx.insert(insert);  // Throws if record already exists
```

### 7.5 INSERT OR UPDATE → Upsert

```java
// SQL: INSERT INTO orders (...) VALUES (...)
//      ON CONFLICT (order_id) DO UPDATE SET status = EXCLUDED.status, total = EXCLUDED.total

Upsert upsert = Upsert.newBuilder()
    .namespace("ns").table("orders")
    .partitionKey(Key.ofText("order_id", "ORD001"))
    .textValue("status", "CONFIRMED")
    .doubleValue("total", 109.50)
    .build();
tx.upsert(upsert);  // Inserts if absent, updates if exists
```

### 7.6 UPDATE → Update

```java
// SQL: UPDATE orders SET status = 'SHIPPED' WHERE order_id = 'ORD001'

Update update = Update.newBuilder()
    .namespace("ns").table("orders")
    .partitionKey(Key.ofText("order_id", "ORD001"))
    .textValue("status", "SHIPPED")
    .build();
tx.update(update);  // No-op if record does not exist
```

### 7.7 DELETE → Delete

```java
// SQL: DELETE FROM orders WHERE order_id = 'ORD001'

Delete delete = Delete.newBuilder()
    .namespace("ns").table("orders")
    .partitionKey(Key.ofText("order_id", "ORD001"))
    .build();
tx.delete(delete);
// Note: No need to read before delete (implicit pre-read enabled)
```

### 7.8 PERFORM → Void Method Call

**PostgreSQL:**
```sql
-- PERFORM discards the result of a query or function call
PERFORM notify_customer(v_customer_id);
PERFORM pg_notify('order_channel', v_order_id);
```

**ScalarDB Java API:**
```java
// PERFORM maps to a void method call
notifyCustomer(tx, customerId);
// Note: pg_notify and similar PostgreSQL-specific functions
// must be replaced with application-layer messaging
```

---

## 8. Feature Mapping: Conditional Writes

**PL/pgSQL Constructs:** `INSERT ... ON CONFLICT`, `UPDATE ... WHERE condition`, `DELETE ... WHERE condition`
**ScalarDB Mapping:** `MutationCondition` with `ConditionBuilder` on Update/Delete operations.

### 8.1 UPDATE only if condition is met

**PostgreSQL:**
```sql
CREATE OR REPLACE FUNCTION withdraw(p_account_id VARCHAR, p_amount NUMERIC)
RETURNS void AS $$
DECLARE
    v_rows INTEGER;
BEGIN
    UPDATE accounts SET balance = balance - p_amount
    WHERE account_id = p_account_id AND balance >= p_amount;

    GET DIAGNOSTICS v_rows = ROW_COUNT;
    IF v_rows = 0 THEN
        RAISE EXCEPTION 'Insufficient funds';
    END IF;
END;
$$ LANGUAGE plpgsql;
```

**ScalarDB Java API (ConditionBuilder):**
```java
// Read current balance
Optional<Result> r = tx.get(getAccount);
double balance = r.get().getDouble("balance");

// Build conditional update
MutationCondition condition = ConditionBuilder
    .updateIf(
        ConditionBuilder.column("balance")
            .isGreaterThanOrEqualToDouble(100.0))
    .build();

Update update = Update.newBuilder()
    .namespace("ns").table("accounts")
    .partitionKey(Key.ofText("account_id", "A001"))
    .doubleValue("balance", balance - 100.0)
    .condition(condition)
    .build();

try {
    tx.update(update);
} catch (UnsatisfiedConditionException e) {
    throw new BusinessException("Insufficient funds");
}
```

### 8.2 DELETE only if condition is met

```java
// SQL: DELETE FROM orders WHERE order_id = 'X' AND status = 'DRAFT'

MutationCondition condition = ConditionBuilder
    .deleteIf(ConditionBuilder.column("status").isEqualToText("DRAFT"))
    .build();

Delete delete = Delete.newBuilder()
    .namespace("ns").table("orders")
    .partitionKey(Key.ofText("order_id", "X"))
    .condition(condition)
    .build();

try {
    tx.delete(delete);
} catch (UnsatisfiedConditionException e) {
    throw new BusinessException("Can only delete DRAFT orders");
}
```

### 8.3 Insert only if not exist

**PostgreSQL:**
```sql
INSERT INTO orders (order_id, status) VALUES ('ORD001', 'PENDING')
ON CONFLICT (order_id) DO NOTHING;
```

**ScalarDB Java API:**
```java
// Use Insert (not Upsert) -- it errors if record exists
try {
    tx.insert(insertOp);  // Throws CrudConflictException if exists
} catch (CrudConflictException e) {
    throw new BusinessException("Record already exists");
}
```

---

## 9. Feature Mapping: Subqueries

**PL/pgSQL Constructs:** `SELECT ... WHERE col IN (SELECT ...)`, correlated subqueries, `EXISTS`
**ScalarDB Mapping:** Sequential operations. First query → Java collection → use results in second query.

### 9.1 IN Subquery

**PostgreSQL:**
```sql
SELECT * FROM orders
WHERE customer_id IN (
    SELECT customer_id FROM premium_customers WHERE tier = 'GOLD'
);
```

**ScalarDB Java API:**
```java
// Step 1: Execute the inner query
Scan innerScan = Scan.newBuilder()
    .namespace("ns").table("premium_customers")
    .all()  // cross-partition scan
    .where(ConditionBuilder.column("tier").isEqualToText("GOLD"))
    .projections("customer_id")
    .build();
List<Result> goldCustomers = tx.scan(innerScan);

// Step 2: Collect IDs into a Java Set
Set<String> goldIds = goldCustomers.stream()
    .map(r -> r.getText("customer_id"))
    .collect(Collectors.toSet());

// Step 3: Scan orders and filter by collected IDs
Scan orderScan = Scan.newBuilder()
    .namespace("ns").table("orders")
    .all()
    .build();
List<Result> orders = tx.scan(orderScan);

List<Result> filtered = orders.stream()
    .filter(r -> goldIds.contains(r.getText("customer_id")))
    .collect(Collectors.toList());
```

> **Note:** Cross-partition scans can be expensive. If the partition key structure allows, prefer multiple targeted Scans over one cross-partition scan.

---

## 10. Feature Mapping: JOINs

**PL/pgSQL Constructs:** `INNER JOIN`, `LEFT JOIN`, `RIGHT JOIN`
**ScalarDB Mapping:** Multiple Get/Scan operations with Java-side merging.

### 10.1 INNER JOIN → Get + Get

**PostgreSQL:**
```sql
SELECT o.order_id, o.total, c.name, c.email
FROM orders o INNER JOIN customers c
ON o.customer_id = c.customer_id
WHERE o.order_id = 'ORD001';
```

**ScalarDB Java API:**
```java
// Get order
Get getOrder = Get.newBuilder()
    .namespace("ns").table("orders")
    .partitionKey(Key.ofText("order_id", "ORD001"))
    .projections("order_id", "total", "customer_id")
    .build();
Result order = tx.get(getOrder).orElseThrow();
String custId = order.getText("customer_id");

// Get customer (the JOIN)
Get getCustomer = Get.newBuilder()
    .namespace("ns").table("customers")
    .partitionKey(Key.ofText("customer_id", custId))
    .projections("name", "email")
    .build();
Result customer = tx.get(getCustomer).orElseThrow();

// Now you have both sides of the JOIN in Java variables
String orderId = order.getText("order_id");
double total = order.getDouble("total");
String name = customer.getText("name");
String email = customer.getText("email");
```

### 10.2 LEFT JOIN → Get with Optional check

```java
// LEFT JOIN: customer may not exist
Optional<Result> customerOpt = tx.get(getCustomer);
String name = customerOpt.isPresent()
    ? customerOpt.get().getText("name")
    : null;  // LEFT JOIN: null when no match
```

### 10.3 Scan + Scan JOIN (batch)

```java
// For joining multiple orders with customers
List<Result> orders = tx.scan(scanOrders);

// Build a map for customers (avoids N+1 Get calls)
Map<String, Result> customerMap = new HashMap<>();
for (Result o : orders) {
    String cid = o.getText("customer_id");
    if (!customerMap.containsKey(cid)) {
        tx.get(Get.newBuilder()
            .namespace("ns").table("customers")
            .partitionKey(Key.ofText("customer_id", cid))
            .build())
        .ifPresent(r -> customerMap.put(cid, r));
    }
}

// Now merge
for (Result o : orders) {
    Result c = customerMap.get(o.getText("customer_id"));
    // Use o and c together
}
```

---

## 11. Feature Mapping: Aggregations

**PL/pgSQL Constructs:** `SUM`, `COUNT`, `AVG`, `MIN`, `MAX`, `GROUP BY`, `HAVING`, `string_agg()`
**ScalarDB Mapping:** `Scan` + Java-side aggregation. No built-in aggregation functions in the Java Transaction API.

### 11.1 COUNT

```java
// SQL: SELECT COUNT(*) FROM orders WHERE customer_id = 'C001'

List<Result> results = tx.scan(Scan.newBuilder()
    .namespace("ns").table("orders")
    .partitionKey(Key.ofText("customer_id", "C001"))
    .build());

int count = results.size();
```

### 11.2 SUM / AVG

```java
// SQL: SELECT SUM(total_amount), AVG(total_amount)
//      FROM orders WHERE customer_id = 'C001'

List<Result> results = tx.scan(scanOrders);

double sum = results.stream()
    .mapToDouble(r -> r.getDouble("total_amount"))
    .sum();

double avg = results.stream()
    .mapToDouble(r -> r.getDouble("total_amount"))
    .average()
    .orElse(0.0);
```

### 11.3 GROUP BY with aggregation

```java
// SQL: SELECT status, COUNT(*), SUM(total)
//      FROM orders GROUP BY status

List<Result> allOrders = tx.scan(scanAllOrders);

Map<String, DoubleSummaryStatistics> grouped = allOrders.stream()
    .collect(Collectors.groupingBy(
        r -> r.getText("status"),
        Collectors.summarizingDouble(r -> r.getDouble("total"))
    ));

for (Map.Entry<String, DoubleSummaryStatistics> entry : grouped.entrySet()) {
    String status = entry.getKey();
    long count = entry.getValue().getCount();
    double sum = entry.getValue().getSum();
}
```

### 11.4 string_agg() → Collectors.joining()

**PostgreSQL:**
```sql
SELECT customer_id, string_agg(order_id, ', ' ORDER BY order_date)
FROM orders GROUP BY customer_id;
```

**ScalarDB Java API:**
```java
// string_agg() maps to Collectors.joining()
List<Result> allOrders = tx.scan(scanAllOrders);

Map<String, String> aggregated = allOrders.stream()
    .collect(Collectors.groupingBy(
        r -> r.getText("customer_id"),
        Collectors.mapping(
            r -> r.getText("order_id"),
            Collectors.joining(", ")
        )
    ));
```

> **Note:** For high-volume tables, Java-side aggregation loads all matching rows into memory. Consider maintaining pre-computed counter/summary tables updated within the same transaction.

---

## 12. Feature Mapping: SQL Functions

**PL/pgSQL Constructs:** `COALESCE`, `NULLIF`, `NOW()`, `gen_random_uuid()`, `CONCAT`, `UPPER`, `string_agg()`, etc.
**ScalarDB Mapping:** Java equivalents. No SQL functions available in the Java Transaction API.

| PostgreSQL Function | Java Equivalent | Notes |
|---------------------|-----------------|-------|
| `gen_random_uuid()` | `UUID.randomUUID().toString()` | Use as partition/clustering key value |
| `NOW()` / `CURRENT_TIMESTAMP` | `System.currentTimeMillis()` or `Instant.now()` | Store as BIGINT (epoch ms) or TIMESTAMPTZ |
| `COALESCE(a, b)` | `a != null ? a : b` (or `Objects.requireNonNullElse`) | Check with `result.isNull("col")` |
| `NULLIF(a, b)` | `a.equals(b) ? null : a` | Use before setting value in builder |
| `CONCAT(a, b)` / `a \|\| b` | `a + b` or `String.join()` | Concatenate in Java before storing |
| `UPPER()` / `LOWER()` | `str.toUpperCase()` / `str.toLowerCase()` | Transform in Java before storing |
| `ROUND(n, d)` | `Math.round()` or `BigDecimal.setScale()` | Use BigDecimal for financial precision |
| `ABS(n)` | `Math.abs(n)` | Standard math operation |
| `AGE()` / `DATE_PART()` | `ChronoUnit.DAYS.between()` / `LocalDate.plusDays()` | Use java.time API for date arithmetic |
| `SUBSTRING(s FROM start FOR len)` | `str.substring(start - 1, start - 1 + len)` | Java is 0-indexed, PostgreSQL is 1-indexed |
| `string_agg(col, delim)` | `Collectors.joining(delim)` | Java stream collector for string aggregation |
| `array_agg(col)` | `Collectors.toList()` | Collect into Java List |

---

## 13. Feature Mapping: Sequences / SERIAL / BIGSERIAL

**PL/pgSQL Constructs:** `nextval('sequence_name')`, `currval('sequence_name')`, `SERIAL`, `BIGSERIAL`, `GENERATED ALWAYS AS IDENTITY`
**ScalarDB Mapping:** UUID generation OR counter table pattern.

### 13.1 UUID (preferred)

**PostgreSQL:**
```sql
CREATE OR REPLACE FUNCTION create_order(p_status VARCHAR)
RETURNS void AS $$
DECLARE
    v_id VARCHAR(36);
BEGIN
    v_id := gen_random_uuid()::TEXT;
    INSERT INTO orders (order_id, status) VALUES (v_id, p_status);
END;
$$ LANGUAGE plpgsql;
```

**ScalarDB Java API:**
```java
// Best approach for distributed IDs
String id = UUID.randomUUID().toString();

Insert insert = Insert.newBuilder()
    .namespace("ns").table("orders")
    .partitionKey(Key.ofText("order_id", id))
    .textValue("status", "PENDING")
    .build();
tx.insert(insert);
```

### 13.2 Counter Table (when sequential IDs are required)

**PostgreSQL (original using sequences):**
```sql
-- Using a sequence
SELECT nextval('orders_id_seq') INTO v_next_id;
INSERT INTO orders (order_id, status) VALUES (v_next_id, 'PENDING');

-- Or using SERIAL/BIGSERIAL column
CREATE TABLE orders (
    order_id BIGSERIAL PRIMARY KEY,
    status VARCHAR(20)
);
-- ID auto-assigned on INSERT
```

**ScalarDB Java API:**
```java
// Read current counter value
Get getCounter = Get.newBuilder()
    .namespace("ns").table("id_counters")
    .partitionKey(Key.ofText("table_name", "orders"))
    .build();
Optional<Result> counterResult = tx.get(getCounter);

long nextId;
if (counterResult.isPresent()) {
    nextId = counterResult.get().getBigInt("current_value") + 1;
    Update updateCounter = Update.newBuilder()
        .namespace("ns").table("id_counters")
        .partitionKey(Key.ofText("table_name", "orders"))
        .bigIntValue("current_value", nextId)
        .build();
    tx.update(updateCounter);
} else {
    nextId = 1;
    Insert insertCounter = Insert.newBuilder()
        .namespace("ns").table("id_counters")
        .partitionKey(Key.ofText("table_name", "orders"))
        .bigIntValue("current_value", nextId)
        .build();
    tx.insert(insertCounter);
}
```

> **Warning:** Counter tables create a hot partition and will cause frequent transaction conflicts under concurrent writes. Use UUID unless sequential IDs are an absolute requirement. If you must use counters, partition by shard key (e.g., region + counter) to reduce contention. Note that `currval()` has no equivalent — the counter value is already available in the `nextId` variable.

---

## 14. Feature Mapping: Temporary Tables

**PL/pgSQL Constructs:** `CREATE TEMP TABLE`, `CREATE TEMPORARY TABLE`, `ON COMMIT DROP`
**ScalarDB Mapping:** Java collections (List, Map, Set) as in-memory working storage.

### 14.1 Temp Table → Java Collection

**PostgreSQL:**
```sql
CREATE OR REPLACE FUNCTION process_pending()
RETURNS void AS $$
BEGIN
    CREATE TEMP TABLE tmp_pending ON COMMIT DROP AS
        SELECT order_id, total FROM orders WHERE status = 'PENDING';

    -- Use tmp_pending in subsequent queries
    UPDATE orders SET status = 'PROCESSING'
    WHERE order_id IN (SELECT order_id FROM tmp_pending);
END;
$$ LANGUAGE plpgsql;
```

**ScalarDB Java API:**
```java
// Java List replaces temp table
List<Result> pendingOrders = tx.scan(Scan.newBuilder()
    .namespace("ns").table("orders")
    .all()
    .where(ConditionBuilder.column("status").isEqualToText("PENDING"))
    .build());

// Work with the results like a temp table
for (Result order : pendingOrders) {
    String orderId = order.getText("order_id");
    double total = order.getDouble("total");
    // ... use in subsequent operations ...
}

// Or build a lookup Map (like indexed temp table)
Map<String, Result> orderMap = pendingOrders.stream()
    .collect(Collectors.toMap(
        r -> r.getText("order_id"), r -> r));
```

---

## 15. Feature Mapping: Dynamic SQL

**PL/pgSQL Constructs:** `EXECUTE format('...', var)`, `EXECUTE '...' USING var`, `EXECUTE sql_string`
**ScalarDB Mapping:** Programmatic operation builder. The Java API is already dynamic — you build operations in code.

### 15.1 Dynamic Table/Column Selection

**PostgreSQL:**
```sql
CREATE OR REPLACE FUNCTION dynamic_lookup(
    p_table_name VARCHAR, p_col_name VARCHAR, p_id VARCHAR
)
RETURNS TEXT AS $$
DECLARE
    v_result TEXT;
BEGIN
    EXECUTE format('SELECT %I FROM %I WHERE id = $1', p_col_name, p_table_name)
    INTO v_result
    USING p_id;
    RETURN v_result;
END;
$$ LANGUAGE plpgsql;
```

**ScalarDB Java API:**
```java
// The builder pattern IS dynamic SQL
Get.Builder builder = Get.newBuilder()
    .namespace("ns")
    .table(tableName)         // variable table name
    .partitionKey(Key.ofText("id", id));

// Dynamic column projection
if (colName != null) {
    builder.projections(colName);  // variable column name
}

Get get = builder.build();
Optional<Result> result = tx.get(get);
```

### 15.2 Dynamic SQL with USING Parameters

**PostgreSQL:**
```sql
CREATE OR REPLACE FUNCTION dynamic_update(
    p_table_name VARCHAR, p_col_name VARCHAR,
    p_value VARCHAR, p_id VARCHAR
)
RETURNS void AS $$
BEGIN
    EXECUTE format('UPDATE %I SET %I = $1 WHERE id = $2', p_table_name, p_col_name)
    USING p_value, p_id;
END;
$$ LANGUAGE plpgsql;
```

**ScalarDB Java API:**
```java
// The builder pattern IS dynamic SQL
Scan.Builder builder = Scan.newBuilder()
    .namespace("ns")
    .table(tableName)         // variable table name
    .partitionKey(Key.ofText("id", id));

// Dynamic column projection
if (colName != null) {
    builder.projections(colName);  // variable column name
}

Scan scan = builder.build();
List<Result> result = tx.scan(scan);
```

---

## 16. Feature Mapping: Output Parameters / RETURN

**PL/pgSQL Constructs:** `OUT` parameters, `RETURNS type`, `RETURNS TABLE(...)`, `RETURNS SETOF type`
**ScalarDB Mapping:** Java return values and result objects.

### 16.1 OUT Parameters → Return Object

**PostgreSQL:**
```sql
CREATE OR REPLACE FUNCTION calculate_order_total(
    p_order_id VARCHAR,
    OUT p_total NUMERIC,
    OUT p_item_count INTEGER
)
RETURNS RECORD AS $$
BEGIN
    SELECT COALESCE(SUM(price * qty), 0), COUNT(*)
    INTO p_total, p_item_count
    FROM order_items
    WHERE order_id = p_order_id;
END;
$$ LANGUAGE plpgsql;
```

**ScalarDB Java API:**
```java
// Define a result class
public class OrderTotalResult {
    public final double total;
    public final int itemCount;
    public OrderTotalResult(double total, int itemCount) {
        this.total = total;
        this.itemCount = itemCount;
    }
}

// Method returns the result (replaces OUT params)
public OrderTotalResult calculateOrderTotal(
        DistributedTransaction tx, String orderId) {

    List<Result> items = tx.scan(Scan.newBuilder()
        .namespace("ns").table("order_items")
        .partitionKey(Key.ofText("order_id", orderId))
        .build());

    double total = items.stream()
        .mapToDouble(r -> r.getDouble("price") * r.getInt("qty"))
        .sum();

    return new OrderTotalResult(total, items.size());
}
```

### 16.2 RETURNS TABLE → List of Result Objects

**PostgreSQL:**
```sql
CREATE OR REPLACE FUNCTION get_customer_orders(p_cust_id VARCHAR)
RETURNS TABLE(order_id VARCHAR, status VARCHAR, total NUMERIC) AS $$
BEGIN
    RETURN QUERY
        SELECT o.order_id, o.status, o.total
        FROM orders o
        WHERE o.customer_id = p_cust_id
        ORDER BY o.order_date DESC;
END;
$$ LANGUAGE plpgsql;
```

**ScalarDB Java API:**
```java
// RETURNS TABLE maps to a List of typed result objects
public class CustomerOrder {
    public final String orderId;
    public final String status;
    public final double total;
    public CustomerOrder(String orderId, String status, double total) {
        this.orderId = orderId;
        this.status = status;
        this.total = total;
    }
}

public List<CustomerOrder> getCustomerOrders(
        DistributedTransaction tx, String custId) {
    List<Result> results = tx.scan(Scan.newBuilder()
        .namespace("ns").table("orders")
        .partitionKey(Key.ofText("customer_id", custId))
        .build());

    return results.stream()
        .map(r -> new CustomerOrder(
            r.getText("order_id"),
            r.getText("status"),
            r.getDouble("total")))
        .collect(Collectors.toList());
}
```

### 16.3 RETURN Value → Method Return

**PostgreSQL:**
```sql
CREATE OR REPLACE FUNCTION get_order_count(p_cust_id VARCHAR)
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count FROM orders WHERE customer_id = p_cust_id;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;
```

**ScalarDB Java API:**
```java
public int getOrderCount(DistributedTransaction tx, String custId) {
    List<Result> results = tx.scan(scanOrders);
    return results.size();
}
```

---

## 17. Feature Mapping: Transaction Control Within SP

**PL/pgSQL Constructs:** `BEGIN`, `COMMIT`, `ROLLBACK`, `SAVEPOINT` within procedures (PostgreSQL 11+ supports transaction control in procedures called via `CALL`)
**ScalarDB Mapping:** Single transaction per service method. ScalarDB does not support nested transactions or savepoints.

### 17.1 Simple Transaction

**PostgreSQL:**
```sql
CREATE OR REPLACE PROCEDURE transfer_funds(
    p_from VARCHAR, p_to VARCHAR, p_amount NUMERIC
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE accounts SET balance = balance - p_amount WHERE id = p_from;
    UPDATE accounts SET balance = balance + p_amount WHERE id = p_to;
    COMMIT;
END;
$$;
```

**ScalarDB Java API:**
```java
public void transferFunds(String fromId, String toId, double amount) {
    // ... retry loop wraps this ...
    DistributedTransaction tx = manager.begin();
    try {
        // Read source account
        Result from = tx.get(Get.newBuilder()
            .namespace("ns").table("accounts")
            .partitionKey(Key.ofText("id", fromId))
            .build()).orElseThrow();

        // Read target account
        Result to = tx.get(Get.newBuilder()
            .namespace("ns").table("accounts")
            .partitionKey(Key.ofText("id", toId))
            .build()).orElseThrow();

        double fromBalance = from.getDouble("balance");
        double toBalance = to.getDouble("balance");

        if (fromBalance < amount) {
            throw new BusinessException("Insufficient funds");
        }

        // Debit source
        tx.update(Update.newBuilder()
            .namespace("ns").table("accounts")
            .partitionKey(Key.ofText("id", fromId))
            .doubleValue("balance", fromBalance - amount)
            .build());

        // Credit target
        tx.update(Update.newBuilder()
            .namespace("ns").table("accounts")
            .partitionKey(Key.ofText("id", toId))
            .doubleValue("balance", toBalance + amount)
            .build());

        tx.commit();
    } catch (Exception e) {
        tx.rollback();
        throw e;
    }
}
```

### 17.2 SAVEPOINT → Not Supported

ScalarDB does not support SAVEPOINTs or nested transactions. If your stored procedure uses SAVEPOINT, you must restructure the logic so that either the entire transaction succeeds or fails.

**PostgreSQL example requiring restructuring:**
```sql
CREATE OR REPLACE PROCEDURE multi_step_process(p_order_id VARCHAR)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE orders SET status = 'PROCESSING' WHERE order_id = p_order_id;
    SAVEPOINT step1;
    BEGIN
        -- Optional step that may fail
        INSERT INTO notifications (order_id, type) VALUES (p_order_id, 'EMAIL');
    EXCEPTION WHEN OTHERS THEN
        ROLLBACK TO step1;
        -- Continue without notification
    END;
    COMMIT;
END;
$$;
```

**Workaround strategies:**
- Split into separate transactions with a progress/status table tracking completed steps
- Use validation logic to prevent reaching the savepoint's rollback scenario
- If partial rollback is essential, model the operation as a saga pattern with compensating transactions
- Consider two-phase commit (2PC) for distributed scenarios

---

## 18. Feature Mapping: Batch Operations

**PL/pgSQL Constructs:** Multiple DML statements in one procedure call, batch INSERT
**ScalarDB Mapping:** `transaction.mutate(List)` or `transaction.batch(List)` for combined operations.

### 18.1 Mutate (multiple writes)

**PostgreSQL:**
```sql
CREATE OR REPLACE FUNCTION create_order_with_audit(
    p_order_id VARCHAR, p_cust_id VARCHAR
)
RETURNS void AS $$
BEGIN
    INSERT INTO orders (order_id, customer_id, status)
    VALUES (p_order_id, p_cust_id, 'PENDING');

    INSERT INTO audit_log (audit_id, table_name, operation)
    VALUES (gen_random_uuid()::TEXT, 'orders', 'INSERT');

    UPDATE customers SET order_count = order_count + 1
    WHERE customer_id = p_cust_id;
END;
$$ LANGUAGE plpgsql;
```

**ScalarDB Java API:**
```java
// ScalarDB: batch them in mutate()
Insert orderInsert = Insert.newBuilder()
    .namespace("ns").table("orders")
    .partitionKey(Key.ofText("order_id", orderId))
    .textValue("status", "PENDING")
    .build();

Insert auditInsert = Insert.newBuilder()
    .namespace("ns").table("audit_log")
    .partitionKey(Key.ofText("audit_id", UUID.randomUUID().toString()))
    .textValue("table_name", "orders")
    .textValue("operation", "INSERT")
    .build();

Update counterUpdate = Update.newBuilder()
    .namespace("ns").table("customers")
    .partitionKey(Key.ofText("customer_id", custId))
    .intValue("order_count", currentCount + 1)
    .build();

// Execute all writes atomically
tx.mutate(Arrays.asList(orderInsert, auditInsert, counterUpdate));
```

> **Note:** `mutate()` vs sequential calls: Both approaches are atomic (all within the same transaction). `mutate()` sends operations in a single batch call, which may be slightly more efficient for multiple writes. Sequential `tx.insert()` / `tx.update()` calls are functionally equivalent.

---

*Migration Strategy Guide — Stored Procedures & Triggers to ScalarDB Application Layer*
*Compatible with: ScalarDB 3.17+*
