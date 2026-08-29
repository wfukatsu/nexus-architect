---
description: |
  Review design documents for structural coherence, traceability, and terminology consistency.
  Used as one perspective within the parallel review system.
model: sonnet
user_invocable: true
---

# Consistency Review

## Expected Outcome

Verify the structural consistency of design documents and output findings in JSON format.

## Review Dimensions

### 1. Structural Coherence (weight: 0.35)
- Consistency of structure and heading levels across documents
- Detection of orphaned sections and broken references
- Logical soundness of the hierarchical structure

### 2. Traceability (weight: 0.35)
- Ability to trace from requirements to design to implementation
- Presence of forward and backward references
- Whether gaps are documented

### 3. Terminology Consistency (weight: 0.30)
- Consistent use of ubiquitous language
- Detection of different names for the same concept
- Abbreviations defined at first occurrence and used consistently

## Scoring

Each dimension scored 1-5 (5: Exemplary, 4: Good, 3: Acceptable, 2: Concerning, 1: Critical)

## Execution

### Step 1: Collect Input File Paths

Glob for all available design and analysis documents — the machine-readable artifacts included,
since the checks below read them, not only their Markdown projections:
- `reports/03_design/**/*.md`
- `reports/03_design/**/*.json` (aggregate / state-machine manifests, the domain event catalog,
  `api-style-decisions.json`)
- `reports/03_design/api-specifications/**/*.yaml`
- `reports/01_analysis/**/*.md`
- `work/traceability.json` when it exists (the graph the ADR and cross-plugin checks resolve
  against — it lives outside `reports/` and is passed explicitly)

Record the full list of found file paths — these will be passed to sub-agents. Record the output
of every validator run below as well: it goes into the `<VALIDATOR_OUTPUT>` block of the Task
prompts and into the `validators` object of the result (Step 3). Every "unless the model's Open
Items already records it with an owner" clause below applies uniformly — a violation the owning
artifact already tracks with an owner is a **minor** finding, never a major one.

When `reports/03_design/aggregates/aggregate-manifest.json` exists, run
`python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/aggregate_manifest.py" <project_dir>` first and pass its output to Task B.
It mechanically checks the seven well-formedness rules of @rules/aggregate-design.md §3; each
violation is a CON-2xx finding unless the model's Open Items already records it with an owner, and
the reviewers check that the schema's tables and the transaction design's TX- entries still follow
the aggregate boundaries (one aggregate per `local` transaction, cross-aggregate writes classified).

When `reports/03_design/domain-event-catalog.json` exists, run
`python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/domain_event_catalog.py" <project_dir>` first and pass its output to Task B.
It checks the Published Language against the aggregate manifest — one publisher per event that
really declares it, every declared event catalogued, consumers that are declared contexts other
than the publisher's, a delivery contract on every published event. Each violation is a CON-2xx
finding unless the catalog's Open Items already records it with an owner; the reviewers
additionally check that every publisher → consumer edge in the catalog matches a relationship
`context-map.md` draws, and that `asyncapi/` names no event the catalog lacks — an event listed
under `orphan_events` counts as catalogued (tracked, minor at most), an event in neither is the
break.

When `reports/03_design/state-machines/state-machine-manifest.json` exists, run
`python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/state_machine_manifest.py" <project_dir>` first and pass its output to Task B.
It mechanically checks the seven well-formedness rules of @rules/state-modeling.md §3, so the
reviewers spend their judgment on whether the *design documents* still agree with the model rather
than on re-deriving reachability by hand. Each violation it reports is a CON-2xx finding unless the
model's Open Items already records it with an owner.

When `reports/03_design/adr/` exists, run
`python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/adr_records.py" <project_dir>` first and pass its output to Task A **and** Task B.
It checks the record contract of @rules/architecture-decision-records.md — every record cites a
non-empty `upstream`, supersession chains close, the index equals the directory. Each shape
violation is a CON-1xx finding (Task A: headings, index, record shape). The graph-side checks are
Task B's (CON-2xx): no `ADR-` cites an `upstream` **id** absent from `work/traceability.json` (a
`reports/...` path is the legacy-path form and is checked for existence, not against the graph;
an `OQ-` is checked against the store); every `type: decision` node carries the record's ids in
`upstream` and its report paths in `sources` (rule §4); and a decision a design document states in
prose — a relationship pattern, a partition key, a reclassified context — has its record, unless
the document's Open Items already records the missing ADR with an owner.

### Step 2: Spawn Three Parallel Dimension Reviewers

In a **single message**, issue all three Task() calls simultaneously so they run in parallel:

**Task A — Structural Coherence (CON-1xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Structural coherence dimension review",
  prompt: """
You are a technical reviewer evaluating design document STRUCTURAL COHERENCE.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Validator results already obtained in Step 1 (each line is a mechanical violation to report as a
finding, or "well-formed" — do not re-derive what they already checked):
<VALIDATOR_OUTPUT>
[Insert the output of every validator run in Step 1, labelled by validator]
</VALIDATOR_OUTPUT>

Write the text of every finding in the project's configured output language
(`options.output_language` in `work/pipeline-progress.json`); keep JSON keys, IDs and file paths
as they are.

Evaluate ONLY the Structural Coherence dimension:
- Consistency of structure and heading levels across documents
- Detection of orphaned sections and broken references
- Logical soundness of the hierarchical structure

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Structural Coherence",
  "weight": 0.35,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "CON-1<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<issue and its impact>",
      "recommendation": "<specific remediation>"
    }
  ]
}
"""
)
```

**Task B — Traceability (CON-2xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Traceability dimension review",
  prompt: """
You are a technical reviewer evaluating design document TRACEABILITY.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Validator results already obtained in Step 1 (each line is a mechanical violation to report as a
finding, or "well-formed" — do not re-derive what they already checked):
<VALIDATOR_OUTPUT>
[Insert the output of every validator run in Step 1, labelled by validator]
</VALIDATOR_OUTPUT>

Write the text of every finding in the project's configured output language
(`options.output_language` in `work/pipeline-progress.json`); keep JSON keys, IDs and file paths
as they are.

Evaluate ONLY the Traceability dimension:
- Ability to trace from requirements to design to implementation
- Presence of forward and backward references
- Whether gaps are documented
- Cross-plugin continuity (when `work/traceability.json` exists from a product handoff, per docs/design.md §1.5): every `FR-` is reachable from a `FEAT-` or explicitly flagged as elicited-fresh; no product `NFR-` was silently re-numbered; no `upstream` ID dangles across the product→architect boundary
- Bounded Context Canvases: every context in `bounded-contexts-redesign.md` has all nine Canvas parts (Name, Purpose, Strategic classification, Domain roles, Inbound communication, Outbound communication, Ubiquitous language, Business decisions, Assumptions and open questions — `skills/redesign/SKILL.md` § Bounded Context Canvas); when the product-side `reports/03_domain/bounded-contexts.md` exists, each `CTX-` keeps its id across the handoff, and a changed purpose, classification or inbound/outbound set is recorded as a decision, not silently redrawn
- Aggregate models (when `reports/03_design/aggregates/` exists, per rules/aggregate-design.md §7): every table the schema design (`scalardb-schema.md` / `data-layer-design.md`) declares belongs to exactly one aggregate, and one aggregate's tables share a partition key where OCC scope requires it; every `local` command writes one aggregate and every transaction design TX- entry that writes two aggregates is a `distributed` or `saga` command on the manifest, never `local`; every repository the implementation spec names is for a root; every invariant maps to a registered problem type in the API design where a command can violate it. An aggregate boundary the schema or the transaction design crosses silently is a traceability break
- State transition models (when `reports/03_design/state-machines/` exists, per rules/state-modeling.md §8): every state the schema's state column permits is a state in the model and vice versa; every `reject` matrix cell has a corresponding error response in the API design; every `ignore` cell has an idempotency contract; every transition classified `saga` appears in the transaction design's saga steps with a compensating transition. A model that no downstream document reflects is a traceability break, not a stylistic one

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Traceability",
  "weight": 0.35,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "CON-2<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<issue and its impact>",
      "recommendation": "<specific remediation>"
    }
  ]
}
"""
)
```

**Task C — Terminology Consistency (CON-3xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Terminology consistency dimension review",
  prompt: """
You are a technical reviewer evaluating design document TERMINOLOGY CONSISTENCY.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Validator results already obtained in Step 1 (each line is a mechanical violation to report as a
finding, or "well-formed" — do not re-derive what they already checked):
<VALIDATOR_OUTPUT>
[Insert the output of every validator run in Step 1, labelled by validator]
</VALIDATOR_OUTPUT>

Write the text of every finding in the project's configured output language
(`options.output_language` in `work/pipeline-progress.json`); keep JSON keys, IDs and file paths
as they are.

Evaluate ONLY the Terminology Consistency dimension:
- Consistent use of ubiquitous language
- Detection of different names for the same concept
- Abbreviations defined at first occurrence and used consistently
- State and event names in any state transition model appear in `ubiquitous-language.md` with the same spelling, and no state is renamed between the model, the schema and the API design
- When `reports/07_test-specs/` (Gherkin scenarios, test specifications) or generated test sources are in the file list: test and scenario names use the glossary's terms for the concept they exercise — a test named for an implementation detail or a synonym the glossary does not record (`testConfirm2`, `checkCart` for an Order) is a finding, per @rules/tdd-workflow.md §6

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Terminology Consistency",
  "weight": 0.30,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "CON-3<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<issue and its impact>",
      "recommendation": "<specific remediation>"
    }
  ]
}
"""
)
```

### Step 3: Merge and Write Output

After all three Tasks complete, compute the weighted score and write output:

```
weighted_score = round(0.35 × scoreA + 0.35 × scoreB + 0.30 × scoreC, 2)
```

Write `reports/review/individual/review-consistency.json`:
```json
{
  "perspective": "consistency",
  "reviewer": "review-consistency",
  "timestamp": "<ISO-8601 now>",
  "dimensions": [<Task A result>, <Task B result>, <Task C result>],
  "validators": {
    "aggregate_manifest": {"exit": 0, "output": "..."},
    "state_machine_manifest": {"exit": 0, "output": "..."},
    "domain_event_catalog": {"exit": 0, "output": "..."},
    "adr_records": {"exit": 0, "output": "..."}
  },
  "weighted_score": <computed>,
  "summary": "<2-3 sentences synthesizing the key findings and overall structural health>"
}
```

`validators` lists only the validators whose artifact existed (Step 1); the synthesizer treats a
non-zero exit as evidence behind the corresponding finding. Stamp `work/pipeline-progress.json`
per @skills/common/progress-registry.md — `in_progress` with `plugin: "architect"` before Step 1,
`completed` with `outputs` and `summary` after this write; on a re-run the `in_progress` write
also clears the previous run's `completed_at` and `summary` so the entry never claims both.

## Output Format

Finding ID prefix: **CON-**
- CON-1xx: Structural Coherence
- CON-2xx: Traceability
- CON-3xx: Terminology Consistency
