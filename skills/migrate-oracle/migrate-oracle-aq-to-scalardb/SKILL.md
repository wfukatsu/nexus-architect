---
description: Generates Oracle AQ setup SQL (payload types, queues, enqueue triggers/SPs) and Java consumer files that dequeue messages and process them using the ScalarDB Java Transaction API.
model: opus
---

# Migrate Oracle Stored Procedures & Triggers to AQ + ScalarDB Consumer Skill

## Purpose

Convert Oracle triggers and stored procedures into an **event-driven architecture** using Oracle Advanced Queuing (AQ) as the messaging layer and ScalarDB Java Transaction API as the consumer layer.

**Producer side (Oracle SQL):** Triggers and stored procedures are replaced with AQ enqueue operations — triggers contain no business logic and simply call enqueue SPs.

**Consumer side (Java):** Message consumer classes dequeue from AQ using JMS and write to ScalarDB-managed tables using the Java Transaction API.

This skill produces:
1. A **complete SQL file** (`aq_setup.sql`) for the Oracle producer side
2. **Java consumer files** for the ScalarDB consumer side
3. An **AQ migration report** documenting all conversions

---

## Skill Responsibility

This skill is responsible for:
- Analyzing triggers and stored procedures from extracted schema JSON
- Determining which triggers/SPs should be converted to AQ enqueue patterns
- Generating SQL for payload types, queue tables, queues, modified triggers, and enqueue SPs
- Generating Java consumer service classes (dequeue + ScalarDB Transaction API)
- Generating message POJO classes and helper utilities
- Producing an AQ migration report

This skill is **NOT** responsible for:
- Orchestration or command handling (handled by `/oracle-to-scalardb` command)
- Schema extraction (handled by Subagent 1)
- Schema report generation (handled by Subagent 2)
- General migration analysis (handled by Subagent 3)
- Direct SP/trigger to Java conversion without AQ (handled by Subagent 5)
- Creating a full consumer application (build files, main class, deployment config)

---

## Input Contract

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `raw_schema_data.json` | File | YES | Extracted Oracle schema data (specifically the `plsql` section) |
| `oracle_schema_report.md` | File | YES | Schema report (for table/column context needed for accurate Key builders) |
| `aq-migration-strategy-guide.md` | File | YES | Reference doc with AQ conversion patterns and code examples |
| `aq-exception-handling-strategy.md` | File | YES | Exception classification and retry/commit strategy for consumer error handling |
| `output_directory` | Directory | YES | Where to write generated files |

---

## Output Contract

| Output | Location | Description |
|--------|----------|-------------|
| AQ Setup SQL | `<OUTPUT_DIR>/aq_setup.sql` | Complete SQL file: payload types, queues, triggers, enqueue SPs |
| Java Consumer Classes | `<OUTPUT_DIR>/generated-java/<QueueName>Consumer.java` | One consumer per queue/message-type |
| Java Message POJOs | `<OUTPUT_DIR>/generated-java/<PayloadName>Message.java` | One POJO per payload type |
| Java Helper Utility | `<OUTPUT_DIR>/generated-java/AqStructHolder.java` | Reusable Oracle STRUCT wrapper for ojdbc11 |
| Exception Classifier | `<OUTPUT_DIR>/generated-java/ExceptionClassifier.java` | Classifies exceptions into RETRIABLE / NON_RETRIABLE / UNKNOWN_TX_STATE for AQ session handling |
| AQ Migration Report | `<OUTPUT_DIR>/scalardb_aq_migration_report.md` | Report documenting all conversions |

---

## How to Parse the JSON

Read `raw_schema_data.json` and extract these sections from `plsql`:

| JSON Path | Contains |
|-----------|----------|
| `plsql.procedures` | Procedure metadata (name, deterministic, parallel, authid) |
| `plsql.functions` | Function metadata (name, return_type, deterministic) |
| `plsql.packages` | Package metadata (name, authid, spec/body status) |
| `plsql.triggers` | Trigger metadata (name, table, timing, event, status) |
| `plsql.arguments` | Parameters for procedures/functions |
| `plsql.source` | PL/SQL source code (grouped by NAME, TYPE, ordered by LINE) |
| `plsql.trigger_source` | Trigger body source code |
| `plsql.procedure_ddl` | Full DDL for procedures |
| `plsql.function_ddl` | Full DDL for functions |
| `plsql.trigger_ddl` | Full DDL for triggers |

