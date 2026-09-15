#!/usr/bin/env python3
"""Golden checks for application-side reads of a generated SQL migration.

    capture  run the statement on the authorized source database once, with the tables it reads, into
             <module>/src/test/resources/golden/SQM-###/golden.json          (needs the source database)
    check    run the generated appside.Sqm###Query against that file with GoldenCheck   (JVM only)

    python3 golden.py capture --project-dir DIR --profile private/profile.json --out <module> --id SQM-### [--max-rows N]
    python3 golden.py check   --project-dir DIR --out <module> --package com.example.migration --id SQM-### [--record]

Capture reads only: it runs no setup script, and it refuses a table larger than --max-rows, because a golden set is a
bounded fixture from a test copy, not an export. golden.json keeps GoldenCheck's format:
{"query", "ordered", "tables": {name: [{col: value}]}, "expected": {"columns", "rows"}} with
Decimal -> {"$dec": "1.5"}, datetime -> {"$ts": ISO}, date -> {"$date": ISO}.
"""
from __future__ import annotations

import argparse
import datetime
import decimal
import json
import os
import subprocess
import sys
from pathlib import Path

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


def capture(entry, inventory, project_dir, source, generated_dir, dialect, max_rows=DEFAULT_MAX_ROWS):
    sid = entry["id"]
    stmt = next(s for s in inventory["statements"] if s["id"] == sid)
    try:
        text = inventory_module.statement_text(stmt, project_dir=project_dir)
    except inventory_module.StaleEvidence as exc:
        raise ValueError(f"{sid}: source changed since the inventory") from exc
    tables = {}
    for table in common.tables_of(text, dialect):
        columns, rows = source.rows(f"SELECT * FROM {table}")
        if len(rows) > max_rows:
            raise ValueError(f"{table} has more than {max_rows} rows; capture golden data from a smaller test copy")
        tables[table] = [dict(zip([c.lower() for c in columns], map(encode, row))) for row in rows]
    columns, rows = source.rows(text)
    data = {"id": sid, "query": text, "ordered": common.is_ordered(text, dialect), "tables": tables,
            "expected": {"columns": [c.lower() for c in columns], "rows": [[encode(v) for v in row] for row in rows]}}
    path = golden_path(generated_dir, sid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def _java(cmd):
    return subprocess.run(cmd).returncode


def check(sid, generated_dir, package, java=None):
    """Run GoldenCheck on the generated query class: exit 0 -> pass, 1 -> fail, anything else -> error."""
    generated = Path(generated_dir)
    stem = sid.replace("-", "").capitalize()
    classpath = os.pathsep.join([str(common.RUNTIME_LIB / "*"), str(generated / "build/classes/java/main")])
    cmd = ["java", "-Duser.language=en", "-Duser.country=US", "-cp", classpath, MAIN,
           str(golden_path(generated, sid)), f"{package}.appside.{stem}Query"]
    if java is None:
        if not golden_path(generated, sid).is_file():
            return {"id": sid, "method": "golden", "outcome": "skipped", "reason": "golden results not captured"}
        if not common.RUNTIME_LIB.is_dir():
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
    sub.choices["check"].add_argument("--package", required=True)
    sub.choices["check"].add_argument("--record", action="store_true")
    args = ap.parse_args(argv)
    project = Path(args.project_dir)
    try:
        manifest, errors = load_and_validate(str(project))
        if manifest is None or errors:
            raise ValueError("the manifest is missing or not valid; run design-sql-migration")
        entries = {e["id"]: e for e in manifest["statements"]}
        if args.command == "capture":
            inventory = json.loads((project / (manifest["inputs"].get("inventory") or INVENTORY_PATH)).read_text(encoding="utf-8"))
            source = common.SourceDatabase(common.source_config(json.loads(Path(args.profile).read_text(encoding="utf-8"))))
            try:
                for sid in args.id:
                    path = capture(entries[sid], inventory, project, source, args.out, manifest["source"]["dialect"], args.max_rows)
                    print(f"{sid}: captured {path}")
            finally:
                source.close()
            return 0
        results = [check(sid, args.out, args.package) for sid in args.id]
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
