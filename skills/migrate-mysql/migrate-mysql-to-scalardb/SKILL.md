---
name: migrate-mysql-to-scalardb
description: Generates ScalarDB migration documentation from MySQL schema analysis. Consumes the MySQL schema analysis Markdown file from the configured output directory as input and produces migration analysis and step-by-step migration guides.
---

# Migrate MySQL to ScalarDB Skill

## Purpose

Generate comprehensive **ScalarDB migration documentation** from an existing MySQL schema analysis report. This skill focuses solely on the migration analysis and documentation logic.

**Key Statement**: This skill consumes the MySQL schema analysis Markdown file from the shared `OUTPUT_DIR` as input.

---

## Skill Responsibility

This skill is responsible for:
- Reading and parsing MySQL schema analysis input
- Performing migration compatibility analysis
- Calculating migration complexity and effort
- Generating migration documentation

This skill is **NOT** responsible for:
- Orchestration or command handling (handled by `/mysql-to-scalardb` command)
- User interaction or query parsing
- Configuration loading (received from command)

---

## Input Contract

The skill receives the following inputs from the command layer:

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `mysql_schema_report` | File path | YES | Path to `mysql_schema_report.md` from Skill 1 |
| `raw_schema_data` | File path | NO | Path to `raw_mysql_schema_data.json` for additional lookup |
| `output_directory` | Directory | YES | Shared output directory (from `.env`) |
| `namespace` | String | NO | Target ScalarDB namespace |

**Note**: Configuration is centralized in `.claude/configuration/databases.env`. Both skills read from this single file.

---

## Output Contract

The skill produces the following outputs:

| Output | File | Description |
|--------|------|-------------|
| Migration Analysis | `scalardb_mysql_migration_analysis.md` | Compatibility analysis, data type mappings, risk assessment |
| Migration Steps | `scalardb_mysql_migration_steps.md` | Step-by-step migration guide with code examples |
| Complexity Score | (in report) | Calculated score 0-10 |
| Effort Rating | (in report) | LOW/MEDIUM/HIGH/VERY HIGH |

---

## Naming Conventions

### Table and Column Names — Use Exact Names from `raw_mysql_schema_data.json`

**Do NOT normalize table names or column names to lowercase or uppercase.**

MySQL's case sensitivity depends on the platform and configuration (`lower_case_table_names` setting). On Linux it is case-sensitive by default; on Windows it is not. The actual stored names vary per database instance. The `raw_mysql_schema_data.json` is extracted directly from the MySQL information schema and always reflects the exact stored name for that specific instance.

**Rule:** Use table names and column names exactly as they appear in `raw_mysql_schema_data.json` in all generated output — migration analysis documents, ScalarDB schema configuration examples, and Java code snippets. Never assume uppercase or lowercase.

```java
// Use whatever casing raw_mysql_schema_data.json shows — do not change it
Get get = Get.newBuilder()
    .namespace("shop")                              // namespace from config
    .table("Orders")                                // use exact name from JSON
    .partitionKey(Key.ofInt("order_id", orderId))   // use exact name from JSON
    .build();
```

---

## Skill Logic

### 1. Parse Input

Read `mysql_schema_report.md` and extract:
- Table definitions and columns
- Data types for mapping
- Constraints for migration planning
- Stored programs for application migration planning

### 2. Perform Type Mapping

Map each MySQL data type to ScalarDB equivalent:

| MySQL Type | ScalarDB Type | Notes |
|------------|---------------|-------|
| bigint | BIGINT | Range: -2^53 to 2^53 |
| binary | BLOB | |
| bit | BOOLEAN | |
| blob, *blob | BLOB | Max ~2GB |
| char, varchar | TEXT | |
| text, *text | TEXT | |
| date | DATE | |
| datetime | TIMESTAMP/TIMESTAMPTZ | |
| double | DOUBLE | |
| float | FLOAT | |
| int, integer | INT | |
| int unsigned | BIGINT | |
| mediumint, smallint, tinyint | INT | |
| time | TIME | |
| timestamp | TIMESTAMPTZ | |
| tinyint(1) | BOOLEAN | |
| varbinary | BLOB | |
| decimal, numeric | NOT SUPPORTED | Use DOUBLE (precision loss) |
| enum | NOT SUPPORTED | Use TEXT |
| set | NOT SUPPORTED | Use TEXT |
| json | NOT SUPPORTED | Use TEXT |
| geometry, point, etc. | NOT SUPPORTED | No spatial support |
| year | NOT SUPPORTED | Use INT |
| bigint unsigned | NOT SUPPORTED | Exceeds range |
| bit(n) where n > 1 | NOT SUPPORTED | |