Also read `oracle_schema_report.md` to extract:
- Table names and their columns with data types
- Primary key definitions (needed to build correct `Key.of*()` calls)
- Foreign key relationships (needed for multi-table operations)

---

## Conversion Decision Logic

### Which triggers/SPs get converted to AQ?

Analyze each trigger and stored procedure to determine if it should be converted to AQ:

| Object | Convert to AQ? | Rationale |
|--------|---------------|-----------|
| Trigger with DML (INSERT/UPDATE/DELETE on another table) | YES | The DML becomes a consumer-side ScalarDB operation |
| Trigger that calls an SP doing DML | YES | Both trigger and SP are converted |
| Trigger with only validation/defaults (no cross-table DML) | NO | Keep as application-layer validation |
| SP that INSERTs/UPDATEs/DELETEs records | YES | The DML moves to the consumer |
| SP with only SELECT/computation | NO | Convert to direct Java (Subagent 5 handles) |
| SP called by a trigger | YES | Becomes the enqueue SP; trigger just calls it |

### Trigger conversion rules

1. **If a trigger has NO business logic** (just calls an SP): The trigger calls the enqueue SP with appropriate parameters. The business logic lives in the consumer.
2. **If a trigger HAS business logic**: Extract the logic. The trigger calls an enqueue SP passing all needed data (OLD/NEW values). The consumer Java code implements the business logic.
3. **Original triggers are DISABLED** — new triggers replace them.
4. **Preserve the original trigger structure** — do not split a single trigger into multiple triggers. If the original trigger fires on multiple events (e.g., `UPDATE OF job_id, department_id`), the AQ replacement is a single trigger with the same event specification: split per column, one update touching both columns would enqueue two messages for what the original handled as one event. The replacement trigger should call the enqueue SP once, passing all relevant OLD/NEW values.

### Stored procedure conversion rules

1. **SPs that do DML**: Converted to enqueue SPs (`DBMS_AQ.ENQUEUE` with `ON_COMMIT` visibility). The actual DML moves to the consumer.
2. **SPs called by triggers**: Become enqueue SPs. The trigger just calls the enqueue SP.
3. **SPs with only SELECT/computation**: Not converted to AQ (handled by Subagent 5 as direct Java).

---

## SQL Generation Rules

### 1. Payload Type

Create one Oracle Object Type per distinct message schema. Include all data the consumer needs:

```sql
CREATE OR REPLACE TYPE <schema>.<payload_type_name> AS OBJECT (
    -- Include all columns the consumer needs to write
    -- Include operation_type VARCHAR2(20) as a routing key
    <column_name>    <oracle_type>,
    ...
    operation_type   VARCHAR2(20)   -- routing key: identifies what the consumer should do
);
```

**Naming convention:** `<table_name>_change_t` (e.g., `job_history_change_t`)

### 2. Queue Table

```sql
BEGIN
    DBMS_AQADM.CREATE_QUEUE_TABLE(
        queue_table        => '<schema>.<queue_table_name>',
        queue_payload_type => '<schema>.<PAYLOAD_TYPE_NAME>'
    );
END;
/
```

**Naming convention:** `<table_name>_qt` (e.g., `job_history_qt`)

### 3. Queue

```sql
BEGIN
    DBMS_AQADM.CREATE_QUEUE(
        queue_name  => '<schema>.<queue_name>',
        queue_table => '<schema>.<queue_table_name>',
        max_retries => 5,
        retry_delay => 0
    );
END;
/

BEGIN
    DBMS_AQADM.START_QUEUE('<schema>.<queue_name>');
END;
/

BEGIN
    DBMS_AQADM.GRANT_QUEUE_PRIVILEGE(
        privilege  => 'ALL',
        queue_name => '<schema>.<queue_name>',
        grantee    => '<schema>'
    );
END;
/
```

**Naming convention:** `<table_name>_queue` (e.g., `job_history_queue`)

### 4. Enqueue Stored Procedures

