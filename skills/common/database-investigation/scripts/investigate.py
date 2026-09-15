"""Command-line entry point."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import uuid

from core.connection import connection_config, verify_probe
from core.design import parse_design
from core.live import collect
from core.output import path_component, write_reports
from core.registry import load_adapter


def run(args, clock, new_id):
    started = clock()
    if args.mode == "live":
        profile = json.loads(Path(args.profile).read_text())
        config = connection_config(profile)
        product, schema, target = profile["product"], profile["schema"], profile["target_id"]
        version = profile["expected_version"]
    else:
        product, schema, target, version = args.product, args.schema, args.target_id, args.version
    if not schema or not isinstance(schema, str):
        raise ValueError("explicit schema is required")
    run_id = path_component(args.run_id or new_id())
    folder = Path(args.output_root) / path_component(target) / args.mode / run_id
    if folder.exists():
        raise ValueError("run directory already exists")
    spec, module = load_adapter(product)
    observed = None
    if args.mode == "design":
        paths = [Path(p) for p in args.input]
        if any(p.suffix.lower() != ".sql" for p in paths):
            raise ValueError("CLI accepts SQL; use the skill's documented evidence workflow for other design documents")
        if any(p.stat().st_size > 10_000_000 for p in paths):
            raise ValueError("split input files larger than 10 MB")
        data = parse_design(paths, spec, schema)
        data["statistics"] = []
    else:
        port = module.connect(config)
        try:
            observed = verify_probe(spec, port, version, config.get("database"))
        except Exception:
            port.close()
            raise
        data = collect(spec, port, schema, clock, args.limit, args.budget)
    complete = bool(data["collections"]) and all(c["status"] in {"ok", "empty"} and not c["truncated"] for c in data["collections"]) and not data["findings"]
    inv = dict(data, schema_version=1, run_id=run_id, mode=args.mode, product=product,
               version=version, schema=schema, target_id=target, started_at=started,
               finished_at=clock(), status="complete" if complete else "partial", observed=observed)
    language = args.lang
    if language is None:
        progress = Path("work/pipeline-progress.json")
        language = json.loads(progress.read_text()).get("options", {}).get("output_language", "en") if progress.exists() else "en"
    write_reports(inv, folder, "ja" if language in {"ja", "Japanese", "日本語"} else "en")
    print(folder)
    return 0 if complete else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    design = sub.add_parser("design")
    design.add_argument("--product", required=True)
    design.add_argument("--schema", required=True)
    design.add_argument("--target-id", required=True)
    design.add_argument("--version")
    design.add_argument("--input", nargs="+", required=True)
    live = sub.add_parser("live")
    live.add_argument("--profile", required=True)
    for child in (design, live):
        child.add_argument("--output-root", default="reports/01_analysis/database-investigation")
        child.add_argument("--run-id")
        child.add_argument("--lang", choices=["ja", "en"])
        child.add_argument("--limit", type=int, default=10000)
        child.add_argument("--budget", type=int, default=120)
    args = parser.parse_args()
    try:
        if not 1 <= args.limit <= 100000 or not 1 <= args.budget <= 3600:
            raise ValueError("invalid limits")
        return run(args, lambda: datetime.now(timezone.utc).isoformat(), lambda: uuid.uuid4().hex)
    except Exception:
        # Driver exceptions and paths can contain passwords, SQL literals or service descriptors.
        print("Investigation failed. Check local profile, input, driver, permissions and destination; no credential or driver exception is printed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
