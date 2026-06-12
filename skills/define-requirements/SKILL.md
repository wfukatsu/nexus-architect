---
description: |
  Define system requirements through document intake and interactive elicitation.
  Classifies functional/non-functional requirements, analyzes data and transaction
  requirements, and assesses ScalarDB applicability.
  /architect:define-requirements [target_path] [--input=<file|dir>] [--auto] [--no-scalardb] to invoke.
  Entry point for the greenfield design path. Can also run standalone or after
  /architect:investigate on the legacy path. Accepts additional input documents
  (RFP, meeting notes, existing design docs) via --input.
model: opus
user_invocable: true
---

# Requirements Definition

## Desired Outcome

Produce a traceable requirements baseline as four deliverables:

1. **Requirements definition** — business context, scope, FR/NFR classification with IDs and priorities, actor list
2. **Data & transaction requirements** — DB inventory, transaction requirements matrix, consistency level per business process
3. **ScalarDB applicability assessment** — decision tree result, XA vs ScalarDB comparison, rationale (skipped with `--no-scalardb`)
4. **Open questions** — unresolved items (TBD), owners, downstream impact

Every requirement carries an ID (`FR-xxx` / `NFR-xxx`), a priority, and a data consistency requirement so that downstream design skills can trace decisions back to requirements.

## Invocation

