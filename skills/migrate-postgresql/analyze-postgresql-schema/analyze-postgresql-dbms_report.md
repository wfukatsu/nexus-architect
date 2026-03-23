# PostgreSQL Database Schema Analysis Report

**Generated**: {metadata.generated_at}
**Schema**: {metadata.schema}
**Database**: {metadata.database_name}
**PostgreSQL Version**: {metadata.version}

---

## 1. Executive Summary

| Category | Count |
|----------|-------|
| Tables | {count of tables.tables} |
| Partitioned Tables | {count of tables.partitioned_tables} |
| Inherited Tables | {count of tables.inheritance} |
| Constraints | {count of tables.constraints} |
| Foreign Keys | {count of tables.foreign_keys} |
| Indexes | {count of indexes.indexes} |
| Partial Indexes | {count of indexes.partial_indexes} |
| Views | {count of views.views} |
| Materialized Views | {count of views.materialized_views} |
| ENUM Types | {count of types.enum_types} |
| Composite Types | {count of types.composite_types} |
| Domain Types | {count of types.domain_types} |
| Range Types | {count of types.range_types} |
| Functions | {count of plpgsql.functions} |
| Procedures | {count of plpgsql.procedures} |
| Triggers | {count of plpgsql.triggers} |
| Event Triggers | {count of plpgsql.event_triggers} |
| Sequences | {count of sequences.sequences} |
| Extensions | {count of extensions.extensions} |
| Foreign Tables | {count of misc.foreign_tables} |
| Foreign Servers | {count of misc.foreign_servers} |
| RLS Policies | {count of security.rls_policies} |
| Text Search Configs | {count of full_text_search.text_search_configs} |
| Invalid Objects | {count of dependencies.invalid_objects} |

---

## 2. Custom Types

> Skip this section if `types` is empty or not present.

### 2.1 ENUM Types

> Source: `types.enum_types`

| Type Name | Schema | Labels |
|-----------|--------|--------|
| {TYPE_NAME} | {SCHEMA_NAME} | {LABELS} |

### 2.2 Composite Types

> Source: `types.composite_types`

| Type Name | Schema | Definition |
|-----------|--------|------------|
| {TYPE_NAME} | {SCHEMA_NAME} | {TYPE_DEFINITION} |

#### Composite Type Attributes

> Source: `types.composite_type_attributes` - Group by TYPE_NAME

| Type Name | Attribute | Position | Data Type | Not Null |
|-----------|-----------|----------|-----------|----------|
| {TYPE_NAME} | {ATTRIBUTE_NAME} | {ATTRIBUTE_POSITION} | {ATTRIBUTE_TYPE} | {NOT_NULL} |

### 2.3 Domain Types

> Source: `types.domain_types`

| Type Name | Schema | Base Type | Not Null | Default | Check Clause |
|-----------|--------|-----------|----------|---------|--------------|
| {TYPE_NAME} | {SCHEMA_NAME} | {BASE_TYPE} | {NOT_NULL} | {DEFAULT_VALUE} | {CHECK_CONSTRAINT} |

### 2.4 Range Types

> Source: `types.range_types`

| Type Name | Schema | Subtype |
|-----------|--------|---------|
| {TYPE_NAME} | {SCHEMA_NAME} | {SUBTYPE} |

---

## 3. Special Column Types

> These sections document columns using PostgreSQL-specific data types.

### 3.1 Array Columns

> Source: `types.array_columns`

| Table Name | Column Name | Data Type | Element Type |
|------------|-------------|-----------|--------------|
| {TABLE_NAME} | {COLUMN_NAME} | {DATA_TYPE} | {ELEMENT_TYPE} |

### 3.2 JSON/JSONB Columns

> Source: `types.json_columns`

| Table Name | Column Name | Data Type |
|------------|-------------|-----------|
| {TABLE_NAME} | {COLUMN_NAME} | {DATA_TYPE} |

### 3.3 XML Columns

> Source: `types.xml_columns`

| Table Name | Column Name | Data Type |
|------------|-------------|-----------|
| {TABLE_NAME} | {COLUMN_NAME} | {DATA_TYPE} |

