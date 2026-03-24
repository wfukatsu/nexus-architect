---
description: Show ScalarDB CRUD operation patterns — builder syntax for Get, Scan, Insert, Upsert, Update, Delete with examples.
user_invocable: true
---

# /scalardb:crud-ops — ScalarDB CRUD Operations Guide

## Instructions

You are a ScalarDB CRUD operations expert. Show the user how to perform specific CRUD operations with the ScalarDB API.

## Interactive Flow

### Step 1: Determine the operation
Ask: "What operation do you need help with?" if not specified.

Options:
- **Get** — Retrieve a single record by primary key or index
- **Scan** — Retrieve multiple records (partition scan, range scan, scan all, index scan)
- **Insert** — Insert a new record (fails if exists)
- **Upsert** — Insert or update a record
- **Update** — Update an existing record (does nothing if not exists)
- **Delete** — Delete a record
- **Batch** — Execute multiple operations atomically
- **Key construction** — Build single and composite keys

### Step 2: Gather context
Ask about their schema:
- Namespace and table name
- Partition key column(s) and type(s)
- Clustering key column(s) and type(s) if applicable
- Value columns they want to read/write

### Step 3: Generate code
Generate the complete code example including:
- Builder pattern usage
- Key construction
- Result extraction
- Proper exception handling
- Transaction lifecycle (begin, operation, commit, rollback)

## Reference

Read `.claude/docs/api-reference.md` for the complete API reference.

## Quick Reference Examples

### Get by Primary Key
```java
Optional<Result> result = tx.get(
    Get.newBuilder()
        .namespace("ns").table("tbl")
        .partitionKey(Key.ofInt("id", 1))
        .clusteringKey(Key.ofInt("ck", 2))
        .build());
```

### Get by Index
```java
Optional<Result> result = tx.get(
    Get.newBuilder()
        .namespace("ns").table("tbl")
        .indexKey(Key.ofText("order_id", orderId))
        .build());
```

### Scan (Partition)
```java
List<Result> results = tx.scan(
    Scan.newBuilder()
        .namespace("ns").table("tbl")
        .partitionKey(Key.ofInt("pk", 1))
        .ordering(Scan.Ordering.desc("ck"))
        .limit(100)
        .build());
```

### Scan (Range)
```java
List<Result> results = tx.scan(
    Scan.newBuilder()
        .namespace("ns").table("tbl")
        .partitionKey(Key.ofInt("pk", 1))
        .start(Key.ofInt("ck", 10)).startInclusive(true)
        .end(Key.ofInt("ck", 20)).endInclusive(false)
        .build());
```

### Scan All
```java
List<Result> results = tx.scan(
    Scan.newBuilder()
        .namespace("ns").table("tbl")
        .all()
        .limit(100)
        .build());
// Requires: scalar.db.cross_partition_scan.enabled=true
```

### Insert
```java
tx.insert(
    Insert.newBuilder()
        .namespace("ns").table("tbl")
        .partitionKey(Key.ofInt("id", 1))
        .textValue("name", "Alice")
        .intValue("age", 30)
        .build());
```

### Upsert
```java
tx.upsert(
    Upsert.newBuilder()
        .namespace("ns").table("tbl")
        .partitionKey(Key.ofInt("id", 1))
        .textValue("name", "Alice")
        .intValue("age", 31)
        .build());
```

### Update with Condition
```java
tx.update(
    Update.newBuilder()
        .namespace("ns").table("tbl")
        .partitionKey(Key.ofInt("id", 1))
        .intValue("balance", newBalance)
        .condition(ConditionBuilder.updateIf(
            ConditionBuilder.column("balance").isGreaterThanOrEqualToInt(amount)
        ).build())
        .build());
```

### Delete
```java
tx.delete(
    Delete.newBuilder()
        .namespace("ns").table("tbl")
        .partitionKey(Key.ofInt("id", 1))
        .clusteringKey(Key.ofInt("ck", 2))
        .build());
```

### Key Construction (Composite)
```java
Key compositeKey = Key.newBuilder()
    .addInt("col1", 1)
    .addText("col2", "abc")
    .build();
```

### Result Extraction
```java
if (result.isPresent()) {
    Result r = result.get();
    int id = r.getInt("id");           // 0 if NULL
    String name = r.getText("name");   // null if NULL
    boolean isNull = r.isNull("name"); // check NULL
}
```

## Output Format

Provide complete, runnable code examples with proper imports and exception handling. Tailor examples to the user's specific schema.
