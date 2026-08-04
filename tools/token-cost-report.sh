#!/usr/bin/env bash
# Render a cost report from the token-usage ledger the agent writes while it runs.
#
# Input (written automatically by hooks/record_token_usage.py, never by hand):
#   work/token-usage.json    aggregated per-phase / per-model billed tokens + USD
#   work/token-usage.jsonl   append-only audit log, one record per hook firing
# Prices come from skills/common/references/model-pricing.json (single source of truth),
# so per-model costs are recomputed at current prices instead of trusted blindly.
# Sessions are named — and their logs read — from the Claude session transcripts the
# ledger points at (~/.claude/projects/<project>/<session-id>.jsonl).
#
# Usage:
#   tools/token-cost-report.sh [PROJECT_DIR] [options]
#
# Modes:
#   (default)          live two-pane dashboard on a TTY; a single render when piped,
#                      or when --json / --md / --once / --session is given
#   --live, --watch    live dashboard: upper pane selects (phases / models / sessions /
#                      days / events), lower pane shows the selection's detail — for a
#                      session, its log. Re-checks the ledger every 10s (--watch=SEC)
#   --once             render the static report once and exit, even on a TTY
#   --follow[=N]       stream ledger events as they are appended (seed with the last N, default 8)
#   --session=ID       print one session: cost, models, and its log (ID may be a prefix)
#
# Live dashboard keys:
#   ↑↓ / j k      move the selection in the upper pane
#   ←→ / Tab / 1-5 switch view      PgUp/PgDn, Ctrl-U/Ctrl-D  scroll the detail pane
#   g / G         detail top / bottom     b  toggle token/cost breakdown
#   r             refresh now              q  quit
#
# Options:
#   --top=N            rows in the per-model / session / timeline tables (default 10)
#   --breakdown=WHAT   what the per-model in/out/cache-read/cache-write columns hold:
#                      tokens (default) or cost
#   --since=SPEC       limit timeline+events: 24h, 7d, 30d, 2026-07-01, or all (default all)
#   --log-tail=N       with --session, print only the last N log entries
#   --lang=ja|en       display language (default: options.output_language, else en)
#   --currency=jpy     show money in JPY (requires --fx=RATE)
#   --fx=RATE          USD->JPY rate used by --currency=jpy
#   --width=N          force output width (default: terminal width, clamped 60..160)
#   --color|--no-color force / disable ANSI color (default: color when stdout is a TTY)
#   --ascii            draw bars, rules and separators with ASCII (# . - | ->) instead of
#                      Unicode. Use when the bars come out as garbled boxes, or when the
#                      terminal renders East Asian ambiguous-width characters double-width
#                      (common in Japanese setups) and the bars overrun their column.
#                      --glyphs=unicode forces the Unicode set back on. The default, auto,
#                      picks ASCII when stdout is not UTF-8 and when --lang=ja, since
#                      Japanese terminals commonly render ambiguous-width characters
#                      double-width and their fonts favour kana over shade blocks. Only the
#                      *drawing* glyphs change - Japanese labels stay Unicode either way
#   --ambiguous-width=N how many columns East Asian ambiguous characters occupy in your
#                      terminal: 1 (default) or 2. Set 2 if the bars and rules render fine
#                      but overrun their column - the usual Japanese terminal setting.
#                      Never guessed: no terminal reports this
#   --debug[=PATH]     log the rendering environment and any dropped curses writes
#                      (default PATH: work/token-cost-debug.log)
#   --json             emit the computed aggregate as JSON instead of the rendered report
#   --md[=PATH]        also write the report as Markdown
#                      (default PATH: reports/05_estimate/token-cost-actuals.md)
#   -h, --help         show this help
#
# PROJECT_DIR defaults to the nearest ancestor of $PWD that contains work/token-usage.json.
# Exit codes: 0 ok, 1 no ledger / no python3, 2 bad usage.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LIB="$SCRIPT_DIR/lib"
PRICING="${NEXUS_PRICING_FILE:-$ROOT/skills/common/references/model-pricing.json}"

