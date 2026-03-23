---
name: migrate-oracle-to-scalardb
description: Generates ScalarDB migration documentation from Oracle schema analysis. Consumes the Oracle schema analysis Markdown file from the configured output directory as input and produces migration analysis and step-by-step migration guides.
---

# Migrate to ScalarDB Schema Skill

## Purpose

Generate comprehensive **ScalarDB migration documentation** from an existing Oracle schema analysis report. This skill focuses solely on the migration analysis and documentation logic.

**Key Statement**: This skill consumes the Oracle schema analysis Markdown file from the shared `OUTPUT_DIR` as input.

---

## Skill Responsibility

This skill is responsible for:
- Reading and parsing Oracle schema analysis input
- Performing migration compatibility analysis
- Calculating migration complexity and effort
- Generating migration documentation

This skill is **NOT** responsible for:
- Orchestration or command handling (handled by `/migrate-oracle-to-scalardb` command)
- User interaction or query parsing
- Configuration loading (received from command)

---

## Input Contract

The skill receives the following inputs from the command layer:

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `oracle_schema_report` | File path | YES | Path to `oracle_schema_report.md` from Skill 1 |
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

Oracle's behavior depends on how the object was created:
- **Unquoted identifiers** (e.g., `CREATE TABLE employees`) → Oracle stores them as `EMPLOYEES`
- **Quoted identifiers** (e.g., `CREATE TABLE "employees"`) → Oracle stores them as `employees` exactly

The `raw_schema_data.json` is extracted directly from Oracle's data dictionary and always reflects the exact stored name — regardless of how the object was originally created. This is the **single source of truth** for names.

**Rule:** Use table names and column names exactly as they appear in `raw_schema_data.json` in all generated output — migration analysis documents, ScalarDB schema configuration examples, and Java code snippets. Never assume uppercase or lowercase.

```java
// If raw_schema_data.json has "table_name": "EMPLOYEES" → use EMPLOYEES
Get get = Get.newBuilder()
    .namespace("hr")                                     // namespace from config
    .table("EMPLOYEES")                                  // use exact name from JSON
    .partitionKey(Key.ofInt("EMPLOYEE_ID", employeeId))  // use exact name from JSON
    .build();

// If raw_schema_data.json has "table_name": "employees" → use employees
Get get = Get.newBuilder()
    .namespace("hr")                                     // namespace from config
    .table("employees")                                  // use exact name from JSON
    .partitionKey(Key.ofInt("employee_id", employeeId))
    .build();
```

---

## Skill Logic

### 1. Parse Input

Read `oracle_schema_report.md` and extract:
- Table definitions and columns
- Data types for mapping
- Constraints for migration planning
- Custom types for flattening analysis
- PL/SQL objects for application migration planning

### 2. Perform Type Mapping

Map each Oracle data type to ScalarDB equivalent:

| Oracle Type | ScalarDB Type | Notes |
|-------------|---------------|-------|
| NUMBER(1) | BOOLEAN | |
| NUMBER(p,0) p≤9 | INT | |
| NUMBER(p,0) p≤18 | BIGINT | |
| NUMBER(p,s) s>0 | DOUBLE | |
| VARCHAR2, CHAR | TEXT | |
| CLOB, NCLOB | TEXT | |
| DATE | DATE | |
| TIMESTAMP | TIMESTAMP | |
| TIMESTAMP WITH TIME ZONE | TIMESTAMPTZ | |
| BLOB, RAW | BLOB | Max ~2GB |
| BFILE | NOT SUPPORTED | Requires workaround |
| Object Types | NOT SUPPORTED | Flatten to columns |
| Nested Tables | NOT SUPPORTED | Separate table |

### 3. Calculate Complexity Score

Apply weighted scoring model:

```
Total = (Data Type × 0.20) + (Schema × 0.25) + (PL/SQL × 0.25) + (App Impact × 0.30)
```

#### Data Type Complexity (0-10)

| Score | Criteria |
|-------|----------|
| 0-2 | Standard types only |
| 3-4 | LOBs requiring size validation |
| 5-6 | BFILE, complex NUMBER precision |
| 7-8 | Object types requiring flattening |
| 9-10 | Nested tables, VARRAYs, collections |

#### Schema Complexity (0-10)

| Score | Criteria |
|-------|----------|
| 0-2 | Simple tables, standard constraints |
| 3-4 | Foreign keys, composite PKs |
| 5-6 | Views requiring conversion |
| 7-8 | Materialized views, partitions |
| 9-10 | Object types, nested tables, inheritance |

#### PL/SQL Complexity (0-10)

| Score | Criteria |
|-------|----------|
| 0 | No PL/SQL |
| 1-3 | Simple procedures (<10) |
| 4-6 | Moderate (10-50 objects) |
| 7-8 | Complex (50+ objects) |
| 9-10 | Heavy business logic in DB |

#### Application Impact (0-10)

| Score | Criteria |
|-------|----------|
| 0-2 | Simple CRUD only |
| 3-4 | JOINs, basic transactions, aggregations |
| 5-6 | Subqueries - require decomposition |
| 7-8 | Complex subqueries, window functions |
| 9-10 | Heavy DB-side logic, stored procedures |

### 4. Generate Reports

