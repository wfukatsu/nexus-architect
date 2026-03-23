# ScalarDB Migration Analysis Report Template (PostgreSQL)

This template is used to generate the **migration analysis** report for PostgreSQL to ScalarDB migration. Replace all `{{PLACEHOLDER}}` tokens with actual values from the source PostgreSQL schema report.

**Input Source**: This report consumes `postgresql_schema_report.md` from the configured output directory (analyze-postgresql-schema output).

---

# PostgreSQL to ScalarDB Migration Analysis

**Generated**: {{TIMESTAMP}}
**Source Database**: {{DATABASE_NAME}}
**Source Schema**: {{SCHEMA_NAME}}
**PostgreSQL Version**: {{POSTGRES_VERSION}}
**Target**: ScalarDB 3.17+
**Primary Migration Path**: ScalarDB SQL (JDBC)

---

## RECOMMENDED: Transaction Metadata Decoupling

> **For this migration, we recommend using `transaction-metadata-decoupling: true` instead of `transaction: true`.**

This approach keeps your **existing PostgreSQL tables unchanged** - ScalarDB stores its transaction metadata in separate `<table>_scalardb` tables.

| Approach | Alters Existing Tables? | Recommended For |
|----------|------------------------|-----------------|
| `transaction: true` | YES - adds columns | New tables only |
| `transaction-metadata-decoupling: true` | **NO - tables unchanged** | **Migrating existing tables** |

**Reference**: https://scalardb.scalar-labs.com/docs/latest/schema-loader-import/#decoupling-transaction-metadata

---

## 1. Executive Summary

### Migration Scope Overview

| Object Type | Count | ScalarDB Compatibility | Migration Effort |
|-------------|-------|------------------------|------------------|
| Tables | {{TABLE_COUNT}} | {{TABLE_COMPAT}} | {{TABLE_EFFORT}} |
| ENUM Types | {{ENUM_COUNT}} | {{ENUM_COMPAT}} | {{ENUM_EFFORT}} |
| Composite Types | {{COMPOSITE_COUNT}} | {{COMPOSITE_COMPAT}} | {{COMPOSITE_EFFORT}} |
| Domain Types | {{DOMAIN_COUNT}} | {{DOMAIN_COMPAT}} | {{DOMAIN_EFFORT}} |
| Array Columns | {{ARRAY_COUNT}} | {{ARRAY_COMPAT}} | {{ARRAY_EFFORT}} |
| JSON/JSONB Columns | {{JSON_COUNT}} | {{JSON_COMPAT}} | {{JSON_EFFORT}} |
| Indexes | {{INDEX_COUNT}} | {{INDEX_COMPAT}} | {{INDEX_EFFORT}} |
| Views | {{VIEW_COUNT}} | {{VIEW_COMPAT}} | {{VIEW_EFFORT}} |
| Materialized Views | {{MVIEW_COUNT}} | {{MVIEW_COMPAT}} | {{MVIEW_EFFORT}} |
| Functions | {{FUNC_COUNT}} | {{FUNC_COMPAT}} | {{FUNC_EFFORT}} |
| Procedures | {{PROC_COUNT}} | {{PROC_COMPAT}} | {{PROC_EFFORT}} |
| Triggers | {{TRIGGER_COUNT}} | {{TRIGGER_COMPAT}} | {{TRIGGER_EFFORT}} |
| Sequences | {{SEQ_COUNT}} | {{SEQ_COMPAT}} | {{SEQ_EFFORT}} |
| RLS Policies | {{RLS_COUNT}} | {{RLS_COMPAT}} | {{RLS_EFFORT}} |
| Extensions | {{EXT_COUNT}} | {{EXT_COMPAT}} | {{EXT_EFFORT}} |

### Compatibility Summary

| Category | Count | Percentage |
|----------|-------|------------|
| Fully Compatible | {{FULL_COMPAT_COUNT}} | {{FULL_COMPAT_PCT}}% |
| Compatible with Changes | {{PARTIAL_COMPAT_COUNT}} | {{PARTIAL_COMPAT_PCT}}% |
| Requires Application Logic | {{APP_LOGIC_COUNT}} | {{APP_LOGIC_PCT}}% |
| Not Supported | {{NOT_SUPPORTED_COUNT}} | {{NOT_SUPPORTED_PCT}}% |

### Risk Assessment

| Risk Level | Description | Objects Affected |
|------------|-------------|------------------|
| HIGH | {{HIGH_RISK_DESC}} | {{HIGH_RISK_OBJECTS}} |
| MEDIUM | {{MEDIUM_RISK_DESC}} | {{MEDIUM_RISK_OBJECTS}} |
| LOW | {{LOW_RISK_DESC}} | {{LOW_RISK_OBJECTS}} |

---

## 2. Data Type Mapping Analysis (Official ScalarDB Documentation)