```sql
CREATE OR REPLACE PROCEDURE <schema>.SP_ENQUEUE_<operation_name> (
    <parameters matching trigger OLD/NEW values>
) AS
    l_enq_opts    DBMS_AQ.ENQUEUE_OPTIONS_T;
    l_msg_props   DBMS_AQ.MESSAGE_PROPERTIES_T;
    l_payload     <payload_type>;
    l_msgid       RAW(16);
BEGIN
    l_payload := <payload_type>(
        <field> => <param>,
        ...
        operation_type => '<OPERATION_TYPE>'   -- routing key
    );
    l_enq_opts.visibility := DBMS_AQ.ON_COMMIT;
    DBMS_AQ.ENQUEUE(
        queue_name         => '<schema>.<queue_name>',
        enqueue_options    => l_enq_opts,
        message_properties => l_msg_props,
        payload            => l_payload,
        msgid              => l_msgid
    );
END SP_ENQUEUE_<operation_name>;
/
```

### 5. Modified Triggers

Preserve the original trigger structure: do not split a single trigger into multiple triggers. If the original trigger fires on `UPDATE OF col1, col2`, the replacement trigger uses the same event specification as a single trigger, so that one update still produces one message.

```sql
-- Disable original trigger
ALTER TRIGGER <schema>.<original_trigger_name> DISABLE;

-- New trigger: no business logic, just calls the enqueue SP
-- Preserve the SAME event specification as the original trigger
CREATE OR REPLACE TRIGGER <schema>.TRG_AQ_<descriptive_name>
    <TIMING> <EVENT> ON <schema>.<table_name>
    FOR EACH ROW
BEGIN
    SP_ENQUEUE_<operation_name>(
        p_col1 => :OLD.col1,   -- or :NEW.col1 depending on timing
        p_col2 => :NEW.col2,
        ...
    );
END TRG_AQ_<descriptive_name>;
/
```

### SQL File Structure

The generated `aq_setup.sql` is organized in this order:

```sql
-- =============================================================================
-- Oracle AQ Setup for <SCHEMA_NAME> Schema
-- Generated: <TIMESTAMP>
-- =============================================================================

-- Section 1: Payload Type Definitions
-- Section 2: Queue Table Creation
-- Section 3: Queue Creation & Configuration
-- Section 4: Disable Original Triggers
-- Section 5: Enqueue Stored Procedures
-- Section 6: New AQ Triggers
-- Section 7: Verification Queries
```

**Note:** Keep the AQ setup SQL minimal — only create the necessary payload types, queues, triggers, and enqueue SPs. Avoid unnecessary idempotent cleanup blocks unless the script is designed to be re-runnable.

---

## Java Consumer Generation Rules

### Target Java Version: 17

All generated Java files target **Java 17**. Use Java 17 features where appropriate: `var`, records, `instanceof` pattern matching, switch expressions, text blocks, `List.of()`, `String.formatted()`.

**Do not use** preview features or anything requiring Java 21+: the generated code has to compile on Java 17.

### Required Dependencies (document in report)

The following JAR files are required for AQ consumer functionality:

| Dependency | Source | Notes |
|------------|--------|-------|
| `aqapi.jar` | Oracle DB (`$ORACLE_HOME/rdbms/jlib/aqapi.jar`) | Must be extracted from Oracle DB installation or container |
| `javax.jms-api-2.0.1.jar` | Maven Central or Oracle DB | JMS 2.0 API |
| `ojdbc11-23.x.jar` | Maven Central (`com.oracle.database.jdbc:ojdbc11`) | Oracle JDBC driver |
| `scalardb-3.19.x.jar` | Maven Central (`com.scalar-labs:scalardb`) | ScalarDB Core (Transaction API) |

**Note:** ScalarDB Core is the default component (open source/community edition). Only add ScalarDB Cluster dependencies if the SQL interface is needed. For the Java Transaction API used by these consumers, ScalarDB Core is sufficient.

**Note:** `aqapi.jar` is NOT available in Maven Central for most versions. It must be obtained from inside the Oracle DB installation directory and added to the project's `libs/` folder.

### File Naming

- **Consumer classes**: `<QueueName>Consumer.java` (PascalCase)
  - Example: `job_history_queue` → `JobHistoryQueueConsumer.java`
- **Message POJOs**: `<PayloadType>Message.java` (PascalCase)
  - Example: `job_history_change_t` → `JobHistoryChangeMessage.java`
- **Helper**: `AqStructHolder.java` (always this name)

Write every file listed in the Output Contract to disk, and make the Generated File Index in the report match the actual files in `generated-java/`. A report that references a file that was never written sends its reader looking for code that does not exist.

### Class templates

