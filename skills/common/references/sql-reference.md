# ScalarDB SQL Reference

Supported SQL grammar for ScalarDB SQL/JDBC interface. Available in Cluster mode only.

## Data Types

`BOOLEAN`, `INT`, `BIGINT`, `FLOAT`, `DOUBLE`, `TEXT`, `BLOB`, `DATE`, `TIME`, `TIMESTAMP`, `TIMESTAMPTZ`

### Literal Formats

| Type | Format | Example |
|------|--------|---------|
| INT | plain number | `10`, `100` |
| BIGINT | number + `L` suffix | `100L`, `200L` |
| FLOAT | decimal + `F` suffix | `1.23F`, `140.0F` |
| DOUBLE | plain decimal | `4.56` |
| TEXT | single-quoted string | `'hello'`, `'world'` |
| BOOLEAN | `TRUE` / `FALSE` | `TRUE` |

### Bind Markers

- Positional: `?`
- Named: `:<name>`

## DDL (Data Definition Language)

### CREATE NAMESPACE

```sql
CREATE NAMESPACE [IF NOT EXISTS] <namespace>
  [WITH '<option>'='<value>' [AND '<option>'='<value>'] ...]
```

### CREATE TABLE

```sql
-- Single-column primary key
CREATE TABLE [IF NOT EXISTS] [ns.]table (
  col1 INT PRIMARY KEY,
  col2 TEXT,
  col3 DOUBLE
)

-- Partition key + clustering keys
CREATE TABLE [IF NOT EXISTS] [ns.]table (
  pk INT,
  ck1 BIGINT,
  ck2 TEXT,
  val1 INT,
  val2 TEXT [ENCRYPTED],
  PRIMARY KEY (pk, ck1, ck2)
) WITH CLUSTERING ORDER BY (ck1 DESC, ck2 ASC)

-- Composite partition key
CREATE TABLE [IF NOT EXISTS] [ns.]table (
  pk1 INT,
  pk2 TEXT,
  ck INT,
  val TEXT,
  PRIMARY KEY ((pk1, pk2), ck)
)
```

### ALTER TABLE

```sql
-- Add column
ALTER TABLE [ns.]table ADD [COLUMN] [IF NOT EXISTS] col_name data_type [ENCRYPTED]

-- Drop column (JDBC backends only; cannot drop key columns)
ALTER TABLE [ns.]table DROP [COLUMN] [IF EXISTS] col_name

-- Rename column (JDBC backends only)
ALTER TABLE [ns.]table RENAME COLUMN old_name TO new_name

-- Rename table (JDBC backends only)
ALTER TABLE [ns.]table RENAME TO new_name

-- Change data type (limited conversions: INT→BIGINT, FLOAT→DOUBLE, any→TEXT)
ALTER TABLE [ns.]table ALTER [COLUMN] col_name [SET DATA] TYPE data_type
```

### DROP / TRUNCATE

```sql
DROP TABLE [IF EXISTS] [ns.]table
TRUNCATE TABLE [ns.]table
DROP NAMESPACE [IF EXISTS] namespace [CASCADE]
```

### CREATE / DROP INDEX

```sql
CREATE INDEX [IF NOT EXISTS] ON [ns.]table (column)
DROP INDEX [IF EXISTS] ON [ns.]table (column)
```

### Coordinator Tables

```sql
CREATE COORDINATOR TABLES [IF NOT EXIST]
TRUNCATE COORDINATOR TABLES
DROP COORDINATOR TABLES [IF EXIST]
```

## DML (Data Manipulation Language)

### SELECT

```sql
SELECT projection [, projection] ...
FROM [ns.]table [AS alias]
  [join [ns.]table [AS alias] ON predicates] ...
[WHERE conditions]
[GROUP BY column [, column] ...]
[HAVING conditions]
[ORDER BY column [ASC|DESC] [, column [ASC|DESC]] ...]
[LIMIT n]
```

**Projections**: `*`, `column [AS alias]`, `aggregate_function [AS alias]`

**Aggregate functions**: `COUNT(*)`, `COUNT(col)`, `SUM(col)`, `AVG(col)`, `MIN(col)`, `MAX(col)`

**WHERE operators**: `=`, `<>`, `!=`, `>`, `>=`, `<`, `<=`, `BETWEEN x AND y`, `[NOT] LIKE pattern [ESCAPE char]`, `IS [NOT] NULL`

**WHERE structure**: Must be either:
- OR of ANDs (disjunctive normal form): `(a AND b) OR (c AND d)`
- AND of ORs (conjunctive normal form): `(a OR b) AND (c OR d)`

**Query execution resolution** (how ScalarDB internally resolves the query):
1. **Get** — full primary key specified
2. **Partition Scan** — partition key specified (may include clustering key conditions)
3. **Index Scan** — secondary-index column equality specified
4. **Cross-partition Scan** — all other cases (requires `scalar.db.cross_partition_scan.enabled=true`)

### JOIN

```sql
-- INNER JOIN
[INNER] JOIN [ns.]table [AS alias] ON join_predicates

-- LEFT OUTER JOIN
LEFT [OUTER] JOIN [ns.]table [AS alias] ON join_predicates

-- RIGHT OUTER JOIN (must be the FIRST join)
RIGHT [OUTER] JOIN [ns.]table [AS alias] ON join_predicates
```

