#!/usr/bin/env bash
# Run every executable contract in the repository.
#
# Suites are discovered, not listed: any file named *.test.py or *.test.sh under the repo is
# picked up, so adding a suite needs no edit here and none in CI. Each suite is self-contained
# (no network, no services, no fixtures beyond scratch directories it creates itself) and exits
# non-zero on failure.
#
# Not covered here: samples/scalardb-transaction-tests (a Gradle project that resolves
# dependencies over the network and runs against a real ScalarDB engine — run it directly after a
# ScalarDB version bump, see CLAUDE.md).
#
# Usage:
#   tools/run-tests.sh            run everything, print a summary
#   tools/run-tests.sh -v         stream each suite's own output too
#   tools/run-tests.sh <pattern>  run only suites whose path matches the pattern

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 2

VERBOSE=0
PATTERN=""
for arg in "$@"; do
  case "$arg" in
    -v|--verbose) VERBOSE=1 ;;
    -h|--help) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) PATTERN="$arg" ;;
  esac
done

# bash 3.2 (the macOS system shell) has no mapfile, and ${#ARR[@]} on an empty array trips
# `set -u` there — hence the read loop and the counter rather than an array length test.
SUITES=""
found=0
while IFS= read -r suite; do
  SUITES="$SUITES$suite
"
  found=$((found + 1))
done < <(find . \( -name '*.test.py' -o -name '*.test.sh' \) \
  -not -path '*/__pycache__/*' -not -path './.git/*' | sed 's|^\./||' | sort)

if [ "$found" -eq 0 ]; then
  echo "run-tests: no suites found — discovery is broken, not the repository" >&2
  exit 2
fi

passed=0
failed=0

failures=""
for suite in $SUITES; do
  case "$suite" in
    *"$PATTERN"*) ;;
    *) continue ;;
  esac
  case "$suite" in
    *.py) cmd=(python3 "$suite") ;;
    *)    cmd=(bash "$suite") ;;
  esac

  if [ "$VERBOSE" -eq 1 ]; then
    printf '\n=== %s ===\n' "$suite"
    "${cmd[@]}"
    status=$?
  else
    output=$("${cmd[@]}" 2>&1)
    status=$?
    [ $status -ne 0 ] && printf '%s\n' "$output"
  fi

  if [ $status -eq 0 ]; then
    passed=$((passed + 1))
    printf 'ok    %s\n' "$suite"
  else
    failed=$((failed + 1))
    failures="$failures $suite"
    printf 'FAIL  %s (exit %d)\n' "$suite" "$status"
  fi
done

total=$((passed + failed))
if [ "$total" -eq 0 ]; then
  echo "run-tests: pattern '$PATTERN' matched no suite" >&2
  exit 2
fi

printf '\n%d/%d suites passed\n' "$passed" "$total"
if [ "$failed" -gt 0 ]; then
  printf 'failed:%s\n' "$failures"
  exit 1
fi
