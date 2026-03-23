# ScalarDB Migration Analysis Report Template

This template is used to generate the **migration analysis** report. Replace all `{{PLACEHOLDER}}` tokens with actual values from the source Oracle schema report.

**Input Source**: This report consumes `oracle_schema_report.md` from the configured output directory (Skill 1 output).

---

# Oracle to ScalarDB Migration Analysis

**Generated**: {{TIMESTAMP}}
**Source Database**: {{DATABASE_NAME}}
**Source Schema**: {{SCHEMA_NAME}}
**Oracle Version**: {{ORACLE_VERSION}}
**Target**: ScalarDB 3.17+
**Primary Migration Path**: ScalarDB Java Transaction API

---

## 1. Migration Strategy

### ScalarDB Component Selection

Determine which ScalarDB components are required based on the database analysis:

| Component | When to Use | License |
|-----------|-------------|---------|
| **ScalarDB Core** (Java Transaction API) | Default for all migrations — CRUD operations, schema import, application access | Open Source / Community |
| **ScalarDB Cluster** (SQL interface) | Only if SQL interface is needed, or aggregate functions (GROUP BY, HAVING) are needed for small use cases | Enterprise |
| **ScalarDB Analytics** | Complex queries: multi-table JOINs (3+), subqueries, window functions, UNION/INTERSECT/EXCEPT, reporting queries | Enterprise |

**Decision Logic:**
1. Start with **ScalarDB Core** (Java Transaction API) — this is always the foundation
2. Add **ScalarDB Cluster** only if the application needs a SQL interface or simple aggregate queries
3. Add **ScalarDB Analytics** if complex queries exist that cannot be decomposed into simple CRUD operations

### Oracle AQ Decision (Oracle Source Databases Only)

**If the Oracle database contains triggers or stored procedures that perform DML on other tables, Oracle AQ MUST be used.** This is a design decision, not optional.

| Condition | Decision |
|-----------|----------|
| Triggers with cross-table DML exist | Oracle AQ is **MANDATORY** |
| Stored procedures with INSERT/UPDATE/DELETE exist | Oracle AQ is **MANDATORY** |
| Only validation triggers (no DML) | AQ not needed — convert to application validation |
| No triggers or stored procedures | AQ not needed |

**Rationale:** The goal is to keep existing database behavior unchanged. Oracle AQ ensures that trigger-driven operations continue to work at the database level, while the Java consumer processes the events and writes through ScalarDB.

### Document Generation Order

This migration analysis follows the strategy above. The subsequent documents must be generated in this order:
1. **Migration Analysis** (this document) — compatibility analysis following the strategy
2. **AQ Setup** (`aq_setup.sql`) — Oracle AQ infrastructure (if triggers/SPs with DML exist)
3. **AQ Migration Report** — AQ conversion details and consumer integration guide
4. **Migration Steps** — final step-by-step guide incorporating all of the above

---

## 2. Executive Summary

### Migration Scope Overview

| Object Type | Count | ScalarDB Compatibility | Migration Effort |
|-------------|-------|------------------------|------------------|
| Tables | {{TABLE_COUNT}} | {{TABLE_COMPAT}} | {{TABLE_EFFORT}} |
| Custom Types | {{TYPE_COUNT}} | {{TYPE_COMPAT}} | {{TYPE_EFFORT}} |
| Indexes | {{INDEX_COUNT}} | {{INDEX_COMPAT}} | {{INDEX_EFFORT}} |
| Views | {{VIEW_COUNT}} | {{VIEW_COMPAT}} | {{VIEW_EFFORT}} |
| Materialized Views | {{MVIEW_COUNT}} | {{MVIEW_COMPAT}} | {{MVIEW_EFFORT}} |
| Procedures | {{PROC_COUNT}} | {{PROC_COMPAT}} | {{PROC_EFFORT}} |
| Functions | {{FUNC_COUNT}} | {{FUNC_COMPAT}} | {{FUNC_EFFORT}} |
| Packages | {{PKG_COUNT}} | {{PKG_COMPAT}} | {{PKG_EFFORT}} |
| Triggers | {{TRIGGER_COUNT}} | {{TRIGGER_COMPAT}} | {{TRIGGER_EFFORT}} |
| Sequences | {{SEQ_COUNT}} | {{SEQ_COMPAT}} | {{SEQ_EFFORT}} |
| Synonyms | {{SYN_COUNT}} | {{SYN_COMPAT}} | {{SYN_EFFORT}} |
| Database Links | {{DBLINK_COUNT}} | {{DBLINK_COMPAT}} | {{DBLINK_EFFORT}} |

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

