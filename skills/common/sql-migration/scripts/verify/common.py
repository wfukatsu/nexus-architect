"""What the verification harnesses share: comparison, the source connection, the runtime, recording.

Data never leaves the harness in a report: a mismatch is described by counts and a row index, not by values.
The source database is reached only through an environment-reference profile whose `environment` is local, test
or staging — the same profile shape as /architect:investigate-db-live, whose validation it reuses.
"""
from __future__ import annotations

import copy
import datetime
import decimal
import importlib.util
import json
import re
import subprocess
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
SQL_MIGRATION = SCRIPTS.parent
INVESTIGATION_CONNECTION = SQL_MIGRATION.parent / "database-investigation" / "scripts" / "core" / "connection.py"
RUNNER = SQL_MIGRATION / "runtime-java" / "build" / "install" / "residual-runner" / "bin" / "residual-runner"
RUNTIME_LIB = SQL_MIGRATION / "runtime-java" / "build" / "install" / "residual-runner" / "lib"
PROJECT_INSTALL = Path("work") / "sql-migration" / "runtime-java" / "build" / "install" / "residual-runner"
ENVIRONMENTS = ("local", "test", "staging")
PRODUCTS = ("oracle", "postgresql", "mysql")
QUERY_TIMEOUT_MS = 60_000


def runner_path(project_dir):
    """The residual runner built into the project (work/sql-migration/runtime-java), else the plugin's."""
    built = Path(project_dir) / PROJECT_INSTALL / "bin" / "residual-runner"
    return built if built.is_file() else RUNNER


def runtime_lib(project_dir):
    built = Path(project_dir) / PROJECT_INSTALL / "lib"
    return built if built.is_dir() else RUNTIME_LIB


