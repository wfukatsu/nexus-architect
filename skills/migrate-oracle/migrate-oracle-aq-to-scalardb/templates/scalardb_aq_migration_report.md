# Oracle AQ Migration Report Template

This template is used to generate the **AQ migration report**. Replace all `{{PLACEHOLDER}}` tokens with actual values from the analysis.

---

# Oracle AQ + ScalarDB Consumer Migration Report

**Generated**: {{TIMESTAMP}}
**Source Database**: {{DATABASE_NAME}}
**Source Schema**: {{SCHEMA_NAME}}
**Target**: ScalarDB 3.17+ with Oracle AQ messaging
**Migration Approach**: Event-driven (AQ Producer → Java Consumer → ScalarDB)

---

## 1. Executive Summary

### Conversion Statistics

| Metric | Count |
|--------|-------|
| Queues Created | {{QUEUE_COUNT}} |
| Payload Types Created | {{PAYLOAD_TYPE_COUNT}} |
| Original Triggers Disabled | {{DISABLED_TRIGGER_COUNT}} |
| New AQ Triggers Created | {{NEW_TRIGGER_COUNT}} |
| Enqueue SPs Created | {{ENQUEUE_SP_COUNT}} |
| Java Consumer Classes Generated | {{CONSUMER_CLASS_COUNT}} |
| Java Message POJOs Generated | {{MESSAGE_POJO_COUNT}} |
| Total Java Files Generated | {{TOTAL_JAVA_FILES}} |

### Complexity Summary

| Rating | Count | Objects |
|--------|-------|---------|
| Low | {{LOW_COUNT}} | {{LOW_OBJECTS}} |
| Medium | {{MEDIUM_COUNT}} | {{MEDIUM_OBJECTS}} |
| High | {{HIGH_COUNT}} | {{HIGH_OBJECTS}} |

**Overall AQ Migration Complexity**: {{OVERALL_COMPLEXITY}}

---

## 2. Architecture Overview

```
Oracle Database (Producer)                    Java Application (Consumer)
================================              ================================

  DML on source tables                         Continuous polling loop
         │                                            │
         v                                            v
  AQ Triggers fire                             receiver.receive(timeout)
  (no business logic)                                 │
         │                                            v
         v                                     parseMessage() → POJO
  Enqueue SPs called                                  │
  DBMS_AQ.ENQUEUE(                                    v
    visibility => ON_COMMIT                    ScalarDB Transaction
  )                                            tx.upsert(target table)
         │                                     tx.commit()
         v                                            │
  COMMIT → messages READY ──────────────────►         v
                                               session.commit()
                                               (message removed from queue)
```

### Queue Map