## 3. Data Type Mapping Analysis

### Oracle to ScalarDB Type Conversions

| Oracle Column | Oracle Type | ScalarDB Type | Conversion Notes | Risk |
|---------------|-------------|---------------|------------------|------|
| {{TABLE}}.{{COLUMN}} | {{ORACLE_TYPE}} | {{SCALARDB_TYPE}} | {{NOTES}} | {{RISK}} |

### Type Conversion Summary

| Oracle Type | Count | ScalarDB Type | Conversion Status |
|-------------|-------|---------------|-------------------|
| {{ORACLE_TYPE}} | {{COUNT}} | {{SCALARDB_TYPE}} | {{STATUS}} |

### Critical Data Type Warnings

#### BIGINT Range Limitation
- **ScalarDB BIGINT Range**: -2^53 to 2^53 (-9,007,199,254,740,992 to 9,007,199,254,740,992)
- **Affected Columns**: {{BIGINT_AFFECTED_COLS}}
- **Action Required**: {{BIGINT_ACTION}}

#### BLOB Size Limitation
- **ScalarDB BLOB Max Size**: ~2GB (2^31-1 bytes)
- **Affected Columns**: {{BLOB_AFFECTED_COLS}}
- **Action Required**: {{BLOB_ACTION}}

#### Precision Loss Risk
- **Affected Columns**: {{PRECISION_AFFECTED_COLS}}
- **Details**: {{PRECISION_DETAILS}}

---

## 4. Table Analysis

### Table Compatibility Matrix

| Table Name | Columns | Has PK | Has LOBs | Has Custom Types | Nested Tables | Compatibility |
|------------|---------|--------|----------|------------------|---------------|---------------|
| {{TABLE_NAME}} | {{COL_COUNT}} | {{HAS_PK}} | {{HAS_LOBS}} | {{HAS_CUSTOM_TYPES}} | {{HAS_NESTED}} | {{COMPAT_STATUS}} |

### Detailed Table Analysis

#### Table: {{TABLE_NAME}}

**Oracle Structure:**
- Columns: {{COLUMN_COUNT}}
- Primary Key: {{PK_COLUMNS}}
- Has LOBs: {{HAS_LOB_COLUMNS}}
- Has Custom Types: {{HAS_CUSTOM_TYPE_COLUMNS}}

**Column Mapping:**

| Column | Oracle Type | ScalarDB Type | Nullable | Notes |
|--------|-------------|---------------|----------|-------|
| {{COLUMN_NAME}} | {{ORACLE_TYPE}} | {{SCALARDB_TYPE}} | {{NULLABLE}} | {{NOTES}} |

**ScalarDB Key Design:**
- **Partition Key**: {{PARTITION_KEY}}
- **Clustering Key**: {{CLUSTERING_KEY}}
- **Secondary Indexes**: {{SECONDARY_INDEXES}}

**Migration Notes:**
{{TABLE_MIGRATION_NOTES}}

---

## 5. Custom Types Analysis

### Object Types

| Type Name | Attributes | Methods | Used By | Migration Approach |
|-----------|------------|---------|---------|-------------------|
| {{TYPE_NAME}} | {{ATTR_COUNT}} | {{METHOD_COUNT}} | {{USED_BY}} | {{APPROACH}} |

### Object Type Flattening Plan

#### Type: {{TYPE_NAME}}

**Original Attributes:**
| Attribute | Data Type | ScalarDB Equivalent |
|-----------|-----------|---------------------|
| {{ATTR_NAME}} | {{ATTR_TYPE}} | {{SCALARDB_TYPE}} |

**Flattening Strategy:**
- Prefix: `{{PREFIX}}_`
- Target Columns: {{FLATTENED_COLUMNS}}

### Collection Types

| Type Name | Element Type | Used In | Migration Approach |
|-----------|--------------|---------|-------------------|
| {{COLL_TYPE_NAME}} | {{ELEMENT_TYPE}} | {{USED_IN}} | {{APPROACH}} |

### Nested Table Migration Plan

