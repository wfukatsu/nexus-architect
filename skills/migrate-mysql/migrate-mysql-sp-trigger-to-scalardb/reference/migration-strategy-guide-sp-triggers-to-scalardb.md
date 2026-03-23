# Migration Strategy Guide: MySQL Stored Procedures & Triggers to ScalarDB Application Layer

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
| IF / CASE / IFNULL | Not in API | Read data with `tx.get()`, evaluate in Java, then write |
| Cursors (DECLARE CURSOR / FETCH) | Not available | `tx.scan()` + Java iteration |
| Sequences / AUTO_INCREMENT | Not available | `UUID.randomUUID()` or counter table pattern |
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

| # | Type | MySQL Behavior |
|---|------|----------------|
| 1 | BEFORE INSERT | Fires before row insert — defaults, ID gen, validation |
| 2 | AFTER INSERT | Fires after insert — audit log, counters (same tx) |
| 3 | BEFORE UPDATE | Fires before update — validate OLD→NEW transitions |
| 4 | AFTER UPDATE | Fires after update — audit trail |
| 5 | BEFORE DELETE | Fires before delete — check dependencies, archive |
| 6 | AFTER DELETE | Fires after delete — cascade, audit, counter decrement |

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

These are the SQL constructs found inside MySQL stored procedures and triggers that need equivalent ScalarDB Java API patterns:

| # | Feature Category | MySQL Constructs |
|---|------------------|------------------|
| 1 | Variables | DECLARE var, SET var = value, SELECT ... INTO var |
| 2 | Cursors | DECLARE CURSOR, OPEN, FETCH, CLOSE |
| 3 | Control flow | IF/ELSEIF/ELSE, WHILE, LOOP, CASE/WHEN, LEAVE, ITERATE |
| 4 | Exception handling | DECLARE CONTINUE/EXIT HANDLER FOR SQLSTATE/SQLEXCEPTION, SIGNAL SQLSTATE |
| 5 | OLD/NEW row access | OLD.column, NEW.column (triggers) |
| 6 | CRUD operations | SELECT, INSERT, UPDATE, DELETE |
| 7 | Conditional writes | INSERT ... ON DUPLICATE KEY UPDATE, INSERT IGNORE |
| 8 | Subqueries | SELECT ... WHERE col IN (SELECT ...) |
| 9 | JOINs | INNER JOIN, LEFT JOIN |
| 10 | Aggregations | SUM, COUNT, AVG, MIN, MAX, GROUP BY |
| 11 | Functions | IFNULL, COALESCE, NOW(), UUID(), CONCAT, GROUP_CONCAT |
| 12 | Sequences | AUTO_INCREMENT, LAST_INSERT_ID() |
| 13 | Temp tables | CREATE TEMPORARY TABLE |
| 14 | Dynamic SQL | PREPARE, EXECUTE, DEALLOCATE PREPARE |
| 15 | Output params | OUT parameters, RETURN values (functions) |
| 16 | Transactions | START TRANSACTION/COMMIT/ROLLBACK within SP |
| 17 | Batch operations | Multiple DML in one call |

---

# Feature Mapping Summary

| Section | Feature | ScalarDB API (with Java) |
|---------|---------|--------------------------|
| 1 | Variables (DECLARE/SET/INTO) | Java variables + `tx.get()` → `result.getText()` |
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
| 12 | Sequences/AUTO_INCREMENT | `UUID.randomUUID()` or counter table pattern |
| 13 | Temp tables | Java List / Map / Set |
| 14 | Dynamic SQL | Builder pattern — already dynamic and type-safe |
| 15 | Output params / RETURN | Java return values and result objects |
| 16 | Transactions in SP | `tx.begin()` / `tx.commit()` / `tx.rollback()` (no SAVEPOINT) |
| 17 | Batch operations | `tx.mutate(List)` or `tx.batch(List)` |

---

# Detailed Feature Mappings

## 2. Feature Mapping: Variables (DECLARE, SET, INTO)

