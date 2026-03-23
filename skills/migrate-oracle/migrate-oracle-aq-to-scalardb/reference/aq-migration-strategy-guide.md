# AQ Migration Strategy Guide: Oracle Triggers & Stored Procedures to AQ + ScalarDB Consumer

## Overview

This guide provides patterns for converting Oracle triggers and stored procedures into an event-driven architecture:

- **Producer (Oracle):** Triggers and stored procedures enqueue messages to Oracle Advanced Queues instead of performing direct DML operations.
- **Consumer (Java):** A Java application dequeues messages via JMS and processes them using the ScalarDB Java Transaction API.

### Why AQ?

| Direct Migration | AQ-Based Migration |
|-----------------|-------------------|
| Application calls ScalarDB directly | Oracle fires trigger → enqueue → Java consumer → ScalarDB |
| Synchronous | Asynchronous (message-based) |
| All logic in Java app | Producer logic stays in Oracle; consumer logic in Java |
| Tight coupling | Loose coupling via message queue |
| No message retry | Built-in retry with `max_retries` and exception queue |

### Architecture

```
Oracle Database (Producer)                Java Application (Consumer)
================================          ================================

UPDATE employees                          Continuous polling loop
SET job_id = 'AD_ASST'                    receiver.receive(timeout)
WHERE employee_id = 107;                    │
       │                                    │ (blocks until message READY)
       v                                    │
TRG_AQ_JOB_CHANGE fires                    │
       │                                    │
       v                                    │
SP_ENQUEUE_CLOSE_HISTORY()                  │
  DBMS_AQ.ENQUEUE(                          │
    visibility => ON_COMMIT  ──────────── invisible until COMMIT
  )                                         │
       │                                    │
COMMIT; ────────────────────────────────── message → READY state
                                            │
                                            v
                                    parseMessage(msg) → POJO
                                            │
                                            v
                                    txManager.begin()
                                    tx.upsert(ScalarDB row)
                                    tx.commit()  ← ScalarDB write done
                                            │
                                            v
                                    session.commit() ← message removed from AQ
```

---

## Prerequisites

### 1. Database Must Be Imported into ScalarDB First

**CRITICAL:** ScalarDB consumer code cannot modify the database unless the target tables are imported and managed through ScalarDB.

Before deploying the AQ consumer:
1. Use ScalarDB Schema Loader with `--import` to import existing Oracle tables
2. Recommended: use `transaction-metadata-decoupling: true` to keep original tables unchanged
3. Verify ScalarDB can read/write the imported tables

### 2. Required JAR Files

| JAR | Source | Maven Central? |
|-----|--------|----------------|
| `aqapi.jar` | `$ORACLE_HOME/rdbms/jlib/aqapi.jar` inside Oracle DB | **NO** — must extract from Oracle installation |
| `javax.jms-api-2.0.1.jar` | Maven Central or Oracle DB | Yes: `javax.jms:javax.jms-api:2.0.1` |
| `ojdbc11-23.x.jar` | Maven Central | Yes: `com.oracle.database.jdbc:ojdbc11:23.4.0.24.05` |
| `scalardb-3.17.x.jar` | Maven Central | Yes: `com.scalar-labs:scalardb:3.17.1` |

**How to extract `aqapi.jar` from Oracle Docker container:**
```bash
# Copy from running container
docker cp oracle-db:/opt/oracle/product/23ai/dbhomeFree/rdbms/jlib/aqapi.jar ./libs/

# Or from Oracle installation directory
cp $ORACLE_HOME/rdbms/jlib/aqapi.jar ./libs/
```

**Gradle example (`build.gradle`):**
```groovy
dependencies {
    implementation fileTree(dir: 'libs', include: ['*.jar'])  // aqapi.jar
    implementation 'javax.jms:javax.jms-api:2.0.1'
    implementation 'com.oracle.database.jdbc:ojdbc11:23.4.0.24.05'
    implementation 'com.scalar-labs:scalardb:3.17.1'
    implementation 'org.slf4j:slf4j-simple:2.0.9'
}
```

---

## SQL Generation Patterns

