# Pipeline Progress Registry

## JSON Schema: `work/pipeline-progress.json`

```json
{
  "$schema": "progress-registry-v1",
  "project_name": "sample-project",
  "target_path": "./target/path",
  "created_at": "ISO8601",
  "updated_at": "ISO8601",
  "options": {
    "scalardb_enabled": true,
    "workflow_type": "legacy|greenfield",
    "output_language": "en",
    "confirm_versions": true,
    "skip_phases": []
  },
  "phases": {
    "investigate": {
      "status": "pending|in_progress|completed|failed|skipped",
      "started_at": null,
      "completed_at": null,
      "updated_at": null,
      "note": "",
      "outputs": [],
      "summary": ""
    }
  },
  "errors": [],
  "warnings": []
}
```

## Options

| Option | Values | Meaning |
|--------|--------|---------|
| `scalardb_enabled` | `true` \| `false` | Whether the ScalarDB-specific phases run |
| `workflow_type` | `legacy` \| `greenfield` | Which entry path the project took |
| `output_language` | `en` \| `ja` | Language of generated report content |
| `confirm_versions` | `true` \| `false` | Project default for confirming resolved dependency versions with the user before pinning them (see @rules/dependency-versions.md). Absent → interactive runs ask, `--auto` runs adopt. Overridden per run by `--confirm-versions` / `--no-confirm-versions`. |
| `skip_phases` | list of phase names | Phases the user excluded |

## Phase Fields

| Field | Written when | Meaning |
|-------|--------------|---------|
| `status` | always | See Status Values below |
| `started_at` | entering the phase | ISO8601 stamp set together with `in_progress` |
| `completed_at` | leaving the phase | ISO8601 stamp set together with `completed` |
| `updated_at` | any write | ISO8601 stamp of the last change to this entry |
| `note` | optional, during a long phase | One short line describing the step in flight (e.g. `"step 3/7: ubiquitous language"`) — surfaced verbatim by the status dashboard |
| `outputs` | on completion | The files the phase actually wrote |
| `summary` | on completion | One or two lines of what it concluded |

## Status Values

| Status | Meaning |
|--------|---------|
| pending | Not yet executed |
| in_progress | Currently running |
| completed | Finished successfully |
| failed | Execution failed |
| skipped | Skipped (condition not met or user-specified) |

## The `in_progress` Contract

**Write `in_progress` before invoking the skill, not after it returns.** The registry is
the only source that can say a phase is running *while* it runs — its declared outputs do
not exist yet, so nothing else on disk shows it. `/architect:report-status` and
`/product:report-status` render this directly, and the token-usage hook attributes cost
to whichever phases are `in_progress`, so a phase that skips this step has its tokens
land in the pending bucket.

Per phase, an orchestrator (`/architect:pipeline`, `/architect:start`, `/product:start`)
therefore writes twice:

1. **Before the skill runs** — `status: "in_progress"`, `started_at`, `updated_at`.
   Parallel phases each get their own entry set at the same time.
2. **After it returns** — `status: "completed"` (or `"failed"` / `"skipped"`),
   `completed_at`, `updated_at`, `outputs`, `summary`.

A skill invoked on its own does the same for its own phase. Long phases may refresh
`note` and `updated_at` between steps; nothing depends on it, and it is never required.

## One Registry, Two Pipelines

`work/pipeline-progress.json` is **shared** by the product and architect pipelines — a
project that ran `/product:start` and then handed off to `/architect:define-requirements`
(@docs/design.md §1) has both pipelines' phases in one file. Two consequences bind every
orchestrator:

1. **Writes are additive.** Never re-register the whole `phases` map, never drop an entry
   whose name your manifest does not define, and never reset an `options` value another
   pipeline set (notably `output_language`). This is also why `init-output` merges rather
   than initializes when the file already exists.
2. **Four phase names are ambiguous.** `map-domains`, `design-api`, `create-domain-story`
   and `report` are defined by **both** manifests, and the map is keyed by bare phase
   name — so an entry under one of them may belong to the other pipeline. Before treating
   such an entry as satisfied (resume, dependency checks, "already done"), **confirm it
   against the phase's own declared `outputs:` on disk**. A `completed` with none of your
   manifest's outputs written is the neighbour's stamp, not your phase: run the phase.
   `tools/nexus-status.sh` applies the same rule and flags these as `shared-name` drift.

## Resume Behavior

- `--resume-from=phase-N`: Execute phases from phase-N onward where status != completed
- `--rerun-from=phase-N`: Reset all phases from phase-N onward to pending and re-execute
- Natural resume: Completed phases are automatically skipped (idempotent) — subject to the
  ambiguous-name confirmation above

Reset semantics follow the same additive rule: `--rerun-from` resets only the phases
**your** manifest defines.

## Orchestrator Usage Patterns

1. Initialize all phases as pending at pipeline start
2. Update status to in_progress before each skill execution
3. Record outputs and summary upon completion, then update to completed
4. Record details in errors upon failure and update to failed
5. Automatically skip downstream phases when a dependency has failed
