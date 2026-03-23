# ScalarDB MySQL Migration Analysis Report Template

This template is used to generate the **migration analysis** report. Replace all `{{PLACEHOLDER}}` tokens with actual values from the source MySQL schema report.

**Input Source**: This report consumes `mysql_schema_report.md` from the configured output directory (Skill 1 output).

---

# MySQL to ScalarDB Migration Analysis

**Generated**: {{TIMESTAMP}}
**Source Database**: {{DATABASE_NAME}}
**MySQL Version**: {{MYSQL_VERSION}}
**Target**: ScalarDB 3.17+
**Primary Migration Path**: ScalarDB SQL (JDBC)

---

## RECOMMENDED: Transaction Metadata Decoupling

> **For this migration, we recommend using `transaction-metadata-decoupling: true` instead of `transaction: true`.**

This approach keeps your **existing MySQL tables unchanged** - ScalarDB stores its transaction metadata in separate `<table>_scalardb` tables.

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
| ENUM Columns | {{ENUM_COUNT}} | {{ENUM_COMPAT}} | {{ENUM_EFFORT}} |
| SET Columns | {{SET_COUNT}} | {{SET_COMPAT}} | {{SET_EFFORT}} |
| JSON Columns | {{JSON_COUNT}} | {{JSON_COMPAT}} | {{JSON_EFFORT}} |
| Indexes | {{INDEX_COUNT}} | {{INDEX_COMPAT}} | {{INDEX_EFFORT}} |
| Views | {{VIEW_COUNT}} | {{VIEW_COMPAT}} | {{VIEW_EFFORT}} |
| Stored Procedures | {{PROC_COUNT}} | {{PROC_COMPAT}} | {{PROC_EFFORT}} |
| Stored Functions | {{FUNC_COUNT}} | {{FUNC_COMPAT}} | {{FUNC_EFFORT}} |
| Triggers | {{TRIGGER_COUNT}} | {{TRIGGER_COMPAT}} | {{TRIGGER_EFFORT}} |
| Events | {{EVENT_COUNT}} | {{EVENT_COMPAT}} | {{EVENT_EFFORT}} |
| Auto-increment Columns | {{AUTO_INC_COUNT}} | {{AUTO_INC_COMPAT}} | {{AUTO_INC_EFFORT}} |
| Generated Columns | {{GEN_COL_COUNT}} | {{GEN_COL_COMPAT}} | {{GEN_COL_EFFORT}} |

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

> ⚠️ **CRITICAL**: Only the data types listed below are officially supported. **Data types NOT listed in the official documentation are NOT SUPPORTED.**

### Supported MySQL Data Types

The following data types are **SUPPORTED** for ScalarDB import:

| MySQL Type | ScalarDB Type | Notes |
|------------|---------------|-------|
| bigint | BIGINT | ⚠️ Range: -2^53 to 2^53 only |
| int, integer | INT | Direct mapping |
| smallint, mediumint, tinyint | INT | Maps to larger type |
| float | FLOAT | Direct mapping |
| double | DOUBLE | Direct mapping |
| varchar, char | TEXT | Direct mapping |
| text, tinytext, mediumtext, longtext | TEXT | Direct mapping |
| blob, tinyblob, mediumblob, longblob | BLOB | Max ~2GB |
| date | DATE | Direct mapping |
| time | TIME | Without timezone |
| datetime | TIMESTAMP | Direct mapping |
| timestamp | TIMESTAMPTZ | Direct mapping |
| tinyint(1), bit(1) | BOOLEAN | Direct mapping |
| binary, varbinary | BLOB | Direct mapping |

### NOT Supported Data Types (Official)

> **Data types not listed above are NOT SUPPORTED.** The following are common data types that are explicitly NOT supported:

| Category | Unsupported Types |
|----------|-------------------|
| Numeric | decimal, numeric |
| String | enum, set |
| JSON | json |
| Spatial | geometry, point, linestring, polygon, etc. |
| Date/Time | year |

### MySQL to ScalarDB Type Conversions

| MySQL Column | MySQL Type | ScalarDB Type | Conversion Notes | Risk |
|--------------|------------|---------------|------------------|------|
| {{TABLE}}.{{COLUMN}} | {{MYSQL_TYPE}} | {{SCALARDB_TYPE}} | {{NOTES}} | {{RISK}} |

### Type Conversion Summary