> **Reference**: https://scalardb.scalar-labs.com/docs/latest/schema-loader-import#data-type-mapping-from-jdbc-databases-to-scalardb

> ⚠️ **CRITICAL**: Only the data types listed below are officially supported. **Data types NOT listed in the official documentation are NOT SUPPORTED.** This includes any PostgreSQL extensions, custom types, or unlisted built-in types.

### Supported PostgreSQL Data Types (ONLY THESE 14 TYPES)

The following data types are **SUPPORTED** for ScalarDB import:

| PostgreSQL Type | ScalarDB Type | Notes |
|-----------------|---------------|-------|
| bigint | BIGINT | ⚠️ Range: -2^53 to 2^53 only |
| boolean | BOOLEAN | Direct mapping |
| bytea | BLOB | Max ~2GB (2^31-1 bytes) |
| character | TEXT | ⚠️ Size mapping warnings |
| character varying | TEXT | ⚠️ Size mapping warnings |
| date | DATE | Direct mapping |
| double precision | DOUBLE | Direct mapping |
| integer | INT | Direct mapping |
| real | FLOAT | Direct mapping |
| smallint | INT | ⚠️ Maps to larger type |
| text | TEXT | Direct mapping |
| time | TIME | Without timezone |
| timestamp | TIMESTAMP | Direct mapping |
| timestamp with time zone | TIMESTAMPTZ | Direct mapping |

### NOT Supported Data Types (Official)

> **Data types not listed above are NOT SUPPORTED.** The following are common data types that are explicitly NOT supported:

| Category | Unsupported Types |
|----------|-------------------|
| Serial/Sequence | bigserial, serial, smallserial |
| Numeric | numeric, money |
| Binary | bit |
| Date/Time | interval, time with time zone |
| JSON | json, jsonb |
| UUID | uuid |
| XML | xml |
| Network | inet, cidr, macaddr, macaddr8 |
| Geometric | point, line, lseg, box, path, polygon, circle |
| Text Search | tsvector, tsquery |
| System | pg_lsn, pg_snapshot, txid_snapshot |
| Arrays | All array types (e.g., integer[], text[]) |
| Range Types | All range types (e.g., int4range, daterange) |
| ENUM Types | User-defined ENUM types |
| Composite Types | User-defined composite types |
| Domain Types | User-defined domain types |
| Extension Types | PostGIS, hstore, ltree, citext, etc. |
| Any Other Types | Any PostgreSQL type not in the 14 supported types above |

### Type Conversion Summary for This Schema

| PostgreSQL Column | PostgreSQL Type | ScalarDB Type | Conversion Notes | Risk |
|-------------------|-----------------|---------------|------------------|------|
| {{TABLE}}.{{COLUMN}} | {{PG_TYPE}} | {{SCALARDB_TYPE}} | {{NOTES}} | {{RISK}} |

### Type Statistics

| PostgreSQL Type | Count | ScalarDB Type | Conversion Status |
|-----------------|-------|---------------|-------------------|
| {{PG_TYPE}} | {{COUNT}} | {{SCALARDB_TYPE}} | {{STATUS}} |

### Critical Data Type Warnings (Official)

#### ⚠️ Warning 1: BIGINT Range Limitation
> The value range of BIGINT in ScalarDB is from **-2^53 to 2^53** (-9,007,199,254,740,992 to 9,007,199,254,740,992), regardless of the size of bigint in the underlying database. If data outside this range exists in the imported table, ScalarDB cannot read it.

- **Affected Columns**: {{BIGINT_AFFECTED_COLS}}
- **Action Required**: {{BIGINT_ACTION}}

#### ⚠️ Warning 2: Size Mapping for character/character varying/smallint
> For certain data types (character, character varying, smallint), ScalarDB may map a data type larger than that of the underlying database. You will see errors when putting a value with a size larger than the size specified in the underlying database.

- **Affected Columns**: {{CHAR_AFFECTED_COLS}}
- **Action Required**: Validate size constraints during data insertion

#### ⚠️ Warning 3: BLOB Size Limitation
> The maximum size of BLOB in ScalarDB is about 2GB (precisely 2^31-1 bytes).

- **Affected Columns**: {{BLOB_AFFECTED_COLS}}
- **Action Required**: {{BLOB_ACTION}}

### Unsupported Types in This Schema

#### NUMERIC Columns (NOT SUPPORTED)
- **Affected Columns**: {{NUMERIC_AFFECTED_COLS}}
- **Migration**: Convert to DOUBLE (precision loss) or TEXT (preserve exact value)

#### JSON/JSONB Columns (NOT SUPPORTED)
- **Affected Columns**: {{JSON_AFFECTED_COLS}}
- **Migration**: Store as TEXT, implement JSON parsing in application

#### UUID Columns (NOT SUPPORTED)
- **Affected Columns**: {{UUID_AFFECTED_COLS}}
- **Migration**: Store as TEXT (36 characters)

