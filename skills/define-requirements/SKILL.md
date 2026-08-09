---
description: |
  Define system requirements through document intake and interactive elicitation.
  Classifies functional/non-functional requirements, analyzes data and transaction
  requirements, and assesses Scalar product applicability (ScalarDB / ScalarDB Saga).
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
3. **Scalar product applicability assessment** — decision tree result (ScalarDB / ScalarDB Saga / neither), XA vs ScalarDB comparison, rationale (skipped with `--no-scalardb`)
4. **Open questions** — one row per question raised during the run, each with its `OQ-` ID, status (`answered` rows stay as the decision record; `deferred` / `external` / `unasked` are what is still open), answer, owner, and downstream impact (@rules/open-questions.md)

Every requirement carries an ID (`FR-xxx` / `NFR-xxx`), a priority, and a data consistency requirement so that downstream design skills can trace decisions back to requirements.

## Invocation

```
/architect:define-requirements [target_path] [--input=<file|dir>]... [--auto] [--no-scalardb]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `target_path` | Optional | Existing codebase to reference (brownfield-style requirements definition) |
| `--input=<file\|dir>` | Optional, repeatable | Additional input documents: RFP, meeting notes, existing design docs, business flow diagrams. Read as text/Markdown/PDF |
| `--auto` | Optional | Skip elicitation; generate from input documents and existing artifacts only. Unknown items become `TBD` and are recorded in Open Questions as `unasked`, carrying the question and the options that would have been offered (@rules/open-questions.md §5). Error if combined with no inputs at all |
| `--no-scalardb` | Optional | Skip the Scalar product applicability assessment (Step 4) |

## Decision Criteria

- **Never fabricate requirements.** Every requirement must be grounded in an input document, an existing artifact, or a user answer. Never guess.
- **Ask before writing `TBD`.** An unknown the materials do not answer is put to the user with `AskUserQuestion` — 2–4 candidate answers derived from the materials, each described by what it changes downstream, with the harness-appended "Other" carrying any answer the options cannot express. `TBD` is only for what the user defers, cannot answer in-session, or was never asked under `--auto`. Full protocol: @rules/open-questions.md.
- **Always confirm numeric targets** (latency, throughput, RPO, RTO). Ask them as bands (`p95 < 100 ms` / `< 500 ms` / `< 1 s`) so an exact figure arrives through free text; record the figure verbatim, normalize only units, and confirm the normalization. Only if the user cannot supply one does it become `TBD` with the question that must be answered.
- **Judge consistency requirements per business process**, not per system. Classify each process as Strong Consistency (ACID) / Eventual Consistency (Saga) / Local Tx using the criteria in the reference template.
- **Gap-driven elicitation**: read all provided materials first, then ask only about items the materials did not answer. Never re-ask something already answered by an input document.

## Prerequisites

| Input | Required/Recommended | Source |
|-------|---------------------|--------|
| `--input` documents (RFP, meeting notes, design docs) | Recommended | User-specified |
| `target_path` (existing codebase) | Optional | User-specified |
| `reports/before/{project}/*.md` | Optional | /architect:investigate (auto-detected and added as input when present on the legacy path) |
| Product reports under `reports/00_core/`, `reports/01_ux/`, `reports/02_spec/`, `reports/03_domain/`, `reports/04_quality/` + `work/traceability.json` | Recommended | /product:* pipeline (auto-detected and added as input when present — the product→architect handoff; mapping in @docs/design.md §1.3) |
| `work/pipeline-progress.json` | Recommended | /architect:init-output (if absent, treat as standalone execution and ask the user for `output_language`) |

If none of these exist, proceed with interactive elicitation only (this combination is an error under `--auto`).

When product reports are present, this skill runs as the **product→architect handoff**: read them first and confirm/extend rather than re-eliciting what they already answer (see @docs/design.md §1.3 for the artifact mapping, ID carry-over rules, and the by-design gaps it does *not* cover).

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/open-questions.md` | The Open Questions protocol: ask with AskUserQuestion before writing `TBD`, question/option shape, free-text handling, and the entry schema for `open-questions.md` |
| `@docs/design.md` §1.3–1.4 | Product→architect artifact mapping, ID carry-over rules, and by-design gaps (read when product reports are present) |
| `workflow/greenfield/01_requirements_analysis.md` | Templates: FR/NFR classification table, DB inventory, transaction requirements matrix, Scalar product applicability decision tree (Step 1.4), XA comparison table (Step 1.5) |
| `research/02_scalardb_usecases_{en\|ja}.md` | Decision tree rationale for ScalarDB applicability — background material predating ScalarDB 3.19 / ScalarDB Saga; the bundle wins on any conflict (@rules/okf-knowledge-bundle.md) |
| `research/15_xa_heterogeneous_investigation_{en\|ja}.md` | XA vs ScalarDB comparison criteria |

Read the `_en` or `_ja` variant matching `options.output_language`. Reference the templates from these files — do not duplicate their content into this skill.

## Execution Steps

### Step 1: Intake (document intake and gap analysis)

1. Read all `--input` documents (for a directory, read contained Markdown/text/PDF files)
2. If `target_path` is given, survey it with Glob/Grep for tech stack, DB usage, and integration points
3. If `reports/before/{project}/*.md` exists, add it as input
4. **Auto-detect product output.** Glob `reports/00_core/`, `reports/01_ux/`, `reports/02_spec/`, `reports/03_domain/`, `reports/04_quality/` and `work/traceability.json`; add any present as inputs. Match **files**, not directories — `/product:init-output` creates `reports/01_ux/domain-stories/` and `reports/02_spec/ui-mocks/` empty, so a directory test would report a handoff on a product project where no phase ever ran. State in the output which product artifacts were found and which were absent: a partial product run (e.g. `--profile=mvp` stops before `feature-list.md`/`nfr.md`) changes what can be carried over, and silently proceeding hides that no `FEAT-`→`FR-` link exists. Map them per @docs/design.md §1.3 — in particular: `nfr.md`/`sla.md` → NFR table (reuse `NFR-` IDs verbatim), `feature-list.md` → FR (`FEAT-`→`FR-`, record the link), `bounded-contexts.md`/`ubiquitous-language.md` → context scoping, `scope-definition.md`/`constraints.md` → scope, `assumptions.md` → open questions, `tech-stack-fitness.md` → prior for the ScalarDB applicability verdict (Step 4). Treat the §1.4 designed gaps (per-process transaction consistency, physical DB inventory, actor/role/permission) as items product does *not* supply — these drive elicitation.
5. Map every template item (business context, FR, NFR, data, consistency, constraints) to "answered by materials" or "unanswered", producing a **gap list**

### Step 2: Elicitation (gap-driven interview) — skipped with `--auto`

Run the 5-stage facilitation below using AskUserQuestion, asking **only items on the gap list**. Present what the materials already established and request confirmation or correction. Batch each stage into one call of at most 3 questions, each offering 2–4 derived candidate answers plus, where deferral is legitimate, an explicit "Defer — record as TBD" option; free text always reaches the user through the appended "Other". Items with no meaningful option set (a name, a rationale, a list) are asked in prose rather than skipped. Update the gap list after each answer; finish when every item is answered, deferred with an owner, or judged external. Question construction, free-text handling and recording: @rules/open-questions.md.

Also pick up here any `deferred` / `unasked` Open Question that this run needs an answer to from **the store** — `work/context.md` § Open Questions, which holds every plugin's questions for the whole project (@rules/open-questions.md §6). Re-ask it in the matching stage's batch and update the entry **in the store**, in place under its existing `OQ-` ID (§7). New questions this run raises are appended to the store too, with IDs allocated as `max(OQ-###) + 1` over the whole store — never by numbering from this skill's own reports, which would collide with the IDs the product run already minted.

| Stage | Items to confirm |
|-------|------------------|
| 1. Business Context | Business goal, target operations, stakeholders, scope (in/out) |
| 2. Functional Requirements | Key business processes, use cases, actors |
| 3. Non-Functional Requirements | Performance (numeric latency/throughput targets), availability, RPO/RTO, security/compliance |
| 4. Data & Integration | Data types and volume, current/planned DBs, external integrations, consistency requirement per business process |
| 5. Constraints | Technical constraints (language/cloud/existing assets), team, budget, schedule |

### Step 3: Classification (organize requirements)

1. Assign `FR-xxx` / `NFR-xxx` IDs, priority (High/Mid/Low), related services, and data consistency requirement using the classification table template. **Carry product IDs forward** when present (@docs/design.md §1.3): derive each `FR-` from a `FEAT-` and record the `FEAT-→FR-` link; **reuse product `NFR-` IDs verbatim** (same ID, same meaning) instead of re-numbering — preserve the single trace chain from `VIS-`/`NSM-` down
2. Build the DB inventory (current or planned databases, types, versions, volumes)
3. Build the transaction requirements matrix: classify each business process into Strong Consistency (ACID) / Eventual Consistency (Saga) / Local Tx with reasons. When `bounded-contexts.md` carries a per-`CTX-` consistency hint (`Strong`/`Eventual`/`TBD`, from /product:map-domains), use it as the **starting point** for the contexts a process spans — confirm or override it with a recorded reason; this is the binding classification (@docs/design.md §1.4)

### Step 4: Scalar Product Applicability — skipped with `--no-scalardb`

0. If `reports/03_domain/tech-stack-fitness.md` exists (from /product:design-architecture), use its ScalarDB/ScalarDL **Adopt/Trial/Reject** verdict as the **prior**: confirm or refute it against the transaction matrix rather than deriving the recommendation from a blank slate, and cite it as the input
1. Walk the decision tree from `workflow/greenfield/01_requirements_analysis.md` (Step 1.4) against the transaction requirements matrix
2. Fill in the assessment criteria checklist
3. If the tree reaches an XA comparison node, fill in the XA vs ScalarDB comparison table (Step 1.5) and record the verdict with rationale
4. Ground capability claims (supported databases, transaction guarantees, edition-gated features; ScalarDL tamper-evidence when in scope) in the version-pinned OKF knowledge bundle per @rules/okf-knowledge-bundle.md — cite the concept's `resource` URL, not memory
5. For each process classified **Eventual Consistency**, note whether ScalarDB Saga is a candidate (compensation is definable and business-acceptable per step) so the design phase inherits the question rather than rediscovering it — @rules/scalardb-saga-patterns.md
6. For each process classified **Strong Consistency** that spans services, note the candidate mechanism (shared-cluster one-phase / Global Transaction API on 3.19+ / application-driven 2PC) — @rules/scalardb-2pc-patterns.md
7. The result is a **recommendation**; the final decision is deferred to /architect:select-scalardb-edition and /architect:start

### Step 5: Review & Output

1. Present the draft deliverables for user confirmation (skipped with `--auto`)
2. Incorporate corrections, then write the four output files
3. **Write back to the traceability graph** (@docs/design.md §1.5): locate `work/traceability.json` or create it as `{ "schema_version": 1, "nodes": [] }` if absent, then append one node per requirement — `FR-` nodes (`type: "requirement"`, `upstream: ["FEAT-…"]`, empty `upstream` when elicited fresh) and architect-originated `NFR-` nodes (`type: "nfr"`). Do **not** duplicate a product `NFR-` that was reused verbatim; physical-only items (transaction-consistency classes, DB inventory, actor/role/permission) get empty `upstream`.
4. Update `work/pipeline-progress.json`: mark the `define-requirements` phase `completed`

## Output

Write to `reports/00_requirements/`:

| File | Content | Condition |
|------|---------|-----------|
| `reports/00_requirements/requirements-definition.md` | Business context, scope, FR/NFR classification table, priorities, actor list | Always |
| `reports/00_requirements/data-transaction-requirements.md` | DB inventory, transaction requirements matrix, consistency level assessment | Always |
| `reports/00_requirements/scalardb-applicability.md` | Decision tree result (Mermaid) per business process — ScalarDB / ScalarDB Saga / neither — XA comparison table, rationale | Unless `--no-scalardb` |
| `reports/00_requirements/open-questions.md` | **A view rendered from the store**, not a second source (@rules/open-questions.md §6): the `work/context.md` § Open Questions rows a reader of these requirements needs, in the §6 row shape — `OQ-` ID, question, status (`answered`/`deferred`/`unasked`/`external`), answer (free-text answers verbatim), options offered, owner, downstream impact, asked-at. Write the store first, then render this; never edit it as the source, and never let it carry a row the store lacks. Note at the top which rows came across the product handoff, so a reader can tell what this run raised from what it inherited | Always |

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
3. Numeric NFR targets (latency, throughput, RPO/RTO) are either filled in or listed in `open-questions.md` with a status explaining why they are still open — no interactive run leaves a `TBD` that was never asked, and every `TBD` in an artifact carries its `OQ-` ID
4. Every business process in the transaction matrix has a consistency level with a reason
5. Scalar product applicability verdict recorded per business process with rationale (unless `--no-scalardb`)
6. `work/pipeline-progress.json` updated with phase status `completed`
7. `work/traceability.json` updated with `FR-`/`NFR-` nodes; every `FR-` derived from product carries its `FEAT-` upstream and no product `NFR-` is re-numbered (@docs/design.md §1.5)

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:start | Orchestrator — runs this skill first on the greenfield path; uses `scalardb-applicability.md` for the ScalarDB usage decision |
| /architect:investigate | Optional upstream on the legacy path — its outputs are auto-detected as inputs |
| /architect:analyze | Downstream — refines actors and ubiquitous language from the requirements baseline |
| /architect:select-scalardb-edition | Downstream — makes the final ScalarDB edition decision based on the applicability recommendation |
