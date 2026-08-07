#!/usr/bin/env bash
# Executable check of the nexus-status CLI contract — the layer above the two data
# modules, which pipeline_status_data.test.py / backlog_status_data.test.py already pin.
#
# What this asserts, against scratch projects it builds itself:
#   - project resolution and exit codes: 0 ok, 1 no project / missing input, 2 bad usage
#   - view selection: --view=auto picks pipeline when a registry exists, else backlog
#   - every output mode renders: default --once text, --json (parseable), --md (with the
#     frontmatter the write hooks require), --ascii, --lang=ja
#   - the filters narrow every mode alike: --group / --phase / --epic apply to --json,
#     not just to the tree, and each render states what it filtered
#   - a render filtered down to nothing says so instead of printing a bare header
#   - a misspelled --phase / --epic is a usage error (2), not a silent empty tree
#   - the backlog view's pipeline strip agrees with the pipeline view's own count
#   - the live-refresh poll notices an *overwritten* file three levels down
#
# Usage: tools/nexus-status.test.sh
# Exit status 0 = all checks pass, 1 = at least one failed.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NX="$ROOT/tools/nexus-status.sh"
BL="$ROOT/tools/backlog-status.sh"
export NX_TEST_ROOT="$ROOT"
FAILURES=0
WORK="$(mktemp -d "${TMPDIR:-/tmp}/nx-status-cli.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

# The launcher reads the terminal for width and color; pin both so output compares.
COMMON=(--width=100 --no-color)

check() {  # check <name> <status> [detail]
  if [ "$2" -eq 0 ]; then
    printf '  [ok] %s\n' "$1"
  else
    printf '  [FAIL] %s%s\n' "$1" "${3:+ — $3}"
    FAILURES=$((FAILURES + 1))
  fi
}

contains() { grep -Fq -- "$2" <<<"$1"; }

exit_code() {  # exit_code <expected> <cmd...>
  local want="$1"; shift
  "$@" >/dev/null 2>&1
  local got=$?
  [ "$got" -eq "$want" ] || { printf 'exited %d, wanted %d\n' "$got" "$want" >&2; }
  [ "$got" -eq "$want" ]
}

# --------------------------------------------------------------------------- fixtures
# A product project mid-pipeline: vision done, scope running, one phase the manifest does
# not know, and a stale phase (success-metrics finished before vision was rewritten).
make_product() {
  local p="$WORK/product"
  mkdir -p "$p/work" "$p/reports/00_core" "$p/reports/backlog"
  cat > "$p/work/pipeline-progress.json" <<'JSON'
{ "project_name": "prod-fx", "updated_at": "2026-08-07T00:00:00Z",
  "options": { "output_language": "ja" },
  "gates": { "validate-assumptions": { "verdict": "conditional-go",
                                       "open_assumptions": ["A1", "A2"] } },
  "phases": {
    "define-vision": { "status": "completed" },
    "define-success-metrics": { "status": "completed" },
    "define-scope": { "status": "in_progress" },
    "hand-written-phase": { "status": "failed" }
  },
  "errors": [], "warnings": [] }
JSON
  for f in vision-mission-value pr-faq success-metrics constraints; do
    printf 'x\n' > "$p/reports/00_core/$f.md"
  done
  # success-metrics finished, then vision was rewritten -> success-metrics is stale
  touch -t 202608060000 "$p/reports/00_core/success-metrics.md"
  cat > "$p/reports/backlog/backlog-manifest.json" <<'JSON'
{ "platform": "github", "project": "o/r", "nodes": [
  { "local_id": "E1", "level": "epic", "title": "Epic one" },
  { "local_id": "I1.1", "level": "issue", "parent_local_id": "E1", "title": "A",
    "impl": { "status": "done" }, "remote": { "iid": 1, "url": "https://x/1" } },
  { "local_id": "I1.2", "level": "issue", "parent_local_id": "E1", "title": "B",
    "impl": { "status": "doing" } },
  { "local_id": "E2", "level": "epic", "title": "Epic two" },
  { "local_id": "I2.1", "level": "issue", "parent_local_id": "E2", "title": "C" } ] }
JSON
  printf '%s\n' "$p"
}

