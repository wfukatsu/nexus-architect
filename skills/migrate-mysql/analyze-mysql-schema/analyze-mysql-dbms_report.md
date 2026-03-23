# MySQL Database Schema Analysis Report

**Generated**: {metadata.generated_at}
**Database**: {metadata.database}
**MySQL Version**: {metadata.mysql_version}
**Server**: {metadata.server_info}
**Hostname**: {metadata.hostname}

---

## 1. Executive Summary

| Category | Count |
|----------|-------|
| Tables | {count of tables.tables} |
| Partitioned Tables | {count of tables.partitioned_tables} |
| Constraints | {count of tables.constraints} |
| Indexes | {count of indexes.indexes} |
| Views | {count of views.views} |
| Stored Procedures | {count of routines.procedures} |
| Stored Functions | {count of routines.functions} |
| Triggers | {count of routines.triggers} |
| Events | {count of routines.events} |
| Auto-increment Columns | {count of tables.auto_increment_columns} |
| Generated Columns | {count of tables.generated_columns} |

### Storage Engines

| Engine | Table Count |
|--------|-------------|
| {ENGINE} | {count} |

### Data Type Distribution

| Data Type | Count |
|-----------|-------|
| {DATA_TYPE} | {count} |

---

## 2. Custom Types

> Skip this section if no special types exist.

### 2.1 ENUM Columns

> Source: `misc.enum_set_columns` - Filter for ENUM - Skip if empty

| Table Name | Column Name | Allowed Values |
|------------|-------------|----------------|
| {TABLE_NAME} | {COLUMN_NAME} | {COLUMN_TYPE} |

### 2.2 SET Columns

> Source: `misc.enum_set_columns` - Filter for SET - Skip if empty

| Table Name | Column Name | Allowed Values |
|------------|-------------|----------------|
| {TABLE_NAME} | {COLUMN_NAME} | {COLUMN_TYPE} |

### 2.3 JSON Columns

> Source: `misc.json_columns` - Skip if empty

| Table Name | Column Name | Notes |
|------------|-------------|-------|
| {TABLE_NAME} | {COLUMN_NAME} | JSON type |

### 2.4 Spatial Columns (Geometry Types)

> Source: `misc.spatial_columns` - Skip if empty

| Table Name | Column Name | Geometry Type | SRID |
|------------|-------------|---------------|------|
| {TABLE_NAME} | {COLUMN_NAME} | {DATA_TYPE} | {SRS_ID} |

---

## 3. Tables

> Source: `tables.tables`

### 3.1 Table Summary

| Table Name | Engine | Row Format | Est. Rows | Data Size | Index Size | Auto Inc | Collation |
|------------|--------|------------|-----------|-----------|------------|----------|-----------|
| {TABLE_NAME} | {ENGINE} | {ROW_FORMAT} | {TABLE_ROWS} | {DATA_LENGTH} | {INDEX_LENGTH} | {AUTO_INCREMENT} | {TABLE_COLLATION} |

### 3.2 Columns

> Source: `tables.columns` - Group by TABLE_NAME

| Table Name | Column Name | Data Type | Column Type | Nullable | Key | Default | Extra |
|------------|-------------|-----------|-------------|----------|-----|---------|-------|
| {TABLE_NAME} | {COLUMN_NAME} | {DATA_TYPE} | {COLUMN_TYPE} | {IS_NULLABLE} | {COLUMN_KEY} | {COLUMN_DEFAULT} | {EXTRA} |

### 3.3 Auto-increment Columns

> Source: `tables.auto_increment_columns` - Skip if empty

| Table Name | Column Name | Data Type | Column Type | Current Value |
|------------|-------------|-----------|-------------|---------------|
| {TABLE_NAME} | {COLUMN_NAME} | {DATA_TYPE} | {COLUMN_TYPE} | {AUTO_INCREMENT} |

### 3.4 Generated Columns

> Source: `tables.generated_columns` - Skip if empty

| Table Name | Column Name | Data Type | Generation Expression | Storage |
|------------|-------------|-----------|----------------------|---------|
| {TABLE_NAME} | {COLUMN_NAME} | {DATA_TYPE} | {GENERATION_EXPRESSION} | {EXTRA} |

### 3.5 Partitioned Tables

> Source: `tables.partitioned_tables` - Skip if empty

| Table Name | Partition Method | Partition Expression | Subpartition Method | Partition Count |
|------------|------------------|---------------------|---------------------|-----------------|
| {TABLE_NAME} | {PARTITION_METHOD} | {PARTITION_EXPRESSION} | {SUBPARTITION_METHOD} | {PARTITION_COUNT} |

