---
name: migrate-oracle-aq-to-scalardb
description: Generates Oracle AQ setup SQL (payload types, queues, enqueue triggers/SPs) and Java consumer files that dequeue messages and process them using the ScalarDB Java Transaction API.
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
4. **Preserve the original trigger structure** — do NOT split a single trigger into multiple triggers. If the original trigger fires on multiple events (e.g., `UPDATE OF job_id, department_id`), the AQ replacement MUST be a single trigger with the same event specification. The replacement trigger should call the enqueue SP once, passing all relevant OLD/NEW values.

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

**IMPORTANT:** Preserve the original trigger structure. Do NOT split a single trigger into multiple triggers. If the original trigger fires on `UPDATE OF col1, col2`, the replacement trigger MUST use the same event specification as a single trigger.

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

The generated `aq_setup.sql` MUST be organized in this order:

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

All generated Java files MUST target **Java 17**. Use Java 17 features where appropriate: `var`, records, `instanceof` pattern matching, switch expressions, text blocks, `List.of()`, `String.formatted()`.

**Do NOT use** preview features or anything requiring Java 21+.

### Required Dependencies (document in report)

The following JAR files are required for AQ consumer functionality:

| Dependency | Source | Notes |
|------------|--------|-------|
| `aqapi.jar` | Oracle DB (`$ORACLE_HOME/rdbms/jlib/aqapi.jar`) | Must be extracted from Oracle DB installation or container |
| `javax.jms-api-2.0.1.jar` | Maven Central or Oracle DB | JMS 2.0 API |
| `ojdbc11-23.x.jar` | Maven Central (`com.oracle.database.jdbc:ojdbc11`) | Oracle JDBC driver |
| `scalardb-3.17.x.jar` | Maven Central (`com.scalar-labs:scalardb`) | ScalarDB Core (Transaction API) |

**Note:** ScalarDB Core is the default component (open source/community edition). Only add ScalarDB Cluster dependencies if the SQL interface is needed. For the Java Transaction API used by these consumers, ScalarDB Core is sufficient.

**Note:** `aqapi.jar` is NOT available in Maven Central for most versions. It must be obtained from inside the Oracle DB installation directory and added to the project's `libs/` folder.

### File Naming

- **Consumer classes**: `<QueueName>Consumer.java` (PascalCase)
  - Example: `job_history_queue` → `JobHistoryQueueConsumer.java`
- **Message POJOs**: `<PayloadType>Message.java` (PascalCase)
  - Example: `job_history_change_t` → `JobHistoryChangeMessage.java`
- **Helper**: `AqStructHolder.java` (always this name)

**IMPORTANT:** ALL files listed in the Output Contract MUST actually be written to disk. The Generated File Index in the report MUST match the actual files in `generated-java/`. Do not reference files that were not written.

### AqStructHolder (generate once)

```java
package com.example.scalardb.aq;

import oracle.sql.Datum;
import oracle.sql.ORAData;
import oracle.sql.STRUCT;

/**
 * Wraps Oracle STRUCT for ojdbc11 compatibility.
 * Required because oracle.sql.STRUCT no longer implements ORAData directly in ojdbc11.
 *
 * Java version: 17
 * Generated by ScalarDB AQ Migration Skill
 */
public class AqStructHolder implements ORAData {
    private final Datum datum;

    public AqStructHolder(Datum datum) {
        this.datum = datum;
    }

    public STRUCT asStruct() {
        return (STRUCT) datum;
    }

    @Override
    public Datum toDatum(java.sql.Connection conn) {
        return datum;
    }
}
```

### Message POJO (one per payload type)

```java
package com.example.scalardb.aq;

/**
 * Message POJO for Oracle AQ payload type: <PAYLOAD_TYPE_NAME>
 * Maps to Oracle Object Type attributes by positional index.
 *
 * Java version: 17
 * Generated by ScalarDB AQ Migration Skill
 */
public class <PayloadName>Message {
    private <type> <field>;     // [0] <oracle_attribute_name>
    ...
    private String operationType;  // [N] operation_type (routing key)

    // Getters and setters for all fields
}
```

### Consumer Service Class (one per queue)