# An architect project whose only outputs sit three levels down, and no backlog at all.
make_architect() {
  local p="$WORK/architect"
  mkdir -p "$p/work" "$p/reports/before/arch-fx"
  cat > "$p/work/pipeline-progress.json" <<'JSON'
{ "project_name": "arch-fx", "options": {},
  "phases": { "investigate": { "status": "completed" } } }
JSON
  for f in technology-stack codebase-structure issues-and-debt ddd-readiness; do
    printf 'x\n' > "$p/reports/before/arch-fx/$f.md"
  done
  printf '%s\n' "$p"
}

# A backlog-only project: no registry, so --view=auto has to land on the backlog.
make_backlog_only() {
  local p="$WORK/backlog-only"
  mkdir -p "$p/reports/backlog"
  cat > "$p/reports/backlog/backlog-manifest.json" <<'JSON'
{ "platform": "gitlab", "project": "g/p", "nodes": [
  { "local_id": "E1", "level": "epic", "title": "Only epic" },
  { "local_id": "I1.1", "level": "issue", "parent_local_id": "E1", "title": "A" } ] }
JSON
  printf '%s\n' "$p"
}

PROD="$(make_product)"
ARCH="$(make_architect)"
BLONLY="$(make_backlog_only)"

# ------------------------------------------------------------------- resolution & codes
echo "project resolution and exit codes"
exit_code 1 "$NX" "$WORK/does-not-exist" --once
check "missing PROJECT_DIR exits 1" "$?"
(cd / && exit_code 1 "$NX" --once)
check "no project above \$PWD exits 1" "$?"
exit_code 2 "$NX" "$PROD" --once --bogus
check "unknown option exits 2" "$?"
for bad in --view=zzz --plugin=zzz --group=zzz --glyphs=zzz --ambiguous-width=3; do
  exit_code 2 "$NX" "$PROD" --once "$bad"
  check "invalid $bad exits 2" "$?"
done
exit_code 1 "$NX" "$ARCH" --once --view=backlog
check "backlog view without a manifest exits 1" "$?"
exit_code 0 "$NX" "$PROD" --once
check "a healthy project exits 0" "$?"
exit_code 0 "$NX" "$PROD/reports/00_core" --once
check "PROJECT_DIR resolves from a subdirectory" "$?"

# ------------------------------------------------------------------------ view selection
echo "view selection"
out="$("$NX" "$PROD" --once "${COMMON[@]}" --lang=en)"
contains "$out" "Product Pipeline"
check "--view=auto picks the detected pipeline when a registry exists" "$?" "$out"
out="$("$NX" "$ARCH" --once "${COMMON[@]}" --lang=en)"
contains "$out" "Architect Pipeline"
check "--view=auto follows the detection, not a fixed plugin" "$?" "$out"
out="$("$NX" "$BLONLY" --once "${COMMON[@]}" --lang=en)"
contains "$out" "Backlog Delivery"
check "--view=auto falls back to the backlog with no registry" "$?" "$out"
out="$("$BL" "$PROD" --once "${COMMON[@]}" --lang=en)"
contains "$out" "Backlog Delivery"
check "backlog-status.sh alias opens the backlog view" "$?" "$out"

# product and architect are separate pipelines, so each is addressable on its own and
# neither shows the other's phases.
out="$("$NX" "$PROD" --once "${COMMON[@]}" --view=architect --lang=en)"
contains "$out" "Architect Pipeline" && contains "$out" "investigate" \
  && ! contains "$out" "define-vision"
check "--view=architect renders the architect tree in a product project" "$?" "$out"
out="$("$NX" "$PROD" --once "${COMMON[@]}" --view=product --lang=en)"
contains "$out" "define-vision" && ! contains "$out" "review-synthesizer"
check "--view=product renders only the product tree" "$?" "$out"

# code generation is its own view: not in either pipeline tree, and grouped by plugin.
out="$("$NX" "$PROD" --once "${COMMON[@]}" --view=product --lang=en)"
! contains "$out" "generate-frontend"
check "the product pipeline view drops its codegen phase" "$?" "$out"
out="$("$NX" "$ARCH" --once "${COMMON[@]}" --view=architect --lang=en)"
! contains "$out" "generate-infra-code" && contains "$out" "generate-test-specs"
check "the architect pipeline view drops codegen but keeps the spec phases" "$?" "$out"
out="$("$NX" "$PROD" --once "${COMMON[@]}" --view=codegen --lang=en)"
contains "$out" "Code Generation" && contains "$out" "generate-frontend" \
  && ! contains "$out" "define-vision"
