"""The backlog tab of the nexus-status dashboard.

The Epic -> Sub-Epic -> Issue tree with each node's delivery status and its
Implemented/Reviewed/Merged stages; the detail pane shows where the status came from,
the PR, the implementation files/decisions, the follow-up origin and the newest review
document. Live state is fetched from the tracker via glab/gh at startup, again in the
background every SYNC_EVERY seconds, and on demand with `s`; per the backlog contract
the tracker wins over the manifest for an Issue, and disagreement is marked as drift.
The background fetch runs off a thread and hands its result to the poll loop through
extra_stamp(), so a 1-2 second round trip to GitLab never freezes the keyboard.

The rendering shell (layout, menus, keys, refresh) lives in status_tui.App; this module
only answers what to show. Its state rules live in backlog_status_data.py.
"""

import os
import sys
import threading
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backlog_status_data as B  # noqa: E402
import status_tui as S  # noqa: E402
import token_cost_data as D  # noqa: E402

env = os.environ.get
PROJ = env("NX_PROJECT_DIR", ".")
EPIC_FILTER = env("NX_EPIC", "") or None
# Tracker syncing as a whole: the startup fetch, `s`, and the background refresh.
SYNC_ENABLED = env("NX_SYNC", "1") == "1"
# How long a synced tracker snapshot is trusted before the view fetches a new one in the
# background. The manifest only moves when a skill writes it, so without this the tab
# went stale the moment anyone closed an Issue in the browser.
SYNC_EVERY = max(30, int(env("NX_SYNC_EVERY", "180") or 180))

WATCH = ("reports/backlog/backlog-manifest.json",
         "reports/backlog/followup-queue.md")


