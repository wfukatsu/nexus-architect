# Subagent Prompt: PostgreSQL Connection Test

**Type:** Bash
**Description:** Tests PostgreSQL database connectivity directly using Python and psycopg2, returning the database product name and version.

## Prompt

Test the PostgreSQL database connection by running a Python connectivity check. Execute this exact command:

```bash
START_SECS=$(date +%s)

python3 - <<'PYEOF'
import sys
try:
    import psycopg2
    conn = psycopg2.connect(
        host="<POSTGRES_HOST>",
        port=<POSTGRES_PORT>,
        dbname="<POSTGRES_DATABASE>",
        user="<POSTGRES_USER>",
        password="<POSTGRES_PASSWORD>",
        connect_timeout=10
    )
    cursor = conn.cursor()
    cursor.execute("SELECT version()")
    version_str = cursor.fetchone()[0]
    # Extract short version e.g. "PostgreSQL 15.4"
    short_ver = " ".join(version_str.split()[:2])
    conn.close()
    print(f"SUCCESS|PostgreSQL|{short_ver}")
except ImportError:
    print("FAILURE|psycopg2 not installed. Run: pip3 install psycopg2-binary")
    sys.exit(1)
except psycopg2.Error as e:
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
- If SUCCESS: include `databaseProduct` (PostgreSQL) and `databaseVersion` from the response
- If FAILURE: include the error message
- DURATION_SECONDS: <elapsed seconds from START_SECS to END_SECS>
- SUMMARY: 1-line summary (e.g. "Connection verified: PostgreSQL 15.4")

## Runtime Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `<POSTGRES_HOST>` | `POSTGRES_HOST` from config | Database host |
| `<POSTGRES_PORT>` | `POSTGRES_PORT` from config | Database port |
| `<POSTGRES_DATABASE>` | `POSTGRES_DATABASE` from config | Database name |
| `<POSTGRES_USER>` | `POSTGRES_USER` from config | Database username |
| `<POSTGRES_PASSWORD>` | `POSTGRES_PASSWORD` from config | Database password |
