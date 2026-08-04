"""One-shot renderer for the token-cost ledger: terminal text, Markdown, or JSON.

Invoked by tools/token-cost-report.sh; configuration arrives through NX_* environment
variables set by that script. The live two-pane dashboard lives in token_cost_tui.py.

Usage: token_cost_report.py <ledger.json> <ledger.jsonl> <model-pricing.json>
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import token_cost_data as D  # noqa: E402

LEDGER, JSONL, PRICING = sys.argv[1], sys.argv[2], sys.argv[3]
env = os.environ.get
LANG = env("NX_LANG", "en")
TOP = max(1, int(env("NX_TOP", "10") or 10))
W = int(env("NX_WIDTH", "100"))
COLOR = env("NX_COLOR", "0") == "1"
JSON_OUT = env("NX_JSON", "0") == "1"
MD_PATH = env("NX_MD", "")
SINCE = env("NX_SINCE", "all")
CUR = env("NX_CURRENCY", "usd")
FX = float(env("NX_FX", "0") or 0)
BREAKDOWN = env("NX_BREAKDOWN", "tokens")
LIVE = env("NX_LIVE", "0") == "1"
BASELINE = float(env("NX_BASELINE", "0") or 0)
WATCH_START = env("NX_WATCH_START", "")
PROJ = env("NX_PROJECT_DIR", ".")

T = D.labels(LANG)
DIM, BOLD, CYAN, GREEN, YELLOW, MAGENTA = "2", "1", "36", "32", "33", "35"


def c(code, text):
    return "\033[%sm%s\033[0m" % (code, text) if COLOR else str(text)


def money(x):
    return D.money(x, CUR, FX)


toks = D.tokens
pad, clip, dw, bar = D.pad, D.clip, D.dw, D.bar
SEP, ARROW = D.G["sep"], D.G["arrow"]

pricing = D.Pricing(PRICING)
report = D.build(LEDGER, JSONL, pricing, SINCE)
transcripts = D.Transcripts(report["ledger"], pricing)

totals = report["totals"]
total_cost, total_usage = totals["cost"], totals["usage"]
total_tokens = totals["tokens"]
sessions, days, events = report["sessions"], report["days"], report["events"]


# ------------------------------------------------------------------ JSON output
if JSON_OUT:
    print(json.dumps(dict(
        project=report["project"], ledger=LEDGER, pricing_version=report["pricing_version"],
        updated_at=report["ledger"].get("updated_at"), window=SINCE,
        totals=dict(cost_usd=round(total_cost, 4),
                    cost_usd_ledger=round(totals["ledger_cost"], 4),
                    billed_tokens=total_tokens, usage=total_usage),
        phases=[dict(name=p["name"], kind=p["kind"], cost_usd=round(p["cost"], 4),
                     billed_tokens=D.billed(p["usage"]), usage=p["usage"], models=p["models"])
                for p in report["phases"]],
        models=[dict(model=m["model"], cost_usd=round(m["cost"], 4),
                     billed_tokens=D.billed(m["usage"]), usage=m["usage"],
                     component_cost_usd={k: round(v, 4) for k, v
                                         in pricing.components(m["usage"], m["model"]).items()})
                for m in report["models"]],
        daily=[dict(day=k, cost_usd=round(v["cost"], 4), billed_tokens=v["tokens"],
                    records=v["n"]) for k, v in sorted(days.items())],
        sessions=[dict(session=k, name=transcripts.name_for(k), cost_usd=round(v["cost"], 4),
                       billed_tokens=v["tokens"], records=v["n"],
                       first=v["first"].isoformat(), last=v["last"].isoformat(),
                       models=sorted(v["models"])) for k, v in sorted(sessions.items())],
        records=report["records"],
    ), ensure_ascii=False, indent=2))
    sys.exit(0)


# --------------------------------------------------------------- text rendering
def rule(ch=None):
    return c(DIM, D.hrule(W, ch))


def head(text):
    return c(BOLD, text) + " " + c(DIM, D.hrule(max(0, W - dw(text) - 1)))


def natural_width(headers, rows):
    """Columns at their unshrunk width, plus the indent and separators."""
    widths = [max([dw(h)] + [dw(r[i]) for r in rows]) for i, h in enumerate(headers)]
    return sum(widths) + 2 * len(widths) + 2


def table(headers, rows, aligns=None, colors=None, noshrink=()):
    if not rows:
        return ["  " + c(DIM, T["no_events"])]
    aligns = aligns or ["l"] * len(headers)
    widths = [max([dw(h)] + [dw(r[i]) for r in rows]) for i, h in enumerate(headers)]
    # Shrink the widest shrinkable column until the row fits. The passes relax in turn — first
    # the shrinkable columns, then their floor, and only as a last resort the noshrink ones —
    # so a narrow terminal trims the roomiest column first. Without the later passes the loop
    # gives up while the row is still too wide and the terminal wraps it.
    for floor, protect in ((8, noshrink), (4, noshrink), (4, ())):
        while sum(widths) + 2 * len(widths) + 2 > W:
            candidates = [i for i in range(len(widths))
                          if i not in protect and widths[i] > floor]
            if not candidates:
                break
            widths[max(candidates, key=lambda i: widths[i])] -= 1
    last = len(headers) - 1

    def cell(text, i):
        # A left-aligned final column needs no padding — that only trails whitespace, and an
        # empty one (the bar columns' blank header) drops out with its separator.
        if i == last:
            if not text:
                return None
            if aligns[i] == "l":
                return clip(text, widths[i])
        return pad(clip(text, widths[i]), widths[i], aligns[i])

    def line(row, color=False):
        cells = []
        for i, text in enumerate(row):
            text = cell(text, i)
            if text is None:
                continue
            cells.append(c(colors[i], text) if color and colors and colors[i] else text)
        return "  " + "  ".join(cells)

    out = ["  " + c(DIM, line(headers)[2:])]
    for row in rows:
        out.append(line(row, color=True))
    return out


def kv(label, value, note=""):
    lw, vw = 20, 14
    if not note:  # nothing follows, so do not pad the value out to a ragged right edge
        return "  " + c(DIM, pad(label, lw)) + c(BOLD, value)
    line = "  " + c(DIM, pad(label, lw)) + c(BOLD, pad(value, vw))
    return line + "  " + c(DIM, clip(note, max(10, W - lw - vw - 4)))


out = []
title = "%s %s %s" % (report["project"] or os.path.basename(PROJ), SEP, T["title"])
if LIVE:
    stamp = "%s %s %s" % (D.G["dot"], T["live"], datetime.now().strftime("%H:%M:%S"))
    out.append(c(BOLD, title) + " " * max(1, W - dw(title) - dw(stamp)) + c(GREEN, stamp))
else:
    out.append(c(BOLD, title))
out.append(c(DIM, clip("%s: %s   %s: %s   %s: %s   %s: %s" % (
    T["project"], report["project"] or "-",
    T["ledger"], os.path.relpath(LEDGER, PROJ),
    T["updated"], report["updated_at"] or "-",
    T["pricing"], report["pricing_version"]), W)))
out.append(rule())

if total_tokens == 0:
    out.append("  " + c(YELLOW, T["no_ledger"]))
    print("\n".join(out))
    sys.exit(0)

# Summary
out.append(head(T["summary"]))
note = ""
ledger_cost = totals["ledger_cost"]
if ledger_cost and abs(ledger_cost - total_cost) / max(ledger_cost, 1e-9) > 0.01:
    note = "%s %s %s %s" % (T["ledger_says"], money(ledger_cost), SEP, T["recomputed"])
out.append(kv(T["total_cost"], money(total_cost), note))
cread = total_usage["cache_read_input_tokens"]
cwrite = total_usage["cache_creation_5m"] + total_usage["cache_creation_1h"]
components = (" %s " % SEP).join("%s %s" % pair for pair in (
    (T["inp"], toks(total_usage["input_tokens"])),
    (T["outp"], toks(total_usage["output_tokens"])),
    (T["cread"], toks(cread)),
    (T["cwrite"], toks(cwrite))))
out.append(kv(T["billed_tokens"], toks(total_tokens), components))
eff = total_cost / (total_tokens / 1e6) if total_tokens else 0.0
out.append(kv(T["cache_share"], "{:.1f}%".format(100.0 * cread / total_tokens),
              "%s %s %s" % (T["effective"], money(eff), T["per_1m"])))
span = "-"
if report["first_ts"] and report["last_ts"]:
    span = "%s %s %s (%d %s)" % (
        report["first_ts"].strftime("%Y-%m-%d"), ARROW,
        report["last_ts"].strftime("%Y-%m-%d"),
        (report["last_ts"].date() - report["first_ts"].date()).days + 1, T["days"])
out.append(kv(T["activity"], "%d %s" % (report["records"], T["records"]),
              "%d %s %s %s" % (len(sessions), T["sessions"], SEP, span)))
if LIVE:
    elapsed = ""
    if WATCH_START:
        try:
            elapsed = "%s %s" % (T["elapsed"], str(timedelta(
                seconds=int(datetime.now().timestamp() - float(WATCH_START)))))
        except ValueError:
            elapsed = ""
    out.append(kv(T["since_watch"], "+" + money(total_cost - BASELINE), elapsed))
out.append("")

bw = max(10, min(18, W // 6))

# Cost by phase
out.append(head(T["phases"]))
rows = []
for p in report["phases"]:
    frac = p["cost"] / total_cost if total_cost else 0
    label = p["name"]
    if p["kind"] == "unassigned":
        label += " " + T["unassigned"]
    elif p["kind"] == "pending":
        label = "pending " + T["pending"]
    rows.append([label, money(p["cost"]), "%s %5.1f%%" % (bar(frac, bw), 100 * frac),
                 toks(D.billed(p["usage"])), ", ".join(p["models"])])
out += table([T["phase"], T["cost"], T["share"], T["tokens"], T["modelsc"]], rows,
             ["l", "r", "l", "r", "l"], [None, BOLD, CYAN, None, DIM], noshrink=(1, 2, 3))
out.append("")

# Cost by model
out.append(head(T["models"]))


def model_rows(barw):
    built = []
    for m in report["models"][:TOP]:
        frac = m["cost"] / total_cost if total_cost else 0
        u = m["usage"]
        if BREAKDOWN == "cost":
            cc = pricing.components(u, m["model"])
            parts = [money(cc["input_tokens"]), money(cc["output_tokens"]),
                     money(cc["cache_read_input_tokens"]), money(cc["cache_write"])]
        else:
            parts = [toks(u["input_tokens"]), toks(u["output_tokens"]),
                     toks(u["cache_read_input_tokens"]),
                     toks(u["cache_creation_5m"] + u["cache_creation_1h"])]
        built.append([m["model"], money(m["cost"]),
                      "%s %5.1f%%" % (bar(frac, barw), 100 * frac),
                      toks(D.billed(u))] + parts)
    return built


m_head = [T["model"], T["cost"], T["share"], T["tokens"],
          T["inp"], T["outp"], T["cread"], T["cwrite"]]
m_align = ["l", "r", "l", "r", "r", "r", "r", "r"]
m_color = [MAGENTA, BOLD, CYAN, None, DIM, DIM, DIM, DIM]
m_noshrink = (1, 2, 3, 4, 5, 6, 7)
# The share bar is the one elastic thing here, so spend it first: try progressively shorter
# bars to keep the four component columns.
rows = model_rows(bw)
for narrower in (10, 6):
    if natural_width(m_head, rows) <= W:
        break
    rows = model_rows(narrower)
# Still over: the components are a breakdown, not the point of the table, so drop them rather
# than wrap — every column but the model name is noshrink, so the row cannot fit otherwise.
if natural_width(m_head, rows) > W:
    rows = model_rows(bw)
    m_head, m_align, m_color = m_head[:4], m_align[:4], m_color[:4]
    rows = [r[:4] for r in rows]
    m_noshrink = (1, 2, 3)
else:
    out.append("  " + c(DIM, clip(T["cap_cost"] if BREAKDOWN == "cost" else T["cap_tokens"],
                                  W - 2)))
out += table(m_head, rows, m_align, m_color, noshrink=m_noshrink)
out.append("")

# Daily timeline
if days:
    out.append(head(T["timeline"]))
    ordered = sorted(days.items())[-TOP:]
    peak = max(v["cost"] for _, v in ordered) or 1.0
    rows = [[k, money(v["cost"]), bar(v["cost"] / peak, bw), toks(v["tokens"]),
             "%d %s" % (v["n"], T["records"])] for k, v in ordered]
    out += table([T["day"], T["cost"], "", T["tokens"], ""], rows,
                 ["l", "r", "l", "r", "r"], [None, BOLD, GREEN, None, DIM],
                 noshrink=(0, 1, 2, 3))
    out.append("")

# Top sessions
if sessions:
    out.append(head(T["top_sessions"]))
    ordered = sorted(sessions.items(), key=lambda kv_: -kv_[1]["cost"])[:TOP]
    rows = [[k[:8], money(v["cost"]), toks(v["tokens"]),
             "%s %s %s" % (v["first"].strftime("%m-%d %H:%M"), ARROW,
                          v["last"].strftime("%m-%d %H:%M")),
             transcripts.name_for(k) or "-"] for k, v in ordered]
    out += table([T["session"], T["cost"], T["tokens"], T["window"], T["sname"]], rows,
                 ["l", "r", "r", "l", "l"], [YELLOW, BOLD, None, DIM, None],
                 noshrink=(0, 1, 2, 3))
    out.append("")

# Recent events
if events:
    out.append(head(T["events"]))
    rows = [[e["ts"].strftime("%m-%d %H:%M:%S"), e["hook"], e["to"], e["session"][:8],
             money(e["cost"]), toks(e["tokens"]), ", ".join(e["models"])]
            for e in events[-TOP:]]
    out += table([T["when"], T["hook"], T["attributed"], T["session"], T["cost"], T["tokens"],
                  T["modelsc"]], rows, ["l", "l", "l", "l", "r", "r", "l"],
                 [DIM, None, CYAN, YELLOW, BOLD, None, DIM], noshrink=(0, 3, 4, 5))
    out.append("")

out.append(rule())
notes = [T["n_attr"], T["n_bill"], T["n_src"]]
if D.since_cutoff(SINCE):
    notes.append(T["n_win"].format(w=SINCE))
for line in notes:
    out.append(c(DIM, clip(SEP + " " + line, W)))
if not LIVE:
    out.append(c(DIM, clip(SEP + " " + T["hint"], W)))

print("\n".join(out))


# ---------------------------------------------------------------- Markdown export
if MD_PATH:
    path = MD_PATH if os.path.isabs(MD_PATH) else os.path.join(PROJ, MD_PATH)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    md = ["---", 'title: "%s"' % T["title"], "schema_version: 1",
          'phase: "Phase 5: Estimate"', "skill: token-cost-report",
          'generated_at: "%s"' % datetime.now(timezone.utc).isoformat(timespec="seconds"),
          "input_files:", "  - work/token-usage.json", "  - work/token-usage.jsonl",
          "---", "", "# %s" % T["title"], "", "| | |", "|---|---|",
          "| %s | %s |" % (T["project"], report["project"] or "-"),
          "| %s | %s |" % (T["updated"], report["updated_at"] or "-"),
          "| %s | %s |" % (T["pricing"], report["pricing_version"]),
          "| %s | **%s** |" % (T["total_cost"], money(total_cost)),
          "| %s | %s |" % (T["billed_tokens"], "{:,}".format(total_tokens)),
          "| %s | %.1f%% |" % (T["cache_share"], 100.0 * cread / total_tokens),
          "| %s | %d %s / %d %s / %s |" % (T["activity"], report["records"], T["records"],
                                           len(sessions), T["sessions"], span),
          "", "## %s" % T["phases"], "",
          "| %s | %s | %s | %s | %s |" % (T["phase"], T["cost"], T["share"], T["tokens"],
                                          T["modelsc"]),
          "|---|---:|---:|---:|---|"]
    for p in report["phases"]:
        md.append("| %s | %s | %.1f%% | %s | %s |" % (
            p["name"], money(p["cost"]), 100 * p["cost"] / total_cost if total_cost else 0,
            "{:,}".format(D.billed(p["usage"])), ", ".join(p["models"])))
    md += ["", "## %s" % T["models"], "",
           "| %s | %s | %s | %s | %s | %s | %s | %s |" % (
               T["model"], T["cost"], T["share"], T["tokens"], T["inp"], T["outp"],
               T["cread"], T["cwrite"]),
           "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for m in report["models"]:
        u = m["usage"]
        md.append("| %s | %s | %.1f%% | %s | %s | %s | %s | %s |" % (
            m["model"], money(m["cost"]), 100 * m["cost"] / total_cost if total_cost else 0,
            "{:,}".format(D.billed(u)), "{:,}".format(u["input_tokens"]),
            "{:,}".format(u["output_tokens"]), "{:,}".format(u["cache_read_input_tokens"]),
            "{:,}".format(u["cache_creation_5m"] + u["cache_creation_1h"])))
    md.append("")
    if sessions:
        md += ["## %s" % T["top_sessions"], "",
               "| %s | %s | %s | %s | %s |" % (T["session"], T["sname"], T["cost"],
                                               T["tokens"], T["window"]),
               "|---|---|---:|---:|---|"]
        for k, v in sorted(sessions.items(), key=lambda kv_: -kv_[1]["cost"]):
            md.append("| `%s` | %s | %s | %s | %s -> %s |" % (
                k[:8], (transcripts.name_for(k) or "-").replace("|", "\\|"), money(v["cost"]),
                "{:,}".format(v["tokens"]), v["first"].strftime("%Y-%m-%d %H:%M"),
                v["last"].strftime("%Y-%m-%d %H:%M")))
        md.append("")
    if days:
        md += ["## %s" % T["timeline"], "",
               "| %s | %s | %s | %s |" % (T["day"], T["cost"], T["tokens"], T["records"]),
               "|---|---:|---:|---:|"]
        for k, v in sorted(days.items()):
            md.append("| %s | %s | %s | %d |" % (k, money(v["cost"]),
                                                 "{:,}".format(v["tokens"]), v["n"]))
        md.append("")
    md += ["## %s" % T["notes"], ""] + ["- %s" % n for n in notes] + [""]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(c(DIM, "%s: %s" % (T["wrote"], os.path.relpath(path, PROJ))))