PROJECT_DIR=""
MODE="auto"
INTERVAL=10
TAIL_N=8
TOP=10
BREAKDOWN="tokens"
LANG_OPT=""
SINCE="all"
SESSION=""
LOG_TAIL=0
CURRENCY="usd"
FX=""
COLOR="auto"
GLYPHS="auto"
AMBIGUOUS=1
DEBUG_LOG=""
JSON_OUT=0
MD_OUT=""
WIDTH=""

usage() { awk 'NR>1 && /^#/ { sub(/^# ?/, ""); print; next } NR>1 { exit }' "$0"; }
die() { echo "token-cost-report: $*" >&2; exit 1; }

for arg in "$@"; do
  case "$arg" in
    --live|--watch) MODE=live ;;
    --live=*|--watch=*) MODE=live; INTERVAL="${arg#*=}" ;;
    --follow)       MODE=follow ;;
    --follow=*)     MODE=follow; TAIL_N="${arg#*=}" ;;
    --once)         MODE=once ;;
    --session=*)    MODE=session; SESSION="${arg#*=}" ;;
    --log-tail=*)   LOG_TAIL="${arg#*=}" ;;
    --top=*)        TOP="${arg#*=}" ;;
    --breakdown=*)  BREAKDOWN="${arg#*=}" ;;
    --since=*)      SINCE="${arg#*=}" ;;
    --lang=*)       LANG_OPT="${arg#*=}" ;;
    --currency=*)   CURRENCY="$(printf '%s' "${arg#*=}" | tr '[:upper:]' '[:lower:]')" ;;
    --fx=*)         FX="${arg#*=}" ;;
    --width=*)      WIDTH="${arg#*=}" ;;
    --no-color)     COLOR=never ;;
    --color)        COLOR=always ;;
    --ascii)        GLYPHS=ascii ;;
    --glyphs=*)     GLYPHS="${arg#*=}" ;;
    --ambiguous-width=*) AMBIGUOUS="${arg#*=}" ;;
    --debug)        DEBUG_LOG="work/token-cost-debug.log" ;;
    --debug=*)      DEBUG_LOG="${arg#*=}" ;;
    --json)         JSON_OUT=1 ;;
    --md)           MD_OUT="reports/05_estimate/token-cost-actuals.md" ;;
    --md=*)         MD_OUT="${arg#*=}" ;;
    -h|--help)      usage; exit 0 ;;
    -*)             echo "token-cost-report: unknown option: $arg" >&2; usage >&2; exit 2 ;;
    *)              PROJECT_DIR="$arg" ;;
  esac
done

command -v python3 >/dev/null 2>&1 || die "python3 is required (the recorder hook needs it too)"
[ -f "$LIB/token_cost_data.py" ] || die "missing helper: $LIB/token_cost_data.py"

# --- resolve the project that owns the ledger -------------------------------------------
find_project() {
  local d="$1"
  [ -d "$d" ] || return 1
  d="$(cd "$d" && pwd)"
  while :; do
    [ -f "$d/work/token-usage.json" ] && { printf '%s\n' "$d"; return 0; }
    [ "$d" = "/" ] && return 1
    d="$(dirname "$d")"
  done
}

if [ -n "$PROJECT_DIR" ]; then
  RESOLVED="$(find_project "$PROJECT_DIR" || true)"
  [ -n "$RESOLVED" ] || die "no work/token-usage.json under $PROJECT_DIR"
else
  RESOLVED="$(find_project "$PWD" || true)"
  [ -n "$RESOLVED" ] || RESOLVED="$(find_project "$ROOT" || true)"
  [ -n "$RESOLVED" ] || die "no work/token-usage.json found.
The ledger is written by the record_token_usage.py hook and only exists after a run in a
project initialized with /architect:init-output. Pass PROJECT_DIR explicitly if it lives
elsewhere."
fi
PROJECT_DIR="$RESOLVED"
LEDGER="$PROJECT_DIR/work/token-usage.json"
JSONL="$PROJECT_DIR/work/token-usage.jsonl"
PROGRESS="$PROJECT_DIR/work/pipeline-progress.json"
[ -f "$PRICING" ] || die "pricing file not found: $PRICING"

# --- display settings -------------------------------------------------------------------
if [ -z "$LANG_OPT" ] && [ -f "$PROGRESS" ]; then
  LANG_OPT="$(python3 -c 'import json,sys
