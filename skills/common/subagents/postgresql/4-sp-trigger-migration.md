# Subagent Prompt: PostgreSQL Stored Procedure & Trigger Migration

**Type:** general-purpose
**Description:** Reads PL/pgSQL definitions from raw_schema_data.json and generates equivalent ScalarDB Java application code (Transaction API only) for functions, procedures, triggers, and trigger functions, with a summary migration report.

## Prompt

You are generating ScalarDB Java application code from PostgreSQL PL/pgSQL functions, procedures, triggers, and trigger functions. Follow these steps:

0. Record start time using Bash: `START_SECS=$(date +%s)`
1. Read the SP/trigger migration skill instructions at: <PLUGIN_ROOT>/skills/migrate-postgresql-sp-trigger-to-scalardb/SKILL.md
2. Read the migration strategy guide (reference doc with all 17 feature mappings and code examples) at: <PLUGIN_ROOT>/skills/migrate-postgresql-sp-trigger-to-scalardb/reference/migration-strategy-guide-sp-triggers-to-scalardb.md
3. Read the report template at: <PLUGIN_ROOT>/skills/migrate-postgresql-sp-trigger-to-scalardb/templates/scalardb_sp_migration_report.md
4. Read the extracted schema data at: <OUTPUT_DIR>/raw_schema_data.json — focus on the `plpgsql` section (functions, procedures, triggers, trigger_functions, function_arguments, function_source)
5. Read the schema report at: <OUTPUT_DIR>/postgresql_schema_report.md — use this for table/column context needed to generate accurate Key builders and namespace values
6. Create the output directory: `<OUTPUT_DIR>/generated-java/` (use Bash: `mkdir -p <OUTPUT_DIR>/generated-java/`)
7. For each function, procedure, trigger, and trigger function found in the JSON:
   a. Classify which of the 17 feature categories it uses
   b. Classify its SP type (Simple CRUD, Business Logic, Multi-table, Cursor/Batch, Aggregation, Subquery-based)
   c. Generate a Java service class using the ScalarDB Java Transaction API exclusively (no JDBC approach)
   d. Write the file to: `<OUTPUT_DIR>/generated-java/<ObjectName>Service.java`
8. Write the summary report to: <OUTPUT_DIR>/scalardb_sp_migration_report.md using the template
9. Record end time and compute duration using Bash: `END_SECS=$(date +%s) && echo $((END_SECS - START_SECS))`

**Important rules:**
- If the `plpgsql` section has no functions, procedures, triggers, or trigger functions, report STATUS: SUCCESS with 0 files generated
- Use the schema report to determine correct Key types (Key.ofText, Key.ofInt, Key.ofBigInt, etc.) based on actual column data types
- Use the POSTGRES_SCHEMA or POSTGRES_DATABASE (lowercase) as the ScalarDB namespace
- Every generated Java class must use the ScalarDB Java Transaction API exclusively (no JDBC)
- Follow the exception handling patterns from the migration strategy guide
- PascalCase the PostgreSQL object names for Java class names (e.g., calculate_order_total → CalculateOrderTotalService)
- PostgreSQL does not have packages — generate files for functions, procedures, trigger functions, and triggers
- Trigger functions are separate entities (functions returning TRIGGER type) — generate a service class for each
- **Target Java 17**: Use Java 17 language features where they improve clarity — `var` for local type inference, records for result/value objects, `instanceof` pattern matching, switch expressions, text blocks (`"""`), `List.of()` / `Map.of()`, and `String.formatted()`. Do NOT use preview features or Java 21+ features.

After completion, report back with EXACTLY this format:
- STATUS: SUCCESS or FAILURE
- REPORT_FILE: <OUTPUT_DIR>/scalardb_sp_migration_report.md
- JAVA_DIR: <OUTPUT_DIR>/generated-java/
- FILES_GENERATED: <count> Java files
- DURATION_SECONDS: <elapsed seconds computed in step 9>
- SUMMARY: <2-3 lines: function count, procedure count, trigger count, trigger function count, feature categories found, overall complexity>
- If FAILURE, include the error details

## Runtime Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `<PLUGIN_ROOT>` | Plugin installation directory | Absolute path to the scalardb-migration plugin root |
| `<OUTPUT_DIR>` | `OUTPUT_DIR` from config | Absolute path to output directory |
