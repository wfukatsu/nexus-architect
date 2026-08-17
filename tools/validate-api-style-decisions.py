#!/usr/bin/env python3
"""Validate reports/03_design/api-style-decisions.json."""

import argparse
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from api_style_decisions import MAX_DOCUMENT_BYTES, render_markdown, validate_document  # noqa: E402


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
        if os.path.getsize(args.path) > MAX_DOCUMENT_BYTES:
            print("api-style-decisions: input exceeds %d bytes" % MAX_DOCUMENT_BYTES,
                  file=sys.stderr)
            return 1
        with open(args.path, encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print("api-style-decisions: %s" % exc, file=sys.stderr)
        return 2
    project_dir = os.path.abspath(os.path.join(os.path.dirname(args.path), "..", ".."))
    plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    okf_root = os.path.join(plugin_root, "knowledge", "okf-scalardb-scalardl", "okf")
    if not os.path.isdir(okf_root):
        # A skipped check is reported, never silent: the run is weaker than a full one, and the
        # reader has to know that rather than read a clean exit as full coverage.
        print("api-style-decisions: note: the OKF knowledge bundle is not checked out at %s, "
              "so native-GraphQL pinned-line resolution was not verified. Run "
              "`git submodule update --init knowledge/okf-scalardb-scalardl` or "
              "`tools/update-okf-bundle.sh` to enable it." % okf_root, file=sys.stderr)
    errors = validate_document(document, project_dir=project_dir, okf_root=okf_root)
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        print("api-style-decisions: %d error(s)" % len(errors), file=sys.stderr)
        return 1
    if args.render_markdown:
        temp_path = None
        try:
            rendered = render_markdown(document, args.lang)
            destination = os.path.abspath(args.render_markdown)
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            fd, temp_path = tempfile.mkstemp(prefix=".api-style-decisions-", suffix=".tmp",
                                             dir=os.path.dirname(destination), text=True)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(rendered)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, destination)
            temp_path = None
        except (OSError, ValueError, RecursionError) as exc:
            print("api-style-decisions: %s" % exc, file=sys.stderr)
            return 2
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
    print("api-style-decisions: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
