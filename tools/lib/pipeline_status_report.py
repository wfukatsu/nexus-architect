"""One-shot renders of a phase tree: ANSI text, JSON, Markdown.

Non-interactive counterpart of pipeline_status_view.py — this is what the agent runs
in-session (--once) and what --json / --md emit for other programs and reports. NX_VIEW
picks which of that module's three trees is rendered: the product pipeline, the architect
pipeline, or code generation (both plugins' codegen phases).

Usage: pipeline_status_report.py <project-dir>
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pipeline_status_data as P  # noqa: E402
import backlog_status_data as B  # noqa: E402  (backlog summary line only)
import token_cost_data as D  # noqa: E402

PROJ = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("NX_PROJECT_DIR", ".")
env = os.environ.get
LANG = env("NX_LANG", "en")
WIDTH = int(env("NX_WIDTH", "100") or 100)
COLOR = env("NX_COLOR", "0") == "1"
JSON_OUT = env("NX_JSON", "0") == "1"
MD_OUT = env("NX_MD", "")
PLUGIN = env("NX_PLUGIN", "") or None
TIER = env("NX_GROUP", "") or None
PHASE_FILTER = env("NX_PHASE", "") or None
VIEW = env("NX_VIEW", "") or "pipeline"

T = P.labels(LANG)


def derive():
    """The state NX_VIEW asked for: one plugin's pipeline, or the codegen tree."""
    if VIEW == "codegen":
        return P.derive_codegen(PROJ)
    plugin = PLUGIN or (VIEW if VIEW in P.PLUGINS else None)
    return P.derive_all(PROJ, plugin=plugin)

DIM, BOLD, CYAN, GREEN, YELLOW, RED, MAGENTA = "2", "1", "36", "32", "33", "31", "35"
STATUS_ANSI = {"pending": DIM, "in_progress": YELLOW, "completed": GREEN,
               "failed": RED, "skipped": DIM, "stale": MAGENTA}


def c(code, text):
    return "\033[%sm%s\033[0m" % (code, text) if COLOR else str(text)


def phase_marks(phase):
    """The compact flag column: drift, gate, optional."""
    marks = []
    if phase["drift"]:
        marks.append(P.PG["drift"])
    if phase["gate"]:
        marks.append(P.PG["gate"])
    if phase["optional"] and not phase["drift"] and not phase["gate"]:
        marks.append("?")
    return "".join(marks)


def stale_note(state, phase):
    """'analyze (upstream 08-06 14:20)' — what invalidated a stale phase."""
    T = P.labels(LANG)
    causes = phase["stale_by"] + phase["stale_inherited"]
    when = ""
    if phase["stale_at"]:
        when = " %s %s" % (T["stale_changed"], datetime.fromtimestamp(
            phase["stale_at"]).strftime("%m-%d %H:%M"))
    return "%s <- %s%s" % (phase["name"], ", ".join(causes), when)


def activity_cell(phase, now):
    if phase["active"]:
        return "%s %s" % (P.PG["active"], T["ago"] % P.rel_time(phase["last_activity"], now))
    if phase["last_activity"]:
        return T["ago"] % P.rel_time(phase["last_activity"], now)
    return ""


def visible_phases(state):
    """The phases --group / --phase leave, in draw order — the one visibility rule.

    Every renderer walks this, so the filters narrow the JSON exactly as they narrow the
    tree instead of the two disagreeing about what the flags mean.
    """
    out = []
    for row, _, _ in P.flatten(state, tier_filter=TIER):
        if row["kind"] != "phase":
            continue
        if PHASE_FILTER and row["phase"]["name"] != PHASE_FILTER:
            continue
        out.append(row["phase"])
    return out


def rows_for(state):
    """(left, counts, marks, status, activity, cost, style_status) per visible row."""
    now = datetime.now(timezone.utc).timestamp()
    out = []
    for row, depth, stack in P.flatten(state, tier_filter=TIER):
        if row["kind"] == "group":
            if PHASE_FILTER and not any(p["name"] == PHASE_FILTER
                                        for p in row["phases"]):
                continue                       # a group with nothing left to show
            done, total = P.group_counts(row["group"])
            out.append((P.group_title(T, row["key"]), "%d/%d" % (done, total),
                        "", None, "", "", None))
            continue
        phase = row["phase"]
        if PHASE_FILTER and phase["name"] != PHASE_FILTER:
            continue
        out.append((B.tree_prefix(depth, stack) + phase["name"],
                    "%d/%d" % (phase["written"], phase["declared"])
                    if phase["declared"] else "",
                    phase_marks(phase),
                    phase,
                    activity_cell(phase, now),
                    D.money(phase["cost_usd"]) if phase["cost_usd"] else "",
                    phase["display_status"]))
    return out


