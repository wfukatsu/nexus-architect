"""The curses shell shared by the nexus-status dashboard views.

Owns everything that is not specific to what is being watched: the three-pane layout
(header / foldable tree / detail), the tab strip, the action menu, the ask panel, the
help panel, the transient notice bar, the poll-and-reload loop, and the key handling.
Each view (pipeline_status_view.BacklogView / PipelineView) supplies the data and the
per-row rendering through the protocol below; the shell never imports either.

View protocol
    name                        "pipeline" | "backlog"
    title                       localized pane title
    available                   False when this project has no such input
    watch_files()               project-relative paths whose mtime triggers a reload
    load()                      (re)read the inputs
    header_lines(width)         [(text, style)] shown under the tab strip
    rows()                      [(row, depth, last_stack)] in draw order
    row_key(row)                stable id used to keep the selection across reloads
    row_line(row, depth, stack, width)  the formatted line for one row
    row_style(row)              style name for an unselected row
    has_children(row)           whether ← / → fold this row
    fold(key, collapse)         apply the fold
    detail_title(row)           label shown on the separator
    detail_lines(row, width)    [(text, style)] for the lower pane
    actions_for(row)            [(label, command)] for the action menu
    default_action(row)         (label, command) for the `c` key
    open_target(row)            URL or path for the `o` key, or None
    ask_questions(row)          [canned question, ...]
    ask_prompt(row, question)   the full prompt sent to claude
    on_key(key, app)            view-specific keys (`s`, `f`, ...); True when handled

Invoked by tools/lib/nexus_status_tui.py, which builds the views and hands them over.
"""

import curses
import os
import subprocess
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import token_cost_data as D  # noqa: E402

env = os.environ.get
LANG = env("NX_LANG", "en")
INTERVAL = max(1, int(env("NX_INTERVAL", "10") or 10))
PROJ = env("NX_PROJECT_DIR", ".")
DEBUG_LOG = env("NX_DEBUG_LOG", "")
EXEC_ENABLED = env("NX_EXEC", "0") == "1"

# style names -> (color pair index, attribute)
STYLES = {"": (0, 0), "bold": (0, curses.A_BOLD), "dim": (3, curses.A_DIM),
          "head": (1, curses.A_BOLD), "accent": (4, 0), "warn": (5, 0),
          "model": (6, 0), "sel": (2, curses.A_BOLD), "alert": (7, curses.A_BOLD)}

SHELL_LABELS = {
    "en": {
        "live": "LIVE", "detail": "Detail", "checked": "checked", "every": "every %ss",
        "too_small": "terminal too small", "copied": "copied", "shown": "command",
        "no_clipboard": "clipboard unavailable - command shown above",
        "paste_hint": "(paste into Claude Code)",
        "exec_hint": "run with --exec to launch claude from here",
        "actions": "actions", "menu_keys": "Enter copy | e run via claude | Esc close",
        "ask": "ask", "ask_free": "free input...", "ask_prompt": "question: ",
        "ask_copied": "question copied", "ask_keys": "Enter ask | Esc close",
        "help": "help", "help_close": "any key closes",
        "empty": "nothing to show",
    },
    "ja": {
        "live": "LIVE", "detail": "詳細", "checked": "確認", "every": "%s秒毎",
        "too_small": "画面が小さすぎます", "copied": "コピー済", "shown": "コマンド",
        "no_clipboard": "クリップボード利用不可 - 上記コマンドを使用",
        "paste_hint": "(Claude Code に貼り付け)",
        "exec_hint": "--exec 付きで起動すると claude をここから実行できます",
        "actions": "アクション", "menu_keys": "Enter コピー | e claude 実行 | Esc 閉じる",
        "ask": "質問", "ask_free": "自由入力...", "ask_prompt": "質問: ",
        "ask_copied": "質問をコピーしました", "ask_keys": "Enter 質問 | Esc 閉じる",
        "help": "ヘルプ", "help_close": "任意のキーで閉じる",
        "empty": "表示するものがありません",
    },
}

