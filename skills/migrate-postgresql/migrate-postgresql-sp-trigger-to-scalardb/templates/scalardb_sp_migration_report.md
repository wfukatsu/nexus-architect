# PostgreSQL Stored Procedure Migration Report

**Generated**: {{TIMESTAMP}}
**Source Database**: {{DATABASE_NAME}}
**Source Schema**: {{SCHEMA_NAME}}
**Target**: ScalarDB 3.17+ Application Layer (Java)

---

## 1. Executive Summary

### Migration Scope

| Object Type | Count | Low Complexity | Medium Complexity | High Complexity |
|-------------|-------|----------------|-------------------|-----------------|
| Functions | {{FUNC_COUNT}} | {{FUNC_LOW}} | {{FUNC_MED}} | {{FUNC_HIGH}} |
| Procedures | {{PROC_COUNT}} | {{PROC_LOW}} | {{PROC_MED}} | {{PROC_HIGH}} |
| Trigger Functions | {{TRGFUNC_COUNT}} | {{TRGFUNC_LOW}} | {{TRGFUNC_MED}} | {{TRGFUNC_HIGH}} |
| Triggers | {{TRIGGER_COUNT}} | {{TRIGGER_LOW}} | {{TRIGGER_MED}} | {{TRIGGER_HIGH}} |
| **Total** | **{{TOTAL_COUNT}}** | **{{TOTAL_LOW}}** | **{{TOTAL_MED}}** | **{{TOTAL_HIGH}}** |

### SP Type Distribution

| SP Type | Count | Description |
|---------|-------|-------------|
| Simple CRUD | {{CRUD_COUNT}} | Direct INSERT/UPDATE/DELETE on one table |
| Business Logic | {{BIZ_COUNT}} | Arithmetic, conditionals, validation |
| Multi-table Transaction | {{MULTI_COUNT}} | Writes across multiple tables |
| Cursor / Batch | {{CURSOR_COUNT}} | Loop through result sets |
| Aggregation | {{AGG_COUNT}} | SUM/COUNT/AVG operations |
| Subquery-based | {{SUB_COUNT}} | Nested SELECT operations |

### Overall Assessment

- **Total PL/pgSQL Objects**: {{TOTAL_COUNT}}
- **Java Files Generated**: {{FILES_GENERATED}}
- **Output Directory**: `{{OUTPUT_DIR}}/generated-java/`
- **Overall Complexity**: {{OVERALL_COMPLEXITY}}
- **Approach**: ScalarDB Java Transaction API

---

## 2. Per-Object Migration Details

### Functions

| # | Function Name | Return Type | SP Type | Features Used | Complexity | Generated File |
|---|--------------|-------------|---------|---------------|------------|----------------|
| {{N}} | {{FUNC_NAME}} | {{RETURN_TYPE}} | {{SP_TYPE}} | {{FEATURES}} | {{COMPLEXITY}} | `{{FILENAME}}` |

### Procedures

| # | Procedure Name | SP Type | Features Used | Complexity | Generated File |
|---|---------------|---------|---------------|------------|----------------|
| {{N}} | {{PROC_NAME}} | {{SP_TYPE}} | {{FEATURES}} | {{COMPLEXITY}} | `{{FILENAME}}` |

### Trigger Functions

| # | Function Name | Associated Triggers | SP Type | Features Used | Complexity | Generated File |
|---|--------------|-------------------|---------|---------------|------------|----------------|
| {{N}} | {{TRGFUNC_NAME}} | {{TRIGGERS}} | {{SP_TYPE}} | {{FEATURES}} | {{COMPLEXITY}} | `{{FILENAME}}` |

### Triggers

| # | Trigger Name | Table | Type | Event | Trigger Function | Complexity | Generated File |
|---|-------------|-------|------|-------|-----------------|------------|----------------|
| {{N}} | {{TRIGGER_NAME}} | {{TABLE}} | {{TRIGGER_TYPE}} | {{EVENT}} | {{TRGFUNC}} | {{COMPLEXITY}} | `{{FILENAME}}` |

---

## 3. Feature Usage Matrix

Shows which of the 17 feature categories each PL/pgSQL object uses:

| Object Name | 1-Var | 2-Cur | 3-Flow | 4-Exc | 5-Old/New | 6-CRUD | 7-Cond | 8-Sub | 9-JOIN | 10-Agg | 11-Func | 12-Seq | 13-Tmp | 14-Dyn | 15-Out | 16-Tx | 17-Bat |
|-------------|-------|-------|--------|-------|-----------|--------|--------|-------|--------|--------|---------|--------|--------|--------|--------|-------|--------|
| {{NAME}} | {{Y/N}} | {{Y/N}} | {{Y/N}} | {{Y/N}} | {{Y/N}} | {{Y/N}} | {{Y/N}} | {{Y/N}} | {{Y/N}} | {{Y/N}} | {{Y/N}} | {{Y/N}} | {{Y/N}} | {{Y/N}} | {{Y/N}} | {{Y/N}} | {{Y/N}} |

### Feature Legend

| # | Feature | ScalarDB Pattern |
|---|---------|-----------------|
| 1 | Variables (DECLARE/SET/INTO) | Java variables + `tx.get()` |
| 2 | Cursors (DECLARE CURSOR/FOR loop) | `tx.scan()` + iteration |
| 3 | Control flow (IF/WHILE/CASE) | Plain Java |
| 4 | Exception handling (EXCEPTION WHEN) | ScalarDB exception types |
| 5 | OLD/NEW row access (triggers) | `tx.get()` = OLD, params = NEW |
| 6 | CRUD operations | Get/Scan/Insert/Update/Delete |
| 7 | Conditional writes | `ConditionBuilder` |
| 8 | Subqueries | Sequential scan + filter |
| 9 | JOINs | Multiple Get/Scan + merge |
| 10 | Aggregations | Scan + Java stream |
| 11 | SQL functions | Java equivalents |
| 12 | Sequences/SERIAL | UUID or counter table |
| 13 | Temp tables | Java collections |
| 14 | Dynamic SQL (EXECUTE) | Builder pattern |
| 15 | Output params/RETURN | Java return values |
| 16 | Transaction control | `tx.begin()`/`commit()`/`rollback()` |
| 17 | Batch operations | `tx.mutate(List)` |

---

## 4. Unsupported Features & Workarounds

### Features Requiring Special Attention

| Feature | Objects Affected | Workaround |
|---------|-----------------|------------|
| {{FEATURE}} | {{OBJECTS}} | {{WORKAROUND}} |

### SAVEPOINTs

{{#IF_SAVEPOINTS}}
The following objects use SAVEPOINTs, which ScalarDB does not support:
| Object | Workaround Strategy |
|--------|-------------------|
| {{NAME}} | {{STRATEGY}} |
{{/IF_SAVEPOINTS}}

### PostgreSQL-Specific Constructs

| Construct | Objects Using It | ScalarDB Equivalent |
|-----------|-----------------|-------------------|
| {{CONSTRUCT}} | {{OBJECTS}} | {{EQUIVALENT}} |

---

## 5. Generated File Index

### Java Source Files

| # | File | Source Object | Type | Lines |
|---|------|--------------|------|-------|
| {{N}} | `generated-java/{{FILENAME}}` | {{SOURCE_OBJECT}} | {{TYPE}} | {{LINES}} |

### Output Summary

```
{{OUTPUT_DIR}}/
├── scalardb_sp_migration_report.md     # This report
└── generated-java/
    ├── {{FILE_1}}
    ├── {{FILE_2}}
    └── ...
```

---

## 6. Migration Recommendations

### Implementation Order

Recommended order for implementing and testing the migrated code:

1. {{RECOMMENDATION_1}}
2. {{RECOMMENDATION_2}}
3. {{RECOMMENDATION_3}}

### Testing Strategy

- [ ] Unit test each service class independently
- [ ] Verify Transaction API implementations produce expected results
- [ ] Test exception handling paths (conflict, unsatisfied condition, unknown state)
- [ ] Load test cursor/batch operations for transaction timeout limits
- [ ] Validate data type precision (especially numeric → DOUBLE conversions)

### Dependencies

```xml
<!-- ScalarDB Transaction API -->
<dependency>
    <groupId>com.scalar-labs</groupId>
    <artifactId>scalardb</artifactId>
    <version>3.17.0</version>
</dependency>
```

---

*Report generated by ScalarDB SP & Trigger Migration Skill*
*Input consumed from: {{RAW_SCHEMA_DATA_PATH}}*
