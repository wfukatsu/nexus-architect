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
      "plugin": "product|architect",
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
| `eli5` | `technical` \| `all` \| `off` | Which Markdown reports open with the plain-language `## ELI5` section of @rules/eli5-summary.md: those written for engineers (the skill list in `tools/lib/report_audience.py`; the default, also when absent), every report, or none. The frontmatter hook enforces it |
| `skip_phases` | list of phase names | Phases the user excluded |
| `profile` | `full` \| `enterprise` \| `poc` \| `analysis` | Which backbone phases the architect run executes — a name from the `profiles` table of `skills/common/skill-dependencies.yaml`; absent → `full`. The dashboard files the phases outside it as excluded ("outside profile …"). The product pipeline records its own `profile` (`mvp` / `core-only` / `ux-to-spec` / `full`) in this same key, so the value is read with `workflow_type` / the phase's `plugin` in mind |
| `depth` | `minimal` \| `standard` \| `comprehensive` | How much optional and review work the architect run does — a name from the manifest's `depths` table; absent → the profile's default. Governs the evidence-gated optional phases, the review perspectives and whether a perspective spawns independent reviewers |
| `layering_style` | `ddd` \| `clean` | Project default for `/architect:design-implementation --layering` — DDD application services, or Clean Architecture Use Case / Interactor / Presenter naming. The canonical record is `layering_style` in the frontmatter of `reports/06_implementation/api-layer-spec.md`, which the generators read; this option only seeds it |
| `learned_rules_path` | path, optional | A learned-rules store shared across projects (@rules/learned-rules.md §1), absolute or relative to the project; absent → `work/learned-rules.json` |
| `learnings` | `true` \| `false` | Whether `review-synthesizer` proposes learned rules; `false` is what `--no-learnings` records. Absent → `true` |
| `quality_gate` | object, optional | Project overrides for the stage-2 test-quality thresholds of @rules/ai-code-quality-gate.md §Test quality — e.g. `{ "coverage": { "domain": { "line": 90, "branch": 80 }, "other": { "line": 70 } }, "mutation": { "threshold": 80 } }`. Absent → the rule's defaults; a build-file rule wins over both |

## Phase Fields

| Field | Written when | Meaning |
|-------|--------------|---------|
| `status` | always | See Status Values below |
| `plugin` | always | `"product"` or `"architect"` — which pipeline's phase this entry is. Both pipelines write this one file and it is keyed by bare phase name, so for the four names both manifests define this field is the only thing that says whose entry it is (see One Registry, Two Pipelines). The token-usage hook reads it to keep the two pipelines' spend in separate ledger buckets |
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
| awaiting_approval | Outputs written; a person's answer or approval is pending — the questions the phase recorded are not yet put to the user, or its skill asked for approval of what it wrote. Blocks dependents like `in_progress`; is never runnable; on resume it is **asked again, never skipped**. Written by interactive orchestrators only — `/architect:pipeline` has nobody to ask and never writes it |
| revising | A phase that had reached `awaiting_approval` or `completed` being reworked in place after a rejection or an answer that changes its output. Attributed tokens like `in_progress`; ends in `completed` (or `failed`). Distinct from `--rerun-from`, which resets to `pending` |
| completed | Finished successfully |
| failed | Execution failed |
| skipped | Skipped (condition not met, outside the profile or depth, or user-specified) |

Every transition out of `pending` is also an event in the audit log (§ Audit Log), appended by
the token-usage hook when it sees the registry change — the orchestrator writes the status, the
hook writes the history.

## The `in_progress` Contract

**Write `in_progress` before invoking the skill, not after it returns.** The registry is
the only source that can say a phase is running *while* it runs — its declared outputs do
not exist yet, so nothing else on disk shows it. `/architect:report-status` and
`/product:report-status` render this directly, and the token-usage hook attributes cost
to whichever phases are `in_progress`, so a phase that skips this step has its tokens
land in the pending bucket.

Per phase, an orchestrator (`/architect:pipeline`, `/architect:start`, `/product:start`)
therefore writes twice:

1. **Before the skill runs** — `status: "in_progress"`, `plugin`, `started_at`,
   `updated_at`. Parallel phases each get their own entry set at the same time. `plugin`
   goes in on this first write: the token-usage hook attributes cost from what the
   registry says *while* the phase runs, so a phase that names its pipeline only at the
   end has its spend recorded unattributably.
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
2. **Every entry names its pipeline.** `map-domains`, `design-api`, `create-domain-story`
   and `report` are defined by **both** manifests and the map is keyed by bare phase name,
   so an entry under one of them is otherwise unattributable. Write `"plugin"` on every
   phase entry you create or stamp, and **read another pipeline's entry as none of your
   business** — not as your phase being done.
   - Where the field is missing (an entry written before this contract), fall back to the
     evidence: before treating such an entry as satisfied (resume, dependency checks,
     "already done"), **confirm it against the phase's own declared `outputs:` on disk**. A
     `completed` with none of your manifest's outputs written is the neighbour's stamp:
     run the phase. `tools/nexus-status.sh` applies exactly this — `plugin` when present,
     output corroboration when not — and flags the unresolved ones as `shared-name` drift.
   - The token-usage hook reads `plugin` too, recording a shared name's spend under
     `<plugin>:<phase>` in `work/token-usage.json` so the two pipelines' cost stays
     separable. An entry with no `plugin` leaves its spend unattributable, and the
     dashboard reports it as unassigned rather than charging it to whichever tab is open.