class BacklogView(S.BaseView):
    name = "backlog"

    def __init__(self, manifest_path, lang):
        S.BaseView.__init__(self)
        self.path = manifest_path
        self.T = B.labels(lang)
        self.title = self.T["title"]
        self.manifest = None
        self.by_id = {}
        self.children = {}
        self.states = {}
        self.summary = {"by_status": {s: 0 for s in B.STATUSES},
                        "issues_total": 0, "issues_done": 0}
        self.queue_count = 0
        self.pipeline = None
        self.sync_cache = None
        self.synced_at = None
        self.sync_warnings = []
        self.sync_error = None
        self._sync_thread = None
        self._sync_result = None    # handed over by the background thread
        self._last_attempt = None
        self._sync_gen = 0          # bumped on arrival so the poll loop reloads
        self.available = os.path.isfile(manifest_path)
        self.load()

    # ------------------------------------------------------------------ data
    def watch_files(self):
        return WATCH

    def has_tracker(self):
        return bool(B.tracker_sources(self.manifest or {}))

    def load(self):
        manifest = B.load_manifest(self.path, PROJ)
        if manifest is not None:
            self.manifest = manifest
            self.by_id, self.children, self.states = B.derive_all(
                manifest, self.sync_cache)
            self.summary = B.overall_summary(manifest, self.states)
            self.available = True
        self.pipeline = B.load_pipeline(PROJ)
        self.queue_count = B.followup_queue_count(PROJ)

    def project_label(self):
        return (self.manifest or {}).get("project") or os.path.basename(
            os.path.abspath(PROJ))

    def active_filters(self):
        """The filters currently narrowing the tree — see PipelineView.active_filters."""
        active = []
        if self.status_filter:
            active.append("%s=%s" % (self.T["filter"], self.status_filter))
        if EPIC_FILTER:
            active.append("--epic=%s" % EPIC_FILTER)
        return active

    def empty_message(self):
        active = self.active_filters()
        if active:
            msg = self.T["no_match"] % ", ".join(active)
            if self.status_filter:      # --epic needs a relaunch; only `f` is live
                msg += " - %s" % self.T["clear_filter"]
            return msg
        return self.T["no_manifest"]

    def sync(self, app):
        """Fetch tracker labels now. Blocks the loop briefly; a banner says so first."""
        if not self.has_tracker():
            app.flash("%s: %s" % (self.T["sync_failed"], self.T["no_tracker"]),
                      "alert", seconds=8)
            return
        app.flash(self.T["syncing"], "warn", seconds=60)
        app.draw()
        self._last_attempt = datetime.now()   # so the poll loop does not re-fetch at once
        try:
            self._apply_sync(*B.sync_tracker(self.manifest))
            app.flash("%s %s" % (self.T["synced"], self.synced_at.strftime("%H:%M:%S")),
                      "accent")
        except RuntimeError as exc:
            self.sync_error = str(exc)
            app.flash("%s: %s" % (self.T["sync_failed"], exc), "alert", seconds=8)

    def _apply_sync(self, cache, warnings):
        self.sync_cache = cache
        self.sync_warnings = warnings
        self.sync_error = None
        self.synced_at = datetime.now()
        self.load()

    def sync_background(self):
        """Start a re-sync off the draw loop; at most one is ever in flight."""
        if self._sync_thread is not None and self._sync_thread.is_alive():
            return
        if not self.has_tracker():
            return
        self._last_attempt = datetime.now()
        manifest = self.manifest

        def worker():
            try:
                self._sync_result = ("ok", B.sync_tracker(manifest))
            except RuntimeError as exc:
                self._sync_result = ("error", str(exc))

        self._sync_thread = threading.Thread(target=worker, daemon=True)
        self._sync_thread.start()

    def extra_stamp(self):
        """Drives the background sync from the poll loop, which is the only per-tick hook.

        Returns a counter that changes exactly when a fetch lands, so App.maybe_refresh
        redraws the tree on a tracker change the same way it does on a manifest change.
        """
        result, self._sync_result = self._sync_result, None
        if result is not None:
            if result[0] == "ok":
                self._apply_sync(*result[1])
            else:                    # a failed fetch keeps the previous snapshot
                self.sync_error = result[1]
            self._sync_gen += 1
        # Off the attempt, not the last success: a tracker that is down would otherwise
        # be retried on every 10-second poll for as long as the dashboard is open.
        if SYNC_ENABLED and (self._last_attempt is None or (
                datetime.now() - self._last_attempt).total_seconds() >= SYNC_EVERY):
            self.sync_background()
        return self._sync_gen

    # ------------------------------------------------------------------ rows
    def rows(self):
        return B.flatten_tree(self.children, self.states, self.collapsed,
                              self.status_filter, EPIC_FILTER)

    def row_key(self, row):
        return row["local_id"]

    def row_style(self, row):
        return B.STATUS_STYLE.get(self.states[row["local_id"]]["status"], "")

    def row_line(self, row, depth, stack, width):
        lid = row["local_id"]
        state = self.states[lid]
        marks = (B.SG["followup"] if state["followup"] else " ") + \
                (B.SG["drift"] if state["drift"] else " ")
        counts = ""
        if row.get("level") in ("epic", "sub-epic"):
            done, total = B.descendant_issue_counts(row, self.children, self.states)
            counts = "%d/%d" % (done, total)
        fold = "+" if (self.children.get(lid) and lid in self.collapsed) else ""
        status_txt = "%s %s" % (B.SG[state["status"]], state["status"])
        right = "%s %s %s  %s" % (D.pad(counts, 5, "r"), marks, D.pad(status_txt, 10),
                                  B.stage_boxes(state["stages"]))
        left_w = width - D.dw(right) - 2
        text = B.tree_prefix(depth, stack) + "%s  %s%s" % (
            lid, row.get("title", ""), (" " + fold if fold else ""))
        return "%s %s" % (D.pad(D.clip(text, left_w), left_w), right)

    def has_children(self, row):
        return bool(self.children.get(row["local_id"]))

    def fold(self, collapse):
        node = self.by_id.get(self.sel_key)
        if node is None:
            return
        lid = node["local_id"]
        if collapse:
            if self.children.get(lid) and lid not in self.collapsed:
                self.collapsed.add(lid)
            elif node.get("parent_local_id") in self.by_id:
                self.sel_key = node["parent_local_id"]
        else:
            self.collapsed.discard(lid)

    # ------------------------------------------------------------------ panes
    def header_lines(self, width):
        T = self.T
        s = self.summary
        frac = s["issues_done"] / s["issues_total"] if s["issues_total"] else 0
        counts = (" %s " % D.G["sep"]).join(
            "%s %d" % (st, s["by_status"][st]) for st in B.STATUSES)
        lines = [("%s %d/%d %s  %s  %s" % (
            T["issues"], s["issues_done"], s["issues_total"], T["done"],
            D.bar(frac, min(20, width // 5)), counts), "bold")]
        meta = []
        if self.pipeline:
            cur = " %s %s" % (B.SG["current"], self.pipeline["current"]) \
                if self.pipeline["current"] else ""
            if self.pipeline.get("stale"):
                cur += " %s %d" % (B.SG["stale"], self.pipeline["stale"])
            meta.append("%s %d/%d%s" % (T["pipeline"], self.pipeline["completed"],
                                        self.pipeline["total"], cur))
        # Why the tree says what it says: when it was last confirmed against the tracker,
        # and — when a fetch failed — what failed, since the rows themselves look the
        # same whether the snapshot behind them is a minute or an hour old.
        trouble = ([self.sync_error] if self.sync_error else []) + self.sync_warnings
        if self.synced_at:
            note = "%s %s" % (T["synced"], self.synced_at.strftime("%H:%M"))
            if trouble:
                note += " (%s: %s)" % (T["sync_partial"], trouble[0])
        elif not self.has_tracker():
            note = T["no_tracker"]
        elif trouble:
            note = "%s: %s" % (T["sync_failed"], trouble[0])
        else:
            note = T["not_synced"]
        meta.append(D.clip(note, max(20, width // 2)))
        meta += self.active_filters()
        if self.queue_count:
            meta.append("%s %s" % (T["queue"], T["queued_entries"] % self.queue_count))
        lines.append(((" %s " % D.G["sep"]).join(meta), "dim"))
        return lines

    def detail_title(self, row):
        return "%s %s" % (row["local_id"], row.get("title", ""))

    def detail_lines(self, node, width):
        T = self.T
        state = self.states[node["local_id"]]
        lines = []
        src = "%s %s" % (T["status"], state["status"])
        src += "  (%s: %s)" % (T["source"], state["source"])
        lines.append((src, B.STATUS_STYLE.get(state["status"], "")))
        if state["drift"]:
            lines.append((T["drift_rollup"] % (state["tracker_status"], state["status"])
                          if state.get("rollup")
                          else T["drift"] % (state["tracker_status"], "manifest"), "warn"))
        lines.append(("%s %s   %s" % (T["stages"], B.stage_boxes(state["stages"]),
                                      T["stages_note"]), "dim"))
        remote = node.get("remote") or {}
        if remote.get("url"):
            lines.append(("%s #%s  %s" % (T["issue"], remote.get("iid", "?"),
                                          remote["url"]), ""))
        pr = node.get("pr") or {}
        if pr.get("url"):
            merged = " (merged)" if pr.get("merged") else ""
            lines.append(("%s %s%s" % (T["pr"], pr["url"], merged), ""))
        origin = node.get("origin") or {}
        if origin:
            lines.append(("%s %s %s %s" % (T["origin"], origin.get("source", "?"),
                                           D.G["sep"], origin.get("discovered_in", "?")),
                          "model"))
        impl = node.get("impl") or {}
        if impl.get("updated_at"):
            lines.append(("%s %s" % (T["updated"], impl["updated_at"]), "dim"))
        for key, label in (("files", T["impl_files"]), ("decisions", T["decisions"])):
            values = impl.get(key) or []
            if isinstance(values, str):
                values = [values]
            if values:
                lines.append(("%s:" % label, "head"))
                lines += [("  " + v, "") for v in values[:10]]
        review = B.latest_review(PROJ, node)
        if review:
            lines.append(("%s round %d: %s" % (
                T["review_doc"], review[1], os.path.relpath(review[0], PROJ)), ""))
        log = B.impl_log_path(PROJ, node)
        if log:
            lines.append(("impl-log: %s" % os.path.relpath(log, PROJ), "dim"))
        if self.queue_count:
            lines.append(("%s: %s" % (T["queue"],
                                      T["queued_entries"] % self.queue_count), "model"))
        return lines

    # ------------------------------------------------------------------ actions
    def actions_for(self, row):
        return B.actions_for(row, self.states[row["local_id"]], self.queue_count)

    def default_action(self, row):
        return B.default_action(row, self.states[row["local_id"]], self.queue_count)

    def open_target(self, row):
        return ((row or {}).get("remote") or {}).get("url")

    def ask_questions(self, row):
        state = self.states[row["local_id"]]
        return [self.T["ask_why"] % state["status"], self.T["ask_next"],
                self.T["ask_summary"]]

    def ask_prompt(self, row, question):
        state = self.states[row["local_id"]]
        context = "%s %s / %s / %s" % (row.get("level", "item"), row["local_id"],
                                       state["status"],
                                       B.stage_boxes(state["stages"]))
        return ("[nexus backlog: %s] %s\n\nProject: %s. Read "
                "reports/backlog/backlog-manifest.json and the item's impl-log / review "
                "documents before answering." % (context, question, PROJ))

    def keys_hint(self):
        return self.T["keys"]

    def help_lines(self):
        T = self.T
        statuses = "  ".join("%s %s" % (B.SG[s], s) for s in B.STATUSES)
        return [(T["help_glyphs"], "head"),
                ("  " + statuses, ""),
                ("  [I][R][M] %s" % T["help_stages"], ""),
                ("  %s         %s" % (B.SG["followup"], T["help_followup"]), ""),
                ("  %s         %s" % (B.SG["drift"], T["help_drift"]), "")]

    def on_key(self, key, app):
        if key in (ord("s"), ord("S")):
            self.sync(app)
            return True
        if key == ord("f"):
            order = [None] + B.STATUSES
            self.status_filter = order[(order.index(self.status_filter) + 1)
                                       % len(order)]
            return True
        return False

    def sync_at_start(self, app):
        if SYNC_ENABLED and self.available:
            self.sync(app)
