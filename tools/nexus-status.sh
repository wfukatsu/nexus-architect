#!/usr/bin/env bash
# Live dashboard for a nexus-architect project, in four views:
#
#   product    the product pipeline's phase tree — each phase's status
#              (pending/in_progress/completed/failed/skipped), how many of its declared
#              outputs exist, whether it is producing tokens right now, and its cost
#   architect  the architect pipeline's phase tree, the same way (product and architect
#              are separate pipelines with separate manifests, so they are separate tabs)
#   codegen    the code-generation phases of both plugins, grouped by plugin — run by
#              hand after either pipeline, and emitting code rather than reports
#   backlog    the Epic -> Sub-Epic -> Issue delivery tree with each item's status and
#              its Implemented / Reviewed / Merged stages
#
# Every view shares the action menu that generates the slash command to run next, the
# `a` key that asks Claude about the selected row, and `?` for help. Tab switches views,
# skipping the ones this project has nothing behind.
#
# Input:
#   work/pipeline-progress.json             pipeline view: the phase registry
#   skills/*/skill-dependencies.yaml        pipeline view: phase order + declared outputs
#   work/token-usage.json / .jsonl          pipeline view: per-phase cost + heartbeat
#   reports/backlog/backlog-manifest.json   backlog view: the node tree + impl.status
#   reports/backlog/followup-queue.md       backlog view: queued follow-ups
#
# Usage:
#   tools/nexus-status.sh [PROJECT_DIR] [options]
#
# Modes:
#   (default)          live dashboard on a TTY; a single render when piped,
#                      or when --json / --md / --once is given
#   --once             render the static tree once and exit, even on a TTY
#   --watch[=SEC]      live dashboard, re-checking the inputs every SEC seconds
#                      (default 10)
#
# Live dashboard keys:
#   ↑↓ / j k   select        ←→ / h l  fold / unfold      Tab  switch view
#   Enter      action menu (1-9 pick · Enter copy · e run via claude · Esc)
#   a          ask Claude about the selected row          ?  help
#   s          sync tracker labels (backlog view)         f  cycle status filter
#   o          open the item's URL / newest output        c  copy the default command
#              (c always copies — o is the key that opens)
#   PgUp/PgDn, Ctrl-U/Ctrl-D  scroll detail              g/G  detail top / bottom
#   r          refresh now                                q  quit
#   Esc        close a menu or the help panel — Esc does not quit, because a terminal
#              that emits an escape sequence ncurses cannot map delivers a bare Esc
#
# Options:
#   --view=product|architect|codegen|backlog|pipeline|auto
#                      which view to open (default auto: the detected pipeline when the
#                      project has work/pipeline-progress.json, else backlog).
#                      `pipeline` means "whichever pipeline this project runs", resolved
#                      from --plugin or from the recorded phase names
#   --plugin=product|architect     which pipeline --view=pipeline|auto resolves to
#                      (default: detected from the recorded phase names)
#   --group=core|extension|all     pipeline views: limit to the manifest phases or to
#                      the manual extension tier (default all; architect only — the
#                      product pipeline has no extension tier, and the codegen view has
#                      no tier split)
#   --phase=<name>     pipeline/codegen view: render only that phase (--once/--md/--json;
#                      the live dashboard ignores it, but still rejects an unknown name).
#                      An unknown name is a usage error in every mode
#   --epic=<id>        backlog view: limit the tree to one Epic (e.g. --epic=E1; applies
#                      to the live dashboard too). An unknown id is a usage error
#
# --group/--phase/--epic narrow --json exactly as they narrow the tree, and the emitted
# `filters` object records which were applied; `summary` always covers the whole project.
#   --sync / --no-sync backlog view: fetch live state from the tracker (GitLab Issues +
#                      group Epics via glab, GitHub Issues via gh). On by default — the
#                      manifest only moves when a skill writes it, so an unsynced tree
#                      shows what the last skill run recorded, not what the tracker says.
#                      The live dashboard refreshes in the background every
#                      NX_SYNC_EVERY seconds (default 180) and on `s`. Use --no-sync for
#                      an offline/manifest-only read
#                      (needs glab/gh on PATH and authenticated)
#   --exec             enable running commands from the dashboard: the action menu's `e`
#                      key and the `a` ask key suspend the dashboard and run `claude`
#                      in the foreground (requires claude on PATH)
#   --lang=ja|en       display language (default: options.output_language, else en)
#   --width=N          force output width (default: terminal width, clamped 60..160)
#   --color|--no-color force / disable ANSI color (default: color on a TTY)
#   --ascii            draw with ASCII glyphs (see token-cost-report.sh for when)
#   --glyphs=auto|ascii|unicode   explicit glyph set (default auto)
#   --ambiguous-width=N  columns for East Asian ambiguous chars: 1 (default) or 2
#   --debug[=PATH]     log rendering diagnostics (default PATH: work/nexus-status-debug.log)
#   --json             emit the derived states as JSON instead of the rendered tree
#   --md[=PATH]        also write the tree as Markdown (default PATH depends on the view:
#                      reports/pipeline-status.md for a pipeline view,
#                      reports/codegen-status.md for codegen,
#                      reports/backlog/backlog-status.md for the backlog)
#   -h, --help         show this help
#
# PROJECT_DIR defaults to the nearest ancestor of $PWD that holds
# work/pipeline-progress.json or reports/backlog/backlog-manifest.json.
# Exit codes: 0 ok, 1 no project / no python3, 2 bad usage (unknown option, or an
# unknown --phase / --epic). A filter that legally matches nothing renders a
# "nothing to show" line and exits 0.
#
# Contract asserted by tools/nexus-status.test.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LIB="$SCRIPT_DIR/lib"