#### Array Type Columns (NOT SUPPORTED)
- **Affected Columns**: {{ARRAY_AFFECTED_COLS}}
- **Migration**: Normalize to separate child tables

#### Serial/Identity Columns (NOT SUPPORTED)
- **Affected Columns**: {{SERIAL_AFFECTED_COLS}}
- **Migration**: Use UUID or application-level ID generation

---

## 3. Table Analysis

### Table Compatibility Matrix

| Table Name | Columns | Has PK | Has Arrays | Has JSON | Has Custom Types | Partitioned | Compatibility |
|------------|---------|--------|------------|----------|------------------|-------------|---------------|
| {{TABLE_NAME}} | {{COL_COUNT}} | {{HAS_PK}} | {{HAS_ARRAYS}} | {{HAS_JSON}} | {{HAS_CUSTOM_TYPES}} | {{PARTITIONED}} | {{COMPAT_STATUS}} |

### Detailed Table Analysis

#### Table: {{TABLE_NAME}}

**PostgreSQL Structure:**
- Columns: {{COLUMN_COUNT}}
- Primary Key: {{PK_COLUMNS}}
- Has SERIAL/IDENTITY: {{HAS_SERIAL}}
- Has Array Columns: {{HAS_ARRAY_COLUMNS}}
- Has JSON/JSONB: {{HAS_JSON_COLUMNS}}

**Column Mapping:**

| Column | PostgreSQL Type | ScalarDB Type | Nullable | Notes |
|--------|-----------------|---------------|----------|-------|
| {{COLUMN_NAME}} | {{PG_TYPE}} | {{SCALARDB_TYPE}} | {{NULLABLE}} | {{NOTES}} |

**ScalarDB Key Design:**
- **Partition Key**: {{PARTITION_KEY}}
- **Clustering Key**: {{CLUSTERING_KEY}}
- **Secondary Indexes**: {{SECONDARY_INDEXES}}

**Migration Notes:**
{{TABLE_MIGRATION_NOTES}}

---

## 4. Custom Types Analysis

### ENUM Types

| Type Name | Values | Used By | Migration Approach |
|-----------|--------|---------|-------------------|
| {{ENUM_NAME}} | {{ENUM_VALUES}} | {{USED_BY}} | TEXT + application validation |

### ENUM Type Migration Plan

#### Type: {{ENUM_NAME}}

**Original Definition:**
```sql
CREATE TYPE {{ENUM_NAME}} AS ENUM ({{ENUM_VALUES}});
```

**Migration Strategy:**
- Convert column to TEXT in ScalarDB
- Add application-level validation for allowed values
- Consider using CHECK constraint in underlying database if supported

### Composite Types

| Type Name | Attributes | Used In | Migration Approach |
|-----------|------------|---------|-------------------|
| {{COMPOSITE_NAME}} | {{ATTR_COUNT}} | {{USED_IN}} | Flatten to columns |

### Composite Type Flattening Plan

#### Type: {{COMPOSITE_NAME}}

**Original Attributes:**
| Attribute | Data Type | ScalarDB Equivalent |
|-----------|-----------|---------------------|
| {{ATTR_NAME}} | {{ATTR_TYPE}} | {{SCALARDB_TYPE}} |

**Flattening Strategy:**
- Prefix: `{{PREFIX}}_`
- Target Columns: {{FLATTENED_COLUMNS}}

### Domain Types

| Type Name | Base Type | Constraints | Migration Approach |
|-----------|-----------|-------------|-------------------|
| {{DOMAIN_NAME}} | {{BASE_TYPE}} | {{CONSTRAINTS}} | Use base type + app validation |

### Array Columns Migration Plan

| Parent Table | Array Column | Element Type | Migration Strategy |
|--------------|--------------|--------------|-------------------|
| {{PARENT_TABLE}} | {{ARRAY_COL}} | {{ELEMENT_TYPE}} | {{STRATEGY}} |

**Array Normalization Example:**

Original:
```sql
CREATE TABLE {{PARENT_TABLE}} (
    id SERIAL PRIMARY KEY,
    {{ARRAY_COL}} {{ELEMENT_TYPE}}[]
);
```

ScalarDB (normalized):
```json
{
  "{{NAMESPACE}}.{{PARENT_TABLE}}": {
    "transaction-metadata-decoupling": true,
    "partition-key": ["id"],
    "columns": {
      "id": "BIGINT"
    }
  },
  "{{NAMESPACE}}.{{PARENT_TABLE}}_{{ARRAY_COL}}": {
    "transaction-metadata-decoupling": true,
    "partition-key": ["parent_id"],
    "clustering-key": ["item_index ASC"],
    "columns": {
      "parent_id": "BIGINT",
      "item_index": "INT",
      "value": "{{SCALARDB_TYPE}}"
    }
  }
}
```