The shape of each generated class is in `${PLUGIN_ROOT}/skills/migrate-oracle/migrate-oracle-aq-to-scalardb/reference/java-consumer-templates.md`: `AqStructHolder` (generated once), the message POJO (one per payload type) and the consumer service class (one per queue). Read it before writing any Java file, and fill its `<...>` placeholders from the payload type and the queue. The rules below — writes, keys, error handling, namespace — apply to what those templates produce.

### ScalarDB Write Patterns

**Upsert (recommended for idempotency):**
```java
var upsert = Upsert.newBuilder()
    .namespace(NAMESPACE)
    .table("<TABLE>")
    .partitionKey(Key.of<Type>("<PK>", value))
    .clusteringKey(Key.of<Type>("<CK>", value))
    .<type>Value("<col>", value)
    .build();
tx.upsert(upsert);
```

Using Upsert is recommended because it provides idempotency during message redelivery: if the consumer crashes after the ScalarDB commit but before the AQ session commit, AQ redelivers the message and the Upsert simply overwrites with identical data. However, Upsert is not mandatory — Insert can be used if duplicate handling is managed differently.

**Insert (alternative):**
```java
var insert = Insert.newBuilder()
    .namespace(NAMESPACE)
    .table("<TABLE>")
    .partitionKey(Key.of<Type>("<PK>", value))
    .<type>Value("<col>", value)
    .build();
tx.insert(insert);
```

### Key Building Rules

Use the schema report to determine correct key types:

| Oracle Type | Key Builder |
|-------------|------------|
| NUMBER(p,0) p<=9 | `Key.ofInt("col", value)` |
| NUMBER(p,0) p<=18 | `Key.ofBigInt("col", value)` |
| NUMBER(p,s) s>0 | `Key.ofDouble("col", value)` |
| VARCHAR2, CHAR | `Key.ofText("col", value)` |
| DATE | `Key.ofDate("col", value)` — use `java.time.LocalDate` |

### Error Handling Pattern

The generated consumer code classifies exceptions to determine whether the AQ session should be rolled back (retriable) or committed (non-retriable / poison message removal). The classification is what the consumer's correctness rests on: a retriable failure committed loses the message, and a poison message rolled back is redelivered again and again. Refer to `aq-exception-handling-strategy.md` for the full classification taxonomy.

#### Exception Classification Summary

| Verdict | AQ Action | Exceptions |
|---------|-----------|------------|
| **RETRIABLE** | `session.rollback()` | `CrudConflictException`, `CommitConflictException`, `TransactionNotFoundException`, `CrudException` (base), `CommitException` (base), `TransactionException` (base) |
| **NON_RETRIABLE** | `session.commit()` (remove poison message) | `UnsatisfiedConditionException`, `IllegalArgumentException`, `ClassCastException`, `NullPointerException`, `ArrayIndexOutOfBoundsException`, `NumberFormatException` |
| **UNKNOWN_TX_STATE** | `session.commit()` + operator alert | `UnknownTransactionStatusException` |

#### Generated ExceptionClassifier Utility

Generate an `ExceptionClassifier.java` file in `generated-java/` for every AQ migration. This utility classifies exceptions into the three verdicts above. The `instanceof` check order goes from most-specific to least-specific subclass, because of the ScalarDB exception hierarchy — a superclass checked first would catch its subclasses:

```
TransactionException
├── TransactionNotFoundException            → RETRIABLE
├── CrudException
│   ├── CrudConflictException               → RETRIABLE
│   └── UnsatisfiedConditionException       → NON_RETRIABLE
├── CommitException
│   ├── CommitConflictException             → RETRIABLE
│   └── UnknownTransactionStatusException   → UNKNOWN_TX_STATE
└── RollbackException                       → (internal, not classified)
```

The class itself is in `${PLUGIN_ROOT}/skills/migrate-oracle/migrate-oracle-aq-to-scalardb/reference/aq-exception-handling-strategy.md` § ExceptionClassifier; generate it as written there, in the same check order.

#### ScalarDbWriter — Preserve Exception Types

The writer does not call `tx.abort()` on `UnknownTransactionStatusException` — the TX may have committed:

```java
try {
    tx.upsert(/* ... */);
    tx.commit();
} catch (UnknownTransactionStatusException e) {
    // DO NOT abort — TX may have committed successfully
    throw e;
} catch (Exception e) {
    try { tx.abort(); } catch (RollbackException ignored) {}
    throw e;  // preserve original type for classifier
}
```

#### Consumer Loop — Two-Phase Error Handling

Separate message parsing (always non-retriable on failure) from processing (classified):

