#!/bin/bash
# Sourced by the hook scripts. claim_once <script> <tool_use_id> succeeds for exactly one caller
# per tool call.
#
# The four plugins share one source root, so each enabled plugin loads its own copy of
# hooks/hooks.json and Claude Code keeps a plugin's copy of a handler separate: with all four
# enabled, one Write runs every hook four times and the model reads the same error four times.
# The copies run in parallel; mkdir is atomic, so the first to create the marker does the work
# and the rest stand down. Anything that prevents claiming (no id, no writable temp directory)
# means "run" — a duplicate report is better than a skipped validation.
claim_once() {
  local id dir
  id=$(printf '%s' "$2" | tr -cd 'A-Za-z0-9_-')
  [ -n "$id" ] || return 0
  dir="${TMPDIR:-/tmp}/nexus-architect-hooks"
  mkdir -p "$dir" 2>/dev/null || return 0
  [ -w "$dir" ] || return 0
  mkdir "$dir/$1-$id" 2>/dev/null || return 1
  # The winner sweeps markers older than an hour; nothing reads them after their tool call.
  find "$dir" -mindepth 1 -maxdepth 1 -type d -mmin +60 -exec rmdir {} + 2>/dev/null
  return 0
}