| MySQL Type | Count | ScalarDB Type | Conversion Status |
|------------|-------|---------------|-------------------|
| {{MYSQL_TYPE}} | {{COUNT}} | {{SCALARDB_TYPE}} | {{STATUS}} |

### Critical Data Type Warnings

#### ⚠️ Warning 1: BIGINT Range Limitation
> The value range of BIGINT in ScalarDB is from **-2^53 to 2^53** (-9,007,199,254,740,992 to 9,007,199,254,740,992), regardless of the size of bigint in the underlying database.

- **Affected Columns**: {{BIGINT_AFFECTED_COLS}}
- **Action Required**: {{BIGINT_ACTION}}

#### ⚠️ Warning 2: DECIMAL/NUMERIC Columns (NOT SUPPORTED)
- **Issue**: No exact decimal support in ScalarDB
- **Affected Columns**: {{DECIMAL_AFFECTED_COLS}}
- **Options**:
  1. Convert to DOUBLE (accept precision loss)
  2. Convert to TEXT (preserve exact value, handle in application)

#### ⚠️ Warning 3: BLOB Size Limitation
> The maximum size of BLOB in ScalarDB is about 2GB (precisely 2^31-1 bytes).

- **Affected Columns**: {{BLOB_AFFECTED_COLS}}
- **Action Required**: {{BLOB_ACTION}}

---

## 3. Table Analysis

### Table Compatibility Matrix

| Table Name | Columns | Has PK | Has Auto-Inc | Has Generated | Has LOBs | Has FK | Compatibility |
|------------|---------|--------|--------------|---------------|----------|--------|---------------|
| {{TABLE_NAME}} | {{COL_COUNT}} | {{HAS_PK}} | {{HAS_AUTO_INC}} | {{HAS_GENERATED}} | {{HAS_LOBS}} | {{HAS_FK}} | {{COMPAT_STATUS}} |

### Detailed Table Analysis

#### Table: {{TABLE_NAME}}

**MySQL Structure:**
- Engine: {{ENGINE}}
- Columns: {{COLUMN_COUNT}}
- Primary Key: {{PK_COLUMNS}}
- Has Auto-increment: {{HAS_AUTO_INCREMENT}}
- Has LOB Columns: {{HAS_LOB_COLUMNS}}
- Has Foreign Keys: {{HAS_FK}}

**Column Mapping:**

| Column Name | MySQL Type | ScalarDB Type | Nullable | Notes |
|-------------|------------|---------------|----------|-------|
| {{COLUMN_NAME}} | {{MYSQL_TYPE}} | {{SCALARDB_TYPE}} | {{NULLABLE}} | {{NOTES}} |

**ScalarDB Key Design:**
- **Partition Key**: {{PARTITION_KEY}}
- **Clustering Key**: {{CLUSTERING_KEY}}
- **Secondary Indexes**: {{SECONDARY_INDEXES}}

**Migration Notes:**
{{TABLE_MIGRATION_NOTES}}

---

## 4. Custom Types Analysis

### ENUM Columns

| Table Name | Column Name | Allowed Values | Migration Approach |
|------------|-------------|----------------|-------------------|
| {{TABLE}} | {{COLUMN}} | {{ENUM_VALUES}} | TEXT + application validation |

### ENUM Column Migration Plan

**Original Definition:**
```sql
CREATE TABLE {{TABLE}} (
    {{COLUMN}} ENUM({{ENUM_VALUES}})
);
```

**Migration Strategy:**
- Convert column to TEXT in ScalarDB
- Add application-level validation for allowed values
- Consider using CHECK constraint in underlying database if supported

### SET Columns

| Table Name | Column Name | Allowed Values | Migration Approach |
|------------|-------------|----------------|-------------------|
| {{TABLE}} | {{COLUMN}} | {{SET_VALUES}} | TEXT + application validation |

**SET Column Migration:**
- Store as comma-separated TEXT
- Parse and validate in application layer

### JSON Columns

| Table Name | Column Name | Migration Approach |
|------------|-------------|-------------------|
| {{TABLE}} | {{COLUMN}} | TEXT + application JSON parsing |

**JSON Column Migration:**
- Store as TEXT in ScalarDB
- Parse JSON in application code
- JSON operators (`->`, `->>`, `JSON_EXTRACT`) not available

---

## 5. Constraint Analysis

### Primary Keys

| Table Name | Constraint Name | Columns | ScalarDB Mapping |
|------------|-----------------|---------|------------------|
| {{TABLE}} | {{PK_NAME}} | {{PK_COLUMNS}} | partition-key / clustering-key |