```java
// PHASE 1: Parse — failure = broken payload, always non-retriable
JobChangeMessage parsed;
try {
    parsed = parseAdtMessage(msg);
} catch (Exception e) {
    log.error("Parse failed (NON_RETRIABLE): {}", e.getMessage(), e);
    session.commit();  // remove unparseable message
    continue;
}

// PHASE 2: Process — classify the outcome
try {
    writer.writeMessage(parsed);
    session.commit();
} catch (Exception e) {
    switch (ExceptionClassifier.classify(e)) {
        case RETRIABLE       -> { session.rollback(); }
        case NON_RETRIABLE   -> { log.error("Poison message removed: {}", e.getMessage(), e); session.commit(); }
        case UNKNOWN_TX_STATE -> { log.error("VERIFY SCALARDB DATA: {}", e.getMessage(), e); session.commit(); }
    }
}
```

### Namespace Handling

- Use the `ORACLE_SCHEMA` or `ORACLE_USER` value as-is for the ScalarDB namespace. Use table and column names exactly as they appear in `raw_schema_data.json` — do not convert to lowercase.
- If `ORACLE_SCHEMA` is empty, use the `ORACLE_USER` value as-is.
- Set as a class constant: `private static final String NAMESPACE = "<value>";`

---

## How the Generated Files Should Be Used

Document this section in the AQ migration report for the user. Its text — the prerequisites and the integration steps — is in `${PLUGIN_ROOT}/skills/migrate-oracle/migrate-oracle-aq-to-scalardb/reference/generated-files-usage.md`; read it when writing the report and adjust it to the files and names this migration generated.

---

## Complexity Assessment

For each trigger/SP being converted to AQ, assess complexity:

| Factor | Low | Medium | High |
|--------|-----|--------|------|
| Tables touched by consumer | 1 | 2-3 | 4+ |
| Payload fields | 1-5 | 6-10 | 11+ |
| Operation types per queue | 1 | 2-3 | 4+ |
| Cross-table dependencies | None | Simple FK | Complex chains |
| Data transformations | None | Simple mapping | Complex logic |

---

## Report Generation

After generating all files, produce `scalardb_aq_migration_report.md` using the template. The report includes:

1. **Executive Summary** — counts of queues, payload types, triggers/SPs converted
2. **AQ Architecture Diagram** — producer/consumer flow
3. **Queue Configuration** — all queues created with settings
4. **Trigger/SP Conversion Table** — original → AQ mapping for each object
5. **Generated SQL Summary** — sections in `aq_setup.sql`
6. **Generated Java File Index** — all consumer, POJO, and helper files
7. **Prerequisites & Integration Guide** — how to use the generated files
8. **Required Dependencies** — JAR files with sources

---

## Files in This Skill

```
skills/migrate-oracle/migrate-oracle-aq-to-scalardb/
├── SKILL.md                              # This file
├── reference/
│   ├── aq-migration-strategy-guide.md    # AQ conversion patterns and code examples
│   ├── aq-exception-handling-strategy.md # Exception classification for consumer retry/commit decisions
│   ├── java-consumer-templates.md        # Class templates: AqStructHolder, message POJO, consumer service
│   ├── generated-files-usage.md          # Report text: prerequisites and integration steps
│   └── AQ-official-docs/                 # Oracle AQ official documentation
│       ├── 23 - Oracle Database Advanced Queuing (AQ)_Html.txt
│       ├── 24 - Oracle Database Advanced Queuing (AQADM)_Html.txt
│       └── 25 - Oracle Advanced Queuing (AQ) DBMS_AQELM.txt
└── templates/
    └── scalardb_aq_migration_report.md   # AQ migration report template
```

---

## Related

- **Command**: `commands/oracle-to-scalardb.md` (orchestration — Step 11)
- **Schema Extraction**: `skills/migrate-oracle/analyze-oracle-schema/` (provides raw_schema_data.json)
- **Schema Report**: `skills/migrate-oracle/analyze-oracle-schema/` (provides oracle_schema_report.md)
- **Migration Analysis**: `skills/migrate-oracle/migrate-oracle-to-scalardb/` (general migration docs)
- **SP & Trigger Migration**: `skills/migrate-oracle/migrate-oracle-sp-trigger-to-scalardb/` (direct Java conversion without AQ)

---

*Skill Version: 1.0*
*Compatible with: ScalarDB 3.17+*
*Target Java Version: 17*
