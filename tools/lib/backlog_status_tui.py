"""Live dashboard for backlog delivery.

Upper pane: the Epic -> Sub-Epic -> Issue tree, foldable, with delivery status and
Implemented/Reviewed/Merged stages per node. Lower pane: the selected node's detail
(status source, PR, impl files/decisions, origin, latest review doc, follow-up queue).
Enter opens an action menu that generates the slash command for the next step —
copied to the clipboard by default, or run via `claude "<command>"` under --exec.

The manifest is re-checked every NX_INTERVAL seconds and re-read only when it changed;
the selection (keyed by local_id) survives the refresh. `s` fetches live tracker labels
via glab/gh — per the backlog contract the tracker wins and drift is marked.
Invoked by tools/backlog-status.sh.

Usage: backlog_status_tui.py <backlog-manifest.json>
"""

import curses
import locale
import os
import subprocess
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backlog_status_data as B  # noqa: E402
import token_cost_data as D  # noqa: E402

MANIFEST = sys.argv[1]
env = os.environ.get
LANG = env("NX_LANG", "en")
INTERVAL = max(1, int(env("NX_INTERVAL", "10") or 10))
PROJ = env("NX_PROJECT_DIR", ".")
DEBUG_LOG = env("NX_DEBUG_LOG", "")
SYNC_AT_START = env("NX_SYNC", "0") == "1"
EXEC_ENABLED = env("NX_EXEC", "0") == "1"
EPIC_FILTER = env("NX_EPIC", "") or None

T = B.labels(LANG)

# style names -> (color pair index, attribute)
STYLES = {"": (0, 0), "bold": (0, curses.A_BOLD), "dim": (3, curses.A_DIM),
          "head": (1, curses.A_BOLD), "accent": (4, 0), "warn": (5, 0),
          "model": (6, 0), "sel": (2, curses.A_BOLD), "alert": (7, curses.A_BOLD)}

WATCH_FILES = ("reports/backlog/backlog-manifest.json",
               "reports/backlog/followup-queue.md",
               "work/pipeline-progress.json")


