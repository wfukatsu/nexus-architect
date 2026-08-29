#!/usr/bin/env bash
# Serve a nexus-architect project's reports/ as a local documentation site, using Blume
# (https://useblume.dev — Markdown-first docs framework on Astro; Node >= 22.12).
#
# The site is a stage, not a source: tools/docs-site/sync_reports.py converts reports/**
# into tools/docs-site/docs/ (MDX so Mermaid renders), copies OpenAPI/AsyncAPI specs into
# Blume's API reference, serves the consolidated HTML report as-is, and builds a landing
# page from work/pipeline-progress.json. reports/ itself is never modified.
#
# Usage:
#   tools/docs-site.sh <command> [PROJECT_DIR] [options]
#
# Commands:
#   dev        sync, then start the dev server with hot reload (default)
#   sync       stage reports/ into the site and exit
#   build      sync, then build the static site into tools/docs-site/dist/
#   preview    serve the last build
#   validate   sync, then check every internal link in the staged site
#   clean      remove the generated stage (docs/, public/, specs/, .blume/, dist/)
#
# Options:
#   --port=N        dev/preview port (Blume's default when omitted)
#   --host          expose the dev server on the LAN
#   --open          open the browser once the dev server is up
#   --no-watch      dev: do not re-sync when reports/ changes
#   --no-install    never run npm install (fail instead if node_modules/ is missing)
#
# PROJECT_DIR defaults to the current directory when it contains reports/, otherwise to
# the repository root. Exit 0 on success, 1 on a failed sync/build, 2 on usage.
set -euo pipefail

SITE="$(cd "$(dirname "${BASH_SOURCE[0]}")/docs-site" && pwd)"
REPO="$(cd "$SITE/../.." && pwd)"

cmd="dev"
project=""
port="" host="" open="" watch=1 install=1
for arg in "$@"; do
  case "$arg" in
    dev|sync|build|preview|validate|clean) cmd="$arg" ;;
    --port=*) port="${arg#--port=}" ;;
    --host) host=1 ;;
    --open) open=1 ;;
    --no-watch) watch=0 ;;
    --no-install) install=0 ;;
    -h|--help) sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "docs-site: unknown option $arg" >&2; exit 2 ;;
    *) project="$arg" ;;
  esac
done

if [[ -z "$project" ]]; then
  if [[ -d "$PWD/reports" ]]; then project="$PWD"; else project="$REPO"; fi
fi
project="$(cd "$project" && pwd)"

if [[ "$cmd" == "clean" ]]; then
  rm -rf "$SITE/docs" "$SITE/public" "$SITE/specs" "$SITE/.blume" "$SITE/.blume-verify" "$SITE/dist"
  echo "docs-site: cleaned $SITE"
  exit 0
fi

# --- toolchain -----------------------------------------------------------------
if ! command -v node >/dev/null; then
  echo "docs-site: node is required (>= 22.12); see https://nodejs.org" >&2; exit 1
fi
node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(a>22||(a===22&&b>=12)?0:1)' \
  || { echo "docs-site: Blume needs Node >= 22.12, found $(node --version)" >&2; exit 1; }
if [[ ! -d "$SITE/node_modules/blume" ]]; then
  if (( install )); then
    echo "docs-site: installing Blume into $SITE (first run only)"
    (cd "$SITE" && npm install --no-audit --no-fund)
  else
    echo "docs-site: $SITE/node_modules is missing and --no-install was given" >&2; exit 1
  fi
fi

# --- stage ---------------------------------------------------------------------
if [[ "$cmd" != "preview" ]]; then
  python3 "$SITE/sync_reports.py" "$project"
fi

dev_args=()
[[ -n "$port" ]] && dev_args+=(--port "$port")
[[ -n "$host" ]] && dev_args+=(--host)
[[ -n "$open" ]] && dev_args+=(--open)

cd "$SITE"
case "$cmd" in
  sync) ;;
  dev)
    if (( watch )); then
      python3 "$SITE/sync_reports.py" "$project" --watch >/dev/null 2>&1 &
      watcher=$!
      trap 'kill "$watcher" 2>/dev/null || true' EXIT
    fi
    echo "docs-site: serving $project/reports — Ctrl-C to stop"
    exec npx blume dev "${dev_args[@]}"
    ;;
  build) npx blume build ;;
  preview) exec npx blume preview "${dev_args[@]}" ;;
  validate) npx blume validate ;;
esac