HELP_LINES = {
    "en": [
        ("navigation", "head"),
        ("  ^v / j k      select row            <> / h l   fold / unfold", ""),
        ("  Tab / S-Tab   switch view           r          refresh now", ""),
        ("  PgUp/PgDn, ^U/^D  scroll detail     g / G      detail top / bottom", ""),
        ("actions", "head"),
        ("  Enter         action menu (1-9 pick, Enter copy, e run via claude)", ""),
        ("  c             copy the default command for the selected row", ""),
        ("  a             ask Claude about the selected row", ""),
        ("  o             open the row's URL or newest output", ""),
        ("  s             sync tracker labels (backlog view)", ""),
        ("  f             cycle the status filter        q / Esc  quit", ""),
    ],
    "ja": [
        ("移動", "head"),
        ("  ^v / j k      行選択                <> / h l   折りたたみ / 展開", ""),
        ("  Tab / S-Tab   ビュー切替             r          今すぐ更新", ""),
        ("  PgUp/PgDn, ^U/^D  詳細スクロール     g / G      詳細の先頭 / 末尾", ""),
        ("操作", "head"),
        ("  Enter         アクションメニュー (1-9 選択, Enter コピー, e claude 実行)", ""),
        ("  c             選択行の既定コマンドをコピー", ""),
        ("  a             選択行について Claude に質問", ""),
        ("  o             行の URL または最新の出力を開く", ""),
        ("  s             トラッカーのラベルを同期 (バックログビュー)", ""),
        ("  f             状態フィルタを切替              q / Esc  終了", ""),
    ],
}


def shell_labels(lang):
    table = SHELL_LABELS.get(lang, SHELL_LABELS["en"])
    if D.ASCII_ONLY:
        return {k: D.plain(v) for k, v in table.items()}
    return table


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


def clipboard_tool():
    """The first available clipboard command, probed once; None when there is none."""
    if sys.platform == "darwin" and _which("pbcopy"):
        return ["pbcopy"]
    if os.environ.get("WAYLAND_DISPLAY") and _which("wl-copy"):
        return ["wl-copy"]
    if _which("xclip"):
        return ["xclip", "-selection", "clipboard"]
    if _which("xsel"):
        return ["xsel", "-ib"]
    return None


def _which(name):
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if d and os.access(os.path.join(d, name), os.X_OK):
            return True
    return False


