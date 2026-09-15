#!/usr/bin/env python3
"""Differential test of a generated SQL migration: the source database against ScalarDB, per statement.

    python3 difftest.py --project-dir DIR --profile private/profile.json --scalardb-properties scalardb.properties \
        --fetcher core|jdbc --out generated/sql-migration/<target> [--id SQM-###]... [--record]

For every read routed to `plan` or `scalardb_sql`, the full original statement runs on the source database and the
migrated route runs on ScalarDB (the generated plan through the runtime, or the generated ScalarDB SQL, which needs
--fetcher jdbc and a licensed ScalarDB Cluster); the result sets are compared. ScalarDB must hold the same rows as
the source for the tables involved. Writes and other routes are recorded as skipped with the reason.

Writes an evidence file under reports/09_verification/sql-migration/ and, with --record, the verification states
into the manifest. Exit 0: no failure; 1: at least one failure or a fatal error.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[4] / "tools" / "lib"))

import inventory as inventory_module  # noqa: E402
from verify import common  # noqa: E402

# A bind marker in the masked SQL: `?`, or `:name` that is not a PostgreSQL `::type` cast. Masked literals are
# removed first, since masking itself writes `'?'`.
BIND_MARKER = re.compile(r"\?|(?<![:\w]):[A-Za-z_]\w*")

SKIP_REASONS = {
    "core_api": "Core API implementations are verified by unit tests against a real engine",
    "app_side": "application-side code is verified by golden checks",
}


def _skip(sid, reason):
    return {"id": sid, "method": "difftest", "outcome": "skipped", "reason": reason}


def run(manifest, inventory, project_dir, source, runner, fetcher, generated_dir, ids=None):
    dialect = manifest["source"]["dialect"]
    statements = {s["id"]: s for s in inventory["statements"]}
    generated = Path(generated_dir)
    results = []
    for entry in manifest["statements"]:
        sid, route = entry["id"], entry["route"]
        if ids and sid not in ids:
            continue
        stmt = statements.get(sid)
        if stmt is None or route in ("schema", "redesign", "retire"):
            continue
        if route in SKIP_REASONS:
            results.append(_skip(sid, SKIP_REASONS[route]))
            continue
        if stmt["category"] != "query":
            results.append(_skip(sid, "writes change state; verify them with unit tests, not result sets"))
            continue
        if route == "scalardb_sql" and fetcher != "jdbc":
            results.append(_skip(sid, "ScalarDB SQL needs ScalarDB Cluster and a license (--fetcher jdbc)"))
            continue
        if stmt.get("binds") or BIND_MARKER.search(stmt["sql"].replace("'?'", "")):
            results.append(_skip(sid, "the statement takes bind parameters; prove it with golden or unit tests"))
            continue
        try:
            text = inventory_module.statement_text(stmt, project_dir=project_dir)
        except inventory_module.StaleEvidence:
            results.append(_skip(sid, "source changed since the inventory"))
            continue
        try:
            _, expected = source.rows(text)
            if route == "plan":
                actual = runner.plan(generated / "src/main/resources/plans" / f"{sid}.plan.json", fetcher)
            else:
                converted = (generated / "src/main/resources/sql" / f"{sid}.sql").read_text(encoding="utf-8")
                actual = runner.sql(converted.strip().rstrip(";").strip())
        except Exception as exc:  # noqa: BLE001 — a harness failure is reported, never a verdict
            results.append({"id": sid, "method": "difftest", "outcome": "error", "reason": type(exc).__name__})
            continue
        same, detail = common.same_rows(expected, actual, common.is_ordered(text, dialect))
        results.append({"id": sid, "method": "difftest", "outcome": "pass"} if same else
                       {"id": sid, "method": "difftest", "outcome": "fail", "reason": detail})
    return results


def main(argv=None):
    from sql_migration_manifest import INVENTORY_PATH, MANIFEST_PATH, load_and_validate

    ap = argparse.ArgumentParser(description="Differential test of a generated SQL migration.")
    ap.add_argument("--project-dir", default=".")
    ap.add_argument("--profile", required=True, help="source database profile (environment references)")
    ap.add_argument("--scalardb-properties", required=True)
    ap.add_argument("--fetcher", default="core", choices=["core", "jdbc"])
    ap.add_argument("--out", required=True, help="the generated module")
    ap.add_argument("--id", action="append", help="verify only this statement (repeatable)")
    ap.add_argument("--record", action="store_true", help="write the verification states into the manifest")
    args = ap.parse_args(argv)
    project = Path(args.project_dir)
    try:
        manifest, errors = load_and_validate(str(project))
        if manifest is None or errors:
            raise ValueError("the manifest is missing or not valid; run design-sql-migration")
        inventory = json.loads((project / (manifest["inputs"].get("inventory") or INVENTORY_PATH)).read_text(encoding="utf-8"))
        config = common.source_config(json.loads(Path(args.profile).read_text(encoding="utf-8")))
        source = common.SourceDatabase(config)
        try:
            runner = common.ResidualRunner(args.scalardb_properties, binary=common.runner_path(project))
            results = run(manifest, inventory, project, source, runner,
                          args.fetcher, args.out, args.id)
        finally:
            source.close()
    except Exception as exc:  # noqa: BLE001 — never print driver messages: they can carry credentials or values
        print(f"difftest failed: {type(exc).__name__}: {exc if isinstance(exc, (ValueError, FileNotFoundError)) else ''}",
              file=sys.stderr)
        return 1
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence = Path("reports/09_verification/sql-migration") / f"difftest-{stamp}.json"
    (project / evidence).parent.mkdir(parents=True, exist_ok=True)
    (project / evidence).write_text(json.dumps({"schema_version": 1, "method": "difftest", "fetcher": args.fetcher,
                                                "environment": config["environment"], "results": results}, indent=2) + "\n")
    if args.record:
        (project / MANIFEST_PATH).write_text(
            json.dumps(common.record(manifest, results, evidence.as_posix()), indent=2, ensure_ascii=False) + "\n")
    counts = {}
    for r in results:
        counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
    print(f"difftest {counts} -> {evidence}")
    return 1 if counts.get("fail") else 0


if __name__ == "__main__":
    sys.exit(main())
