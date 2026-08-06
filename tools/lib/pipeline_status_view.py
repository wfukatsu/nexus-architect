"""The pipeline tab of the nexus-status dashboard.

The product / architect phase tree grouped by category (the architect manual extension
tier is its own foldable group), showing each phase's status, how many of its declared
outputs exist, whether it is producing tokens right now, and its recorded cost. The
detail pane shows the declared outputs with their real state, unmet dependencies, the
registry timestamps and note, and the product validation gate.

The rendering shell (layout, menus, keys, refresh) lives in status_tui.App; this module
only answers what to show. Its state rules live in pipeline_status_data.py.
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backlog_status_data as B  # noqa: E402  (tree glyphs + backlog summary line)
import pipeline_status_data as P  # noqa: E402
import status_tui as S  # noqa: E402
import token_cost_data as D  # noqa: E402

env = os.environ.get
PROJ = env("NX_PROJECT_DIR", ".")
PLUGIN = env("NX_PLUGIN", "") or None
TIER = env("NX_GROUP", "") or None

WATCH = ("work/pipeline-progress.json", "work/token-usage.json",
         "work/token-usage.jsonl")


class PipelineView(S.BaseView):
    name = "pipeline"

    def __init__(self, project_dir, lang):
        S.BaseView.__init__(self)
        self.project_dir = project_dir
        self.T = P.labels(lang)
        self.title = self.T["title"]
        self.state = None
        self.backlog = None
        self.available = os.path.isfile(
            os.path.join(project_dir, "work", "pipeline-progress.json"))
        self.load()

    # ------------------------------------------------------------------ data
    def watch_files(self):
        return WATCH

    def extra_stamp(self):
        """Newest mtime two levels into the output trees.

        A phase writing its third report file changes only the mtime of the directory
        holding it, so watching `reports/` alone would miss it and the tree would sit
        stale until the registry happened to change. Two levels of scandir is a handful
        of stats per poll and catches every phase's declared output directory.
        """
        newest = 0.0
        for top in ("reports", "design-system", "generated"):
            root = os.path.join(self.project_dir, top)
            try:
                entries = list(os.scandir(root))
            except OSError:
                continue
            newest = max(newest, os.path.getmtime(root))
            for entry in entries:
                try:
                    newest = max(newest, entry.stat().st_mtime)
                    if entry.is_dir():
                        for sub in os.scandir(entry.path):
                            newest = max(newest, sub.stat().st_mtime)
                except OSError:
                    continue
        return newest

    def load(self):
        self.state = P.derive_all(self.project_dir, plugin=PLUGIN)
        self.available = self.state["has_progress"] or any(
            p["written"] for p in self.state["phases"].values())
        # One name column for every row, so the status block lines up instead of
        # floating at the far right of a 160-column terminal. Phase rows carry a
        # two-segment tree prefix (a gap for the group level plus the connector).
        prefix_w = D.dw(B.tree_prefix(1, (True, False)))
        self.name_w = max([D.dw(n) + prefix_w for n in self.state["phases"]]
                          + [D.dw(P.group_title(self.T, g["key"]))
                             for g in self.state["groups"]] + [24])
        self.backlog = self.state["backlog"]

    def project_label(self):
        return "%s (%s)" % (self.state["project"], self.state["plugin"])

    def empty_message(self):
        return self.T["no_progress"]

    # ------------------------------------------------------------------ rows
    def rows(self):
        return P.flatten(self.state, self.collapsed, self.status_filter,
                         tier_filter=TIER)

    def row_key(self, row):
        return "%s:%s" % (row["kind"], row["key"])

    def row_style(self, row):
        if row["kind"] == "group":
            return "head"
        return P.PHASE_STYLE.get(row["phase"]["display_status"], "")

    def row_line(self, row, depth, stack, width):
        if row["kind"] == "group":
            done, total = P.group_counts(row["group"])
            fold = " +" if row["key"] in self.collapsed else ""
            left = "%s%s" % (P.group_title(self.T, row["key"]), fold)
            left_w = min(self.name_w, max(10, width - D.dw("  0/0") - 2))
            return "%s  %s" % (D.pad(D.clip(left, left_w), left_w),
                               D.pad("%d/%d" % (done, total), 5, "r"))
        phase = row["phase"]
        now = datetime.now(timezone.utc).timestamp()
        marks = ""
        if phase["drift"]:
            marks = P.PG["drift"]
        elif phase["gate"]:
            marks = P.PG["gate"]
        elif phase["optional"]:
            marks = "?"
        status = phase["display_status"]
        activity = ""
        if phase["active"]:
            activity = "%s %s" % (P.PG["active"],
                                  P.rel_time(phase["last_activity"], now))
        elif phase["last_activity"]:
            activity = P.rel_time(phase["last_activity"], now)
        counts = "%d/%d" % (phase["written"], phase["declared"]) \
            if phase["declared"] else ""
        right = "%s %s %s %s %s %s" % (
            P.output_bar(phase), D.pad(counts, 5, "r"), D.pad(marks, 1),
            D.pad("%s %s" % (P.PG[status], status), 13),
            D.pad(activity, 7),
            D.pad(D.money(phase["cost_usd"]) if phase["cost_usd"] else "", 7, "r"))
        left_w = min(self.name_w, max(10, width - D.dw(right) - 2))
        left = B.tree_prefix(depth, stack) + phase["name"]
        return "%s %s" % (D.pad(D.clip(left, left_w), left_w), right)

    def has_children(self, row):
        return row["kind"] == "group"

    def fold(self, collapse):
        rows = {self.row_key(r[0]): r[0] for r in self.rows()}
        row = rows.get(self.sel_key)
        if row is None:
            return
        if row["kind"] == "group":
            if collapse:
                self.collapsed.add(row["key"])
            else:
                self.collapsed.discard(row["key"])
            return
        if collapse:                       # from a phase, ← jumps to its group header
            group = "extension" if row["phase"]["tier"] == "extension" \
                else row["phase"]["category"]
            self.sel_key = "group:%s" % group

    # ------------------------------------------------------------------ panes
    def header_lines(self, width):
        T = self.T
        state = self.state
        s = state["summary"]
        frac = s["completed"] / s["total"] if s["total"] else 0
        counts = (" %s " % D.G["sep"]).join(
            "%s %d" % (st, s["by_status"][st]) for st in P.DISPLAY_STATUSES
            if s["by_status"][st])
        lines = [("%s %d/%d %s  %s  %s" % (
            T["phases"], s["completed"], s["total"], T["done"],
            D.bar(frac, min(20, width // 5)), counts), "bold")]

        line = []
        if state["current"]:
            line.append("%s %s %s" % (P.PG["current"], T["current"], state["current"]))
        if state["next"]:
            line.append("%s: %s" % (T["next"], state["next"]))
        if s["latest_activity"]:
            line.append(T["ago"] % P.rel_time(s["latest_activity"]))
        if self.status_filter:
            line.append("filter: %s" % self.status_filter)
        lines.append(((" %s " % D.G["sep"]).join(line), "head"))

        gate = state["gate"]
        if gate:
            note = "  %s %d" % (T["open_assumptions"], len(gate["open_assumptions"])) \
                if gate["open_assumptions"] else ""
            lines.append(("%s %s: %s%s" % (P.PG["gate"], T["gate"], gate["verdict"],
                                           note),
                          "accent" if gate["verdict"] == "go" else "warn"))
        meta = []
        if self.backlog:
            meta.append("%s %s" % (T["backlog"],
                                   T["issues_done"] % (self.backlog[0],
                                                       self.backlog[1])))
        if s["total_cost_usd"]:
            meta.append("%s %s" % (T["total_cost"], D.money(s["total_cost_usd"])))
        if not state["has_progress"]:
            meta.append(T["no_progress"])
        if meta:
            lines.append(((" %s " % D.G["sep"]).join(meta), "dim"))
        return lines

    def detail_title(self, row):
        if row["kind"] == "group":
            return P.group_title(self.T, row["key"])
        return row["phase"]["name"]

    def detail_lines(self, row, width):
        T = self.T
        if row["kind"] == "group":
            done, total = P.group_counts(row["group"])
            lines = [("%s %d/%d" % (T["done"], done, total), "head")]
            for phase in row["group"]["phases"]:
                status = phase["display_status"]
                lines.append(("  %s %s %s" % (P.PG[status],
                                              D.pad(phase["name"], 28), status),
                              P.PHASE_STYLE.get(status, "")))
            return lines

        phase = row["phase"]
        lines = []
        src = "%s %s  (%s: %s)" % (T["status"], phase["display_status"], T["source"],
                                   {"progress": T["source_progress"],
                                    "derived": T["source_derived"],
                                    "condition": T["source_condition"]}[phase["source"]])
        lines.append((src, P.PHASE_STYLE.get(phase["display_status"], "")))
        if phase["stale"]:
            if phase["stale_by"]:
                lines.append((T["stale_upstream"] % ", ".join(phase["stale_by"]), "warn"))
            if phase["stale_inherited"]:
                lines.append((T["stale_inherited"] % ", ".join(phase["stale_inherited"]),
                              "warn"))
            if phase["stale_at"]:
                lines.append(("  %s: %s" % (T["stale_changed"], datetime.fromtimestamp(
                    phase["stale_at"]).strftime("%m-%d %H:%M")), "dim"))
            lines.append((T["stale_hint"], "dim"))
        if phase["drift"]:
            lines.append((T["drift_missing"] if phase["drift"] == "outputs-missing"
                          else T["drift_present"], "warn"))
        if phase["excluded"]:
            lines.append((T["skipped_option"] if phase["excluded"] == "option"
                          else T["skipped_condition"], "dim"))
        flags = [T[k] for k in ("optional", "rerunnable", "standalone")
                 if phase[k]]
        if phase["gate"]:
            flags.append(T["gate_phase"])
        meta = "%s %s" % (T["model"], phase["model"] or "-")
        if flags:
            meta += "   %s" % (" %s " % D.G["sep"]).join(flags)
        if phase["cost_usd"]:
            meta += "   %s %s" % (T["cost"], D.money(phase["cost_usd"]))
        lines.append((meta, "dim"))

        if phase["declared"]:
            lines.append(("%s (%d/%d):" % (T["declared"], phase["written"],
                                           phase["declared"]), "head"))
            for out in phase["outputs"]:
                glyph = P.PG["completed"] if out["exists"] else P.PG["pending"]
                stamp = ""
                if out["exists"] and out["mtime"]:
                    stamp = "  %s" % datetime.fromtimestamp(
                        out["mtime"]).strftime("%m-%d %H:%M")
                lines.append(("  %s %s%s" % (glyph, out["path"], stamp),
                              "" if out["exists"] else "dim"))
        if phase["depends_on"]:
            lines.append(("%s: %s" % (T["deps"], ", ".join(phase["depends_on"])), "dim"))
        if phase["blocked_by"]:
            lines.append(("%s: %s" % (T["blocked_by"], ", ".join(phase["blocked_by"])),
                          "warn"))
        for key, label in (("started_at", T["started"]),
                           ("completed_at", T["completed_at"]),
                           ("updated_at", T["updated"]), ("note", T["note"]),
                           ("summary", T["summary"])):
            if phase.get(key):
                lines.append(("%s: %s" % (label, phase[key]), "dim"))
        if phase["last_activity"]:
            lines.append(("%s: %s" % (T["active"],
                                      T["ago"] % P.rel_time(phase["last_activity"])),
                          "accent" if phase["active"] else "dim"))
        for err in self.state["errors"]:
            if phase["name"] in str(err):
                lines.append(("%s: %s" % (T["errors"], err), "alert"))
        return lines

    # ------------------------------------------------------------------ actions
    def actions_for(self, row):
        if row["kind"] == "group":
            phases = [p for p in row["group"]["phases"] if p["runnable"]]
            target = phases[0] if phases else row["group"]["phases"][0]
            return P.actions_for(self.state, target)
        return P.actions_for(self.state, row["phase"])

    def default_action(self, row):
        if row["kind"] == "group":
            acts = self.actions_for(row)
            return acts[0] if acts else None
        return P.default_action(self.state, row["phase"])

    def open_target(self, row):
        if row["kind"] == "group":
            return None
        existing = [o["resolved"] or o["path"] for o in row["phase"]["outputs"]
                    if o["exists"]]
        return existing[0] if existing else None

    def ask_questions(self, row):
        T = self.T
        if row["kind"] == "group":
            return [T["ask_next"], T["ask_summary"]]
        if row["phase"]["stale"]:
            return [T["ask_stale"], T["ask_next"], T["ask_summary"]]
        return [T["ask_why"] % row["phase"]["status"], T["ask_next"], T["ask_summary"]]

    def ask_prompt(self, row, question):
        if row["kind"] == "group":
            context = "%s %s" % (self.state["plugin"],
                                 P.group_title(self.T, row["key"]))
        else:
            context = P.phase_context(self.state, row["phase"], self.T)
        return ("[nexus pipeline: %s] %s\n\nProject: %s. Read "
                "work/pipeline-progress.json and the phase's declared outputs under "
                "reports/ before answering." % (context, question, PROJ))

    def keys_hint(self):
        return self.T["keys"]

    def help_lines(self):
        T = self.T
        statuses = "  ".join("%s %s" % (P.PG[s], s) for s in P.DISPLAY_STATUSES)
        return [(T["help_glyphs"], "head"),
                ("  " + statuses, ""),
                ("  [==..]    %s" % T["help_outputs"], ""),
                ("  %s         %s" % (P.PG["stale"], T["help_stale"]), ""),
                ("  %s         %s" % (P.PG["drift"], T["help_drift"]), ""),
                ("  %s         %s" % (P.PG["active"], T["help_active"]), ""),
                ("  ?         %s" % T["help_optional"], "")]

    def on_key(self, key, app):
        if key == ord("f"):
            order = [None] + P.DISPLAY_STATUSES
            self.status_filter = order[(order.index(self.status_filter) + 1)
                                       % len(order)]
            return True
        return False
