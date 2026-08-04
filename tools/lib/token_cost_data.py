"""Shared data layer for the token-cost report tools.

Loads the ledger the agent records while it runs (work/token-usage.json and
work/token-usage.jsonl), prices it from skills/common/references/model-pricing.json, and
resolves Claude session transcripts so a session can be shown by name and by log.

Consumed by tools/lib/token_cost_report.py (one-shot report / Markdown / JSON) and
tools/lib/token_cost_tui.py (live two-pane dashboard). Pricing semantics mirror
hooks/record_token_usage.py — that hook writes the ledger, this module reads it.
"""

import glob
import json
import os
import sys
import unicodedata
from datetime import date, datetime, timedelta

USAGE_KEYS = ["input_tokens", "output_tokens", "cache_read_input_tokens",
              "cache_creation_5m", "cache_creation_1h", "web_search_requests"]
TOKEN_KEYS = USAGE_KEYS[:5]


# --------------------------------------------------------------------------- basics
def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def zero():
    return {k: 0 for k in USAGE_KEYS}


def add(dst, src):
    for k in USAGE_KEYS:
        dst[k] += int((src or {}).get(k, 0) or 0)
    return dst


def billed(usage):
    """Billed tokens: everything the API charges for, excluding server-tool requests."""
    return sum(int((usage or {}).get(k, 0) or 0) for k in TOKEN_KEYS)


