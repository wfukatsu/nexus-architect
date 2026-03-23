---
name: migrate-postgresql-to-scalardb
description: Generates ScalarDB migration documentation from PostgreSQL schema analysis. Consumes the PostgreSQL schema analysis Markdown file from the configured output directory as input and produces migration analysis and step-by-step migration guides.
---

# Migrate PostgreSQL to ScalarDB Schema Skill

## Purpose

Generate comprehensive **ScalarDB migration documentation** from an existing PostgreSQL schema analysis report. This skill focuses solely on the migration analysis and documentation logic.

**Key Statement**: This skill consumes the PostgreSQL schema analysis Markdown file from the shared `OUTPUT_DIR` as input.

---

## Skill Responsibility

This skill is responsible for:
- Reading and parsing PostgreSQL schema analysis input
- Performing migration compatibility analysis
- Calculating migration complexity and effort
- Generating migration documentation

This skill is **NOT** responsible for:
- Orchestration or command handling (handled by `/postgresql-to-scalardb` command)
- User interaction or query parsing
- Configuration loading (received from command)

---

## Input Contract

The skill receives the following inputs from the command layer:

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `postgresql_schema_report` | File path | YES | Path to `postgresql_schema_report.md` from analyze-postgresql-schema |
| `raw_schema_data` | File path | NO | Path to `raw_schema_data.json` for additional lookup |
| `output_directory` | Directory | YES | Shared output directory (from `.env`) |
| `namespace` | String | NO | Target ScalarDB namespace |

**Note**: Configuration is centralized in `.claude/configuration/databases.env`. Both skills read from this single file.

---

## Output Contract

The skill produces the following outputs:

| Output | File | Description |
|--------|------|-------------|
| Migration Analysis | `scalardb_migration_analysis.md` | Compatibility analysis, data type mappings, risk assessment |
| Migration Steps | `scalardb_migration_steps.md` | Step-by-step migration guide with code examples |
| Complexity Score | (in report) | Calculated score 0-10 |
| Effort Rating | (in report) | LOW/MEDIUM/HIGH/VERY HIGH |

---

## Naming Conventions

### Table and Column Names — Use Exact Names from `raw_schema_data.json`

**Do NOT normalize table names or column names to lowercase or uppercase.**

PostgreSQL's behavior depends on how the object was created:
- **Unquoted identifiers** (e.g., `CREATE TABLE accounts`) → PostgreSQL folds them to `accounts` (lowercase)
- **Quoted identifiers** (e.g., `CREATE TABLE "Accounts"`) → PostgreSQL stores them as `Accounts` exactly

The `raw_schema_data.json` is extracted directly from PostgreSQL's information schema and always reflects the exact stored name — regardless of how the object was originally created. This is the **single source of truth** for names.

**Rule:** Use table names and column names exactly as they appear in `raw_schema_data.json` in all generated output — migration analysis documents, ScalarDB schema configuration examples, and Java code snippets. Never assume uppercase or lowercase.

```java
// Use whatever casing raw_schema_data.json shows — do not change it
Get get = Get.newBuilder()
    .namespace("public")                                  // namespace from config
    .table("accounts")                                    // use exact name from JSON
    .partitionKey(Key.ofInt("account_id", accountId))     // use exact name from JSON
    .build();
```

---

## Skill Logic

### 1. Parse Input

Read `postgresql_schema_report.md` and extract:
- Table definitions and columns
- Data types for mapping
- Constraints for migration planning
- Custom types (ENUM, composite, domain) for mapping analysis
- PL/pgSQL objects for application migration planning

### 2. Perform Type Mapping (Official ScalarDB Documentation)

> **Reference**: https://scalardb.scalar-labs.com/docs/latest/schema-loader-import#data-type-mapping-from-jdbc-databases-to-scalardb

> ⚠️ **IMPORTANT**: Only the data types listed below are officially supported. **Data types NOT listed in the official documentation are NOT SUPPORTED.** This includes any PostgreSQL extensions, custom types, or unlisted built-in types.

#### Supported PostgreSQL Data Types (ONLY THESE 14 TYPES)

| PostgreSQL Type | ScalarDB Type | Notes |
|-----------------|---------------|-------|
| bigint | BIGINT | ⚠️ **Warning**: ScalarDB range is -2^53 to 2^53 only |
| boolean | BOOLEAN | Direct mapping |
| bytea | BLOB | Max ~2GB (2^31-1 bytes) |
| character | TEXT | ⚠️ ScalarDB may map larger than source; size errors possible |
| character varying | TEXT | ⚠️ ScalarDB may map larger than source; size errors possible |
| date | DATE | Direct mapping |
| double precision | DOUBLE | Direct mapping |
| integer | INT | Direct mapping |
| real | FLOAT | Direct mapping |
| smallint | INT | ⚠️ ScalarDB maps to larger type; size errors possible on write |
| text | TEXT | Direct mapping |
| time | TIME | Without timezone only |
| timestamp | TIMESTAMP | Direct mapping |
| timestamp with time zone | TIMESTAMPTZ | Direct mapping |

