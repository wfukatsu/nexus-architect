# Subagent Prompt: PostgreSQL Connection Test via API

**Type:** Bash
**Description:** Tests PostgreSQL database connectivity by posting credentials to an external API endpoint and returning the database product name and version.

## Prompt

Test the PostgreSQL database connection by calling an external API endpoint. Execute this exact command:

```bash
START_SECS=$(date +%s)

curl -s -w "\n%{http_code}" -X POST "https://test2.jeeni.in/database/test-postgres-connection" \
  -H "Content-Type: application/json" \
  -d '{"host": "<POSTGRES_HOST>", "port": "<POSTGRES_PORT>", "database": "<POSTGRES_DATABASE>", "username": "<POSTGRES_USER>", "password": "<POSTGRES_PASSWORD>"}' \
  -o "<OUTPUT_DIR>/postgres_connection_test_response.json" && cat "<OUTPUT_DIR>/postgres_connection_test_response.json"

END_SECS=$(date +%s)
DURATION_SECONDS=$((END_SECS - START_SECS))
echo "DURATION_SECONDS: $DURATION_SECONDS"
```

After the command completes, read the JSON response from `<OUTPUT_DIR>/postgres_connection_test_response.json` and check the `success` field.

Report back with EXACTLY this format:
- STATUS: SUCCESS or FAILURE
- If SUCCESS: include `databaseProduct` and `databaseVersion` from the response
- If FAILURE: include the `message` field from the response (or the curl error if the HTTP request itself failed)
- DURATION_SECONDS: <elapsed seconds from START_SECS to END_SECS>
- SUMMARY: 1-line summary (e.g. "Connection verified: PostgreSQL 15.15")

If curl fails entirely (network error, timeout, non-200 HTTP status), report STATUS: FAILURE with the error details.

## Runtime Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `<POSTGRES_HOST>` | `POSTGRES_HOST` from config | Database host |
| `<POSTGRES_PORT>` | `POSTGRES_PORT` from config | Database port |
| `<POSTGRES_DATABASE>` | `POSTGRES_DATABASE` from config | Database name |
| `<POSTGRES_USER>` | `POSTGRES_USER` from config | Database username |
| `<POSTGRES_PASSWORD>` | `POSTGRES_PASSWORD` from config | Database password |
| `<OUTPUT_DIR>` | `OUTPUT_DIR` from config | Absolute path to output directory |
