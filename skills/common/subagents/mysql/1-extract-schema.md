# Subagent Prompt: MySQL Schema Extraction

**Type:** Bash
**Description:** Runs the mysql_db_extractor.py script against a live MySQL database to extract comprehensive schema metadata into raw_mysql_schema_data.json.

## Prompt

Run the MySQL schema extractor script. Execute this exact command:

```bash
START_SECS=$(date +%s)

python <PLUGIN_ROOT>/skills/analyze-mysql-schema/scripts/mysql_db_extractor.py --config .claude/configuration/databases.env <INCLUDE_SOURCE_FLAG>

END_SECS=$(date +%s)
DURATION_SECONDS=$((END_SECS - START_SECS))
echo "DURATION_SECONDS: $DURATION_SECONDS"
```

Where `<INCLUDE_SOURCE_FLAG>` is:
- `--include-source` if MYSQL_INCLUDE_SOURCE is "true"
- omitted entirely if MYSQL_INCLUDE_SOURCE is "false"

After the command completes, report back with EXACTLY this format:
- STATUS: SUCCESS or FAILURE
- OUTPUT_FILE: <the path to raw_mysql_schema_data.json as shown in script output>
- DURATION_SECONDS: <elapsed seconds from START_SECS to END_SECS>
- SUMMARY: <1-2 line summary of what was extracted, e.g. "Extracted 12 tables, 5 views, 3 stored procedures">
- If FAILURE, include the full error message

## Runtime Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `<PLUGIN_ROOT>` | Plugin installation directory | Absolute path to the scalardb-migration plugin root |
| `<INCLUDE_SOURCE_FLAG>` | `MYSQL_INCLUDE_SOURCE` from config | `--include-source` or empty |
