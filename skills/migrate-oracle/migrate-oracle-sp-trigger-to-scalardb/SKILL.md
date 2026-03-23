---
name: migrate-oracle-sp-trigger-to-scalardb
description: Generates ScalarDB Java application code from Oracle PL/SQL stored procedures, functions, packages, and triggers. Produces Java Transaction API implementations plus a summary migration report.
---

# Migrate Oracle Stored Procedures & Triggers to ScalarDB Skill

## Purpose

Generate equivalent **ScalarDB Java application code** from Oracle PL/SQL stored procedures, functions, packages, and triggers. Since ScalarDB does not support stored procedures or triggers, all database-side logic must be converted to application-layer Java service classes.

This skill produces **one implementation per object** using the ScalarDB Java Transaction API (Get/Scan/Insert/Update/Delete builders).

---

## Skill Responsibility

This skill is responsible for:
- Reading and parsing PL/SQL definitions from extracted schema JSON
- Classifying each object by type and feature categories used
- Generating Java service classes with ScalarDB Java Transaction API implementations
- Producing a summary migration report indexing all generated files

This skill is **NOT** responsible for:
- Orchestration or command handling (handled by `/oracle-to-scalardb` command)
- Schema extraction (handled by Subagent 1)
- Schema report generation (handled by Subagent 2)
- General migration analysis (handled by Subagent 3)

---

## Input Contract

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `raw_schema_data.json` | File | YES | Extracted Oracle schema data (specifically the `plsql` section) |
| `oracle_schema_report.md` | File | YES | Schema report (for table/column context needed for accurate Key builders) |
| `migration-strategy-guide-sp-triggers-to-scalardb.md` | File | YES | Reference doc with 17 feature mappings and code examples |
| `output_directory` | Directory | YES | Where to write generated files |

---

## Output Contract

| Output | Location | Description |
|--------|----------|-------------|
| Java Service Classes | `<OUTPUT_DIR>/generated-java/<ObjectName>Service.java` | One file per procedure/function/package/trigger |
| Summary Report | `<OUTPUT_DIR>/scalardb_sp_migration_report.md` | Index of all generated files with analysis |

---

## How to Parse the JSON

Read `raw_schema_data.json` and extract these sections from `plsql`:

| JSON Path | Contains |
|-----------|----------|
| `plsql.procedures` | Procedure metadata (name, deterministic, parallel, authid) |
| `plsql.functions` | Function metadata (name, return_type, deterministic) |
| `plsql.packages` | Package metadata (name, authid, spec/body status) |
| `plsql.package_procedures` | Procedures within packages |
| `plsql.triggers` | Trigger metadata (name, table, timing, event, status) |
| `plsql.arguments` | Parameters for procedures/functions |
| `plsql.source` | PL/SQL source code (grouped by NAME, TYPE, ordered by LINE) |
| `plsql.trigger_source` | Trigger body source code |
| `plsql.procedure_ddl` | Full DDL for procedures |
| `plsql.function_ddl` | Full DDL for functions |
| `plsql.package_ddl` | Full DDL for packages (spec + body) |
| `plsql.trigger_ddl` | Full DDL for triggers |

Also read `oracle_schema_report.md` to extract:
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

Map each Oracle trigger to its application-layer equivalent pattern:

| # | Trigger Type | Application-Layer Pattern |
|---|-------------|---------------------------|
| 1 | BEFORE INSERT | Validation + defaults in the insert service method, before `tx.insert()` |
| 2 | AFTER INSERT (atomic) | Additional writes (audit, counters) in the same transaction after `tx.insert()` |
| 3 | AFTER INSERT (async) | Separate async handler (event/message queue) after transaction commits |
| 4 | BEFORE UPDATE | Validate OLD→NEW transitions using `tx.get()` before `tx.update()` |
| 5 | AFTER UPDATE | Audit trail / side effects in same transaction after `tx.update()` |
| 6 | BEFORE DELETE | Dependency checks / archival using `tx.get()` before `tx.delete()` |
| 7 | AFTER DELETE | Cascade deletes / audit in same transaction after `tx.delete()` |
| 8 | INSTEAD OF | Custom DML handler replacing view operations with multi-table logic |

---

## The 17 Feature Categories

When analyzing each PL/SQL object, identify which of these feature categories it uses. Each category maps to specific ScalarDB API patterns (detailed in `migration-strategy-guide-sp-triggers-to-scalardb.md`):

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
| Records | Lightweight result/value objects (e.g., `record JobHistoryKey(int employeeId, long startDate) {}`) |
| `instanceof` pattern matching | Replace `instanceof` + cast pairs (e.g., `if (obj instanceof String s) { ... }`) |
| Switch expressions | Replace multi-branch `if/else` or `switch` statements returning a value |
| Text blocks (`"""..."""`) | Multi-line SQL-like strings or error messages |
| `List.of()` / `Map.of()` | Immutable collection literals (prefer over `Arrays.asList`) |
| `String.formatted()` | Inline string formatting (prefer over `String.format()`) |
| Sealed interfaces | Model closed hierarchies of result types (optional, for complex SPs) |