### 3.4 Geometric Columns

> Source: `types.geometric_columns`

| Table Name | Column Name | Data Type |
|------------|-------------|-----------|
| {TABLE_NAME} | {COLUMN_NAME} | {DATA_TYPE} |

### 3.5 Network Type Columns

> Source: `types.network_columns`

| Table Name | Column Name | Data Type |
|------------|-------------|-----------|
| {TABLE_NAME} | {COLUMN_NAME} | {DATA_TYPE} |

---

## 4. Tables

> Source: `tables.tables`

### 4.1 Table Summary

| Table Name | Schema | Owner | Est. Rows | Has Indexes | Has Triggers | Has RLS | Unlogged | Description |
|------------|--------|-------|-----------|-------------|--------------|---------|----------|-------------|
| {TABLE_NAME} | {SCHEMA_NAME} | {TABLE_OWNER} | {ROW_ESTIMATE} | {HAS_INDEXES} | {HAS_TRIGGERS} | {HAS_RLS} | {UNLOGGED} | {DESCRIPTION} |

### 4.2 Columns

> Source: `tables.columns` - Group by TABLE_NAME

| Table Name | Column Name | Position | Data Type | Nullable | Default | Identity | Generated | Description |
|------------|-------------|----------|-----------|----------|---------|----------|-----------|-------------|
| {TABLE_NAME} | {COLUMN_NAME} | {ORDINAL_POSITION} | {DATA_TYPE} | {NOT_NULL} | {COLUMN_DEFAULT} | {IDENTITY_GENERATION} | {IS_GENERATED} | {DESCRIPTION} |

### 4.3 Identity Columns

> Source: `tables.identity_columns` - Skip if empty

| Table Name | Column Name | Identity Type | Start | Increment | Min | Max | Cache | Cycle |
|------------|-------------|---------------|-------|-----------|-----|-----|-------|-------|
| {TABLE_NAME} | {COLUMN_NAME} | {IDENTITY_TYPE} | {START_VALUE} | {INCREMENT} | {MIN_VALUE} | {MAX_VALUE} | {CACHE} | {CYCLE} |

### 4.4 Serial Columns

> Source: `tables.serial_columns` - Skip if empty

| Table Name | Column Name | Sequence Name |
|------------|-------------|---------------|
| {TABLE_NAME} | {COLUMN_NAME} | {SEQUENCE_NAME} |

### 4.5 Generated Columns

> Source: `tables.generated_columns` - Skip if empty

| Table Name | Column Name | Generation Expression |
|------------|-------------|----------------------|
| {TABLE_NAME} | {COLUMN_NAME} | {GENERATION_EXPRESSION} |

### 4.6 Partitioned Tables

> Source: `tables.partitioned_tables` - Skip if empty

| Table Name | Partition Strategy | Partition Key | Partition Count |
|------------|-------------------|---------------|-----------------|
| {TABLE_NAME} | {PARTITION_STRATEGY} | {PARTITION_KEY} | {PARTITION_COUNT} |

#### Partitions

> Source: `tables.partitions`

| Parent Table | Partition Name | Partition Bound |
|--------------|----------------|-----------------|
| {PARENT_TABLE} | {PARTITION_NAME} | {PARTITION_EXPR} |

### 4.7 Table Inheritance

> Source: `tables.inheritance` - Skip if empty

| Parent Table | Child Table | Inheritance Order |
|--------------|-------------|-------------------|
| {PARENT_TABLE} | {CHILD_TABLE} | {INHERITANCE_ORDER} |

---

## 5. Constraints

> Source: `tables.constraints` - Group by CONSTRAINT_TYPE

### 5.1 Primary Keys

| Table Name | Constraint Name | Columns | Deferrable | Deferred | Validated |
|------------|-----------------|---------|------------|----------|-----------|
| {TABLE_NAME} | {CONSTRAINT_NAME} | {COLUMN_LIST} | {DEFERRABLE} | {DEFERRED} | {VALIDATED} |

### 5.2 Foreign Keys

> Source: `tables.foreign_keys`