PROJECT_DIR=""
MODE="auto"
VIEW="${NX_DEFAULT_VIEW:-auto}"
INTERVAL=10
LANG_OPT=""
COLOR="auto"
GLYPHS="auto"
AMBIGUOUS=1
DEBUG_LOG=""
JSON_OUT=0
MD_OUT=""
MD_REQUESTED=0
WIDTH=""
SYNC="${NX_SYNC:-1}"   # pre-set NX_SYNC=0 for an offline default
EXEC=0
EPIC=""
PLUGIN=""
GROUP=""
PHASE=""

usage() { awk 'NR>1 && /^#/ { sub(/^# ?/, ""); print; next } NR>1 { exit }' "$0"; }
die() { echo "nexus-status: $*" >&2; exit 1; }
usage_die() { echo "nexus-status: $*" >&2; exit 2; }

for arg in "$@"; do
  case "$arg" in
    --watch|--live)  MODE=live ;;
    --watch=*|--live=*) MODE=live; INTERVAL="${arg#*=}" ;;
    --once)          MODE=once ;;
    --view=*)        VIEW="${arg#*=}" ;;
    --plugin=*)      PLUGIN="${arg#*=}" ;;
    --group=*)       GROUP="${arg#*=}" ;;
    --phase=*)       PHASE="${arg#*=}" ;;
    --sync)          SYNC=1 ;;
    --no-sync)       SYNC=0 ;;
    --exec)          EXEC=1 ;;
    --epic=*)        EPIC="${arg#*=}" ;;
    --lang=*)        LANG_OPT="${arg#*=}" ;;
    --width=*)       WIDTH="${arg#*=}" ;;
    --no-color)      COLOR=never ;;
    --color)         COLOR=always ;;
    --ascii)         GLYPHS=ascii ;;
    --glyphs=*)      GLYPHS="${arg#*=}" ;;
    --ambiguous-width=*) AMBIGUOUS="${arg#*=}" ;;
    --debug)         DEBUG_LOG="work/nexus-status-debug.log" ;;
    --debug=*)       DEBUG_LOG="${arg#*=}" ;;
    --json)          JSON_OUT=1 ;;
    --md)            MD_REQUESTED=1 ;;
    --md=*)          MD_REQUESTED=1; MD_OUT="${arg#*=}" ;;
    -h|--help)       usage; exit 0 ;;
    -*)              echo "nexus-status: unknown option: $arg" >&2; usage >&2; exit 2 ;;
    *)               PROJECT_DIR="$arg" ;;
  esac
done

command -v python3 >/dev/null 2>&1 || die "python3 is required"
[ -f "$LIB/pipeline_status_data.py" ] || die "missing helper: $LIB/pipeline_status_data.py"

case "$VIEW" in
  product|architect|codegen|pipeline|backlog|auto) ;;
  *) usage_die "--view must be product, architect, codegen, backlog, pipeline or auto" ;;