#### Partitions

> Source: `tables.partitions`

| Table Name | Partition Name | Subpartition Name | Position | Description | Rows | Data Length |
|------------|----------------|-------------------|----------|-------------|------|-------------|
| {TABLE_NAME} | {PARTITION_NAME} | {SUBPARTITION_NAME} | {PARTITION_ORDINAL_POSITION} | {PARTITION_DESCRIPTION} | {TABLE_ROWS} | {DATA_LENGTH} |

### 3.6 LOB Columns (TEXT/BLOB)

> Source: `tables.lob_columns` - Skip if empty

| Table Name | Column Name | Data Type | Max Length | Character Set |
|------------|-------------|-----------|------------|---------------|
| {TABLE_NAME} | {COLUMN_NAME} | {DATA_TYPE} | {CHARACTER_MAXIMUM_LENGTH} | {CHARACTER_SET_NAME} |

---

## 4. Constraints

> Source: `tables.constraints` - Group by CONSTRAINT_TYPE

### 4.1 Primary Keys

| Table Name | Constraint Name | Columns |
|------------|-----------------|---------|
| {TABLE_NAME} | {CONSTRAINT_NAME} | {COLUMN_LIST} |

### 4.2 Foreign Keys

> Source: `tables.foreign_key_details` for complete FK info

| Table Name | Constraint Name | Column Name | Ref Table | Ref Column | On Update | On Delete |
|------------|-----------------|-------------|-----------|------------|-----------|-----------|
| {TABLE_NAME} | {CONSTRAINT_NAME} | {COLUMN_NAME} | {REFERENCED_TABLE_NAME} | {REFERENCED_COLUMN_NAME} | {UPDATE_RULE} | {DELETE_RULE} |

### 4.3 Unique Constraints

| Table Name | Constraint Name | Columns |
|------------|-----------------|---------|
| {TABLE_NAME} | {CONSTRAINT_NAME} | {COLUMN_LIST} |

### 4.4 Check Constraints

> Source: `tables.check_constraints` - Skip if empty (MySQL 8.0.16+)

| Table Name | Constraint Name | Check Clause | Enforced |
|------------|-----------------|--------------|----------|
| {TABLE_NAME} | {CONSTRAINT_NAME} | {CHECK_CLAUSE} | {ENFORCED} |

#### Constraint Columns

> Source: `tables.constraint_columns`

| Constraint Name | Table Name | Column Name | Position |
|-----------------|------------|-------------|----------|
| {CONSTRAINT_NAME} | {TABLE_NAME} | {COLUMN_NAME} | {ORDINAL_POSITION} |

---

## 5. Indexes

> Source: `indexes.indexes`

### 5.1 Index Summary

| Index Name | Table Name | Index Type | Unique | Nullable | Columns | Cardinality |
|------------|------------|------------|--------|----------|---------|-------------|
| {INDEX_NAME} | {TABLE_NAME} | {INDEX_TYPE} | {NON_UNIQUE} | {NULLABLE} | {COLUMN_LIST} | {CARDINALITY} |

### 5.2 Index Columns

> Source: `indexes.index_columns`

| Index Name | Table Name | Column Name | Position | Collation | Sub Part |
|------------|------------|-------------|----------|-----------|----------|
| {INDEX_NAME} | {TABLE_NAME} | {COLUMN_NAME} | {SEQ_IN_INDEX} | {COLLATION} | {SUB_PART} |

### 5.3 Fulltext Indexes

> Source: `indexes.fulltext_indexes` - Skip if empty

| Index Name | Table Name | Columns | Parser |
|------------|------------|---------|--------|
| {INDEX_NAME} | {TABLE_NAME} | {COLUMN_LIST} | {INDEX_COMMENT} |

### 5.4 Spatial Indexes

> Source: `indexes.spatial_indexes` - Skip if empty

| Index Name | Table Name | Column Name |
|------------|------------|-------------|
| {INDEX_NAME} | {TABLE_NAME} | {COLUMN_NAME} |

### 5.5 Expression-Based Indexes (Functional Indexes)

> Source: `indexes.expression_indexes` - Skip if empty (MySQL 8.0.13+)

| Index Name | Table Name | Expression | Position |
|------------|------------|------------|----------|
| {INDEX_NAME} | {TABLE_NAME} | {EXPRESSION} | {SEQ_IN_INDEX} |

---

## 6. Views

> Source: `views.views`

### 6.1 View Summary