### Pattern 1: Payload Type

Create one Oracle Object Type per distinct message schema. The payload carries all data the consumer needs.

**RDBMS (what to generate):**
```sql
CREATE OR REPLACE TYPE HR.hr_job_change_t AS OBJECT (
    employee_id    NUMBER(6),
    old_job_id     VARCHAR2(10),
    new_job_id     VARCHAR2(10),
    old_dept_id    NUMBER(4),
    new_dept_id    NUMBER(4),
    change_date    DATE,
    start_date     DATE,
    salary         NUMBER(8,2),
    operation_type VARCHAR2(20)    -- routing key: 'CLOSE_HISTORY', 'OPEN_HISTORY', etc.
);
/
```

**Rules:**
- Include ALL columns the consumer needs to write to the target table
- Include an `operation_type VARCHAR2(20)` field as the last attribute — this is the routing key the consumer uses to determine which handler to call
- Name convention: `<target_table>_change_t` (lowercase with underscores)
- Use Oracle types that match the source table columns

### Pattern 2: Queue Table + Queue

**RDBMS (what to generate):**
```sql
-- Clean up if re-running (idempotent)
BEGIN DBMS_AQADM.STOP_QUEUE('HR.hr_job_change_queue'); EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN DBMS_AQADM.DROP_QUEUE('HR.hr_job_change_queue'); EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN DBMS_AQADM.DROP_QUEUE_TABLE('HR.hr_job_change_qt', force => TRUE); EXCEPTION WHEN OTHERS THEN NULL; END;
/

-- Create queue table (stores messages on disk)
BEGIN
    DBMS_AQADM.CREATE_QUEUE_TABLE(
        queue_table        => 'HR.hr_job_change_qt',
        queue_payload_type => 'HR.HR_JOB_CHANGE_T'
    );
END;
/

-- Create queue (with retry settings)
BEGIN
    DBMS_AQADM.CREATE_QUEUE(
        queue_name  => 'HR.hr_job_change_queue',
        queue_table => 'HR.hr_job_change_qt',
        max_retries => 5,
        retry_delay => 0
    );
END;
/

-- Start queue and grant access
BEGIN DBMS_AQADM.START_QUEUE('HR.hr_job_change_queue'); END;
/
BEGIN
    DBMS_AQADM.GRANT_QUEUE_PRIVILEGE(
        privilege  => 'ALL',
        queue_name => 'HR.hr_job_change_queue',
        grantee    => 'HR'
    );
END;
/
```

**Rules:**
- Queue table name: `<target_table>_qt`
- Queue name: `<target_table>_queue`
- `max_retries => 5` — allows consumer 5 retry attempts before moving to exception queue
- `retry_delay => 0` — failed messages return to READY immediately
- Always include idempotent cleanup blocks at the top for re-runnability

### Pattern 3: Enqueue Stored Procedure

**Original SP (before):**
```sql
CREATE OR REPLACE PROCEDURE HR.ADD_JOB_HISTORY (
    p_emp_id IN NUMBER, p_start_date IN DATE, p_end_date IN DATE,
    p_job_id IN VARCHAR2, p_department_id IN NUMBER
) IS
BEGIN
    INSERT INTO job_history (employee_id, start_date, end_date, job_id, department_id)
    VALUES (p_emp_id, p_start_date, p_end_date, p_job_id, p_department_id);
END ADD_JOB_HISTORY;
```

