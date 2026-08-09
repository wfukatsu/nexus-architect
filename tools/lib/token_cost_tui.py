"""Live two-pane dashboard for the token-cost ledger.

Upper pane: a selectable list, switchable between phases / models / sessions / days / events.
Lower pane: the detail of whatever is selected above — for a session that includes its log,
read from the Claude session transcript and priced per assistant turn.

The ledger is re-checked every NX_INTERVAL seconds and re-read only when it changed; the
selection survives the refresh. Invoked by tools/token-cost-report.sh.

Usage: token_cost_tui.py <ledger.json> <ledger.jsonl> <model-pricing.json>
"""

import curses
import locale
import os
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import token_cost_data as D  # noqa: E402

LEDGER, JSONL, PRICING = sys.argv[1], sys.argv[2], sys.argv[3]
env = os.environ.get
LANG = env("NX_LANG", "en")
CUR = env("NX_CURRENCY", "usd")
FX = float(env("NX_FX", "0") or 0)
SINCE = env("NX_SINCE", "all")
# The dashboard is read to answer "what did this cost", so the per-model components are
# priced by default; `b` switches them back to token counts. The static report keeps
# tokens as its default (see token_cost_report.py) — there, the columns are a breakdown of
# the token total the table already shows.
BREAKDOWN = env("NX_BREAKDOWN", "cost")
INTERVAL = max(1, int(env("NX_INTERVAL", "10") or 10))
PROJ = env("NX_PROJECT_DIR", ".")
DEBUG_LOG = env("NX_DEBUG_LOG", "")

T = D.labels(LANG)
TABS = ["phases", "models", "sessions", "days", "events"]
TAB_LABELS = {"phases": T["tab_phases"], "models": T["tab_models"],
              "sessions": T["tab_sessions"], "days": T["tab_days"], "events": T["tab_events"]}
MAX_EVENT_ROWS = 500
ROLE_LABEL = {"user": T["role_user"], "assistant": T["role_assistant"], "tool": T["role_tool"],
              "tool-result": T["role_toolres"], "summary": T["role_summary"]}

# style names -> (color pair index, attribute)
STYLES = {"": (0, 0), "bold": (0, curses.A_BOLD), "dim": (3, curses.A_DIM),
          "head": (1, curses.A_BOLD), "accent": (4, 0), "warn": (5, 0), "model": (6, 0),
          "sel": (2, curses.A_BOLD)}


def money(x):
    return D.money(x, CUR, FX)


toks = D.tokens


def wrap(text, width, max_lines=3):
    """Wrap by display width; returns at most max_lines lines, last one elided."""
    text = str(text)
    lines, cur = [], ""
    for ch in text:
        if D.dw(cur) + D.dw(ch) > width:
            lines.append(cur)
            cur = ch
            if len(lines) >= max_lines:
                break
        else:
            cur += ch
    if len(lines) < max_lines and cur:
        lines.append(cur)
    if D.dw("".join(lines)) < D.dw(text):
        if lines:
            lines[-1] = D.clip(lines[-1] + D.G["ellipsis"], width)
        else:
            lines = [D.clip(text, width)]
    return lines or [""]