def parse_ts(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone()
    except Exception:
        return None


def since_cutoff(spec):
    """'24h' / '7d' / '2026-07-01' / 'all' -> aware datetime or None."""
    spec = (spec or "all").strip().lower()
    if spec in ("", "all", "0"):
        return None
    now = datetime.now().astimezone()
    if spec.endswith("h") and spec[:-1].isdigit():
        return now - timedelta(hours=int(spec[:-1]))
    if spec.endswith("d") and spec[:-1].isdigit():
        return now - timedelta(days=int(spec[:-1]))
    try:
        return datetime.fromisoformat(spec).astimezone()
    except Exception:
        return None


# --------------------------------------------------------------------------- pricing
class Pricing:
    """Prices from model-pricing.json, including time-limited introductory rates."""

    def __init__(self, path):
        self.path = path
        self.data = load_json(path, {}) or {}

    @property
    def version(self):
        return self.data.get("version") or "-"

    def family(self, model):
        m = (model or "").lower()
        for fam in self.data.get("families", []):
            for sub in fam.get("match", []):
                if sub in m:
                    return fam
        return self.data.get("default", {"input": 3.0, "output": 15.0})

    def prices(self, fam):
        inp, out = fam.get("input", 3.0), fam.get("output", 15.0)
        until = fam.get("intro_until")
        if until and "intro_input" in fam:
            try:
                if date.today() <= date.fromisoformat(until):
                    inp, out = fam.get("intro_input", inp), fam.get("intro_output", out)
            except Exception:
                pass
        return inp, out

    def components(self, usage, model):
        """Per-component cost (USD) of one model's usage."""
        fam = self.family(model)
        mult = self.data.get("cache_multipliers", {})
        inp, out = self.prices(fam)
        usage = usage or {}
        return {
            "input_tokens": usage.get("input_tokens", 0) * inp / 1e6,
            "output_tokens": usage.get("output_tokens", 0) * out / 1e6,
            "cache_read_input_tokens":
                usage.get("cache_read_input_tokens", 0) * inp * mult.get("read", 0.1) / 1e6,
            "cache_write":
                (usage.get("cache_creation_5m", 0) * mult.get("write_5m", 1.25)
                 + usage.get("cache_creation_1h", 0) * mult.get("write_1h", 2.0)) * inp / 1e6,
        }

    def cost(self, usage, model):
        total = sum(self.components(usage, model).values())
        per_1k = (self.data.get("server_tools") or {}).get("web_search_per_1k", 0.0)
        return total + (usage or {}).get("web_search_requests", 0) * per_1k / 1000.0

    def cost_by_model(self, by_model):
        return sum(self.cost(u, m) for m, u in (by_model or {}).items())


# ----------------------------------------------------------------------- transcripts
class Transcripts:
    """Claude session transcripts: which file holds a session, its name, and its log.

    The ledger records every transcript it has read (`_transcripts`); anything missing from
    it is looked up under ~/.claude/projects/*/<session-id>.jsonl.
    """

    def __init__(self, ledger, pricing=None):
        self.pricing = pricing
        self.index = {}
        for path in (ledger.get("_transcripts") or {}).keys():
            base = os.path.basename(path)
            if base.endswith(".jsonl"):
                self.index[base[:-6]] = path
        self._names = {}
        self._logs = {}

    def path_for(self, sid):
        path = self.index.get(sid)
        if path and os.path.exists(path):
            return path
        hits = glob.glob(os.path.expanduser("~/.claude/projects/*/%s.jsonl" % sid))
        return hits[0] if hits else None

    # -- name ---------------------------------------------------------------
    def name_for(self, sid):
        if not sid:
            return ""
        if sid in self._names:
            return self._names[sid]
        path = self.path_for(sid)
        self._names[sid] = self._read_name(path) if path else ""
        return self._names[sid]

    def _read_name(self, path, max_lines=400):
        first_user = ""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    if rec.get("type") == "summary" and rec.get("summary"):
                        return clean(rec["summary"])
                    if first_user or rec.get("type") != "user" or rec.get("isMeta"):
                        continue
                    msg = rec.get("message") or {}
                    if msg.get("role") != "user":
                        continue
                    text = clean(flatten_text(msg.get("content")))
                    # skip harness-injected turns: reminders, command wrappers, caveats
                    if not text or text.startswith("<") or text.lower().startswith("caveat:"):
                        continue
                    first_user = text
        except Exception:
            pass
        return first_user

    # -- log ----------------------------------------------------------------
    def log_for(self, sid, max_entries=4000):
        """Compact conversation log for one session, priced per assistant turn.

        Entries: {ts, kind, text, model, tokens, cost} where kind is
        user | assistant | tool | tool-result | summary.
        """
        if not sid:
            return []
        path = self.path_for(sid)
        if not path:
            return []
        try:
            stamp = os.path.getmtime(path)
        except OSError:
            return []
        cached = self._logs.get(sid)
        if cached and cached[0] == stamp:
            return cached[1]

        entries, seen_ids = [], set()
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    entries.extend(self._entries_from(rec, seen_ids))
        except Exception:
            return []
        entries = entries[-max_entries:]
        self._logs[sid] = (stamp, entries)
        return entries

    def _entries_from(self, rec, seen_ids):
        kind_type = rec.get("type")
        ts = parse_ts(rec.get("timestamp"))
        out = []
        if kind_type == "summary" and rec.get("summary"):
            out.append(dict(ts=ts, kind="summary", text=clean(rec["summary"]),
                            model="", tokens=0, cost=0.0))
            return out
        msg = rec.get("message") or {}
        content = msg.get("content")
        if kind_type == "user":
            results = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_result"] \
                if isinstance(content, list) else []
            if results:
                for blk in results:
                    body = clean(flatten_text(blk.get("content")))
                    flag = "error" if blk.get("is_error") else ""
                    out.append(dict(ts=ts, kind="tool-result", text=body or "(empty)",
                                    model=flag, tokens=0, cost=0.0))
            else:
                text = clean(flatten_text(content))
                if text:
                    out.append(dict(ts=ts, kind="user", text=text, model="",
                                    tokens=0, cost=0.0))
        elif kind_type == "assistant":
            mid = msg.get("id") or rec.get("uuid")
            usage, cost = zero(), 0.0
            model = msg.get("model") or ""
            # one API response can span several lines sharing a message id: price it once
            if mid and mid not in seen_ids:
                seen_ids.add(mid)
                usage = usage_from_transcript(msg.get("usage"))
                cost = self.pricing.cost(usage, model) if self.pricing else 0.0
            text = clean(flatten_text(content))
            blocks = content if isinstance(content, list) else []
            thinking = clean(" ".join(str(b.get("thinking") or "") for b in blocks
                                      if isinstance(b, dict) and b.get("type") == "thinking"))
            tools = [b.get("name") for b in blocks
                     if isinstance(b, dict) and b.get("type") == "tool_use"]

            def emit(kind, body):
                # the turn's cost lands on its first entry, so a turn is never counted twice
                nonlocal usage, cost
                out.append(dict(ts=ts, kind=kind, text=body, model=model,
                                tokens=billed(usage), cost=cost))
                usage, cost = zero(), 0.0

            if thinking:
                emit("thinking", thinking)
            if text:
                emit("assistant", text)
            for name in tools:
                emit("tool", str(name))
            if not thinking and not text and not tools and billed(usage):
                emit("assistant", "(no text)")
        return out


def usage_from_transcript(u):
    """Transcript usage block -> ledger usage shape (same rules as the recorder hook)."""
    u = u or {}
    acc = zero()
    acc["input_tokens"] = int(u.get("input_tokens") or 0)
    acc["output_tokens"] = int(u.get("output_tokens") or 0)
    acc["cache_read_input_tokens"] = int(u.get("cache_read_input_tokens") or 0)
    cc = u.get("cache_creation") or {}
    c5 = int(cc.get("ephemeral_5m_input_tokens") or 0)
    c1 = int(cc.get("ephemeral_1h_input_tokens") or 0)
    if c5 or c1:
        acc["cache_creation_5m"], acc["cache_creation_1h"] = c5, c1
    else:
        acc["cache_creation_5m"] = int(u.get("cache_creation_input_tokens") or 0)
    st = u.get("server_tool_use") or {}
    acc["web_search_requests"] = int(st.get("web_search_requests") or 0)
    return acc


def flatten_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for blk in content:
            if isinstance(blk, dict) and blk.get("type") == "text":
                parts.append(str(blk.get("text") or ""))
            elif isinstance(blk, str):
                parts.append(blk)
        return " ".join(parts)
    return ""


def clean(text):
    return " ".join(str(text).split()).strip()


# ------------------------------------------------------------------------ aggregation
def build(ledger_path, jsonl_path, pricing, since="all"):
    """Aggregate both ledger artifacts into one report structure."""
    ledger = load_json(ledger_path, {}) or {}
    phases, model_usage = [], {}

    def collect(name, by_model, kind):
        usage, cost, per_model = zero(), 0.0, {}
        for model, u in (by_model or {}).items():
            add(usage, u)
            mc = pricing.cost(u, model)
            cost += mc
            per_model[model] = dict(usage=dict(u), cost=mc)
            add(model_usage.setdefault(model, zero()), u)
        if billed(usage) == 0:
            return
        phases.append(dict(name=name, kind=kind, usage=usage, cost=cost,
                           by_model=per_model, models=sorted((by_model or {}).keys())))

    for name, phase in (ledger.get("phases") or {}).items():
        collect(name, phase.get("by_model"), "unassigned" if name == "_unassigned" else "phase")
    collect("_pending", (ledger.get("_pending") or {}).get("by_model"), "pending")
    phases.sort(key=lambda r: -r["cost"])

    total_cost = sum(p["cost"] for p in phases)
    total_usage = zero()
    for p in phases:
        add(total_usage, p["usage"])

    models = sorted((dict(model=m, usage=u, cost=pricing.cost(u, m))
                     for m, u in model_usage.items() if billed(u) > 0),
                    key=lambda r: -r["cost"])

    cutoff = since_cutoff(since)
    events, days, sessions = [], {}, {}
    first_ts = last_ts = None
    records = 0
    try:
        with open(jsonl_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                ts = parse_ts(rec.get("ts"))
                if ts is None or (cutoff and ts < cutoff):
                    continue
                records += 1
                first_ts = ts if first_ts is None or ts < first_ts else first_ts
                last_ts = ts if last_ts is None or ts > last_ts else last_ts
                by_model = rec.get("delta_by_model") or {}
                usage, cost = zero(), 0.0
                for model, u in by_model.items():
                    add(usage, u)
                    cost += pricing.cost(u, model)
                sid = rec.get("session_id") or ""
                phase_key = rec.get("attributed_to") or ""
                event = dict(ts=ts, hook=rec.get("hook", ""), to=phase_key, session=sid,
                             by_model={m: dict(u) for m, u in by_model.items()},
                             models=sorted(by_model.keys()), usage=usage, cost=cost,
                             tokens=billed(usage),
                             newly_completed=rec.get("newly_completed") or [],
                             in_progress=rec.get("in_progress") or [],
                             pending_flushed=bool(rec.get("pending_flushed")))
                events.append(event)

                day = days.setdefault(ts.strftime("%Y-%m-%d"),
                                      dict(cost=0.0, tokens=0, n=0, models=set(),
                                           sessions=set(), phases=set()))
                day["cost"] += cost
                day["tokens"] += event["tokens"]
                day["n"] += 1
                day["models"].update(by_model.keys())
                day["sessions"].add(sid)
                day["phases"].add(phase_key)

                ses = sessions.setdefault(sid, dict(cost=0.0, tokens=0, n=0, first=ts, last=ts,
                                                    models=set(), phases=set(),
                                                    by_model={}))
                ses["cost"] += cost
                ses["tokens"] += event["tokens"]
                ses["n"] += 1
                ses["models"].update(by_model.keys())
                ses["phases"].add(phase_key)
                ses["first"] = min(ses["first"], ts)
                ses["last"] = max(ses["last"], ts)
                for model, u in by_model.items():
                    add(ses["by_model"].setdefault(model, zero()), u)
    except FileNotFoundError:
        pass

    return dict(
        ledger=ledger, ledger_path=ledger_path, jsonl_path=jsonl_path,
        project=ledger.get("project_name") or "",
        updated_at=(ledger.get("updated_at") or "")[:19].replace("T", " "),
        pricing_version=pricing.version,
        phases=phases, models=models, events=events, days=days, sessions=sessions,
        totals=dict(cost=total_cost, usage=total_usage, tokens=billed(total_usage),
                    ledger_cost=float(ledger.get("total_cost_usd") or 0.0)),
        records=records, first_ts=first_ts, last_ts=last_ts, since=since,
    )


# -------------------------------------------------------------------------- rendering
# The characters the report draws with fail in two *separate* ways — do not conflate them:
#
#   Misalignment. U+2588 █, U+2500 ─, U+00B7 ·, U+2192 →, U+25CF ●, U+03A3 Σ and U+2026 …
#   are East Asian *Ambiguous* width. A terminal told to render ambiguous characters
#   double-width (the usual setting in Japanese environments) draws each one twice as wide
#   as dw() counts by default, so bars overrun their column. That is what AMBIGUOUS_WIDE
#   below corrects; it never produces garbled characters.
#
#   Garbled characters. A terminal or font without a glyph prints a replacement box. Note
#   that U+2591 ░ — the likeliest one to be missing — is *Neutral*, not Ambiguous, so no
#   amount of width bookkeeping helps: the fix is a different character set entirely.
#
# The ASCII set has neither problem, and is what gets used when the output is not UTF-8.
UNICODE_GLYPHS = dict(bar_full="█", bar_empty="░", rule="─", sep="·", arrow="→",
                      dot="●", sigma="Σ", ellipsis="…")
ASCII_GLYPHS = dict(bar_full="#", bar_empty=".", rule="-", sep="|", arrow="->",
                    dot="*", sigma="sum", ellipsis="..")
# Applied to the translated label strings, which embed the same characters inline.
TO_ASCII = {"█": "#", "░": ".", "─": "-", "·": "|", "→": "->", "←": "<-",
            "↑": "^", "↓": "v", "●": "*", "Σ": "sum", "…": "..", "／": "/", "—": "-"}
# Adjacent pairs first, so the key hints read "^v" and "<>" rather than "^v" and "<--->".
TO_ASCII_PAIRS = (("↑↓", "^v"), ("←→", "<>"), ("→←", "><"))


def _ascii_mode():
    mode = os.environ.get("NX_GLYPHS", "auto").lower()
    if mode in ("ascii", "unicode"):
        return mode == "ascii"
    enc = (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "").replace("_", "")
    return "utf8" not in enc


ASCII_ONLY = _ascii_mode()
G = ASCII_GLYPHS if ASCII_ONLY else UNICODE_GLYPHS
# There is no reliable way to ask a terminal how it renders ambiguous-width characters, so
# this is the user's call (--ambiguous-width=2), never guessed from $TERM or the locale.
AMBIGUOUS_WIDE = os.environ.get("NX_AMBIGUOUS", "1") == "2"
WIDE_CLASSES = ("W", "F", "A") if AMBIGUOUS_WIDE else ("W", "F")

try:  # a terminal in a non-UTF-8 locale still gets a report, not an encoding traceback
    sys.stdout.reconfigure(errors="replace")
except (AttributeError, ValueError):
    pass


def plain(text):
    """Swap the drawing characters embedded in a label for their ASCII stand-ins."""
    text = str(text)
    for pair, repl in TO_ASCII_PAIRS:
        text = text.replace(pair, repl)
    return "".join(TO_ASCII.get(ch, ch) for ch in text)


def dw(text):
    """Display width in terminal columns, per the configured ambiguous-width rule."""
    return sum(2 if unicodedata.east_asian_width(ch) in WIDE_CLASSES else 1 for ch in str(text))


def pad(text, width, align="l"):
    gap = max(0, width - dw(text))
    return str(text) + " " * gap if align == "l" else " " * gap + str(text)


def clip(text, width):
    text = str(text)
    if dw(text) <= width:
        return text
    ell = G["ellipsis"]
    if width <= dw(ell):
        return ell[:width]
    out = ""
    for ch in text:
        if dw(out) + dw(ch) > width - dw(ell):
            break
        out += ch
    return out + ell


def _bar_glyphs():
    """The filled/empty pair to draw bars with, guaranteed equal in column width.

    █ U+2588 is East Asian Ambiguous but ░ U+2591 is Neutral, so under
    --ambiguous-width=2 they are two columns and one. A mixed-width pair makes the
    bar's total length depend on its own value — a full bar twice the length of an
    empty one. Fall back to the ASCII pair rather than draw that.
    """
    full, empty = G["bar_full"], G["bar_empty"]
    if dw(full) == dw(empty):
        return full, empty
    return ASCII_GLYPHS["bar_full"], ASCII_GLYPHS["bar_empty"]


BAR_FULL, BAR_EMPTY = _bar_glyphs()
BAR_CELL = max(1, dw(BAR_FULL))


def hrule(columns, glyph=None):
    """A horizontal rule `columns` wide — repeat count is columns / glyph width.

    Same trap as bar(): ─ U+2500 is Ambiguous, so under --ambiguous-width=2 a rule of
    N characters covers 2N columns and every separator runs twice past the edge.
    """
    glyph = glyph or G["rule"]
    return glyph * max(0, columns // max(1, dw(glyph)))


def bar(frac, width):
    """A bar `width` terminal *columns* wide — not `width` characters."""
    try:
        frac = min(1.0, max(0.0, float(frac)))
    except (TypeError, ValueError):
        frac = 0.0
    cells = max(1, width // BAR_CELL)
    filled = int(round(frac * cells))
    return BAR_FULL * filled + BAR_EMPTY * (cells - filled)


def money(value, currency="usd", fx=0.0):
    if currency == "jpy" and fx > 0:
        return "¥{:,.0f}".format(value * fx)
    if 0 < value < 0.01:
        return "${:.4f}".format(value)
    return "${:,.2f}".format(value)


def tokens(count):
    count = float(count or 0)
    for unit, div in (("B", 1e9), ("M", 1e6), ("k", 1e3)):
        if count >= div:
            scaled = count / div
            return ("{:.2f}{}" if scaled < 10 else "{:.1f}{}").format(scaled, unit)
    return "{:,.0f}".format(count)


# ------------------------------------------------------------------------------ i18n
LABELS = {
    "en": dict(
        title="Token Cost Report", live="LIVE", project="project", ledger="ledger",
        updated="updated", pricing="pricing", since_watch="since watch start", elapsed="elapsed",
        summary="Summary", total_cost="Total cost", billed_tokens="Billed tokens",
        cache_share="Cache-read share", activity="Activity", effective="effective",
        per_1m="per 1M billed tokens", records="records", sessions="sessions", days="days",
        ledger_says="ledger", recomputed="recomputed at current pricing",
        phases="Cost by phase", models="Cost by model", timeline="Daily timeline",
        top_sessions="Top sessions", events="Recent events",
        phase="Phase", cost="Cost", share="Share", tokens="Tokens", model="Model",
        modelsc="Models", day="Day", session="Session", window="Window", when="When",
        hook="Hook", attributed="Attributed to", sname="Session name",
        inp="in", outp="out", cread="cache-read", cwrite="cache-write",
        cap_tokens="in / out / cache-read / cache-write columns are billed tokens (--breakdown=cost shows their cost instead)",
        cap_cost="in / out / cache-read / cache-write columns are the cost of each component (--breakdown=tokens shows token counts)",
        pending="(pending — not yet attributed)",
        unassigned="(non-pipeline work in this repo)",
        no_events="no events in the selected window",
        no_ledger="the ledger has no usage recorded yet",
        notes="Notes",
        n_attr="Per-phase figures mean \"billed while this phase was active\", not \"caused by this phase alone\".",
        n_bill="USD assumes per-token API/Console billing; under a Claude subscription these are reference-only.",
        n_src="Timeline / sessions / events are derived from token-usage.jsonl; totals come from token-usage.json.",
        n_win="Window: {w}",
        hint="Live: run with no flag   Stream: --follow   Markdown: --md   Machine-readable: --json",
        wrote="wrote",
        # TUI
        tab_phases="Phases", tab_models="Models", tab_sessions="Sessions",
        tab_days="Days", tab_events="Events",
        detail="Detail", log="Session log", transcript="Transcript",
        no_transcript="transcript not found — the session log is unavailable",
        no_selection="nothing to select in this view",
        keys="↑↓ select · ←→/Tab view · PgUp/PgDn scroll detail · r refresh · q quit",
        refreshed="checked", watching="every {s}s", all_time="all time",
        ev_running="In progress", ev_completed="Completed", ev_flushed="Pending flushed",
        components="Components", contributors="Top contributors", used_by="Used by",
        turns="turns", nearby="Log around this event", of="of",
        role_user="user", role_assistant="assistant", role_tool="tool",
        role_toolres="result", role_summary="summary", role_thinking="thinking",
        loading="loading…",
    ),
    "ja": dict(
        title="トークンコストレポート", live="ライブ", project="プロジェクト", ledger="台帳",
        updated="更新", pricing="価格表", since_watch="監視開始からの増分", elapsed="経過",
        summary="サマリー", total_cost="合計コスト", billed_tokens="課金トークン",
        cache_share="キャッシュ読取比率", activity="アクティビティ", effective="実効単価",
        per_1m="／課金トークン100万", records="レコード", sessions="セッション", days="日間",
        ledger_says="台帳値", recomputed="現行価格で再計算",
        phases="フェーズ別コスト", models="モデル別コスト", timeline="日次推移",
        top_sessions="セッション別上位", events="直近イベント",
        phase="フェーズ", cost="コスト", share="比率", tokens="トークン", model="モデル",
        modelsc="モデル", day="日付", session="セッション", window="期間", when="日時",
        hook="フック", attributed="計上先", sname="セッション名",
        inp="入力", outp="出力", cread="キャッシュ読取", cwrite="キャッシュ書込",
        cap_tokens="入力 / 出力 / キャッシュ読取 / キャッシュ書込 の各列は課金トークン数（--breakdown=cost でコスト表示）",
        cap_cost="入力 / 出力 / キャッシュ読取 / キャッシュ書込 の各列は各要素のコスト（--breakdown=tokens でトークン数表示）",
        pending="（未計上）",
        unassigned="（このリポジトリのパイプライン外作業）",
        no_events="対象期間にイベントがありません",
        no_ledger="台帳にまだ使用量が記録されていません",
        notes="注記",
        n_attr="フェーズ別の数値は「そのフェーズが実行中に課金された量」であり、そのフェーズ単独の消費量ではありません。",
        n_bill="USD 表示はトークン従量課金（API/Console）前提です。サブスクリプション利用時は参考値として扱ってください。",
        n_src="日次推移・セッション・イベントは token-usage.jsonl 由来、合計は token-usage.json 由来です。",
        n_win="対象期間: {w}",
        hint="ライブ表示: 引数なしで実行   ストリーム: --follow   Markdown 出力: --md   機械可読: --json",
        wrote="出力しました",
        # TUI
        tab_phases="フェーズ", tab_models="モデル", tab_sessions="セッション",
        tab_days="日次", tab_events="イベント",
        detail="詳細", log="セッションログ", transcript="トランスクリプト",
        no_transcript="トランスクリプトが見つからないため、ログを表示できません",
        no_selection="この表示に選択できる項目がありません",
        keys="↑↓ 選択 · ←→/Tab 表示切替 · PgUp/PgDn 詳細スクロール · r 更新 · q 終了",
        refreshed="確認", watching="{s}秒間隔", all_time="全期間",
        ev_running="実行中", ev_completed="完了", ev_flushed="保留分を計上",
        components="内訳", contributors="主な内訳", used_by="使用箇所",
        turns="ターン", nearby="このイベント前後のログ", of="/",
        role_user="ユーザー", role_assistant="アシスタント", role_tool="ツール",
        role_toolres="結果", role_summary="要約", role_thinking="思考",
        loading="読み込み中…",
    ),
}


def labels(lang):
    table = LABELS.get(lang, LABELS["en"])
    if ASCII_ONLY:
        return {k: plain(v) for k, v in table.items()}
    return table
