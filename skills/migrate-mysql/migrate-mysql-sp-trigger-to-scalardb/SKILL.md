---
name: migrate-mysql-sp-trigger-to-scalardb
description: Generates ScalarDB Java application code from MySQL stored procedures, functions, and triggers. Produces Java Transaction API implementations plus a summary migration report.
---

# Migrate MySQL Stored Procedures & Triggers to ScalarDB Skill

## Purpose

Generate equivalent **ScalarDB Java application code** from MySQL stored procedures, functions, and triggers. Since ScalarDB does not support stored procedures or triggers, all database-side logic must be converted to application-layer Java service classes.

This skill produces **one implementation per object** using the ScalarDB Java Transaction API (Get/Scan/Insert/Update/Delete builders).

---

## Skill Responsibility

This skill is responsible for:
- Reading and parsing routine definitions from extracted schema JSON
- Classifying each object by type and feature categories used
- Generating Java service classes with ScalarDB Java Transaction API implementations
- Producing a summary migration report indexing all generated files

This skill is **NOT** responsible for:
- Orchestration or command handling (handled by `/mysql-to-scalardb` command)
- Schema extraction (handled by Subagent 1)
- Schema report generation (handled by Subagent 2)
- General migration analysis (handled by Subagent 3)

---

## Input Contract

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `raw_mysql_schema_data.json` | File | YES | Extracted MySQL schema data (specifically the `routines` section) |
| `mysql_schema_report.md` | File | YES | Schema report (for table/column context needed for accurate Key builders) |
| `migration-strategy-guide-sp-triggers-to-scalardb.md` | File | YES | Reference doc with 17 feature mappings and code examples |
| `output_directory` | Directory | YES | Where to write generated files |

---

## Output Contract

| Output | Location | Description |
|--------|----------|-------------|
| Java Service Classes | `<OUTPUT_DIR>/generated-java/<ObjectName>Service.java` | One file per procedure/function/trigger |
| Summary Report | `<OUTPUT_DIR>/scalardb_mysql_sp_migration_report.md` | Index of all generated files with analysis |

---

## How to Parse the JSON

Read `raw_mysql_schema_data.json` and extract these sections from `routines`:

| JSON Path | Contains |
|-----------|----------|
| `routines.procedures` | Procedure metadata (name, definer, security_type, sql_data_access) |
| `routines.functions` | Function metadata (name, return_type, definer, is_deterministic) |
| `routines.triggers` | Trigger metadata (name, table, timing, event, action_statement) |
| `routines.parameters` | Parameters for procedures/functions (name, data_type, mode) |
| `routines.procedure_source` | Procedure source code (dict keyed by procedure name) |
| `routines.function_source` | Function source code (dict keyed by function name) |

Note: Trigger source code is typically embedded in the `triggers[].ACTION_STATEMENT` field.

Also read `mysql_schema_report.md` to extract:
- Table names and their columns with data types
- Primary key definitions (needed to build correct `Key.of*()` calls)
- Foreign key relationships (needed for multi-table operations)

---

## Stored Procedure Type Classification

Classify each stored procedure/function into one of these 6 categories:

| # | Type | Indicators | Complexity |
|---|------|-----------|------------|
| 1 | Simple CRUD | Single INSERT/UPDATE/DELETE, no control flow | Low |
| 2 | Business Logic | Arithmetic, conditionals, validation rules | Medium |
| 3 | Multi-table Transaction | Writes to 2+ tables, FK relationships | Medium-High |
| 4 | Cursor / Batch Processing | CURSOR, FETCH, WHILE loops over result sets | High |
| 5 | Aggregation | SUM, COUNT, AVG, GROUP BY | Medium |
| 6 | Subquery-based | Nested SELECT, IN (SELECT ...), EXISTS | High |

---

## Trigger Type Mapping

Map each MySQL trigger to its application-layer equivalent pattern:

| # | Trigger Type | Application-Layer Pattern |
|---|-------------|---------------------------|
| 1 | BEFORE INSERT | Validation + defaults in the insert service method, before `tx.insert()` |
| 2 | AFTER INSERT | Additional writes (audit, counters) in the same transaction after `tx.insert()` |
| 3 | BEFORE UPDATE | Validate OLD→NEW transitions using `tx.get()` before `tx.update()` |
| 4 | AFTER UPDATE | Audit trail / side effects in same transaction after `tx.update()` |
| 5 | BEFORE DELETE | Dependency checks / archival using `tx.get()` before `tx.delete()` |
| 6 | AFTER DELETE | Cascade deletes / audit in same transaction after `tx.delete()` |

**Note:** MySQL does not support INSTEAD OF triggers or asynchronous triggers. All MySQL triggers are row-level.

---

## The 17 Feature Categories

When analyzing each MySQL routine, identify which of these feature categories it uses. Each category maps to specific ScalarDB API patterns (detailed in `migration-strategy-guide-sp-triggers-to-scalardb.md`):

| # | Feature | ScalarDB API Pattern |
|---|---------|---------------------|
| 1 | Variables (DECLARE/SET/INTO) | Java variables + `tx.get()` → `result.getText()` |
| 2 | Cursors | `tx.scan()` + for loop, or `tx.getScanner()` for lazy |
| 3 | Control flow (IF/WHILE/CASE) | Plain Java — no API needed |
| 4 | Exception handling | ScalarDB exception types (`CrudConflictException`, etc.) |
| 5 | OLD/NEW row access | `tx.get()` = OLD, method params = NEW |
| 6 | CRUD operations | Get / Scan / Insert / Upsert / Update / Delete |
| 7 | Conditional writes | `ConditionBuilder.updateIf()` / `deleteIf()` |
| 8 | Subqueries | Sequential `tx.scan()` + Java Set/filter |
| 9 | JOINs | Multiple `tx.get()` / `tx.scan()` + Java merge |
| 10 | Aggregations | `tx.scan()` + Java stream (sum, collect, groupingBy) |
| 11 | SQL functions | Java equivalents (UUID, Instant, Math, String) |
| 12 | Sequences/AUTO_INCREMENT | `UUID.randomUUID()` or counter table pattern |
| 13 | Temp tables | Java List / Map / Set |
| 14 | Dynamic SQL | Builder pattern — already dynamic |
| 15 | Output params / RETURN | Java return values and result objects |
| 16 | Transactions in SP | `tx.begin()` / `tx.commit()` / `tx.rollback()` |
| 17 | Batch operations | `tx.mutate(List)` |

---

## Java Code Generation Rules

### Target Java Version: 17

All generated Java files MUST target **Java 17**. Use these Java 17 language features where appropriate:

| Feature | When to Use |
|---------|------------|
| `var` | Local variable type inference for verbose generic types (e.g., `var result = tx.get(get)`) |
| Records | Lightweight result/value objects (e.g., `record OrderKey(int orderId) {}`) |
| `instanceof` pattern matching | Replace `instanceof` + cast pairs (e.g., `if (obj instanceof String s) { ... }`) |
| Switch expressions | Replace multi-branch `if/else` or `switch` statements returning a value |
| Text blocks (`"""..."""`) | Multi-line SQL-like strings or error messages |
| `List.of()` / `Map.of()` | Immutable collection literals (prefer over `Arrays.asList`) |
| `String.formatted()` | Inline string formatting (prefer over `String.format()`) |
| Sealed interfaces | Model closed hierarchies of result types (optional, for complex SPs) |

**Do NOT use** preview features or anything requiring Java 21+.

### File Naming

- **Procedures**: `<ProcedureName>Service.java` (PascalCase)
  - Example: `calculate_order_total` → `CalculateOrderTotalService.java`
- **Functions**: `<FunctionName>Service.java` (PascalCase)
  - Example: `get_discount_rate` → `GetDiscountRateService.java`
- **Triggers**: `<TriggerName>Service.java` (PascalCase)
  - Example: `trg_audit_log` → `TrgAuditLogService.java`

### Class Structure

Each generated `.java` file MUST contain:

```java
package com.example.scalardb.migration;

import com.scalar.db.api.*;
import com.scalar.db.io.Key;
import com.scalar.db.exception.transaction.*;
import java.util.*;
import java.util.stream.*;

/**
 * Migrated from MySQL: <OBJECT_TYPE> <OBJECT_NAME>
 * Original features used: <comma-separated feature categories>
 * SP Type: <classification from 6 types>
 * Complexity: <Low/Medium/Medium-High/High>
 *
 * Java version: 17
 * Generated by ScalarDB SP & Trigger Migration Skill
 */
public class <ObjectName>Service {

    private static final String NAMESPACE = "<database_lowercase>";

    /**
     * ScalarDB Java Transaction API implementation of <OBJECT_NAME>
     * Uses ScalarDB Get/Scan/Insert/Update/Delete builders.
     */
    public <ReturnType> <methodName>(DistributedTransaction tx, <params>)
            throws TransactionException {
        // Transaction API implementation here — use Java 17 features (var, records, switch expressions, etc.)
    }
}
```

### Key Building Rules

Use the schema report to determine correct key types:

| MySQL Type | Key Builder |
|------------|------------|
| INT | `Key.ofInt("col", value)` |
| BIGINT | `Key.ofBigInt("col", value)` |
| DECIMAL, DOUBLE, FLOAT | `Key.ofDouble("col", value)` |
| VARCHAR, CHAR, TEXT | `Key.ofText("col", value)` |
| TINYINT(1) boolean | `Key.ofBoolean("col", value)` |

### Error Handling Pattern

Every generated method MUST include proper ScalarDB exception handling:

```java
try {
    // ... operation logic ...
} catch (UnsatisfiedConditionException e) {
    // Conditional write failed
} catch (CrudConflictException e) {
    // Transaction conflict — caller should retry
    throw e;
} catch (CommitConflictException e) {
    // Commit conflict — caller should retry
    throw e;
} catch (UnknownTransactionStatusException e) {
    // Unknown state — do NOT retry blindly
    throw e;
}
```

### Namespace Handling

- Use the `MYSQL_DATABASE` value (lowercase) as the ScalarDB namespace
- Set as a class constant: `private static final String NAMESPACE = "<value>";`

---

## Complexity Assessment

For each MySQL routine, calculate complexity based on:

| Factor | Low | Medium | High |
|--------|-----|--------|------|
| Lines of code | <50 | 50-200 | >200 |
| Tables touched | 1 | 2-3 | 4+ |
| Feature categories used | 1-3 | 4-7 | 8+ |
| Has cursors | No | Simple | Nested/complex |
| Has subqueries | No | Simple IN | Correlated |
| Has dynamic SQL | No | — | Yes |
| Transaction control | None/simple | Multi-table | Savepoints |

**Overall complexity:**
- **Low**: Simple CRUD, few features, 1 table
- **Medium**: Business logic, moderate features, 2-3 tables
- **Medium-High**: Multi-table transactions, cursors
- **High**: Cursor/batch + subqueries + dynamic SQL + complex exception handling

---

## Report Generation

After generating all Java files, produce `scalardb_mysql_sp_migration_report.md` using the template. The report includes:

1. **Executive Summary** — counts of procedures/functions/triggers, complexity breakdown
2. **Per-Object Table** — object name, type, classification, features used, complexity, generated file
3. **Feature Usage Matrix** — which of the 17 categories each routine uses
4. **Unsupported Features / Workarounds** — anything requiring special attention
5. **Generated File Index** — list of all `.java` files with descriptions

---

## Files in This Skill

```
skills/migrate-mysql-sp-trigger-to-scalardb/
├── SKILL.md                              # This file
├── reference/
│   └── migration-strategy-guide-sp-triggers-to-scalardb.md       # 17 feature mappings with code examples
└── templates/
    └── scalardb_sp_migration_report.md   # Report template
```

---

## Related

- **Command**: `commands/mysql-to-scalardb.md` (orchestration — Step 11)
- **Schema Extraction**: `skills/analyze-mysql-schema/` (provides raw_mysql_schema_data.json)
- **Schema Report**: `skills/analyze-mysql-schema/` (provides mysql_schema_report.md)
- **Migration Analysis**: `skills/migrate-mysql-to-scalardb/` (general migration docs)

---

*Skill Version: 1.1*
*Compatible with: ScalarDB 3.17+*
*Target Java Version: 17*
