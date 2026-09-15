#!/usr/bin/env python3
"""Golden checks for application-side reads of a generated SQL migration.

    capture  run the statement on the authorized source database once, with the tables it reads, into
             <module>/src/test/resources/golden/SQM-###/golden.json          (needs the source database)
    check    run the generated appside.Sqm###Query against that file with GoldenCheck   (JVM only)

    python3 golden.py capture --project-dir DIR --profile private/profile.json --out <module> --id SQM-### [--max-rows N]
                              [--query rendering.sql --param NAME=VALUE ...]
    python3 golden.py check   --project-dir DIR --out <module> --package com.example.migration --id SQM-### [--record]

Capture reads only: it runs no setup script, and it refuses a table larger than --max-rows, because a golden set is a
bounded fixture from a test copy, not an export. A statement that cannot run as the inventory holds it (JPQL, dynamic
SQL, bind parameters) is refused unless the user renders it: --query is one concrete SELECT in the source dialect with
:name markers, --param gives their values (and any other value the implementation needs, such as a substituted column).
golden.json keeps GoldenCheck's format:
{"source", "query", "ordered", "params", "rendering", "tables": {name: [{col: value}]}, "expected": {"columns", "rows"}}
with Decimal -> {"$dec": "1.5"}, datetime -> {"$ts": ISO}, date -> {"$date": ISO}; "rendering" is "statement" or "user";
"source" is the manifest's source dialect, which GoldenCheck names in its summary line (its diffs say expected / actual).
"""
from __future__ import annotations

import argparse
import datetime
import decimal
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import sqlglot
from sqlglot import exp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[4] / "tools" / "lib"))

import inventory as inventory_module  # noqa: E402
from verify import common  # noqa: E402

MAIN = "com.scalar.migrate.appside.golden.GoldenCheck"
DEFAULT_MAX_ROWS = 10_000


def encode(value):
    if isinstance(value, decimal.Decimal):
        return {"$dec": str(value)}
    if isinstance(value, datetime.datetime):  # before date: datetime is a date subclass
        return {"$ts": value.isoformat()}
    if isinstance(value, datetime.date):
        return {"$date": value.isoformat()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"cannot encode a {type(value).__name__} value")


def golden_path(generated_dir, sid):
    return Path(generated_dir) / "src/test/resources/golden" / sid / "golden.json"


def parse_params(items):
    """--param NAME=VALUE values: JSON when the value parses as JSON (1, 1.5, true, "42"), the raw text otherwise."""
    params = {}
    for item in items or []:
        name, sep, raw = item.partition("=")
        if not sep or not re.fullmatch(r"[A-Za-z_]\w*", name):
            raise ValueError(f"--param takes NAME=VALUE, got {item!r}")
        try:
            params[name] = json.loads(raw)
        except json.JSONDecodeError:
            params[name] = raw
    return params


def _not_runnable(stmt, text):
    """Why the inventory text cannot run on the source database as it is, or None."""
    if stmt.get("language", "sql") != "sql":
        return f"the statement is {stmt['language'].upper()}, not SQL"
    if stmt.get("dynamic"):
        return "the statement is dynamic SQL"
    if stmt.get("binds") or inventory_module.java_binds(text):
        return "the statement takes bind parameters"
    return None


def _rendered(sql, params, dialect):
    """The user's rendering, checked: one read the source dialect parses, a value for every :name marker."""
    sql = sql.strip().rstrip(";").strip()
    try:
        parsed = [e for e in sqlglot.parse(sql, read=dialect) if e is not None]
    except sqlglot.errors.ParseError:
        parsed = []
    if len(parsed) != 1 or not isinstance(parsed[0], exp.Query):
        raise ValueError("a rendering must be one SELECT statement in the source dialect")
    missing = [m for m in common.markers(sql) if m not in params]
    if missing:
        raise ValueError(f"the rendering has no value for :{missing[0]}")
    return sql


