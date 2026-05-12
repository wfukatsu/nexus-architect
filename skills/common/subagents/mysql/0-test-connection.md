# Subagent Prompt: MySQL Connection Test

**Type:** Bash
**Description:** Tests MySQL database connectivity directly using Python and mysql-connector-python, returning the database product name and version.

## Prompt

Test the MySQL database connection by running a Python connectivity check. Execute this exact command:

```bash
START_SECS=$(date +%s)

python3 - <<'PYEOF'
import sys
try:
    import mysql.connector
    conn = mysql.connector.connect(
        host="<MYSQL_HOST>",
        port=<MYSQL_PORT>,
        database="<MYSQL_DATABASE>",
        user="<MYSQL_USER>",
        password="<MYSQL_PASSWORD>",
        connection_timeout=10
    )
    cursor = conn.cursor()
    cursor.execute("SELECT VERSION()")
    version = cursor.fetchone()[0]
    cursor.execute("SELECT DATABASE()")
    db = cursor.fetchone()[0]
    conn.close()
    print(f"SUCCESS|MySQL|{version}")
except ImportError:
    print("FAILURE|mysql-connector-python not installed. Run: pip3 install mysql-connector-python")
    sys.exit(1)
except mysql.connector.Error as e:
    print(f"FAILURE|{e}")
    sys.exit(1)
PYEOF

END_SECS=$(date +%s)
DURATION_SECONDS=$((END_SECS - START_SECS))
echo "DURATION_SECONDS: $DURATION_SECONDS"
```

Parse the output line starting with `SUCCESS|` or `FAILURE|`.

Report back with EXACTLY this format:
- STATUS: SUCCESS or FAILURE
- If SUCCESS: include `databaseProduct` (MySQL) and `databaseVersion` from the response
- If FAILURE: include the error message
- DURATION_SECONDS: <elapsed seconds from START_SECS to END_SECS>
- SUMMARY: 1-line summary (e.g. "Connection verified: MySQL 8.0.32")

## Runtime Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `<MYSQL_HOST>` | `MYSQL_HOST` from config | Database host |
| `<MYSQL_PORT>` | `MYSQL_PORT` from config | Database port |
| `<MYSQL_DATABASE>` | `MYSQL_DATABASE` from config | Database name |
| `<MYSQL_USER>` | `MYSQL_USER` from config | Database username |
| `<MYSQL_PASSWORD>` | `MYSQL_PASSWORD` from config | Database password |