| Parent Table | Nested Column | Storage Table | Migration Strategy |
|--------------|---------------|---------------|-------------------|
| {{PARENT_TABLE}} | {{NESTED_COL}} | {{STORAGE_TABLE}} | {{STRATEGY}} |

---

## 6. Constraint Analysis

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

## 7. Index Analysis

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

### Unsupported Index Types
| Index | Type | Reason | Workaround |
|-------|------|--------|------------|
| {{INDEX}} | {{TYPE}} | {{REASON}} | {{WORKAROUND}} |

---

## 8. PL/SQL Objects Analysis

### Stored Procedures

| Procedure | Parameters | Complexity | Migration Effort |
|-----------|------------|------------|------------------|
| {{PROC_NAME}} | {{PARAM_COUNT}} | {{COMPLEXITY}} | {{EFFORT}} |

### Functions

| Function | Parameters | Return Type | Complexity | Migration Effort |
|----------|------------|-------------|------------|------------------|
| {{FUNC_NAME}} | {{PARAM_COUNT}} | {{RETURN_TYPE}} | {{COMPLEXITY}} | {{EFFORT}} |

### Packages

| Package | Procedures | Functions | Complexity | Migration Effort |
|---------|------------|-----------|------------|------------------|
| {{PKG_NAME}} | {{PROC_COUNT}} | {{FUNC_COUNT}} | {{COMPLEXITY}} | {{EFFORT}} |

### Triggers

| Trigger | Table | Event | Timing | Migration Approach |
|---------|-------|-------|--------|-------------------|
| {{TRIGGER_NAME}} | {{TABLE}} | {{EVENT}} | {{TIMING}} | {{APPROACH}} |

### PL/SQL Migration Summary

**Total PL/SQL Objects**: {{TOTAL_PLSQL}}
**Migration Approach**: Convert to application code (Java/Kotlin/etc.)
**Estimated Effort**: {{PLSQL_EFFORT}}

---

## 9. Views and Materialized Views Analysis

### Standard Views

| View Name | Base Tables | Complexity | Migration Approach |
|-----------|-------------|------------|-------------------|
| {{VIEW_NAME}} | {{BASE_TABLES}} | {{COMPLEXITY}} | {{APPROACH}} |

### Materialized Views

| MView Name | Refresh Method | Base Tables | Migration Approach |
|------------|----------------|-------------|-------------------|
| {{MVIEW_NAME}} | {{REFRESH}} | {{BASE_TABLES}} | {{APPROACH}} |

---

## 10. LOB Storage Analysis

### LOB Columns

| Table | Column | LOB Type | Size Concern | SecureFile | Migration Notes |
|-------|--------|----------|--------------|------------|-----------------|
| {{TABLE}} | {{COLUMN}} | {{LOB_TYPE}} | {{SIZE_CONCERN}} | {{SECUREFILE}} | {{NOTES}} |

### BFILE Columns (External Files)

| Table | Column | Directory | Migration Required |
|-------|--------|-----------|-------------------|
| {{TABLE}} | {{COLUMN}} | {{DIRECTORY}} | File migration + column type change |

---

## 11. Sequences Analysis

| Sequence | Start | Increment | Used By | Replacement Strategy |
|----------|-------|-----------|---------|---------------------|
| {{SEQ_NAME}} | {{START_VAL}} | {{INCREMENT}} | {{USED_BY}} | {{STRATEGY}} |

**Sequence Replacement Options:**
1. UUID generation (recommended for distributed systems)
2. Application-level ID generator (Snowflake, etc.)
3. Database-specific auto-increment (if using single underlying database)

---

## 12. Database Links and Synonyms

### Database Links

| DB Link | Host | Used By | Migration Impact |
|---------|------|---------|------------------|
| {{DBLINK_NAME}} | {{HOST}} | {{USED_BY}} | {{IMPACT}} |

### Synonyms

| Synonym | Target Object | Migration Approach |
|---------|---------------|-------------------|
| {{SYNONYM}} | {{TARGET}} | Update all references |

---

## 13. Security Model Analysis

### Object Privileges

| Object | Grantee | Privilege | ScalarDB Approach |
|--------|---------|-----------|-------------------|
| {{OBJECT}} | {{GRANTEE}} | {{PRIVILEGE}} | {{APPROACH}} |

