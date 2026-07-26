#!/usr/bin/env bash
# Exercises the delivery-mode interlock that /architect:implement-backlog Step 5b
# and /architect:generate-docs specify: source-root resolution, the
# git check-ignore gate, the working-branch commit, and empty-commit detection.
# Everything except tracker (Issue) linkage, which needs a real GitLab/GitHub.
set -u
PASS=0; FAIL=0
check() { # name, condition-exit
  if [ "$2" -eq 0 ]; then echo "  PASS  $1"; PASS=$((PASS+1));
  else echo "  FAIL  $1"; FAIL=$((FAIL+1)); fi
}

REPO=$(mktemp -d)/target
mkdir -p "$REPO"/{services/api/src,generated/api}
cd "$REPO" || exit 1

git init -q -b main
git config user.email t@example.com
git config user.name Test

# The output conventions a target project commonly adopts.
printf 'reports/\ngenerated/\nwork/\n' > .gitignore
cat > services/api/package.json <<'JSON'
{ "name": "api", "scripts": { "build": "tsc", "test": "vitest run" } }
JSON
echo 'export const x = 1;' > services/api/src/index.ts
echo 'scaffold' > generated/api/placeholder.txt
git add -A && git commit -qm "initial"

echo "delivery-mode interlock ($REPO)"
echo
echo "1. the gate rejects a git-ignored source root"
git check-ignore -q generated/api; rc=$?
check "check-ignore reports generated/api as ignored (exit 0)" "$([ $rc -eq 0 ] && echo 0 || echo 1)"
rule=$(git check-ignore -v generated/api | awk '{print $1}')
check "the matching rule is reportable to the user (${rule:-none})" \
      "$([ -n "$rule" ] && echo 0 || echo 1)"

echo
echo "2. the gate accepts a real source root"
git check-ignore -q services/api; rc=$?
check "check-ignore exits 1 for services/api (not ignored)" "$([ $rc -eq 1 ] && echo 0 || echo 1)"
inside=$(git rev-parse --is-inside-work-tree 2>/dev/null)
check "root resolves inside the worktree" "$([ "$inside" = true ] && echo 0 || echo 1)"

echo
echo "3. docs commit lands on the working branch"
git checkout -q -b feature/I1.2.3-api-docs
cat > services/api/README.md <<'MD'
# api

<!-- nexus:begin:build-and-run -->
## Build and run

| Command | Runs |
|---------|------|
| `npm run build` | `tsc` |
| `npm run test` | `vitest run` |
<!-- nexus:end:build-and-run -->
MD
git add -A
git commit -qm "docs: document api build and run (#3)"
staged=$(git show --stat --format= HEAD | grep -c "services/api/README.md")
check "commit staged the intended file" "$([ "$staged" -ge 1 ] && echo 0 || echo 1)"
check "commit message references the Issue" \
      "$(git log -1 --format=%s | grep -q '(#3)' && echo 0 || echo 1)"
check "branch is the shared contract name" \
      "$([ "$(git rev-parse --abbrev-ref HEAD)" = feature/I1.2.3-api-docs ] && echo 0 || echo 1)"

echo
echo "4. empty-commit detection catches an ignored output path"
mkdir -p generated/api
cat > generated/api/README.md <<'MD'
# would-be docs written into an ignored tree
MD
git add -A 2>/dev/null
if git diff --cached --quiet; then staged_any=0; else staged_any=1; fi
check "git add staged nothing (the silent failure the gate prevents)" \
      "$([ "$staged_any" -eq 0 ] && echo 0 || echo 1)"
git commit -qm "docs: into ignored tree (#4)" 2>/dev/null
rc=$?
check "commit refuses to create an empty commit" \
      "$([ $rc -ne 0 ] && echo 0 || echo 1)"

echo
echo "5. verified commands correspond to real build targets"
for c in build test; do
  grep -q "\"$c\"" services/api/package.json
  check "documented 'npm run $c' exists in package.json" $?
done

echo
echo "$PASS passed, $FAIL failed"
cd / && rm -rf "$(dirname "$REPO")"
[ "$FAIL" -eq 0 ]
