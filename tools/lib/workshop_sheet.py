#!/usr/bin/env python3
"""Workshop mode: the questions a dialogue phase would ask, as a sheet several people answer.

`AskUserQuestion` reaches one person in one session. A workshop sheet reaches the room: the
skill records its questions in the store as usual (rules/open-questions.md §6), renders them
to `work/workshop/<phase>.md`, stamps the phase `awaiting_approval` and stops; people answer in
the sheet (tick an option, or write under Answer, and sign `Answered by:`); the next run
collects the answers into the store and the audit log and continues (rules/open-questions.md §9).

    python3 tools/lib/workshop_sheet.py <project_dir> render <phase> [ids=OQ-001,OQ-002] [plugin=…]
    python3 tools/lib/workshop_sheet.py <project_dir> collect <phase> [plugin=…]

`render` takes the listed ids, or every `unasked` / `deferred` row when none are listed, and
appends one QUESTION_ASKED per question (detail names the sheet). `collect` reads the sheet,
writes each answer into the store row (`answered`, the answer, the role when given), appends
QUESTION_ANSWERED with the signer as actor, and prints JSON: {"answered": [...], "pending":
[...], "sheet": path}. Exit 0; 1 when the store or the sheet is missing; 2 on a usage error.
A question with no tick and no answer text stays pending — the phase stays `awaiting_approval`.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import open_questions as Q  # noqa: E402
try:
    import audit_log as AUDIT  # noqa: E402
except Exception:  # pragma: no cover - the log is evidence, never a gate
    AUDIT = None

SHEET_DIR = os.path.join("work", "workshop")
OPTION_SPLIT = re.compile(r"\s*(?:/|;|\|)\s*")


def sheet_path(project_dir, phase):
    return os.path.join(project_dir, SHEET_DIR, "%s.md" % phase)


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def options_of(row):
    raw = (row.get("options offered") or "").strip()
    if not raw:
        return []
    return [o.strip() for o in OPTION_SPLIT.split(raw) if o.strip()]


def render(project_dir, phase, ids=None, plugin=None):
    rows, exists = Q.read_store(project_dir)
    if not exists:
        raise FileNotFoundError("no work/context.md under %s" % project_dir)
    by_id = {r["id"]: r for r in rows}
    if ids:
        missing = [i for i in ids if i not in by_id]
        if missing:
            raise KeyError("not in the store: %s" % ", ".join(missing))
        chosen = [by_id[i] for i in ids]
    else:
        chosen = [r for r in rows if r["status_word"] in ("unasked", "deferred")]
    path = sheet_path(project_dir, phase)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "---",
        'title: "Workshop sheet — %s"' % phase,
        "phase: %s" % phase,
        "generated_at: \"%s\"" % now_iso(),
        "questions: [%s]" % ", ".join(r["id"] for r in chosen),
        "schema_version: 1",
        "---",
        "",
        "# Workshop sheet: %s" % phase,
        "",
        "> How to answer: tick one option (`- [x]`) or write the answer under `Answer:`, then put",
        "> your name after `Answered by:` and, if you want, your decision role after `Role:`",
        "> (docs/decision-roles.md). Leave a question untouched to leave it open. The next run of",
        "> the phase collects this sheet.",
        "",
    ]
    for r in chosen:
        lines.append("## %s — %s" % (r["id"], r.get("question", "")))
        lines.append("")
        if r.get("owner") or r.get("role"):
            lines.append("> for: %s" % " ".join(x for x in (r.get("owner", ""),
                                                           ("[%s]" % r["role"]) if r.get("role") else "") if x))
            lines.append("")
        opts = options_of(r)
        if opts:
            lines.append("Options:")
            for o in opts:
                lines.append("- [ ] %s" % o)
            lines.append("- [ ] Other (write it under Answer)")
            lines.append("")
        lines += ["Answer:", "", "Answered by:", "", "Role:", ""]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    if AUDIT is not None and chosen:
        try:
            actor = AUDIT.actor_name(project_dir)
            AUDIT.append_events(project_dir, [
                AUDIT.make_event("QUESTION_ASKED", phase=phase, plugin=plugin, actor=actor,
                                 ref=r["id"], detail="workshop sheet %s" % os.path.relpath(path, project_dir))
                for r in chosen])
        except Exception:
            pass
    return path, [r["id"] for r in chosen]


def parse_sheet(text):
    """{OQ-id: {"answer", "answered_by", "role"}} from a sheet; empty strings when blank."""
    sections = re.split(r"^## (OQ-\d{3,}) — .*$", text, flags=re.M)
    out = {}
    for i in range(1, len(sections), 2):
        qid, body = sections[i], sections[i + 1]
        ticked = re.findall(r"^- \[[xX]\] (.*)$", body, re.M)
        ticked = [t for t in ticked if not t.startswith("Other (")]
        fields = {"answer": "", "answered_by": "", "role": ""}
        for key, label in (("answer", "Answer"), ("answered_by", "Answered by"), ("role", "Role")):
            m = re.search(r"^%s:[ \t]*(.*?)\n(.*?)(?=^(?:Answer|Answered by|Role):|\Z)" % label,
                          body, re.M | re.S)
            if m:
                value = (m.group(1) + "\n" + m.group(2)).strip()
                fields[key] = " ".join(value.split())
        if not fields["answer"] and ticked:
            fields["answer"] = ticked[0]
        out[qid] = fields
    return out


def write_answers(project_dir, answers):
    """Set Status / Answer (/ Role) on each store row in place; returns the ids written."""
    path = os.path.join(project_dir, Q.STORE)
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    header, written, out = None, [], []
    for line in lines:
        cells = Q.split_cells(line) if line.lstrip().startswith("|") else None
        if cells and cells[0].strip("`").lower() in Q.ID_HEADERS:
            header = ["id"] + [c.strip("`").lower() for c in cells[1:]]
        elif header and cells and cells[0] in answers and "status" in header and "answer" in header:
            a = answers[cells[0]]
            cells = cells + [""] * (len(header) - len(cells))
            cells[header.index("status")] = "answered"
            cells[header.index("answer")] = a["answer"]
            if a.get("role") and "role" in header:
                cells[header.index("role")] = a["role"]
            line = "| " + " | ".join(cells) + " |"
            written.append(cells[0])
        out.append(line)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + ("\n" if lines else ""))
    return written


def collect(project_dir, phase, plugin=None):
    path = sheet_path(project_dir, phase)
    if not os.path.isfile(path):
        raise FileNotFoundError("no sheet %s" % path)
    rows, exists = Q.read_store(project_dir)
    if not exists:
        raise FileNotFoundError("no work/context.md under %s" % project_dir)
    with open(path, encoding="utf-8") as fh:
        parsed = parse_sheet(fh.read())
    answered = {qid: f for qid, f in parsed.items() if f["answer"]}
    pending = [qid for qid, f in parsed.items() if not f["answer"]]
    written = write_answers(project_dir, answered) if answered else []
    if AUDIT is not None and written:
        try:
            AUDIT.append_events(project_dir, [
                AUDIT.make_event("QUESTION_ANSWERED", phase=phase, plugin=plugin,
                                 actor=answered[qid]["answered_by"] or AUDIT.actor_name(project_dir),
                                 ref=qid, detail=answered[qid]["answer"])
                for qid in written])
        except Exception:
            pass
    return {"answered": [{"id": qid, "answer": answered[qid]["answer"],
                          "answered_by": answered[qid]["answered_by"], "role": answered[qid]["role"]}
                         for qid in written],
            "pending": pending, "sheet": os.path.relpath(path, project_dir)}


def main(argv):
    if len(argv) < 3:
        sys.stderr.write(__doc__)
        return 2
    project, verb, phase = argv[0], argv[1], argv[2]
    opts = {}
    for arg in argv[3:]:
        key, sep, value = arg.partition("=")
        if not sep or key not in ("ids", "plugin"):
            sys.stderr.write("workshop_sheet: expected ids= or plugin=, got %r\n" % arg)
            return 2
        opts[key] = value
    if not os.path.isdir(project):
        sys.stderr.write("workshop_sheet: not a directory: %s\n" % project)
        return 2
    try:
        if verb == "render":
            ids = [i.strip() for i in opts.get("ids", "").split(",") if i.strip()] or None
            path, chosen = render(project, phase, ids, opts.get("plugin"))
            sys.stdout.write(json.dumps({"sheet": os.path.relpath(path, project), "questions": chosen},
                                        ensure_ascii=False) + "\n")
            return 0
        if verb == "collect":
            sys.stdout.write(json.dumps(collect(project, phase, opts.get("plugin")),
                                        ensure_ascii=False) + "\n")
            return 0
    except FileNotFoundError as exc:
        sys.stderr.write("workshop_sheet: %s\n" % exc)
        return 1
    except KeyError as exc:
        sys.stderr.write("workshop_sheet: %s\n" % exc.args[0])
        return 2
    sys.stderr.write("workshop_sheet: verb must be render or collect\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