Using templates, generate:
1. `scalardb_migration_analysis.md` - Analysis report
2. `scalardb_migration_steps.md` - Step-by-step guide

---

## ScalarDB SQL Capabilities

### Supported SQL Features

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
| Multi-table JOINs | Not optimized like MySQL/Oracle | Complex queries may be slow |
| Execution model | Partition-based Get/Scan operations | JOINs resolved per-partition |

**Recommendation**: For complex multi-table JOINs, use **ScalarDB Analytics** instead.

### 2. WHERE Clause Restrictions

| Restriction | Description |
|-------------|-------------|
| Predicate Form | Must be in **DNF** (OR-of-ANDs) or **CNF** (AND-of-ORs) |
| Arbitrary combinations | May not parse correctly |
| Partition key | Should include partition key for optimal performance |

### 3. Cross-Partition Operations

| Operation | Behavior |
|-----------|----------|
| UPDATE without partition key | Requires cross-partition scan |
| DELETE without partition key | Requires cross-partition scan |
| Full table scan | Must be explicitly enabled; impacts performance |

### 4. Encrypted Columns Restrictions

| Feature | Encrypted Columns |
|---------|-------------------|
| WHERE conditions | ❌ NOT allowed |
| ORDER BY clauses | ❌ NOT allowed |
| Secondary indexes | ❌ Cannot be created |

### 5. Secondary Index Limitations

| Restriction | Description |
|-------------|-------------|
| Encrypted tables | Cannot create secondary indexes |
| Object storage backends | May not support secondary indexes |

### 6. Features NOT Supported in ScalarDB SQL

| Feature | Workaround |
|---------|------------|
| Subqueries | Sequential queries or **ScalarDB Analytics** |
| UNION/INTERSECT/EXCEPT | Multiple queries + application merge |
| Window functions (ROW_NUMBER, RANK) | **ScalarDB Analytics** |
| Complex aggregations | **ScalarDB Analytics** |
| Stored procedures | Convert to application methods |
| Triggers | Application-level event handling |
| Sequences | UUID or application-level ID generation |

---

## ScalarDB Analytics (REQUIRED for Complex Queries)

> **When to Use**: If your Oracle schema uses complex JOINs, subqueries, window functions, or analytical queries, you **MUST** plan for ScalarDB Analytics deployment.

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

### Analytics Setup Requirements

When ScalarDB Analytics is required:

1. **Additional Infrastructure**: ScalarDB Analytics server deployment
2. **Configuration**: Analytics-specific properties file
3. **Dependencies**: Additional Maven/Gradle dependencies
4. **Query Routing**: Application must route queries appropriately

### Analytics Reference

| Reference | URL |
|-----------|-----|
| ScalarDB Analytics Overview | https://scalardb.scalar-labs.com/docs/latest/scalardb-analytics/ |
| Analytics CLI Reference | https://scalardb.scalar-labs.com/docs/latest/scalardb-analytics/reference-cli-command/ |

---

## ScalarDB Component Strategy

| Component | When to Use | License |
|-----------|-------------|---------|
| **ScalarDB Core** (Java Transaction API) | Default — CRUD operations, schema import, application access | Open Source / Community |
| **ScalarDB Cluster** (SQL interface) | Only if SQL interface needed, or aggregate functions for small use cases | Enterprise |
| **ScalarDB Analytics** | Complex queries: multi-table JOINs (3+), subqueries, window functions, reporting | Enterprise |

Start with ScalarDB Core. Add Cluster only if a SQL interface is specifically needed. Use Analytics for complex queries that cannot be decomposed into simple CRUD.

### Oracle AQ Decision

**If the Oracle database contains triggers or stored procedures that perform DML on other tables, Oracle AQ MUST be used.** This is a design decision, not optional. The goal is to preserve existing database behavior unchanged while routing writes through ScalarDB.

### Mandatory References

| Reference | URL |
|-----------|-----|
| **ScalarDB Java Transaction API** | https://scalardb.scalar-labs.com/docs/latest/api-guide/ |
| **ScalarDB SQL Grammar (Reference)** | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/grammar/ |
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

---

## Oracle Feature Mapping

### Fully Supported (ScalarDB SQL)

- Tables with standard data types
- Primary keys → partition-key + clustering-key
- Basic indexes → secondary-index
- Simple SELECT, INSERT, UPDATE, DELETE
- JOIN queries (2-3 tables)
- GROUP BY with aggregates (v3.17+)

### Partially Supported

- Foreign keys → Application-level enforcement
- Check constraints → Application-level validation
- CLOB/BLOB → TEXT/BLOB (size limits)
- Views → Import as tables or queries

### Requires Workaround

| Feature | Workaround |
|---------|------------|
| Subqueries | Sequential queries or ScalarDB Analytics |
| Sequences | UUID or application-level ID |
| Triggers | Application event handling |
| Stored procedures | Application methods |
| Object types | Flatten to columns |
| Nested tables | Separate tables with FK |

---

## Files in This Skill

```
skills/migrate-oracle-to-scalardb/
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

- **Command**: `commands/migrate-oracle-to-scalardb.md` (orchestration)
- **Prerequisite Skill**: `skills/analyze-oracle-schema/` (input provider)

---

*Skill Version: 1.2*
*Compatible with: ScalarDB 3.17+*