| Table Name | Constraint Name | Column Name | Ref Table | Ref Column | On Update | On Delete | Deferrable |
|------------|-----------------|-------------|-----------|------------|-----------|-----------|------------|
| {TABLE_NAME} | {CONSTRAINT_NAME} | {COLUMN_NAME} | {REFERENCED_TABLE} | {REFERENCED_COLUMN} | {UPDATE_ACTION} | {DELETE_ACTION} | {DEFERRABLE} |

### 5.3 Unique Constraints

| Table Name | Constraint Name | Columns | Deferrable | Validated |
|------------|-----------------|---------|------------|-----------|
| {TABLE_NAME} | {CONSTRAINT_NAME} | {COLUMN_LIST} | {DEFERRABLE} | {VALIDATED} |

### 5.4 Check Constraints

> Source: `tables.check_constraints`

| Table Name | Constraint Name | Check Clause |
|------------|-----------------|--------------|
| {TABLE_NAME} | {CONSTRAINT_NAME} | {CHECK_CLAUSE} |

### 5.5 Exclusion Constraints

| Table Name | Constraint Name | Definition | Deferrable |
|------------|-----------------|------------|------------|
| {TABLE_NAME} | {CONSTRAINT_NAME} | {DEFINITION} | {DEFERRABLE} |

---

## 6. Indexes

> Source: `indexes.indexes`

### 6.1 Index Summary

| Index Name | Table Name | Index Type | Unique | Columns | Valid | Partial |
|------------|------------|------------|--------|---------|-------|---------|
| {INDEX_NAME} | {TABLE_NAME} | {INDEX_TYPE} | {IS_UNIQUE} | {COLUMNS} | {IS_VALID} | {IS_PARTIAL} |

### 6.2 Index Columns

> Source: `indexes.index_columns`

| Index Name | Table Name | Column Name | Position | Descending | Nulls First |
|------------|------------|-------------|----------|------------|-------------|
| {INDEX_NAME} | {TABLE_NAME} | {COLUMN_NAME} | {ORDINAL_POSITION} | {DESCENDING} | {NULLS_FIRST} |

### 6.3 Index Expressions

> Source: `indexes.index_expressions` - Skip if empty

| Index Name | Table Name | Expression | Position |
|------------|------------|------------|----------|
| {INDEX_NAME} | {TABLE_NAME} | {EXPRESSION} | {ORDINAL_POSITION} |

### 6.4 Partial Indexes

> Source: `indexes.partial_indexes` - Skip if empty

| Index Name | Table Name | Predicate |
|------------|------------|-----------|
| {INDEX_NAME} | {TABLE_NAME} | {PREDICATE} |

### 6.5 Unique Indexes

> Source: `indexes.unique_indexes`

| Index Name | Table Name | Columns |
|------------|------------|---------|
| {INDEX_NAME} | {TABLE_NAME} | {COLUMNS} |

---

## 7. Views

> Source: `views.views`

### 7.1 View Summary

| View Name | Schema | Owner | Updatable | Check Option | Description |
|-----------|--------|-------|-----------|--------------|-------------|
| {VIEW_NAME} | {SCHEMA_NAME} | {VIEW_OWNER} | {IS_UPDATABLE} | {CHECK_OPTION} | {DESCRIPTION} |

### 7.2 View Columns

> Source: `views.view_columns`

| View Name | Column Name | Position | Data Type | Nullable |
|-----------|-------------|----------|-----------|----------|
| {VIEW_NAME} | {COLUMN_NAME} | {ORDINAL_POSITION} | {DATA_TYPE} | {IS_NULLABLE} |

### 7.3 View Definitions

> Source: `views.view_definitions`

For each view, show the SQL:

```sql
-- View: {VIEW_NAME}
{VIEW_DEFINITION}
```

### 7.4 Materialized Views

> Source: `views.materialized_views` - Skip if empty

| View Name | Schema | Owner | Is Populated | Description |
|-----------|--------|-------|--------------|-------------|
| {MVIEW_NAME} | {SCHEMA_NAME} | {OWNER} | {IS_POPULATED} | {DESCRIPTION} |

#### Materialized View Indexes