```java
package com.example.scalardb.aq;

import com.scalar.db.api.*;
import com.scalar.db.io.Key;
import com.scalar.db.exception.transaction.*;
import oracle.jms.*;
import oracle.sql.STRUCT;
import javax.jms.*;
import java.math.BigDecimal;
import java.util.*;

/**
 * AQ Consumer for queue: <QUEUE_NAME>
 * Dequeues messages and processes them using ScalarDB Java Transaction API.
 *
 * Original triggers/SPs converted:
 *   - <list of original trigger/SP names>
 *
 * Java version: 17
 * Generated by ScalarDB AQ Migration Skill
 */
public class <QueueName>Consumer {

    private static final String NAMESPACE = "<schema>";
    private static final String QUEUE_OWNER = "<SCHEMA>";
    private static final String QUEUE_NAME = "<queue_name>";
    private static final long RECEIVE_TIMEOUT_MS = 10_000;

    private final DistributedTransactionManager txManager;

    public <QueueName>Consumer(DistributedTransactionManager txManager) {
        this.txManager = txManager;
    }

    /**
     * Processes a single dequeued message using ScalarDB Transaction API.
     * Routes to the appropriate handler based on operation_type.
     *
     * @param message the parsed message POJO
     * @throws TransactionException if ScalarDB transaction fails
     */
    public void processMessage(<PayloadName>Message message) throws TransactionException {
        switch (message.getOperationType()) {
            case "<OPERATION_1>" -> handle<Operation1>(message);
            case "<OPERATION_2>" -> handle<Operation2>(message);
            default -> throw new IllegalArgumentException(
                "Unknown operation type: " + message.getOperationType());
        }
    }

    // --- Handler methods (one per operation_type) ---

    private void handle<Operation1>(<PayloadName>Message msg) throws TransactionException {
        DistributedTransaction tx = txManager.begin();
        try {
            // ScalarDB write logic — Upsert recommended for idempotency
            var upsert = Upsert.newBuilder()
                .namespace(NAMESPACE)
                .table("<TABLE_NAME>")
                .partitionKey(Key.of<Type>("<PK_COL>", msg.get<PkField>()))
                // .clusteringKey(...) if applicable
                // .xxxValue("<col>", msg.get<Field>()) for each column
                .build();
            tx.upsert(upsert);
            tx.commit();
        } catch (Exception e) {
            tx.abort();
            throw e;
        }
    }

    // --- AQ JMS message parsing ---

    /**
     * Parses an Oracle ADT message (STRUCT) into a message POJO.
     * Attribute positions match the Oracle Object Type definition order.
     */
    public static <PayloadName>Message parseMessage(Message jmsMessage) throws Exception {
        var adtMsg = (AQjmsAdtMessage) jmsMessage;
        var holder = (AqStructHolder) adtMsg.getAdtPayload();
        Object[] attrs = holder.asStruct().getAttributes();

        var msg = new <PayloadName>Message();
        // Map each positional attribute to the POJO field
        // msg.setField((<cast>) attrs[index]);
        return msg;
    }
}
```

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

**CRITICAL:** The generated consumer code MUST classify exceptions to determine whether the AQ session should be rolled back (retriable) or committed (non-retriable / poison message removal). Refer to `aq-exception-handling-strategy.md` for the full classification taxonomy.

#### Exception Classification Summary

| Verdict | AQ Action | Exceptions |
|---------|-----------|------------|
| **RETRIABLE** | `session.rollback()` | `CrudConflictException`, `CommitConflictException`, `TransactionNotFoundException`, `CrudException` (base), `CommitException` (base), `TransactionException` (base) |
| **NON_RETRIABLE** | `session.commit()` (remove poison message) | `UnsatisfiedConditionException`, `IllegalArgumentException`, `ClassCastException`, `NullPointerException`, `ArrayIndexOutOfBoundsException`, `NumberFormatException` |
| **UNKNOWN_TX_STATE** | `session.commit()` + operator alert | `UnknownTransactionStatusException` |

#### Generated ExceptionClassifier Utility

Generate an `ExceptionClassifier.java` file in `generated-java/` for every AQ migration. This utility classifies exceptions into the three verdicts above. The `instanceof` check order MUST go from most-specific to least-specific subclass due to the ScalarDB exception hierarchy:

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

```java
import com.scalar.db.exception.transaction.*;

public final class ExceptionClassifier {

    public enum Verdict { RETRIABLE, NON_RETRIABLE, UNKNOWN_TX_STATE }

    private ExceptionClassifier() {}

    public static Verdict classify(Exception e) {
        // ScalarDB: definitely transient (most specific first)
        if (e instanceof CrudConflictException)         return Verdict.RETRIABLE;
        if (e instanceof CommitConflictException)        return Verdict.RETRIABLE;
        if (e instanceof TransactionNotFoundException)   return Verdict.RETRIABLE;

        // ScalarDB: unknown commit state
        if (e instanceof UnknownTransactionStatusException) return Verdict.UNKNOWN_TX_STATE;

        // ScalarDB: definitely non-retriable
        if (e instanceof UnsatisfiedConditionException)  return Verdict.NON_RETRIABLE;

        // ScalarDB: base classes (may be transient) — let max_retries decide
        if (e instanceof TransactionException)           return Verdict.RETRIABLE;

        // Parse/application: permanently broken data
        if (e instanceof ClassCastException)             return Verdict.NON_RETRIABLE;
        if (e instanceof NullPointerException)           return Verdict.NON_RETRIABLE;
        if (e instanceof ArrayIndexOutOfBoundsException) return Verdict.NON_RETRIABLE;
        if (e instanceof NumberFormatException)          return Verdict.NON_RETRIABLE;
        if (e instanceof IllegalArgumentException)       return Verdict.NON_RETRIABLE;

        // Default: assume transient, let max_retries be the safety net
        return Verdict.RETRIABLE;
    }
}
```