---

## 5. Constraint Analysis

### Primary Keys

| Table | Constraint Name | Columns | ScalarDB Mapping |
|-------|-----------------|---------|------------------|
| {{TABLE}} | {{PK_NAME}} | {{PK_COLUMNS}} | partition-key / clustering-key |

### Foreign Keys

| Table | Constraint | References | On Delete | Migration Impact |
|-------|------------|------------|-----------|------------------|
| {{TABLE}} | {{FK_NAME}} | {{REF_TABLE}}.{{REF_COLS}} | {{DELETE_RULE}} | Application-level enforcement |

**Foreign Key Migration Strategy:**
- ScalarDB does not enforce referential integrity at the database level
- All FK relationships must be enforced in application code
- Consider using two-phase commit patterns for cross-table consistency

### Unique Constraints

| Table | Constraint | Columns | Migration Approach |
|-------|------------|---------|-------------------|
| {{TABLE}} | {{UK_NAME}} | {{UK_COLUMNS}} | {{APPROACH}} |

### Check Constraints

| Table | Constraint | Condition | Migration Approach |
|-------|------------|-----------|-------------------|
| {{TABLE}} | {{CK_NAME}} | {{CONDITION}} | Application validation |

---

## 6. Index Analysis

### Index Migration Matrix

| Index Name | Table | Type | Columns | ScalarDB Support | Migration |
|------------|-------|------|---------|------------------|-----------|
| {{INDEX_NAME}} | {{TABLE}} | {{INDEX_TYPE}} | {{COLUMNS}} | {{SUPPORT}} | {{MIGRATION}} |

### Primary Key Indexes
- Automatically handled by partition-key and clustering-key definitions

### Secondary Indexes
| Index | Table | Column | ScalarDB secondary-index |
|-------|-------|--------|-------------------------|
| {{INDEX}} | {{TABLE}} | {{COLUMN}} | {{RECOMMENDATION}} |

### Partial Indexes (NOT SUPPORTED)
| Index | Table | WHERE Condition | Workaround |
|-------|-------|-----------------|------------|
| {{INDEX}} | {{TABLE}} | {{WHERE}} | Application-level filtering |

### Expression Indexes (NOT SUPPORTED)
| Index | Table | Expression | Workaround |
|-------|-------|------------|------------|
| {{INDEX}} | {{TABLE}} | {{EXPRESSION}} | Consider additional computed column |

### GiST/GIN/BRIN Indexes (NOT SUPPORTED)
| Index | Type | Table | Workaround |
|-------|------|-------|------------|
| {{INDEX}} | {{TYPE}} | {{TABLE}} | Use standard B-tree or external search |

---

## 7. PL/pgSQL Objects Analysis

### Functions

| Function | Language | Parameters | Return Type | Complexity | Migration Effort |
|----------|----------|------------|-------------|------------|------------------|
| {{FUNC_NAME}} | {{LANGUAGE}} | {{PARAM_COUNT}} | {{RETURN_TYPE}} | {{COMPLEXITY}} | {{EFFORT}} |

### Procedures (PostgreSQL 11+)

| Procedure | Language | Parameters | Complexity | Migration Effort |
|-----------|----------|------------|------------|------------------|
| {{PROC_NAME}} | {{LANGUAGE}} | {{PARAM_COUNT}} | {{COMPLEXITY}} | {{EFFORT}} |

### Triggers

| Trigger | Table | Event | Timing | Migration Approach |
|---------|-------|-------|--------|-------------------|
| {{TRIGGER_NAME}} | {{TABLE}} | {{EVENT}} | {{TIMING}} | {{APPROACH}} |

### Event Triggers

| Trigger | Event | Migration Approach |
|---------|-------|-------------------|
| {{TRIGGER_NAME}} | {{EVENT}} | Application-level event handling |

### Custom Aggregates

| Aggregate | State Type | Migration Approach |
|-----------|------------|-------------------|
| {{AGG_NAME}} | {{STATE_TYPE}} | Application-level aggregation |

### PL/pgSQL Migration Summary

**Total PL/pgSQL Objects**: {{TOTAL_PLPGSQL}}
**Migration Approach**: Convert to application code (Java/Kotlin/etc.)
**Estimated Effort**: {{PLPGSQL_EFFORT}}

---

## 8. Views and Materialized Views Analysis

### Standard Views

| View Name | Base Tables | Complexity | Migration Approach |
|-----------|-------------|------------|-------------------|
| {{VIEW_NAME}} | {{BASE_TABLES}} | {{COMPLEXITY}} | {{APPROACH}} |

### Materialized Views

| MView Name | Populated | Base Tables | Migration Approach |
|------------|-----------|-------------|-------------------|
| {{MVIEW_NAME}} | {{POPULATED}} | {{BASE_TABLES}} | {{APPROACH}} |

