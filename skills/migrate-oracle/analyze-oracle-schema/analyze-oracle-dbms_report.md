# Oracle Database Schema Analysis Report

**Generated**: {metadata.generated_at}
**Schema**: {metadata.schema}
**Database**: {metadata.database_name}

---

## 1. Executive Summary

| Category | Count |
|----------|-------|
| Tables | {count of tables.tables} |
| Partitioned Tables | {count of tables.partitioned_tables} |
| Constraints | {count of tables.constraints} |
| Indexes | {count of indexes.indexes} |
| Views | {count of views.views} |
| Materialized Views | {count of views.materialized_views} |
| Object Types | {count of types.object_types} |
| Collection Types | {count of types.collection_types} |
| Procedures | {count of plsql.procedures} |
| Functions | {count of plsql.functions} |
| Packages | {count of plsql.packages} |
| Triggers | {count of plsql.triggers} |
| Sequences | {count of misc.sequences} |
| Synonyms | {count of misc.synonyms} |
| DB Links | {count of misc.db_links} |
| Scheduler Jobs | {count of misc.scheduler_jobs} |
| Invalid Objects | {count of dependencies.invalid_objects} |

---

## 2. Custom Types

> Skip this section if `types` is empty or not present.

### 2.1 Object Types

> Source: `types.object_types`

| Type Name | Attributes | Methods | Supertype | Final | Instantiable |
|-----------|------------|---------|-----------|-------|--------------|
| {TYPE_NAME} | {ATTRIBUTES} | {METHODS} | {SUPERTYPE_NAME} | {FINAL} | {INSTANTIABLE} |

#### Type Attributes

> Source: `types.type_attributes` - Group by TYPE_NAME

| Type Name | Attribute | Data Type | Position |
|-----------|-----------|-----------|----------|
| {TYPE_NAME} | {ATTR_NAME} | {ATTR_TYPE_NAME} | {ATTR_NO} |

#### Type Methods

> Source: `types.type_methods` - Group by TYPE_NAME

| Type Name | Method | Method Type | Parameters | Final | Overriding |
|-----------|--------|-------------|------------|-------|------------|
| {TYPE_NAME} | {METHOD_NAME} | {METHOD_TYPE} | {PARAMETERS} | {FINAL} | {OVERRIDING} |

### 2.2 Collection Types

> Source: `types.collection_types`

| Type Name | Collection Type | Element Type | Upper Bound |
|-----------|-----------------|--------------|-------------|
| {TYPE_NAME} | {COLL_TYPE} | {ELEM_TYPE_NAME} | {UPPER_BOUND} |

---

## 3. Tables

> Source: `tables.tables`

### 3.1 Table Summary

| Table Name | Est. Rows | Partitioned | Temporary | IOT Type | Compression | Logging |
|------------|-----------|-------------|-----------|----------|-------------|---------|
| {TABLE_NAME} | {NUM_ROWS} | {PARTITIONED} | {TEMPORARY} | {IOT_TYPE} | {COMPRESSION} | {LOGGING} |

### 3.2 Columns

> Source: `tables.columns` - Group by TABLE_NAME

| Table Name | Column Name | Data Type | Length | Precision | Scale | Nullable | Identity |
|------------|-------------|-----------|--------|-----------|-------|----------|----------|
| {TABLE_NAME} | {COLUMN_NAME} | {DATA_TYPE} | {DATA_LENGTH} | {DATA_PRECISION} | {DATA_SCALE} | {NULLABLE} | {IDENTITY_COLUMN} |

### 3.3 Identity Columns

> Source: `tables.identity_columns` - Skip if empty

| Table Name | Column Name | Generation Type | Options |
|------------|-------------|-----------------|---------|
| {TABLE_NAME} | {COLUMN_NAME} | {GENERATION_TYPE} | {IDENTITY_OPTIONS} |

### 3.4 Partitioned Tables

> Source: `tables.partitioned_tables` - Skip if empty

| Table Name | Partition Type | Subpartition Type | Partition Count |
|------------|----------------|-------------------|-----------------|
| {TABLE_NAME} | {PARTITIONING_TYPE} | {SUBPARTITIONING_TYPE} | {PARTITION_COUNT} |

