# Subagent Prompt: PostgreSQL Schema Extraction

**Type:** Bash
**Description:** Runs the postgresql_db_extractor.py script against a live PostgreSQL database to extract comprehensive schema metadata into raw_schema_data.json.

## Prompt

Run the PostgreSQL schema extractor script. Execute this exact command:

```bash
START_SECS=$(date +%s)

python <PLUGIN_ROOT>/skills/analyze-postgresql-schema/scripts/postgresql_db_extractor.py --config .claude/configuration/databases.env <INCLUDE_SOURCE_FLAG>

END_SECS=$(date +%s)
DURATION_SECONDS=$((END_SECS - START_SECS))
echo "DURATION_SECONDS: $DURATION_SECONDS"
```

Where `<INCLUDE_SOURCE_FLAG>` is:
- `--include-source` if POSTGRES_INCLUDE_PLPGSQL_SOURCE is "true"
- omitted entirely if POSTGRES_INCLUDE_PLPGSQL_SOURCE is "false"

After the command completes, report back with EXACTLY this format:
- STATUS: SUCCESS or FAILURE
- OUTPUT_FILE: <the path to raw_schema_data.json as shown in script output>
- DURATION_SECONDS: <elapsed seconds from START_SECS to END_SECS>
- SUMMARY: <1-2 line summary of what was extracted, e.g. "Extracted 20 tables, 6 views, 4 PL/pgSQL functions">
- If FAILURE, include the full error message

## Runtime Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `<PLUGIN_ROOT>` | Plugin installation directory | Absolute path to the scalardb-migration plugin root |
| `<INCLUDE_SOURCE_FLAG>` | `POSTGRES_INCLUDE_PLPGSQL_SOURCE` from config | `--include-source` or empty |