def normalize(value):
    """Make PostgreSQL / Oracle / MySQL / H2 / ScalarDB values comparable: integral numbers as ints, dates as ISO."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, decimal.Decimal):
        value = float(value)
    if isinstance(value, float):
        value = round(value, 6)
        return int(value) if value.is_integer() else value
    if isinstance(value, datetime.datetime):
        return value.date().isoformat() if value.time() == datetime.time(0) else value.isoformat(sep=" ")
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, str):
        try:  # H2 / JDBC may return a date-time string for a DATE value
            parsed = datetime.datetime.fromisoformat(value.replace("T", " ").split(".")[0])
            return parsed.date().isoformat() if parsed.time() == datetime.time(0) else parsed.isoformat(sep=" ")
        except ValueError:
            return value
    if value is None or isinstance(value, int):
        return value
    return str(value)


def same_rows(expected, actual, ordered):
    """(equal, detail). The detail names counts and a row index only — never a value."""
    left = [tuple(normalize(v) for v in row) for row in expected]
    right = [tuple(normalize(v) for v in row) for row in actual]
    if len(left) != len(right):
        return False, f"{len(left)} rows expected, {len(right)} returned"
    if not ordered:
        left, right = sorted(left, key=repr), sorted(right, key=repr)
    for index, (a, b) in enumerate(zip(left, right)):
        if a != b:
            order = "" if ordered else " in sorted order"
            return False, f"row {index} differs{order} ({len(left)} rows expected, {len(right)} returned)"
    return True, None


def is_ordered(sql, dialect):
    import sqlglot

    try:
        return sqlglot.parse_one(sql, read=dialect).args.get("order") is not None
    except Exception:  # noqa: BLE001 — an unparsable statement is compared as a multiset
        return False


SQL_TOKEN = re.compile(r"'(?:[^']|'')*'|(?<![:\w]):([A-Za-z_]\w*)|%")


def markers(sql):
    """Named bind markers (:name) outside string literals, each once, in order of first use."""
    names = []
    for match in SQL_TOKEN.finditer(sql):
        if match.group(1) and match.group(1) not in names:
            names.append(match.group(1))
    return names


def driver_sql(sql, product):
    """sql for a driver call with parameters: :name -> %(name)s with every % doubled (psycopg, PyMySQL); Oracle binds :name."""
    if product == "oracle":
        return sql

    def token(match):
        if match.group(1):
            return f"%({match.group(1)})s"
        return match.group(0).replace("%", "%%")

    return SQL_TOKEN.sub(token, sql)


def tables_of(sql, dialect):
    import sqlglot
    from sqlglot import exp

    tree = sqlglot.parse_one(sql, read=dialect)
    ctes = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    return sorted({t.name.lower() for t in tree.find_all(exp.Table) if t.name and t.name.lower() not in ctes})


def _investigation_connection():
    spec = importlib.util.spec_from_file_location("database_investigation_connection", INVESTIGATION_CONNECTION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_config(profile):
    """Connection settings from an environment-reference profile; ValueError for production or literal secrets."""
    if not isinstance(profile, dict):
        raise ValueError("the profile must be a JSON object")
    environment = profile.get("environment")
    if environment == "production":
        raise ValueError("verification never connects to a production database; use a disposable, test or staging copy")
    if environment not in ENVIRONMENTS:
        raise ValueError("profile.environment must be local, test or staging")
    if profile.get("product") not in PRODUCTS:
        raise ValueError("profile.product must be oracle, postgresql or mysql")
    config = _investigation_connection().connection_config({k: v for k, v in profile.items() if k != "environment"})
    config.update(environment=environment, product=profile["product"])
    return config


class SourceDatabase:
    """Read-only session on the authorized source database. rows(sql) -> (columns, rows), bounded."""

    def __init__(self, config, max_rows=100_000):
        self.config, self.max_rows = config, max_rows
        product = config["product"]
        if product == "postgresql":
            import psycopg
            self.connection = psycopg.connect(
                host=config["host"], port=config["port"], dbname=config.get("database"), user=config["user"],
                password=config.get("password"), connect_timeout=10, autocommit=True,
                sslmode="disable" if config["plaintext"] else "verify-full", sslrootcert=config.get("tls_ca"),
                options=f"-c default_transaction_read_only=on -c statement_timeout={QUERY_TIMEOUT_MS}")
        elif product == "mysql":
            import pymysql
            self.connection = pymysql.connect(
                host=config["host"], port=config["port"], database=config.get("database"), user=config["user"],
                password=config.get("password", ""), connect_timeout=10, read_timeout=QUERY_TIMEOUT_MS // 1000,
                autocommit=True, local_infile=False, ssl_ca=config.get("tls_ca"),
                ssl_verify_cert=not config["plaintext"], ssl_verify_identity=not config["plaintext"])
            with self.connection.cursor() as cur:
                cur.execute("SET SESSION TRANSACTION READ ONLY")
        else:
            import oracledb
            oracledb.defaults.fetch_decimals = True  # NUMBER as Decimal, as the source means it
            params = dict(host=config["host"], port=config["port"], service_name=config.get("service"),
                          user=config["user"], password=config.get("password"),
                          protocol="tcp" if config["plaintext"] else "tcps")
            for key in ("wallet_location", "wallet_password"):
                if config.get(key):
                    params[key] = config[key]
            self.connection = oracledb.connect(**params)
            self.connection.call_timeout = QUERY_TIMEOUT_MS

    def rows(self, sql, params=None):
        """params binds the :name markers of sql; None runs it as it is."""
        cursor = self.connection.cursor()
        try:
            if self.config["product"] == "oracle":
                cursor.execute("SET TRANSACTION READ ONLY")
            if params is None:
                cursor.execute(sql)
            else:
                cursor.execute(driver_sql(sql, self.config["product"]), params)
            columns = [d[0].lower() for d in cursor.description]
            fetched = cursor.fetchmany(self.max_rows + 1)
            if len(fetched) > self.max_rows:
                raise ValueError(f"the statement returned more than {self.max_rows} rows")
            return columns, [list(r) for r in fetched]
        finally:
            cursor.close()
            if self.config["product"] == "oracle":
                self.connection.rollback()

    def close(self):
        self.connection.close()


class ResidualRunner:
    """The vendored runtime's CLI: run a plan, or one ScalarDB SQL statement, through ScalarDB."""

    def __init__(self, properties, binary=RUNNER):
        if not Path(binary).is_file():
            raise FileNotFoundError(f"{binary} not found; run `gradle installDist` in {SQL_MIGRATION / 'runtime-java'}")
        self.properties, self.binary = str(properties), str(binary)

    def _run(self, *args):
        done = subprocess.run([self.binary, *args], capture_output=True, text=True)
        if done.returncode != 0:
            first = next((l for l in done.stderr.splitlines() if l.startswith(("Exception", "Caused by"))), "runtime failed")
            raise RuntimeError(first.split(":", 1)[0])  # the exception class only: messages can carry values
        return json.loads(done.stdout)["rows"]

    def plan(self, path, fetcher):
        return self._run("run", "--plan", str(path), "--properties", self.properties, "--fetcher", fetcher)

    def sql(self, text):
        return self._run("sql", "--properties", self.properties, "--sql", text)


def record(manifest, results, evidence):
    """A copy of the manifest with `verification` set from harness results.

    pass -> verified, fail -> failed (both with method and evidence); skipped -> skipped with its reason, unless an
    earlier run already proved or disproved the statement; error -> unchanged, because a broken harness is no verdict.
    """
    out = copy.deepcopy(manifest)
    entries = {e.get("id"): e for e in out.get("statements", []) if isinstance(e, dict)}
    for result in results:
        entry = entries.get(result["id"])
        if entry is None:
            continue
        current = (entry.get("verification") or {}).get("status")
        outcome = result["outcome"]
        if outcome in ("pass", "fail"):
            entry["verification"] = {"status": "verified" if outcome == "pass" else "failed",
                                     "method": result["method"], "evidence": evidence}
        elif outcome == "skipped" and current not in ("verified", "failed"):
            entry["verification"] = {"status": "skipped", "reason": result.get("reason") or "not verified"}
    return out