| Queue | Queue Table | Payload Type | Source Table | Target Table |
|-------|-------------|--------------|-------------|--------------|
{{#EACH_QUEUE}}
| {{QUEUE_NAME}} | {{QUEUE_TABLE}} | {{PAYLOAD_TYPE}} | {{SOURCE_TABLE}} | {{TARGET_TABLE}} |
{{/EACH_QUEUE}}

---

## 3. Queue Configuration

{{#EACH_QUEUE_DETAIL}}
### Queue: {{QUEUE_NAME}}

| Setting | Value |
|---------|-------|
| Queue Table | `{{QUEUE_TABLE}}` |
| Payload Type | `{{PAYLOAD_TYPE}}` |
| Max Retries | {{MAX_RETRIES}} |
| Retry Delay | {{RETRY_DELAY}} seconds |
| Message Grouping | {{MESSAGE_GROUPING}} |
| Visibility | ON_COMMIT |

**Operation Types (routing keys):**

| Operation Type | Description | Consumer Handler |
|---------------|-------------|-----------------|
{{#EACH_OPERATION}}
| `{{OP_TYPE}}` | {{OP_DESCRIPTION}} | `handle{{OP_METHOD}}()` |
{{/EACH_OPERATION}}

{{/EACH_QUEUE_DETAIL}}

---

## 4. Trigger & SP Conversion Details

### Original Triggers (Disabled)

| # | Trigger Name | Table | Timing/Event | Status |
|---|-------------|-------|-------------|--------|
{{#EACH_DISABLED_TRIGGER}}
| {{N}} | `{{TRIGGER_NAME}}` | `{{TABLE_NAME}}` | {{TIMING}} {{EVENT}} | DISABLED |
{{/EACH_DISABLED_TRIGGER}}

### New AQ Triggers (Created)

| # | Trigger Name | Table | Timing/Event | Calls SP | Operation Type |
|---|-------------|-------|-------------|----------|---------------|
{{#EACH_NEW_TRIGGER}}
| {{N}} | `{{TRIGGER_NAME}}` | `{{TABLE_NAME}}` | {{TIMING}} {{EVENT}} | `{{ENQUEUE_SP}}` | `{{OP_TYPE}}` |
{{/EACH_NEW_TRIGGER}}

### Enqueue Stored Procedures (Created)

| # | SP Name | Queue | Operation Type | Parameters |
|---|---------|-------|---------------|------------|
{{#EACH_ENQUEUE_SP}}
| {{N}} | `{{SP_NAME}}` | `{{QUEUE_NAME}}` | `{{OP_TYPE}}` | {{PARAM_COUNT}} params |
{{/EACH_ENQUEUE_SP}}

### Conversion Mapping (Original → AQ)

| Original Object | Type | Converted To | Notes |
|-----------------|------|-------------|-------|
{{#EACH_CONVERSION}}
| `{{ORIGINAL_NAME}}` | {{ORIGINAL_TYPE}} | `{{NEW_NAME}}` ({{NEW_TYPE}}) | {{NOTES}} |
{{/EACH_CONVERSION}}

---

## 5. Generated SQL Summary

**File**: `{{OUTPUT_DIR}}/aq_setup.sql`

| Section | Content | Lines |
|---------|---------|-------|
| 1 - Header | Schema info, timestamp | {{HEADER_LINES}} |
| 2 - Payload Types | `CREATE TYPE` definitions | {{PAYLOAD_LINES}} |
| 3 - Queue Tables | `DBMS_AQADM.CREATE_QUEUE_TABLE` | {{QUEUE_TABLE_LINES}} |
| 4 - Queues | `CREATE_QUEUE`, `START_QUEUE`, `GRANT_QUEUE_PRIVILEGE` | {{QUEUE_LINES}} |
| 5 - Disable Triggers | `ALTER TRIGGER ... DISABLE` | {{DISABLE_LINES}} |
| 6 - Enqueue SPs | `CREATE PROCEDURE` with `DBMS_AQ.ENQUEUE` | {{SP_LINES}} |
| 7 - New Triggers | `CREATE TRIGGER` calling enqueue SPs | {{TRIGGER_LINES}} |
| 8 - Verification | Diagnostic queries | {{VERIFY_LINES}} |
| **Total** | | **{{TOTAL_SQL_LINES}}** |

---

## 6. Generated Java File Index

| # | File | Type | Description | Lines |
|---|------|------|-------------|-------|
{{#EACH_JAVA_FILE}}
| {{N}} | `{{FILENAME}}` | {{FILE_TYPE}} | {{DESCRIPTION}} | {{LINES}} |
{{/EACH_JAVA_FILE}}

**Directory structure:**
```
{{OUTPUT_DIR}}/generated-java/
{{#EACH_FILE_TREE}}
├── {{FILENAME}}
{{/EACH_FILE_TREE}}
```

---

## 7. Prerequisites & Integration Guide

### Step 1: Import Database into ScalarDB

**CRITICAL**: ScalarDB consumer code cannot modify the database unless tables are imported and managed through ScalarDB.

```bash
# Import existing Oracle tables into ScalarDB
java -jar scalardb-schema-loader-3.17.0.jar \
  --config scalardb.properties \
  --schema-file import_schema.json \
  --import
```

Use `transaction-metadata-decoupling: true` in the import schema to keep original tables unchanged.

### Step 2: Run AQ Setup SQL

Execute the generated SQL file against the Oracle database:

```bash
sqlplus {{SCHEMA_NAME}}/password@//host:port/service @aq_setup.sql
```

This creates:
- {{PAYLOAD_TYPE_COUNT}} payload type(s)
- {{QUEUE_COUNT}} queue(s) with queue table(s)
- Disables {{DISABLED_TRIGGER_COUNT}} original trigger(s)
- Creates {{ENQUEUE_SP_COUNT}} enqueue SP(s)
- Creates {{NEW_TRIGGER_COUNT}} new AQ trigger(s)

### Step 3: Add Required Dependencies

```groovy
// build.gradle
dependencies {
    // AQ JMS — must be extracted from Oracle DB installation
    implementation fileTree(dir: 'libs', include: ['*.jar'])  // aqapi.jar

    // From Maven Central
    implementation 'javax.jms:javax.jms-api:2.0.1'
    implementation 'com.oracle.database.jdbc:ojdbc11:23.4.0.24.05'
    implementation 'com.scalar-labs:scalardb:3.17.1'
    implementation 'org.slf4j:slf4j-simple:2.0.9'
}
```

**Required JAR files not in Maven Central:**

| JAR | Where to Find |
|-----|--------------|
| `aqapi.jar` | `$ORACLE_HOME/rdbms/jlib/aqapi.jar` — extract from Oracle DB container: `docker cp oracle-db:$ORACLE_HOME/rdbms/jlib/aqapi.jar ./libs/` |

### Step 4: Add Generated Java Files to Your Project

Copy the generated files from `{{OUTPUT_DIR}}/generated-java/` into your application source tree under the `com.example.scalardb.aq` package (or rename to your preferred package).

### Step 5: Wire Up the Consumer Loop

The generated consumer classes provide `processMessage()` and `parseMessage()` methods. Your application provides the JMS connection and dequeue loop:

```java
// Initialize ScalarDB
TransactionFactory factory = TransactionFactory.create("scalardb.properties");
DistributedTransactionManager txManager = factory.getTransactionManager();

// Initialize AQ JMS
QueueConnectionFactory qcf = AQjmsFactory.getQueueConnectionFactory(jdbcUrl, props);
QueueConnection conn = qcf.createQueueConnection(user, pass);
conn.start();
QueueSession session = conn.createQueueSession(true, Session.SESSION_TRANSACTED);
Queue queue = ((AQjmsSession) session).getQueue("{{SCHEMA_NAME}}", "{{PRIMARY_QUEUE}}");
ORADataFactory payloadFactory = (datum, sqlType) -> new AqStructHolder(datum);
QueueReceiver receiver = ((AQjmsSession) session).createReceiver(queue, null, payloadFactory);

// Process messages with exception classification
var consumer = new {{PRIMARY_CONSUMER_CLASS}}(txManager);
while (!Thread.currentThread().isInterrupted()) {
    Message msg = receiver.receive(10_000);
    if (msg == null) continue;

    // Phase 1: Parse — failure = broken payload, remove immediately
    {{PRIMARY_MESSAGE_CLASS}} parsed;
    try {
        parsed = {{PRIMARY_CONSUMER_CLASS}}.parseMessage(msg);
    } catch (Exception e) {
        log.error("Parse failed — removing poison message: {}", e.getMessage(), e);
        session.commit();
        continue;
    }

    // Phase 2: Process — classify the outcome
    try {
        consumer.processMessage(parsed);
        session.commit();   // message permanently removed from queue
    } catch (Exception e) {
        switch (ExceptionClassifier.classify(e)) {
            case RETRIABLE       -> session.rollback();  // AQ redelivers, retry_count++
            case NON_RETRIABLE   -> { log.error("Poison: {}", e.getMessage(), e); session.commit(); }
            case UNKNOWN_TX_STATE -> { log.error("VERIFY DATA: {}", e.getMessage(), e); session.commit(); }
        }
    }
}
```

---

## 8. Idempotency & Error Handling

### Dual-Transaction Pattern

| Step | Transaction | On Success | On Failure |
|------|------------|-----------|-----------|
| 1 | ScalarDB: `tx.commit()` | Data written | `tx.abort()` → classified by `ExceptionClassifier` |
| 2 | AQ JMS: `session.commit()` | Message removed | Depends on exception verdict (see below) |

### Exception Classification

The generated `ExceptionClassifier.java` categorizes every consumer exception into one of three verdicts:

| Verdict | AQ Session Action | Effect | Example Exceptions |
|---------|-------------------|--------|-------------------|
| **RETRIABLE** | `session.rollback()` | Message returns to queue, `retry_count++` | `CrudConflictException`, `CommitConflictException`, `TransactionNotFoundException` |
| **NON_RETRIABLE** | `session.commit()` | Poison message removed immediately | `UnsatisfiedConditionException`, `IllegalArgumentException`, `ClassCastException`, `NullPointerException` |
| **UNKNOWN_TX_STATE** | `session.commit()` | Message removed; operator must verify ScalarDB data | `UnknownTransactionStatusException` |

**Why classify?** Without classification, a poison message (e.g., unknown `operation_type`) is rolled back and retried `max_retries` times before reaching the exception queue — wasting dequeue cycles for a failure that will never succeed. With classification, poison messages are removed in one cycle.

### Upsert for Idempotency

The generated consumer code uses `Upsert` (recommended) instead of `Insert`. This handles the case where ScalarDB commits but the JVM crashes before `session.commit()` — AQ redelivers the message and the Upsert simply overwrites with identical data.

**Note**: Upsert is recommended but not mandatory. If your use case requires strict insert-only semantics, you can change `tx.upsert()` to `tx.insert()` in the generated consumer code.

### Message Retry Behavior

| Scenario | retry_count | Message State |
|----------|-------------|--------------|
| `session.rollback()` (RETRIABLE verdict) | Incremented | READY (retry_delay=0) or WAITING |
| `session.commit()` (NON_RETRIABLE verdict) | N/A | Message removed — logged for review |
| JVM crash (no rollback) | NOT incremented | Redelivered as-is |
| retry_count > max_retries | — | Moved to exception queue (`*_E`) |

---

## 9. Recommendations

{{#EACH_RECOMMENDATION}}
{{N}}. {{RECOMMENDATION}}
{{/EACH_RECOMMENDATION}}

### Testing Checklist

- [ ] Run `aq_setup.sql` on a test/dev database first
- [ ] Verify queues are running: `SELECT * FROM dba_queues WHERE owner = '{{SCHEMA_NAME}}'`
- [ ] Execute a test DML to trigger an enqueue
- [ ] Verify message appears in queue: `SELECT * FROM aq$<queue_table>`
- [ ] Start the Java consumer and verify ScalarDB write
- [ ] Test failure scenario: stop consumer mid-processing, verify AQ redelivery
- [ ] Verify idempotency: same message processed twice produces same result

---

*Report generated by ScalarDB AQ Migration Skill*
*Input consumed from: raw_schema_data.json, oracle_schema_report.md*