#### NOT Supported PostgreSQL Data Types

> **Data types not listed above are NOT SUPPORTED.** The following are common data types that are explicitly NOT supported:

| Category | Unsupported Types |
|----------|-------------------|
| **Serial/Sequence** | serial, smallserial, bigserial |
| **Numeric** | numeric, money |
| **Binary** | bit |
| **Date/Time** | interval, time with time zone |
| **JSON** | json, jsonb |
| **UUID** | uuid |
| **XML** | xml |
| **Network** | inet, cidr, macaddr, macaddr8 |
| **Geometric** | point, line, lseg, box, path, polygon, circle |
| **Text Search** | tsvector, tsquery |
| **System** | pg_lsn, pg_snapshot, txid_snapshot |
| **Arrays** | All array types (e.g., integer[], text[]) |
| **Range Types** | All range types (e.g., int4range, daterange) |
| **ENUM Types** | User-defined ENUM types |
| **Composite Types** | User-defined composite types |
| **Domain Types** | User-defined domain types |
| **Extension Types** | Any types from PostgreSQL extensions (e.g., PostGIS, hstore, ltree) |
| **Any Other Types** | Any PostgreSQL type not in the 14 supported types above |

#### Critical Warnings (From Official Documentation)

> ⚠️ **BIGINT Range Warning**: The value range of BIGINT in ScalarDB is from **-2^53 to 2^53**, regardless of the size of bigint in the underlying database. If data outside this range exists in the imported table, ScalarDB cannot read it.

> ⚠️ **Size Mapping Warning**: For certain data types (smallint, character, character varying), ScalarDB may map a data type larger than that of the underlying database. You will see errors when putting a value with a size larger than the size specified in the underlying database.

> ⚠️ **BLOB Size Warning**: The maximum size of BLOB in ScalarDB is about 2GB (precisely 2^31-1 bytes).

#### Migration Strategies for Unsupported Types

| Unsupported Type | Migration Strategy |
|------------------|-------------------|
| serial/bigserial | Use UUID or application-level ID generation |
| numeric | Convert to DOUBLE (precision loss) or store as TEXT |
| money | Convert to DOUBLE or store as TEXT |
| json/jsonb | Store as TEXT, parse in application |
| uuid | Store as TEXT (36 characters) |
| xml | Store as TEXT |
| bit | Store as TEXT |
| inet/cidr/macaddr | Store as TEXT |
| interval | Convert to separate columns or application logic |
| time with time zone | Use TIME (without timezone) or store as TEXT |
| Arrays | Normalize to separate child table |
| Range types | Store as two boundary columns (start, end) |
| ENUM | Store as TEXT + application validation |
| Composite types | Flatten to individual columns |
| Domain types | Use base type + application validation |
| tsvector/tsquery | Use ScalarDB Vector Search or external search |
| Geometric types | Store coordinates as separate DOUBLE columns |
| Extension types (PostGIS, hstore, etc.) | Convert to supported types or TEXT |
| Any unlisted type | **NOT SUPPORTED** - Must convert to one of the 14 supported types |

### 3. Calculate Complexity Score

Apply weighted scoring model:

```
Total = (Data Type × 0.20) + (Schema × 0.25) + (PL/pgSQL × 0.25) + (App Impact × 0.30)
```

#### Data Type Complexity (0-10)

| Score | Criteria |
|-------|----------|
| 0-2 | Standard types only (INTEGER, VARCHAR, BOOLEAN, TIMESTAMP) |
| 3-4 | BYTEA requiring size validation |
| 5-6 | JSON/JSONB, UUID columns |
| 7-8 | Array types requiring normalization |
| 9-10 | Composite types, range types, tsvector |

#### Schema Complexity (0-10)

| Score | Criteria |
|-------|----------|
| 0-2 | Simple tables with standard constraints |
| 3-4 | Foreign keys, composite primary keys |
| 5-6 | Views requiring conversion |
| 7-8 | Materialized views, partitioned tables |
| 9-10 | Table inheritance, complex RLS policies |

#### PL/pgSQL Complexity (0-10)

| Score | Criteria |
|-------|----------|
| 0 | No PL/pgSQL objects |
| 1-3 | Simple functions (<10) |
| 4-6 | Moderate (10-50 objects) |
| 7-8 | Complex (50+ objects, triggers) |
| 9-10 | Heavy business logic in DB, event triggers |