**Converted SP (after — enqueues instead of INSERT):**
```sql
CREATE OR REPLACE PROCEDURE HR.SP_ENQUEUE_CLOSE_HISTORY (
    p_emp_id    IN NUMBER,
    p_start_dt  IN DATE,
    p_end_dt    IN DATE,
    p_old_job   IN VARCHAR2,
    p_new_job   IN VARCHAR2,
    p_old_dept  IN NUMBER,
    p_new_dept  IN NUMBER,
    p_salary    IN NUMBER
) AS
    l_enq_opts    DBMS_AQ.ENQUEUE_OPTIONS_T;
    l_msg_props   DBMS_AQ.MESSAGE_PROPERTIES_T;
    l_payload     hr_job_change_t;
    l_msgid       RAW(16);
BEGIN
    l_payload := hr_job_change_t(
        employee_id    => p_emp_id,
        old_job_id     => p_old_job,
        new_job_id     => p_new_job,
        old_dept_id    => NVL(p_old_dept, 0),
        new_dept_id    => NVL(p_new_dept, 0),
        change_date    => p_end_dt,
        start_date     => p_start_dt,
        salary         => NVL(p_salary, 0),
        operation_type => 'CLOSE_HISTORY'
    );

    l_enq_opts.visibility := DBMS_AQ.ON_COMMIT;

    DBMS_AQ.ENQUEUE(
        queue_name         => 'HR.hr_job_change_queue',
        enqueue_options    => l_enq_opts,
        message_properties => l_msg_props,
        payload            => l_payload,
        msgid              => l_msgid
    );
END SP_ENQUEUE_CLOSE_HISTORY;
/
```

**Rules:**
- Name convention: `SP_ENQUEUE_<OPERATION_NAME>`
- Accept all parameters needed to populate the payload type
- Use `NVL()` for nullable NUMBER fields to avoid Oracle STRUCT null issues
- Set `visibility := DBMS_AQ.ON_COMMIT` — messages are invisible until the enclosing transaction commits
- Set `operation_type` to a descriptive routing key the consumer will switch on

### Pattern 4: Trigger Conversion

**Original trigger (before):**
```sql
CREATE OR REPLACE TRIGGER HR.UPDATE_JOB_HISTORY
    AFTER UPDATE OF job_id, department_id ON HR.employees
    FOR EACH ROW
BEGIN
    add_job_history(:OLD.employee_id, :OLD.hire_date, SYSDATE,
                    :OLD.job_id, :OLD.department_id);
END;
```

**Converted triggers (after — no business logic, just call enqueue SPs):**
```sql
-- Disable original trigger
ALTER TRIGGER HR.UPDATE_JOB_HISTORY DISABLE;

-- New trigger for job_id changes
CREATE OR REPLACE TRIGGER HR.TRG_AQ_JOB_CHANGE
    AFTER UPDATE OF job_id ON HR.employees
    FOR EACH ROW
BEGIN
    SP_ENQUEUE_CLOSE_HISTORY(
        p_emp_id   => :OLD.employee_id,
        p_start_dt => :OLD.hire_date,
        p_end_dt   => SYSDATE,
        p_old_job  => :OLD.job_id,
        p_new_job  => :NEW.job_id,
        p_old_dept => :OLD.department_id,
        p_new_dept => :OLD.department_id,
        p_salary   => :OLD.salary
    );
END TRG_AQ_JOB_CHANGE;
/

-- New trigger for department_id changes
CREATE OR REPLACE TRIGGER HR.TRG_AQ_DEPT_CHANGE
    AFTER UPDATE OF department_id ON HR.employees
    FOR EACH ROW
BEGIN
    SP_ENQUEUE_OPEN_HISTORY(
        p_emp_id   => :NEW.employee_id,
        p_start_dt => SYSDATE,
        p_end_dt   => SYSDATE + 365,
        p_old_job  => :NEW.job_id,
        p_new_job  => :NEW.job_id,
        p_old_dept => :OLD.department_id,
        p_new_dept => :NEW.department_id,
        p_salary   => :NEW.salary
    );
END TRG_AQ_DEPT_CHANGE;
/
```

**Rules:**
- **Triggers contain NO business logic** — they only call the enqueue SP with `:OLD` and `:NEW` values
- Name convention: `TRG_AQ_<DESCRIPTIVE_NAME>`
- Original triggers are `DISABLE`d, not dropped (allows rollback)
- If the original trigger fires on multiple columns (e.g., `UPDATE OF job_id, department_id`), consider splitting into separate column-specific triggers with distinct `operation_type` values
- Use `:OLD.*` for values that represent the state before the change
- Use `:NEW.*` for values that represent the state after the change

---

## Java Consumer Patterns

### Pattern 5: AqStructHolder (Utility)

Required because `oracle.sql.STRUCT` does not implement `ORAData` directly in ojdbc11:

```java
package com.example.scalardb.aq;

import oracle.sql.Datum;
import oracle.sql.ORAData;
import oracle.sql.STRUCT;

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

### Pattern 6: Message POJO

Maps Oracle Object Type attributes by **positional index** (matching the `CREATE TYPE` definition order):

```java
package com.example.scalardb.aq;

import java.time.LocalDate;

public class JobHistoryChangeMessage {
    private int employeeId;        // [0] employee_id
    private String oldJobId;       // [1] old_job_id
    private String newJobId;       // [2] new_job_id
    private int oldDeptId;         // [3] old_dept_id
    private int newDeptId;         // [4] new_dept_id
    private LocalDate changeDate;  // [5] change_date
    private LocalDate startDate;   // [6] start_date
    private double salary;         // [7] salary
    private String operationType;  // [8] operation_type

    // Getters and setters
    public int getEmployeeId() { return employeeId; }
    public void setEmployeeId(int employeeId) { this.employeeId = employeeId; }
    // ... all other getters/setters ...
}
```

**Parsing from Oracle STRUCT:**
```java
public static JobHistoryChangeMessage parseMessage(Message jmsMessage) throws Exception {
    var adtMsg = (AQjmsAdtMessage) jmsMessage;
    var holder = (AqStructHolder) adtMsg.getAdtPayload();
    Object[] attrs = holder.asStruct().getAttributes();

    var msg = new JobHistoryChangeMessage();
    msg.setEmployeeId(((BigDecimal) attrs[0]).intValue());
    msg.setOldJobId((String) attrs[1]);
    msg.setNewJobId((String) attrs[2]);
    msg.setOldDeptId(((BigDecimal) attrs[3]).intValue());
    msg.setNewDeptId(((BigDecimal) attrs[4]).intValue());
    msg.setChangeDate(toLocalDate(attrs[5]));
    msg.setStartDate(toLocalDate(attrs[6]));
    msg.setSalary(((BigDecimal) attrs[7]).doubleValue());
    msg.setOperationType((String) attrs[8]);
    return msg;
}

private static LocalDate toLocalDate(Object oracleDate) {
    if (oracleDate == null) return null;
    if (oracleDate instanceof java.sql.Timestamp ts) return ts.toLocalDateTime().toLocalDate();
    if (oracleDate instanceof java.sql.Date d) return d.toLocalDate();
    return LocalDate.parse(oracleDate.toString());
}
```

**Type mapping for STRUCT attribute parsing:**

| Oracle Type in Object | Java Cast from `attrs[N]` |
|----------------------|--------------------------|
| NUMBER(p) | `((BigDecimal) attrs[N]).intValue()` or `.longValue()` |
| NUMBER(p,s) | `((BigDecimal) attrs[N]).doubleValue()` |
| VARCHAR2 | `(String) attrs[N]` |
| DATE | `toLocalDate(attrs[N])` — see helper above |
| TIMESTAMP | `((java.sql.Timestamp) attrs[N]).toLocalDateTime()` |

### Pattern 7: Consumer Service with ScalarDB

The consumer processes messages and writes to ScalarDB-managed tables:

```java
package com.example.scalardb.aq;

import com.scalar.db.api.*;
import com.scalar.db.io.Key;
import com.scalar.db.exception.transaction.*;

public class JobHistoryQueueConsumer {

    private static final String NAMESPACE = "hr";

    private final DistributedTransactionManager txManager;

    public JobHistoryQueueConsumer(DistributedTransactionManager txManager) {
        this.txManager = txManager;
    }

    public void processMessage(JobHistoryChangeMessage message) throws TransactionException {
        switch (message.getOperationType()) {
            case "CLOSE_HISTORY" -> handleCloseHistory(message);
            case "OPEN_HISTORY"  -> handleOpenHistory(message);
            default -> throw new IllegalArgumentException(
                "Unknown operation: " + message.getOperationType());
        }
    }