> Source: `views.mview_indexes`

| View Name | Index Name | Index Type | Unique |
|-----------|------------|------------|--------|
| {MVIEW_NAME} | {INDEX_NAME} | {INDEX_TYPE} | {IS_UNIQUE} |

---

## 8. Stored Programs

### 8.1 Functions

> Source: `plpgsql.functions`

| Function Name | Schema | Return Type | Language | Deterministic | Security | Parallel |
|---------------|--------|-------------|----------|---------------|----------|----------|
| {FUNCTION_NAME} | {SCHEMA_NAME} | {RETURN_TYPE} | {LANGUAGE} | {VOLATILITY} | {SECURITY_TYPE} | {PARALLEL} |

### 8.2 Procedures

> Source: `plpgsql.procedures`

| Procedure Name | Schema | Language | Security |
|----------------|--------|----------|----------|
| {PROCEDURE_NAME} | {SCHEMA_NAME} | {LANGUAGE} | {SECURITY_TYPE} |

### 8.3 Parameters

> Source: `plpgsql.function_arguments` - Group by ROUTINE_NAME

| Routine Name | Parameter Name | Position | Mode | Data Type | Has Default |
|--------------|----------------|----------|------|-----------|-------------|
| {ROUTINE_NAME} | {PARAMETER_NAME} | {ORDINAL_POSITION} | {PARAMETER_MODE} | {DATA_TYPE} | {PARAMETER_DEFAULT} |

### 8.4 Triggers

> Source: `plpgsql.triggers`

| Trigger Name | Table Name | Timing | Event | Level | Function | Enabled |
|--------------|------------|--------|-------|-------|----------|---------|
| {TRIGGER_NAME} | {TABLE_NAME} | {ACTION_TIMING} | {EVENT_MANIPULATION} | {ACTION_ORIENTATION} | {ACTION_STATEMENT} | {IS_ENABLED} |

### 8.5 Trigger Functions

> Source: `plpgsql.trigger_functions`

| Function Name | Return Type | Language |
|---------------|-------------|----------|
| {FUNCTION_NAME} | trigger | {LANGUAGE} |

### 8.6 Event Triggers

> Source: `plpgsql.event_triggers` - Skip if empty

| Trigger Name | Event | Function | Enabled | Tags |
|--------------|-------|----------|---------|------|
| {EVENT_TRIGGER_NAME} | {EVENT_NAME} | {FUNCTION_NAME} | {ENABLED} | {TAGS} |

### 8.7 Aggregates

> Source: `plpgsql.aggregates` - Skip if empty

| Aggregate Name | Schema | Argument Types | State Type |
|----------------|--------|----------------|------------|
| {AGGREGATE_NAME} | {SCHEMA_NAME} | {ARG_TYPES} | {STATE_TYPE} |

### 8.8 Operators

> Source: `plpgsql.operators` - Skip if empty

| Operator Name | Schema | Left Arg | Right Arg | Result | Procedure |
|---------------|--------|----------|-----------|--------|-----------|
| {OPERATOR_NAME} | {SCHEMA_NAME} | {LEFT_TYPE} | {RIGHT_TYPE} | {RESULT_TYPE} | {PROCEDURE} |

### 8.9 Function/Procedure Source

> Source: `plpgsql.function_source` - Include if INCLUDE_PLPGSQL_SOURCE=true

```sql
-- Function: {ROUTINE_NAME}
{ROUTINE_DEFINITION}
```

---

## 9. Sequences

> Source: `sequences.sequences`

| Sequence Name | Schema | Data Type | Start | Increment | Min | Max | Cache | Cycle | Owner |
|---------------|--------|-----------|-------|-----------|-----|-----|-------|-------|-------|
| {SEQUENCE_NAME} | {SCHEMA_NAME} | {DATA_TYPE} | {START_VALUE} | {INCREMENT} | {MINIMUM_VALUE} | {MAXIMUM_VALUE} | {CACHE_SIZE} | {CYCLE_OPTION} | {OWNER_TABLE}.{OWNER_COLUMN} |

### 9.1 Sequence Usage

> Source: `sequences.sequence_usage` - Which columns use which sequences