```
/architect:define-requirements [target_path] [--input=<file|dir>]... [--auto] [--no-scalardb]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `target_path` | Optional | Existing codebase to reference (brownfield-style requirements definition) |
| `--input=<file\|dir>` | Optional, repeatable | Additional input documents: RFP, meeting notes, existing design docs, business flow diagrams. Read as text/Markdown/PDF |
| `--auto` | Optional | Skip elicitation; generate from input documents and existing artifacts only. Unknown items become `TBD` and are recorded in Open Questions. Error if combined with no inputs at all |
| `--no-scalardb` | Optional | Skip the ScalarDB applicability assessment (Step 4) |

## Judgment Criteria

- **Never fabricate requirements.** Every requirement must be grounded in an input document, an existing artifact, or a user answer. If a value is unknown, record it as `TBD` in Open Questions — do not guess.
- **Always confirm numeric targets** (latency, throughput, RPO, RTO). If they cannot be obtained, record them as `TBD` with the question that must be answered.
- **Judge consistency requirements per business process**, not per system. Classify each process as Strong Consistency (ACID) / Eventual Consistency (Saga) / Local Tx using the criteria in the reference template.
- **Gap-driven elicitation**: read all provided materials first, then ask only about items the materials did not answer. Never re-ask something already answered by an input document.

## Prerequisites

| Input | Required/Recommended | Source |
|-------|---------------------|--------|
| `--input` documents (RFP, meeting notes, design docs) | Recommended | User-specified |
| `target_path` (existing codebase) | Optional | User-specified |
| `reports/before/{project}/*.md` | Optional | /architect:investigate (auto-detected and added as input when present on the legacy path) |
| `work/pipeline-progress.json` | Recommended | /architect:init-output (if absent, treat as standalone execution and ask the user for `output_language`) |

If none of these exist, proceed with interactive elicitation only (this combination is an error under `--auto`).

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `workflow/greenfield/01_requirements_analysis.md` | Templates: FR/NFR classification table, DB inventory, transaction requirements matrix, applicability decision tree, XA comparison table |
| `research/02_scalardb_usecases_{en\|ja}.md` | Decision tree rationale for ScalarDB applicability |
| `research/15_xa_heterogeneous_investigation_{en\|ja}.md` | XA vs ScalarDB comparison criteria |

Read the `_en` or `_ja` variant matching `options.output_language`. Reference the templates from these files — do not duplicate their content into this skill.

## Execution Steps

### Step 1: Intake (document intake and gap analysis)

1. Read all `--input` documents (for a directory, read contained Markdown/text/PDF files)
2. If `target_path` is given, survey it with Glob/Grep for tech stack, DB usage, and integration points
3. If `reports/before/{project}/*.md` exists, add it as input
4. Map every template item (business context, FR, NFR, data, consistency, constraints) to "answered by materials" or "unanswered", producing a **gap list**

### Step 2: Elicitation (gap-driven interview) — skipped with `--auto`

Run the 5-stage facilitation below using AskUserQuestion, asking **only items on the gap list**. Present what the materials already established and request confirmation or correction. Target at most 3 questions per stage. Update the gap list after each answer; finish when every item is either answered or confirmed as TBD.

| Stage | Items to confirm |
|-------|------------------|
| 1. Business Context | Business goal, target operations, stakeholders, scope (in/out) |
| 2. Functional Requirements | Key business processes, use cases, actors |
| 3. Non-Functional Requirements | Performance (numeric latency/throughput targets), availability, RPO/RTO, security/compliance |
| 4. Data & Integration | Data types and volume, current/planned DBs, external integrations, consistency requirement per business process |
| 5. Constraints | Technical constraints (language/cloud/existing assets), team, budget, schedule |

### Step 3: Classification (organize requirements)

1. Assign `FR-xxx` / `NFR-xxx` IDs, priority (High/Mid/Low), related services, and data consistency requirement using the classification table template
2. Build the DB inventory (current or planned databases, types, versions, volumes)
3. Build the transaction requirements matrix: classify each business process into Strong Consistency (ACID) / Eventual Consistency (Saga) / Local Tx with reasons

### Step 4: ScalarDB Applicability — skipped with `--no-scalardb`

1. Walk the decision tree from `workflow/greenfield/01_requirements_analysis.md` (Step 1.4) against the transaction requirements matrix
2. Fill in the assessment criteria checklist
3. If the tree reaches an XA comparison node, fill in the XA vs ScalarDB comparison table (Step 1.5) and record the verdict with rationale
4. The result is a **recommendation**; the final decision is deferred to /architect:select-scalardb-edition and /architect:start

### Step 5: Review & Output

1. Present the draft deliverables for user confirmation (skipped with `--auto`)
2. Incorporate corrections, then write the four output files
3. Update `work/pipeline-progress.json`: mark the `define-requirements` phase `completed`

## Output

Write to `reports/00_requirements/`:

| File | Content | Condition |
|------|---------|-----------|
| `reports/00_requirements/requirements-definition.md` | Business context, scope, FR/NFR classification table, priorities, actor list | Always |
| `reports/00_requirements/data-transaction-requirements.md` | DB inventory, transaction requirements matrix, consistency level assessment | Always |
| `reports/00_requirements/scalardb-applicability.md` | Decision tree result (Mermaid), XA comparison table, rationale | Unless `--no-scalardb` |
| `reports/00_requirements/open-questions.md` | Unresolved items (TBD), who to ask, impact on downstream phases | Always |

Write all document content in the language configured in `work/pipeline-progress.json` (`options.output_language`). YAML frontmatter keys remain in English regardless of the output language.

### Output Frontmatter

```yaml
---
title: "Requirements Definition: {project}"
schema_version: 1
phase: "Phase 0: Requirements"
skill: define-requirements
generated_at: "ISO8601"
mode: "interactive|auto"
input_files:
  - <paths of ingested --input documents>
---
```

Mermaid diagrams (applicability decision tree, context diagram) follow @rules/mermaid-best-practices.md.

## Completion Criteria

1. All four output files written (three when `--no-scalardb`)
2. Every FR/NFR has an ID, priority, and data consistency requirement
3. Numeric NFR targets (latency, throughput, RPO/RTO) are either filled in or listed as TBD in `open-questions.md`
4. Every business process in the transaction matrix has a consistency level with a reason
5. ScalarDB applicability verdict recorded with rationale (unless `--no-scalardb`)
6. `work/pipeline-progress.json` updated with phase status `completed`

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:start | Orchestrator — runs this skill first on the greenfield path; uses `scalardb-applicability.md` for the ScalarDB usage decision |
| /architect:investigate | Optional upstream on the legacy path — its outputs are auto-detected as inputs |
| /architect:analyze | Downstream — refines actors and ubiquitous language from the requirements baseline |
| /architect:select-scalardb-edition | Downstream — makes the final ScalarDB edition decision based on the applicability recommendation |
