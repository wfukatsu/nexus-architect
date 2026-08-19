#!/usr/bin/env bash
# Fetch / update / report on an OKF knowledge bundle.
#
# Usage:
#   tools/update-okf-bundle.sh [ensure|update|status] [--bundle=scalardb|k8s-tf]
#
#   ensure   make the bundle available locally (no-op if present)   [default]
#   update   pull the newest bundle from its remote
#   status   show the resolved path and what is in it
#
# Two bundles ship with this repository and they are obtained differently:
#
#   --bundle=scalardb  (default)  ScalarDB / ScalarDL / ScalarDB Saga docs.
#                                 git submodule knowledge/okf-scalardb-scalardl, else a shallow
#                                 clone cache. Has a live remote; `update` fetches.
#                                 Resolution order: rules/okf-knowledge-bundle.md
#
#   --bundle=k8s-tf               Kubernetes / Terraform / GitOps platform docs.
#                                 VENDORED into knowledge/okf-k8s-tf — its origin repository was
#                                 deleted, so there is no remote and `update` cannot fetch.
#                                 Resolution order: rules/okf-k8s-tf-bundle.md
#                                 See knowledge/OKF-K8S-TF-PROVENANCE.md for why.
#
# Prints the resolved bundle root on success; exits 1 when the bundle cannot be obtained.

set -euo pipefail

REPO_URL="https://github.com/wfukatsu/OKF-ScalarDB-ScalarDL.git"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$ROOT}"
SUB_DIR="$ROOT/knowledge/okf-scalardb-scalardl"
CACHE_DIR="${OKF_CACHE_DIR:-$HOME/.cache/nexus-architect/okf-scalardb-scalardl}"

# k8s-tf: vendored in-repo. NEXUS_OKF_K8S_TF overrides for a project that carries its own copy;
# INFRA_DESIGN_OKF is honoured as the name the standalone infra-design plugin used.
K8S_OVERRIDE="${NEXUS_OKF_K8S_TF:-${INFRA_DESIGN_OKF:-}}"
K8S_VENDORED="$PLUGIN_ROOT/knowledge/okf-k8s-tf"
K8S_CACHE="${OKF_K8S_CACHE_DIR:-$HOME/.cache/nexus-architect/okf-k8s-tf}"

BUNDLE="scalardb"
MODE=""
for arg in "$@"; do
  case "$arg" in
    --bundle=*) BUNDLE="${arg#--bundle=}" ;;
    ensure|update|status) MODE="$arg" ;;
    *) echo "usage: $0 [ensure|update|status] [--bundle=scalardb|k8s-tf]" >&2; exit 1 ;;
  esac
done
MODE="${MODE:-ensure}"
case "$BUNDLE" in
  scalardb|k8s-tf) ;;
  *) echo "unknown bundle: $BUNDLE (expected scalardb or k8s-tf)" >&2; exit 1 ;;
esac

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

# ------------------------------------------------------------------ k8s-tf

# The k8s-tf bundle root holds index.md directly (the scalardb bundle nests one okf/ level).
is_k8s_bundle() { [ -f "$1/index.md" ] && [ -d "$1/foundation" ]; }

k8s_resolve() {
  for d in "$K8S_OVERRIDE" "$K8S_VENDORED" "$K8S_CACHE"; do
    [ -n "$d" ] && is_k8s_bundle "$d" && { printf '%s\n' "$d"; return 0; }
  done
  return 1
}

k8s_ensure() {
  local dir
  if dir="$(k8s_resolve)"; then
    echo "okf-bundle(k8s-tf): available at $dir"
    return 0
  fi
  echo "okf-bundle(k8s-tf): NOT available." >&2
  echo "  This bundle is vendored at knowledge/okf-k8s-tf and has no remote to fetch from" >&2
  echo "  (see knowledge/OKF-K8S-TF-PROVENANCE.md). Restore it from this repository, or point" >&2
  echo "  NEXUS_OKF_K8S_TF at a copy." >&2
  return 1
}

k8s_update() {
  local dir; dir="$(k8s_resolve)" || { k8s_ensure; return 1; }
  echo "okf-bundle(k8s-tf): vendored — there is no remote to update from."
  echo "  Origin repository was deleted; the copy at $dir is the source of record."
  echo "  See knowledge/OKF-K8S-TF-PROVENANCE.md."
  return 0
}

k8s_status() {
  local dir
  if ! dir="$(k8s_resolve)"; then k8s_ensure; return 1; fi
  echo "bundle:        k8s-tf (vendored — no remote)"
  echo "resolved:      $dir"
  echo "okf_version:   $(grep -m1 '^okf_version:' "$dir/index.md" | sed 's/okf_version: *//; s/"//g')"
  echo "documents:     $(find "$dir" -name '*.md' -not -path '*/.git/*' | wc -l | tr -d ' ')"
  local earliest
  earliest="$(grep -rh '^stale_after:' "$dir" | sed 's/stale_after: *//; s/"//g' | sort | head -1)"
  echo "stale_after:   earliest ${earliest:-none} (a document past its date is re-verified, not quoted as current)"
  echo "sections:"
  local idx
  for idx in "$dir"/*/index.md; do
    [ -f "$idx" ] || continue
    echo "  $(basename "$(dirname "$idx")")"
  done
}

if [ "$BUNDLE" = "k8s-tf" ]; then
  case "$MODE" in
    ensure)  k8s_ensure ;;
    update)  k8s_update ;;
    status)  k8s_status ;;
  esac
else
  case "$MODE" in
    ensure)  ensure ;;
    update)  update ;;
    status)  status ;;
  esac
fi