**MySQL Constructs:** `DECLARE var_name type`, `SET var_name = value`, `SELECT ... INTO var_name`
**ScalarDB Mapping:** Standard Java variables. No API needed — use Java's type system directly.

### 2.1 DECLARE and SET

**MySQL Stored Procedure:**
```sql
DELIMITER //
CREATE PROCEDURE init_order()
BEGIN
    DECLARE v_order_id VARCHAR(36);
    DECLARE v_total DECIMAL(10,2);
    DECLARE v_status VARCHAR(20);
    SET v_order_id = UUID();
    SET v_total = 0.00;
    SET v_status = 'PENDING';
END//
DELIMITER ;
```

**ScalarDB Java API:**
```java
// Java variables replace DECLARE + SET
String orderId = UUID.randomUUID().toString();
double total = 0.00;
String status = "PENDING";
```

### 2.2 SELECT INTO

**MySQL Stored Procedure:**
```sql
DELIMITER //
CREATE PROCEDURE get_account_info(IN p_acc_id VARCHAR(36))
BEGIN
    DECLARE v_balance DECIMAL(10,2);
    DECLARE v_name VARCHAR(100);
    SELECT balance, name INTO v_balance, v_name
    FROM accounts WHERE account_id = p_acc_id;
END//
DELIMITER ;
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

## 3. Feature Mapping: Cursors (DECLARE CURSOR, FETCH, CLOSE)

**MySQL Constructs:** `DECLARE cursor_name CURSOR FOR SELECT ...`, `OPEN`, `FETCH`, `CLOSE`, `DECLARE CONTINUE HANDLER FOR NOT FOUND`
**ScalarDB Mapping:** `Scan` + `List<Result>` iteration, or `Scan` + `Scanner` for lazy iteration.

### 3.1 Simple Cursor (all rows in partition)

**MySQL Stored Procedure:**
```sql
DELIMITER //
CREATE PROCEDURE process_orders(IN p_cust_id VARCHAR(36))
BEGIN
    DECLARE v_oid VARCHAR(36);
    DECLARE v_amt DECIMAL(10,2);
    DECLARE v_done INT DEFAULT 0;
    DECLARE order_cursor CURSOR FOR
        SELECT order_id, total_amount FROM orders
        WHERE customer_id = p_cust_id;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = 1;

    OPEN order_cursor;
    read_loop: LOOP
        FETCH order_cursor INTO v_oid, v_amt;
        IF v_done THEN
            LEAVE read_loop;
        END IF;
        -- process each row
        UPDATE orders SET processed = 1 WHERE order_id = v_oid;
    END LOOP;
    CLOSE order_cursor;
END//
DELIMITER ;
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

### 3.2 Lazy Cursor (large result sets)

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

## 4. Feature Mapping: Control Flow (IF/ELSEIF/ELSE, WHILE, CASE)

**MySQL Constructs:** `IF/ELSEIF/ELSE/END IF`, `WHILE/END WHILE`, `LOOP/END LOOP`, `CASE/WHEN/END CASE`, `LEAVE`, `ITERATE`
**ScalarDB Mapping:** Standard Java control flow. No special API needed.

### 4.1 IF/ELSEIF/ELSE

**MySQL:**
```sql
DELIMITER //
CREATE PROCEDURE update_account(IN p_id VARCHAR(36), IN p_amount DECIMAL(10,2))
BEGIN
    DECLARE v_status VARCHAR(20);
    SELECT status INTO v_status FROM accounts WHERE id = p_id;

    IF v_status = 'ACTIVE' THEN
        UPDATE accounts SET balance = balance + p_amount WHERE id = p_id;
    ELSEIF v_status = 'SUSPENDED' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Account suspended';
    ELSE
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Account inactive';
    END IF;
END//
DELIMITER ;
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
    throw new BusinessException("Account suspended");
} else {
    throw new BusinessException("Account inactive");
}
```

### 4.2 WHILE Loop

