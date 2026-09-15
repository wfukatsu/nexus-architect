"""Shared setup for the SQL migration suites: the import path, and the one third-party requirement.

The converter needs sqlglot (pinned in the repository's requirements.txt). CI installs it, so there a
missing module fails the suite. A local run without it prints SKIP and exits 0 — green but weaker,
the same trade the GraphQL suite makes for the OKF bundle — rather than failing on an environment gap.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT / "scripts"))


def require_sqlglot():
    try:
        import sqlglot  # noqa: F401
    except ModuleNotFoundError:
        message = "sqlglot is not installed (pip install -r requirements.txt)"
        if os.environ.get("CI"):
            print("FAIL: " + message, file=sys.stderr)
            sys.exit(1)
        print("SKIP: " + message + "; CI runs this suite")
        sys.exit(0)
