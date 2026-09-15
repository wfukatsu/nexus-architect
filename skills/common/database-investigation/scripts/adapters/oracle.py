"""Oracle thin driver; call timeout includes server cancellation on supported servers."""
from core.connection import Port


def bound_query(sql, schema, limit):
    params = {"maxrows": limit + 1}
    if schema is not None:
        params["scope"] = schema
    # sql comes only from the repository registry; scope and row limit remain binds.
    return "SELECT * FROM (" + sql + ") WHERE ROWNUM <= :maxrows", params  # nosec B608


def configure(conn, seconds):
    conn.call_timeout = seconds * 1000


def connect(config):
    import oracledb
    params = dict(
        host=config["host"], port=config["port"], service_name=config["service"],
        user=config["user"], password=config.get("password"), tcp_connect_timeout=10,
        retry_count=0, protocol="tcp" if config["plaintext"] else "tcps", ssl_server_dn_match=True,
    )
    for key in ("wallet_location", "wallet_password"):
        if config.get(key):
            params[key] = config[key]
    conn = oracledb.connect(**params)
    try:
        conn.call_timeout = 15000
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
    except Exception:
        conn.close()
        raise
    return Port(conn, configure, bound_query)
