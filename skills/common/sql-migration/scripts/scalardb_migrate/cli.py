"""CLI: python -m scalardb_migrate.cli <file.sql> --dialect oracle|postgres|mysql [options]"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from .appside import group_issues, parse_expected_rows
from .converter import convert_script
from .decomposer import DEFAULT_ROW_LIMIT
from .schema import SchemaRegistry

# reported in the application-side section instead of the per-statement table
GROUPED_CODES = {"APP_SEMANTICS", "DESIGN", "COST", "ROW_LIMIT", "COST_DEADLINE", "CONFIG"}


def _parse_keys(items: list[str]) -> dict[str, tuple[list[str], list[str]]]:
    """--keys table=p1,p2/c1,c2  (partition keys / clustering keys)"""
    out = {}
    for item in items or []:
        table, _, spec = item.partition("=")
        p, _, c = spec.partition("/")
        out[table.strip().lower()] = ([x.strip() for x in p.split(",") if x.strip()],
                                      [x.strip() for x in c.split(",") if x.strip()])
    return out


def render_markdown(results, dialect: str, source: str) -> str:
    counts = Counter(r.status for r in results)
    lines = [f"# ScalarDB SQL migration report", "",
             f"- source: `{source}` (dialect: {dialect})",
             f"- statements: {len(results)}  |  OK: {counts.get('OK', 0)}  |  "
             f"converted with warnings: {counts.get('WARN', 0)}  |  app-side plan: {counts.get('PLANNED', 0)}  |  "
             f"not convertible: {counts.get('ERROR', 0)}", ""]
    icon = {"OK": "✅", "WARN": "⚠️", "ERROR": "❌", "PLANNED": "🧩"}
    lines += ["| # | kind | status | source | ScalarDB SQL | issues |", "|---|---|---|---|---|---|"]
    for r in results:
        src = r.source_sql.replace("\n", " ").replace("|", "\\|")
        src = src[:90] + ("…" if len(src) > 90 else "")
        out = "; ".join(r.converted).replace("\n", " ").replace("|", "\\|")
        out = out[:90] + ("…" if len(out) > 90 else "")
        iss = "<br>".join(f"**{i.severity}** {i.code}: {i.message}".replace("|", "\\|")
                          for i in r.issues if i.code not in GROUPED_CODES)
        lines.append(f"| {r.index} | {r.kind} | {icon[r.status]} {r.status} | `{src}` | `{out}` | {iss} |")
    code_counts = Counter((i.severity, i.code) for r in results for i in r.issues)
    lines += ["", "## Issue summary", "", "| severity | code | count |", "|---|---|---|"]
    for (sev, code), n in sorted(code_counts.items(), key=lambda kv: (-{'ERROR': 2, 'WARN': 1, 'INFO': 0}[kv[0][0]], -kv[1])):
        lines.append(f"| {sev} | {code} | {n} |")
    sections = (("Move to the application", "app_side"), ("Semantics the application must keep", "semantics"),
                ("Design", "design"), ("Read cost", "cost"), ("Settings", "config"))
    work = [(r, group_issues(r.issues)) for r in results]
    work = [(r, g) for r, g in work if r.status in ("ERROR", "PLANNED") or g["cost"]]
    if work:
        lines += ["", "## Application-side work", ""]
        for r, g in work:
            lines += [f"### #{r.index} {r.status}: `{r.source_sql.splitlines()[0][:80]}`", ""]
            if r.status == "PLANNED":
                lines += ["The plan fetches through ScalarDB and runs the original SQL in H2.", ""]
            for title, key in sections:
                if g[key]:
                    lines += [f"**{title}**", ""] + [f"- {i.code}: {i.message}" for i in g[key]] + [""]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyse and convert SQL to ScalarDB SQL (PoC)")
    ap.add_argument("file")
    ap.add_argument("--dialect", "--source", dest="dialect", required=True, choices=["oracle", "postgres", "mysql"],
                    help="source dialect (--source is accepted as an alias)")
    ap.add_argument("--schema", help="ScalarDB Schema Loader JSON with existing table definitions")
    ap.add_argument("--keys", action="append", help="partition/clustering key hint: table=p1,p2/c1,c2")
    ap.add_argument("--out-dir", default=None, help="write <name>.scalardb.sql, <name>.report.md, "
                                                     "<name>.report.json, <name>.schema.json here")
    ap.add_argument("--plan-dir", default=None, help="write one <name>.<n>.plan.json per PLANNED statement here")
    ap.add_argument("--no-plan", action="store_true", help="do not build app-side plans for unconvertible SELECTs")
    ap.add_argument("--storage", default="jdbc", choices=["jdbc", "cassandra"],
                    help="storage behind ScalarDB: on cassandra, cross-partition ORDER BY and key IN-lists are planned")
    ap.add_argument("--expected-rows", action="append", metavar="TABLE=N[:PER_KEY]",
                    help="rows in a table (and rows per partition / index key) for read-cost estimates")
    ap.add_argument("--isolation", default="SERIALIZABLE", choices=["SERIALIZABLE", "SNAPSHOT", "READ_COMMITTED"],
                    help="Consensus Commit isolation level the estimates assume (SERIALIZABLE re-reads scans at commit)")
    ap.add_argument("--row-limit", type=int, default=DEFAULT_ROW_LIMIT, help="plan guardrail: max rows fetched per table")
    ap.add_argument("--h2-indexes", action="store_true",
                    help="plans build H2 indexes on the fetched tables (joins over large fetches, e.g. batch jobs; "
                         "overhead for small requests)")
    args = ap.parse_args(argv)
    logging.getLogger("sqlglot").setLevel(logging.ERROR)  # unsupported-argument warnings are reported as issues

    text = Path(args.file).read_text(encoding="utf-8")
    registry = SchemaRegistry.from_schema_loader_json(args.schema) if args.schema else SchemaRegistry()
    results, registry = convert_script(text, args.dialect, registry, _parse_keys(args.keys), decompose=not args.no_plan,
                                       storage=args.storage, expected_rows=parse_expected_rows(args.expected_rows),
                                       isolation=args.isolation, row_limit=args.row_limit,
                                       h2_indexes=args.h2_indexes)

    for r in results:
        print(f"[{r.index:>3}] {r.status:<5} {r.kind:<12} {r.source_sql.splitlines()[0][:70]}")
        for i in r.issues:
            print(f"        {i.severity:<5} {i.code}: {i.message}")
        for c in r.converted:
            print("        => " + c.replace("\n", "\n           "))
    counts = Counter(r.status for r in results)
    print(f"\n{len(results)} statements: OK={counts.get('OK', 0)} WARN={counts.get('WARN', 0)} "
          f"PLANNED={counts.get('PLANNED', 0)} ERROR={counts.get('ERROR', 0)}")
    if args.plan_dir:
        pd = Path(args.plan_dir)
        pd.mkdir(parents=True, exist_ok=True)
        stem = Path(args.file).stem
        for r in results:
            if r.plan:
                (pd / f"{stem}.{r.index}.plan.json").write_text(json.dumps(r.plan, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"plans written to {pd}/")

    if args.out_dir:
        out = Path(args.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        stem = Path(args.file).stem
        sql_lines = []
        for r in results:
            if r.converted:
                sql_lines += [c + ";" for c in r.converted]
            elif r.plan:
                sql_lines.append("-- [APP-SIDE PLAN #%d] %s" % (r.index, r.source_sql.replace("\n", " ")[:200]))
            else:
                sql_lines.append("-- [NOT CONVERTED #%d] %s" % (r.index, r.source_sql.replace("\n", " ")[:200]))
        (out / f"{stem}.scalardb.sql").write_text("\n".join(sql_lines) + "\n", encoding="utf-8")
        (out / f"{stem}.report.md").write_text(render_markdown(results, args.dialect, args.file), encoding="utf-8")
        (out / f"{stem}.report.json").write_text(json.dumps([asdict(r) for r in results], indent=2, ensure_ascii=False),
                                                 encoding="utf-8")
        (out / f"{stem}.schema.json").write_text(registry.to_schema_loader_json(), encoding="utf-8")
        print(f"written to {out}/")
    return 0 if not counts.get("ERROR") else 1


if __name__ == "__main__":
    sys.exit(main())