check "--view=codegen renders only the code-generation phases" "$?" "$out"
out="$("$NX" "$PROD" --once "${COMMON[@]}" --view=codegen --lang=en --json)"
python3 - "$out" <<'PY'
import json, sys
d = json.loads(sys.argv[1])
names = {p["name"]: p for p in d["phases"]}
ok = (d["view"] == "codegen" and d["section"] == "codegen"
      and names["generate-frontend"]["command"] == "/product:generate-frontend"
      and names["generate-frontend"]["group"] == "product"
      and all(p["section"] == "codegen" for p in d["phases"]))
sys.exit(0 if ok else 1)
PY
check "--json says it is the codegen view and each phase keeps its own plugin" "$?" "$out"

# -------------------------------------------------------------------------- output modes
echo "output modes"
out="$("$NX" "$PROD" --once "${COMMON[@]}" --lang=en)"
contains "$out" "define-scope" && contains "$out" "in_progress" \
  && contains "$out" "stale" && contains "$out" "gate: conditional-go" \
  && contains "$out" "hand-written-phase"
check "one-shot text carries status, staleness, the gate and unmanifested phases" "$?" \
  "$out"
out="$("$NX" "$PROD" --once "${COMMON[@]}" --lang=ja)"
contains "$out" "プロダクトパイプライン" && contains "$out" "ゲート"
check "--lang=ja localizes the pipeline view" "$?" "$out"
out="$("$NX" "$PROD" --once "${COMMON[@]}" --view=codegen --lang=ja)"
contains "$out" "コード生成" && contains "$out" "プロダクト (フロントエンド)"
check "--lang=ja localizes the codegen view and its plugin groups" "$?" "$out"
out="$("$NX" "$PROD" --once "${COMMON[@]}" --view=backlog --lang=ja)"
contains "$out" "Issue 1/3 完了" && ! contains "$out" "Issues 1/3 done"
check "--lang=ja localizes the backlog header too" "$?" "$out"
out="$("$NX" "$PROD" --once "${COMMON[@]}" --ascii --lang=en)"
residue="$(tr -d '\11\12\40-\176' <<<"$out")"
[ -z "$residue" ]
check "--ascii --lang=en emits no non-ASCII byte" "$?" "$(od -c <<<"$residue" | head -2)"
"$NX" "$PROD" --json | python3 -c 'import json,sys; json.load(sys.stdin)' 2>/dev/null
check "--json parses" "$?"
"$NX" "$PROD" --json --view=backlog | python3 -c 'import json,sys; json.load(sys.stdin)' \
  2>/dev/null
check "--json parses in the backlog view" "$?"
"$NX" "$PROD" --md >/dev/null 2>&1
head -1 "$PROD/reports/pipeline-status.md" 2>/dev/null | grep -q '^---$'
check "--md writes a file that opens with frontmatter" "$?"
grep -q "^schema_version: 1$" "$PROD/reports/pipeline-status.md" 2>/dev/null
check "--md frontmatter carries schema_version" "$?"
"$NX" "$PROD" --md --view=backlog >/dev/null 2>&1
head -1 "$PROD/reports/backlog/backlog-status.md" 2>/dev/null | grep -q '^---$'
check "--md writes the backlog report too" "$?"

# ------------------------------------------------------------------------------ filters
echo "filters apply to every mode"
count_phases() { python3 -c 'import json,sys; print(len(json.load(sys.stdin)["phases"]))'; }
n_all="$("$NX" "$ARCH" --json | count_phases)"
n_ext="$("$NX" "$ARCH" --json --group=extension | count_phases)"
[ "${n_ext:-0}" -gt 0 ] && [ "${n_ext:-0}" -lt "${n_all:-0}" ]
check "--group narrows --json (all=$n_all extension=$n_ext)" "$?"
"$NX" "$ARCH" --json --group=extension | python3 -c '
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if all(p["group"] == "extension" for p in d["phases"])
         and d["filters"]["group"] == "extension" else 1)'