**Materialized View Migration Options:**
1. Import as regular table (static snapshot)
2. Implement as application-level caching
3. Use ScalarDB Analytics for analytical queries

---

## 9. Sequences and SERIAL Columns

### Sequences

| Sequence | Start | Increment | Used By | Replacement Strategy |
|----------|-------|-----------|---------|---------------------|
| {{SEQ_NAME}} | {{START_VAL}} | {{INCREMENT}} | {{USED_BY}} | {{STRATEGY}} |

### SERIAL/BIGSERIAL Columns

| Table | Column | Type | Replacement Strategy |
|-------|--------|------|---------------------|
| {{TABLE}} | {{COLUMN}} | {{TYPE}} | {{STRATEGY}} |

### IDENTITY Columns (PostgreSQL 10+)

| Table | Column | Generation | Replacement Strategy |
|-------|--------|------------|---------------------|
| {{TABLE}} | {{COLUMN}} | {{GENERATION}} | {{STRATEGY}} |

**Sequence Replacement Options:**
1. UUID generation (recommended for distributed systems)
2. Application-level ID generator (Snowflake, ULID, etc.)
3. Database-specific auto-increment (if using single underlying database)

---

## 10. Security Model Analysis

### Table Privileges

| Table | Grantee | Privilege | ScalarDB Approach |
|-------|---------|-----------|-------------------|
| {{TABLE}} | {{GRANTEE}} | {{PRIVILEGE}} | {{APPROACH}} |

### Row Level Security Policies

| Table | Policy | Command | Migration Impact |
|-------|--------|---------|------------------|
| {{TABLE}} | {{POLICY}} | {{CMD}} | Requires application-level security |

**RLS Migration Strategy:**
- ScalarDB does not support row-level security
- Implement equivalent logic in application layer
- Consider using ScalarDB's attribute-based access control (Enterprise)

### Column Privileges

| Table | Column | Grantee | Privilege | Migration Approach |
|-------|--------|---------|-----------|-------------------|
| {{TABLE}} | {{COLUMN}} | {{GRANTEE}} | {{PRIVILEGE}} | Application-level |

---

## 11. Extensions Analysis

### Installed Extensions

| Extension | Version | Impact on Migration |
|-----------|---------|---------------------|
| {{EXT_NAME}} | {{VERSION}} | {{IMPACT}} |

### Extension-Specific Migration Notes

#### pgcrypto
- Encryption functions must be moved to application layer
- Consider ScalarDB Enterprise encryption features

#### PostGIS
- Spatial types NOT supported in ScalarDB
- Consider external geospatial service

#### pg_trgm
- Trigram similarity search not available
- Consider ScalarDB Vector Search or external search service

#### hstore
- Key-value storage can use JSONB → TEXT migration path

#### uuid-ossp
- UUID generation moves to application layer

---

## 12. Partitioned Tables Analysis

### Partitioned Tables

| Table | Strategy | Partition Key | Migration Approach |
|-------|----------|---------------|-------------------|
| {{TABLE}} | {{STRATEGY}} | {{PARTITION_KEY}} | {{APPROACH}} |

### Partitions

| Parent Table | Partition | Bound | Migration Notes |
|--------------|-----------|-------|-----------------|
| {{PARENT}} | {{PARTITION}} | {{BOUND}} | {{NOTES}} |

**Partitioning Migration Strategy:**
- ScalarDB partition-key is different from PostgreSQL partitioning
- Underlying database may handle physical partitioning
- Design ScalarDB partition-key for query optimization

---

## 13. Table Inheritance Analysis

### Inheritance Hierarchies

| Parent Table | Child Tables | Migration Approach |
|--------------|--------------|-------------------|
| {{PARENT}} | {{CHILDREN}} | {{APPROACH}} |

**Inheritance Migration Options:**
1. **Flatten**: Merge all child table data into single table
2. **Normalize**: Keep separate tables, manage relationships in application
3. **Type discriminator**: Add type column to distinguish record types

---

## 14. Migration Risk Matrix

### High Risk Items

| Item | Type | Risk | Mitigation |
|------|------|------|------------|
| {{ITEM}} | {{TYPE}} | {{RISK_DESC}} | {{MITIGATION}} |

### Medium Risk Items

| Item | Type | Risk | Mitigation |
|------|------|------|------------|
| {{ITEM}} | {{TYPE}} | {{RISK_DESC}} | {{MITIGATION}} |

### Low Risk Items

| Item | Type | Risk | Mitigation |
|------|------|------|------------|
| {{ITEM}} | {{TYPE}} | {{RISK_DESC}} | {{MITIGATION}} |

---

## 15. Recommendations

### Immediate Actions
1. {{RECOMMENDATION_1}}
2. {{RECOMMENDATION_2}}
3. {{RECOMMENDATION_3}}

### Pre-Migration Requirements
- [ ] {{PREREQ_1}}
- [ ] {{PREREQ_2}}
- [ ] {{PREREQ_3}}