esac
case "$PLUGIN" in ""|product|architect) ;; *) usage_die "--plugin must be product or architect" ;; esac
case "$GROUP" in ""|all|core|extension) ;; *) usage_die "--group must be core, extension or all" ;; esac

PIPELINE_MARK="work/pipeline-progress.json"
BACKLOG_MARK="reports/backlog/backlog-manifest.json"

# --- resolve the project ----------------------------------------------------------------
find_project() {
  local d="$1"
  [ -d "$d" ] || return 1
  d="$(cd "$d" && pwd)"
  while :; do
    [ -f "$d/$PIPELINE_MARK" ] && { printf '%s\n' "$d"; return 0; }
    [ -f "$d/$BACKLOG_MARK" ] && { printf '%s\n' "$d"; return 0; }
    [ "$d" = "/" ] && return 1
    d="$(dirname "$d")"
  done
}

if [ -n "$PROJECT_DIR" ]; then
  RESOLVED="$(find_project "$PROJECT_DIR" || true)"
  [ -n "$RESOLVED" ] || die "no $PIPELINE_MARK or $BACKLOG_MARK under $PROJECT_DIR"
else
  RESOLVED="$(find_project "$PWD" || true)"
  [ -n "$RESOLVED" ] || die "no nexus-architect project found.
$PIPELINE_MARK is written by /architect:init-output or /product:init-output;
$BACKLOG_MARK by /architect:export-backlog. Pass PROJECT_DIR explicitly if the
target project lives elsewhere."
fi
PROJECT_DIR="$RESOLVED"
MANIFEST="$PROJECT_DIR/$BACKLOG_MARK"
PROGRESS="$PROJECT_DIR/$PIPELINE_MARK"

if [ "$VIEW" = "auto" ]; then
  if [ -f "$PROGRESS" ]; then VIEW=pipeline; else VIEW=backlog; fi
fi
if [ "$VIEW" = "backlog" ] && [ ! -f "$MANIFEST" ]; then
  die "no $BACKLOG_MARK in $PROJECT_DIR
The manifest is written by /architect:export-backlog."
fi
# Every view but the backlog is derived from the phase manifests plus this registry.
if [ "$VIEW" != "backlog" ] && [ ! -f "$PROGRESS" ]; then
  die "no $PIPELINE_MARK in $PROJECT_DIR
The progress registry is written by /architect:init-output or /product:init-output."
fi

if [ "$MD_REQUESTED" = 1 ] && [ -z "$MD_OUT" ]; then
  case "$VIEW" in
    backlog) MD_OUT="reports/backlog/backlog-status.md" ;;
    codegen) MD_OUT="reports/codegen-status.md" ;;
    *)       MD_OUT="reports/pipeline-status.md" ;;
  esac
fi

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
case "$GLYPHS" in auto|ascii|unicode) ;; *) usage_die "--glyphs must be auto, ascii or unicode" ;; esac
case "$AMBIGUOUS" in 1|2) ;; *) usage_die "--ambiguous-width must be 1 or 2" ;; esac
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
  echo "nexus-status: debug log -> $DEBUG_LOG" >&2
fi
export NX_LANG="$LANG_OPT" NX_WIDTH="$WIDTH" NX_COLOR="$USE_COLOR" \
       NX_JSON="$JSON_OUT" NX_MD="$MD_OUT" NX_PROJECT_DIR="$PROJECT_DIR" \
       NX_INTERVAL="$INTERVAL" NX_SYNC="$SYNC" NX_EXEC="$EXEC" NX_EPIC="$EPIC" \
       NX_VIEW="$VIEW" NX_PLUGIN="$PLUGIN" NX_GROUP="$GROUP" NX_PHASE="$PHASE" \
       NX_PLUGIN_ROOT="$ROOT"

case "$MODE" in
  once)
    if [ "$VIEW" = "backlog" ]; then
      exec python3 "$LIB/backlog_status_report.py" "$MANIFEST"
    else
      exec python3 "$LIB/pipeline_status_report.py" "$PROJECT_DIR"
    fi
    ;;
  live)
    [ -t 0 ] && [ -t 1 ] || die "the live dashboard needs an interactive terminal - use --once (or --json/--md) when piping"
    exec python3 "$LIB/nexus_status_tui.py" "$PROJECT_DIR"
    ;;
esac