**MySQL:**
```sql
DELIMITER //
CREATE PROCEDURE insert_batch(IN p_batch_id VARCHAR(36))
BEGIN
    DECLARE v_i INT DEFAULT 1;
    WHILE v_i <= 10 DO
        INSERT INTO batch_items(seq, batch_id) VALUES (v_i, p_batch_id);
        SET v_i = v_i + 1;
    END WHILE;
END//
DELIMITER ;
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

**MySQL:**
```sql
DELIMITER //
CREATE PROCEDURE get_discount(IN p_tier VARCHAR(20), OUT p_discount DECIMAL(3,2))
BEGIN
    SET p_discount = CASE p_tier
        WHEN 'GOLD' THEN 0.20
        WHEN 'SILVER' THEN 0.10
        ELSE 0.00
    END;
END//
DELIMITER ;
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

**MySQL Constructs:** `DECLARE CONTINUE HANDLER`, `DECLARE EXIT HANDLER`, `DECLARE HANDLER FOR SQLSTATE`, `DECLARE HANDLER FOR SQLEXCEPTION`, `SIGNAL SQLSTATE`, `RESIGNAL`
**ScalarDB Mapping:** Java try/catch with ScalarDB-specific exception types.

### 5.1 Exception Type Mapping

| MySQL Construct | ScalarDB Exception | Handling |
|-----------------|-------------------|----------|
| `SIGNAL SQLSTATE '45000'` | `throw new BusinessException(...)` | Custom exception for validation failures |
| `DECLARE EXIT HANDLER FOR SQLEXCEPTION` | `catch (TransactionException e)` | Catch-all for ScalarDB errors |
| `DECLARE EXIT HANDLER FOR SQLSTATE '40001'` (deadlock) | `CrudConflictException` | Retry the entire transaction from `begin()` |
| `DECLARE HANDLER FOR 1062` (dup key) | `CrudConflictException` | Retry or use Upsert instead of Insert |
| Commit failure | `CommitException` / `CommitConflictException` | Retry from `begin()` for conflict; investigate for others |
| Unknown commit state | `UnknownTransactionStatusException` | Check tx status externally; decide retry |
| `ROW_COUNT() = 0` | `Optional.empty()` / empty List | Check `result.isPresent()` or `results.isEmpty()` |
| `DECLARE CONTINUE HANDLER FOR NOT FOUND` | `Optional.empty()` check | Check `result.isPresent()` before accessing values |
| `ROLLBACK` in handler | `tx.rollback()` in catch block | Always rollback before retry or throw |

### 5.2 MySQL Handler → Java Exception Pattern

**MySQL:**
```sql
DELIMITER //
CREATE PROCEDURE safe_transfer(IN p_from VARCHAR(36), IN p_to VARCHAR(36), IN p_amount DECIMAL(10,2))
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    DECLARE EXIT HANDLER FOR SQLSTATE '45000'
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    -- ... transfer logic ...
    COMMIT;
END//
DELIMITER ;
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

### 5.3 SIGNAL SQLSTATE → throw BusinessException

**MySQL:**
```sql
DELIMITER //
CREATE PROCEDURE validate_order(IN p_amount DECIMAL(10,2))
BEGIN
    IF p_amount <= 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Order amount must be positive';
    END IF;
END//
DELIMITER ;
```

**ScalarDB Java API:**
```java
if (amount <= 0) {
    throw new BusinessException("Order amount must be positive");
}
```

---

## 6. Feature Mapping: OLD/NEW Row Access (Triggers)

**MySQL Constructs:** `OLD.column`, `NEW.column` (in trigger body)
**ScalarDB Mapping:** `Get` (read current row = OLD), Java method parameters = NEW values.

### 6.1 Pattern

**MySQL Trigger:**
```sql
DELIMITER //
CREATE TRIGGER trg_orders_before_update
BEFORE UPDATE ON orders
FOR EACH ROW
BEGIN
    IF OLD.status = 'CANCELLED' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Cannot update cancelled order';
    END IF;
    SET NEW.updated_at = NOW();
END//
DELIMITER ;

CREATE TRIGGER trg_orders_after_update
AFTER UPDATE ON orders
FOR EACH ROW
BEGIN
    INSERT INTO order_audit (order_id, audit_id, old_status, new_status, changed_by, changed_at)
    VALUES (OLD.order_id, UUID(), OLD.status, NEW.status, CURRENT_USER(), NOW());