#### Partition Keys

> Source: `tables.partition_keys`

| Table Name | Column Name | Position | Key Type |
|------------|-------------|----------|----------|
| {NAME} | {COLUMN_NAME} | {COLUMN_POSITION} | {OBJECT_TYPE} |

#### Partitions

> Source: `tables.partitions`

| Table Name | Partition Name | Position | High Value | Subpartitions |
|------------|----------------|----------|------------|---------------|
| {TABLE_NAME} | {PARTITION_NAME} | {PARTITION_POSITION} | {HIGH_VALUE} | {SUBPARTITION_COUNT} |

### 3.5 External Tables

> Source: `tables.external_tables` - Skip if empty

| Table Name | Access Driver | Default Directory | Reject Limit |
|------------|---------------|-------------------|--------------|
| {TABLE_NAME} | {TYPE_NAME} | {DEFAULT_DIRECTORY_NAME} | {REJECT_LIMIT} |

### 3.6 LOB Columns

> Source: `tables.lob_columns` - Skip if empty

| Table Name | Column Name | LOB Type | In Row | Chunk | Cache | Logging |
|------------|-------------|----------|--------|-------|-------|---------|
| {TABLE_NAME} | {COLUMN_NAME} | {SEGMENT_NAME} | {IN_ROW} | {CHUNK} | {CACHE} | {LOGGING} |

---

## 4. Constraints

> Source: `tables.constraints` - Group by CONSTRAINT_TYPE

### 4.1 Primary Keys

| Table Name | Constraint Name | Columns | Status | Validated | Deferrable |
|------------|-----------------|---------|--------|-----------|------------|
| {TABLE_NAME} | {CONSTRAINT_NAME} | {COLUMN_LIST} | {STATUS} | {VALIDATED} | {DEFERRABLE} |

### 4.2 Foreign Keys

> Source: `tables.foreign_key_details` for complete FK info

| Table Name | Constraint Name | Column Name | Ref Table | Ref Column | On Update | On Delete |
|------------|-----------------|-------------|-----------|------------|-----------|-----------|
| {TABLE_NAME} | {CONSTRAINT_NAME} | {COLUMN_NAME} | {REF_TABLE_NAME} | {REF_COLUMN_NAME} | {UPDATE_RULE} | {DELETE_RULE} |

### 4.3 Unique Constraints

| Table Name | Constraint Name | Columns | Status | Validated |
|------------|-----------------|---------|--------|-----------|
| {TABLE_NAME} | {CONSTRAINT_NAME} | {COLUMN_LIST} | {STATUS} | {VALIDATED} |

### 4.4 Check Constraints

| Table Name | Constraint Name | Check Clause | Status |
|------------|-----------------|--------------|--------|
| {TABLE_NAME} | {CONSTRAINT_NAME} | {SEARCH_CONDITION} | {STATUS} |

#### Constraint Columns

> Source: `tables.constraint_columns`

| Constraint Name | Table Name | Column Name | Position |
|-----------------|------------|-------------|----------|
| {CONSTRAINT_NAME} | {TABLE_NAME} | {COLUMN_NAME} | {POSITION} |

---

## 5. Indexes

> Source: `indexes.indexes`

### 5.1 Index Summary

| Index Name | Table Name | Index Type | Unique | Compression | Status | Partitioned |
|------------|------------|------------|--------|-------------|--------|-------------|
| {INDEX_NAME} | {TABLE_NAME} | {INDEX_TYPE} | {UNIQUENESS} | {COMPRESSION} | {STATUS} | {PARTITIONED} |

### 5.2 Index Columns

> Source: `indexes.index_columns`

| Index Name | Table Name | Column Name | Position | Descending |
|------------|------------|-------------|----------|------------|
| {INDEX_NAME} | {TABLE_NAME} | {COLUMN_NAME} | {COLUMN_POSITION} | {DESCEND} |

### 5.3 Function-Based Index Expressions

> Source: `indexes.index_expressions` - Skip if empty

| Index Name | Table Name | Expression | Position |
|------------|------------|------------|----------|
| {INDEX_NAME} | {TABLE_NAME} | {COLUMN_EXPRESSION} | {COLUMN_POSITION} |

### 5.4 Partitioned Indexes