| Sequence Name | Table Name | Column Name |
|---------------|------------|-------------|
| {SEQUENCE_NAME} | {TABLE_NAME} | {COLUMN_NAME} |

---

## 10. Extensions

> Source: `extensions.extensions`

| Extension Name | Version | Schema | Relocatable | Description |
|----------------|---------|--------|-------------|-------------|
| {EXTENSION_NAME} | {VERSION} | {SCHEMA_NAME} | {RELOCATABLE} | {DESCRIPTION} |

### 10.1 Extension Objects

> Source: `extensions.extension_objects` - Skip if empty

| Extension Name | Object Name | Object Type |
|----------------|-------------|-------------|
| {EXTENSION_NAME} | {OBJECT_NAME} | {OBJECT_TYPE} |

---

## 11. Security

### 11.1 Table Privileges

> Source: `security.table_privileges`

| Table Name | Grantee | Privilege | Is Grantable | Grantor |
|------------|---------|-----------|--------------|---------|
| {TABLE_NAME} | {GRANTEE} | {PRIVILEGE_TYPE} | {IS_GRANTABLE} | {GRANTOR} |

### 11.2 Column Privileges

> Source: `security.column_privileges` - Skip if empty

| Table Name | Column Name | Grantee | Privilege | Is Grantable |
|------------|-------------|---------|-----------|--------------|
| {TABLE_NAME} | {COLUMN_NAME} | {GRANTEE} | {PRIVILEGE_TYPE} | {IS_GRANTABLE} |

### 11.3 Row Level Security Policies

> Source: `security.rls_policies` - Skip if empty

| Table Name | Policy Name | Permissive | Roles | Command | Using Expression | With Check |
|------------|-------------|------------|-------|---------|------------------|------------|
| {TABLE_NAME} | {POLICY_NAME} | {PERMISSIVE} | {ROLES} | {COMMAND} | {USING_EXPRESSION} | {WITH_CHECK_EXPRESSION} |

### 11.4 Roles

> Source: `security.roles`

| Role Name | Superuser | Inherit | Create Role | Create DB | Can Login | Replication | Connection Limit |
|-----------|-----------|---------|-------------|-----------|-----------|-------------|------------------|
| {ROLE_NAME} | {IS_SUPERUSER} | {INHERIT} | {CAN_CREATE_ROLE} | {CAN_CREATE_DB} | {CAN_LOGIN} | {REPLICATION} | {CONNECTION_LIMIT} |

---

## 12. Foreign Data Wrappers

### 12.1 Foreign Servers

> Source: `misc.foreign_servers` - Skip if empty

| Server Name | Foreign Data Wrapper | Owner | Options |
|-------------|---------------------|-------|---------|
| {SERVER_NAME} | {FOREIGN_DATA_WRAPPER} | {OWNER} | {OPTIONS} |

### 12.2 Foreign Tables

> Source: `misc.foreign_tables` - Skip if empty

| Table Name | Schema | Server Name | Options |
|------------|--------|-------------|---------|
| {TABLE_NAME} | {SCHEMA_NAME} | {SERVER_NAME} | {OPTIONS} |

---

## 13. Full-Text Search

### 13.1 Text Search Configurations

> Source: `full_text_search.text_search_configs` - Skip if empty

| Config Name | Schema | Owner | Parser | Description |
|-------------|--------|-------|--------|-------------|
| {CONFIG_NAME} | {SCHEMA_NAME} | {OWNER} | {PARSER_NAME} | {DESCRIPTION} |

### 13.2 TSVECTOR Columns

> Source: `full_text_search.tsvector_columns` - Skip if empty

| Table Name | Column Name | Data Type |
|------------|-------------|-----------|
| {TABLE_NAME} | {COLUMN_NAME} | {DATA_TYPE} |

---

## 14. Replication

### 14.1 Publications

> Source: `misc.publications` - Skip if empty

| Publication Name | Owner | All Tables | Insert | Update | Delete | Truncate |
|------------------|-------|------------|--------|--------|--------|----------|
| {PUBLICATION_NAME} | {OWNER} | {ALL_TABLES} | {PUBINSERT} | {PUBUPDATE} | {PUBDELETE} | {PUBTRUNCATE} |