#### Application Impact (0-10)

| Score | Criteria |
|-------|----------|
| 0-2 | Simple CRUD only |
| 3-4 | JOINs, basic transactions, aggregations |
| 5-6 | Subqueries - require decomposition |
| 7-8 | Window functions, CTEs, complex subqueries |
| 9-10 | Heavy DB-side logic, stored procedures |

### 4. Generate Reports

Using templates, generate:
1. `scalardb_migration_analysis.md` - Analysis report
2. `scalardb_migration_steps.md` - Step-by-step guide

---

## PostgreSQL-Specific Unsupported Features

| Feature | Status | Migration Strategy |
|---------|--------|-------------------|
| Table Inheritance | NOT SUPPORTED | Flatten or normalize |
| SERIAL/IDENTITY | NOT SUPPORTED | UUID or app-level sequence |
| Sequences | NOT SUPPORTED | UUID or app-level counter |
| Triggers | NOT SUPPORTED | Application event handlers |
| Functions/Procedures | NOT SUPPORTED | Convert to application code |
| Row Level Security | NOT SUPPORTED | Application-level security |
| Materialized Views | NOT SUPPORTED | Application caching |
| Full-Text Search | NOT SUPPORTED | ScalarDB Vector Search or Elasticsearch |
| JSONB Operators | NOT SUPPORTED | Application-level JSON parsing |
| Foreign Data Wrappers | NOT SUPPORTED | Import data first |
| Generated Columns | NOT SUPPORTED | Compute in application |
| Partitioning | PARTIAL | Underlying DB handles |
| ENUM Types | NOT SUPPORTED | TEXT + app validation |
| Array Types | NOT SUPPORTED | Normalize to child table |
| Range Types | NOT SUPPORTED | Two boundary columns |
| Composite Types | NOT SUPPORTED | Flatten to columns |

---

## ScalarDB SQL Capabilities

### Supported Features

| Feature | Support | Notes |
|---------|---------|-------|
| SELECT, INSERT, UPDATE, DELETE | ✅ Supported | Standard DML operations |
| JOIN (INNER, LEFT, RIGHT) | ⚠️ Limited | See limitations below |
| WHERE clauses | ⚠️ Limited | Must use DNF or CNF form |
| ORDER BY, LIMIT | ✅ Supported | |
| GROUP BY, HAVING | ✅ Supported | |
| COUNT, SUM, AVG, MIN, MAX | ✅ Supported | |
| CREATE/DROP TABLE | ✅ Supported | DDL operations |
| CREATE INDEX | ✅ Supported | Secondary indexes |

---

## ScalarDB SQL Limitations (CRITICAL)

> **Reference**: https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/grammar/

ScalarDB SQL has significant differences from traditional RDBMS SQL. These must be analyzed during migration.

### 1. JOIN Limitations

| Aspect | ScalarDB Behavior | Impact |
|--------|-------------------|--------|
| Cross-partition JOINs | May cause cross-partition scans | Performance degradation |
| Multi-table JOINs | Not optimized like PostgreSQL | Complex queries may be slow |
| Execution model | Partition-based Get/Scan operations | JOINs resolved per-partition |

**Recommendation**: For complex multi-table JOINs, use **ScalarDB Analytics** instead.

### 2. WHERE Clause Restrictions

| Restriction | Description |
|-------------|-------------|
| Predicate Form | Must be in **DNF** (OR-of-ANDs) or **CNF** (AND-of-ORs) |
| Arbitrary combinations | May not parse correctly |
| Partition key | Should include partition key for optimal performance |

### 3. Features NOT Supported in ScalarDB SQL

| Feature | PostgreSQL | Workaround |
|---------|------------|------------|
| Subqueries | Common | Sequential queries or ScalarDB Analytics |
| CTEs (WITH) | Common | Convert to subqueries or application logic |
| Window functions | ROW_NUMBER, RANK, etc. | ScalarDB Analytics |
| UNION/INTERSECT/EXCEPT | Set operations | Multiple queries + application merge |
| Stored procedures | CREATE PROCEDURE | Convert to application methods |
| Functions | CREATE FUNCTION | Convert to application methods |
| Triggers | CREATE TRIGGER | Application-level event handling |
| Sequences | NEXTVAL | UUID or application-level ID generation |

---

## ScalarDB Analytics (REQUIRED for Complex Queries)

> **When to Use**: If your PostgreSQL schema uses complex JOINs, subqueries, window functions, or analytical queries, you **MUST** plan for ScalarDB Analytics deployment.

### Decision Matrix