def view_title(state):
    """'Architect Pipeline' / 'Code Generation' — what this render is of."""
    return T.get("title_%s" % state["plugin"], T["title"])


def header_lines(state):
    lines = []
    s = state["summary"]
    lines.append(c(BOLD, "%s %s %s" % (state["project"], D.G["sep"], view_title(state))))
    frac = s["completed"] / s["total"] if s["total"] else 0
    counts = (" %s " % D.G["sep"]).join(
        "%s %d" % (st, s["by_status"][st]) for st in P.DISPLAY_STATUSES
        if s["by_status"][st])
    lines.append("%s %d/%d %s  %s  %s" % (
        T["phases"], s["completed"], s["total"], T["done"],
        D.bar(frac, min(24, WIDTH // 4)), counts))

    line = []
    if state["current"]:
        line.append("%s %s %s" % (P.PG["current"], T["current"], state["current"]))
    if state["next"]:
        line.append("%s: %s" % (T["next"], state["next"]))
    if s["latest_activity"]:
        line.append(T["ago"] % P.rel_time(s["latest_activity"]))
    if line:
        lines.append(c(CYAN, (" %s " % D.G["sep"]).join(line)))

    gate = state["gate"]
    if gate:
        style = GREEN if gate["verdict"] == "go" else YELLOW
        note = "  %s %d" % (T["open_assumptions"], len(gate["open_assumptions"])) \
            if gate["open_assumptions"] else ""
        lines.append(c(style, "%s %s: %s%s" % (P.PG["gate"], T["gate"],
                                               gate["verdict"], note)))

    backlog = state["backlog"]
    if backlog:
        lines.append(c(DIM, "%s %s" % (T["backlog"],
                                       T["issues_done"] % (backlog[0], backlog[1]))))
    meta = []
    if s["total_cost_usd"]:
        meta.append("%s %s" % (T["total_cost"], D.money(s["total_cost_usd"])))
    if state["updated_at"]:
        meta.append("%s %s" % (T["updated"], state["updated_at"]))
    if not state["has_progress"]:
        meta.append(T["no_progress"])
    if meta:
        lines.append(c(DIM, (" %s " % D.G["sep"]).join(meta)))
    return lines


def render_text(state):
    lines = header_lines(state)
    lines.append(D.hrule(min(WIDTH, 100)))
    rows = rows_for(state)
    if not rows:
        why = []
        if PHASE_FILTER:
            why.append("--phase=%s" % PHASE_FILTER)
        if TIER:
            why.append("--group=%s" % TIER)
        lines.append(c(DIM, "  %s%s" % (T["empty"],
                                        "  (%s)" % " ".join(why) if why else "")))
        if TIER == "extension" and state["plugin"] == "product":
            lines.append(c(DIM, "  %s" % T["no_extension_tier"]))
        elif not why and state["plugin"] in ("product", "architect"):
            lines.append(c(DIM, "  %s" % T["no_%s" % state["plugin"]]))
        return "\n".join(lines)
    name_w = max((D.dw(r[0]) for r in rows), default=0)
    name_w = min(name_w, max(20, WIDTH - 46))
    for name, counts, marks, phase, activity, cost, status in rows:
        if phase is None:                      # group header
            lines.append(c(BOLD, "%s  %s" % (D.pad(D.clip(name, name_w), name_w),
                                             D.pad(counts, 6, "r"))))
            continue
        status_txt = "%s %s" % (P.PG[status], status)
        lines.append("%s  %s %s %s %s %s %s" % (
            D.pad(D.clip(name, name_w), name_w),
            P.output_bar(phase),
            D.pad(counts, 5, "r"),
            D.pad(marks, 2),
            D.pad(c(STATUS_ANSI[status], status_txt), 13 + (9 if COLOR else 0)),
            D.pad(activity, 10),
            D.pad(cost, 8, "r")))
    # The per-phase footers report on what was asked for: with a filter active they
    # cover the rows on screen, not phases the reader deliberately narrowed away.
    shown = visible_phases(state)
    stale = [p for p in shown if p["stale"]]
    if stale:
        lines.append(c(MAGENTA, "%s (%s):" % (P.STALE, T["stale_hint"])))
        for phase in stale[:8]:
            lines.append(c(MAGENTA, "  " + stale_note(state, phase)))
        if len(stale) > 8:
            lines.append(c(MAGENTA, "  ... +%d" % (len(stale) - 8)))
    drifted = [p["name"] for p in shown if p["drift"]]
    if drifted:
        lines.append(c(YELLOW, "drift: %s" % ", ".join(sorted(drifted))))
    failed = [p["name"] for p in shown if p["status"] == "failed"]
    if failed:
        lines.append(c(RED, "failed: %s" % ", ".join(sorted(failed))))
    for err in state["errors"][:5]:
        lines.append(c(RED, "%s: %s" % (T["errors"], err)))
    for warn in state["warnings"][:5]:
        lines.append(c(YELLOW, "%s: %s" % (T["warnings"], warn)))
    return "\n".join(lines)


def render_json(state):
    phases = []
    for p in visible_phases(state):
        name = p["name"]
        phases.append({
            "name": name, "group": p["group"], "plugin": P.phase_plugin(state, p),
            "section": p["section"], "tier": p["tier"], "model": p["model"],
            "status": p["status"], "display_status": p["display_status"],
            "stale": p["stale"], "stale_by": p["stale_by"] + p["stale_inherited"],
            "stale_at": datetime.fromtimestamp(
                p["stale_at"], timezone.utc).isoformat(timespec="seconds")
            if p["stale_at"] else None,
            "source": p["source"], "drift": p["drift"],
            "excluded": p["excluded"], "optional": p["optional"], "gate": p["gate"],
            "outputs_written": p["written"], "outputs_declared": p["declared"],
            "outputs": p["outputs"], "depends_on": p["depends_on"],
            "blocked_by": p["blocked_by"], "runnable": p["runnable"],
            "active": p["active"],
            "last_activity": datetime.fromtimestamp(
                p["last_activity"], timezone.utc).isoformat(timespec="seconds")
            if p["last_activity"] else None,
            "cost_usd": p["cost_usd"], "started_at": p["started_at"],
            "completed_at": p["completed_at"], "updated_at": p["updated_at"],
            "note": p["note"], "summary": p["summary"],
            "command": "%s%s" % (P.PLUGINS[P.phase_plugin(state, p)]["prefix"], name),
        })
    backlog = state["backlog"]
    return json.dumps({
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "view": state["plugin"], "section": state["section"],
        "plugin": state["plugin"], "project": state["project"],
        "has_progress": state["has_progress"], "options": state["options"],
        # What the reader is looking at, so a narrowed `phases` list is never mistaken
        # for the whole pipeline. `summary` always covers this view's whole tree.
        "filters": {"group": TIER, "phase": PHASE_FILTER},
        "summary": state["summary"], "gate": state["gate"],
        "current": state["current"], "next": state["next"],
        "backlog": {"issues_done": backlog[0], "issues_total": backlog[1]}
        if backlog else None,
        "errors": state["errors"], "warnings": state["warnings"],
        "phases": phases,
    }, ensure_ascii=False, indent=2)


def render_md(state, text):
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    heading = {"product": "Product Pipeline Progress",
               "architect": "Architect Pipeline Progress",
               "codegen": "Code Generation Progress"}.get(state["plugin"],
                                                          "Pipeline Progress")
    fm = "\n".join((
        "---",
        'title: "%s"' % heading,
        "schema_version: 1",
        'phase: "Pipeline Status"',
        "skill: report-status",
        'generated_at: "%s"' % now,
        "input_files:",
        "  - work/pipeline-progress.json",
        "---",
    ))
    return "%s\n\n# %s\n\n```text\n%s\n```\n" % (fm, heading, D.plain(text))


def main():
    state = derive()
    # A misspelled --phase used to render an empty tree and exit 0, which reads like
    # "this phase has nothing" rather than "no such phase".
    if PHASE_FILTER and PHASE_FILTER not in state["phases"]:
        print("nexus-status: %s" % (T["unknown_phase"] % PHASE_FILTER), file=sys.stderr)
        print("nexus-status: %s" % (T["known_phases"] % (
            state["plugin"], ", ".join(state["phases"]))), file=sys.stderr)
        return 2
    if JSON_OUT:
        print(render_json(state))
        return 0
    text = render_text(state)
    if MD_OUT:
        path = MD_OUT if os.path.isabs(MD_OUT) else os.path.join(PROJ, MD_OUT)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        global COLOR
        color, COLOR = COLOR, False
        plain_text = render_text(state)
        COLOR = color
        with open(path, "w", encoding="utf-8") as f:
            f.write(render_md(state, plain_text))
        print("nexus-status: wrote %s" % path, file=sys.stderr)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