END//
DELIMITER ;
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

**MySQL Constructs:** `SELECT`, `INSERT`, `UPDATE`, `DELETE`
**ScalarDB Mapping:** `Get`/`Scan` for reads, `Insert`/`Upsert`/`Update`/`Delete` for writes.

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
// SQL: INSERT INTO orders (order_id, status, total)
//      VALUES ('ORD001', 'CONFIRMED', 109.50)
//      ON DUPLICATE KEY UPDATE status = 'CONFIRMED', total = 109.50

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

---

## 8. Feature Mapping: Conditional Writes

**MySQL Constructs:** `INSERT ... ON DUPLICATE KEY UPDATE`, `INSERT IGNORE`, `UPDATE ... WHERE condition`, conditional checks
**ScalarDB Mapping:** `MutationCondition` with `ConditionBuilder` on Update/Delete operations.

### 8.1 UPDATE only if condition is met

**MySQL:**
```sql
DELIMITER //
CREATE PROCEDURE withdraw(IN p_account_id VARCHAR(36), IN p_amount DECIMAL(10,2))
BEGIN
    DECLARE v_rows INT;
    UPDATE accounts SET balance = balance - p_amount
    WHERE account_id = p_account_id AND balance >= p_amount;
    SET v_rows = ROW_COUNT();
    IF v_rows = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Insufficient funds';
    END IF;
END//
DELIMITER ;
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

```java
// Use Insert (not Upsert) -- it errors if record exists
// Replaces: INSERT IGNORE or INSERT ... ON DUPLICATE KEY
try {
    tx.insert(insertOp);  // Throws CrudConflictException if exists
} catch (CrudConflictException e) {
    throw new BusinessException("Record already exists");
}
```

---

## 9. Feature Mapping: Subqueries

**MySQL Constructs:** `SELECT ... WHERE col IN (SELECT ...)`, correlated subqueries, `EXISTS`
**ScalarDB Mapping:** Sequential operations. First query → Java collection → use results in second query.

### 9.1 IN Subquery

**MySQL:**
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

**MySQL Constructs:** `INNER JOIN`, `LEFT JOIN`, `RIGHT JOIN`
**ScalarDB Mapping:** Multiple Get/Scan operations with Java-side merging.

### 10.1 INNER JOIN → Get + Get

**MySQL:**
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

**MySQL Constructs:** `SUM`, `COUNT`, `AVG`, `MIN`, `MAX`, `GROUP BY`, `HAVING`
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

> **Note:** For high-volume tables, Java-side aggregation loads all matching rows into memory. Consider maintaining pre-computed counter/summary tables updated within the same transaction.

---

## 12. Feature Mapping: SQL Functions

**MySQL Constructs:** `IFNULL`, `COALESCE`, `NOW()`, `UUID()`, `CONCAT`, `GROUP_CONCAT`, `UPPER`, `LAST_INSERT_ID()`, etc.
**ScalarDB Mapping:** Java equivalents. No SQL functions available in the Java Transaction API.

| MySQL Function | Java Equivalent | Notes |
|----------------|-----------------|-------|
| `UUID()` | `UUID.randomUUID().toString()` | Use as partition/clustering key value |
| `NOW()` / `CURRENT_TIMESTAMP` | `System.currentTimeMillis()` or `Instant.now()` | Store as BIGINT (epoch ms) or TIMESTAMPTZ |
| `IFNULL(a, b)` | `a != null ? a : b` (or `Objects.requireNonNullElse`) | Check with `result.isNull("col")` first |
| `COALESCE(a, b, c)` | `a != null ? a : (b != null ? b : c)` | Chain null checks in Java |
| `NULLIF(a, b)` | `a.equals(b) ? null : a` | Use before setting value in builder |
| `CONCAT(a, b)` | `a + b` or `String.join()` | Concatenate in Java before storing |
| `GROUP_CONCAT(col SEPARATOR ',')` | `list.stream().map(...).collect(Collectors.joining(","))` | Java Collectors.joining() replaces GROUP_CONCAT |
| `UPPER()` / `LOWER()` | `str.toUpperCase()` / `str.toLowerCase()` | Transform in Java before storing |
| `ROUND(n, d)` | `Math.round()` or `BigDecimal.setScale()` | Use BigDecimal for financial precision |
| `ABS(n)` | `Math.abs(n)` | Standard math operation |
| `DATEDIFF(d1, d2)` / `DATE_ADD()` | `ChronoUnit.DAYS.between()` / `LocalDate.plusDays()` | Use java.time API for date arithmetic |
| `SUBSTRING(s, start, len)` | `str.substring(start - 1, start - 1 + len)` | Java string is 0-indexed, MySQL is 1-indexed |
| `LAST_INSERT_ID()` | `UUID.randomUUID().toString()` | Use UUID; AUTO_INCREMENT not available in ScalarDB |

### 12.1 GROUP_CONCAT → Collectors.joining()

**MySQL:**
```sql
SELECT order_id, GROUP_CONCAT(product_name SEPARATOR ', ')
FROM order_items
WHERE order_id = 'ORD001'
GROUP BY order_id;
```

**ScalarDB Java API:**
```java
List<Result> items = tx.scan(Scan.newBuilder()
    .namespace("ns").table("order_items")
    .partitionKey(Key.ofText("order_id", "ORD001"))
    .projections("product_name")
    .build());

