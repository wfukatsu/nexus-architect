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

### A `Put` with no preceding `Get` is an INSERT, and fails on an existing record

This is the trap the deprecation above exists to remove, and it is invisible until commit.

Consensus Commit decides what a `Put` means from **whether the transaction read the record first**.
With no preceding `Get` in the same transaction it attaches an implicit `PutIfNotExists`, so:

| In one transaction | Record absent | Record exists |
|--------------------|---------------|---------------|
| `put(...)` alone | commits — inserts | **`CommitConflictException` at commit** — `DB-CORE-20013: The record being prepared already exists` |
| `get(...)` then `put(...)` | commits — inserts | commits — updates |

Verified against ScalarDB 3.19.0. The failure surfaces at `commit()`, not at `put()`, so the write
looks accepted and the transaction fails later with a *conflict* error that reads like contention —
sending you to retry logic for a bug that no retry can fix. Retrying is in fact the wrong response:
every attempt fails identically.

Two consequences for generated and hand-written code:

- **A read-modify-write must actually read.** `get()` the record in the same transaction before
  `put()`, which you need anyway to evaluate any precondition or ownership predicate on it.
- **Prefer the explicit operations** (`insert` / `upsert` / `update`) precisely because they state
  the intent instead of inferring it from read history. An `update()` on a missing record does
  nothing rather than surprising you; an `upsert()` works whether or not the record exists.

Static review does not catch this. An independent reviewer reading a blind-`Put` implementation
flagged its missing authorization check and its split transactions, and never noted that the
operation could not succeed at all — that took executing it (@rules/ai-code-quality-gate.md stage 4).

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

## Composite Clustering Keys Are ONE Key

`clusteringKey(...)` is a **setter, not an appender**. Chaining it once per column silently keeps
only the last call, and the operation then fails at execution with
`DB-CORE-10021: The clustering key is not properly specified`.

```java
// WRONG — saga_id is dropped; only step survives
.clusteringKey(Key.ofText("saga_id", sagaId))
.clusteringKey(Key.ofText("step", step))

// RIGHT — one Key carrying both columns, in clustering-key order
.clusteringKey(Key.newBuilder()
        .addText("saga_id", sagaId)
        .addText("step", step)
        .build())
```

The same applies to a multi-column partition key. Column order must match the order declared in the
table metadata.

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
