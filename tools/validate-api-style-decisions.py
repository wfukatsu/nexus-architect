#!/usr/bin/env python3
"""Validate reports/03_design/api-style-decisions.json."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from api_style_decisions import render_markdown, validate_document  # noqa: E402


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?",
                        default="reports/03_design/api-style-decisions.json")
    parser.add_argument("--render-markdown")
    parser.add_argument("--lang", choices=("en", "ja"), default="en")
    return parser.parse_args(argv[1:])


def main(argv):
    args = parse_args(argv)
    try:
        with open(args.path, encoding="utf-8") as handle:
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
    if args.render_markdown:
        try:
            with open(args.render_markdown, "w", encoding="utf-8") as handle:
                handle.write(render_markdown(document, args.lang))
        except OSError as exc:
            print("api-style-decisions: %s" % exc, file=sys.stderr)
            return 2
    print("api-style-decisions: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