| Query Pattern | ScalarDB SQL | ScalarDB Analytics |
|---------------|--------------|-------------------|
| Simple CRUD (single table) | ✅ Use | Not needed |
| Single-partition queries | ✅ Use | Not needed |
| Simple 2-table JOINs (same partition) | ✅ Use | Not needed |
| Multi-table JOINs (cross-partition) | ⚠️ Performance issues | ✅ **Use Analytics** |
| Subqueries | ❌ Not supported | ✅ **Use Analytics** |
| Window functions | ❌ Not supported | ✅ **Use Analytics** |
| Complex aggregations | ⚠️ Limited | ✅ **Use Analytics** |
| UNION/INTERSECT/EXCEPT | ❌ Not supported | ✅ **Use Analytics** |
| Analytical/reporting queries | ⚠️ Not optimized | ✅ **Use Analytics** |

### Analytics Reference

| Reference | URL |
|-----------|-----|
| ScalarDB Analytics Overview | https://scalardb.scalar-labs.com/docs/latest/scalardb-analytics/ |
| Analytics CLI Reference | https://scalardb.scalar-labs.com/docs/latest/scalardb-analytics/reference-cli-command/ |

---

## ScalarDB SQL as Primary Migration Path

### Mandatory References

| Reference | URL |
|-----------|-----|
| **ScalarDB SQL Grammar (CRITICAL)** | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/grammar/ |
| ScalarDB Cluster SQL (JDBC) | https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/getting-started-with-scalardb-cluster-sql-jdbc/ |
| ScalarDB SQL Migration Guide | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/migration-guide |
| **Decoupling Transaction Metadata (RECOMMENDED)** | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import/#decoupling-transaction-metadata |
| Schema Loader Data Type Mapping | https://scalardb.scalar-labs.com/docs/latest/schema-loader/#data-type-mapping-between-scalardb-and-other-databases |

---

## RECOMMENDED: Transaction Metadata Decoupling

For migration scenarios, use **`transaction-metadata-decoupling: true`** instead of `transaction: true`.

### Why This Matters for Migration

| Configuration | Effect on Existing Tables | Best For |
|---------------|---------------------------|----------|
| `"transaction": true` | **ALTERS** table - adds metadata columns | New tables |
| `"transaction-metadata-decoupling": true` | **NO CHANGE** - metadata in separate table | **Migrating existing tables** |

### How It Works

When using `transaction-metadata-decoupling: true`:
1. Original table (e.g., `customers`) remains **unchanged**
2. ScalarDB creates `customers_scalardb` for transaction metadata
3. Application accesses data via `<table_name>_scalardb`
4. Easy rollback - just drop the metadata table

### Configuration Example

```json
{
  "namespace.table_name": {
    "transaction-metadata-decoupling": true,
    "partition-key": ["id"],
    "columns": {
      "id": "BIGINT",
      "name": "TEXT"
    }
  }
}
```

> **Note**: Use `transaction-metadata-decoupling: true` OR `transaction: true` - they are mutually exclusive.

---

## PostgreSQL Feature Mapping

### Fully Supported (ScalarDB SQL)

- Tables with standard data types (INTEGER, VARCHAR, BOOLEAN, TIMESTAMP, etc.)
- Primary keys → partition-key + clustering-key
- Basic indexes → secondary-index
- Simple SELECT, INSERT, UPDATE, DELETE
- JOIN queries (2-3 tables)
- GROUP BY with aggregates (v3.17+)

### Partially Supported

- Foreign keys → Application-level enforcement
- Check constraints → Application-level validation
- BYTEA → BLOB (size limits)
- Views → Import as tables or queries

### Requires Workaround

| Feature | Workaround |
|---------|------------|
| Subqueries | Sequential queries or ScalarDB Analytics |
| Sequences/SERIAL | UUID or application-level ID |
| Triggers | Application event handling |
| Stored procedures/functions | Application methods |
| ENUM types | TEXT + application validation |
| Array types | Separate child table |
| JSONB operators | Application-level JSON parsing |
| Table inheritance | Flatten or merge tables |
| Partitioning | Let underlying DB handle |

---

## Files in This Skill

```
skills/migrate-postgresql-to-scalardb/
├── SKILL.md                              # This file
├── reference/
│   └── scalardb_reference.md             # Complete ScalarDB reference
└── templates/
    ├── scalardb_migration_analysis.md    # Analysis report template
    └── scalardb_migration_steps.md       # Steps guide template
```

**Configuration file** (in `.claude/configuration/`):
| `databases.env` | Consolidated database configuration (Oracle, MySQL, PostgreSQL) |

---

## Related

- **Command**: `commands/postgresql-to-scalardb.md` (orchestration)
- **Prerequisite Skill**: `skills/analyze-postgresql-schema/` (input provider)

---

*Skill Version: 1.0*
*Compatible with: ScalarDB 3.17+*