### Foreign Keys

| Table Name | Constraint Name | Column Name | Ref Table | Ref Column | On Update | On Delete | Migration Impact |
|------------|-----------------|-------------|-----------|------------|-----------|-----------|------------------|
| {{TABLE}} | {{FK_NAME}} | {{FK_COLS}} | {{REF_TABLE}} | {{REF_COLS}} | {{UPDATE_RULE}} | {{DELETE_RULE}} | Application-level enforcement |

**Foreign Key Migration Strategy:**
- ScalarDB does not enforce referential integrity at the database level
- All FK relationships must be enforced in application code
- CASCADE operations must be implemented in application transactions

### Unique Constraints

| Table Name | Constraint Name | Columns | Migration Approach |
|------------|-----------------|---------|-------------------|
| {{TABLE}} | {{UK_NAME}} | {{UK_COLUMNS}} | Application check before insert |

### Check Constraints

| Table Name | Constraint Name | Check Clause | Migration Approach |
|------------|-----------------|--------------|-------------------|
| {{TABLE}} | {{CK_NAME}} | {{CONDITION}} | Application validation |

---

## 6. Index Analysis

### Index Migration Matrix

| Index Name | Table Name | Index Type | Columns | ScalarDB Support | Migration |
|------------|------------|------------|---------|------------------|-----------|
| {{INDEX_NAME}} | {{TABLE}} | {{INDEX_TYPE}} | {{COLUMNS}} | {{SUPPORT}} | {{MIGRATION}} |

### Primary Key Indexes
- Automatically handled by partition-key and clustering-key definitions

### Secondary Indexes

| Index Name | Table Name | Column Name | ScalarDB secondary-index |
|------------|------------|-------------|-------------------------|
| {{INDEX}} | {{TABLE}} | {{COLUMN}} | {{RECOMMENDATION}} |

### Fulltext Indexes (NOT SUPPORTED)

| Index Name | Table Name | Columns | Workaround |
|------------|------------|---------|------------|
| {{INDEX}} | {{TABLE}} | {{COLUMNS}} | Consider ScalarDB Vector Search or external search |

### Spatial Indexes (NOT SUPPORTED)

| Index Name | Table Name | Columns | Workaround |
|------------|------------|---------|------------|
| {{INDEX}} | {{TABLE}} | {{COLUMNS}} | NOT SUPPORTED |

---

## 7. Stored Programs Analysis

### Stored Procedures

| Procedure Name | Parameters | Deterministic | Complexity | Migration Effort |
|----------------|------------|---------------|------------|------------------|
| {{PROC_NAME}} | {{PARAM_COUNT}} | {{DETERMINISTIC}} | {{COMPLEXITY}} | {{EFFORT}} |

### Stored Functions

| Function Name | Parameters | Return Type | Deterministic | Complexity | Migration Effort |
|---------------|------------|-------------|---------------|------------|------------------|
| {{FUNC_NAME}} | {{PARAM_COUNT}} | {{RETURN_TYPE}} | {{DETERMINISTIC}} | {{COMPLEXITY}} | {{EFFORT}} |

### Triggers

| Trigger Name | Table Name | Event | Timing | Migration Approach |
|--------------|------------|-------|--------|-------------------|
| {{TRIGGER_NAME}} | {{TABLE}} | {{EVENT}} | {{TIMING}} | Application event handler |

### Events (Scheduled Tasks)

| Event Name | Type | Interval | Status | Migration Approach |
|------------|------|----------|--------|-------------------|
| {{EVENT_NAME}} | {{TYPE}} | {{INTERVAL}} | {{STATUS}} | External scheduler (cron, etc.) |

### Stored Programs Migration Summary

**Total Stored Programs**: {{TOTAL_STORED_PROGRAMS}}
**Migration Approach**: Convert to application code (Java/Kotlin/etc.)
**Estimated Effort**: {{STORED_PROGRAMS_EFFORT}}

---

## 8. Views Analysis

### Standard Views

| View Name | Base Tables | Updatable | Complexity | Migration Approach |
|-----------|-------------|-----------|------------|-------------------|
| {{VIEW_NAME}} | {{BASE_TABLES}} | {{UPDATABLE}} | {{COMPLEXITY}} | {{APPROACH}} |

