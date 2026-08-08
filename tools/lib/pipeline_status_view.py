"""The pipeline tabs of the nexus-status dashboard.

Three of the dashboard's four tabs are built from this module, because they show the same
thing about different work:

  PipelineView(plugin="product")    the product pipeline's phase tree
  PipelineView(plugin="architect")  the architect pipeline's phase tree
  CodegenView                       the code-generation phases of both plugins

Product and architect are separate pipelines with separate manifests, so they get
separate tabs rather than one tree whose contents depend on which plugin was detected.
Code generation is run by hand after either of them and emits code instead of reports, so
it gets a third — grouped by the plugin each phase belongs to, and offering that plugin's
slash commands.

Each tree is grouped and foldable (for a pipeline tab by category, with the architect
manual extension tier its own group), showing each phase's status, how many of its
declared outputs exist, whether it is producing tokens right now, and its recorded cost.
The detail pane shows the declared outputs with their real state, unmet dependencies, the
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
TIER = env("NX_GROUP", "") or None

WATCH = ("work/pipeline-progress.json", "work/token-usage.json",
         "work/token-usage.jsonl")

# How far into reports/ | design-system/ | generated/ the change poll looks, and how
# many entries it is allowed to stat before giving up. 3 covers the deepest declared
# output (reports/before/{project}/*.md); the budget keeps a generated/ tree with a
# node_modules/ in it from turning a 10s poll into a filesystem crawl.
WALK_DEPTH = 3
WALK_BUDGET = 4000



class PipelineView(S.BaseView):
    """One plugin's design pipeline. `plugin` is always named — never detected here."""

    def __init__(self, project_dir, lang, plugin="architect"):
        S.BaseView.__init__(self)
        self.project_dir = project_dir
        self.plugin = plugin
        self.name = plugin
        self.T = P.labels(lang)
        self.title = self.T["tab_%s" % plugin]
        self.state = None
        self.backlog = None
        self.available = False
        self.load()

    # ------------------------------------------------------------------ data
    def derive(self):
        return P.derive_all(self.project_dir, plugin=self.plugin)

    def is_available(self):
        """Whether this tab has anything behind it.

        A project that only ever ran architect must not offer a Product tab full of
        phases that were never part of it — but one that has just been initialized has no
        evidence either way yet, and there the detected plugin's tab still opens.
        """
        state = self.state
        return bool(state["evidence"]
                    or (state["has_progress"]
                        and state["plugin"] == state["detected_plugin"]))

    def watch_files(self):
        return WATCH

    def stamp_key(self):
        """The walk below reads the project and nothing else, so the three pipeline tabs
        over one project all produce the same number. Telling the shell that lets it run
        the scan once per poll instead of once per tab."""
        return ("pipeline-tree", os.path.abspath(self.project_dir))

    def extra_stamp(self):
        """Newest mtime in the output trees, files included, to WALK_DEPTH levels.

        A phase writing its third report file changes only the mtime of the directory
        holding it, so watching `reports/` alone would miss it and the tree would sit
        still until the registry happened to change.

        Directory mtimes alone are not enough either: **overwriting an existing file
        leaves every parent directory untouched**, and that is exactly the case
        staleness is about — a rerun or a hand edit of a report that already exists.
        Architect writes those three levels down (`reports/before/{project}/*.md`,
        `reports/review/individual/*.json`), so the files themselves are stat'ed, to a
        bounded depth and a bounded count: a few hundred stats per poll at most.
        """
        newest = 0.0
        seen = 0
        for top in ("reports", "design-system", "generated"):
            stack = [(os.path.join(self.project_dir, top), 0)]
            while stack:
                path, depth = stack.pop()
                try:
                    entries = list(os.scandir(path))
                    newest = max(newest, os.path.getmtime(path))
                except OSError:
                    continue
                for entry in entries:
                    if seen >= WALK_BUDGET:
                        return newest
                    seen += 1
                    try:
                        newest = max(newest, entry.stat().st_mtime)
                        if entry.is_dir() and depth + 1 < WALK_DEPTH:
                            stack.append((entry.path, depth + 1))
                    except OSError:
                        continue
        return newest

    def load(self):
        self.state = self.derive()
        self.available = self.is_available()
        # One name column for every row, so the status block lines up instead of
        # floating at the far right of a 160-column terminal. Phase rows carry a
        # two-segment tree prefix (a gap for the group level plus the connector).
        prefix_w = D.dw(B.tree_prefix(1, (True, False)))
        self.name_w = max([D.dw(n) + prefix_w for n in self.state["phases"]]
                          + [D.dw(P.group_title(self.T, g["key"]))
                             for g in self.state["groups"]] + [24])
        self.backlog = self.state["backlog"]

    def project_label(self):
        # The tab strip already names the pipeline, so the title bar only has to name
        # the project.
        return self.state["project"]

    def active_filters(self):
        """The filters currently narrowing this tab, as the user set them.

        What an empty tree means depends entirely on this: with no filter it says the
        pipeline never ran, with one it says nothing matched. Reporting the first when
        the second is true contradicts the header on the same screen.
        """
        active = []
        if self.status_filter:
            active.append("%s=%s" % (self.T["filter"], self.status_filter))
        if TIER in ("core", "extension") and self.state.get("section") == "pipeline":
            active.append("--group=%s" % TIER)
        return active

    def empty_message(self):
        active = self.active_filters()
        if active:
            msg = self.T["no_match"] % ", ".join(active)
            # `f` clears the status filter and nothing else — --group came from the
            # command line and needs a relaunch, so only offer the key that works.
            if self.status_filter:
                msg += " - %s" % self.T["clear_filter"]
            return msg
        if not self.state["has_progress"]:
            return self.T["no_progress"]
        return self.T["no_%s" % self.name]

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
            self.sel_key = "group:%s" % row["phase"]["group"]

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
        line += self.active_filters()
        if line:
            lines.append(((" %s " % D.G["sep"]).join(line), "head"))

        # A failure has to reach the headline. The progress fraction is measured over the
        # required path only (@pipeline_status_data.derive_all), so a phase that failed in
        # the manual extension tier — or one recorded outside the manifest entirely — is
        # missing from the status counts above and its row can sit below the fold.
        failed = [p["name"] for p in self.state["phases"].values()
                  if p["display_status"] == "failed"]
        if failed:
            lines.append(("%s %s: %s" % (P.PG["failed"], T["failed_phases"],
                                         ", ".join(failed)), "alert"))

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
            lines.append((T[{"outputs-missing": "drift_missing",
                             "shared-name": "drift_shared"}.get(
                                 phase["drift"], "drift_present")], "warn"))
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
        # "still pending" / "still failed" is the question worth asking; "still completed"
        # is not, so a finished phase leads with what it produced instead.
        if row["phase"]["display_status"] in ("completed", "skipped"):
            return [T["ask_summary"], T["ask_next"]]
        return [T["ask_why"] % row["phase"]["display_status"], T["ask_next"],
                T["ask_summary"]]

    def ask_prompt(self, row, question):
        if row["kind"] == "group":
            context = "%s %s" % (self.state["plugin"],
                                 P.group_title(self.T, row["key"]))
        else:
            context = P.phase_context(self.state, row["phase"], self.T)
        return ("[nexus %s: %s] %s\n\nProject: %s. Read "
                "work/pipeline-progress.json and the phase's declared outputs before "
                "answering." % (self.name, context, question, PROJ))

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


class CodegenView(PipelineView):
    """The code-generation tab: both plugins' codegen phases, grouped by plugin.

    Its rows, detail pane, action menu and keys are the pipeline view's — a codegen phase
    is an ordinary phase with declared outputs, dependencies and a cost. What differs is
    where it comes from: the tree spans both manifests, so the commands it offers come
    from each phase's own plugin, and the core/extension tier filter does not apply.

    `sources` is the list of plugins to show. The dashboard passes the pipeline tabs it
    already built, so deciding which pipelines ran costs nothing here; a caller that
    passes nothing has it worked out from the project.
    """

    def __init__(self, project_dir, lang, sources=None):
        self.sources = sources
        PipelineView.__init__(self, project_dir, lang, plugin="codegen")

    def derive(self):
        plugins = self.sources() if callable(self.sources) else self.sources
        return P.derive_codegen(self.project_dir, plugins=plugins)

    def is_available(self):
        # Codegen is where you go to *start* generating, so the tab opens as soon as the
        # project has a pipeline at all — not only once something has been generated.
        return bool(self.state["has_progress"] or self.state["evidence"])

    def rows(self):
        return P.flatten(self.state, self.collapsed, self.status_filter)