class App:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.manifest = None
        self.by_id = {}
        self.children = {}
        self.states = {}
        self.summary = {"by_status": {s: 0 for s in B.STATUSES},
                        "issues_total": 0, "issues_done": 0}
        self.pipeline = None
        self.queue_count = 0
        self.collapsed = set()
        self.status_filter = None
        self.sel_key = None
        self.sel_idx = 0
        self.list_top = 0
        self.detail_top = 0
        self.menu = None          # (entries, selected_index) while the menu is open
        self.notice = None        # (text, style, expires_at) transient result bar
        self.sync_cache = None
        self.synced_at = None
        self.clip_tool = B.clipboard_tool()
        self.stamps = ()
        self.last_check = 0.0
        self.last_refresh = None
        self.load()
        if SYNC_AT_START:
            self.sync()

    # ------------------------------------------------------------------ data
    def stamps_now(self):
        out = []
        for rel in WATCH_FILES:
            try:
                out.append(os.path.getmtime(os.path.join(PROJ, rel)))
            except OSError:
                out.append(0)
        return tuple(out)

    def load(self):
        manifest = B.load_manifest(MANIFEST)
        if manifest is not None:
            self.manifest = manifest
            self.by_id, self.children, self.states = B.derive_all(
                manifest, self.sync_cache)
            self.summary = B.overall_summary(manifest, self.states)
        self.pipeline = B.load_pipeline(PROJ)
        self.queue_count = B.followup_queue_count(PROJ)
        self.stamps = self.stamps_now()
        self.last_refresh = datetime.now()

    def maybe_refresh(self, force=False):
        now = time.time()
        if not force and now - self.last_check < INTERVAL:
            return False
        self.last_check = now
        if force or self.stamps_now() != self.stamps:
            self.load()
            return True
        return False

    def sync(self):
        """Fetch tracker labels. Blocks the loop briefly; a banner says so first."""
        self.flash(T["syncing"], "warn", seconds=60)
        self.draw()
        try:
            self.sync_cache = B.sync_tracker(self.manifest)
            self.synced_at = datetime.now()
            self.load()
            self.flash("%s %s" % (T["synced"], self.synced_at.strftime("%H:%M:%S")),
                       "accent")
        except RuntimeError as exc:
            self.flash("%s: %s" % (T["sync_failed"], exc), "alert", seconds=8)

    # ------------------------------------------------------------------ rows
    def rows(self):
        return B.flatten_tree(self.children, self.states, self.collapsed,
                              self.status_filter, EPIC_FILTER)

    def selected(self, rows):
        if not rows:
            self.sel_key = None
            return None
        keys = [n["local_id"] for n, _, _ in rows]
        if self.sel_key in keys:
            idx = keys.index(self.sel_key)
        else:
            idx = min(self.sel_idx, len(keys) - 1)
        self.sel_idx = idx
        self.sel_key = keys[idx]
        return idx

    # ------------------------------------------------------------------ detail
    def detail_lines(self, node, width):
        state = self.states[node["local_id"]]
        lines = []
        src = "%s %s" % (T["status"], state["status"])
        src += "  (%s: %s)" % (T["source"], state["source"])
        lines.append((src, B.STATUS_STYLE.get(state["status"], "")))
        if state["drift"]:
            lines.append((T["drift"] % (state["tracker_status"], "manifest"), "warn"))
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
    def open_menu(self, node):
        state = self.states[node["local_id"]]
        entries = B.actions_for(node, state, self.queue_count)
        if not entries:
            return
        default = B.default_action(node, state, self.queue_count)
        idx = next((i for i, e in enumerate(entries) if e == default), 0)
        self.menu = (node, entries, idx)

    def flash(self, text, style="", seconds=5):
        self.notice = (text, style, time.time() + seconds)

    def perform(self, node, label, command, execute=False):
        if label == "open URL":
            B.open_url(command)
            self.flash("%s %s" % (T["shown"], command), "dim")
            return
        if execute:
            self.run_claude(command)
            return
        if B.copy_clipboard(self.clip_tool, command):
            self.flash("%s %s %s  %s" % (T["copied"], D.G["arrow"], command,
                                         T["paste_hint"]), "accent", seconds=8)
        else:
            self.flash("%s: %s  %s" % (T["shown"], command, T["no_clipboard"]),
                       "warn", seconds=8)

    def run_claude(self, command):
        """Suspend curses, run claude in the foreground, then restore and refresh."""
        curses.endwin()
        try:
            subprocess.call(["claude", command])
        except Exception as exc:
            print("backlog-status: claude failed: %s" % exc, file=sys.stderr)
            time.sleep(2)
        self.stdscr.refresh()
        curses.curs_set(0)
        self.maybe_refresh(force=True)
        self.flash("%s %s claude" % (command, D.G["arrow"]), "accent")

    # ---------------------------------------------------------------- drawing
    def draw(self):
        stdscr = self.stdscr
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        if height < 12 or width < 50:
            put(stdscr, 0, 0, T["too_small"], width, "warn")
            stdscr.refresh()
            return

        # header
        project = (self.manifest or {}).get("project") or os.path.basename(PROJ)
        title = "%s %s %s" % (project, D.G["sep"], T["title"])
        clock = "%s %s %s" % (D.G["dot"], T["live"], datetime.now().strftime("%H:%M:%S"))
        put(stdscr, 0, 0, title, width - D.dw(clock) - 1, "head")
        put(stdscr, 0, width - D.dw(clock) - 1, clock, D.dw(clock), "accent")

        s = self.summary
        frac = s["issues_done"] / s["issues_total"] if s["issues_total"] else 0
        counts = (" %s " % D.G["sep"]).join(
            "%s %d" % (st, s["by_status"][st]) for st in B.STATUSES)
        put(stdscr, 1, 0, "%s %d/%d %s  %s  %s" % (
            T["issues"], s["issues_done"], s["issues_total"], T["done"],
            D.bar(frac, min(20, width // 5)), counts), width, "bold")

        meta = []
        if self.pipeline:
            cur = " %s %s" % (B.SG["current"], self.pipeline["current"]) \
                if self.pipeline["current"] else ""
            meta.append("%s %d/%d%s" % (T["pipeline"], self.pipeline["completed"],
                                        self.pipeline["total"], cur))
        meta.append("%s %s (%s)" % (T["checked"],
                                    self.last_refresh.strftime("%H:%M:%S"),
                                    T["every"] % INTERVAL))
        meta.append("%s %s" % (T["synced"], self.synced_at.strftime("%H:%M"))
                    if self.synced_at else T["not_synced"])
        if self.status_filter:
            meta.append("%s: %s" % (T["filter"], self.status_filter))
        put(stdscr, 2, 0, (" %s " % D.G["sep"]).join(meta), width, "dim")

        rows = self.rows()
        idx = self.selected(rows)

        # tree pane
        list_start = 4
        detail_reserve = 8
        list_h = max(3, min(len(rows) or 1, height - list_start - detail_reserve))
        counter = "%d/%d" % ((idx or 0) + 1, len(rows)) if rows else "0/0"
        put(stdscr, 3, 0, D.hrule(width - D.dw(counter) - 2), width, "dim")
        put(stdscr, 3, width - D.dw(counter) - 1, counter, D.dw(counter), "dim")

        if idx is None:
            put(stdscr, list_start, 2, T["no_manifest"], width - 2, "dim")
            sep_y = list_start + 1
        else:
            if idx < self.list_top:
                self.list_top = idx
            if idx >= self.list_top + list_h:
                self.list_top = idx - list_h + 1
            self.list_top = max(0, min(self.list_top, max(0, len(rows) - list_h)))
            stage_w = D.dw(B.stage_boxes({"implemented": 1, "reviewed": 1, "merged": 1}))
            for i in range(list_h):
                row_i = self.list_top + i
                if row_i >= len(rows):
                    break
                node, depth, stack = rows[row_i]
                lid = node["local_id"]
                state = self.states[lid]
                marks = (B.SG["followup"] if state["followup"] else " ") + \
                        (B.SG["drift"] if state["drift"] else " ")
                counts = ""
                if node.get("level") in ("epic", "sub-epic"):
                    done, total = B.descendant_issue_counts(node, self.children,
                                                            self.states)
                    counts = "%d/%d" % (done, total)
                fold = ""
                if self.children.get(lid):
                    fold = "+" if lid in self.collapsed else ""
                status_txt = "%s %s" % (B.SG[state["status"]], state["status"])
                right = "%s %s %s  %s" % (D.pad(counts, 5, "r"), marks,
                                          D.pad(status_txt, 10),
                                          B.stage_boxes(state["stages"]))
                left_w = width - D.dw(right) - 4
                text = B.tree_prefix(depth, stack) + "%s  %s%s" % (
                    lid, node.get("title", ""), (" " + fold if fold else ""))
                line = "%s %s" % (D.pad(D.clip(text, left_w), left_w), right)
                selected_row = row_i == idx
                style = "sel" if selected_row else B.STATUS_STYLE.get(state["status"], "")
                put(stdscr, list_start + i, 1, D.pad(line, width - 2), width - 1, style)
            sep_y = list_start + min(list_h, len(rows))

        # separator + detail
        sel_node = self.by_id.get(self.sel_key) if self.sel_key else None
        label = " %s " % T["detail"]
        if sel_node is not None:
            label = " %s %s %s %s " % (T["detail"], D.G["sep"], sel_node["local_id"],
                                       D.clip(sel_node.get("title", ""), 40))
        put(stdscr, sep_y, 0, D.hrule(width), width, "dim")
        put(stdscr, sep_y, 2, label, width - 2, "dim")

        detail_y = sep_y + 1
        detail_h = height - detail_y - 1
        lines = self.detail_lines(sel_node, width - 2) if sel_node else []
        max_top = max(0, len(lines) - detail_h)
        self.detail_top = max(0, min(self.detail_top, max_top))
        for i in range(detail_h):
            j = self.detail_top + i
            if j >= len(lines):
                break
            text, style = lines[j]
            put(stdscr, detail_y + i, 1, text, width - 2, style)
        if len(lines) > detail_h:
            counter = " %d-%d/%d " % (self.detail_top + 1,
                                      min(len(lines), self.detail_top + detail_h),
                                      len(lines))
            put(stdscr, sep_y, max(0, width - D.dw(counter) - 2), counter, width, "dim")

        # bottom bar: transient notice wins over the key hints
        if self.notice and time.time() < self.notice[2]:
            text, style, _ = self.notice
            put(stdscr, height - 1, 0, D.pad(" " + text, width - 1), width - 1, style)
        else:
            self.notice = None
            put(stdscr, height - 1, 0, D.pad(T["keys"], width - 1), width - 1, "dim")

        if self.menu:
            self.draw_menu(height, width)

        # Discard what curses believes is on the screen and repaint every line. Its model
        # miscounts East Asian double-width cells, so the update optimizer skips cells it
        # thinks already match and fragments of the previous frame survive. touchwin() is
        # not enough — the redraw has to be forced. (Same fix as token_cost_tui.py.)
        stdscr.redrawwin()
        stdscr.refresh()

    def draw_menu(self, height, width):
        node, entries, sel = self.menu
        title = " %s %s %s " % (node["local_id"],
                                D.clip(node.get("title", ""), 30), T["actions"])
        rows = ["%s %d  %s  %s" % (">" if i == sel else " ", i + 1,
                                   D.pad(label, 22), D.clip(cmd, width - 40))
                for i, (label, cmd) in enumerate(entries)]
        hint = T["menu_keys"] if EXEC_ENABLED else \
            T["menu_keys"].split("|")[0] + "| " + T["exec_hint"]
        box_w = min(width - 4, max(D.dw(title), D.dw(hint) + 2,
                                   max(D.dw(r) for r in rows) + 2) + 2)
        box_h = len(rows) + 4
        y0 = max(1, (height - box_h) // 2)
        x0 = max(1, (width - box_w) // 2)
        horiz = D.hrule(box_w - 2)
        put(self.stdscr, y0, x0, "+" + horiz + "+", box_w, "head")
        put(self.stdscr, y0, x0 + 2, title, box_w - 4, "head")
        for i, row in enumerate(rows):
            body = D.pad(" " + row, box_w - 2)
            put(self.stdscr, y0 + 1 + i, x0, "|", 1, "head")
            put(self.stdscr, y0 + 1 + i, x0 + 1, body, box_w - 2,
                "sel" if i == sel else "")
            put(self.stdscr, y0 + 1 + i, x0 + box_w - 1, "|", 1, "head")
        put(self.stdscr, y0 + 1 + len(rows), x0, "|" + D.pad(" " + hint, box_w - 2)
            + "|", box_w, "dim")
        put(self.stdscr, y0 + 2 + len(rows), x0, "+" + horiz + "+", box_w, "head")

    # ------------------------------------------------------------------- loop
    def move(self, delta):
        rows = self.rows()
        if not rows:
            return
        keys = [n["local_id"] for n, _, _ in rows]
        idx = max(0, min(len(keys) - 1, self.sel_idx + delta))
        self.sel_idx = idx
        self.sel_key = keys[idx]
        self.detail_top = 0

    def fold(self, collapse):
        node = self.by_id.get(self.sel_key)
        if node is None:
            return
        lid = node["local_id"]
        has_kids = bool(self.children.get(lid))
        if collapse:
            if has_kids and lid not in self.collapsed:
                self.collapsed.add(lid)
            elif node.get("parent_local_id") in self.by_id:
                self.sel_key = node["parent_local_id"]
        else:
            self.collapsed.discard(lid)

    def handle_menu_key(self, key):
        node, entries, sel = self.menu
        if key in (27, ord("q")):
            self.menu = None
        elif key in (curses.KEY_DOWN, ord("j")):
            self.menu = (node, entries, (sel + 1) % len(entries))
        elif key in (curses.KEY_UP, ord("k")):
            self.menu = (node, entries, (sel - 1) % len(entries))
        elif ord("1") <= key <= ord("9") and key - ord("1") < len(entries):
            self.menu = (node, entries, key - ord("1"))
        elif key in (curses.KEY_ENTER, 10, 13):
            label, cmd = entries[sel]
            self.menu = None
            self.perform(node, label, cmd)
        elif key == ord("e"):
            label, cmd = entries[sel]
            self.menu = None
            if EXEC_ENABLED and label != "open URL":
                self.perform(node, label, cmd, execute=True)
            else:
                self.flash(T["exec_hint"], "warn")

    def run(self):
        stdscr = self.stdscr
        curses.curs_set(0)
        stdscr.timeout(500)
        while True:
            self.draw()
            try:
                key = stdscr.getch()
            except KeyboardInterrupt:
                return
            if key == -1:
                self.maybe_refresh()
                continue
            if self.menu:
                self.handle_menu_key(key)
                continue
            if key in (ord("q"), ord("Q"), 27):
                return
            elif key in (curses.KEY_DOWN, ord("j")):
                self.move(1)
            elif key in (curses.KEY_UP, ord("k")):
                self.move(-1)
            elif key in (curses.KEY_LEFT, ord("h")):
                self.fold(collapse=True)
            elif key in (curses.KEY_RIGHT, ord("l")):
                self.fold(collapse=False)
            elif key in (curses.KEY_ENTER, 10, 13):
                node = self.by_id.get(self.sel_key)
                if node is not None:
                    self.open_menu(node)
            elif key in (ord("s"), ord("S")):
                self.sync()
            elif key == ord("f"):
                order = [None] + B.STATUSES
                self.status_filter = order[(order.index(self.status_filter) + 1)
                                           % len(order)]
            elif key == ord("c"):
                node = self.by_id.get(self.sel_key)
                if node is not None:
                    act = B.default_action(node, self.states[node["local_id"]],
                                           self.queue_count)
                    if act:
                        self.perform(node, act[0], act[1])
            elif key == ord("o"):
                node = self.by_id.get(self.sel_key)
                url = ((node or {}).get("remote") or {}).get("url")
                if url:
                    B.open_url(url)
                    self.flash(url, "dim")
            elif key in (curses.KEY_NPAGE, 4):        # PgDn / Ctrl-D
                self.detail_top += 10
            elif key in (curses.KEY_PPAGE, 21):       # PgUp / Ctrl-U
                self.detail_top = max(0, self.detail_top - 10)
            elif key in (curses.KEY_HOME, ord("g")):
                self.detail_top = 0
            elif key in (curses.KEY_END, ord("G")):
                self.detail_top = 10 ** 6
            elif key in (ord("r"), ord("R")):
                self.maybe_refresh(force=True)
            elif key == curses.KEY_RESIZE:
                pass
            self.maybe_refresh()


# ------------------------------------------------------------------- utilities
def debug(fmt, *args):
    """Append one line to the debug log, when --debug asked for one."""
    if not DEBUG_LOG:
        return
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as fh:
            fh.write("%s %s\n" % (datetime.now().strftime("%H:%M:%S.%f")[:-3],
                                  fmt % args))
    except OSError:
        pass


def put(stdscr, y, x, text, width, style=""):
    if width <= 0 or y < 0 or x < 0:
        return
    text = D.clip(text, width)
    pair, attr = STYLES.get(style, (0, 0))
    if pair and curses.has_colors():
        attr |= curses.color_pair(pair)
    elif style == "dim":
        attr |= curses.A_DIM
    elif style == "sel":
        attr |= curses.A_REVERSE
    try:
        stdscr.addstr(y, x, text, attr)
    except curses.error as exc:
        # Writing the bottom-right cell always raises, and so does anything curses
        # thinks runs past the edge. Recorded under --debug, never fatal.
        debug("addstr failed y=%d x=%d dw=%d width=%d style=%s: %s | %r",
              y, x, D.dw(text), width, style or "-", exc, text[:60])


def main(stdscr):
    debug("start term=%s encoding=%s locale=%s ncurses=%s size=%dx%d "
          "glyphs=%s ambiguous_wide=%s",
          os.environ.get("TERM", "-"), getattr(sys.stdout, "encoding", "-"),
          locale.setlocale(locale.LC_CTYPE), curses.version, *stdscr.getmaxyx()[::-1],
          "ascii" if D.ASCII_ONLY else "unicode", D.AMBIGUOUS_WIDE)
    if curses.has_colors():
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(3, curses.COLOR_WHITE, -1)
        curses.init_pair(4, curses.COLOR_GREEN, -1)
        curses.init_pair(5, curses.COLOR_YELLOW, -1)
        curses.init_pair(6, curses.COLOR_MAGENTA, -1)
        curses.init_pair(7, curses.COLOR_RED, -1)
    App(stdscr).run()


if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, "")
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