| View Name | Updatable | Check Option | Security Type | Definer |
|-----------|-----------|--------------|---------------|---------|
| {TABLE_NAME} | {IS_UPDATABLE} | {CHECK_OPTION} | {SECURITY_TYPE} | {DEFINER} |

### 6.2 View Definitions

> Source: `views.view_source`

For each view, show the SQL:

```sql
-- View: {VIEW_NAME}
{VIEW_DEFINITION}
```

### 6.3 View Columns

> Source: `views.view_columns`

| View Name | Column Name | Data Type | Nullable | Position |
|-----------|-------------|-----------|----------|----------|
| {TABLE_NAME} | {COLUMN_NAME} | {DATA_TYPE} | {IS_NULLABLE} | {ORDINAL_POSITION} |

---

## 7. Stored Programs

> This section covers stored procedures, functions, triggers, and events.

### 7.1 Stored Procedures

> Source: `routines.procedures`

| Procedure Name | Deterministic | SQL Data Access | Security Type | Definer | Created |
|----------------|---------------|-----------------|---------------|---------|---------|
| {ROUTINE_NAME} | {IS_DETERMINISTIC} | {SQL_DATA_ACCESS} | {SECURITY_TYPE} | {DEFINER} | {CREATED} |

#### Procedure Parameters

> Source: `routines.procedure_parameters` - Group by SPECIFIC_NAME

| Procedure Name | Parameter Name | Position | Mode | Data Type |
|----------------|----------------|----------|------|-----------|
| {SPECIFIC_NAME} | {PARAMETER_NAME} | {ORDINAL_POSITION} | {PARAMETER_MODE} | {DATA_TYPE} |

### 7.2 Stored Functions

> Source: `routines.functions`

| Function Name | Return Type | Deterministic | SQL Data Access | Security Type | Definer |
|---------------|-------------|---------------|-----------------|---------------|---------|
| {ROUTINE_NAME} | {DATA_TYPE} | {IS_DETERMINISTIC} | {SQL_DATA_ACCESS} | {SECURITY_TYPE} | {DEFINER} |

#### Function Parameters

> Source: `routines.function_parameters` - Group by SPECIFIC_NAME

| Function Name | Parameter Name | Position | Data Type |
|---------------|----------------|----------|-----------|
| {SPECIFIC_NAME} | {PARAMETER_NAME} | {ORDINAL_POSITION} | {DATA_TYPE} |

### 7.3 Triggers

> Source: `routines.triggers`

| Trigger Name | Table Name | Event | Timing | Action Order | Definer |
|--------------|------------|-------|--------|--------------|---------|
| {TRIGGER_NAME} | {EVENT_OBJECT_TABLE} | {EVENT_MANIPULATION} | {ACTION_TIMING} | {ACTION_ORDER} | {DEFINER} |

#### Trigger Ordering

> Source: `routines.trigger_ordering` - Skip if empty (MySQL 5.7.2+)

| Trigger Name | Follows | Precedes |
|--------------|---------|----------|
| {TRIGGER_NAME} | {ACTION_REFERENCE_OLD_TABLE} | {ACTION_REFERENCE_NEW_TABLE} |

### 7.4 Events (Scheduled Tasks)

> Source: `routines.events` - Skip if empty

| Event Name | Type | Status | Execute At | Interval | Last Executed |
|------------|------|--------|------------|----------|---------------|
| {EVENT_NAME} | {EVENT_TYPE} | {STATUS} | {EXECUTE_AT} | {INTERVAL_VALUE} {INTERVAL_FIELD} | {LAST_EXECUTED} |

### 7.5 Routine Source Code

> Source: `routines.procedure_source` and `routines.function_source` - If INCLUDE_SOURCE=true

```sql
-- Procedure: {ROUTINE_NAME}
{ROUTINE_DEFINITION}
```

```sql
-- Function: {ROUTINE_NAME}
{ROUTINE_DEFINITION}
```

---

## 8. Security

### 8.1 Schema Privileges

> Source: `security.schema_privileges`

| Grantee | Privilege | Grantable |
|---------|-----------|-----------|
| {GRANTEE} | {PRIVILEGE_TYPE} | {IS_GRANTABLE} |

### 8.2 Table Privileges

> Source: `security.table_privileges`

| Table Name | Grantee | Privilege | Grantable |
|------------|---------|-----------|-----------|
| {TABLE_NAME} | {GRANTEE} | {PRIVILEGE_TYPE} | {IS_GRANTABLE} |

### 8.3 Column Privileges

> Source: `security.column_privileges` - Skip if empty

