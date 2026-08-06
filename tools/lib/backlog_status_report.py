"""One-shot renders of the backlog-status tree: ANSI text, JSON, Markdown.

Non-interactive counterpart of backlog_status_view.py — this is what the agent runs
in-session (--once) and what --json / --md emit for other programs and reports.

Usage: backlog_status_report.py <backlog-manifest.json>
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backlog_status_data as B  # noqa: E402
import token_cost_data as D  # noqa: E402

MANIFEST = sys.argv[1]
env = os.environ.get
LANG = env("NX_LANG", "en")
WIDTH = int(env("NX_WIDTH", "100") or 100)
COLOR = env("NX_COLOR", "0") == "1"
JSON_OUT = env("NX_JSON", "0") == "1"
MD_OUT = env("NX_MD", "")
SYNC = env("NX_SYNC", "0") == "1"
PROJ = env("NX_PROJECT_DIR", ".")
EPIC_FILTER = env("NX_EPIC", "") or None

T = B.labels(LANG)

DIM, BOLD, CYAN, GREEN, YELLOW, RED, MAGENTA = "2", "1", "36", "32", "33", "31", "35"
STATUS_ANSI = {"todo": DIM, "doing": YELLOW, "review": CYAN, "done": GREEN,
               "blocked": RED}


def c(code, text):
    return "\033[%sm%s\033[0m" % (code, text) if COLOR else str(text)


def status_cell(state):
    glyph = B.SG[state["status"]]
    text = "%s %s" % (glyph, state["status"])
    return c(STATUS_ANSI[state["status"]], text)


def visible_nodes(children, states):
    """The rows an --epic filter leaves, in draw order — the one visibility rule.

    Every renderer walks this, so `--epic` narrows the JSON exactly as it narrows the
    tree instead of the two disagreeing about what "limit to one Epic" means.
    """
    return B.flatten_tree(children, states, epic_filter=EPIC_FILTER)


def tree_rows(children, states):
    """(prefix+title, markers, counts, state) per visible node, fully expanded."""
    rows = []
    for node, depth, stack in visible_nodes(children, states):
        lid = node["local_id"]
        state = states[lid]
        marks = []
        if state["followup"]:
            marks.append(B.SG["followup"])
        if state["drift"]:
            marks.append(B.SG["drift"])
        counts = ""
        if node.get("level") in ("epic", "sub-epic"):
            done, total = B.descendant_issue_counts(node, children, states)
            counts = "%d/%d" % (done, total)
        rows.append((B.tree_prefix(depth, stack) + "%s  %s" % (lid, node.get("title", "")),
                     " ".join(marks), counts, state))
    return rows


def render_text(manifest, children, states, summary, pipeline, queue_count, synced_at):
    lines = []
    project = manifest.get("project") or os.path.basename(PROJ)
    lines.append(c(BOLD, "%s %s %s" % (project, D.G["sep"], T["title"])))
    bar_w = min(24, WIDTH // 4)
    frac = summary["issues_done"] / summary["issues_total"] if summary["issues_total"] else 0
    counts = (" %s " % D.G["sep"]).join(
        "%s %d" % (s, summary["by_status"][s]) for s in B.STATUSES)
    lines.append("%s %d/%d %s  %s  %s" % (
        T["issues"], summary["issues_done"], summary["issues_total"], T["done"],
        D.bar(frac, bar_w), counts))
    if pipeline:
        cur = " %s %s" % (B.SG["current"], pipeline["current"]) if pipeline["current"] else ""
        if pipeline.get("stale"):
            cur += " %s %d" % (B.SG["stale"], pipeline["stale"])
        lines.append(c(DIM, "%s %d/%d%s" % (T["pipeline"], pipeline["completed"],
                                            pipeline["total"], cur)))
    sync_note = "%s %s" % (T["synced"], synced_at.strftime("%H:%M")) if synced_at \
        else T["not_synced"]
    lines.append(c(DIM, sync_note))
    lines.append(D.hrule(min(WIDTH, 100)))

    rows = tree_rows(children, states)
    if not rows:
        lines.append(c(DIM, "  %s%s" % (T["empty"], "  (--epic=%s)" % EPIC_FILTER
                                        if EPIC_FILTER else "")))
        return "\n".join(lines)
    title_w = max(D.dw(r[0]) for r in rows) if rows else 0
    title_w = min(title_w, WIDTH - 30)
    for title, marks, counts, state in rows:
        lines.append("%s  %s %s %s %s" % (
            D.pad(D.clip(title, title_w), title_w),
            D.pad(counts, 5, "r"),
            D.pad(marks, 2),
            D.pad(status_cell(state), 12 + (9 if COLOR else 0)),
            B.stage_boxes(state["stages"])))
    if queue_count:
        lines.append(c(MAGENTA, "%s: %s" % (T["queue"], T["queued_entries"] % queue_count)))
    blocked = [lid for lid, s in states.items() if s["status"] == "blocked"]
    if blocked:
        lines.append(c(RED, "blocked: %s" % ", ".join(sorted(blocked))))
    drifted = [lid for lid, s in states.items() if s["drift"]]
    if drifted:
        lines.append(c(YELLOW, "drift (tracker wins): %s" % ", ".join(sorted(drifted))))
    return "\n".join(lines)


def render_json(manifest, children, states, summary, pipeline, queue_count, synced_at):
    visible = {n["local_id"] for n, _, _ in visible_nodes(children, states)}
    nodes = []
    for n in manifest["nodes"]:
        lid = n.get("local_id")
        if lid not in states or lid not in visible:
            continue
        s = states[lid]
        nodes.append({
            "local_id": lid, "level": n.get("level"), "title": n.get("title"),
            "parent_local_id": n.get("parent_local_id"),
            "status": s["status"], "source": s["source"], "drift": s["drift"],
            "stages": s["stages"], "followup": s["followup"],
            "iid": (n.get("remote") or {}).get("iid"),
            "url": (n.get("remote") or {}).get("url"),
            "pr_url": (n.get("pr") or {}).get("url"),
            "updated_at": (n.get("impl") or {}).get("updated_at"),
        })
    return json.dumps({
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "platform": manifest.get("platform"), "project": manifest.get("project"),
        "group": manifest.get("group"), "summary": summary,
        # What the reader is looking at, so a narrowed `nodes` list is never mistaken
        # for the whole backlog. `summary` always covers the whole manifest.
        "filters": {"epic": EPIC_FILTER},
        "pipeline": pipeline, "followup_queue": queue_count,
        "synced_at": synced_at.isoformat(timespec="seconds") if synced_at else None,
        "nodes": nodes,
    }, ensure_ascii=False, indent=2)


def render_md(manifest, children, states, summary, pipeline, queue_count, text):
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    fm = "\n".join((
        "---",
        'title: "Backlog Delivery Status"',
        "schema_version: 1",
        'phase: "Backlog Delivery"',
        "skill: report-backlog-status",
        'generated_at: "%s"' % now,
        "input_files:",
        "  - reports/backlog/backlog-manifest.json",
        "---",
    ))
    return "%s\n\n# Backlog Delivery Status\n\n```text\n%s\n```\n" % (fm, D.plain(text))


def main():
    manifest = B.load_manifest(MANIFEST)
    if manifest is None:
        print("backlog-status: unreadable manifest: %s" % MANIFEST, file=sys.stderr)
        return 1
    sync_cache, synced_at = None, None
    if SYNC:
        try:
            sync_cache = B.sync_tracker(manifest)
            synced_at = datetime.now()
        except RuntimeError as exc:
            print("backlog-status: %s: %s" % (T["sync_failed"], exc), file=sys.stderr)
    by_id, children, states = B.derive_all(manifest, sync_cache)
    # A misspelled --epic used to render an empty tree and exit 0, which reads like
    # "this Epic has nothing in it" rather than "no such Epic".
    if EPIC_FILTER:
        roots = [n["local_id"] for n in children.get(None, [])]
        if EPIC_FILTER not in roots:
            print("backlog-status: %s" % (T["unknown_epic"] % EPIC_FILTER),
                  file=sys.stderr)
            print("backlog-status: %s" % (T["known_epics"] % (", ".join(roots) or "-")),
                  file=sys.stderr)
            return 2
    summary = B.overall_summary(manifest, states)
    pipeline = B.load_pipeline(PROJ)
    queue_count = B.followup_queue_count(PROJ)

    if JSON_OUT:
        print(render_json(manifest, children, states, summary, pipeline,
                          queue_count, synced_at))
        return 0
    text = render_text(manifest, children, states, summary, pipeline,
                       queue_count, synced_at)
    if MD_OUT:
        path = MD_OUT if os.path.isabs(MD_OUT) else os.path.join(PROJ, MD_OUT)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # Strip ANSI for the file: re-render plain.
        global COLOR
        color, COLOR = COLOR, False
        plain_text = render_text(manifest, children, states, summary, pipeline,
                                 queue_count, synced_at)
        COLOR = color
        with open(path, "w", encoding="utf-8") as f:
            f.write(render_md(manifest, children, states, summary, pipeline,
                              queue_count, plain_text))
        print("backlog-status: wrote %s" % path, file=sys.stderr)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
