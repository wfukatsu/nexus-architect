"""Non-interactive dump of one session: cost, models, and the Claude session log.

The same session view the live dashboard shows in its lower pane, for a terminal that is
not interactive (piping, in-session tool calls, saving to a file).

Usage: token_cost_session.py <ledger.json> <ledger.jsonl> <model-pricing.json> <session-prefix>
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import token_cost_data as D  # noqa: E402

LEDGER, JSONL, PRICING, WANTED = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
env = os.environ.get
LANG = env("NX_LANG", "en")
W = int(env("NX_WIDTH", "100"))
COLOR = env("NX_COLOR", "0") == "1"
CUR = env("NX_CURRENCY", "usd")
FX = float(env("NX_FX", "0") or 0)
SINCE = env("NX_SINCE", "all")
TAIL = int(env("NX_LOG_TAIL", "0") or 0)

T = D.labels(LANG)


def c(code, text):
    return "\033[%sm%s\033[0m" % (code, text) if COLOR else str(text)


def money(x):
    return D.money(x, CUR, FX)


pricing = D.Pricing(PRICING)
report = D.build(LEDGER, JSONL, pricing, SINCE)
transcripts = D.Transcripts(report["ledger"], pricing)

matches = [sid for sid in report["sessions"] if sid.startswith(WANTED)]
if not matches:
    matches = [sid for sid in report["sessions"] if WANTED in sid]
if not matches:
    print("token-cost-report: no recorded session matches %r" % WANTED, file=sys.stderr)
    print("known sessions: %s" % ", ".join(sorted(s[:8] for s in report["sessions"])),
          file=sys.stderr)
    sys.exit(1)
if len(matches) > 1:
    print("token-cost-report: %r matches %d sessions: %s"
          % (WANTED, len(matches), ", ".join(s[:8] for s in matches)), file=sys.stderr)
    sys.exit(1)

sid = matches[0]
s = report["sessions"][sid]
name = transcripts.name_for(sid) or sid
path = transcripts.path_for(sid)

print(c("1", "%s %s %s" % (name, D.G["sep"], T["log"])))
print(c("2", D.G["rule"] * W))
rows = (
    (T["session"], sid),
    (T["cost"], "%s   %s %s   %d %s" % (money(s["cost"]), D.tokens(s["tokens"]), T["tokens"],
                                        s["n"], T["records"])),
    (T["window"], "%s %s %s" % (s["first"].strftime("%Y-%m-%d %H:%M:%S"), D.G["arrow"],
                                s["last"].strftime("%Y-%m-%d %H:%M:%S"))),
    (T["modelsc"], ", ".join(sorted(s["models"]))),
    (T["attributed"], ", ".join(sorted(p for p in s["phases"] if p)) or "-"),
    (T["transcript"], path or T["no_transcript"]),
)
# Sized to the widest label, never a fixed width: ja "トランスクリプト" is 16 columns and
# would leave no gap before its value.
LW = max(D.dw(label) for label, _ in rows) + 2
for label, value in rows:
    print("  %s%s" % (c("2", D.pad(label, LW)), D.clip(value, max(20, W - LW - 2))))

if not path:
    print()
    print("  " + c("33", T["no_transcript"]))
    sys.exit(0)

log = transcripts.log_for(sid)
if TAIL:
    log = log[-TAIL:]
print()
print(c("1", "%s (%d %s)" % (T["log"], len(log), T["turns"])))
print(c("2", D.G["rule"] * W))

ROLE = {"user": (T["role_user"], "32"), "assistant": (T["role_assistant"], ""),
        "tool": (T["role_tool"], "35"), "tool-result": (T["role_toolres"], "2"),
        "summary": (T["role_summary"], "33")}

for entry in log:
    stamp = entry["ts"].strftime("%m-%d %H:%M:%S") if entry["ts"] else " " * 14
    role, color = ROLE.get(entry["kind"], (entry["kind"], ""))
    prefix = "%s  %s " % (stamp, D.pad(role, 12))
    body = D.clip(entry["text"], max(20, W - D.dw(prefix) - 22))
    tail = ""
    if entry.get("cost"):
        tail = "  %s / %s" % (money(entry["cost"]), D.tokens(entry["tokens"]))
    line = c("2", stamp) + "  " + (c(color, D.pad(role, 12)) if color else D.pad(role, 12)) \
        + " " + body + c("2", tail)
    print(line)
