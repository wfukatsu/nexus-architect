#!/usr/bin/env bash
# Outcome evals: run a frozen task through the pipeline and score what it produced.
#
#   tools/eval-outcomes.sh run <task> [claude -p options...]   # paid: a full pipeline run
#   tools/eval-outcomes.sh grade <project_dir> [<task>]        # free: score an existing project
#   tools/eval-outcomes.sh list
#
# A task is a directory under evals/outcomes/<task>/ holding task.json ({"title", "input",
# "commands": [...], "expected": "expected.json"}), task.md (the brief and what the thresholds
# mean) and expected.json (the thresholds tools/lib/outcome_graders.py applies). `run` stages
# the task's input as a scratch project, stages the architect plugin the way tools/eval-plugin.sh
# does, runs each command with `claude -p` in that project, then grades it; the scorecard lands in
# evals/results/outcomes-<task>-<timestamp>/ (git-ignored) next to the scratch project's work/.
# `grade` scores a project that already ran — this toolkit's or another's on the same brief — with
# the task's thresholds when a task is named, so two runs are compared by one yardstick
# (evals/README.md § Outcome evals). A run needs a Claude credential and costs money; nothing here
# is part of CI.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TASKS="$ROOT/evals/outcomes"
GRADER="$ROOT/tools/lib/outcome_graders.py"

usage() { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }

task_field() {  # task_field <task> <key> -> value (strings) or lines (lists)
  python3 - "$TASKS/$1/task.json" "$2" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
value = data.get(sys.argv[2])
if isinstance(value, list):
    print("\n".join(value))
elif value is not None:
    print(value)
PY
}

cmd="${1:-}"; shift || true
case "$cmd" in
  list)
    for t in "$TASKS"/*/; do
      t="$(basename "$t")"; [ -f "$TASKS/$t/task.json" ] || continue
      printf '%-24s %s\n' "$t" "$(task_field "$t" title)"
    done ;;
  grade)
    project="${1:-}"; task="${2:-}"
    [ -n "$project" ] && [ -d "$project" ] || usage
    if [ -n "$task" ]; then
      [ -f "$TASKS/$task/expected.json" ] || { echo "no such task: $task" >&2; exit 2; }
      python3 "$GRADER" "$project" "expected=$TASKS/$task/expected.json"
    else
      python3 "$GRADER" "$project"
    fi ;;
  run)
    task="${1:-}"; shift || true
    [ -n "$task" ] && [ -f "$TASKS/$task/task.json" ] || usage
    input="$(task_field "$task" input)"
    [ -d "$ROOT/$input" ] || { echo "task input missing: $input" >&2; exit 2; }
    stamp="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
    OUT="$ROOT/evals/results/outcomes-$task-$stamp"
    mkdir -p "$OUT"
    PROJECT="$OUT/project"
    rsync -a --exclude reports --exclude generated --exclude work --exclude build --exclude .gradle \
      "$ROOT/$input/" "$PROJECT/"
    # The architect plugin, staged as tools/eval-plugin.sh stages it, so the commands below reach
    # `/architect:*` as an installed user's do and the installed copies stay out of the measurement.
    STAGE="$(mktemp -d "${TMPDIR:-/tmp}/nexus-outcome-plugin.XXXXXX")"
    trap 'rm -rf "$STAGE"' EXIT
    rsync -a --exclude .git --exclude knowledge --exclude samples --exclude evals \
      --exclude node_modules --exclude reports --exclude generated --exclude work "$ROOT/" "$STAGE/"
    rm -f "$STAGE/.claude-plugin/marketplace.json"
    python3 - "$ROOT/.claude-plugin/marketplace.json" "$STAGE" <<'PY'
import json, os, sys
plugins = json.load(open(sys.argv[1]))["plugins"]
entry = next(p for p in plugins if p["name"] == "architect")
stage = sys.argv[2]
mine = {os.path.normpath(s) for s in entry["skills"]}
for other in plugins:
    for skill in other["skills"]:
        if os.path.normpath(skill) not in mine:
            os.remove(os.path.join(stage, skill, "SKILL.md"))
with open(os.path.join(stage, ".claude-plugin", "plugin.json"), "w") as fh:
    json.dump({"name": entry["name"], "version": entry["version"],
               "description": entry.get("description", ""), "skills": entry["skills"]}, fh)
PY
    echo "task $task -> $PROJECT"
    started="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    while IFS= read -r command; do
      [ -n "$command" ] || continue
      echo "== claude -p '$command'"
      (cd "$PROJECT" && claude -p "$command" --plugin-dir "$STAGE" "$@") | tee -a "$OUT/transcript.txt"
    done < <(task_field "$task" commands)
    finished="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    python3 "$GRADER" "$PROJECT" "expected=$TASKS/$task/expected.json" "out=$OUT/scorecard.json" \
      | tee "$OUT/scorecard.txt" || true
    python3 - "$OUT/scorecard.json" "$task" "$started" "$finished" <<'PY'
import json, sys
card = json.load(open(sys.argv[1]))
card["task"] = sys.argv[2]; card["run_started"] = sys.argv[3]; card["run_finished"] = sys.argv[4]
json.dump(card, open(sys.argv[1], "w"), ensure_ascii=False, indent=2)
PY
    echo "scorecard: $OUT/scorecard.json" ;;
  *) usage ;;
esac
