"""Validated environment references and bounded DB-API execution."""
import math
import os
import re


def connection_config(profile):
    allowed = {"product", "expected_version", "schema", "target_id", "allow_local_plaintext"}
    fields = {"host", "port", "database", "user", "password", "service", "tls_ca", "wallet_location", "wallet_password"}
    if set(profile) - allowed - {f + "_env" for f in fields}:
        raise ValueError("profile accepts environment references, not literal connection secrets or driver options")
    config = {}
    for field in fields:
        key = profile.get(field + "_env")
        if key:
            if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", key) or key not in os.environ:
                raise ValueError("missing connection environment variable")
            config[field] = os.environ[key]
    for field in ("host", "port", "user"):
        if not config.get(field):
            raise ValueError("host, port and user environment references are required")
    config["port"] = int(config["port"])
    plaintext = profile.get("allow_local_plaintext", False)
    if not isinstance(plaintext, bool):
        raise ValueError("allow_local_plaintext must be boolean")
    if plaintext and config["host"] not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError("plaintext is limited to explicit local test connections")
    config["plaintext"] = plaintext
    return config


class Port:
    def __init__(self, connection, configure, bound_query, query_timeout=15):
        self.connection, self.configure, self.bound_query = connection, configure, bound_query
        self.query_timeout = query_timeout

    def query(self, spec, schema, limit, timeout):
        sql = spec["sql"]
        if not sql.lstrip().upper().startswith("SELECT ") or ";" in sql:
            raise ValueError("query is not a registered single SELECT")
        seconds = max(1, math.ceil(min(timeout, self.query_timeout)))
        self.configure(self.connection, seconds)
        cursor = self.connection.cursor()
        try:
            sql, params = self.bound_query(sql, schema, limit)
            cursor.execute(sql, params)
            names = [x[0].lower() for x in cursor.description]
            return [dict(zip(names, row)) for row in cursor.fetchmany(limit + 1)]
        finally:
            cursor.close()

    def close(self):
        self.connection.close()


def verify_probe(spec, port, expected_version, expected_catalog):
    rows = port.query({"id": "probe", "sql": spec["probe"]}, None, 1, 10)
    if len(rows) != 1:
        raise ValueError("database identification failed")
    row = rows[0]
    product = str(row.get("product", "")).lower()
    version = str(row["version"])
    # Compatible products report the base product's name; the adapter declares what gives them away.
    identity = product + " " + version.lower()
    if spec["id"] not in product or row.get("compatible_product") or any(m in identity for m in spec.get("compatible_markers", [])):
        raise ValueError("database product mismatch or unverified compatible product")
    release = re.match(r"\d+(?:\.\d+)*", version)
    if not isinstance(expected_version, str) or not re.fullmatch(r"\d+(?:\.\d+)*", expected_version):
        raise ValueError("expected version must be an explicit numeric release")
    if not release or not (release[0] == expected_version or release[0].startswith(expected_version + ".")):
        raise ValueError("database version differs from approved profile")
    if int(release[0].split(".")[0]) < spec["min_major"]:
        raise ValueError("database version outside adapter capability")
    if expected_catalog is not None and row["catalog"] != expected_catalog:
        raise ValueError("database catalog differs from profile")
    return {"product": spec["id"], "version": version, "catalog": row["catalog"], "visibility": "objects visible to connected user; absence is not proof of nonexistence"}