### Application Changes Required
1. {{APP_CHANGE_1}}
2. {{APP_CHANGE_2}}
3. {{APP_CHANGE_3}}

---

## 16. Migration Complexity Assessment

### Complexity Scoring Model

Migration complexity is calculated using a weighted scoring system based on four categories.

### Scoring Criteria Applied

#### Data Type Complexity (Weight: 20%)
| Score Range | Criteria |
|-------------|----------|
| 0-2 | All standard types (INTEGER, VARCHAR, BOOLEAN, TIMESTAMP) with direct mapping |
| 3-4 | BYTEA, NUMERIC requiring precision consideration |
| 5-6 | JSON/JSONB columns, UUID columns |
| 7-8 | Array types requiring normalization |
| 9-10 | Composite types, range types, tsvector columns |

#### Schema Complexity (Weight: 25%)
| Score Range | Criteria |
|-------------|----------|
| 0-2 | Simple tables with standard constraints |
| 3-4 | Foreign keys, composite primary keys |
| 5-6 | Views requiring conversion |
| 7-8 | Materialized views, partitioned tables |
| 9-10 | Table inheritance, complex RLS policies |

#### PL/pgSQL Complexity (Weight: 25%)
| Score Range | Criteria |
|-------------|----------|
| 0 | No PL/pgSQL objects |
| 1-3 | Simple functions (<10) |
| 4-6 | Moderate PL/pgSQL (10-50 objects, some triggers) |
| 7-8 | Complex PL/pgSQL (50+ objects, trigger chains) |
| 9-10 | Heavy PL/pgSQL (business logic in database, event triggers) |

#### Application Impact (Weight: 30%)
| Score Range | Criteria |
|-------------|----------|
| 0-2 | Simple CRUD operations only |
| 3-4 | JOIN queries, basic transactions, GROUP BY with aggregations (v3.17+) |
| 5-6 | **Subqueries, CTEs** - require decomposition or Analytics |
| 7-8 | **Window functions, complex subqueries** - require Analytics or app rewrite |
| 8-9 | Complex queries with function dependencies |
| 9-10 | Heavy database-side logic, triggers for business rules |

**NOTE**: ScalarDB 3.17+ supports GROUP BY, HAVING, and aggregate functions (COUNT, SUM, AVG, MIN, MAX). Subqueries, CTEs, and window functions still require workarounds.

### Calculated Scores

| Category | Score | Weight | Weighted Score |
|----------|-------|--------|----------------|
| Data Type Complexity | {{DT_SCORE}}/10 | 20% | {{DT_WEIGHTED}} |
| Schema Complexity | {{SCHEMA_SCORE}}/10 | 25% | {{SCHEMA_WEIGHTED}} |
| PL/pgSQL Complexity | {{PLPGSQL_SCORE}}/10 | 25% | {{PLPGSQL_WEIGHTED}} |
| Application Impact | {{APP_SCORE}}/10 | 30% | {{APP_WEIGHTED}} |
| **Total** | | | **{{TOTAL_SCORE}}/10** |

### Complexity Rating Scale

| Score Range | Rating | Description |
|-------------|--------|-------------|
| 0.0 - 2.5 | LOW | Direct migration with minimal changes |
| 2.6 - 5.0 | MEDIUM | Requires schema adjustments and query rewrites |
| 5.1 - 7.5 | HIGH | Significant refactoring needed |
| 7.6 - 10.0 | VERY HIGH | Major application redesign required |

**Overall Migration Complexity**: {{COMPLEXITY_RATING}} ({{TOTAL_SCORE}}/10)

---

## 17. Migration Effort Estimation

### Effort Calculation Formula

```
Schema Migration Effort = (Tables × 0.5) + (Custom Types × 2) + (Array Columns × 2) + (Unsupported Columns × 1)
Data Migration Effort = (Tables × 1) + (BYTEA Columns × 2) + (Row Estimate / 100000)
Application Migration Effort = (PL/pgSQL Objects × 4) + (Triggers × 3) + (Complex Queries × 2) + (FK Relationships × 0.5)
Testing Effort = Total Migration Effort × 0.3
```

### Calculated Effort

| Category | Calculation | Effort Units |
|----------|-------------|--------------|
| Schema Migration | {{SCHEMA_EFFORT_CALC}} | {{SCHEMA_EFFORT}} |
| Data Migration | {{DATA_EFFORT_CALC}} | {{DATA_EFFORT}} |
| Application Migration | {{APP_EFFORT_CALC}} | {{APP_EFFORT}} |
| Testing | {{TEST_EFFORT_CALC}} | {{TEST_EFFORT}} |
| **Total** | | **{{TOTAL_EFFORT}}** |

### Effort Rating

