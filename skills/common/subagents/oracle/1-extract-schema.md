# Subagent Prompt: Oracle Schema Extraction

**Type:** Bash
**Description:** Runs the oracle_db_extractor.py script against a live Oracle database to extract comprehensive schema metadata into raw_schema_data.json.

## Prompt

Run the Oracle schema extractor script. Execute these commands in order:

```bash
START_SECS=$(date +%s)

python <PLUGIN_ROOT>/skills/analyze-oracle-schema/scripts/oracle_db_extractor.py --config .claude/configuration/databases.env <INCLUDE_SOURCE_FLAG>

END_SECS=$(date +%s)
DURATION_SECONDS=$((END_SECS - START_SECS))
echo "DURATION_SECONDS: $DURATION_SECONDS"
```

Where `<INCLUDE_SOURCE_FLAG>` is:
- `--include-source` if ORACLE_INCLUDE_PLSQL_SOURCE is "true"
- omitted entirely if ORACLE_INCLUDE_PLSQL_SOURCE is "false"

After the command completes, report back with EXACTLY this format:
- STATUS: SUCCESS or FAILURE
- OUTPUT_FILE: <the path to raw_schema_data.json as shown in script output>
- DURATION_SECONDS: <elapsed seconds from START_SECS to END_SECS>
- SUMMARY: <1-2 line summary of what was extracted, e.g. "Extracted 15 tables, 8 views, 3 PL/SQL objects">
- If FAILURE, include the full error message

## Runtime Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `<PLUGIN_ROOT>` | Plugin installation directory | Absolute path to the scalardb-migration plugin root |
| `<INCLUDE_SOURCE_FLAG>` | `ORACLE_INCLUDE_PLSQL_SOURCE` from config | `--include-source` or empty |
