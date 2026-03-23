# Subagent Prompt: Oracle Connection Test via SQL*Plus

**Type:** Bash
**Description:** Tests Oracle database connectivity directly using SQL*Plus. Returns the database version on success, or a clear error message on failure.

## Prompt

Test the Oracle database connection using SQL*Plus. Execute these steps in order:

```bash
START_SECS=$(date +%s)

# Step 1: Determine SQL*Plus binary
SQLPLUS_BIN="<ORACLE_SQLPLUS_PATH>"
if [ -z "$SQLPLUS_BIN" ]; then
  SQLPLUS_BIN=$(which sqlplus 2>/dev/null)
fi

# Step 2: Verify SQL*Plus is available
if [ -z "$SQLPLUS_BIN" ] || [ ! -f "$SQLPLUS_BIN" ]; then
  echo '{"success": false, "message": "SQL*Plus not found. Please install SQL*Plus or set ORACLE_SQLPLUS_PATH in .claude/configuration/databases.env"}' > "<OUTPUT_DIR>/connection_test_response.json"
  END_SECS=$(date +%s)
  echo "DURATION_SECONDS: $((END_SECS - START_SECS))"
  echo "SQLPLUS_NOT_FOUND"
  exit 0
fi

# Step 3: Run connection test — connect and fetch Oracle version banner
SQLPLUS_OUTPUT=$("$SQLPLUS_BIN" -S /nolog 2>&1 <<EOF
CONNECT <ORACLE_USER>/<ORACLE_PASSWORD>@<ORACLE_HOST>:<ORACLE_PORT>/<ORACLE_SERVICE>
SET PAGESIZE 0 FEEDBACK OFF VERIFY OFF HEADING OFF ECHO OFF TRIMOUT ON
SELECT banner FROM v\$version WHERE ROWNUM = 1;
EXIT;
EOF
)

END_SECS=$(date +%s)
echo "DURATION_SECONDS: $((END_SECS - START_SECS))"
echo "$SQLPLUS_OUTPUT"
```

After the commands complete, inspect the output and determine the result:

**SUCCESS** — output contains an Oracle version banner (e.g. `Oracle Database 19c ...`):
- Write result to `<OUTPUT_DIR>/connection_test_response.json`:
  ```json
  {"success": true, "databaseVersion": "<the full banner line>"}
  ```

**FAILURE: SQL*Plus not found** — output contains `SQLPLUS_NOT_FOUND`:
- Write result to `<OUTPUT_DIR>/connection_test_response.json`:
  ```json
  {"success": false, "message": "SQL*Plus not found. Please install SQL*Plus or set ORACLE_SQLPLUS_PATH in .claude/configuration/databases.env"}
  ```

**FAILURE: ORA- error** — output contains an `ORA-` error code:
- Write result to `<OUTPUT_DIR>/connection_test_response.json`:
  ```json
  {"success": false, "message": "<the full ORA- error line>"}
  ```

**FAILURE: other** — any other unexpected output:
- Write result to `<OUTPUT_DIR>/connection_test_response.json`:
  ```json
  {"success": false, "message": "<the raw output>"}
  ```

Report back with EXACTLY this format:
- STATUS: SUCCESS or FAILURE
- If SUCCESS: include the Oracle version banner line
- If FAILURE: include the exact error message (ORA- code, or SQL*Plus not found message)
- DURATION_SECONDS: <elapsed seconds>
- SUMMARY: 1-line summary (e.g. "Connection verified: Oracle Database 19c Enterprise Edition" or "Connection failed: ORA-12541: no listener")

## Runtime Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `<ORACLE_HOST>` | `ORACLE_HOST` from config | Database host |
| `<ORACLE_PORT>` | `ORACLE_PORT` from config | Listener port |
| `<ORACLE_SERVICE>` | `ORACLE_SERVICE` from config | Service name or SID |
| `<ORACLE_USER>` | `ORACLE_USER` from config | Database username |
| `<ORACLE_PASSWORD>` | `ORACLE_PASSWORD` from config | Database password |
| `<ORACLE_SQLPLUS_PATH>` | `ORACLE_SQLPLUS_PATH` from config | Absolute path to sqlplus binary (empty = use PATH) |
| `<OUTPUT_DIR>` | `OUTPUT_DIR` from config | Absolute path to output directory |