| Effort Units | Rating |
|--------------|--------|
| 0-10 | LOW |
| 11-30 | MEDIUM |
| 31-60 | HIGH |
| 60+ | VERY HIGH |

**Overall Migration Effort**: {{EFFORT_RATING}}

---

## 18. ScalarDB SQL Limitations Analysis (CRITICAL)

> **Reference**: https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/grammar/

ScalarDB SQL has significant differences from PostgreSQL. These limitations must be understood for successful migration.

### PostgreSQL Features NOT Available in ScalarDB SQL

| PostgreSQL Feature | ScalarDB Status | Workaround |
|-------------------|-----------------|------------|
| CTEs (WITH clause) | ❌ NOT supported | Convert to subqueries or application logic |
| Window functions | ❌ NOT supported | ScalarDB Analytics |
| LATERAL joins | ❌ NOT supported | Application logic |
| ARRAY constructors | ❌ NOT supported | Normalize to child table |
| JSON operators | ❌ NOT supported | Application-level JSON parsing |
| RETURNING clause | ❌ NOT supported | Separate SELECT after INSERT/UPDATE |
| UPSERT (ON CONFLICT) | ❌ NOT supported | Read-check-write pattern |
| COPY command | ❌ NOT supported | Batch INSERT statements |
| LISTEN/NOTIFY | ❌ NOT supported | External message queue |

### ScalarDB Execution Model

ScalarDB operates as a **distributed key-value store** with SQL interface. Understanding this is critical:

| Aspect | PostgreSQL | ScalarDB |
|--------|------------|----------|
| Execution Model | Query optimizer, index scans | Partition-based Get/Scan operations |
| JOINs | Optimized with query plans | Resolved per-partition; cross-partition may be slow |
| Aggregations | Optimized for analytics | Must scan relevant partitions |
| Transactions | MVCC, row-level locking | Distributed consensus |

---

## 19. ScalarDB Analytics Assessment

> **When ScalarDB Analytics is Required**: If your schema uses CTEs, subqueries, window functions, or analytical queries, you MUST plan for ScalarDB Analytics deployment.

### Supported vs Requires Analytics

| Feature | ScalarDB SQL | ScalarDB Analytics |
|---------|--------------|-------------------|
| Simple CRUD | ✅ Use | Not needed |
| Single-partition queries | ✅ Use | Not needed |
| Simple 2-table JOINs | ✅ Use (within partition) | Use if cross-partition |
| Multi-table JOINs | ⚠️ Performance issues | ✅ **Recommended** |
| CTEs (WITH clause) | ❌ Not supported | ✅ **Required** |
| Subqueries | ❌ Not supported | ✅ **Required** |
| Window functions | ❌ Not supported | ✅ **Required** |
| Complex aggregations | ⚠️ Limited | ✅ **Recommended** |
| UNION / INTERSECT / EXCEPT | ❌ Not supported | ✅ **Required** |