def capture(entry, inventory, project_dir, source, generated_dir, dialect, max_rows=DEFAULT_MAX_ROWS, rendering=None):
    sid = entry["id"]
    stmt = next(s for s in inventory["statements"] if s["id"] == sid)
    try:
        text = inventory_module.statement_text(stmt, project_dir=project_dir)
    except inventory_module.StaleEvidence as exc:
        raise ValueError(f"{sid}: source changed since the inventory") from exc
    if rendering is None:
        reason = _not_runnable(stmt, text)
        if reason:
            raise ValueError(f"{sid}: {reason}; render it as one concrete SELECT with --query, and --param for its values")
        query, params = text, {}
    else:
        params = dict(rendering.get("params") or {})
        query = _rendered(rendering["sql"], params, dialect)
    tables = {}
    for table in common.tables_of(query, dialect):
        columns, rows = source.rows(f"SELECT * FROM {table}")
        if len(rows) > max_rows:
            raise ValueError(f"{table} has more than {max_rows} rows; capture golden data from a smaller test copy")
        tables[table] = [dict(zip([c.lower() for c in columns], map(encode, row))) for row in rows]
    bound = {name: params[name] for name in common.markers(query)}  # Oracle refuses a bind the SQL does not use
    columns, rows = source.rows(query, bound or None)
    data = {"id": sid, "source": dialect, "query": query, "ordered": common.is_ordered(query, dialect),
            "params": {name: encode(value) for name, value in params.items()},
            "rendering": "statement" if rendering is None else "user", "tables": tables,
            "expected": {"columns": [c.lower() for c in columns], "rows": [[encode(v) for v in row] for row in rows]}}
    path = golden_path(generated_dir, sid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def _java(cmd):
    return subprocess.run(cmd).returncode


def check(sid, generated_dir, package, java=None, runtime_lib=None):
    """Run GoldenCheck on the generated query class: exit 0 -> pass, 1 -> fail, anything else -> error."""
    generated = Path(generated_dir)
    stem = sid.replace("-", "").capitalize()
    lib = Path(runtime_lib) if runtime_lib else common.RUNTIME_LIB
    classpath = os.pathsep.join([str(lib / "*"), str(generated / "build/classes/java/main")])
    cmd = ["java", "-Duser.language=en", "-Duser.country=US", "-cp", classpath, MAIN,
           str(golden_path(generated, sid)), f"{package}.appside.{stem}Query"]
    if java is None:
        if not golden_path(generated, sid).is_file():
            return {"id": sid, "method": "golden", "outcome": "skipped", "reason": "golden results not captured"}
        if not lib.is_dir():
            return {"id": sid, "method": "golden", "outcome": "error", "reason": "runtime not installed (gradle installDist)"}
    code = (java or _java)(cmd)
    outcome = {0: "pass", 1: "fail"}.get(code, "error")
    result = {"id": sid, "method": "golden", "outcome": outcome}
    if outcome == "error":
        result["reason"] = f"GoldenCheck exited {code}"
    return result


def main(argv=None):
    from sql_migration_manifest import INVENTORY_PATH, MANIFEST_PATH, load_and_validate

    ap = argparse.ArgumentParser(description="Golden checks for application-side reads.")
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("capture", "check"):
        p = sub.add_parser(name)
        p.add_argument("--project-dir", default=".")
        p.add_argument("--out", required=True, help="the generated module")
        p.add_argument("--id", action="append", required=True, help="statement to process (repeatable)")
    sub.choices["capture"].add_argument("--profile", required=True, help="source database profile (environment references)")
    sub.choices["capture"].add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS)
    sub.choices["capture"].add_argument("--query", help="one concrete SELECT rendering the statement (source dialect, :name markers)")
    sub.choices["capture"].add_argument("--param", action="append", metavar="NAME=VALUE", help="a value of the rendering (repeatable)")
    sub.choices["check"].add_argument("--package", required=True)
    sub.choices["check"].add_argument("--record", action="store_true")
    args = ap.parse_args(argv)
    project = Path(args.project_dir)
    if args.command == "capture" and (args.query or args.param) and (len(args.id) != 1 or not args.query):
        print("golden capture failed: --query renders one statement; pass exactly one --id, and --param only with --query",
              file=sys.stderr)
        return 1
    try:
        manifest, errors = load_and_validate(str(project))
        if manifest is None or errors:
            raise ValueError("the manifest is missing or not valid; run design-sql-migration")
        entries = {e["id"]: e for e in manifest["statements"]}
        if args.command == "capture":
            inventory = json.loads((project / (manifest["inputs"].get("inventory") or INVENTORY_PATH)).read_text(encoding="utf-8"))
            rendering = ({"sql": Path(args.query).read_text(encoding="utf-8"), "params": parse_params(args.param)}
                         if args.query else None)
            source = common.SourceDatabase(common.source_config(json.loads(Path(args.profile).read_text(encoding="utf-8"))))
            try:
                for sid in args.id:
                    path = capture(entries[sid], inventory, project, source, args.out, manifest["source"]["dialect"],
                                   args.max_rows, rendering)
                    print(f"{sid}: captured {path}")
            finally:
                source.close()
            return 0
        results = [check(sid, args.out, args.package, runtime_lib=common.runtime_lib(project)) for sid in args.id]
    except Exception as exc:  # noqa: BLE001 — never print driver messages: they can carry credentials or values
        print(f"golden {args.command} failed: {type(exc).__name__}: {exc if isinstance(exc, (ValueError, KeyError)) else ''}",
              file=sys.stderr)
        return 1
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence = Path("reports/09_verification/sql-migration") / f"golden-{stamp}.json"
    (project / evidence).parent.mkdir(parents=True, exist_ok=True)
    (project / evidence).write_text(json.dumps({"schema_version": 1, "method": "golden", "results": results}, indent=2) + "\n")
    if args.record:
        (project / MANIFEST_PATH).write_text(
            json.dumps(common.record(manifest, results, evidence.as_posix()), indent=2, ensure_ascii=False) + "\n")
    for r in results:
        print(f"{r['id']}: {r['outcome']}" + (f" ({r['reason']})" if r.get("reason") else ""))
    return 1 if any(r["outcome"] == "fail" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
