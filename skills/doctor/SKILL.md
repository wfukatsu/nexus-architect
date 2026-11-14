---
description: |
  Check the install and a project: plugins at the repository's version, hooks and skills in
  place, the two knowledge bundles present and fresh, the project's registry, question store,
  audit log, learned rules and claims readable. Run it first when a command misbehaves.
argument-hint: '[project_dir]'
allowed-tools:
  - Bash(${CLAUDE_PLUGIN_ROOT}/tools/doctor.sh *)
  - 'Bash("${CLAUDE_PLUGIN_ROOT}/tools/doctor.sh" *)'
model: haiku
disable-model-invocation: true
---

# Doctor

**Usage:** `/architect:doctor [project_dir]`

Wraps `${CLAUDE_PLUGIN_ROOT}/tools/doctor.sh`, which prints one line per check — `ok`, `warn` or
`FAIL` with its detail — in five sections, and exits 1 when anything failed.

## Desired Outcome

The user knows, in one screen, whether what they are about to run is what they think it is: the
installed plugins at the repository's version (a session serves the installed copy, so a newer
checkout is the most common surprise), the hooks registered and their scripts present, the
ScalarDB and Kubernetes/Terraform knowledge bundles populated and inside their `stale_after`
dates, and the project's files in the shapes the skills read.

## Execution

Run `"${CLAUDE_PLUGIN_ROOT}/tools/doctor.sh" <project_dir>` — the project directory when the
user names one, otherwise the current directory when it holds `work/pipeline-progress.json`,
otherwise nothing (the repository and install checks still run). Pass `format=json` only when the
user asks for machine-readable output.

| Section | Checks | A failure means |
|---------|--------|-----------------|
| repository | `marketplace.json` parses, the four plugins share one version, every registered skill has a `SKILL.md`, `hooks.json` names scripts that exist, `hooks/claim.sh` present | The checkout is incomplete or mid-edit — run `bash tools/run-tests.sh` there |
| tools | `bash`, `git`, `python3` required; `gh`, `glab`, `claude`, `rtk` optional (warn) | Install the missing tool; an optional one only limits backlog delivery, evals or condensed output |
| install | each `<plugin>@nexus-architect` in `~/.claude/plugins/installed_plugins.json`, its version against the repository's | A warning, never a failure: update the plugin (`/plugin`), or point the run at the checkout with the plugin-directory option of the `claude` command |
| bundles | `knowledge/okf-scalardb-scalardl/okf` populated (the submodule), `knowledge/okf-k8s-tf` present, no document past its `stale_after` | `tools/update-okf-bundle.sh ensure`; a stale document is `/architect:revise-knowledge` |
| project | the registry parses with object options and a known profile / depth, every phase status known, phases awaiting approval listed, the Open Questions store headed `ID`, the audit log, learned rules and claims parse | A hand edit broke a file the skills read; the detail names it |

Report the output as it is. When a section warns, say in one line what the user can do about it
(the table's last column); do not fix anything yourself — the doctor never writes.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:report-status | What the project is doing; the doctor is whether it can be read |
| /architect:update-knowledge | Fetches the bundle the doctor found empty |
| /architect:revise-knowledge | Re-verifies the bundle documents the doctor found past their date |