class App:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.pricing = D.Pricing(PRICING)
        self.data = None
        self.transcripts = None
        self.tab = 0
        self.sel_idx = {t: 0 for t in TABS}
        self.sel_key = {t: None for t in TABS}
        self.list_top = {t: 0 for t in TABS}
        self.detail_top = 0
        self.breakdown = BREAKDOWN
        self.started = time.time()
        self.baseline = None
        self.stamps = ()
        self.last_check = 0.0
        self.last_refresh = None
        self.load()

    # ------------------------------------------------------------------ data
    def stamps_now(self):
        out = []
        for path in (LEDGER, JSONL):
            try:
                out.append(os.path.getmtime(path))
            except OSError:
                out.append(0)
        return tuple(out)

    def load(self):
        self.data = D.build(LEDGER, JSONL, self.pricing, SINCE)
        self.transcripts = D.Transcripts(self.data["ledger"], self.pricing)
        self.stamps = self.stamps_now()
        self.last_refresh = datetime.now()
        if self.baseline is None:
            self.baseline = self.data["totals"]["cost"]

    def maybe_refresh(self, force=False):
        now = time.time()
        if not force and now - self.last_check < INTERVAL:
            return False
        self.last_check = now
        if force or self.stamps_now() != self.stamps:
            self.load()
            return True
        return False

    # ------------------------------------------------------------------ rows
    def rows_for(self, tab):
        """(headers, aligns, rows, keys) for one tab; rows are lists of plain strings."""
        d = self.data
        total = d["totals"]["cost"] or 1.0
        if tab == "phases":
            headers = [T["phase"], T["cost"], T["share"], T["tokens"], T["modelsc"]]
            aligns = ["l", "r", "r", "r", "l"]
            rows, keys = [], []
            for p in d["phases"]:
                rows.append([p["name"], money(p["cost"]),
                             "%.1f%%" % (100 * p["cost"] / total),
                             toks(D.billed(p["usage"])), ", ".join(p["models"])])
                keys.append(p["name"])
            return headers, aligns, rows, keys
        if tab == "models":
            headers = [T["model"], T["cost"], T["share"], T["tokens"],
                       T["inp"], T["outp"], T["cread"], T["cwrite"]]
            aligns = ["l", "r", "r", "r", "r", "r", "r", "r"]
            rows, keys = [], []
            for m in d["models"]:
                u = m["usage"]
                if self.breakdown == "cost":
                    cc = self.pricing.components(u, m["model"])
                    parts = [money(cc["input_tokens"]), money(cc["output_tokens"]),
                             money(cc["cache_read_input_tokens"]), money(cc["cache_write"])]
                else:
                    parts = [toks(u["input_tokens"]), toks(u["output_tokens"]),
                             toks(u["cache_read_input_tokens"]),
                             toks(u["cache_creation_5m"] + u["cache_creation_1h"])]
                rows.append([m["model"], money(m["cost"]),
                             "%.1f%%" % (100 * m["cost"] / total), toks(D.billed(u))] + parts)
                keys.append(m["model"])
            return headers, aligns, rows, keys
        if tab == "sessions":
            headers = [T["session"], T["sname"], T["cost"], T["tokens"], T["window"]]
            aligns = ["l", "l", "r", "r", "l"]
            rows, keys = [], []
            for sid, s in sorted(d["sessions"].items(), key=lambda kv: kv[1]["last"], reverse=True):
                rows.append([sid[:8], self.transcripts.name_for(sid) or "-", money(s["cost"]),
                             toks(s["tokens"]),
                             "%s %s %s" % (s["first"].strftime("%m-%d %H:%M"), D.G["arrow"],
                                          s["last"].strftime("%m-%d %H:%M"))])
                keys.append(sid)
            return headers, aligns, rows, keys
        if tab == "days":
            headers = [T["day"], T["cost"], "", T["tokens"], T["records"], T["sessions"]]
            aligns = ["l", "r", "l", "r", "r", "r"]
            items = sorted(d["days"].items(), reverse=True)
            peak = max([v["cost"] for _, v in items] or [1.0]) or 1.0
            rows, keys = [], []
            for day, v in items:
                rows.append([day, money(v["cost"]), D.bar(v["cost"] / peak, 12),
                             toks(v["tokens"]), str(v["n"]), str(len(v["sessions"]))])
                keys.append(day)
            return headers, aligns, rows, keys
        headers = [T["when"], T["hook"], T["attributed"], T["session"], T["cost"],
                   T["tokens"], T["modelsc"]]
        aligns = ["l", "l", "l", "l", "r", "r", "l"]
        rows, keys = [], []
        for i, e in enumerate(reversed(d["events"][-MAX_EVENT_ROWS:])):
            rows.append([e["ts"].strftime("%m-%d %H:%M:%S"), e["hook"], e["to"],
                         e["session"][:8], money(e["cost"]), toks(e["tokens"]),
                         ", ".join(e["models"])])
            keys.append("%s|%s|%d" % (e["ts"].isoformat(), e["session"], i))
        return headers, aligns, rows, keys

    def selected(self, tab, keys):
        if not keys:
            return None
        key = self.sel_key.get(tab)
        if key in keys:
            idx = keys.index(key)
        else:
            idx = min(self.sel_idx.get(tab, 0), len(keys) - 1)
        self.sel_idx[tab] = idx
        self.sel_key[tab] = keys[idx]
        return idx

    # ---------------------------------------------------------------- detail
    def detail_lines(self, tab, key, width):
        d = self.data
        if key is None:
            return [(T["no_selection"], "dim")]
        if tab == "phases":
            return self.detail_phase(key, width)
        if tab == "models":
            return self.detail_model(key, width)
        if tab == "sessions":
            return self.detail_session(key, width)
        if tab == "days":
            return self.detail_day(key, width)
        idx = self.sel_idx["events"]
        recent = list(reversed(d["events"][-MAX_EVENT_ROWS:]))
        if idx >= len(recent):
            return [(T["no_selection"], "dim")]
        return self.detail_event(recent[idx], width)

    def kv_line(self, label, value, width=22):
        return ("%s%s" % (D.pad(label, width), value), "")

    def model_block(self, by_model, width):
        """Per-model table: tokens and cost of every component."""
        lines = [("%s" % T["components"], "head")]
        headers = [T["model"], T["cost"], T["tokens"], T["inp"], T["outp"], T["cread"],
                   T["cwrite"]]
        rows = []
        for model, entry in sorted(by_model.items(),
                                   key=lambda kv: -(kv[1]["cost"] if isinstance(kv[1], dict)
                                                    and "cost" in kv[1] else 0)):
            usage = entry["usage"] if isinstance(entry, dict) and "usage" in entry else entry
            cost = entry["cost"] if isinstance(entry, dict) and "cost" in entry \
                else self.pricing.cost(usage, model)
            if self.breakdown == "cost":
                cc = self.pricing.components(usage, model)
                parts = [money(cc["input_tokens"]), money(cc["output_tokens"]),
                         money(cc["cache_read_input_tokens"]), money(cc["cache_write"])]
            else:
                parts = [toks(usage["input_tokens"]), toks(usage["output_tokens"]),
                         toks(usage["cache_read_input_tokens"]),
                         toks(usage["cache_creation_5m"] + usage["cache_creation_1h"])]
            rows.append([model, money(cost), toks(D.billed(usage))] + parts)
        lines += table_lines(headers, rows, ["l", "r", "r", "r", "r", "r", "r"], width)
        return lines

    def detail_phase(self, name, width):
        phase = next((p for p in self.data["phases"] if p["name"] == name), None)
        if not phase:
            return [(T["no_selection"], "dim")]
        total = self.data["totals"]["cost"] or 1.0
        lines = [(name, "head")]
        if phase["kind"] == "unassigned":
            lines.append((T["unassigned"], "dim"))
        elif phase["kind"] == "pending":
            lines.append((T["pending"], "dim"))
        lines += [
            self.kv_line(T["cost"], "%s  (%.1f%%)" % (money(phase["cost"]),
                                                      100 * phase["cost"] / total)),
            self.kv_line(T["billed_tokens"], toks(D.billed(phase["usage"]))),
            ("", ""),
        ]
        lines += self.model_block(phase["by_model"], width)
        contributors = {}
        for e in self.data["events"]:
            if e["to"] == name and e["session"]:
                contributors[e["session"]] = contributors.get(e["session"], 0.0) + e["cost"]
        if contributors:
            lines += [("", ""), (T["contributors"], "head")]
            rows = [[sid[:8], money(cost), D.clip(self.transcripts.name_for(sid) or "-",
                                                  max(20, width - 26))]
                    for sid, cost in sorted(contributors.items(), key=lambda kv: -kv[1])[:8]]
            lines += table_lines([T["session"], T["cost"], T["sname"]], rows,
                                 ["l", "r", "l"], width)
        return lines

    def detail_model(self, model, width):
        entry = next((m for m in self.data["models"] if m["model"] == model), None)
        if not entry:
            return [(T["no_selection"], "dim")]
        total = self.data["totals"]["cost"] or 1.0
        usage, cc = entry["usage"], self.pricing.components(entry["usage"], model)
        fam = self.pricing.family(model)
        price_in, price_out = self.pricing.prices(fam)
        lines = [
            (model, "head"),
            self.kv_line(T["cost"], "%s  (%.1f%%)" % (money(entry["cost"]),
                                                      100 * entry["cost"] / total)),
            self.kv_line(T["billed_tokens"], toks(D.billed(usage))),
            self.kv_line(T["pricing"], "in $%.2f / out $%.2f %s" % (price_in, price_out,
                                                                    T["per_1m"])),
            ("", ""),
            (T["components"], "head"),
        ]
        rows = [
            [T["inp"], toks(usage["input_tokens"]), money(cc["input_tokens"])],
            [T["outp"], toks(usage["output_tokens"]), money(cc["output_tokens"])],
            [T["cread"], toks(usage["cache_read_input_tokens"]),
             money(cc["cache_read_input_tokens"])],
            [T["cwrite"], toks(usage["cache_creation_5m"] + usage["cache_creation_1h"]),
             money(cc["cache_write"])],
        ]
        lines += table_lines(["", T["tokens"], T["cost"]], rows, ["l", "r", "r"], width)
        used = [(p["name"], p["by_model"][model]["cost"])
                for p in self.data["phases"] if model in p["by_model"]]
        if used:
            lines += [("", ""), (T["used_by"], "head")]
            lines += table_lines([T["phase"], T["cost"]],
                                 [[n, money(cost)] for n, cost in sorted(used, key=lambda x: -x[1])],
                                 ["l", "r"], width)
        sess = {}
        for sid, s in self.data["sessions"].items():
            if model in s["by_model"]:
                sess[sid] = self.pricing.cost(s["by_model"][model], model)
        if sess:
            lines += [("", ""), (T["contributors"], "head")]
            rows = [[sid[:8], money(cost), D.clip(self.transcripts.name_for(sid) or "-",
                                                  max(20, width - 26))]
                    for sid, cost in sorted(sess.items(), key=lambda kv: -kv[1])[:8]]
            lines += table_lines([T["session"], T["cost"], T["sname"]], rows,
                                 ["l", "r", "l"], width)
        return lines

    def detail_session(self, sid, width):
        s = self.data["sessions"].get(sid)
        if not s:
            return [(T["no_selection"], "dim")]
        path = self.transcripts.path_for(sid)
        lines = [
            (self.transcripts.name_for(sid) or sid, "head"),
            self.kv_line(T["session"], sid),
            self.kv_line(T["cost"], "%s   %s %s   %d %s" % (
                money(s["cost"]), toks(s["tokens"]), T["tokens"], s["n"], T["records"])),
            self.kv_line(T["window"], "%s %s %s" % (s["first"].strftime("%Y-%m-%d %H:%M:%S"),
                                                  D.G["arrow"],
                                                   s["last"].strftime("%Y-%m-%d %H:%M:%S"))),
            self.kv_line(T["attributed"], ", ".join(sorted(p for p in s["phases"] if p)) or "-"),
            self.kv_line(T["transcript"],
                         D.clip(path or T["no_transcript"], max(20, width - 23))),
            ("", ""),
        ]
        lines += self.model_block(s["by_model"], width)
        lines.append(("", ""))
        if not path:
            lines.append((T["no_transcript"], "warn"))
            return lines
        log = self.transcripts.log_for(sid)
        lines.append(("%s (%d %s)" % (T["log"], len(log), T["turns"]), "head"))
        lines += self.log_lines(log, width)
        return lines

    def log_lines(self, log, width, limit=None):
        out = []
        entries = log[-limit:] if limit else log
        for entry in entries:
            stamp = entry["ts"].strftime("%m-%d %H:%M:%S") if entry["ts"] else " " * 14
            role = ROLE_LABEL.get(entry["kind"], entry["kind"])
            cost = ""
            if entry.get("cost"):
                cost = "  %s / %s" % (money(entry["cost"]), toks(entry["tokens"]))
            style = {"user": "accent", "assistant": "", "tool": "model",
                     "tool-result": "dim", "summary": "warn"}.get(entry["kind"], "")
            prefix = "%s  %s " % (stamp, D.pad(role, 11))
            body_width = max(20, width - D.dw(prefix))
            body = wrap(entry["text"], body_width, 4 if entry["kind"] in ("user", "assistant") else 1)
            out.append((prefix + body[0] + (cost if len(body) == 1 else ""), style))
            for extra in body[1:]:
                out.append((" " * D.dw(prefix) + extra, style))
            if len(body) > 1 and cost:
                out.append((" " * D.dw(prefix) + cost.strip(), "dim"))
        return out or [(T["no_events"], "dim")]

    def detail_day(self, day, width):
        v = self.data["days"].get(day)
        if not v:
            return [(T["no_selection"], "dim")]
        lines = [
            (day, "head"),
            self.kv_line(T["cost"], "%s   %s %s   %d %s" % (
                money(v["cost"]), toks(v["tokens"]), T["tokens"], v["n"], T["records"])),
            self.kv_line(T["modelsc"], ", ".join(sorted(v["models"]))),
            self.kv_line(T["attributed"], ", ".join(sorted(p for p in v["phases"] if p)) or "-"),
            ("", ""),
        ]
        per_session = {}
        for e in self.data["events"]:
            if e["ts"].strftime("%Y-%m-%d") == day and e["session"]:
                per_session[e["session"]] = per_session.get(e["session"], 0.0) + e["cost"]
        if per_session:
            lines.append((T["top_sessions"], "head"))
            rows = [[sid[:8], money(cost), D.clip(self.transcripts.name_for(sid) or "-",
                                                  max(20, width - 26))]
                    for sid, cost in sorted(per_session.items(), key=lambda kv: -kv[1])]
            lines += table_lines([T["session"], T["cost"], T["sname"]], rows,
                                 ["l", "r", "l"], width)
        hours = {}
        for e in self.data["events"]:
            if e["ts"].strftime("%Y-%m-%d") == day:
                hours[e["ts"].strftime("%H")] = hours.get(e["ts"].strftime("%H"), 0.0) + e["cost"]
        if hours:
            peak = max(hours.values()) or 1.0
            lines += [("", ""), (T["timeline"], "head")]
            rows = [["%s:00" % h, money(cost), D.bar(cost / peak, 24)]
                    for h, cost in sorted(hours.items())]
            lines += table_lines(["", T["cost"], ""], rows, ["l", "r", "l"], width)
        return lines

    def detail_event(self, event, width):
        lines = [
            (event["ts"].strftime("%Y-%m-%d %H:%M:%S"), "head"),
            self.kv_line(T["hook"], event["hook"]),
            self.kv_line(T["attributed"], event["to"] or "-"),
            self.kv_line(T["cost"], "%s   %s %s" % (money(event["cost"]),
                                                    toks(event["tokens"]), T["tokens"])),
            self.kv_line(T["session"], "%s  %s" % (
                event["session"][:8],
                D.clip(self.transcripts.name_for(event["session"]) or "-",
                       max(20, width - 34)))),
        ]
        if event["in_progress"]:
            lines.append(self.kv_line(T["ev_running"], ", ".join(event["in_progress"])))
        if event["newly_completed"]:
            lines.append(self.kv_line(T["ev_completed"], ", ".join(event["newly_completed"])))
        if event["pending_flushed"]:
            lines.append(self.kv_line(T["ev_flushed"], "true"))
        lines.append(("", ""))
        lines += self.model_block({m: u for m, u in event["by_model"].items()}, width)
        log = self.transcripts.log_for(event["session"])
        if log:
            window = timedelta(minutes=2)
            near = [e for e in log if e["ts"] and abs(e["ts"] - event["ts"]) <= window]
            lines += [("", ""), (T["nearby"], "head")]
            lines += self.log_lines(near or log, width, limit=25)
        return lines

    # ---------------------------------------------------------------- drawing
    def draw(self):
        stdscr = self.stdscr
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        if height < 12 or width < 50:
            put(stdscr, 0, 0, "terminal too small", width, "warn")
            stdscr.refresh()
            return
        d = self.data
        totals = d["totals"]

        # header
        title = "%s %s %s" % (d["project"] or os.path.basename(PROJ), D.G["sep"], T["title"])
        clock = "%s %s %s" % (D.G["dot"], T["live"], datetime.now().strftime("%H:%M:%S"))
        put(stdscr, 0, 0, title, width - D.dw(clock) - 1, "head")
        put(stdscr, 0, width - D.dw(clock) - 1, clock, D.dw(clock), "accent")
        summary = "%s %s   %s +%s   %s %s   %s %s / %s %s" % (
            T["total_cost"], money(totals["cost"]),
            T["since_watch"], money(totals["cost"] - (self.baseline or 0.0)),
            T["billed_tokens"], toks(totals["tokens"]),
            T["records"], d["records"], T["sessions"], len(d["sessions"]))
        put(stdscr, 1, 0, summary, width, "bold")
        meta = (" %s " % D.G["sep"]).join((
            "%s %s" % (T["updated"], d["updated_at"] or "-"),
            "%s %s" % (T["pricing"], d["pricing_version"]),
            "%s %s (%s)" % (T["refreshed"], self.last_refresh.strftime("%H:%M:%S"),
                            T["watching"].format(s=INTERVAL)),
            T["n_win"].format(w=SINCE if D.since_cutoff(SINCE) else T["all_time"])))
        put(stdscr, 2, 0, meta, width, "dim")

        # tabs
        col = 0
        for i, tab in enumerate(TABS):
            label = " %d %s " % (i + 1, TAB_LABELS[tab])
            put(stdscr, 3, col, label, max(0, width - col), "sel" if i == self.tab else "dim")
            col += D.dw(label) + 1
            if col >= width:
                break

        headers, aligns, rows, keys = self.rows_for(TABS[self.tab])
        tab = TABS[self.tab]
        idx = self.selected(tab, keys)

        # The list pane never grows past its own content: a one-row view must not leave a
        # void above a detail pane that is being cut off at the bottom.
        list_h = max(1, min(len(rows), max(3, int((height - 8) * 0.42))))
        list_start = 5
        widths = column_widths(headers, rows, aligns, width - 2)
        header_line = render_row(headers, widths, aligns)
        if len(rows) > list_h and idx is not None:
            counter = "%d/%d" % (idx + 1, len(rows))
            header_line = D.pad(D.clip(header_line, width - D.dw(counter) - 3),
                                width - D.dw(counter) - 3) + " " + counter
        put(stdscr, 4, 1, header_line, width - 1, "dim")

        if idx is None:
            put(stdscr, list_start, 2, T["no_selection"], width - 2, "dim")
        else:
            top = self.list_top[tab]
            if idx < top:
                top = idx
            if idx >= top + list_h:
                top = idx - list_h + 1
            top = max(0, min(top, max(0, len(rows) - list_h)))
            self.list_top[tab] = top
            for i in range(list_h):
                row_i = top + i
                if row_i >= len(rows):
                    break
                text = render_row(rows[row_i], widths, aligns)
                put(stdscr, list_start + i, 1, D.pad(text, width - 2), width - 1,
                    "sel" if row_i == idx else "")

        # separator
        sep_y = list_start + list_h
        label = " %s " % T["detail"]
        put(stdscr, sep_y, 0, D.hrule(width), width, "dim")
        put(stdscr, sep_y, 2, label, width - 2, "dim")

        # detail pane
        detail_y = sep_y + 1
        detail_h = height - detail_y - 1
        lines = self.detail_lines(tab, self.sel_key.get(tab), width - 2)
        max_top = max(0, len(lines) - detail_h)
        self.detail_top = max(0, min(self.detail_top, max_top))
        for i in range(detail_h):
            j = self.detail_top + i
            if j >= len(lines):
                break
            text, style = lines[j]
            put(stdscr, detail_y + i, 1, text, width - 1, style)
        if len(lines) > detail_h:
            # On the separator, not over the last detail line — that row holds real content.
            counter = " %d-%d/%d " % (self.detail_top + 1,
                                      min(len(lines), self.detail_top + detail_h), len(lines))
            put(stdscr, sep_y, max(0, width - D.dw(counter) - 2), counter, width, "dim")

        # One column short of the edge: writing the bottom-right cell advances the cursor
        # off the screen and curses returns ERR, which dropped the last cell of this row on
        # every frame. (--debug surfaced it; it had been failing silently.)
        put(stdscr, height - 1, 0, D.pad(T["keys"], width - 1), width - 1, "dim")
        # Which unit the in/out/cache columns are in, pinned right: the columns themselves
        # carry no unit, so without this the reader cannot tell $ from token counts at a
        # glance — and `b` is the only way back.
        bd = T["k_bd_cost"] if self.breakdown == "cost" else T["k_bd_tokens"]
        if D.dw(T["keys"]) + D.dw(bd) + 3 <= width - 1:
            put(stdscr, height - 1, width - D.dw(bd) - 2, bd, width - 1, "dim")
        # Discard what curses believes is on the screen and repaint every line. Its model
        # miscounts East Asian double-width cells, so the update optimizer skips cells it
        # thinks already match and fragments of the previous frame survive — a session's cost
        # table showing the previous tab's numbers, labels reading "計上先ークン". touchwin()
        # is not enough: that re-copies the window but still diffs against the same stale
        # model, so the redraw has to be forced.
        stdscr.redrawwin()
        stdscr.refresh()

    # ------------------------------------------------------------------- loop
    def move(self, delta):
        tab = TABS[self.tab]
        _, _, rows, keys = self.rows_for(tab)
        if not keys:
            return
        idx = max(0, min(len(keys) - 1, self.sel_idx.get(tab, 0) + delta))
        self.sel_idx[tab] = idx
        self.sel_key[tab] = keys[idx]
        self.detail_top = 0

    def switch(self, delta):
        self.tab = (self.tab + delta) % len(TABS)
        self.detail_top = 0

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
            if key in (ord("q"), ord("Q"), 27):
                return
            elif key in (curses.KEY_DOWN, ord("j")):
                self.move(1)
            elif key in (curses.KEY_UP, ord("k")):
                self.move(-1)
            elif key in (curses.KEY_RIGHT, ord("\t"), ord("l")):
                self.switch(1)
            elif key in (curses.KEY_LEFT, curses.KEY_BTAB, ord("h")):
                self.switch(-1)
            elif ord("1") <= key <= ord("5"):
                self.tab = key - ord("1")
                self.detail_top = 0
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
            elif key == ord("b"):
                self.breakdown = "cost" if self.breakdown == "tokens" else "tokens"
            elif key == curses.KEY_RESIZE:
                pass
            self.maybe_refresh()