**Do NOT use** preview features or anything requiring Java 21+.

### File Naming

- **Procedures/Functions**: `<ProcedureName>Service.java` (PascalCase)
  - Example: `CALCULATE_ORDER_TOTAL` → `CalculateOrderTotalService.java`
- **Packages**: `<PackageName>Service.java` (PascalCase, all package procedures in one file)
  - Example: `ORDER_MGMT` → `OrderMgmtService.java`
- **Triggers**: `<TriggerName>Service.java` (PascalCase)
  - Example: `TRG_AUDIT_LOG` → `TrgAuditLogService.java`

### Class Structure

Each generated `.java` file MUST contain:

```java
package com.example.scalardb.migration;

// ScalarDB Core (open source/community) — default dependency.
// Only use ScalarDB Cluster if SQL interface is needed.
import com.scalar.db.api.*;
import com.scalar.db.io.Key;
import com.scalar.db.exception.transaction.*;
import java.util.*;
import java.util.stream.*;

/**
 * Migrated from Oracle PL/SQL: <OBJECT_TYPE> <OBJECT_NAME>
 * Original features used: <comma-separated feature categories>
 * SP Type: <classification from 6 types>
 * Complexity: <Low/Medium/Medium-High/High>
 *
 * Java version: 17
 * Generated by ScalarDB SP & Trigger Migration Skill
 */
public class <ObjectName>Service {

    private static final String NAMESPACE = "<schema_as_is>";

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

| Oracle Type | Key Builder |
|-------------|------------|
| NUMBER(p,0) p≤9 | `Key.ofInt("col", value)` |
| NUMBER(p,0) p≤18 | `Key.ofBigInt("col", value)` |
| NUMBER(p,s) s>0 | `Key.ofDouble("col", value)` |
| VARCHAR2, CHAR | `Key.ofText("col", value)` |
| NUMBER(1) boolean | `Key.ofBoolean("col", value)` |
| DATE | `Key.ofDate("col", localDateValue)` — use `java.time.LocalDate` (ScalarDB 3.17+ native DATE) |
| TIMESTAMP | `Key.ofTimestamp("col", localDateTimeValue)` — use `java.time.LocalDateTime` (ScalarDB 3.17+ native TIMESTAMP) |

> **Important:** ScalarDB 3.17+ supports native DATE and TIMESTAMP types. Do NOT map Oracle DATE to BIGINT (epoch millis) — that mapping is incorrect. Use `Key.ofDate()` with `java.time.LocalDate` for DATE columns and `Key.ofTimestamp()` with `java.time.LocalDateTime` for TIMESTAMP columns.

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

- Use the `ORACLE_SCHEMA` or `ORACLE_USER` value as-is for the ScalarDB namespace. Use table and column names exactly as they appear in `raw_schema_data.json` — do not convert to lowercase.
- If `ORACLE_SCHEMA` is empty, use the `ORACLE_USER` value as-is
- Set as a class constant: `private static final String NAMESPACE = "<value>";`

---

## Complexity Assessment

For each PL/SQL object, calculate complexity based on:

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

After generating all Java files, produce `scalardb_sp_migration_report.md` using the template.

> **Avoid duplicate content:** The SP migration report should only contain information unique to the SP/trigger conversion. Do not duplicate content from the migration analysis report (`scalardb_migration_analysis.md`). Focus on: per-object conversion details, generated file index, feature usage matrix, and implementation recommendations.

The report includes:

1. **Executive Summary** — counts of procedures/functions/triggers, complexity breakdown
2. **Per-Object Table** — object name, type, classification, features used, complexity, generated file
3. **Feature Usage Matrix** — which of the 17 categories each SP uses
4. **Unsupported Features / Workarounds** — anything requiring special attention
5. **Generated File Index** — list of all `.java` files with descriptions

---

## Files in This Skill

```
skills/migrate-oracle-sp-trigger-to-scalardb/
├── SKILL.md                              # This file
├── reference/
│   └── migration-strategy-guide-sp-triggers-to-scalardb.md       # 17 feature mappings with code examples
└── templates/
    └── scalardb_sp_migration_report.md   # Report template
```

---

## Related

- **Command**: `commands/oracle-to-scalardb.md` (orchestration — Step 12)
- **Schema Extraction**: `skills/analyze-oracle-schema/` (provides raw_schema_data.json)
- **Schema Report**: `skills/analyze-oracle-schema/` (provides oracle_schema_report.md)
- **Migration Analysis**: `skills/migrate-oracle-to-scalardb/` (general migration docs)

---

*Skill Version: 1.1*
*Compatible with: ScalarDB 3.17+ (ScalarDB Core / open source by default; use ScalarDB Cluster only if SQL interface is needed)*
*Target Java Version: 17*