    private void handleCloseHistory(JobHistoryChangeMessage msg) throws TransactionException {
        DistributedTransaction tx = txManager.begin();
        try {
            var upsert = Upsert.newBuilder()
                .namespace(NAMESPACE)
                .table("JOB_HISTORY")
                .partitionKey(Key.ofInt("EMPLOYEE_ID", msg.getEmployeeId()))
                .clusteringKey(Key.ofDate("START_DATE", msg.getStartDate()))
                .dateValue("END_DATE", msg.getChangeDate())
                .textValue("JOB_ID", msg.getOldJobId())
                .intValue("DEPARTMENT_ID", msg.getOldDeptId())
                .build();
            tx.upsert(upsert);
            tx.commit();
        } catch (Exception e) {
            tx.abort();
            throw e;
        }
    }

    private void handleOpenHistory(JobHistoryChangeMessage msg) throws TransactionException {
        DistributedTransaction tx = txManager.begin();
        try {
            var upsert = Upsert.newBuilder()
                .namespace(NAMESPACE)
                .table("JOB_HISTORY")
                .partitionKey(Key.ofInt("EMPLOYEE_ID", msg.getEmployeeId()))
                .clusteringKey(Key.ofDate("START_DATE", msg.getStartDate()))
                .dateValue("END_DATE", msg.getChangeDate())
                .textValue("JOB_ID", msg.getNewJobId())
                .intValue("DEPARTMENT_ID", msg.getNewDeptId())
                .build();
            tx.upsert(upsert);
            tx.commit();
        } catch (Exception e) {
            tx.abort();
            throw e;
        }
    }
}
```

---

## The Dual-Transaction Pattern

The consumer uses **two independent transactions** per message:

```
1. ScalarDB transaction:  tx.commit()     → writes data to ScalarDB-managed table
2. AQ JMS transaction:    session.commit() → removes message from queue permanently
```

**Failure scenarios:**

| Scenario | ScalarDB | AQ Session | Result |
|----------|----------|-----------|--------|
| Both succeed | Committed | Committed | Normal — data written, message removed |
| ScalarDB fails | Rolled back | Rolled back | AQ redelivers (retry_count++) |
| JVM crashes after ScalarDB commit, before session commit | Committed | Not committed | AQ redelivers — Upsert overwrites with same data (idempotent) |
| session.rollback() after ScalarDB commit | Committed | Rolled back | AQ redelivers — Upsert handles it |

**Key insight:** Using `Upsert` instead of `Insert` makes the consumer idempotent. On redelivery, the same data is written again without error. This is recommended but not mandatory.

---

## Verification Queries

Include these in the generated SQL file for the user to verify the AQ setup:

```sql
-- Verify queue is running
SELECT name, queue_table, max_retries, retry_delay
FROM dba_queues
WHERE owner = '<SCHEMA>' AND queue_type = 'NORMAL_QUEUE';

-- Check messages in queue
SELECT RAWTOHEX(MSG_ID) AS msg_id, ENQ_TIME, MSG_STATE, RETRY_COUNT,
       t.user_data.operation_type AS op_type
FROM   aq$<queue_table> t
WHERE  MSG_STATE IN ('WAITING', 'READY')
ORDER  BY ENQ_TIME;

-- Check exception queue (dead letters)
SELECT RAWTOHEX(MSG_ID), ENQ_TIME, RETRY_COUNT, MSG_STATE
FROM   aq$<queue_table> t
WHERE  QUEUE LIKE '%_E';

-- Verify trigger status
SELECT trigger_name, status, triggering_event, table_name
FROM   all_triggers
WHERE  owner = '<SCHEMA>'
ORDER  BY trigger_name;
```

---

## Queue Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `max_retries` | 5 | Number of delivery attempts before moving to exception queue |
| `retry_delay` | 0 | Seconds to wait before retrying a failed message (0 = immediate) |
| `message_grouping` | NONE | Set to `DBMS_AQADM.TRANSACTIONAL` for atomic message groups |
| `visibility` | `ON_COMMIT` | Messages invisible until producer COMMIT |

---

*Strategy Guide Version: 1.0*
*Based on: Oracle AQ (DBMS_AQ / DBMS_AQADM) + ScalarDB 3.17 Java Transaction API*
