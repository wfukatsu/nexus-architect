#!/usr/bin/env bash
# Outcome evals: run a frozen task through the pipeline and score what it produced.
#
#   tools/eval-outcomes.sh run <task> [claude -p options...]   # paid: a full pipeline run
#   tools/eval-outcomes.sh grade <project_dir> [<task>]        # free: score an existing project
#   tools/eval-outcomes.sh compare <a> <b> [<task>]            # free: two runs side by side
#   tools/eval-outcomes.sh list
#
# A task is a directory under evals/outcomes/<task>/ holding task.json ({"title", "input",
# "input_sha256", "commands": [...], "expected": "expected.json"}), task.md (the brief and what
# the thresholds mean), expected.json (the thresholds tools/lib/outcome_graders.py applies) and,
# when a run exists, reference-scorecard.json. `run` stages the task's input as a scratch
# project (warning when its fingerprint is not the pinned one), stages the architect plugin the
# way tools/eval-plugin.sh does, runs each command with `claude -p` in that project, then grades
# it; the scorecard lands in evals/results/outcomes-<task>-<timestamp>/ (git-ignored) next to the
# scratch project's work/. A headless run needs `--permission-mode bypassPermissions` (or
# `--dangerously-skip-permissions`) after the task name, or it stalls on the first prompt; the
# scratch project is the only thing it writes to. `--max-budget-usd` caps each session, not the
# run: the pipeline session alone costs about USD 65 on samples/ec-monolith at list price and
# degrades its method under a lower cap, so give it USD 100 or more. The options passed are
# recorded in the scorecard as `claude_options`. `grade` scores a project that already ran —
# this toolkit's or another's on the same brief — with the task's thresholds when a task is
# named; `compare` puts two scorecards (or project directories) side by side and says which
# metrics are comparable (evals/README.md § Outcome evals). A run needs a Claude credential and
# costs money; nothing here is part of CI.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TASKS="$ROOT/evals/outcomes"
GRADER="$ROOT/tools/lib/outcome_graders.py"

usage() { sed -n '2,23p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }

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
  compare)
    a="${1:-}"; b="${2:-}"; task="${3:-}"
    [ -n "$a" ] && [ -n "$b" ] && [ -e "$a" ] && [ -e "$b" ] || usage
    if [ -n "$task" ]; then
      [ -f "$TASKS/$task/expected.json" ] || { echo "no such task: $task" >&2; exit 2; }
      python3 "$GRADER" compare "$a" "$b" "expected=$TASKS/$task/expected.json"
    else
      python3 "$GRADER" compare "$a" "$b"
    fi ;;
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
    pinned="$(task_field "$task" input_sha256)"
    actual="$(python3 "$GRADER" fingerprint "$ROOT/$input")"
    if [ -n "$pinned" ] && [ "$pinned" != "$actual" ]; then
      echo "warning: $input is not the input this task was written against (pinned ${pinned:0:12}, actual ${actual:0:12}); the thresholds may not apply" >&2
    fi
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
      # stdin from /dev/null: `claude -p` reads a non-TTY stdin into its prompt, so without it the
      # first session swallows the rest of the command list and runs every command in one session.
      (cd "$PROJECT" && claude -p "$command" --plugin-dir "$STAGE" "$@" < /dev/null) | tee -a "$OUT/transcript.txt"
    done < <(task_field "$task" commands)
    finished="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    python3 "$GRADER" "$PROJECT" "expected=$TASKS/$task/expected.json" "out=$OUT/scorecard.json" \
      | tee "$OUT/scorecard.txt" || true
    python3 - "$OUT/scorecard.json" "$task" "$started" "$finished" "$pinned" "$actual" "$*" <<'PY'
import json, sys
card = json.load(open(sys.argv[1]))
card["task"] = sys.argv[2]; card["run_started"] = sys.argv[3]; card["run_finished"] = sys.argv[4]
card["claude_options"] = sys.argv[7]  # what `claude -p` was given after the task name: the budget cap, model, permissions
card["input_sha256"] = {"pinned": sys.argv[5] or None, "actual": sys.argv[6], "matches": sys.argv[5] == sys.argv[6]}
json.dump(card, open(sys.argv[1], "w"), ensure_ascii=False, indent=2)
PY
    echo "scorecard: $OUT/scorecard.json" ;;
  *) usage ;;
esac