def copy_clipboard(tool, text):
    """True when the copy succeeded; never raises."""
    if not tool:
        return False
    try:
        subprocess.run(tool, input=text.encode("utf-8"), timeout=5,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def open_target(target):
    """Open a URL or a file with the platform opener; True when it launched."""
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    try:
        subprocess.Popen([opener, target], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


class App:
    def __init__(self, stdscr, views, initial=0):
        self.stdscr = stdscr
        self.views = views
        self.view_idx = initial
        self.T = shell_labels(LANG)
        self.modal = None         # {"kind","row","entries","sel","title","hint"}
        self.help_open = False
        self.notice = None        # (text, style, expires_at)
        self.clip_tool = clipboard_tool()
        self.stamps = ()
        self.last_check = 0.0
        self.last_refresh = None
        self.load()

    # ------------------------------------------------------------------ data
    @property
    def view(self):
        return self.views[self.view_idx]

    def stamps_now(self):
        out = []
        for view in self.views:
            for rel in view.watch_files():
                try:
                    out.append(os.path.getmtime(os.path.join(PROJ, rel)))
                except OSError:
                    out.append(0)
            out.append(view.extra_stamp())
        return tuple(out)

    def load(self):
        for view in self.views:
            view.load()
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

    def switch_view(self, delta):
        for _ in range(len(self.views)):
            self.view_idx = (self.view_idx + delta) % len(self.views)
            if self.view.available:
                return
        # every other view is unavailable: stay where we were

    # ------------------------------------------------------------------ rows
    def selected(self, rows):
        view = self.view
        if not rows:
            view.sel_key = None
            return None
        keys = [view.row_key(r[0]) for r in rows]
        if view.sel_key in keys:
            idx = keys.index(view.sel_key)
        else:
            idx = min(view.sel_idx, len(keys) - 1)
        view.sel_idx = idx
        view.sel_key = keys[idx]
        return idx

    def selected_row(self):
        view = self.view
        for row, _, _ in view.rows():
            if view.row_key(row) == view.sel_key:
                return row
        return None

    def move(self, delta):
        view = self.view
        rows = view.rows()
        if not rows:
            return
        keys = [view.row_key(r[0]) for r in rows]
        idx = max(0, min(len(keys) - 1, view.sel_idx + delta))
        view.sel_idx = idx
        view.sel_key = keys[idx]
        view.detail_top = 0

    # ------------------------------------------------------------------ actions
    def flash(self, text, style="", seconds=5):
        self.notice = (text, style, time.time() + seconds)

    def open_menu(self, row):
        entries = self.view.actions_for(row)
        if not entries:
            return
        default = self.view.default_action(row)
        idx = next((i for i, e in enumerate(entries) if e == default), 0)
        self.modal = {"kind": "actions", "row": row, "entries": entries, "sel": idx,
                      "title": " %s %s " % (D.clip(self.view.detail_title(row), 40),
                                            self.T["actions"]),
                      "hint": self.T["menu_keys"] if EXEC_ENABLED
                      else self.T["menu_keys"].split("|")[0] + "| " + self.T["exec_hint"]}

    def open_ask(self, row):
        questions = self.view.ask_questions(row)
        entries = [(q, "") for q in questions] + [(self.T["ask_free"], "")]
        self.modal = {"kind": "ask", "row": row, "entries": entries, "sel": 0,
                      "title": " %s %s " % (D.clip(self.view.detail_title(row), 40),
                                            self.T["ask"]),
                      "hint": self.T["ask_keys"]}

    def perform(self, row, label, command, execute=False):
        if label == "open URL" or label == "open output":
            target = command
            if not target.startswith("http") and not os.path.isabs(target):
                target = os.path.join(PROJ, target)
            open_target(target)
            self.flash("%s %s" % (self.T["shown"], command), "dim")
            return
        if execute:
            self.run_claude(command)
            return
        if copy_clipboard(self.clip_tool, command):
            self.flash("%s %s %s  %s" % (self.T["copied"], D.G["arrow"], command,
                                         self.T["paste_hint"]), "accent", seconds=8)
        else:
            self.flash("%s: %s  %s" % (self.T["shown"], command,
                                       self.T["no_clipboard"]), "warn", seconds=8)

    def ask(self, row, question):
        """Send a context-carrying question to claude, or hand it to the clipboard.

        Running an agent is an explicit opt-in (--exec), the same gate the action menu
        uses; without it the fully-built prompt goes to the clipboard instead.
        """
        prompt = self.view.ask_prompt(row, question)
        if EXEC_ENABLED:
            self.run_claude(prompt)
            return
        if copy_clipboard(self.clip_tool, prompt):
            self.flash("%s  %s" % (self.T["ask_copied"], self.T["paste_hint"]),
                       "accent", seconds=8)
        else:
            self.flash("%s: %s" % (self.T["shown"], prompt), "warn", seconds=10)

    def read_line(self, prompt):
        """Read one line from the bottom bar; None when cancelled."""
        height, width = self.stdscr.getmaxyx()
        put(self.stdscr, height - 1, 0, D.pad(" " + prompt, width - 1), width - 1, "sel")
        self.stdscr.refresh()
        curses.echo()
        curses.curs_set(1)
        self.stdscr.timeout(-1)
        try:
            raw = self.stdscr.getstr(height - 1, min(width - 2, D.dw(prompt) + 2), 200)
            text = raw.decode("utf-8", "replace").strip()
        except Exception:
            text = ""
        finally:
            curses.noecho()
            curses.curs_set(0)
            self.stdscr.timeout(500)
        return text or None

    def run_claude(self, command):
        """Suspend curses, run claude in the foreground, then restore and refresh."""
        curses.endwin()
        try:
            subprocess.call(["claude", command])
        except Exception as exc:
            print("nexus-status: claude failed: %s" % exc, file=sys.stderr)
            time.sleep(2)
        self.stdscr.refresh()
        curses.curs_set(0)
        self.maybe_refresh(force=True)
        self.flash("%s %s claude" % (D.clip(command, 60), D.G["arrow"]), "accent")

    # ---------------------------------------------------------------- drawing
    def draw(self):
        stdscr = self.stdscr
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        if height < 14 or width < 50:
            put(stdscr, 0, 0, self.T["too_small"], width, "warn")
            stdscr.refresh()
            return
        view = self.view

        # header: title + clock, then the tab strip
        title = "%s %s %s" % (view.project_label(), D.G["sep"], view.title)
        clock = "%s %s %s" % (D.G["dot"], self.T["live"],
                              datetime.now().strftime("%H:%M:%S"))
        put(stdscr, 0, 0, title, width - D.dw(clock) - 1, "head")
        put(stdscr, 0, width - D.dw(clock) - 1, clock, D.dw(clock), "accent")

        x = 0
        for i, v in enumerate(self.views):
            tab = " %s " % v.title
            style = "sel" if i == self.view_idx else ("" if v.available else "dim")
            put(stdscr, 1, x, tab, width - x, style)
            x += D.dw(tab) + 1
        meta = "%s %s (%s)" % (self.T["checked"], self.last_refresh.strftime("%H:%M:%S"),
                               self.T["every"] % INTERVAL)
        put(stdscr, 1, max(x, width - D.dw(meta) - 1), meta, width - x, "dim")

        y = 2
        for text, style in view.header_lines(width)[:4]:
            put(stdscr, y, 0, text, width, style)
            y += 1

        rows = view.rows()
        idx = self.selected(rows)

        list_start = y + 1
        detail_reserve = 8
        list_h = max(3, min(len(rows) or 1, height - list_start - detail_reserve))
        counter = "%d/%d" % ((idx or 0) + 1, len(rows)) if rows else "0/0"
        put(stdscr, y, 0, D.hrule(width - D.dw(counter) - 2), width, "dim")
        put(stdscr, y, width - D.dw(counter) - 1, counter, D.dw(counter), "dim")

        if idx is None:
            put(stdscr, list_start, 2,
                view.empty_message() or self.T["empty"], width - 2, "dim")
            sep_y = list_start + 1
        else:
            if idx < view.list_top:
                view.list_top = idx
            if idx >= view.list_top + list_h:
                view.list_top = idx - list_h + 1
            view.list_top = max(0, min(view.list_top, max(0, len(rows) - list_h)))
            for i in range(list_h):
                row_i = view.list_top + i
                if row_i >= len(rows):
                    break
                row, depth, stack = rows[row_i]
                line = view.row_line(row, depth, stack, width - 2)
                style = "sel" if row_i == idx else view.row_style(row)
                put(stdscr, list_start + i, 1, D.pad(line, width - 2), width - 1, style)
            sep_y = list_start + min(list_h, len(rows))

        # separator + detail
        sel_row = self.selected_row()
        label = " %s " % self.T["detail"]
        if sel_row is not None:
            label = " %s %s %s " % (self.T["detail"], D.G["sep"],
                                    D.clip(view.detail_title(sel_row), 48))
        put(stdscr, sep_y, 0, D.hrule(width), width, "dim")
        put(stdscr, sep_y, 2, label, width - 2, "dim")

        detail_y = sep_y + 1
        detail_h = height - detail_y - 1
        lines = view.detail_lines(sel_row, width - 2) if sel_row is not None else []
        max_top = max(0, len(lines) - detail_h)
        view.detail_top = max(0, min(view.detail_top, max_top))
        for i in range(detail_h):
            j = view.detail_top + i
            if j >= len(lines):
                break
            text, style = lines[j]
            put(stdscr, detail_y + i, 1, text, width - 2, style)
        if len(lines) > detail_h:
            counter = " %d-%d/%d " % (view.detail_top + 1,
                                      min(len(lines), view.detail_top + detail_h),
                                      len(lines))
            put(stdscr, sep_y, max(0, width - D.dw(counter) - 2), counter, width, "dim")

        # bottom bar: transient notice wins over the key hints
        if self.notice and time.time() < self.notice[2]:
            text, style, _ = self.notice
            put(stdscr, height - 1, 0, D.pad(" " + text, width - 1), width - 1, style)
        else:
            self.notice = None
            put(stdscr, height - 1, 0, D.pad(view.keys_hint(), width - 1),
                width - 1, "dim")

        if self.help_open:
            self.draw_help(height, width)
        elif self.modal:
            self.draw_modal(height, width)

        # Discard what curses believes is on the screen and repaint every line. Its model
        # miscounts East Asian double-width cells, so the update optimizer skips cells it
        # thinks already match and fragments of the previous frame survive. touchwin() is
        # not enough — the redraw has to be forced. (Same fix as token_cost_tui.py.)
        stdscr.redrawwin()
        stdscr.refresh()

    def draw_box(self, y0, x0, box_w, title, rows, hint, sel=None):
        horiz = D.hrule(box_w - 2)
        put(self.stdscr, y0, x0, "+" + horiz + "+", box_w, "head")
        put(self.stdscr, y0, x0 + 2, title, box_w - 4, "head")
        for i, (text, style) in enumerate(rows):
            body = D.pad(" " + text, box_w - 2)
            put(self.stdscr, y0 + 1 + i, x0, "|", 1, "head")
            put(self.stdscr, y0 + 1 + i, x0 + 1, body, box_w - 2,
                "sel" if sel == i else style)
            put(self.stdscr, y0 + 1 + i, x0 + box_w - 1, "|", 1, "head")
        put(self.stdscr, y0 + 1 + len(rows), x0,
            "|" + D.pad(" " + hint, box_w - 2) + "|", box_w, "dim")
        put(self.stdscr, y0 + 2 + len(rows), x0, "+" + horiz + "+", box_w, "head")

    def draw_modal(self, height, width):
        modal = self.modal
        entries = modal["entries"]
        if modal["kind"] == "actions":
            rows = [("%s %d  %s  %s" % (">" if i == modal["sel"] else " ", i + 1,
                                        D.pad(label, 22), D.clip(cmd, width - 44)), "")
                    for i, (label, cmd) in enumerate(entries)]
        else:
            rows = [("%s %d  %s" % (">" if i == modal["sel"] else " ", i + 1,
                                    D.clip(label, width - 20)), "")
                    for i, (label, _) in enumerate(entries)]
        box_w = min(width - 4, max(D.dw(modal["title"]), D.dw(modal["hint"]) + 2,
                                   max(D.dw(r[0]) for r in rows) + 2) + 2)
        box_h = len(rows) + 4
        y0 = max(1, (height - box_h) // 2)
        x0 = max(1, (width - box_w) // 2)
        self.draw_box(y0, x0, box_w, modal["title"], rows, modal["hint"],
                      sel=modal["sel"])

    def draw_help(self, height, width):
        lines = list(HELP_LINES.get(LANG, HELP_LINES["en"]))
        if D.ASCII_ONLY:
            lines = [(D.plain(t), s) for t, s in lines]
        # Each view documents its own glyphs, so the legend always shows the set that
        # is actually on screen (Unicode or ASCII).
        for view in self.views:
            if view.available:
                lines += view.help_lines()
        box_w = min(width - 4, max(D.dw(t) for t, _ in lines) + 4)
        box_h = len(lines) + 4
        y0 = max(0, (height - box_h) // 2)
        x0 = max(1, (width - box_w) // 2)
        self.draw_box(y0, x0, box_w, " %s " % self.T["help"], lines,
                      self.T["help_close"])

    # ------------------------------------------------------------------- loop
    def handle_modal_key(self, key):
        modal = self.modal
        entries = modal["entries"]
        if key in (27, ord("q")):
            self.modal = None
            return
        if key in (curses.KEY_DOWN, ord("j")):
            modal["sel"] = (modal["sel"] + 1) % len(entries)
            return
        if key in (curses.KEY_UP, ord("k")):
            modal["sel"] = (modal["sel"] - 1) % len(entries)
            return
        fire = key in (curses.KEY_ENTER, 10, 13)
        if ord("1") <= key <= ord("9") and key - ord("1") < len(entries):
            modal["sel"] = key - ord("1")
            if modal["kind"] == "actions":
                return          # a number only moves the cursor; Enter runs it
            fire = True         # the ask menu has one action, so a number fires it
        if fire:
            label, cmd = entries[modal["sel"]]
            row = modal["row"]
            self.modal = None
            if modal["kind"] == "actions":
                self.perform(row, label, cmd)
            else:
                question = label
                if label == self.T["ask_free"]:
                    question = self.read_line(self.T["ask_prompt"])
                    if not question:
                        return
                self.ask(row, question)
            return
        if key == ord("e") and modal["kind"] == "actions":
            label, cmd = entries[modal["sel"]]
            row = modal["row"]
            self.modal = None
            if EXEC_ENABLED and label not in ("open URL", "open output"):
                self.perform(row, label, cmd, execute=True)
            else:
                self.flash(self.T["exec_hint"], "warn")

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
            if self.help_open:
                self.help_open = False
                continue
            if self.modal:
                self.handle_modal_key(key)
                continue
            view = self.view
            if key in (ord("q"), ord("Q"), 27):
                return
            elif key in (curses.KEY_DOWN, ord("j")):
                self.move(1)
            elif key in (curses.KEY_UP, ord("k")):
                self.move(-1)
            elif key in (curses.KEY_LEFT, ord("h")):
                view.fold(collapse=True)
            elif key in (curses.KEY_RIGHT, ord("l")):
                view.fold(collapse=False)
            elif key == 9:                              # Tab
                self.switch_view(1)
            elif key in (curses.KEY_BTAB, 353):         # Shift-Tab
                self.switch_view(-1)
            elif key in (curses.KEY_ENTER, 10, 13):
                row = self.selected_row()
                if row is not None:
                    self.open_menu(row)
            elif key == ord("a"):
                row = self.selected_row()
                if row is not None:
                    self.open_ask(row)
            elif key == ord("?"):
                self.help_open = True
            elif key == ord("c"):
                row = self.selected_row()
                act = view.default_action(row) if row is not None else None
                if act:
                    self.perform(row, act[0], act[1])
            elif key == ord("o"):
                row = self.selected_row()
                target = view.open_target(row) if row is not None else None
                if target:
                    full = target if target.startswith("http") or os.path.isabs(target) \
                        else os.path.join(PROJ, target)
                    open_target(full)
                    self.flash(target, "dim")
            elif key in (curses.KEY_NPAGE, 4):          # PgDn / Ctrl-D
                view.detail_top += 10
            elif key in (curses.KEY_PPAGE, 21):         # PgUp / Ctrl-U
                view.detail_top = max(0, view.detail_top - 10)
            elif key in (curses.KEY_HOME, ord("g")):
                view.detail_top = 0
            elif key in (curses.KEY_END, ord("G")):
                view.detail_top = 10 ** 6
            elif key in (ord("r"), ord("R")):
                self.maybe_refresh(force=True)
            elif key == curses.KEY_RESIZE:
                pass
            else:
                view.on_key(key, self)
            self.maybe_refresh()


class BaseView:
    """Per-view selection/scroll state and the defaults a view may leave alone."""

    name = "view"
    title = "view"
    available = True

    def __init__(self):
        self.sel_key = None
        self.sel_idx = 0
        self.list_top = 0
        self.detail_top = 0
        self.collapsed = set()
        self.status_filter = None

    def project_label(self):
        return os.path.basename(os.path.abspath(PROJ))

    def empty_message(self):
        return None

    def keys_hint(self):
        return ""

    def help_lines(self):
        return []

    def extra_stamp(self):
        """A number that changes when this view's non-file inputs changed."""
        return 0

    def has_children(self, row):
        return False

    def fold(self, collapse):
        return None

    def open_target(self, row):
        return None

    def on_key(self, key, app):
        return False
