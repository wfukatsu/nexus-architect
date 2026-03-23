---
description: ScalarDB CRUD API usage rules — applies when writing Java code that uses ScalarDB CRUD operations
globs:
  - "**/*.java"
---

# ScalarDB CRUD API Rules

## Always Use Builder Pattern

All operations must use the builder pattern:

```java
Get.newBuilder().namespace("ns").table("tbl").partitionKey(key).build();
Scan.newBuilder().namespace("ns").table("tbl").partitionKey(key).build();
Insert.newBuilder().namespace("ns").table("tbl").partitionKey(key).build();
```

Do NOT use deprecated constructors like `new Get(key)`.

## Always Specify Namespace and Table

Every operation must have `.namespace()` and `.table()` set explicitly:

```java
// CORRECT:
Get.newBuilder()
    .namespace("sample")
    .table("customers")
    .partitionKey(Key.ofInt("customer_id", 1))
    .build();

// WRONG — missing namespace/table:
Get.newBuilder()
    .partitionKey(Key.ofInt("customer_id", 1))
    .build();
```

## Put Is Deprecated — Use Insert, Upsert, or Update

Since ScalarDB 3.13.0, `Put` is deprecated. Use:
- `Insert` — Insert only; throws conflict if record exists
- `Upsert` — Insert or update (no conditions)
- `Update` — Update only; does nothing if record doesn't exist

```java
// DEPRECATED:
transaction.put(Put.newBuilder()...build());

// USE INSTEAD:
transaction.insert(Insert.newBuilder()...build());
transaction.upsert(Upsert.newBuilder()...build());
transaction.update(Update.newBuilder()...build());
```

## Key Construction

Use the typed factory methods:

```java
Key.ofInt("col", 42)
Key.ofText("col", "hello")
Key.ofBigInt("col", 9999L)
Key.ofDouble("col", 3.14)
Key.ofBoolean("col", true)
```

For composite keys:

```java
Key.newBuilder()
    .addInt("col1", 1)
    .addText("col2", "hello")
    .build();
```

## Check Optional<Result> Properly

`get()` returns `Optional<Result>`. Always check before accessing:

```java
Optional<Result> result = transaction.get(get);
if (!result.isPresent()) {
    // Handle missing record
}
String name = result.get().getText("name");
```

## Result Null Handling

Primitive getters return default values when NULL:
- `getInt()` → 0
- `getBigInt()` → 0L
- `getFloat()` → 0.0f
- `getDouble()` → 0.0
- `getBoolean()` → false

Object getters return null:
- `getText()` → null
- `getBlob()` → null

Use `isNull("col")` to check for NULL explicitly.

## Use mutate() for Multiple Mutations

Instead of deprecated `put(List)` or `delete(List)`, use `mutate()`:

```java
transaction.mutate(Arrays.asList(insert1, update1, delete1));
```

## Cross-Partition Scan Requires Configuration

Using `Scan.newBuilder().all()` requires:
```properties
scalar.db.cross_partition_scan.enabled=true
```