String concatenated = items.stream()
    .map(r -> r.getText("product_name"))
    .collect(Collectors.joining(", "));
```

### 12.2 IFNULL → Java null check

**MySQL:**
```sql
SELECT IFNULL(nickname, name) AS display_name FROM users WHERE user_id = 'U001';
```

**ScalarDB Java API:**
```java
Optional<Result> result = tx.get(getUser);
Result user = result.orElseThrow();

String displayName = !user.isNull("nickname")
    ? user.getText("nickname")
    : user.getText("name");
```

---

## 13. Feature Mapping: Sequences / AUTO_INCREMENT

**MySQL Constructs:** `AUTO_INCREMENT`, `LAST_INSERT_ID()`
**ScalarDB Mapping:** UUID generation OR counter table pattern.

### 13.1 UUID (preferred)

**MySQL:**
```sql
-- MySQL AUTO_INCREMENT approach
CREATE TABLE orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    status VARCHAR(20)
);
INSERT INTO orders (status) VALUES ('PENDING');
SET @new_id = LAST_INSERT_ID();
```

**ScalarDB Java API:**
```java
// Best approach for distributed IDs — replaces AUTO_INCREMENT
String id = UUID.randomUUID().toString();

Insert insert = Insert.newBuilder()
    .namespace("ns").table("orders")
    .partitionKey(Key.ofText("order_id", id))
    .textValue("status", "PENDING")
    .build();
tx.insert(insert);
```

### 13.2 Counter Table (when sequential IDs are required)

**MySQL:**
```sql
-- MySQL pattern using LAST_INSERT_ID() for atomic increment
UPDATE id_counters SET current_value = LAST_INSERT_ID(current_value + 1)
WHERE table_name = 'orders';
SET @next_id = LAST_INSERT_ID();
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

> **Warning:** Counter tables create a hot partition and will cause frequent transaction conflicts under concurrent writes. Use UUID unless sequential IDs are an absolute requirement. If you must use counters, partition by shard key (e.g., region + counter) to reduce contention.

---

## 14. Feature Mapping: Temporary Tables

**MySQL Constructs:** `CREATE TEMPORARY TABLE`
**ScalarDB Mapping:** Java collections (List, Map, Set) as in-memory working storage.

### 14.1 Temp Table → Java Collection

