#!/usr/bin/env bash
# Run the behavioural evals (evals/) against one of the four plugins.
#
#   tools/eval-plugin.sh <architect|scalardb|product|infra> [claude plugin eval options...]
#
# `claude plugin eval` loads a plugin from a directory with .claude-plugin/plugin.json. This
# repository has none: its four plugins are entries in marketplace.json that share one source
# directory and differ only in their `skills` list. Pointed at the repository, the eval loads a
# single plugin named after the directory with the skills directly under skills/ — no product or
# infra skill, and every name under the wrong prefix. Pointed at an installed plugin by name, it
# loads nothing (measured on Claude Code v2.1.294).
#
# So this stages what Claude Code builds at install time: a copy of the tree whose plugin.json
# carries the marketplace entry's name and skill list, and in which only that plugin's skills exist. The cases tagged with the plugin's name then
# run against it, and skills are invoked as `<plugin>:<skill>`, exactly as an installed user's are.
#
# A run needs a Claude credential and costs money; nothing here is part of CI.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN="${1:-}"
case "$PLUGIN" in
  architect|scalardb|product|infra) shift ;;
  *) echo "usage: $(basename "$0") <architect|scalardb|product|infra> [claude plugin eval options...]" >&2
     exit 2 ;;
esac

STAGE="$(mktemp -d "${TMPDIR:-/tmp}/nexus-eval-$PLUGIN.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT

rsync -a --exclude .git --exclude knowledge --exclude samples --exclude 'evals/results' \
  --exclude node_modules --exclude reports --exclude generated --exclude work \
  "$ROOT/" "$STAGE/"
rm -f "$STAGE/.claude-plugin/marketplace.json"
# plugin.json's `skills` adds to the default scan of skills/ rather than replacing it, so the other
# plugins' skills have to be absent, not merely unlisted. Only the SKILL.md goes: the directories
# stay, because skills read each other's reference files by path.
python3 - "$ROOT/.claude-plugin/marketplace.json" "$PLUGIN" "$STAGE" <<'PY'
import json, os, sys
plugins = json.load(open(sys.argv[1]))["plugins"]
entry = next(p for p in plugins if p["name"] == sys.argv[2])
stage = sys.argv[3]
mine = {os.path.normpath(s) for s in entry["skills"]}
for other in plugins:
    for skill in other["skills"]:
        if os.path.normpath(skill) not in mine:
            os.remove(os.path.join(stage, skill, "SKILL.md"))
with open(os.path.join(stage, ".claude-plugin", "plugin.json"), "w") as fh:
    json.dump({"name": entry["name"], "version": entry["version"],
               "description": entry.get("description", ""), "skills": entry["skills"]}, fh)
PY

OUT="$ROOT/evals/results/$PLUGIN-$(date -u +%Y-%m-%dT%H-%M-%SZ)"
claude plugin eval "$STAGE" --tag "$PLUGIN" --ablation none --trust-plugin --no-publish \
  --output-dir "$OUT" "$@"
