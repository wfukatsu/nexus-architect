#!/usr/bin/env python3
"""Validate reports/03_design/api-style-decisions.json."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from api_style_decisions import validate_document  # noqa: E402


def main(argv):
    path = argv[1] if len(argv) > 1 else "reports/03_design/api-style-decisions.json"
    try:
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print("api-style-decisions: %s" % exc, file=sys.stderr)
        return 2
    errors = validate_document(document)
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        print("api-style-decisions: %d error(s)" % len(errors), file=sys.stderr)
        return 1
    print("api-style-decisions: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