### 3. Calculate Complexity Score

Apply weighted scoring model:

```
Total = (Data Type x 0.20) + (Schema x 0.25) + (Stored Programs x 0.25) + (App Impact x 0.30)
```

#### Data Type Complexity (0-10)

| Score | Criteria |
|-------|----------|
| 0-2 | Standard types only (INT, VARCHAR, DATE, etc.) |
| 3-4 | Some LOBs (BLOB, TEXT) requiring size validation |
| 5-6 | DECIMAL columns requiring precision handling |
| 7-8 | JSON columns requiring TEXT conversion |
| 9-10 | ENUM, SET, spatial types |

#### Schema Complexity (0-10)

| Score | Criteria |
|-------|----------|
| 0-2 | Simple tables with standard constraints |
| 3-4 | Foreign keys, composite primary keys |
| 5-6 | Views requiring conversion |
| 7-8 | Partitioned tables, generated columns |
| 9-10 | Multiple unsupported features |

#### Stored Programs Complexity (0-10)

| Score | Criteria |
|-------|----------|
| 0 | No stored programs |
| 1-3 | Simple procedures/functions (<10) |
| 4-6 | Moderate (10-50 objects, some triggers) |
| 7-8 | Complex (50+ objects, events) |
| 9-10 | Heavy business logic in database |

#### Application Impact (0-10)

| Score | Criteria |
|-------|----------|
| 0-2 | Simple CRUD operations only |
| 3-4 | JOINs, basic transactions, aggregations |
| 5-6 | **Subqueries** - require decomposition or Analytics |
| 7-8 | **Window functions, complex subqueries** - require Analytics |
| 8-9 | Complex queries with stored procedure dependencies |
| 9-10 | Heavy database-side logic, triggers for business rules |

### 4. Generate Reports

Using templates, generate:
1. `scalardb_mysql_migration_analysis.md` - Analysis report
2. `scalardb_mysql_migration_steps.md` - Step-by-step guide

---

## ScalarDB SQL Capabilities

### Supported SQL Features

| Feature | Support | Notes |
|---------|---------|-------|
| SELECT, INSERT, UPDATE, DELETE | Supported | Standard DML operations |
| JOIN (INNER, LEFT, RIGHT) | Limited | See limitations below |
| WHERE clauses | Limited | Must use DNF or CNF form |
| ORDER BY, LIMIT | Supported | |
| GROUP BY, HAVING | Supported | |
| COUNT, SUM, AVG, MIN, MAX | Supported | |
| CREATE/DROP TABLE | Supported | DDL operations |
| CREATE INDEX | Supported | Secondary indexes |

---

## ScalarDB SQL Limitations (CRITICAL)

> **Reference**: https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/grammar/

### 1. JOIN Limitations

| Aspect | ScalarDB Behavior | Impact |
|--------|-------------------|--------|
| Cross-partition JOINs | May cause cross-partition scans | Performance degradation |
| Multi-table JOINs | Not optimized like MySQL | Complex queries may be slow |
| Execution model | Partition-based Get/Scan operations | JOINs resolved per-partition |

**Recommendation**: For complex multi-table JOINs, use **ScalarDB Analytics** instead.

### 2. WHERE Clause Restrictions

| Restriction | Description |
|-------------|-------------|
| Predicate Form | Must be in **DNF** (OR-of-ANDs) or **CNF** (AND-of-ORs) |
| Arbitrary combinations | May not parse correctly |
| Partition key | Should include partition key for optimal performance |

### 3. Features NOT Supported in ScalarDB SQL