## Resume Behavior

- `--resume-from=phase-N`: Execute phases from phase-N onward where status != completed
- `--rerun-from=phase-N`: Reset all phases from phase-N onward to pending and re-execute
- Natural resume: Completed phases are automatically skipped (idempotent) — subject to the
  ambiguous-name confirmation above
- A phase found `awaiting_approval` is neither skipped nor rerun: an interactive orchestrator
  puts its recorded questions (or its approval) to the user again and then stamps it; a
  non-interactive one leaves it as it is and names it in the final message

## Resume Point

A dialogue-driven phase runs in steps, and a session can end between two of them. The registry
carries one top-level `resume_point` so the next session continues where the last stopped
rather than from the phase's first question:

```json
"resume_point": { "phase": "define-requirements", "step": "3b", "note": "example map for FR-004",
                  "updated_at": "2026-11-14T09:12:00Z" }
```

`phase` is required; `step` and `note` are free text the skill chooses (its own step numbering).
Written by `/architect:start` (and `/product:start`) when an inline phase moves between steps,
cleared (set to `null`) when that phase completes; `/architect:report-status` shows it in the
header. A sub-agent phase has no resume point: it either returns or it failed.

## Audit Log

`work/audit/events.jsonl` is the project's append-only history — one JSON object per line, never
rewritten, both pipelines in one file. The registry says where a run is; the audit log says what
happened and who did it. Writer: `tools/lib/audit_log.py` (library and command line); reader:
`python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/audit_log.py" <project_dir> list [tail=N] [event=…] [phase=…]`.

| Field | Meaning |
|-------|---------|
| `ts` | ISO8601 UTC |
| `event` | One of the taxonomy below |
| `category` | `phase` / `gate` / `question` / `decision` / `delivery` / `learning`, derived from the event |
| `phase` | The phase (or backlog item id) the event belongs to, or null |
| `plugin` | `product` / `architect` when known |
| `actor` | `git config user.name` of the project — never the email — or the value passed as `actor=` |
| `ref` | What the event points at: an `OQ-` / `ADR-` id, a PR/MR URL, a verdict file |
| `detail` | One line of free text |
| `source` | `hook` (the registry transition the token-usage hook observed) or `skill` |

| Event | Written by | When |
|-------|------------|------|
| `PHASE_STARTED` / `PHASE_COMPLETED` / `PHASE_FAILED` / `PHASE_SKIPPED` / `PHASE_AWAITING_APPROVAL` / `PHASE_REVISING` | `hooks/record_token_usage.py` | A phase's `status` changed to that value since the hook last fired (its first firing on a project baselines and emits nothing). Runtimes without hooks run the hook by hand after stamping the registry, as they run the report validators |
| `GATE_APPROVED` / `GATE_REJECTED` / `GATE_SKIPPED` | `deliver-backlog` (stage c), `merge-issue` (Step 2), `capture-followup` (Step 3) | The user approved or rejected at the gate; `GATE_SKIPPED` when `--yes-merge` / `--auto` pre-authorised it, with the flag in `detail` |
| `QUESTION_ASKED` / `QUESTION_ANSWERED` / `QUESTION_DEFERRED` | Every skill that asks, per `rules/open-questions.md` §6 | A question was put to the user (`ref` = its `OQ-`), answered, or left `deferred` / `unasked` / `external` |
| `ADR_RECORDED` | The five skills that write ADRs, per `rules/architecture-decision-records.md` §4 | A record was appended (`ref` = its `ADR-`) |
| `VERDICT_RECORDED` | `review-synthesizer` | The quality-gate verdict was written (`detail` = `PASS` / `CONDITIONAL_PASS` / `FAIL`) |
| `PR_OPENED` / `PR_MERGED` | `review-issue` (Step 5), `merge-issue` (Step 3) | The PR/MR was raised or merged (`ref` = its URL) |
| `RULE_PROPOSED` / `RULE_ACCEPTED` / `RULE_REJECTED` | `tools/lib/learned_rules.py`, run by `review-synthesizer` (propose) and `/architect:start` (decide) | A learned rule was proposed from a recurring finding, or a person decided it (`ref` = its `LR-`, `rules/learned-rules.md`) |

A skill appends with one positional command, no flags:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/audit_log.py" <project_dir> GATE_APPROVED phase=E1-I3 ref=<pr-url> detail="reviewed in session"
```

An unknown event name exits 2 and appends nothing. The log is evidence, never a gate: a failed
append is reported in the skill's output and the run continues.

Reset semantics follow the same additive rule: `--rerun-from` resets only the phases
**your** manifest defines.

## Orchestrator Usage Patterns

1. Initialize all phases as pending at pipeline start
2. Update status to in_progress before each skill execution
3. Record outputs and summary upon completion, then update to completed
4. Record details in errors upon failure and update to failed
5. Automatically skip downstream phases when a dependency has failed
