#!/usr/bin/env bash
# Live dashboard for backlog delivery: the Epic -> Sub-Epic -> Issue tree with each
# item's delivery status (todo/doing/review/done/blocked) and its Implemented /
# Reviewed / Merged stages, plus an action menu that generates the slash command to
# run next (/architect:implement-backlog I1.2.3, ...).
#
# Input (written by /architect:export-backlog and advanced by the delivery skills):
#   reports/backlog/backlog-manifest.json   the node tree + impl.status / pr state
#   reports/backlog/followup-queue.md       (optional) queued follow-ups
#   reports/backlog/impl-log/, reviews/     (optional) detail-pane sources
#   work/pipeline-progress.json             (optional) pipeline phase strip
# State is derived from impl.status (and, after a sync, the live tracker labels —
# the tracker wins); a node's `labels` array is never read, it is the creation seed.
#
# Usage:
#   tools/backlog-status.sh [PROJECT_DIR] [options]
#
# Modes:
#   (default)          live dashboard on a TTY; a single render when piped,
#                      or when --json / --md / --once is given
#   --once             render the static tree once and exit, even on a TTY
#   --watch[=SEC]      live dashboard, re-checking the manifest every SEC seconds
#                      (default 10)
#
# Live dashboard keys:
#   ↑↓ / j k   select        ←→ / h l  fold / unfold
#   Enter      action menu (1-9 pick · Enter copy · e run via claude · Esc)
#   s          sync tracker labels via glab/gh      f  cycle status filter
#   o          open the item's URL                  c  copy the default command
#   PgUp/PgDn, Ctrl-U/Ctrl-D  scroll detail        g/G  detail top / bottom
#   r          refresh now                          q  quit
#
# Options:
#   --sync             fetch live status::* labels once at startup (also: s key)
#   --exec             enable the action menu's `e` key: suspend the dashboard and
#                      run `claude "<command>"` in the foreground (requires claude
#                      on PATH)
#   --epic=<id>        limit the tree to one Epic (e.g. --epic=E1)
#   --lang=ja|en       display language (default: options.output_language, else en)
#   --width=N          force output width (default: terminal width, clamped 60..160)
#   --color|--no-color force / disable ANSI color (default: color on a TTY)
#   --ascii            draw with ASCII glyphs (see token-cost-report.sh for when)
#   --glyphs=auto|ascii|unicode   explicit glyph set (default auto)
#   --ambiguous-width=N  columns for East Asian ambiguous chars: 1 (default) or 2
#   --debug[=PATH]     log rendering diagnostics (default PATH: work/backlog-status-debug.log)
#   --json             emit the derived states as JSON instead of the rendered tree
#   --md[=PATH]        also write the tree as Markdown
#                      (default PATH: reports/backlog/backlog-status.md)
#   -h, --help         show this help
#
# PROJECT_DIR defaults to the nearest ancestor of $PWD that contains
# reports/backlog/backlog-manifest.json.
# Exit codes: 0 ok, 1 no manifest / no python3, 2 bad usage.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LIB="$SCRIPT_DIR/lib"

PROJECT_DIR=""
MODE="auto"
INTERVAL=10
LANG_OPT=""
COLOR="auto"
GLYPHS="auto"
AMBIGUOUS=1
DEBUG_LOG=""
JSON_OUT=0
MD_OUT=""
WIDTH=""
SYNC=0
EXEC=0
EPIC=""

usage() { awk 'NR>1 && /^#/ { sub(/^# ?/, ""); print; next } NR>1 { exit }' "$0"; }
die() { echo "backlog-status: $*" >&2; exit 1; }

for arg in "$@"; do
  case "$arg" in
    --watch|--live)  MODE=live ;;
    --watch=*|--live=*) MODE=live; INTERVAL="${arg#*=}" ;;
    --once)          MODE=once ;;
    --sync)          SYNC=1 ;;
    --exec)          EXEC=1 ;;
    --epic=*)        EPIC="${arg#*=}" ;;
    --lang=*)        LANG_OPT="${arg#*=}" ;;
    --width=*)       WIDTH="${arg#*=}" ;;
    --no-color)      COLOR=never ;;
    --color)         COLOR=always ;;
    --ascii)         GLYPHS=ascii ;;
    --glyphs=*)      GLYPHS="${arg#*=}" ;;
    --ambiguous-width=*) AMBIGUOUS="${arg#*=}" ;;
    --debug)         DEBUG_LOG="work/backlog-status-debug.log" ;;
    --debug=*)       DEBUG_LOG="${arg#*=}" ;;
    --json)          JSON_OUT=1 ;;
    --md)            MD_OUT="reports/backlog/backlog-status.md" ;;
    --md=*)          MD_OUT="${arg#*=}" ;;
    -h|--help)       usage; exit 0 ;;
    -*)              echo "backlog-status: unknown option: $arg" >&2; usage >&2; exit 2 ;;
    *)               PROJECT_DIR="$arg" ;;
  esac
done

command -v python3 >/dev/null 2>&1 || die "python3 is required"
[ -f "$LIB/backlog_status_data.py" ] || die "missing helper: $LIB/backlog_status_data.py"

# --- resolve the project that owns the backlog ------------------------------------------
find_project() {
  local d="$1"
  [ -d "$d" ] || return 1
  d="$(cd "$d" && pwd)"
  while :; do
    [ -f "$d/reports/backlog/backlog-manifest.json" ] && { printf '%s\n' "$d"; return 0; }
    [ "$d" = "/" ] && return 1
    d="$(dirname "$d")"
  done
}

if [ -n "$PROJECT_DIR" ]; then
  RESOLVED="$(find_project "$PROJECT_DIR" || true)"
  [ -n "$RESOLVED" ] || die "no reports/backlog/backlog-manifest.json under $PROJECT_DIR"
else
  RESOLVED="$(find_project "$PWD" || true)"
  [ -n "$RESOLVED" ] || die "no reports/backlog/backlog-manifest.json found.
The manifest is written by /architect:export-backlog. Pass PROJECT_DIR explicitly if the
target project lives elsewhere."
fi
PROJECT_DIR="$RESOLVED"
MANIFEST="$PROJECT_DIR/reports/backlog/backlog-manifest.json"
PROGRESS="$PROJECT_DIR/work/pipeline-progress.json"

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
case "$GLYPHS" in auto|ascii|unicode) ;; *) die "--glyphs must be auto, ascii or unicode" ;; esac
case "$AMBIGUOUS" in 1|2) ;; *) die "--ambiguous-width must be 1 or 2" ;; esac
if [ "$EXEC" = 1 ]; then
  command -v claude >/dev/null 2>&1 || die "--exec requires the claude CLI on PATH"
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
  echo "backlog-status: debug log -> $DEBUG_LOG" >&2
fi
export NX_LANG="$LANG_OPT" NX_WIDTH="$WIDTH" NX_COLOR="$USE_COLOR" \
       NX_JSON="$JSON_OUT" NX_MD="$MD_OUT" NX_PROJECT_DIR="$PROJECT_DIR" \
       NX_INTERVAL="$INTERVAL" NX_SYNC="$SYNC" NX_EXEC="$EXEC" NX_EPIC="$EPIC"

case "$MODE" in
  once)
    exec python3 "$LIB/backlog_status_report.py" "$MANIFEST"
    ;;
  live)
    [ -t 0 ] && [ -t 1 ] || die "the live dashboard needs an interactive terminal - use --once (or --json/--md) when piping"
    exec python3 "$LIB/backlog_status_tui.py" "$MANIFEST"
    ;;
esac