**JOIN predicate requirements**:
- `INNER JOIN` / `LEFT JOIN`: predicates must include all primary-key columns OR a secondary-index column from the **right** table
- `RIGHT JOIN`: predicates must include all primary-key columns OR a secondary-index column from the **left** table

**Not supported**: `FULL OUTER JOIN`, `CROSS JOIN`, `NATURAL JOIN`

### INSERT

```sql
INSERT INTO [ns.]table [(col1, col2, ...)]
  VALUES (val1, val2, ...) [, (val1, val2, ...)] ...
```

- Full primary key required in VALUES
- Throws conflict if record already exists
- Returns `updateCount`

### UPSERT

```sql
UPSERT INTO [ns.]table [(col1, col2, ...)]
  VALUES (val1, val2, ...) [, (val1, val2, ...)] ...
```

- Full primary key required in VALUES
- Inserts if not exists, updates if exists
- ScalarDB-specific extension (not standard SQL)

### UPDATE

```sql
UPDATE [ns.]table [AS alias]
  SET col1 = val1 [, col2 = val2] ...
  [WHERE conditions]
```

- Recommend specifying primary key in WHERE to avoid cross-partition scan

### DELETE

```sql
DELETE FROM [ns.]table [AS alias]
  [WHERE conditions]
```

## TCL (Transaction Control Language)

```sql
BEGIN                    -- Begin a transaction
START TRANSACTION        -- Alias for BEGIN

COMMIT                   -- Commit the transaction
ROLLBACK                 -- Rollback the transaction
ABORT                    -- Alias for ROLLBACK

-- Two-phase commit statements
PREPARE                  -- Prepare the transaction for 2PC
VALIDATE                 -- Validate (only for SERIALIZABLE + EXTRA_READ)

SUSPEND                  -- Suspend the current session
RESUME                   -- Resume a suspended session

SET MODE <mode>          -- Set transaction mode
```

## DCL (Data Control Language)

### User Management

```sql
CREATE USER username [WITH] {PASSWORD 'pwd' | SUPERUSER | NO_SUPERUSER} ...
ALTER USER username [WITH] {PASSWORD 'pwd' | SUPERUSER | NO_SUPERUSER} ...
DROP USER username
```

### Privileges

Privilege types: `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP`, `TRUNCATE`, `ALTER`, `ALL [PRIVILEGES]`, `GRANT OPTION`

```sql
-- Grant on table
GRANT privilege [, ...] ON [TABLE] table [, ...]
  TO [USER] username [, ...] [WITH GRANT OPTION]

-- Grant on namespace
GRANT privilege [, ...] ON NAMESPACE namespace [, ...]
  TO [USER] username [, ...] [WITH GRANT OPTION]

-- Revoke
REVOKE privilege [, ...] ON [TABLE] table [, ...] FROM [USER] username [, ...]
REVOKE privilege [, ...] ON NAMESPACE namespace [, ...] FROM [USER] username [, ...]
```

**Privilege constraints**:
- `INSERT` and `UPDATE` must be granted/revoked together
- Cannot grant `UPDATE` or `DELETE` without `SELECT`
- Cannot revoke `SELECT` if user has `INSERT` or `UPDATE`

### Role Management

```sql
CREATE ROLE role_name
DROP ROLE role_name
GRANT ROLE role [, ...] TO [USER] username [, ...]
REVOKE ROLE role [, ...] FROM [USER] username [, ...]
```

## Utility Statements

```sql
USE namespace              -- Set default namespace
SHOW NAMESPACES            -- List all namespaces
SHOW TABLES                -- List tables in current namespace
DESCRIBE [ns.]table        -- Show table schema
SHOW USERS                 -- List users
SHOW ROLES                 -- List roles
SHOW GRANTS                -- Show privileges
```

## SQL Limitations

1. **No DISTINCT** keyword
2. **No subqueries** (nested SELECT)
3. **No CTEs** (WITH ... AS)
4. **No window functions** (OVER, PARTITION BY, ROW_NUMBER, etc.)
5. **No FULL OUTER JOIN**
6. **No UNION / INTERSECT / EXCEPT**
7. **No CROSS JOIN / NATURAL JOIN**
8. **JOIN constraints** — ON predicates must reference primary key or secondary-index columns
9. **RIGHT OUTER JOIN** must be the first join in a multi-join query
10. **WHERE structure** — must be in DNF or CNF (no arbitrary boolean expressions)
11. **Encrypted columns** — cannot appear in WHERE or ORDER BY clauses
12. **Cross-partition scan** — requires explicit config; may downgrade isolation on non-JDBC backends
13. **ALTER TABLE** — most operations only on JDBC backends; limited on Cassandra; minimal on DynamoDB/CosmosDB
14. **Data type conversions** — limited: INT→BIGINT, FLOAT→DOUBLE, any→TEXT
15. **No auto-increment / sequence** — use UUID or application-generated IDs

## JDBC-Specific Notes

- Use `setObject()`/`getObject()` for DATE, TIME, TIMESTAMP, TIMESTAMPTZ (NOT legacy JDBC methods)
- Quote reserved words with double quotes: `"timestamp"`, `"order"`, `"key"`
- Always qualify tables with namespace: `ns.table`
- `UPSERT` is not standard SQL — specific to ScalarDB
- Error code 301 in `SQLException` = `UnknownTransactionStatusException`