**MySQL:**
```sql
DELIMITER //
CREATE PROCEDURE process_pending()
BEGIN
    CREATE TEMPORARY TABLE tmp_pending (
        order_id VARCHAR(36),
        total DECIMAL(10,2)
    );
    INSERT INTO tmp_pending
        SELECT order_id, total FROM orders WHERE status = 'PENDING';
    -- Use tmp_pending in subsequent queries
    DROP TEMPORARY TABLE IF EXISTS tmp_pending;
END//
DELIMITER ;
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

**MySQL Constructs:** `PREPARE`, `EXECUTE`, `DEALLOCATE PREPARE`, `CONCAT` for building SQL strings
**ScalarDB Mapping:** Programmatic operation builder. The Java API is already dynamic — you build operations in code.

### 15.1 Dynamic Table/Column Selection

**MySQL:**
```sql
DELIMITER //
CREATE PROCEDURE dynamic_query(IN p_table_name VARCHAR(64), IN p_col_name VARCHAR(64), IN p_id VARCHAR(36))
BEGIN
    SET @sql = CONCAT('SELECT ', p_col_name, ' FROM ', p_table_name, ' WHERE id = ?');
    SET @p_id = p_id;
    PREPARE stmt FROM @sql;
    EXECUTE stmt USING @p_id;
    DEALLOCATE PREPARE stmt;
END//
DELIMITER ;
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

For multiple columns output:
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

**MySQL Constructs:** `OUT` parameters in procedures, `RETURN` value in functions
**ScalarDB Mapping:** Java return values and result objects.

### 16.1 OUT Parameters → Return Object

**MySQL:**
```sql
DELIMITER //
CREATE PROCEDURE calculate_order_total(
    IN p_order_id VARCHAR(36),
    OUT p_total DECIMAL(10,2),
    OUT p_item_count INT
)
BEGIN
    SELECT SUM(price * qty), COUNT(*)
    INTO p_total, p_item_count
    FROM order_items
    WHERE order_id = p_order_id;
END//
DELIMITER ;

-- Calling:
CALL calculate_order_total('ORD001', @total, @count);
SELECT @total, @count;
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

### 16.2 RETURN Value (Function) → Method Return

**MySQL:**
```sql
DELIMITER //
CREATE FUNCTION get_order_count(p_cust_id VARCHAR(36))
RETURNS INT
DETERMINISTIC
BEGIN
    DECLARE v_count INT;
    SELECT COUNT(*) INTO v_count FROM orders WHERE customer_id = p_cust_id;
    RETURN v_count;
END//
DELIMITER ;
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

**MySQL Constructs:** `START TRANSACTION`, `COMMIT`, `ROLLBACK`, `SAVEPOINT` within stored procedures
**ScalarDB Mapping:** Single transaction per service method. ScalarDB does not support nested transactions or savepoints.

### 17.1 Simple Transaction

**MySQL:**
```sql
DELIMITER //
CREATE PROCEDURE transfer_funds(
    IN p_from VARCHAR(36),
    IN p_to VARCHAR(36),
    IN p_amount DECIMAL(10,2)
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    UPDATE accounts SET balance = balance - p_amount WHERE id = p_from;
    UPDATE accounts SET balance = balance + p_amount WHERE id = p_to;
    COMMIT;
END//
DELIMITER ;
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

**Workaround strategies:**
- Split into separate transactions with a progress/status table tracking completed steps
- Use validation logic to prevent reaching the savepoint's rollback scenario
- If partial rollback is essential, model the operation as a saga pattern with compensating transactions
- Consider two-phase commit (2PC) for distributed scenarios

---

## 18. Feature Mapping: Batch Operations

**MySQL Constructs:** Multiple DML statements in one procedure call, batch INSERT
**ScalarDB Mapping:** `transaction.mutate(List)` or `transaction.batch(List)` for combined operations.

### 18.1 Mutate (multiple writes)

**MySQL:**
```sql
DELIMITER //
CREATE PROCEDURE create_order(
    IN p_order_id VARCHAR(36),
    IN p_cust_id VARCHAR(36)
)
BEGIN
    INSERT INTO orders (order_id, customer_id, status) VALUES (p_order_id, p_cust_id, 'PENDING');
    INSERT INTO audit_log (audit_id, table_name, operation) VALUES (UUID(), 'orders', 'INSERT');
    UPDATE customers SET order_count = order_count + 1 WHERE customer_id = p_cust_id;
END//
DELIMITER ;
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