{{#IF_ANALYTICS_REQUIRED}}

#### ScalarDB Analytics is REQUIRED for this migration

Based on schema analysis, the following features require ScalarDB Analytics:

| Feature/Pattern | Tables Affected | Reason |
|-----------------|-----------------|--------|
| {{FEATURE}} | {{TABLES}} | {{REASON}} |

{{/IF_ANALYTICS_REQUIRED}}

{{#IF_ANALYTICS_NOT_REQUIRED}}

#### ScalarDB Analytics NOT Required

Based on schema analysis:
- No CTEs detected
- No subqueries detected
- No window functions detected
- Standard ScalarDB SQL is sufficient for this migration

{{/IF_ANALYTICS_NOT_REQUIRED}}

---

## 20. Partition Key Design Recommendations

> **Critical for Performance**: Poor partition key design leads to cross-partition operations and performance degradation.

### Recommended Key Design for This Schema

| Table | Suggested Partition Key | Suggested Clustering Key | Rationale |
|-------|------------------------|-------------------------|-----------|
| {{TABLE_NAME}} | {{PARTITION_KEY}} | {{CLUSTERING_KEY}} | {{RATIONALE}} |

### Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Low-cardinality partition key | Hot partitions, poor distribution | Use composite key or higher cardinality column |
| No partition key in queries | Full table scans | Design queries to include partition key |
| Mismatched keys across related tables | Slow JOINs | Align partition keys for JOIN optimization |

---

## Appendix A: PostgreSQL to ScalarDB Data Type Reference

| PostgreSQL Type | ScalarDB Type | Range/Limit | Notes |
|-----------------|---------------|-------------|-------|
| SMALLINT | INT | -2^31 to 2^31-1 | |
| INTEGER | INT | -2^31 to 2^31-1 | |
| BIGINT | BIGINT | -2^53 to 2^53 | Range limitation |
| SERIAL | INT | | Sequence replacement needed |
| BIGSERIAL | BIGINT | | Sequence replacement needed |
| REAL | FLOAT | 32-bit IEEE 754 | |
| DOUBLE PRECISION | DOUBLE | 64-bit IEEE 754 | |
| NUMERIC/DECIMAL | DOUBLE | ~15-17 digits | Precision loss possible |
| CHAR(n) | TEXT | Unlimited | |
| VARCHAR(n) | TEXT | Unlimited | |
| TEXT | TEXT | Unlimited | |
| BYTEA | BLOB | ~2GB | |
| BOOLEAN | BOOLEAN | true/false | |
| DATE | DATE | 1000-01-01 to 9999-12-31 | |
| TIME | TIME | 00:00:00 to 23:59:59.999999 | |
| TIMESTAMP | TIMESTAMP | millisecond precision | |
| TIMESTAMPTZ | TIMESTAMPTZ | millisecond precision, UTC | |
| JSON | TEXT | | Loses operators |
| JSONB | TEXT | | Loses operators/indexing |
| UUID | TEXT | | |
| INET | TEXT | | |
| CIDR | TEXT | | |
| MACADDR | TEXT | | |
| ARRAY | NOT SUPPORTED | | Normalize to child table |
| ENUM | TEXT | | App validation |
| Composite | NOT SUPPORTED | | Flatten to columns |
| Range | NOT SUPPORTED | | Two boundary columns |
| tsvector | NOT SUPPORTED | | Use Vector Search |
| Geometric | NOT SUPPORTED | | |

---

## Appendix B: Unsupported PostgreSQL Features Summary

| Feature | ScalarDB Status | Workaround |
|---------|-----------------|------------|
| Table Inheritance | Not Supported | Flatten or normalize |
| SERIAL/IDENTITY | Not Supported | UUID or app-level generator |
| Sequences | Not Supported | UUID or app-level counter |
| Triggers | Not Supported | Application event handling |
| Functions | Not Supported | Application methods |
| Procedures | Not Supported | Application methods |
| Row Level Security | Not Supported | Application security |
| Views | Partial | Import as table or query |
| Materialized Views | Not Supported | Application caching |
| Array Types | Not Supported | Normalize to child table |
| ENUM Types | Not Supported | TEXT + validation |
| Composite Types | Not Supported | Flatten to columns |
| Range Types | Not Supported | Two boundary columns |
| JSONB Operators | Not Supported | Application JSON parsing |
| Full-Text Search | Not Supported | Vector Search or external |
| Foreign Data Wrappers | Not Supported | Import data first |
| Generated Columns | Not Supported | Compute in application |
| Partial Indexes | Not Supported | Application filtering |
| Expression Indexes | Not Supported | Computed columns |
| GiST/GIN/BRIN Indexes | Not Supported | B-tree or external |
| CTEs (WITH clause) | Not Supported | ScalarDB Analytics |
| Window Functions | Not Supported | ScalarDB Analytics |
| LATERAL Joins | Not Supported | Application logic |

---

## Appendix C: Mandatory ScalarDB Documentation References

### Primary Migration Path: ScalarDB SQL

| Reference | URL | Purpose |
|-----------|-----|---------|
| ScalarDB Cluster SQL (JDBC) Getting Started | https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/getting-started-with-scalardb-cluster-sql-jdbc/ | JDBC setup and configuration |
| ScalarDB SQL Grammar Reference | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/grammar/ | SQL syntax, DDL, DML operations |
| ScalarDB SQL Migration Guide | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/migration-guide | Step-by-step migration instructions |

### Schema and Data Type References

| Reference | URL | Purpose |
|-----------|-----|---------|
| Schema Loader Data Type Mapping | https://scalardb.scalar-labs.com/docs/latest/schema-loader/#data-type-mapping-between-scalardb-and-other-databases | Type conversion reference |
| Schema Loader Import | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import | Importing existing tables |
| JDBC Data Type Mapping | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import#data-type-mapping-from-jdbc-databases-to-scalardb | PostgreSQL → ScalarDB types |

### ScalarDB Analytics (for Complex Queries)

| Reference | URL | Purpose |
|-----------|-----|---------|
| ScalarDB Analytics Overview | https://scalardb.scalar-labs.com/docs/latest/scalardb-analytics/ | Aggregations, subqueries, analytics |
| ScalarDB Analytics CLI | https://scalardb.scalar-labs.com/docs/latest/scalardb-analytics/reference-cli-command/ | Analytics CLI commands |

### General References

| Reference | URL |
|-----------|-----|
| ScalarDB Main Documentation | https://scalardb.scalar-labs.com/docs/latest/ |
| Supported Databases | https://scalardb.scalar-labs.com/docs/latest/requirements/#databases |
| Features Overview | https://scalardb.scalar-labs.com/docs/latest/features |

---

*Analysis generated by Migrate PostgreSQL to ScalarDB Schema Skill*
*Input consumed from: ${POSTGRESQL_SCHEMA_REPORT_MD}*