> Source: `indexes.partitioned_indexes` - Skip if empty

| Index Name | Table Name | Partition Type | Locality | Partition Count |
|------------|------------|----------------|----------|-----------------|
| {INDEX_NAME} | {TABLE_NAME} | {PARTITIONING_TYPE} | {LOCALITY} | {PARTITION_COUNT} |

---

## 6. Views

> Source: `views.views`

### 6.1 View Summary

| View Name | Updatable | Check Option | Read Only |
|-----------|-----------|--------------|-----------|
| {VIEW_NAME} | {IS_UPDATABLE} | {CHECK_OPTION} | {READ_ONLY} |

### 6.2 View Definitions

> Source: `views.view_source` for the SQL text.
> **IMPORTANT**: If `view_source` contains truncated or incomplete SQL (e.g., only `SELECT` with no columns), then reconstruct the full view definition from `plsql.source` (type=VIEW) or from `tables.table_ddl` entries for the view name. Also cross-reference `dependencies.dependencies` to identify all base tables used by the view.

For each view, show the **complete** SQL definition:

```sql
-- View: {VIEW_NAME}
{FULL_VIEW_SQL}
```

> If the full SQL cannot be reconstructed from any source, document the view's base tables (from dependencies) and all output columns (from `views.view_columns`) so the migration team can reconstruct the query.

### 6.3 View Columns

> Source: `views.view_columns`

| View Name | Column Name | Data Type | Nullable | Updatable |
|-----------|-------------|-----------|----------|-----------|
| {VIEW_NAME} | {COLUMN_NAME} | {DATA_TYPE} | {NULLABLE} | {UPDATABLE} |

### 6.4 Materialized Views

> Source: `views.materialized_views` - Skip if empty

| View Name | Refresh Mode | Refresh Method | Build Mode | Last Refresh | Staleness |
|-----------|--------------|----------------|------------|--------------|-----------|
| {MVIEW_NAME} | {REFRESH_MODE} | {REFRESH_METHOD} | {BUILD_MODE} | {LAST_REFRESH_DATE} | {STALENESS} |

#### MView Queries

> Source: `views.mview_query`

```sql
-- Materialized View: {MVIEW_NAME}
{QUERY}
```

---

## 7. Stored Programs

### 7.1 Procedures

> Source: `plsql.procedures`

| Procedure Name | Deterministic | Parallel | Authid | Pipelined |
|----------------|---------------|----------|--------|-----------|
| {PROCEDURE_NAME} | {DETERMINISTIC} | {PARALLEL} | {AUTHID} | {PIPELINED} |

### 7.2 Functions

> Source: `plsql.functions`

| Function Name | Return Type | Deterministic | Parallel | Authid | Result Cache |
|---------------|-------------|---------------|----------|--------|--------------|
| {FUNCTION_NAME} | {RETURN_TYPE} | {DETERMINISTIC} | {PARALLEL} | {AUTHID} | {RESULT_CACHE} |

### 7.3 Packages

> Source: `plsql.packages`

| Package Name | Authid | Spec Status | Body Status |
|--------------|--------|-------------|-------------|
| {PACKAGE_NAME} | {AUTHID} | {SPEC_STATUS} | {BODY_STATUS} |

#### Package Procedures

> Source: `plsql.package_procedures`

| Package Name | Procedure Name | Overload | Pipelined | Deterministic |
|--------------|----------------|----------|-----------|---------------|
| {PACKAGE_NAME} | {PROCEDURE_NAME} | {OVERLOAD} | {PIPELINED} | {DETERMINISTIC} |

### 7.4 Parameters

> Source: `plsql.arguments` - Group by OBJECT_NAME

| Object Name | Parameter Name | Position | Data Type | Mode | Has Default |
|-------------|----------------|----------|-----------|------|-------------|
| {OBJECT_NAME} | {ARGUMENT_NAME} | {POSITION} | {DATA_TYPE} | {IN_OUT} | {DEFAULTED} |

### 7.5 Triggers

> Source: `plsql.triggers`

| Trigger Name | Table Name | Timing | Event | Status | Level |
|--------------|------------|--------|-------|--------|-------|
| {TRIGGER_NAME} | {TABLE_NAME} | {TRIGGER_TYPE} | {TRIGGERING_EVENT} | {STATUS} | {ACTION_TYPE} |

