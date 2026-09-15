"""MySQL: server SELECT deadline plus finite socket I/O deadlines."""
from core.connection import Port


def configure(conn, seconds):
    with conn.cursor() as cur:
        cur.execute("SET SESSION MAX_EXECUTION_TIME = %s", (seconds * 1000,))


def connect(config):
    import pymysql
    if not config["plaintext"] and not config.get("tls_ca"):
        raise ValueError("MySQL requires a TLS CA environment reference")
    conn = pymysql.connect(
        host=config["host"], port=config["port"], database=config["database"], user=config["user"],
        password=config.get("password", ""), connect_timeout=10, read_timeout=20, write_timeout=20,
        autocommit=True, local_infile=False, ssl_ca=config.get("tls_ca"),
        ssl_verify_cert=not config["plaintext"], ssl_verify_identity=not config["plaintext"],
        cursorclass=pymysql.cursors.SSCursor,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SET SESSION TRANSACTION READ ONLY")
    except Exception:
        conn.close()
        raise
    return Port(conn, configure, lambda schema: (schema,))