### 14.2 Subscriptions

> Source: `misc.subscriptions` - Skip if empty

| Subscription Name | Owner | Enabled | Connection | Publications |
|-------------------|-------|---------|------------|--------------|
| {SUBSCRIPTION_NAME} | {OWNER} | {ENABLED} | {CONNECTION} | {PUBLICATIONS} |

---

## 15. Rules

> Source: `misc.rules` - Skip if empty

| Rule Name | Table Name | Event | Instead | Definition |
|-----------|------------|-------|---------|------------|
| {RULE_NAME} | {TABLE_NAME} | {EVENT} | {IS_INSTEAD} | {DEFINITION} |

---

## 16. Dependencies

### 16.1 Object Dependencies

> Source: `dependencies.dependencies` - Show key dependencies

| Dependent Object | Dependent Type | Referenced Object | Ref Type | Dependency Type |
|------------------|----------------|-------------------|----------|-----------------|
| {DEPENDENT_OBJECT} | {DEPENDENT_CLASS} | {REFERENCED_OBJECT} | {REFERENCED_CLASS} | {DEPENDENCY_TYPE} |

### 16.2 Invalid Objects

> Source: `dependencies.invalid_objects` - Skip if empty

| Object Name | Object Type | Status |
|-------------|-------------|--------|
| {OBJECT_NAME} | {OBJECT_TYPE} | {STATUS} |

### 16.3 Foreign Key Dependencies

> Source: `dependencies.fk_dependencies`

| Table Name | Constraint Name | Ref Table |
|------------|-----------------|-----------|
| {TABLE_NAME} | {CONSTRAINT_NAME} | {REFERENCED_TABLE} |

### 16.4 Table Dependency Sequence (Migration Order)

> Source: `dependencies.migration_order` - List in order

Tables should be migrated in this order based on foreign key dependency analysis:


1. {object_name_1}
2. {object_name_2}
3. ...

---

## 17. Schemas

> Source: `misc.schemas`

| Schema Name | Owner | Description |
|-------------|-------|-------------|
| {SCHEMA_NAME} | {OWNER} | {DESCRIPTION} |

---

## Appendix A: DDL Scripts

### A.1 Table DDL

> Source: `tables.table_ddl` - Dictionary of table_name -> DDL

For each table:

```sql
-- Table: {TABLE_NAME}
{DDL}
```

### A.2 Function Source Code

> Source: `plpgsql.function_source` - Include if INCLUDE_PLPGSQL_SOURCE=true

```sql
-- Function: {FUNCTION_NAME}
{SOURCE_CODE}
```

### A.3 Trigger Source Code

> Source: `plpgsql.trigger_source`

```sql
-- Trigger: {TRIGGER_NAME}
{TRIGGER_BODY}
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
9. **Do NOT add migration commentary** - this is purely extraction/documentation

**JSON Structure Reference:**

```
{
  "metadata": { generated_at, schema, database_name, database_type, version },
  "types": { enum_types, composite_types, composite_type_attributes, domain_types, range_types, array_columns, json_columns, xml_columns, geometric_columns, network_columns },
  "tables": { tables, columns, identity_columns, serial_columns, generated_columns, partitioned_tables, partitions, inheritance, constraints, check_constraints, foreign_keys, table_ddl },
  "indexes": { indexes, index_columns, index_expressions, partial_indexes, unique_indexes },
  "views": { views, view_columns, view_definitions, materialized_views, mview_indexes },
  "plpgsql": { functions, procedures, function_arguments, function_source, triggers, trigger_functions, event_triggers, aggregates, operators },
  "sequences": { sequences, sequence_usage },
  "security": { table_privileges, column_privileges, rls_policies, roles },
  "extensions": { extensions, extension_objects },
  "misc": { schemas, foreign_tables, foreign_servers, publications, subscriptions, rules },
  "full_text_search": { text_search_configs, tsvector_columns },
  "dependencies": { dependencies, invalid_objects, fk_dependencies, migration_order }
}
```