#### Trigger Ordering

> Source: `plsql.trigger_ordering` - Skip if empty

| Trigger Name | Referenced Trigger | Ordering Type |
|--------------|-------------------|---------------|
| {TRIGGER_NAME} | {REFERENCED_TRIGGER_NAME} | {ORDERING_TYPE} |

### 7.6 Compilation Errors

> Source: `plsql.errors` - Skip if empty

| Object Name | Object Type | Line | Position | Error |
|-------------|-------------|------|----------|-------|
| {NAME} | {TYPE} | {LINE} | {POSITION} | {TEXT} |

---

## 8. Sequences

> Source: `misc.sequences`

| Sequence Name | Min Value | Max Value | Increment | Cycle | Cache | Order | Last Number |
|---------------|-----------|-----------|-----------|-------|-------|-------|-------------|
| {SEQUENCE_NAME} | {MIN_VALUE} | {MAX_VALUE} | {INCREMENT_BY} | {CYCLE_FLAG} | {CACHE_SIZE} | {ORDER_FLAG} | {LAST_NUMBER} |

---

## 9. Synonyms

### 9.1 Private Synonyms

> Source: `misc.synonyms`

| Synonym Name | Table Owner | Table Name | DB Link |
|--------------|-------------|------------|---------|
| {SYNONYM_NAME} | {TABLE_OWNER} | {TABLE_NAME} | {DB_LINK} |

### 9.2 Public Synonyms

> Source: `misc.public_synonyms` - Skip if empty

| Synonym Name | Table Owner | Table Name | DB Link |
|--------------|-------------|------------|---------|
| {SYNONYM_NAME} | {TABLE_OWNER} | {TABLE_NAME} | {DB_LINK} |

---

## 10. Database Links

> Source: `misc.db_links` - Skip if empty

| DB Link | Username | Host | Created |
|---------|----------|------|---------|
| {DB_LINK} | {USERNAME} | {HOST} | {CREATED} |

---

## 11. Scheduler Jobs

### 11.1 DBMS_SCHEDULER Jobs

> Source: `misc.scheduler_jobs` - Skip if empty

| Job Name | Job Type | Enabled | State | Last Start | Next Run |
|----------|----------|---------|-------|------------|----------|
| {JOB_NAME} | {JOB_TYPE} | {ENABLED} | {STATE} | {LAST_START_DATE} | {NEXT_RUN_DATE} |

### 11.2 Scheduler Programs

> Source: `misc.scheduler_programs` - Skip if empty

| Program Name | Program Type | Enabled | Arguments |
|--------------|--------------|---------|-----------|
| {PROGRAM_NAME} | {PROGRAM_TYPE} | {ENABLED} | {NUMBER_OF_ARGUMENTS} |

### 11.3 Scheduler Schedules

> Source: `misc.scheduler_schedules` - Skip if empty

| Schedule Name | Repeat Interval | Start Date | End Date |
|---------------|-----------------|------------|----------|
| {SCHEDULE_NAME} | {REPEAT_INTERVAL} | {START_DATE} | {END_DATE} |

### 11.4 Legacy DBMS_JOB Jobs

> Source: `misc.legacy_jobs` - Skip if empty

| Job ID | What | Interval | Last Date | Next Date | Broken |
|--------|------|----------|-----------|-----------|--------|
| {JOB} | {WHAT} | {INTERVAL} | {LAST_DATE} | {NEXT_DATE} | {BROKEN} |

---

## 12. Security

### 12.1 Object Privileges

> Source: `security.object_privileges`

| Grantee | Object Name | Privilege | Is Grantable | Grantor |
|---------|-------------|-----------|--------------|---------|
| {GRANTEE} | {OBJECT_NAME} | {PRIVILEGE} | {GRANTABLE} | {GRANTOR} |

### 12.2 Column Privileges

> Source: `security.column_privileges` - Skip if empty

| Table Name | Column Name | Grantee | Privilege | Is Grantable |
|------------|-------------|---------|-----------|--------------|
| {TABLE_NAME} | {COLUMN_NAME} | {GRANTEE} | {PRIVILEGE} | {GRANTABLE} |