| Table Name | Column Name | Grantee | Privilege | Grantable |
|------------|-------------|---------|-----------|-----------|
| {TABLE_NAME} | {COLUMN_NAME} | {GRANTEE} | {PRIVILEGE_TYPE} | {IS_GRANTABLE} |

### 8.4 Routine Privileges

> Source: `security.routine_privileges` - Skip if empty

| Routine Name | Type | Grantee | Privilege | Grantable |
|--------------|------|---------|-----------|-----------|
| {ROUTINE_NAME} | {ROUTINE_TYPE} | {GRANTEE} | {PRIVILEGE_TYPE} | {IS_GRANTABLE} |

### 8.5 User Accounts

> Source: `security.users` - Skip if not collected

| User | Host | Account Locked | Password Expired |
|------|------|----------------|------------------|
| {USER} | {HOST} | {ACCOUNT_LOCKED} | {PASSWORD_EXPIRED} |

---

## 9. MySQL-Specific Features

### 9.1 Virtual Columns

> Source: `misc.virtual_columns` - Skip if empty

| Table Name | Column Name | Expression | Storage |
|------------|-------------|------------|---------|
| {TABLE_NAME} | {COLUMN_NAME} | {GENERATION_EXPRESSION} | {EXTRA} |

### 9.2 Foreign Key Constraints with CASCADE

> Source: `misc.cascade_fks` - Skip if empty

| Table Name | Constraint Name | On Update | On Delete |
|------------|-----------------|-----------|-----------|
| {TABLE_NAME} | {CONSTRAINT_NAME} | {UPDATE_RULE} | {DELETE_RULE} |

### 9.3 Storage Engine Details

| Engine | Tables | Total Data Size | Total Index Size |
|--------|--------|-----------------|------------------|
| {ENGINE} | {count} | {DATA_LENGTH} | {INDEX_LENGTH} |

### 9.4 Character Sets in Use

| Character Set | Default Collation | Tables Using |
|---------------|-------------------|--------------|
| {CHARACTER_SET_NAME} | {DEFAULT_COLLATE_NAME} | {count} |

### 9.5 Collations in Use

| Collation | Character Set | Tables Using |
|-----------|---------------|--------------|
| {COLLATION_NAME} | {CHARACTER_SET_NAME} | {count} |

### 9.6 Key Server Variables

> Source: `misc.server_variables`

| Variable | Value |
|----------|-------|
| version | {value} |
| character_set_server | {value} |
| collation_server | {value} |
| default_storage_engine | {value} |
| innodb_buffer_pool_size | {value} |
| max_connections | {value} |
| sql_mode | {value} |

---

## 10. Dependencies

### 10.1 Foreign Key Dependencies

> Source: `dependencies.fk_dependencies` - For migration ordering

| Table Name | Constraint Name | Ref Table | Ref Column |
|------------|-----------------|-----------|------------|
| {TABLE_NAME} | {CONSTRAINT_NAME} | {REFERENCED_TABLE_NAME} | {REFERENCED_COLUMN_NAME} |

### 10.2 View Dependencies

> Source: `dependencies.view_dependencies` - Tables used by views

| View Name | Depends On Table |
|-----------|------------------|
| {VIEW_NAME} | {TABLE_NAME} |

### 10.3 Trigger Dependencies

> Source: `dependencies.trigger_dependencies` - Tables with triggers

| Table Name | Trigger Name | Event | Timing |
|------------|--------------|-------|--------|
| {TABLE_NAME} | {TRIGGER_NAME} | {EVENT_MANIPULATION} | {ACTION_TIMING} |

### 10.4 Routine Dependencies

> Source: `dependencies.routine_dependencies` - If available

| Routine Name | Type | Depends On | Dependency Type |
|--------------|------|------------|-----------------|
| {ROUTINE_NAME} | {ROUTINE_TYPE} | {REFERENCED_NAME} | {DEPENDENCY_TYPE} |

### 10.5 Table Dependency Sequence (Migration Order)

> Source: `dependencies.migration_order` - Based on FK analysis

Tables should be migrated in this order based on foreign key dependency analysis:

1. {table_name_1} (no dependencies)
2. {table_name_2} (depends on: table_name_1)
3. ...

---

## 11. Statistics

### 11.1 Table Sizes

> Source: `statistics.table_sizes`

| Table Name | Rows | Avg Row Len | Data Size | Index Size | Total Size |
|------------|------|-------------|-----------|------------|------------|
| {TABLE_NAME} | {TABLE_ROWS} | {AVG_ROW_LENGTH} | {DATA_LENGTH} | {INDEX_LENGTH} | {TOTAL_SIZE} |