# ------------------------------------------------------------------- utilities
def column_widths(headers, rows, aligns, total_width):
    widths = [max([D.dw(h)] + [D.dw(r[i]) for r in rows]) for i, h in enumerate(headers)]
    while sum(widths) + 2 * len(widths) > total_width:
        candidates = [i for i in range(len(widths)) if widths[i] > 6]
        if not candidates:
            break
        widths[max(candidates, key=lambda i: widths[i])] -= 1
    return widths


def render_row(cells, widths, aligns):
    return "  ".join(D.pad(D.clip(cell, widths[i]), widths[i], aligns[i])
                     for i, cell in enumerate(cells))


def table_lines(headers, rows, aligns, width):
    widths = column_widths(headers, rows, aligns, width)
    out = [(render_row(headers, widths, aligns), "dim")]
    for row in rows:
        out.append((render_row(row, widths, aligns), ""))
    return out


def debug(fmt, *args):
    """Append one line to the debug log, when --debug asked for one."""
    if not DEBUG_LOG:
        return
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as fh:
            fh.write("%s %s\n" % (datetime.now().strftime("%H:%M:%S.%f")[:-3], fmt % args))
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
        # Writing the bottom-right cell always raises, and so does anything curses thinks
        # runs past the edge — which is how a width miscount shows up. Swallowing these
        # silently is what made the repaint bug invisible, so record them under --debug.
        # Still non-fatal: one dropped cell must not take the dashboard down.
        debug("addstr failed y=%d x=%d dw=%d width=%d style=%s: %s | %r",
              y, x, D.dw(text), width, style or "-", exc, text[:60])


def main(stdscr):
    # The rendering environment, recorded once: which of these disagree is the whole
    # question when the screen comes out garbled or misaligned.
    debug("start term=%s encoding=%s locale=%s ncurses=%s size=%dx%d "
          "glyphs=%s ambiguous_wide=%s bar=%r/%r",
          os.environ.get("TERM", "-"), getattr(sys.stdout, "encoding", "-"),
          locale.setlocale(locale.LC_CTYPE), curses.version, *stdscr.getmaxyx()[::-1],
          "ascii" if D.ASCII_ONLY else "unicode", D.AMBIGUOUS_WIDE,
          D.BAR_FULL, D.BAR_EMPTY)
    if curses.has_colors():
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(3, curses.COLOR_WHITE, -1)
        curses.init_pair(4, curses.COLOR_GREEN, -1)
        curses.init_pair(5, curses.COLOR_YELLOW, -1)
        curses.init_pair(6, curses.COLOR_MAGENTA, -1)
    App(stdscr).run()


if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, "")
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
