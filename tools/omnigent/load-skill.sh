#!/usr/bin/env bash
#
# load-skill.sh — Omnigent skill resolver for nexus-architect.
#
# Resolves a Claude-Code-style slash command (e.g. /architect:investigate) to
# the corresponding SKILL.md on disk, prints a short translation preamble that
# tells an Omnigent worker how to interpret Claude-specific constructs, then
# prints the full SKILL.md body with ${CLAUDE_PLUGIN_ROOT} expanded to the
# absolute repository root.
#
# Usage:
#   load-skill.sh <plugin>:<name>   # e.g. architect:investigate, scalardb:model, product:define-vision
#   load-skill.sh <name>            # plugin defaults to the architect (flat) namespace
#   load-skill.sh --list            # enumerate every skill across all three plugins
#   load-skill.sh --help            # show this usage
#
# Resolution rules (filesystem-only; does NOT read .claude-plugin/marketplace.json):
#   product:<name>    -> skills/product/<name>/SKILL.md   (product skills are nested)
#   architect:<name>  -> skills/<name>/SKILL.md           (flat namespace)
#   scalardb:<name>   -> skills/<name>/SKILL.md           (flat namespace, shares the dir)
#
# architect and scalardb share the flat skills/ directory, so both prefixes —
# and the no-prefix default — resolve flat skills identically.
#
# Exit status: 0 on success, non-zero on a missing/ambiguous skill or bad usage.

set -u

PROG="$(basename "$0")"

# --- Repository root resolution -------------------------------------------
# Robust against any CWD: prefer git, fall back to the script's own location
# (this file lives at <root>/tools/omnigent/load-skill.sh).
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "${ROOT:-}" ]; then
  ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi
SKILLS_DIR="$ROOT/skills"

usage() {
  sed -n '3,33p' "$0" | sed 's/^# \{0,1\}//'
}

err() {
  printf '%s\n' "$PROG: $*" >&2
}

# --- --list ---------------------------------------------------------------
list_skills() {
  if [ ! -d "$SKILLS_DIR" ]; then
    err "skills directory not found: $SKILLS_DIR"
    return 1
  fi

  local count=0

  echo "# nexus-architect skills (repo root: $ROOT)"
  echo
  echo "## Flat namespace — invoke as architect:<name> or scalardb:<name>"
  echo "## (architect and scalardb share skills/<name>/SKILL.md)"
  # Depth-2 SKILL.md under skills/ => skills/<name>/SKILL.md. Product skills are
  # depth 3 (skills/product/<name>/SKILL.md) and are therefore excluded here.
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    name="$(basename "$(dirname "$f")")"
    echo "  $name"
    count=$((count + 1))
  done <<EOF
$(find "$SKILLS_DIR" -mindepth 2 -maxdepth 2 -name SKILL.md 2>/dev/null | sort)
EOF

  echo
  echo "## product namespace — invoke as product:<name>"
  echo "## (nested under skills/product/<name>/SKILL.md)"
  if [ -d "$SKILLS_DIR/product" ]; then
    while IFS= read -r f; do
      [ -n "$f" ] || continue
      name="$(basename "$(dirname "$f")")"
      echo "  $name"
      count=$((count + 1))
    done <<EOF
$(find "$SKILLS_DIR/product" -mindepth 2 -maxdepth 2 -name SKILL.md 2>/dev/null | sort)
EOF
  fi

  echo
  echo "## Nested sub-skills — read by PATH, not as a slash command"
  echo "## (migration routers delegate to these; load via architect:<parent>/<child>)"
  # Depth-3 SKILL.md under skills/ => skills/<parent>/<child>/SKILL.md. These are
  # the migration router sub-skills. Product skills are also depth 3 but are
  # already listed above as a first-class namespace, so exclude skills/product/*.
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    # Exclude product skills with a fixed-string (glob) match — $SKILLS_DIR may
    # contain regex metacharacters, so avoid a regex filter like grep -v.
    [[ "$f" == "$SKILLS_DIR/product/"* ]] && continue
    rel="${f#"$SKILLS_DIR"/}"          # e.g. migrate-oracle/migrate-oracle-to-scalardb/SKILL.md
    echo "  ${rel%/SKILL.md}"
    count=$((count + 1))
  done <<EOF
$(find "$SKILLS_DIR" -mindepth 3 -maxdepth 3 -name SKILL.md 2>/dev/null | sort)
EOF

  echo
  echo "Total: $count skills"

  [ "$count" -gt 0 ]
}

