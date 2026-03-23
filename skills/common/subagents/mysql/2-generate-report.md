# Subagent Prompt: MySQL Schema Report Generation

**Type:** general-purpose
**Description:** Reads raw_mysql_schema_data.json and the report template, then generates mysql_schema_report.md with a complete human-readable schema analysis.

## Prompt

You are generating a MySQL schema analysis report. Follow these steps:

0. Record start time using Bash: `START_SECS=$(date +%s)`
1. Read the skill instructions at: <PLUGIN_ROOT>/skills/analyze-mysql-schema/SKILL.md
2. Read the report template at: <PLUGIN_ROOT>/skills/analyze-mysql-schema/analyze-mysql-dbms_report.md
3. Read the extracted JSON data at: <OUTPUT_DIR>/raw_mysql_schema_data.json
4. Following the SKILL.md instructions and the report template structure exactly, generate the complete schema report.
5. Write the report to: <OUTPUT_DIR>/mysql_schema_report.md
6. Record end time and compute duration using Bash: `END_SECS=$(date +%s) && echo $((END_SECS - START_SECS))`

Rules:
- Follow the template structure exactly
- Use the JSON field references indicated in each section
- Skip sections entirely if no data exists (no empty tables, no "N/A")
- Calculate summary metrics for the Executive Summary from actual data
- This is a pure schema report — do NOT add migration commentary or compatibility assessments

After completion, report back with EXACTLY this format:
- STATUS: SUCCESS or FAILURE
- REPORT_FILE: <OUTPUT_DIR>/mysql_schema_report.md
- DURATION_SECONDS: <elapsed seconds computed in step 6>
- SUMMARY: <executive summary — table count, view count, stored procedure count, total objects, key observations in 2-3 lines>
- If FAILURE, include the error details

## Runtime Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `<PLUGIN_ROOT>` | Plugin installation directory | Absolute path to the scalardb-migration plugin root |
| `<OUTPUT_DIR>` | `OUTPUT_DIR` from config | Absolute path to output directory |