**Total Data Size**: {sum of DATA_LENGTH}
**Total Index Size**: {sum of INDEX_LENGTH}
**Total Size**: {sum of TOTAL_SIZE}

### 11.2 Index Statistics

> Source: `statistics.index_stats`

| Table Name | Index Name | Cardinality | Nullable | Avg Size |
|------------|------------|-------------|----------|----------|
| {TABLE_NAME} | {INDEX_NAME} | {CARDINALITY} | {NULLABLE} | {AVG_SIZE} |

---

## 12. All Objects Summary

> Source: `misc.all_objects`

| Object Name | Object Type | Created | Last Altered |
|-------------|-------------|---------|--------------|
| {OBJECT_NAME} | {OBJECT_TYPE} | {CREATED} | {LAST_ALTERED} |

---

## Appendix A: DDL Scripts

### A.1 Table DDL

> Source: `tables.table_ddl` - Dictionary of table_name -> DDL

For each table:

```sql
-- Table: {TABLE_NAME}
{DDL}
```

### A.2 View DDL

> Source: `views.view_ddl`

```sql
-- View: {VIEW_NAME}
CREATE VIEW {VIEW_NAME} AS
{VIEW_DEFINITION}
```

### A.3 Procedure DDL

> Source: `routines.procedure_ddl`

```sql
-- Procedure: {ROUTINE_NAME}
{DDL}
```

### A.4 Function DDL

> Source: `routines.function_ddl`

```sql
-- Function: {ROUTINE_NAME}
{DDL}
```

### A.5 Trigger DDL

> Source: `routines.trigger_ddl`

```sql
-- Trigger: {TRIGGER_NAME}
{DDL}
```

### A.6 Event DDL

> Source: `routines.event_ddl`

```sql
-- Event: {EVENT_NAME}
{DDL}
```

---

## Appendix B: Stored Routine Source Code

> Include only if INCLUDE_SOURCE=true

### B.1 Procedure Source

> Source: `routines.procedure_source` - Full source code

```sql
-- Procedure: {ROUTINE_NAME}
{ROUTINE_DEFINITION}
```

### B.2 Function Source

> Source: `routines.function_source` - Full source code

```sql
-- Function: {ROUTINE_NAME}
{ROUTINE_DEFINITION}
```

### B.3 Trigger Source

> Source: `routines.trigger_source` - Full action statements

```sql
-- Trigger: {TRIGGER_NAME}
{ACTION_STATEMENT}
```

### B.4 Event Source

> Source: `routines.event_source` - Full event definitions

```sql
-- Event: {EVENT_NAME}
{EVENT_DEFINITION}
```

---

## Report Generation Notes

**Instructions for Claude:**

1. Read `raw_mysql_schema_data.json` from the configured OUTPUT_DIR
2. For each section, check if the data exists and is non-empty
3. **Skip sections entirely** if no data exists - do not show empty tables
4. Replace field placeholders `{FIELD_NAME}` with actual values from JSON
5. Group data by relevant keys where indicated (e.g., columns by TABLE_NAME)
6. Format DDL code blocks properly with syntax highlighting
7. Calculate counts for the Executive Summary from actual data
8. Format sizes in human-readable format (KB, MB, GB)
9. Preserve data types (don't convert nulls to strings)

**JSON Structure Reference:**

```
{
  "metadata": { generated_at, database, mysql_version, server_info, hostname },
  "tables": { tables, columns, auto_increment_columns, generated_columns,
              partitioned_tables, partitions, constraints, foreign_key_details,
              check_constraints, constraint_columns, lob_columns, table_ddl },
  "indexes": { indexes, index_columns, fulltext_indexes, spatial_indexes,
               expression_indexes },
  "views": { views, view_source, view_columns, view_ddl },
  "routines": { procedures, functions, triggers, events,
                procedure_parameters, function_parameters,
                procedure_source, function_source, trigger_source, event_source,
                procedure_ddl, function_ddl, trigger_ddl, event_ddl },
  "security": { schema_privileges, table_privileges, column_privileges,
                routine_privileges, users },
  "misc": { json_columns, spatial_columns, enum_set_columns, virtual_columns,
            cascade_fks, server_variables, character_sets, collations,
            engines, all_objects },
  "dependencies": { fk_dependencies, view_dependencies, trigger_dependencies,
                    routine_dependencies, migration_order },
  "statistics": { table_sizes, index_stats }
}
```

---

*Report generated by MySQL Schema Analysis Skill*
*Source: {metadata.database}*
