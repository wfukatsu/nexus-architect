#!/usr/bin/env python3
"""The Open Questions store, read by header and grouped for whoever has to answer.

`work/context.md` § Open Questions is one Markdown table (rules/open-questions.md §6). This
reads it the way the report builder and the UI views do — by its header, the first cell `ID`
or `OQ-###` — and groups the rows so each stakeholder sees only what waits on them:

    python3 tools/lib/open_questions.py <project_dir> [by=role|owner|status|phase] [status=open|all|<name>] [format=text|json]

`status=open` (the default) is every row that is not `answered`. `by=role` groups by the
`Role` column (docs/decision-roles.md); rows without one fall under "(no role)". `by=phase`
groups by the phase named in the Impact column, when any. Exit 0 with output, 1 when the
store does not exist, 2 on a usage error. Never writes.
"""
import json
import os
import re
import sys

ID_HEADERS = ("id", "oq-###")
OPEN = "open"
STORE = os.path.join("work", "context.md")


def split_cells(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", s)]


def status_word(raw):
    m = re.search(r"[a-z-]+", (raw or "").strip("*` ").lower())
    return m.group(0) if m else (raw or "")


def read_store(project_dir):
    """(rows, exists): the latest row per OQ- id, every column kept under its lower-cased
    header name (`id`, `question`, `status`, `answer`, `options offered`, `owner`, `impact`,
    `asked at`, `role`), plus `status_word`. `exists` is False when the file is absent."""
    path = os.path.join(project_dir, STORE)
    if not os.path.isfile(path):
        return [], False
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    header, latest = None, {}
    for line in lines:
        if not line.lstrip().startswith("|"):
            continue
        cells = split_cells(line)
        if cells and cells[0].strip("`").lower() in ID_HEADERS:
            header = ["id"] + [c.strip("`").lower() for c in cells[1:]]
            continue
        if not header or not cells or not re.fullmatch(r"OQ-\d{3,}", cells[0]):
            continue
        row = dict(zip(header, cells))
        row["id"] = cells[0]
        row["status_word"] = status_word(row.get("status", ""))
        latest[cells[0]] = row
    return list(latest.values()), True


def select(rows, status=OPEN):
    if status == "all":
        return list(rows)
    if status == OPEN:
        return [r for r in rows if r["status_word"] != "answered"]
    return [r for r in rows if r["status_word"] == status]


def phase_of(row):
    m = re.search(r"\b([a-z][a-z0-9]*(?:-[a-z0-9]+)+)\b", row.get("impact", ""))
    return m.group(1) if m else ""


def group(rows, by="role"):
    """{key: [rows]} in first-seen order; an empty key is shown as "(no <by>)"."""
    keys = {"role": lambda r: r.get("role", ""), "owner": lambda r: r.get("owner", ""),
            "status": lambda r: r["status_word"], "phase": phase_of}
    if by not in keys:
        raise ValueError("by must be one of %s" % ", ".join(keys))
    out = {}
    for row in rows:
        key = (keys[by](row) or "").strip() or "(no %s)" % by
        out.setdefault(key, []).append(row)
    return out


def render_text(groups, by):
    lines = []
    for key, rows in groups.items():
        lines.append("%s: %s (%d)" % (by, key, len(rows)))
        for r in rows:
            who = " ".join(x for x in (r.get("owner", ""), ("[%s]" % r["role"]) if r.get("role") else "")
                           if x)
            lines.append("  %s  %-9s %s%s" % (r["id"], r["status_word"], r.get("question", ""),
                                               ("  — " + who) if who and by != "owner" else ""))
    return "\n".join(lines) if lines else "no open questions"


def main(argv):
    if not argv:
        sys.stderr.write(__doc__)
        return 2
    project = argv[0]
    opts = {"by": "role", "status": OPEN, "format": "text"}
    for arg in argv[1:]:
        key, sep, value = arg.partition("=")
        if not sep or key not in opts:
            sys.stderr.write("open_questions: expected by=, status= or format=, got %r\n" % arg)
            return 2
        opts[key] = value
    if opts["format"] not in ("text", "json"):
        sys.stderr.write("open_questions: format must be text or json\n")
        return 2
    rows, exists = read_store(project)
    if not exists:
        sys.stderr.write("open_questions: no %s under %s\n" % (STORE, project))
        return 1
    try:
        groups = group(select(rows, opts["status"]), opts["by"])
    except ValueError as exc:
        sys.stderr.write("open_questions: %s\n" % exc)
        return 2
    if opts["format"] == "json":
        sys.stdout.write(json.dumps({"by": opts["by"], "status": opts["status"],
                                     "groups": groups}, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(render_text(groups, opts["by"]) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