### 12.3 System Privileges

> Source: `security.system_privileges`

| Privilege | Admin Option |
|-----------|--------------|
| {PRIVILEGE} | {ADMIN_OPTION} |

### 12.4 Role Privileges

> Source: `security.role_privileges`

| Role | Admin Option | Default |
|------|--------------|---------|
| {GRANTED_ROLE} | {ADMIN_OPTION} | {DEFAULT_ROLE} |

### 12.5 VPD Policies

> Source: `security.vpd_policies` - Skip if empty

| Object Name | Policy Name | Function | Select | Insert | Update | Delete | Enabled |
|-------------|-------------|----------|--------|--------|--------|--------|---------|
| {OBJECT_NAME} | {POLICY_NAME} | {FUNCTION} | {SEL} | {INS} | {UPD} | {DEL} | {ENABLE} |

---

## 13. Oracle-Specific Features

### 13.1 XMLType Columns

> Source: `misc.xmltype_columns` - Skip if empty

| Table Name | Column Name | Storage Type | Schema |
|------------|-------------|--------------|--------|
| {TABLE_NAME} | {COLUMN_NAME} | {STORAGE_TYPE} | {XMLSCHEMA} |

### 13.2 JSON Columns

> Source: `misc.json_columns` - Skip if empty

| Table Name | Column Name | Format | Constraint |
|------------|-------------|--------|------------|
| {TABLE_NAME} | {COLUMN_NAME} | {FORMAT} | {CONSTRAINT_NAME} |

### 13.3 Spatial Columns

> Source: `misc.spatial_columns` - Skip if empty

| Table Name | Column Name | SRID | Dimension Info |
|------------|-------------|------|----------------|
| {TABLE_NAME} | {COLUMN_NAME} | {SRID} | {DIMINFO} |

### 13.4 Advanced Queuing

#### Queue Tables

> Source: `misc.aq_queue_tables` - Skip if empty

| Queue Table | Object Type | Sort Order | Multi-Consumer |
|-------------|-------------|------------|----------------|
| {QUEUE_TABLE} | {OBJECT_TYPE} | {SORT_ORDER} | {RECIPIENTS} |

#### Queues

> Source: `misc.aq_queues` - Skip if empty

| Queue Name | Queue Table | Queue Type | Enqueue | Dequeue |
|------------|-------------|------------|---------|---------|
| {NAME} | {QUEUE_TABLE} | {QUEUE_TYPE} | {ENQUEUE_ENABLED} | {DEQUEUE_ENABLED} |

### 13.5 Directories

> Source: `misc.directories` - Skip if empty

| Directory Name | Path |
|----------------|------|
| {DIRECTORY_NAME} | {DIRECTORY_PATH} |

### 13.6 Editions

> Source: `misc.editions` - Skip if empty

| Edition Name | Parent | Usable |
|--------------|--------|--------|
| {EDITION_NAME} | {PARENT_EDITION_NAME} | {USABLE} |

### 13.7 Flashback Data Archives

> Source: `misc.flashback_archives` - Skip if empty

| Archive Name | Status | Retention Days |
|--------------|--------|----------------|
| {FLASHBACK_ARCHIVE_NAME} | {STATUS} | {RETENTION_IN_DAYS} |

---

## 14. Dependencies

### 14.1 Object Dependencies

> Source: `dependencies.dependencies` - Show key dependencies

| Object Name | Object Type | References | Ref Type | Dependency Type |
|-------------|-------------|------------|----------|-----------------|
| {OBJECT_NAME} | {OBJECT_TYPE} | {REFERENCED_NAME} | {REFERENCED_TYPE} | {DEPENDENCY_TYPE} |

### 14.2 External Dependencies

> Source: `dependencies.external_dependencies` - Objects depending on other schemas

| Object Name | Object Type | External Owner | External Object | External Type |
|-------------|-------------|----------------|-----------------|---------------|
| {OBJECT_NAME} | {OBJECT_TYPE} | {REFERENCED_OWNER} | {REFERENCED_NAME} | {REFERENCED_TYPE} |

### 14.3 SYS Package Dependencies

> Source: `dependencies.sys_dependencies` - Built-in Oracle packages used

