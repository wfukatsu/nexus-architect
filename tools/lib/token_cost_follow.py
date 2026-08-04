"""Formatter for --follow: one line per ledger event, read from stdin as it is appended.

Fed by `tail -F work/token-usage.jsonl` in tools/token-cost-report.sh.
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import token_cost_data as D  # noqa: E402

env = os.environ.get
COLOR = env("NX_COLOR", "0") == "1"
CUR = env("NX_CURRENCY", "usd")
FX = float(env("NX_FX", "0") or 0)
LANG = env("NX_LANG", "en")
LEDGER = env("NX_LEDGER", "")
W = int(env("NX_WIDTH", "100") or 100)

T = D.labels(LANG)
transcripts = D.Transcripts(D.load_json(LEDGER, {}) or {})


def c(code, text):
    return "\033[%sm%s\033[0m" % (code, text) if COLOR else str(text)


# Fixed columns: timestamp, session id, cost, billed tokens (+ two spaces between each).
FIXED = 14 + 8 + 10 + 9 + 2 * 6
# The three text columns give up room in proportion to what they have to spare, down to a
# floor, and are dropped right-to-left once even the floors do not fit. Without this the row
# is a constant ~140 columns and every normal terminal wraps it.
PREF = [12, 20, 16, 28]   # hook, attributed_to, models, session name
FLOOR = [6, 8, 6, 8]


def elastic_widths(budget):
    if budget >= sum(PREF):
        return PREF
    keep = len(PREF)
    while keep and budget < sum(FLOOR[:keep]):
        keep -= 1
    if not keep:
        return []
    pref, floor = PREF[:keep], FLOOR[:keep]
    room = sum(pref) - sum(floor)
    spare = budget - sum(floor)
    if not room or spare >= room:
        return pref
    return [f + int(spare * (p - f) / room) for f, p in zip(floor, pref)]


running = 0.0
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        rec = json.loads(line)
    except Exception:
        continue
    by_model = rec.get("delta_by_model") or {}
    tokens = sum(D.billed(u) for u in by_model.values())
    cost = float(rec.get("delta_cost_usd") or 0.0)
    running += cost
    stamp = str(rec.get("ts", ""))[:19].replace("T", " ")
    parsed = D.parse_ts(rec.get("ts"))
    if parsed:
        stamp = parsed.strftime("%m-%d %H:%M:%S")
    sid = rec.get("session_id") or ""
    total = "%s %s" % (D.G["sigma"], D.money(running, CUR, FX))
    widths = elastic_widths(W - FIXED - D.dw(total) - 2 * 4)
    # Elastic text in PREF/FLOOR order — hook, attributed_to, models, session name — each
    # dropped once the budget no longer covers its floor.
    text = dict(zip(("hook", "attr", "models", "name"),
                    [rec.get("hook") or "", rec.get("attributed_to") or "",
                     ",".join(sorted(by_model.keys())), transcripts.name_for(sid) or "-"]))
    style = {"hook": "2", "attr": "36", "models": "35", "name": "2"}
    width = dict(zip(("hook", "attr", "models", "name"), widths))

    def col(key):
        w = width.get(key)
        return [c(style[key], D.pad(D.clip(text[key], w), w))] if w else []

    cells = ([c("2", stamp)] + col("hook") + col("attr")
             + [c("33", sid[:8]), c("1", "%10s" % D.money(cost, CUR, FX)),
                "%9s" % D.tokens(tokens)]
             + col("models") + col("name") + [c("2", total)])
    print("  ".join(cells))
    sys.stdout.flush()