check "--group=extension yields only extension phases, and says so in filters" "$?"
one="$("$NX" "$ARCH" --json --phase=analyze | python3 -c '
import json, sys
d = json.load(sys.stdin)
print("%d:%s" % (len(d["phases"]), d["phases"][0]["name"] if d["phases"] else "-"))')"
[ "$one" = "1:analyze" ]
check "--phase narrows --json to that phase" "$?" "$one"
out="$("$NX" "$PROD" --once "${COMMON[@]}" --phase=define-scope --lang=en)"
contains "$out" "define-scope" && ! contains "$out" "define-vision" \
  && ! contains "$out" "hand-written-phase"
check "--phase narrows the tree and its per-phase footers" "$?" "$out"
epic="$("$NX" "$PROD" --json --view=backlog --epic=E2 | python3 -c '
import json, sys
d = json.load(sys.stdin)
print("%s:%s" % (",".join(n["local_id"] for n in d["nodes"]), d["filters"]["epic"]))')"
[ "$epic" = "E2,I2.1:E2" ]
check "--epic narrows --json to that Epic's subtree" "$?" "$epic"

# ----------------------------------------------------------------------- empty & unknown
echo "empty results and unknown filters"
out="$("$NX" "$PROD" --once "${COMMON[@]}" --group=extension --lang=en)"
contains "$out" "nothing to show" && contains "$out" "no manual extension tier"
check "an empty render explains itself instead of printing a bare header" "$?" "$out"
err="$("$NX" "$PROD" --once --lang=en --phase=nope 2>&1 >/dev/null)"; code=$?
{ [ "$code" -eq 2 ] && contains "$err" "unknown phase: nope" \
    && contains "$err" "define-scope"; }
check "a misspelled --phase is a usage error (2) that lists the real phases" "$?" \
  "code=$code $err"
err="$("$NX" "$PROD" --once --lang=en --view=backlog --epic=NOPE 2>&1 >/dev/null)"
code=$?
{ [ "$code" -eq 2 ] && contains "$err" "unknown epic: NOPE" \
    && contains "$err" "E1, E2"; }
check "a misspelled --epic is a usage error (2) that lists the real Epics" "$?" \
  "code=$code $err"
err="$("$NX" "$PROD" --once --phase=nope 2>&1 >/dev/null)"
contains "$err" "存在しないフェーズ"
check "the usage error is localized like everything else" "$?" "$err"

# ------------------------------------------------------------------- cross-view agreement
echo "the two views agree"
"$NX" "$PROD" --json > "$WORK/pipe.json"
"$NX" "$PROD" --json --view=backlog > "$WORK/back.json"
python3 - "$WORK/pipe.json" "$WORK/back.json" <<'PY'
import json, sys
pipe = json.load(open(sys.argv[1]))
back = json.load(open(sys.argv[2]))
want = (pipe["summary"]["completed"], pipe["summary"]["total"], pipe["summary"]["stale"])
strip = back["pipeline"] or {}
got = (strip.get("completed"), strip.get("total"), strip.get("stale"))
if want != got:
    print("pipeline strip %s != pipeline view %s" % (got, want))
    sys.exit(1)
PY
check "the backlog view's pipeline strip matches the pipeline view" "$?"

# ------------------------------------------------------------------------- refresh poll
echo "live-refresh change detection"
python3 - "$ARCH" <<'PY'
import os, sys, time
sys.path.insert(0, os.path.join(os.environ["NX_TEST_ROOT"], "tools", "lib"))
os.environ["NX_PLUGIN_ROOT"] = os.environ["NX_TEST_ROOT"]
os.environ["NX_PROJECT_DIR"] = sys.argv[1]
import pipeline_status_view as PV
proj = sys.argv[1]
view = PV.PipelineView(proj, "en")
before = view.extra_stamp()
time.sleep(1.1)
# Overwrite an EXISTING file three levels down: not one directory mtime changes.
deep = os.path.join(proj, "reports", "before", "arch-fx", "technology-stack.md")
with open(deep, "w") as fh:
    fh.write("rewritten\n")
if view.extra_stamp() == before:
    print("overwriting %s did not move the stamp" % deep)
    sys.exit(1)
PY
check "overwriting an existing depth-3 report is noticed by the poll" "$?"

printf '%d failure(s)\n' "$FAILURES"
[ "$FAILURES" -eq 0 ]
