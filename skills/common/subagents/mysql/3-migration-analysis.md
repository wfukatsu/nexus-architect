# Subagent Prompt: MySQL Migration Analysis

**Type:** general-purpose
**Description:** Reads the MySQL schema report and ScalarDB reference docs, then generates scalardb_mysql_migration_analysis.md and scalardb_mysql_migration_steps.md with compatibility analysis and a step-by-step migration guide.

## Prompt

You are generating ScalarDB migration documentation from a MySQL schema report. Follow these steps:

0. Record start time using Bash: `START_SECS=$(date +%s)`
1. Read the migration skill instructions at: <PLUGIN_ROOT>/skills/migrate-mysql-to-scalardb/SKILL.md
2. Read the ScalarDB reference documentation at: <PLUGIN_ROOT>/skills/migrate-mysql-to-scalardb/reference/scalardb_mysql_reference.md
3. Read the migration analysis template at: <PLUGIN_ROOT>/skills/migrate-mysql-to-scalardb/templates/scalardb_mysql_migration_analysis.md
4. Read the migration steps template at: <PLUGIN_ROOT>/skills/migrate-mysql-to-scalardb/templates/scalardb_mysql_migration_steps.md
5. Read the schema report at: <OUTPUT_DIR>/mysql_schema_report.md
6. Following the SKILL.md instructions, templates, and reference docs, generate both migration documents.
7. Write the migration analysis to: <OUTPUT_DIR>/scalardb_mysql_migration_analysis.md
8. Write the migration steps to: <OUTPUT_DIR>/scalardb_mysql_migration_steps.md
9. Record end time and compute duration using Bash: `END_SECS=$(date +%s) && echo $((END_SECS - START_SECS))`

After completion, report back with EXACTLY this format:
- STATUS: SUCCESS or FAILURE
- FILES_WRITTEN: scalardb_mysql_migration_analysis.md, scalardb_mysql_migration_steps.md
- COMPLEXITY_SCORE: <the calculated migration complexity score, e.g. "65/100 - Moderate">
- DURATION_SECONDS: <elapsed seconds computed in step 9>
- SUMMARY: <2-3 line summary of key migration findings — number of compatible types, unsupported features requiring workarounds, critical items>
- If FAILURE, include the error details

## Runtime Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `<PLUGIN_ROOT>` | Plugin installation directory | Absolute path to the scalardb-migration plugin root |
| `<OUTPUT_DIR>` | `OUTPUT_DIR` from config | Absolute path to output directory |
