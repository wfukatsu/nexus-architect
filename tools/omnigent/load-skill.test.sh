#!/usr/bin/env bash
#
# load-skill.test.sh — self-contained tests for load-skill.sh.
# Exits non-zero on any failure. Discovers the real skill set rather than
# hardcoding counts, so it stays valid as skills are added or removed.

set -u

TEST_DIR="$(cd "$(dirname "$0")" && pwd)"
LOADER="$TEST_DIR/load-skill.sh"
ROOT="$(git -C "$TEST_DIR" rev-parse --show-toplevel 2>/dev/null || (cd "$TEST_DIR/../.." && pwd))"

PASS=0
FAIL=0

ok()   { printf 'ok   - %s\n' "$1"; PASS=$((PASS + 1)); }
nok()  { printf 'FAIL - %s\n' "$1"; FAIL=$((FAIL + 1)); }

# check <description> <expected-exit> <command...>
# Verifies the command exits with the expected status.
check_exit() {
  local desc="$1" want="$2"; shift 2
  "$@" >/dev/null 2>&1
  local got=$?
  if [ "$got" -eq "$want" ]; then ok "$desc (exit $got)"; else nok "$desc (want exit $want, got $got)"; fi
}

# assert_contains <description> <needle> <command...>
# Fails if the command exits non-zero (so an errored loader can't pass merely by
# emitting the needle on stderr) or if the needle is absent from stdout.
assert_contains() {
  local desc="$1" needle="$2"; shift 2
  local out status
  out="$("$@" 2>/dev/null)"; status=$?
  if [ "$status" -ne 0 ]; then
    nok "$desc (command exited $status, expected 0)"
  elif printf '%s' "$out" | grep -qF -- "$needle"; then
    ok "$desc"
  else
    nok "$desc (missing: $needle)"
  fi
}

# assert_not_contains <description> <needle> <command...>
# Fails if the command exits non-zero (an error with empty stdout must NOT pass) or
# if the needle IS present. For cases where a non-zero exit is the expected outcome,
# use check_exit instead.
assert_not_contains() {
  local desc="$1" needle="$2"; shift 2
  local out status
  out="$("$@" 2>/dev/null)"; status=$?
  if [ "$status" -ne 0 ]; then
    nok "$desc (command exited $status, expected 0)"
  elif printf '%s' "$out" | grep -qF -- "$needle"; then
    nok "$desc (unexpectedly found: $needle)"
  else
    ok "$desc"
  fi
}

echo "== load-skill.sh test suite =="
echo "loader: $LOADER"
echo "root:   $ROOT"
echo

# Loader must exist and be executable.
if [ -x "$LOADER" ]; then ok "loader is executable"; else nok "loader is executable"; fi

# --- Resolve one skill per plugin (DISCOVER fixtures, never hardcode names) -----
# Derive a real flat skill and a real product skill from the filesystem so these
# tests stay valid as skills are renamed/added/removed. Assert the loader resolves
# the discovered skill to its own SKILL.md ("Source file:" path) and emits the
# preamble marker — no hardcoded skill names, body text, or counts.

PREAMBLE_MARKER="OMNIGENT TRANSLATION PREAMBLE"

# Flat skill: skills/<name>/SKILL.md (architect + scalardb share this namespace).
FLAT_SKILL_FILE="$(find "$ROOT/skills" -mindepth 2 -maxdepth 2 -name SKILL.md 2>/dev/null | sort | head -1)"
if [ -n "$FLAT_SKILL_FILE" ]; then
  FLAT_NAME="$(basename "$(dirname "$FLAT_SKILL_FILE")")"
  echo "   (flat fixture: $FLAT_NAME -> $FLAT_SKILL_FILE)"

  assert_contains "architect:<flat> resolves to its SKILL.md (Source file)" "Source file: $FLAT_SKILL_FILE" \
    bash "$LOADER" "architect:$FLAT_NAME"
  assert_contains "architect:<flat> emits translation preamble" "$PREAMBLE_MARKER" \
    bash "$LOADER" "architect:$FLAT_NAME"
  # scalardb shares the flat namespace, so it resolves the same file.
  assert_contains "scalardb:<flat> resolves the same flat SKILL.md" "Source file: $FLAT_SKILL_FILE" \
    bash "$LOADER" "scalardb:$FLAT_NAME"
  # Bare name defaults to the architect/flat namespace -> same file.
  assert_contains "bare <flat> defaults to flat namespace" "Source file: $FLAT_SKILL_FILE" \
    bash "$LOADER" "$FLAT_NAME"
else
  nok "could not discover any flat skill under skills/*/SKILL.md"
fi

# Product skill: skills/product/<name>/SKILL.md (nested namespace).
PROD_SKILL_FILE="$(find "$ROOT/skills/product" -mindepth 2 -maxdepth 2 -name SKILL.md 2>/dev/null | sort | head -1)"
if [ -n "$PROD_SKILL_FILE" ]; then
  PROD_NAME="$(basename "$(dirname "$PROD_SKILL_FILE")")"
  echo "   (product fixture: $PROD_NAME -> $PROD_SKILL_FILE)"

  assert_contains "product:<name> resolves to its nested SKILL.md (Source file)" "Source file: $PROD_SKILL_FILE" \
    bash "$LOADER" "product:$PROD_NAME"
  assert_contains "product:<name> emits translation preamble" "$PREAMBLE_MARKER" \
    bash "$LOADER" "product:$PROD_NAME"