**Migration Options:**
1. Import view as materialized table (static snapshot)
2. Execute underlying query directly
3. Create application-level abstraction

---

## 9. Sequences and Auto-increment Analysis

### Auto-increment Columns

| Table Name | Column Name | Type | Current Value | Replacement Strategy |
|------------|-------------|------|---------------|---------------------|
| {{TABLE}} | {{COLUMN}} | {{TYPE}} | {{CURRENT_VALUE}} | {{STRATEGY}} |

### Replacement Strategies

| Strategy | Pros | Cons | Best For |
|----------|------|------|----------|
| UUID | Globally unique, no coordination | 36 chars, not sequential | Distributed systems |
| Snowflake ID | Sequential, 64-bit | Requires ID generator setup | High-volume inserts |
| Application sequence | Simple | Requires coordination | Single-app scenarios |
| ULID | Sortable, 26 chars | External library needed | Time-ordered IDs |

**Recommended**: UUID for distributed systems, Snowflake-style ID for high-volume sequential needs.

---

## 10. LOB Storage Analysis

### TEXT/BLOB Columns

| Table Name | Column Name | LOB Type | Size Concern | Migration Notes |
|------------|-------------|----------|--------------|-----------------|
| {{TABLE}} | {{COLUMN}} | {{LOB_TYPE}} | {{SIZE_CONCERN}} | {{NOTES}} |

**LOB Migration Notes:**
- TEXT columns → ScalarDB TEXT (unlimited)
- BLOB columns → ScalarDB BLOB (max ~2GB)
- LONGTEXT/LONGBLOB → Validate size limits

---

## 11. Security Model Analysis

### Table Privileges

| Table Name | Grantee | Privilege | ScalarDB Approach |
|------------|---------|-----------|-------------------|
| {{TABLE}} | {{GRANTEE}} | {{PRIVILEGE}} | {{APPROACH}} |

### Column Privileges

| Table Name | Column Name | Grantee | Privilege | Migration Approach |
|------------|-------------|---------|-----------|-------------------|
| {{TABLE}} | {{COLUMN}} | {{GRANTEE}} | {{PRIVILEGE}} | Application-level |

**Security Migration Notes:**
- ScalarDB does not support MySQL's GRANT/REVOKE at table level
- Implement access control in application layer
- Consider ScalarDB Enterprise for advanced security features

---

## 12. Partitioned Tables Analysis

### Partitioned Tables

| Table Name | Partition Method | Partition Expression | Partition Count | Migration Approach |
|------------|------------------|---------------------|-----------------|-------------------|
| {{TABLE}} | {{METHOD}} | {{EXPRESSION}} | {{COUNT}} | {{APPROACH}} |

### Partitions

| Table Name | Partition Name | Description | Rows | Migration Notes |
|------------|----------------|-------------|------|-----------------|
| {{TABLE}} | {{PARTITION}} | {{DESCRIPTION}} | {{ROWS}} | {{NOTES}} |

**Partitioning Migration Strategy:**
- ScalarDB partition-key is different from MySQL partitioning
- Underlying database may handle physical partitioning
- Design ScalarDB partition-key for query optimization

---

## 13. Migration Risk Matrix

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

## 14. Recommendations

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

## 15. Migration Complexity Assessment

### Complexity Scoring Model

Migration complexity is calculated using a weighted scoring system based on four categories.

### Scoring Criteria Applied

#### Data Type Complexity (Weight: 20%)
| Score Range | Criteria |
|-------------|----------|
| 0-2 | All standard types (INT, VARCHAR, DATE) with direct mapping |
| 3-4 | Some LOBs (BLOB, TEXT) requiring size validation |
| 5-6 | DECIMAL columns requiring precision handling |
| 7-8 | JSON columns requiring TEXT conversion |
| 9-10 | ENUM, SET, spatial types requiring significant changes |

#### Schema Complexity (Weight: 25%)
| Score Range | Criteria |
|-------------|----------|
| 0-2 | Simple tables with standard constraints |
| 3-4 | Foreign keys, composite primary keys |
| 5-6 | Views requiring conversion |
| 7-8 | Partitioned tables, generated columns |
| 9-10 | Multiple unsupported features combined |

#### Stored Programs Complexity (Weight: 25%)
| Score Range | Criteria |
|-------------|----------|
| 0 | No stored programs |
| 1-3 | Simple procedures/functions (<10) |
| 4-6 | Moderate (10-50 objects, some triggers) |
| 7-8 | Complex (50+ objects, events, trigger chains) |
| 9-10 | Heavy business logic in database |

