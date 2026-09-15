#!/usr/bin/env python3
"""Convert a SQL script to ScalarDB SQL: the vendored converter's CLI, runnable by path.

    python3 "${CLAUDE_PLUGIN_ROOT}/skills/common/sql-migration/scripts/convert.py" <file.sql> --source oracle|postgres|mysql \
        [--schema schema.json] [--keys t=p1,p2/c1] [--storage jdbc|cassandra] [--expected-rows t=N[:K]] \
        [--isolation SERIALIZABLE|SNAPSHOT|READ_COMMITTED] [--row-limit N] [--h2-indexes] \
        [--out-dir DIR] [--plan-dir DIR] [--no-plan]

Exit 0 when no statement is ERROR, 1 when at least one is. Requires sqlglot (requirements.txt).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scalardb_migrate.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
