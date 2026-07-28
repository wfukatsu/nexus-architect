#!/usr/bin/env bash
# Fetch / update the OKF ScalarDB-ScalarDL knowledge bundle from remote.
#
# Usage:
#   tools/update-okf-bundle.sh            # ensure: make the bundle available locally (no-op if present)
#   tools/update-okf-bundle.sh update     # pull the newest bundle from the remote
#   tools/update-okf-bundle.sh status     # show resolved path, local/remote commits, bundled versions
#
# Resolution order matches rules/okf-knowledge-bundle.md:
#   1. git submodule at knowledge/okf-scalardb-scalardl (init if empty)
#   2. shallow clone cache at ~/.cache/nexus-architect/okf-scalardb-scalardl
#
# Prints the resolved okf/ root on success; exits 1 when the bundle cannot be obtained.

set -euo pipefail

REPO_URL="https://github.com/wfukatsu/OKF-ScalarDB-ScalarDL.git"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUB_DIR="$ROOT/knowledge/okf-scalardb-scalardl"
CACHE_DIR="${OKF_CACHE_DIR:-$HOME/.cache/nexus-architect/okf-scalardb-scalardl}"
MODE="${1:-ensure}"

is_bundle() { [ -f "$1/okf/index.md" ]; }

submodule_configured() {
  git -C "$ROOT" config --file .gitmodules --get submodule.knowledge/okf-scalardb-scalardl.path >/dev/null 2>&1
}

resolve() {
  if is_bundle "$SUB_DIR"; then echo "$SUB_DIR"; return 0; fi
  if is_bundle "$CACHE_DIR"; then echo "$CACHE_DIR"; return 0; fi
  return 1
}

ensure() {
  if resolve >/dev/null; then
    echo "okf-bundle: already available at $(resolve)/okf"
    return 0
  fi
  if submodule_configured && git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
    echo "okf-bundle: initializing git submodule ..."
    if git -C "$ROOT" submodule update --init knowledge/okf-scalardb-scalardl && is_bundle "$SUB_DIR"; then
      echo "okf-bundle: available at $SUB_DIR/okf"
      return 0
    fi
    echo "okf-bundle: submodule init failed, falling back to cache clone" >&2
  fi
  echo "okf-bundle: cloning to cache $CACHE_DIR ..."
  mkdir -p "$(dirname "$CACHE_DIR")"
  git clone --depth 1 "$REPO_URL" "$CACHE_DIR"
  is_bundle "$CACHE_DIR" && echo "okf-bundle: available at $CACHE_DIR/okf"
}

update() {
  ensure >/dev/null
  local dir; dir="$(resolve)"
  if [ "$dir" = "$SUB_DIR" ] && git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
    local before after
    before="$(git -C "$dir" rev-parse --short HEAD)"
    git -C "$ROOT" submodule update --remote --init knowledge/okf-scalardb-scalardl
    after="$(git -C "$dir" rev-parse --short HEAD)"
    if [ "$before" = "$after" ]; then
      echo "okf-bundle: already up to date ($after)"
    else
      echo "okf-bundle: updated $before -> $after"
      echo "okf-bundle: note — the submodule pointer moved; commit it in the parent repo to pin the new state"
    fi
  else
    local before after
    before="$(git -C "$dir" rev-parse --short HEAD)"
    git -C "$dir" fetch --depth 1 origin main
    git -C "$dir" reset --hard origin/main --quiet
    after="$(git -C "$dir" rev-parse --short HEAD)"
    if [ "$before" = "$after" ]; then
      echo "okf-bundle: cache already up to date ($after)"
    else
      echo "okf-bundle: cache updated $before -> $after"
    fi
  fi
  echo "okf-bundle: available at $dir/okf"
}

status() {
  local dir
  if ! dir="$(resolve)"; then
    echo "okf-bundle: NOT available locally (run: tools/update-okf-bundle.sh)"
    exit 1
  fi
  echo "resolved:      $dir/okf"
  echo "local commit:  $(git -C "$dir" rev-parse --short HEAD) ($(git -C "$dir" log -1 --format=%cs))"
  echo "remote main:   $(git ls-remote "$REPO_URL" main 2>/dev/null | cut -c1-7 || echo 'unreachable')"
  echo "products:"
  for idx in "$dir"/okf/products/*/index.md; do
    local prod latest
    prod="$(basename "$(dirname "$idx")")"
    latest="$(grep -m1 '^latest_version:' "$idx" | sed "s/latest_version: *//; s/'//g")"
    echo "  $prod (latest: $latest)"
  done
}

case "$MODE" in
  ensure)  ensure ;;
  update)  update ;;
  status)  status ;;
  *) echo "usage: $0 [ensure|update|status]" >&2; exit 1 ;;
esac