# --- Translation preamble -------------------------------------------------
print_preamble() {
  local plugin="$1" name="$2" path="$3"
  cat <<EOF
===== OMNIGENT TRANSLATION PREAMBLE =====
You are running the nexus-architect skill: ${plugin}:${name}
Source file: ${path}
CLAUDE_PLUGIN_ROOT == ${ROOT}  (already expanded in the body below)

This SKILL.md was authored for Claude Code. Interpret its Claude-specific
constructs as follows under Omnigent:

Tool mapping:
  Read                -> sys_os_read
  Write               -> sys_os_write
  Edit / MultiEdit    -> sys_os_edit
  Bash / Grep / Glob  -> sys_os_shell (use rg/find/grep/sed within the shell)

Path mapping:
  Repository root is ${ROOT}. Resolve CLAUDE_PLUGIN_ROOT, @rules/, @templates/,
  @skills/ and other repo-relative paths against this absolute root; do NOT assume
  your CWD equals it. (CLAUDE_PLUGIN_ROOT placeholders are already expanded in the
  body below.)

Task(...) blocks:
  DEFAULT: run each Task prompt body SEQUENTIALLY in this worker and have the
  orchestrator aggregate the results. (sys_call_async dispatches a registered
  local Python tool, NOT an agent/sub-agent session — do not use it for this.)
  Genuine PARALLEL sub-agent execution is an orchestrator capability via the
  session/sub-agent dispatch API (e.g. sys_session_send), not available to a
  plain worker. Either way the orchestrator computes any composite scores after
  all results are collected.

AskUserQuestion / interactive choices:
  Hand off to the orchestrator<->human gate: present the numbered choices,
  pause, and resume when the human replies. Under --auto / profile runs,
  interactivity is bypassed (pick the documented default and continue).

Hooks (NOT auto-fired under Omnigent):
  After writing any report .md, run BOTH validation hooks as an explicit gate:
    bash ${ROOT}/hooks/validate-frontmatter.sh <file.md>
    bash ${ROOT}/hooks/validate-mermaid.sh <file.md>
  A non-zero exit means the file is invalid — fix it before continuing.

model: frontmatter:
  Ignored under a single session model, OR map the tier (opus/sonnet/haiku) to
  a per-dispatch model when the orchestrator supports it.

Pipeline sequencing:
  Read skills/common/skill-dependencies.yaml for the architect DAG (or
  skills/product/common/skill-dependencies.yaml for the product pipeline) and track
  progress in work/pipeline-progress.json (plain data, not a Claude construct).
===== END PREAMBLE — SKILL BODY FOLLOWS =====

EOF
}

# --- Argument handling ----------------------------------------------------
if [ "$#" -ne 1 ]; then
  usage
  exit 2
fi

case "$1" in
  --help|-h)
    usage
    exit 0
    ;;
  --list|-l)
    list_skills
    exit $?
    ;;
  -*)
    err "unknown option: $1"
    usage
    exit 2
    ;;
esac

# Parse <plugin>:<name> or bare <name> (defaults to architect namespace).
arg="$1"
case "$arg" in
  *:*)
    plugin="${arg%%:*}"
    name="${arg#*:}"
    ;;
  *)
    plugin="architect"
    name="$arg"
    ;;
esac

if [ -z "$plugin" ] || [ -z "$name" ]; then
  err "could not parse '$arg' as <plugin>:<name> or <name>"
  exit 2
fi

# Reject path-traversal components in the skill name (e.g. architect:../foo).
# Legit nested names like migrate-oracle/migrate-oracle-to-scalardb are unaffected.
IFS='/' read -ra _name_parts <<< "$name"
for _part in "${_name_parts[@]}"; do
  if [ "$_part" = "." ] || [ "$_part" = ".." ]; then
    err "invalid skill name '$name': path components '.' and '..' are not allowed"
    exit 2
  fi
done

case "$plugin" in
  product)
    skill_path="$SKILLS_DIR/product/$name/SKILL.md"
    ;;
  architect|scalardb)
    skill_path="$SKILLS_DIR/$name/SKILL.md"
    ;;
  *)
    err "unknown plugin '$plugin' (expected: architect, scalardb, or product)"
    exit 2
    ;;
esac

if [ ! -f "$skill_path" ]; then
  err "skill not found: ${plugin}:${name}"
  err "  looked up: $skill_path"
  err "  run '$PROG --list' to see available skills"
  exit 1
fi

# --- Emit preamble + body with \${CLAUDE_PLUGIN_ROOT} expanded ------------
print_preamble "$plugin" "$name" "$skill_path"

# Literal token to find — single quotes are intentional (no expansion here).
# shellcheck disable=SC2016
token='${CLAUDE_PLUGIN_ROOT}'
body="$(cat "$skill_path")"

# Replace the token literally. On bash 5.2+ with patsub_replacement enabled, a '&'
# in the replacement ($ROOT) would be taken as "the matched text"; disable it around
# the substitution so the replacement is always literal, then restore prior state.
# (Trailing-newline normalization from $(cat ...) is acceptable and left as-is.)
_patsub_was_on=""
if shopt -q patsub_replacement 2>/dev/null; then
  _patsub_was_on="yes"
  shopt -u patsub_replacement
fi
printf '%s\n' "${body//"$token"/$ROOT}"
_emit_status=$?
# Always restore the prior option state, then exit with printf's status so a write
# failure (e.g. broken pipe) is not masked by the restore command's own exit code.
if [ -n "$_patsub_was_on" ]; then shopt -s patsub_replacement; fi
exit "$_emit_status"
