---
description: |
  Fetch or update the OKF ScalarDB/ScalarDL knowledge bundle from its remote repository.
  /architect:update-knowledge [--latest] [--status] to invoke.
  Run with no flag to make the bundle available locally (first fetch); --latest pulls the
  newest bundle from remote; --status reports the resolved path, commits, and bundled versions.
model: haiku
user_invocable: true
---

# Knowledge Bundle Update

## Desired Outcome

The OKF ScalarDB/ScalarDL knowledge bundle (@rules/okf-knowledge-bundle.md) is present locally
and, when requested, updated to the newest state of its remote
(https://github.com/wfukatsu/OKF-ScalarDB-ScalarDL), so ScalarDB/ScalarDL skills can ground
implementation decisions in current version-pinned documentation.

## Execution

All modes run one script: `${CLAUDE_PLUGIN_ROOT}/tools/update-okf-bundle.sh`. It resolves the
bundle in the same order as the rule (git submodule -> `~/.cache/nexus-architect/` shallow
clone) and prints the resolved `okf/` root.

| Invocation | Command | Effect |
|------------|---------|--------|
| `/architect:update-knowledge` | `tools/update-okf-bundle.sh` | Ensure the bundle is available locally; fetches from remote only if absent (submodule init, else cache clone). No-op when present. |
| `/architect:update-knowledge --latest` | `tools/update-okf-bundle.sh update` | Fetch the newest bundle from remote. On the submodule this moves the pinned commit; on the cache it fast-forwards to `origin/main`. |
| `/architect:update-knowledge --status` | `tools/update-okf-bundle.sh status` | Show resolved path, local commit vs remote `main`, and the bundled products with their latest versions. |

After running, report to the user:
1. The resolved `okf/` path and whether anything was fetched
2. The product/version table from `status` (run it after `update`)
3. When `--latest` moved the submodule pointer: remind that the change is a modification in the
   parent repository — commit it to pin the new bundle state, or leave it uncommitted to discard

## Failure Handling

- Script exit 1 with no network: report that the bundle could not be fetched and that
  ScalarDB/ScalarDL skills will fall back to online docs labeled as not version-pinned
- Never edit files under `knowledge/okf-scalardb-scalardl/` — the bundle is generated upstream;
  changes belong in the OKF-ScalarDB-ScalarDL repository

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /scalardb:docs | Consumer — searches the bundle this skill fetches |
| /architect:design-scalardb, /architect:generate-scalardb-code | Consumers — ground design/implementation decisions in the bundle |