| Object Name | Object Type | SYS Package | Package Type |
|-------------|-------------|-------------|--------------|
| {OBJECT_NAME} | {OBJECT_TYPE} | {SYS_OBJECT} | {SYS_OBJECT_TYPE} |

### 14.4 Invalid Objects

> Source: `dependencies.invalid_objects` - Skip if empty

| Object Name | Object Type | Status | Last DDL |
|-------------|-------------|--------|----------|
| {OBJECT_NAME} | {OBJECT_TYPE} | {STATUS} | {LAST_DDL_TIME} |

### 14.5 Compilation Errors

> Source: `dependencies.object_errors` - Skip if empty

| Object Name | Object Type | Line | Position | Error |
|-------------|-------------|------|----------|-------|
| {OBJECT_NAME} | {OBJECT_TYPE} | {LINE} | {POSITION} | {ERROR_MESSAGE} |

### 14.6 Foreign Key Dependencies

> Source: `dependencies.fk_dependencies`

| Table Name | Constraint Name | Ref Table |
|------------|-----------------|-----------|
| {TABLE_NAME} | {CONSTRAINT_NAME} | {REFERENCED_TABLE} |

### 14.7 Table Dependency Sequence (Migration Order)

> Source: `dependencies.migration_order` - List in order

Tables should be migrated in this order based on foreign key dependency analysis:

1. {object_name_1}
2. {object_name_2}
3. ...

---

## 15. All Objects Summary

> Source: `dependencies.all_objects`

| Object Name | Object Type | Status | Created | Last DDL |
|-------------|-------------|--------|---------|----------|
| {OBJECT_NAME} | {OBJECT_TYPE} | {STATUS} | {CREATED} | {LAST_DDL_TIME} |

---

## Appendix A: DDL Scripts

### A.1 Table DDL

> Source: `tables.table_ddl` - Dictionary of table_name -> DDL

For each table:

```sql
-- Table: {TABLE_NAME}
{DDL}
```

### A.2 Procedure DDL

> Source: `plsql.procedure_ddl`

```sql
-- Procedure: {PROCEDURE_NAME}
{DDL}
```

### A.3 Function DDL

> Source: `plsql.function_ddl`

```sql
-- Function: {FUNCTION_NAME}
{DDL}
```

### A.4 Package DDL

> Source: `plsql.package_ddl` - Contains 'spec' and 'body' for each package

```sql
-- Package Spec: {PACKAGE_NAME}
{spec}

-- Package Body: {PACKAGE_NAME}
{body}
```

### A.5 Trigger DDL

> Source: `plsql.trigger_ddl`

```sql
-- Trigger: {TRIGGER_NAME}
{DDL}
```

---

## Appendix B: Source Code

### B.1 Source Code by Object

> Source: `plsql.source` - Group by NAME, TYPE, order by LINE

```sql
-- {TYPE}: {NAME}
{concatenated TEXT lines}
```

---

## Report Generation Notes

**Instructions for Claude:**

1. Read `raw_schema_data.json` from the configured OUTPUT_DIR
2. For each section, check if the data exists and is non-empty
3. **Skip sections entirely** if no data exists - do not show empty tables
4. Replace field placeholders `{FIELD_NAME}` with actual values from JSON
5. Group data by relevant keys where indicated (e.g., columns by TABLE_NAME)
6. Format DDL code blocks properly with syntax highlighting
7. Calculate counts for the Executive Summary from actual data
8. Preserve data types (don't convert nulls to strings)

**JSON Structure Reference:**

```
{
  "metadata": { generated_at, schema, database_name },
  "types": { object_types, type_attributes, type_methods, collection_types, ... },
  "tables": { tables, columns, constraints, foreign_key_details, table_ddl, ... },
  "indexes": { indexes, index_columns, index_expressions, ... },
  "views": { views, view_source, materialized_views, mview_query, ... },
  "plsql": { procedures, functions, packages, triggers, source, *_ddl, ... },
  "security": { object_privileges, system_privileges, role_privileges, ... },
  "misc": { sequences, synonyms, db_links, scheduler_jobs, ... },
  "dependencies": { dependencies, invalid_objects, migration_order, ... }
}
```