#### ScalarDbWriter — Preserve Exception Types

The writer MUST NOT call `tx.abort()` on `UnknownTransactionStatusException` — the TX may have committed:

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

Document this section in the AQ migration report for the user:

### Prerequisites

1. **Import the database into ScalarDB first.** ScalarDB consumer code cannot modify the database unless the tables are migrated and managed through ScalarDB. Use the Schema Loader with `--import` to import existing Oracle tables.

2. **Run `aq_setup.sql` against the Oracle database.** This creates the AQ infrastructure (payload types, queues) and replaces the original triggers/SPs with AQ-enabled versions.

3. **Add required JAR files to your project:**
   - `aqapi.jar` — extract from `$ORACLE_HOME/rdbms/jlib/aqapi.jar` inside the Oracle DB container or installation
   - `javax.jms-api-2.0.1.jar` — available from Maven Central or Oracle DB
   - `ojdbc11` — Oracle JDBC driver from Maven Central
   - `scalardb` — ScalarDB from Maven Central

### Integration Steps

1. **Add the generated Java files** to your application's source tree under `com.example.scalardb.aq` (or your preferred package).

2. **Initialize ScalarDB** in your application startup:
   ```java
   TransactionFactory factory = TransactionFactory.create("scalardb.properties");
   DistributedTransactionManager txManager = factory.getTransactionManager();
   ```

3. **Create the AQ JMS consumer loop** in your application's main class or service runner. The generated consumer classes provide `processMessage()` and `parseMessage()` methods — your application provides the JMS connection and dequeue loop:
   ```java
   // Application responsibility: JMS connection, session, receiver
   QueueConnectionFactory qcf = AQjmsFactory.getQueueConnectionFactory(jdbcUrl, props);
   QueueConnection conn = qcf.createQueueConnection(user, pass);
   QueueSession session = conn.createQueueSession(true, Session.SESSION_TRANSACTED);
   Queue queue = ((AQjmsSession) session).getQueue(QUEUE_OWNER, QUEUE_NAME);
   ORADataFactory payloadFactory = (datum, sqlType) -> new AqStructHolder(datum);
   QueueReceiver receiver = ((AQjmsSession) session).createReceiver(queue, null, payloadFactory);

   // Use generated consumer with exception classification
   var consumer = new <QueueName>Consumer(txManager);
   while (!Thread.currentThread().isInterrupted()) {
       Message msg = receiver.receive(10_000);
       if (msg == null) continue;

       // Phase 1: Parse — failure = broken payload, remove immediately
       <PayloadName>Message parsed;
       try {
           parsed = <QueueName>Consumer.parseMessage(msg);
       } catch (Exception e) {
           log.error("Parse failed — removing poison message: {}", e.getMessage(), e);
           session.commit();
           continue;
       }

       // Phase 2: Process — classify the outcome
       try {
           consumer.processMessage(parsed);
           session.commit();   // removes message from AQ
       } catch (Exception e) {
           switch (ExceptionClassifier.classify(e)) {
               case RETRIABLE       -> session.rollback();
               case NON_RETRIABLE   -> { log.error("Poison: {}", e.getMessage(), e); session.commit(); }
               case UNKNOWN_TX_STATE -> { log.error("VERIFY DATA: {}", e.getMessage(), e); session.commit(); }
           }
       }
   }
   ```

4. **The dual-transaction pattern**: ScalarDB commits first, then AQ session commits. If the JVM crashes between the two, AQ redelivers the message and the Upsert handles it idempotently.

5. **Exception classification**: The generated `ExceptionClassifier.java` determines whether a failed message should be retried (`session.rollback()`) or removed as a poison message (`session.commit()`). See `aq-exception-handling-strategy.md` for the full taxonomy.

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
skills/migrate-oracle-aq-to-scalardb/
├── SKILL.md                              # This file
├── reference/
│   ├── aq-migration-strategy-guide.md    # AQ conversion patterns and code examples
│   ├── aq-exception-handling-strategy.md # Exception classification for consumer retry/commit decisions
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
- **Schema Extraction**: `skills/analyze-oracle-schema/` (provides raw_schema_data.json)
- **Schema Report**: `skills/analyze-oracle-schema/` (provides oracle_schema_report.md)
- **Migration Analysis**: `skills/migrate-oracle-to-scalardb/` (general migration docs)
- **SP & Trigger Migration**: `skills/migrate-oracle-sp-trigger-to-scalardb/` (direct Java conversion without AQ)

---

*Skill Version: 1.0*
*Compatible with: ScalarDB 3.17+*
*Target Java Version: 17*