### VPD Policies

| Policy | Object | Migration Impact |
|--------|--------|------------------|
| {{POLICY}} | {{OBJECT}} | Requires application-level security |

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
| 0-2 | All standard types (NUMBER, VARCHAR2, DATE) with direct mapping |
| 3-4 | Some LOBs (CLOB, BLOB) requiring size validation |
| 5-6 | BFILE columns, complex NUMBER precision |
| 7-8 | Object types requiring flattening |
| 9-10 | Nested tables, VARRAYs, complex collections |

#### Schema Complexity (Weight: 25%)
| Score Range | Criteria |
|-------------|----------|
| 0-2 | Simple tables with standard constraints |
| 3-4 | Foreign keys, composite primary keys |
| 5-6 | Views requiring conversion |
| 7-8 | Materialized views, partitioned tables |
| 9-10 | Object types, nested tables, type inheritance |

#### PL/SQL Complexity (Weight: 25%)
| Score Range | Criteria |
|-------------|----------|
| 0 | No PL/SQL objects |
| 1-3 | Simple procedures/functions (<10) |
| 4-6 | Moderate PL/SQL (10-50 objects, some packages) |
| 7-8 | Complex PL/SQL (50+ objects, triggers, packages) |
| 9-10 | Heavy PL/SQL (business logic in database) |

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
| PL/SQL Complexity | {{PLSQL_SCORE}}/10 | 25% | {{PLSQL_WEIGHTED}} |
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
Schema Migration Effort = (Tables × 0.5) + (Custom Types × 2) + (Nested Tables × 3) + (Unsupported Columns × 1)
Data Migration Effort = (Tables × 1) + (LOB Columns × 2) + (Row Estimate / 100000)
Application Migration Effort = (PL/SQL Objects × 4) + (Triggers × 3) + (Complex Queries × 2) + (FK Relationships × 0.5)
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

ScalarDB SQL has significant differences from traditional RDBMS SQL (MySQL, Oracle, PostgreSQL). These limitations must be understood for successful migration.

### ScalarDB Execution Model

ScalarDB operates as a **distributed key-value store** with SQL interface. Understanding this is critical:

| Aspect | Traditional RDBMS | ScalarDB |
|--------|-------------------|----------|
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

**Example of DNF (valid)**:
```sql
WHERE (a = 1 AND b = 2) OR (a = 3 AND b = 4)
```

### Cross-Partition Operations

| Operation | Without Partition Key | Impact |
|-----------|----------------------|--------|
| UPDATE | Requires cross-partition scan | Performance degradation |
| DELETE | Requires cross-partition scan | Performance degradation |
| SELECT | Full table scan | Must be explicitly enabled |

### Secondary Index Limitations

| Limitation | Description |
|------------|-------------|
| Encrypted columns | Cannot create secondary indexes on encrypted columns |
| Object storage | May not support secondary indexes depending on backend |

### Encrypted Column Restrictions

| Feature | Encrypted Columns |
|---------|-------------------|
| WHERE conditions | ❌ NOT allowed |
| ORDER BY clauses | ❌ NOT allowed |
| Secondary indexes | ❌ Cannot be created |

---

## 19. ScalarDB Analytics Assessment

> **When ScalarDB Analytics is Required**: If your schema uses complex JOINs, subqueries, window functions, or analytical queries, you MUST plan for ScalarDB Analytics deployment.

### Supported vs Requires Analytics

| Feature | ScalarDB SQL | ScalarDB Analytics |
|---------|--------------|-------------------|
| Simple CRUD | ✅ Use | Not needed |
| Single-partition queries | ✅ Use | Not needed |
| Simple 2-table JOINs | ✅ Use (within partition) | Use if cross-partition |
| Multi-table JOINs | ⚠️ Performance issues | ✅ **Recommended** |
| Subqueries | ❌ Not supported | ✅ **Required** |
| Window functions (ROW_NUMBER, RANK, etc.) | ❌ Not supported | ✅ **Required** |
| Complex aggregations | ⚠️ Limited | ✅ **Recommended** |
| UNION / INTERSECT / EXCEPT | ❌ Not supported | ✅ **Required** |
| Analytical/reporting queries | ⚠️ Not optimized | ✅ **Required** |

