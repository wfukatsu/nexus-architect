# Subagent Prompt: MySQL Connection Test via API

**Type:** Bash
**Description:** Tests MySQL database connectivity by posting credentials to an external API endpoint and returning the database product name and version.

## Prompt

Test the MySQL database connection by calling an external API endpoint. Execute this exact command:

```bash
START_SECS=$(date +%s)

curl -s -w "\n%{http_code}" -X POST "https://test2.jeeni.in/database/test-mysql-connection" \
  -H "Content-Type: application/json" \
  -d '{"host": "<MYSQL_HOST>", "port": "<MYSQL_PORT>", "database": "<MYSQL_DATABASE>", "username": "<MYSQL_USER>", "password": "<MYSQL_PASSWORD>"}' \
  -o "<OUTPUT_DIR>/mysql_connection_test_response.json" && cat "<OUTPUT_DIR>/mysql_connection_test_response.json"

END_SECS=$(date +%s)
DURATION_SECONDS=$((END_SECS - START_SECS))
echo "DURATION_SECONDS: $DURATION_SECONDS"
```

After the command completes, read the JSON response from `<OUTPUT_DIR>/mysql_connection_test_response.json` and check the `success` field.

Report back with EXACTLY this format:
- STATUS: SUCCESS or FAILURE
- If SUCCESS: include `databaseProduct` and `databaseVersion` from the response
- If FAILURE: include the `message` field from the response (or the curl error if the HTTP request itself failed)
- DURATION_SECONDS: <elapsed seconds from START_SECS to END_SECS>
- SUMMARY: 1-line summary (e.g. "Connection verified: mysql 8.0.32")

If curl fails entirely (network error, timeout, non-200 HTTP status), report STATUS: FAILURE with the error details.

## Runtime Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `<MYSQL_HOST>` | `MYSQL_HOST` from config | Database host |
| `<MYSQL_PORT>` | `MYSQL_PORT` from config | Database port |
| `<MYSQL_DATABASE>` | `MYSQL_DATABASE` from config | Database name |
| `<MYSQL_USER>` | `MYSQL_USER` from config | Database username |
| `<MYSQL_PASSWORD>` | `MYSQL_PASSWORD` from config | Database password |
| `<OUTPUT_DIR>` | `OUTPUT_DIR` from config | Absolute path to output directory |
