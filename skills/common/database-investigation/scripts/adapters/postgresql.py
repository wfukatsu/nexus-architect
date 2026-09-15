"""PostgreSQL: server statement deadline, verified TLS, read-only sessions."""
from core.connection import Port


def configure(conn, seconds):
    with conn.cursor() as cur:
        cur.execute("SELECT pg_catalog.set_config('statement_timeout', %s, false)", (str(seconds * 1000),))


def connect(config):
    import psycopg
    conn = psycopg.connect(
        host=config["host"], port=config["port"], dbname=config["database"], user=config["user"],
        password=config.get("password"), connect_timeout=10, autocommit=True,
        sslmode="disable" if config["plaintext"] else "verify-full",
        sslrootcert=config.get("tls_ca"), options="-c default_transaction_read_only=on -c statement_timeout=15000 -c lock_timeout=3000",
    )
    return Port(conn, configure, lambda schema: (schema,))
