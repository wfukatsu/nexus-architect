# Subagent Prompt: Oracle AQ Migration

**Type:** general-purpose
**Description:** Analyzes PL/SQL triggers and stored procedures from raw_schema_data.json, generates Oracle AQ setup SQL (payload types, queues, enqueue triggers/SPs) and Java consumer files that dequeue messages and process them using the ScalarDB Java Transaction API, with an AQ migration report.

## Prompt

You are generating Oracle AQ setup SQL and Java consumer code from Oracle PL/SQL triggers and stored procedures. Follow these steps:

0. Record start time using Bash: `START_SECS=$(date +%s)`
1. Read the AQ migration skill instructions at: <PLUGIN_ROOT>/skills/migrate-oracle-aq-to-scalardb/SKILL.md
2. Read the AQ migration strategy guide (reference doc with SQL and Java patterns) at: <PLUGIN_ROOT>/skills/migrate-oracle-aq-to-scalardb/reference/aq-migration-strategy-guide.md
3. Read the exception handling strategy (exception classification for consumer retry/commit decisions) at: <PLUGIN_ROOT>/skills/migrate-oracle-aq-to-scalardb/reference/aq-exception-handling-strategy.md
4. Read the report template at: <PLUGIN_ROOT>/skills/migrate-oracle-aq-to-scalardb/templates/scalardb_aq_migration_report.md
5. Read the extracted schema data at: <OUTPUT_DIR>/raw_schema_data.json — focus on the `plsql` section (procedures, functions, triggers, source, DDL)
6. Read the schema report at: <OUTPUT_DIR>/oracle_schema_report.md — use this for table/column context needed to generate accurate Key builders and namespace values
7. Ensure the output directory exists: `mkdir -p <OUTPUT_DIR>/generated-java/`
8. Analyze each trigger and stored procedure to determine which should be converted to AQ:
   - Triggers that perform DML on other tables → convert to AQ
   - SPs that perform INSERT/UPDATE/DELETE → convert to AQ enqueue
   - Triggers that only call SPs → trigger calls enqueue SP, SP becomes enqueue SP
   - SPs with only SELECT/computation → skip (handled by Subagent 5)
9. For each group of related triggers/SPs targeting the same table:
   a. Design the payload type (include all columns the consumer needs + operation_type routing key)
   b. Generate queue table and queue configuration
   c. Generate enqueue stored procedures (one per operation type)
   d. Generate modified triggers (no business logic — just call enqueue SPs)
   e. Generate disable statements for original triggers
10. Write the complete SQL file to: <OUTPUT_DIR>/aq_setup.sql — organized in sections: payload types, queue tables, queues, disable original triggers, enqueue SPs, new AQ triggers, verification queries
11. For each queue, generate Java consumer files:
    a. Message POJO class (`<PayloadName>Message.java`) — one per payload type
    b. Consumer service class (`<QueueName>Consumer.java`) — with `processMessage()` and `parseMessage()` methods
    c. AqStructHolder utility (`AqStructHolder.java`) — generate once
    d. ExceptionClassifier utility (`ExceptionClassifier.java`) — generate once, classifies exceptions into RETRIABLE / NON_RETRIABLE / UNKNOWN_TX_STATE verdicts per aq-exception-handling-strategy.md
    e. Write all Java files to: `<OUTPUT_DIR>/generated-java/`
12. Write the AQ migration report to: <OUTPUT_DIR>/scalardb_aq_migration_report.md using the template
13. Record end time and compute duration using Bash: `END_SECS=$(date +%s) && echo $((END_SECS - START_SECS))`

**Important rules:**
- If the `plsql` section has no triggers or stored procedures that perform DML, report STATUS: SUCCESS with 0 conversions
- Use the schema report to determine correct Key types (Key.ofText, Key.ofInt, Key.ofBigInt, etc.) based on actual column data types
- Use the ORACLE_SCHEMA or ORACLE_USER value as-is for the ScalarDB namespace. Use table and column names exactly as they appear in raw_schema_data.json — do not convert to lowercase.
- Consumer Java classes MUST use the ScalarDB Java Transaction API exclusively (no JDBC)
- Use Upsert (recommended) for idempotent consumer writes — but note this is not mandatory
- Generated consumer code MUST use the ExceptionClassifier to determine whether to rollback (retriable) or commit (non-retriable poison message removal) the AQ session. Follow the classification rules in aq-exception-handling-strategy.md.
- The ScalarDbWriter MUST NOT call tx.abort() on UnknownTransactionStatusException — the TX may have committed successfully
- Do NOT split a single Oracle trigger into multiple AQ triggers. If the original trigger fires on UPDATE OF job_id, department_id (combined), create ONE replacement AQ trigger that fires on the same event. Keep the trigger design aligned with the original structure.
- Triggers MUST contain NO business logic — they only call enqueue SPs with :OLD/:NEW values
- All enqueue SPs MUST use `visibility := DBMS_AQ.ON_COMMIT`
- Include the `operation_type` field in every payload type as the last attribute
- PascalCase Oracle object names for Java class names
- **Target Java 17**: Use Java 17 language features where they improve clarity — `var`, records, `instanceof` pattern matching, switch expressions, text blocks, `List.of()`, `String.formatted()`. Do NOT use preview features or Java 21+ features.
- Include required dependency information in the report: `aqapi.jar` (from `$ORACLE_HOME/rdbms/jlib/`), `javax.jms-api-2.0.1.jar`, `ojdbc11`, `scalardb`
- Document in the report that the database must be imported into ScalarDB first before the consumer can work
- ALL Java files listed in the Generated File Index MUST actually be written to disk. Verify that every file referenced in the report exists in generated-java/.

After completion, report back with EXACTLY this format:
- STATUS: SUCCESS or FAILURE
- SQL_FILE: <OUTPUT_DIR>/aq_setup.sql
- REPORT_FILE: <OUTPUT_DIR>/scalardb_aq_migration_report.md
- JAVA_DIR: <OUTPUT_DIR>/generated-java/
- QUEUES_CREATED: <count> queues
- FILES_GENERATED: <count> Java files + 1 SQL file
- DURATION_SECONDS: <elapsed seconds computed in step 12>
- SUMMARY: <2-3 lines: triggers/SPs converted, queues created, consumer classes generated, overall complexity>
- If FAILURE, include the error details

## Runtime Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `<PLUGIN_ROOT>` | Plugin installation directory | Absolute path to the scalardb-migration plugin root |
| `<OUTPUT_DIR>` | `OUTPUT_DIR` from config | Absolute path to output directory |