#### Application Impact (Weight: 30%)
| Score Range | Criteria |
|-------------|----------|
| 0-2 | Simple CRUD operations only |
| 3-4 | JOIN queries, basic transactions, GROUP BY with aggregations (v3.17+) |
| 5-6 | **Subqueries** - require decomposition or Analytics |
| 7-8 | **Window functions, complex subqueries** - require Analytics or app rewrite |
| 8-9 | Complex queries with stored procedure dependencies |
| 9-10 | Heavy database-side logic, triggers for business rules |

**NOTE**: ScalarDB 3.17+ supports GROUP BY, HAVING, and aggregate functions (COUNT, SUM, AVG, MIN, MAX). Subqueries and window functions still require workarounds.

### Calculated Scores

| Category | Score | Weight | Weighted Score |
|----------|-------|--------|----------------|
| Data Type Complexity | {{DT_SCORE}}/10 | 20% | {{DT_WEIGHTED}} |
| Schema Complexity | {{SCHEMA_SCORE}}/10 | 25% | {{SCHEMA_WEIGHTED}} |
| Stored Programs Complexity | {{SP_SCORE}}/10 | 25% | {{SP_WEIGHTED}} |
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

## 16. Migration Effort Estimation

### Effort Calculation Formula

```
Schema Migration Effort = (Tables × 0.5) + (Custom Types × 2) + (ENUM/SET Columns × 1) + (Unsupported Columns × 1)
Data Migration Effort = (Tables × 1) + (LOB Columns × 2) + (Row Estimate / 100000)
Application Migration Effort = (Stored Programs × 4) + (Triggers × 3) + (Complex Queries × 2) + (FK Relationships × 0.5)
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

## 17. ScalarDB SQL Limitations Analysis (CRITICAL)

> **Reference**: https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/grammar/

ScalarDB SQL has significant differences from MySQL. These limitations must be understood for successful migration.

### MySQL Features NOT Available in ScalarDB SQL

| MySQL Feature | ScalarDB Status | Workaround |
|---------------|-----------------|------------|
| AUTO_INCREMENT | ❌ NOT supported | UUID or application ID generator |
| Subqueries | ❌ NOT supported | ScalarDB Analytics or application logic |
| Window functions | ❌ NOT supported | ScalarDB Analytics |
| UNION / INTERSECT / EXCEPT | ❌ NOT supported | Multiple queries + application merge |
| ON DUPLICATE KEY UPDATE | ❌ NOT supported | Read-check-write pattern |
| INSERT ... SELECT | ❌ NOT supported | Separate SELECT then INSERT |
| REPLACE INTO | ❌ NOT supported | Delete + Insert pattern |
| JSON operators | ❌ NOT supported | Application-level JSON parsing |
| Stored procedures | ❌ NOT supported | Application methods |
| Triggers | ❌ NOT supported | Application event handlers |
| Events | ❌ NOT supported | External scheduler |

### ScalarDB Execution Model

ScalarDB operates as a **distributed key-value store** with SQL interface. Understanding this is critical:

| Aspect | MySQL | ScalarDB |
|--------|-------|----------|
| Execution Model | Query optimizer, index scans | Partition-based Get/Scan operations |
| JOINs | Optimized with query plans | Resolved per-partition; cross-partition may be slow |
| Aggregations | Optimized for analytics | Must scan relevant partitions |
| Transactions | Row/page locking | Distributed consensus |

### JOIN Limitations

| Limitation | Description | Impact |
|------------|-------------|--------|
| Cross-partition JOINs | JOINs across different partition keys | May trigger cross-partition scans |
| Multi-table JOINs | 3+ table JOINs | Not optimized like traditional RDBMS |
| JOIN performance | Depends on partition key design | Poor key design = poor JOIN performance |

**Recommendation**: Design partition keys to minimize cross-partition operations.

### WHERE Clause Restrictions

| Restriction | Description |
|-------------|-------------|
| Predicate Form | Must be in **DNF** (OR-of-ANDs) or **CNF** (AND-of-ORs) form |
| Arbitrary combinations | Complex WHERE clauses may not parse |
| Partition key | Include partition key in WHERE for optimal performance |

---

## 18. ScalarDB Analytics Assessment

> **When ScalarDB Analytics is Required**: If your schema uses subqueries, window functions, or analytical queries, you MUST plan for ScalarDB Analytics deployment.

### Supported vs Requires Analytics

| Feature | ScalarDB SQL | ScalarDB Analytics |
|---------|--------------|-------------------|
| Simple CRUD | ✅ Use | Not needed |
| Single-partition queries | ✅ Use | Not needed |
| Simple 2-table JOINs | ✅ Use (within partition) | Use if cross-partition |
| Multi-table JOINs | ⚠️ Performance issues | ✅ **Recommended** |
| Subqueries | ❌ Not supported | ✅ **Required** |
| Window functions | ❌ Not supported | ✅ **Required** |
| Complex aggregations | ⚠️ Limited | ✅ **Recommended** |
| UNION / INTERSECT / EXCEPT | ❌ Not supported | ✅ **Required** |
| Analytical/reporting queries | ⚠️ Not optimized | ✅ **Required** |

{{#IF_ANALYTICS_REQUIRED}}

#### ScalarDB Analytics is REQUIRED for this migration

Based on schema analysis, the following features require ScalarDB Analytics:

| Feature/Pattern | Tables Affected | Reason |
|-----------------|-----------------|--------|
| {{FEATURE}} | {{TABLES}} | {{REASON}} |

#### Analytics Setup Requirements

1. **Additional Infrastructure**:
   - ScalarDB Analytics server deployment
   - Separate properties file configuration

2. **Additional Dependencies**:
   ```xml
   <dependency>
       <groupId>com.scalar-labs</groupId>
       <artifactId>scalardb-analytics</artifactId>
       <version>{{VERSION}}</version>
   </dependency>
   ```

3. **Query Routing**:
   - Application must route complex queries to Analytics endpoint
   - Simple CRUD continues to use standard ScalarDB SQL

4. **Architecture Change**:
   ```
   Application
       │
       ├──► ScalarDB Cluster (SQL) ──► CRUD, simple JOINs
       │
       └──► ScalarDB Analytics ──► Subqueries, window functions, complex JOINs
   ```

{{/IF_ANALYTICS_REQUIRED}}

{{#IF_ANALYTICS_NOT_REQUIRED}}

#### ScalarDB Analytics NOT Required

Based on schema analysis:
- No subqueries detected
- No window functions detected
- No complex multi-table JOINs detected
- Standard ScalarDB SQL is sufficient for this migration

**Note**: Monitor query patterns post-migration. If complex analytical queries are added later, Analytics may become necessary.

{{/IF_ANALYTICS_NOT_REQUIRED}}

### Analytics Reference Documentation

| Reference | URL |
|-----------|-----|
| ScalarDB Analytics Overview | https://scalardb.scalar-labs.com/docs/latest/scalardb-analytics/ |
| ScalarDB Analytics CLI | https://scalardb.scalar-labs.com/docs/latest/scalardb-analytics/reference-cli-command/ |

---

## 19. Partition Key Design Recommendations

> **Critical for Performance**: Poor partition key design leads to cross-partition operations and performance degradation.

### Partition Key Design Guidelines

| Guideline | Description |
|-----------|-------------|
| High cardinality | Choose keys with many distinct values |
| Query patterns | Include partition key in most WHERE clauses |
| Even distribution | Avoid hot partitions |
| JOIN optimization | Related tables should have compatible partition keys |

### Recommended Key Design for This Schema

| Table Name | Suggested Partition Key | Suggested Clustering Key | Rationale |
|------------|------------------------|-------------------------|-----------|
| {{TABLE_NAME}} | {{PARTITION_KEY}} | {{CLUSTERING_KEY}} | {{RATIONALE}} |

### Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Low-cardinality partition key | Hot partitions, poor distribution | Use composite key or higher cardinality column |
| No partition key in queries | Full table scans | Design queries to include partition key |
| Mismatched keys across related tables | Slow JOINs | Align partition keys for JOIN optimization |

---

## 20. ScalarDB Advanced Features Opportunities

### Vector Search (Enterprise Premium)

{{#IF_FULLTEXT_EXISTS}}
**Opportunity**: Replace FULLTEXT indexes with ScalarDB Vector Search for semantic similarity.

**Reference**: https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/getting-started-with-vector-search/
{{/IF_FULLTEXT_EXISTS}}

### Object Storage Backend

ScalarDB can use object storage as a database backend:
- Amazon S3
- Azure Blob Storage
- Google Cloud Storage

**References**:
- https://scalardb.scalar-labs.com/docs/latest/requirements/#object-storage
- https://scalardb.scalar-labs.com/docs/latest/configurations/?databases=S3#storage-related-configurations

---

## Appendix A: MySQL to ScalarDB Data Type Reference

| MySQL Type | ScalarDB Type | Range/Limit | Notes |
|------------|---------------|-------------|-------|
| TINYINT | INT | -2^31 to 2^31-1 | Maps to larger type |
| SMALLINT | INT | -2^31 to 2^31-1 | Maps to larger type |
| MEDIUMINT | INT | -2^31 to 2^31-1 | Maps to larger type |
| INT/INTEGER | INT | -2^31 to 2^31-1 | Direct mapping |
| BIGINT | BIGINT | -2^53 to 2^53 | ⚠️ Range limitation |
| FLOAT | FLOAT | 32-bit IEEE 754 | Direct mapping |
| DOUBLE | DOUBLE | 64-bit IEEE 754 | Direct mapping |
| DECIMAL/NUMERIC | DOUBLE | ~15-17 digits | ⚠️ Precision loss possible |
| CHAR(n) | TEXT | Unlimited | Direct mapping |
| VARCHAR(n) | TEXT | Unlimited | Direct mapping |
| TINYTEXT | TEXT | Unlimited | Direct mapping |
| TEXT | TEXT | Unlimited | Direct mapping |
| MEDIUMTEXT | TEXT | Unlimited | Direct mapping |
| LONGTEXT | TEXT | Unlimited | Direct mapping |
| BINARY | BLOB | ~2GB | Direct mapping |
| VARBINARY | BLOB | ~2GB | Direct mapping |
| TINYBLOB | BLOB | ~2GB | Direct mapping |
| BLOB | BLOB | ~2GB | Direct mapping |
| MEDIUMBLOB | BLOB | ~2GB | Direct mapping |
| LONGBLOB | BLOB | ~2GB | ⚠️ Size limitation |
| TINYINT(1) | BOOLEAN | true/false | Direct mapping |
| BIT(1) | BOOLEAN | true/false | Direct mapping |
| DATE | DATE | 1000-01-01 to 9999-12-31 | Direct mapping |
| TIME | TIME | 00:00:00 to 23:59:59.999999 | Direct mapping |
| DATETIME | TIMESTAMP | millisecond precision | Direct mapping |
| TIMESTAMP | TIMESTAMPTZ | millisecond precision, UTC | Direct mapping |
| ENUM | TEXT | | ⚠️ App validation required |
| SET | TEXT | | ⚠️ App validation required |
| JSON | TEXT | | ⚠️ Loses operators |
| Spatial Types | NOT SUPPORTED | | |

---

## Appendix B: Unsupported MySQL Features Summary

| Feature | ScalarDB Status | Workaround |
|---------|-----------------|------------|
| AUTO_INCREMENT | Not Supported | UUID or app-level generator |
| ENUM Type | Not Supported | TEXT + application validation |
| SET Type | Not Supported | TEXT + application validation |
| JSON Type | Partial (as TEXT) | Store as TEXT, parse in app |
| Spatial Types | Not Supported | NOT SUPPORTED |
| Generated Columns | Not Supported | Compute in application |
| Stored Procedures | Not Supported | Application methods |
| Functions | Not Supported | Application methods |
| Triggers | Not Supported | Application event handling |
| Events | Not Supported | External scheduler |
| Views | Partial | Import as table or query |
| Fulltext Indexes | Not Supported | Vector Search or external |
| Spatial Indexes | Not Supported | NOT SUPPORTED |
| Foreign Key Constraints | Not Enforced | Application-level enforcement |
| ON DUPLICATE KEY | Not Supported | Read-check-write pattern |
| INSERT ... SELECT | Not Supported | Separate operations |
| REPLACE INTO | Not Supported | Delete + Insert |
| Subqueries | Not Supported | ScalarDB Analytics |
| Window Functions | Not Supported | ScalarDB Analytics |
| UNION/INTERSECT/EXCEPT | Not Supported | Multiple queries + app merge |

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
| MySQL Schema Import | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import/?databases=MySQL_MariaDB_TiDB | MySQL-specific import |

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
| Vector Search | https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/getting-started-with-vector-search/ |

---

*Analysis generated by Migrate MySQL to ScalarDB Schema Skill*
*Input consumed from: ${MYSQL_SCHEMA_REPORT_MD}*