### Schema Analysis for Analytics Requirements

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
| Analytics CLI Reference | https://scalardb.scalar-labs.com/docs/latest/scalardb-analytics/reference-cli-command/ |

---

## 20. Partition Key Design Recommendations

> **Critical for Performance**: Poor partition key design leads to cross-partition operations and performance degradation.

### Partition Key Design Guidelines

| Guideline | Description |
|-----------|-------------|
| High cardinality | Choose keys with many distinct values |
| Query patterns | Include partition key in most WHERE clauses |
| Even distribution | Avoid hot partitions |
| JOIN optimization | Related tables should have compatible partition keys |

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

## Appendix A: ScalarDB Data Type Reference

| ScalarDB Type | Range/Limit | Oracle Equivalent |
|---------------|-------------|-------------------|
| BOOLEAN | true/false | NUMBER(1) |
| INT | -2^31 to 2^31-1 | NUMBER(10) |
| BIGINT | -2^53 to 2^53 | NUMBER(16) |
| FLOAT | 32-bit IEEE 754 | BINARY_FLOAT |
| DOUBLE | 64-bit IEEE 754 | BINARY_DOUBLE |
| TEXT | Unlimited | VARCHAR2, CLOB |
| BLOB | ~2GB | BLOB |
| DATE | 1000-01-01 to 9999-12-31 | DATE |
| TIME | 00:00:00 to 23:59:59.999999 | N/A |
| TIMESTAMP | millisecond precision | TIMESTAMP |
| TIMESTAMPTZ | millisecond precision, UTC | TIMESTAMP WITH TIME ZONE |

---

## Appendix B: Unsupported Oracle Features Summary

| Feature | ScalarDB Status | Workaround |
|---------|-----------------|------------|
| Object Types | Not Supported | Flatten to columns |
| Nested Tables | Not Supported | Separate table |
| VARRAYs | Not Supported | Separate table or JSON |
| Sequences | Not Supported | UUID or app-level generator |
| Triggers | Not Supported | Application event handling |
| Stored Procedures | Not Supported | Application methods |
| Functions | Not Supported | Application methods |
| Packages | Not Supported | Application classes |
| Views | Partial | Import as table or query |
| Materialized Views | Not Supported | Application caching |
| Database Links | Not Supported | Multiple connections |
| VPD Policies | Not Supported | Application security |
| XMLType | Not Supported | TEXT column |
| Spatial Types | Not Supported | Custom solution |
| BFILE | Not Supported | BLOB + file migration |

---

## Appendix C: Mandatory ScalarDB Documentation References

### Primary Migration Path: ScalarDB Java Transaction API

| Reference | URL | Purpose |
|-----------|-----|---------|
| ScalarDB Java Transaction API | https://scalardb.scalar-labs.com/docs/latest/api-guide/ | Transaction API (Get/Scan/Insert/Update/Delete) |
| ScalarDB SQL Grammar Reference | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/grammar/ | SQL syntax reference |
| ScalarDB SQL Migration Guide | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/migration-guide | Step-by-step migration instructions |

### Schema and Data Type References

| Reference | URL | Purpose |
|-----------|-----|---------|
| Schema Loader Data Type Mapping | https://scalardb.scalar-labs.com/docs/latest/schema-loader/#data-type-mapping-between-scalardb-and-other-databases | Type conversion reference |
| Schema Loader Import | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import | Importing existing tables |
| Data Type Mapping (Import) | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import#data-type-mapping-from-jdbc-databases-to-scalardb | Oracle → ScalarDB types |

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

## RECOMMENDED: Transaction Metadata Decoupling

> **For this migration, we recommend using `transaction-metadata-decoupling: true` instead of `transaction: true`.**

This approach keeps your **existing Oracle tables unchanged** — ScalarDB stores its transaction metadata in separate `<table>_scalardb` tables.

| Approach | Alters Existing Tables? | Recommended For |
|----------|------------------------|-----------------|
| `transaction: true` | YES — adds metadata columns | New tables only |
| `transaction-metadata-decoupling: true` | **NO — tables unchanged** | **Migrating existing tables** |

**Reference**: https://scalardb.scalar-labs.com/docs/latest/schema-loader-import/#decoupling-transaction-metadata

---

*Analysis generated by Migrate to ScalarDB Schema Skill*
*Input consumed from: ${ORACLE_SCHEMA_REPORT_MD}*
