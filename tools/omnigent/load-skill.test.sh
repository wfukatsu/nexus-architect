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
assert_contains() {
  local desc="$1" needle="$2"; shift 2
  local out
  out="$("$@" 2>/dev/null)"
  if printf '%s' "$out" | grep -qF -- "$needle"; then ok "$desc"; else nok "$desc (missing: $needle)"; fi
}

# assert_not_contains <description> <needle> <command...>
assert_not_contains() {
  local desc="$1" needle="$2"; shift 2
  local out
  out="$("$@" 2>/dev/null)"
  if printf '%s' "$out" | grep -qF -- "$needle"; then nok "$desc (unexpectedly found: $needle)"; else ok "$desc"; fi
}

echo "== load-skill.sh test suite =="
echo "loader: $LOADER"
echo "root:   $ROOT"
echo

# Loader must exist and be executable.
if [ -x "$LOADER" ]; then ok "loader is executable"; else nok "loader is executable"; fi

# --- Resolve one skill per plugin (discover real names, don't assume) -----

# architect skill: investigate is a core flat skill.
assert_contains "architect:investigate resolves and emits body" "# System Investigation" \
  bash "$LOADER" architect:investigate
assert_contains "architect:investigate emits translation preamble" "OMNIGENT TRANSLATION PREAMBLE" \
  bash "$LOADER" architect:investigate

# scalardb skill: model lives flat under skills/model/SKILL.md.
assert_contains "scalardb:model resolves (flat namespace)" "OMNIGENT TRANSLATION PREAMBLE" \
  bash "$LOADER" scalardb:model
assert_contains "scalardb:model source path is skills/model/SKILL.md" "skills/model/SKILL.md" \
  bash "$LOADER" scalardb:model

# product skill: define-vision is nested under skills/product/define-vision/.
assert_contains "product:define-vision resolves (nested path)" "skills/product/define-vision/SKILL.md" \
  bash "$LOADER" product:define-vision
assert_contains "product:define-vision emits body" "OMNIGENT TRANSLATION PREAMBLE" \
  bash "$LOADER" product:define-vision

# Bare name defaults to the architect/flat namespace.
assert_contains "bare 'investigate' defaults to flat namespace" "# System Investigation" \
  bash "$LOADER" investigate

# --- ${CLAUDE_PLUGIN_ROOT} substitution -----------------------------------
# Pick a skill that actually references the token, discovered from the tree.
TOKEN_SKILL_FILE="$(grep -rl 'CLAUDE_PLUGIN_ROOT' "$ROOT/skills" 2>/dev/null | grep '/SKILL.md$' | head -1)"
if [ -n "$TOKEN_SKILL_FILE" ]; then
  # Derive the slash name from the path.
  rel="${TOKEN_SKILL_FILE#"$ROOT"/skills/}"
  case "$rel" in
    product/*/SKILL.md) sname="product:$(basename "$(dirname "$TOKEN_SKILL_FILE")")" ;;
    */SKILL.md)         sname="architect:$(basename "$(dirname "$TOKEN_SKILL_FILE")")" ;;
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
# Run from /tmp; the loader must still find the repo via the script location.
NONROOT_OUT="$(cd /tmp && bash "$LOADER" architect:investigate 2>/dev/null)"
if printf '%s' "$NONROOT_OUT" | grep -qF '# System Investigation'; then
  ok "resolves from a non-repo-root CWD (/tmp)"
else
  nok "resolves from a non-repo-root CWD (/tmp)"
fi

# --- Summary --------------------------------------------------------------
echo
echo "== $PASS passed, $FAIL failed =="
[ "$FAIL" -eq 0 ]