else
  nok "could not discover any product skill under skills/product/*/SKILL.md"
fi

# --- ${CLAUDE_PLUGIN_ROOT} substitution -----------------------------------
# Pick a skill that actually references the token, discovered from the tree.
TOKEN_SKILL_FILE="$(grep -rl 'CLAUDE_PLUGIN_ROOT' "$ROOT/skills" 2>/dev/null | grep '/SKILL.md$' | head -1)"
if [ -n "$TOKEN_SKILL_FILE" ]; then
  # Derive the slash name from the path (handles flat, product, and nested
  # parent/child sub-skills — derive the full relative name, not just a basename).
  rel="${TOKEN_SKILL_FILE#"$ROOT"/skills/}"
  stripped="${rel%/SKILL.md}"           # e.g. review-code, product/define-vision, migrate-oracle/<child>
  case "$stripped" in
    product/*) sname="product:${stripped#product/}" ;;
    *)         sname="architect:$stripped" ;;
  esac
  echo "   (token skill for substitution test: $sname)"
  # The expanded root must appear...
  assert_contains "\${CLAUDE_PLUGIN_ROOT} expanded to absolute root in body" "$ROOT/skills" \
    bash "$LOADER" "$sname"
  # ...and the literal token must NOT remain anywhere in the output.
  # shellcheck disable=SC2016
  assert_not_contains "no literal \${CLAUDE_PLUGIN_ROOT} token remains" '${CLAUDE_PLUGIN_ROOT}' \
    bash "$LOADER" "$sname"
else
  echo "   (no SKILL.md references CLAUDE_PLUGIN_ROOT; substitution test skipped)"
fi

# --- Missing skill --------------------------------------------------------
check_exit "missing skill returns non-zero" 1 \
  bash "$LOADER" architect:this-skill-does-not-exist
# The error names what was looked up; it goes to stderr, so capture both streams.
missing_all="$(bash "$LOADER" architect:this-skill-does-not-exist 2>&1)"
if printf '%s' "$missing_all" | grep -qF 'this-skill-does-not-exist'; then
  ok "missing skill names what was looked up"
else
  nok "missing skill names what was looked up"
fi
# The error must go to stderr specifically (not stdout).
missing_err="$(bash "$LOADER" product:nope 2>&1 >/dev/null)"
if printf '%s' "$missing_err" | grep -qF 'skill not found'; then
  ok "missing skill prints error to stderr"
else
  nok "missing skill prints error to stderr"
fi

# Unknown plugin is rejected.
check_exit "unknown plugin returns non-zero" 2 \
  bash "$LOADER" bogus:investigate

# Path-traversal components in the name are rejected (exit 2), while legit nested
# names (parent/child) remain valid — exercised by the substitution/list tests.
check_exit "name with '..' is rejected (path traversal)" 2 \
  bash "$LOADER" architect:../foo
check_exit "bare name with '..' is rejected (path traversal)" 2 \
  bash "$LOADER" ../etc/passwd

# --- --list ---------------------------------------------------------------
check_exit "--list exits 0" 0 bash "$LOADER" --list
LIST_OUT="$(bash "$LOADER" --list 2>/dev/null)"
# Entry lines are indented by two spaces; headers begin with '#', summary with 'Total:'.
LIST_COUNT="$(printf '%s\n' "$LIST_OUT" | grep -cE '^  [^ ]')"
if [ "$LIST_COUNT" -gt 0 ]; then
  ok "--list returns >0 entries ($LIST_COUNT)"
else
  nok "--list returns >0 entries (got $LIST_COUNT)"
fi
# Contract: --list enumerates every resolvable SKILL.md. Expected count is derived
# from the filesystem (no hardcoded magic number).
FS_COUNT="$(find "$ROOT/skills" -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')"
if [ "$LIST_COUNT" -eq "$FS_COUNT" ]; then
  ok "--list count matches filesystem SKILL.md count ($FS_COUNT)"
else
  nok "--list count ($LIST_COUNT) matches filesystem count ($FS_COUNT)"
fi

# --- Resolves from a non-repo-root CWD ------------------------------------
# Run from /tmp; the loader must still find the repo via its own script location.
# Use the already-DISCOVERED flat fixture (no hardcoded skill name or body text):
# resolution succeeds if the emitted "Source file:" path points at that SKILL.md.
if [ -n "${FLAT_SKILL_FILE:-}" ]; then
  NONROOT_OUT="$(cd /tmp && bash "$LOADER" "architect:$FLAT_NAME" 2>/dev/null)"
  if printf '%s' "$NONROOT_OUT" | grep -qF "Source file: $FLAT_SKILL_FILE"; then
    ok "resolves from a non-repo-root CWD (/tmp)"
  else
    nok "resolves from a non-repo-root CWD (/tmp)"
  fi
else
  nok "resolves from a non-repo-root CWD (/tmp) — no flat fixture discovered"
fi

# --- Summary --------------------------------------------------------------
echo
echo "== $PASS passed, $FAIL failed =="
[ "$FAIL" -eq 0 ]