| Feature | Workaround |
|---------|------------|
| Subqueries | Sequential queries or **ScalarDB Analytics** |
| UNION/INTERSECT/EXCEPT | Multiple queries + application merge |
| Window functions | **ScalarDB Analytics** |
| AUTO_INCREMENT | UUID or application-level ID generator |
| Stored procedures | Convert to application methods |
| Triggers | Application-level event handling |
| Events | External scheduler (cron, Kubernetes CronJob) |

---

## ScalarDB Analytics (REQUIRED for Complex Queries)

> **When to Use**: If your MySQL schema uses complex JOINs, subqueries, window functions, or analytical queries, you **MUST** plan for ScalarDB Analytics deployment.

### Decision Matrix

| Query Pattern | ScalarDB SQL | ScalarDB Analytics |
|---------------|--------------|-------------------|
| Simple CRUD (single table) | Use | Not needed |
| Single-partition queries | Use | Not needed |
| Simple 2-table JOINs (same partition) | Use | Not needed |
| Multi-table JOINs (cross-partition) | Performance issues | **Use Analytics** |
| Subqueries | Not supported | **Required** |
| Window functions | Not supported | **Required** |
| Complex aggregations | Limited | **Recommended** |
| UNION/INTERSECT/EXCEPT | Not supported | **Required** |

### Analytics Reference

| Reference | URL |
|-----------|-----|
| ScalarDB Analytics Overview | https://scalardb.scalar-labs.com/docs/latest/scalardb-analytics/ |
| ScalarDB Analytics Quickstart | https://scalardb.scalar-labs.com/docs/3.16/scalardb-analytics/quickstart/ |

---

## ScalarDB Advanced Features

### Vector Search (Enterprise Premium)

ScalarDB supports vector search for RAG and AI-driven use cases:
- Embedding storage and similarity search
- Integration with LangChain4j
- Supports OpenSearch, pgvector, Azure AI Search

**Reference**: https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/getting-started-with-vector-search/

### Object Storage Backend (Private Preview)

ScalarDB can use object storage as a backend:
- Amazon S3
- Azure Blob Storage
- Google Cloud Storage

**References**:
- https://scalardb.scalar-labs.com/docs/latest/requirements/#object-storage
- https://scalardb.scalar-labs.com/docs/latest/configurations/?databases=S3#storage-related-configurations

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

**Reference**: https://scalardb.scalar-labs.com/docs/latest/schema-loader-import/#decoupling-transaction-metadata

---

## MySQL Feature Mapping

### Fully Supported (ScalarDB SQL)

- Tables with standard data types
- Primary keys -> partition-key + clustering-key
- Basic indexes -> secondary-index
- Simple SELECT, INSERT, UPDATE, DELETE
- JOIN queries (2-3 tables)
- GROUP BY with aggregates (v3.17+)

### Partially Supported

- Foreign keys -> Application-level enforcement
- Check constraints -> Application-level validation
- BLOB/TEXT -> BLOB/TEXT (size limits)
- Views -> Import as tables or queries

### Requires Workaround

| Feature | Workaround |
|---------|------------|
| Subqueries | Sequential queries or ScalarDB Analytics |
| AUTO_INCREMENT | UUID or application-level ID |
| Triggers | Application event handling |
| Stored procedures | Application methods |
| Stored functions | Application methods |
| Events | External scheduler |
| ENUM/SET | TEXT with application validation |
| JSON | TEXT with application parsing |
| DECIMAL | DOUBLE (accept precision loss) or TEXT |
| Spatial types | NOT SUPPORTED |

---

## Files in This Skill

```
skills/migrate-mysql-to-scalardb/
├── SKILL.md                                   # This file
├── reference/
│   └── scalardb_mysql_reference.md            # Complete ScalarDB reference for MySQL
└── templates/
    ├── scalardb_mysql_migration_analysis.md   # Analysis report template
    └── scalardb_mysql_migration_steps.md      # Steps guide template
```

**Configuration file** (in `.claude/configuration/`):
| `databases.env` | Consolidated database configuration (Oracle, MySQL, PostgreSQL) |

---

## Related

- **Command**: `commands/mysql-to-scalardb.md` (orchestration)
- **Prerequisite Skill**: `skills/analyze-mysql-schema/` (input provider)

---

*Skill Version: 1.0*
*Compatible with: ScalarDB 3.17+*