try:
    d = json.load(open(sys.argv[1]))
    print((d.get("options") or {}).get("output_language") or "")
except Exception:
    print("")' "$PROGRESS")"
fi
case "$LANG_OPT" in ja|en) ;; *) LANG_OPT="en" ;; esac

if [ -z "$WIDTH" ]; then WIDTH="$(tput cols 2>/dev/null || echo 100)"; fi
[ "$WIDTH" -ge 60 ] 2>/dev/null || WIDTH=60
[ "$WIDTH" -le 160 ] 2>/dev/null || WIDTH=160

USE_COLOR=0
case "$COLOR" in
  always) USE_COLOR=1 ;;
  never)  USE_COLOR=0 ;;
  auto)   if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then USE_COLOR=1; fi ;;
esac

[ "$INTERVAL" -ge 1 ] 2>/dev/null || INTERVAL=10
[ "$TOP" -ge 1 ] 2>/dev/null || TOP=10
case "$BREAKDOWN" in tokens|cost) ;; *) die "--breakdown must be tokens or cost" ;; esac
case "$GLYPHS" in auto|ascii|unicode) ;; *) die "--glyphs must be auto, ascii or unicode" ;; esac
case "$AMBIGUOUS" in 1|2) ;; *) die "--ambiguous-width must be 1 or 2" ;; esac
if [ "$CURRENCY" = "jpy" ] && [ -z "$FX" ]; then
  die "--currency=jpy requires --fx=RATE (e.g. --fx=155)"
fi

# The default is the live dashboard on a TTY; anything that produces a file or a stream of
# bytes for another program stays a single render.
if [ "$MODE" = "auto" ]; then
  if [ -t 1 ] && [ -t 0 ] && [ "$JSON_OUT" -eq 0 ] && [ -z "$MD_OUT" ]; then
    MODE=live
  else
    MODE=once
  fi
fi

export NX_GLYPHS="$GLYPHS" NX_AMBIGUOUS="$AMBIGUOUS"
if [ -n "$DEBUG_LOG" ]; then
  case "$DEBUG_LOG" in /*) ;; *) DEBUG_LOG="$PROJECT_DIR/$DEBUG_LOG" ;; esac
  mkdir -p "$(dirname "$DEBUG_LOG")" 2>/dev/null || true
  export NX_DEBUG_LOG="$DEBUG_LOG"
  echo "token-cost-report: debug log -> $DEBUG_LOG" >&2
fi
export NX_LANG="$LANG_OPT" NX_TOP="$TOP" NX_WIDTH="$WIDTH" NX_COLOR="$USE_COLOR" \
       NX_SINCE="$SINCE" NX_CURRENCY="$CURRENCY" NX_FX="${FX:-0}" \
       NX_JSON="$JSON_OUT" NX_PROJECT_DIR="$PROJECT_DIR" NX_BREAKDOWN="$BREAKDOWN" \
       NX_INTERVAL="$INTERVAL" NX_LEDGER="$LEDGER" NX_LOG_TAIL="$LOG_TAIL" NX_MD="$MD_OUT"

case "$MODE" in
  once)
    exec python3 "$LIB/token_cost_report.py" "$LEDGER" "$JSONL" "$PRICING"
    ;;

  live)
    [ -t 0 ] && [ -t 1 ] || die "the live dashboard needs an interactive terminal - use --once (or --json/--md) when piping"
    exec python3 "$LIB/token_cost_tui.py" "$LEDGER" "$JSONL" "$PRICING"
    ;;

  session)
    exec python3 "$LIB/token_cost_session.py" "$LEDGER" "$JSONL" "$PRICING" "$SESSION"
    ;;

  follow)
    [ -f "$JSONL" ] || die "no audit log to follow: $JSONL"
    if [ "$USE_COLOR" = 1 ]; then
      printf '\033[2mfollowing %s - Ctrl-C to stop\033[0m\n' "${JSONL#"$PROJECT_DIR"/}"
    else
      printf 'following %s - Ctrl-C to stop\n' "${JSONL#"$PROJECT_DIR"/}"
    fi
    exec tail -n "$TAIL_N" -F "$JSONL" 2>/dev/null | python3 -u "$LIB/token_cost_follow.py"
    ;;
esac
