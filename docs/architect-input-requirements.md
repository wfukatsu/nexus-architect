# architect Plugin — Input Requirements Guide

A reference for the information **you (the user) need to supply** to run the `architect` plugin.
Files that skills generate or hand off automatically (artifacts under `reports/`, etc.) are out of scope; this focuses on the information a human must bring to run the pipeline.

For the product plugin, see [product-input-requirements.md](product-input-requirements.md).

## Common Principles

- **Never fabricate.** Requirements and numbers must be grounded in an input document, an existing artifact, or a user answer. Unknowns are never guessed — they are **asked**: the skill offers 2-4 candidate answers via AskUserQuestion and the appended "Other" takes any answer the options cannot express, so you can always reply in your own words. Only what you defer, cannot answer in-session, or was never asked (`--auto`) is recorded as `TBD` (Open Questions), with its owner and impact. See [`rules/open-questions.md`](../rules/open-questions.md).
- **Gap-driven elicitation.** Provided materials are read first; only items the materials do not answer are asked. The richer your inputs, the shorter the dialogue.
- **Two execution modes.** Interactive (default) and `--auto` (skips elicitation, generates from input documents and existing artifacts only; nothing is asked, so unknowns become `TBD` recorded as `unasked` — carrying the question and the options that would have been offered, so a later interactive pass can answer them). `--auto` errors out if there are no inputs at all.
- **Output language.** Switched via `options.output_language` in `work/pipeline-progress.json` (`en` default / `ja`). The input material itself can be in any language (Japanese sources are fine).

## Purpose and Entry Points

**Purpose:** legacy refactoring / greenfield design / consulting deliverables.

**There are two entry points**, each requiring different inputs.

- **Legacy analysis / refactoring:** `/architect:investigate` (starts from investigating an existing codebase)
- **Greenfield design:** `/architect:define-requirements` (starts from requirements definition)
- `/architect:start` interactively decides which path to take.

## 1. Legacy Analysis Path (via `/architect:investigate`)

| Input | Necessity | Content |
|-------|-----------|---------|
| `target_path` (path to the codebase to investigate) | **Required** | The repository/directory to analyze. Cannot start without it |
| A way to **run** the legacy system (for `/architect:generate-characterization-tests`) | Required before the first transformation step | The build must succeed in-session and one seam (HTTP, CLI, public function) must be drivable. The database it needs is either available (its `docker-compose`, a daemon) or substituted **test-only** — an H2/SQLite profile added as a test dependency, never a change under `src/main/` — with the substitution's limits reported. Golden masters are recorded from the running code, so a system that cannot be run yields no characterization suite |

> With just the codebase specified, the investigation of technology stack, structure, technical debt, and DDD readiness runs automatically. No additional materials are required, but if you have existing design docs, they can be passed to the downstream `define-requirements` via `--input`.

## 2. Greenfield Design Path (via `/architect:define-requirements`)

| Input | Necessity | Content |
|-------|-----------|---------|
| Input materials (`--input=<file\|dir>`) | Recommended | RFP, meeting notes, existing design docs, business flow diagrams, etc. Text/Markdown/PDF. Repeatable / directory allowed |
| Existing codebase (`target_path`) | Optional | If you have existing assets to reference brownfield-style |
| product plugin artifacts | Optional (auto-linked if present) | `reports/00_core/` etc. + `work/traceability.json`. Auto-detected when present and treated as the product→architect handoff |

> If none of the above exist, requirements definition proceeds by **dialogue only** (but combining `--auto` with zero inputs is an error).

## 3. Items Always Confirmed via Dialogue (Greenfield)

For anything the materials do not cover, you are asked across the following five stages (max 3 questions per stage; nothing already answered by an input document is re-asked).

| Stage | What is confirmed |
|-------|-------------------|
| 1. Business context | Business goal, target operations, stakeholders, scope (in/out) |
| 2. Functional requirements | Key business processes, use cases, actors |
| 3. Non-functional requirements | Performance (**numeric latency/throughput targets**), availability, RPO/RTO, security/compliance |
| 4. Data & integration | Data types and volume, current/planned DBs, external integrations, **per-business-process consistency requirements** |
| 5. Constraints | Technical constraints (language/cloud/existing assets), team, budget, schedule |

> **Numeric targets (latency, throughput, RPO, RTO) are always confirmed.** If they cannot be obtained, they are recorded as `TBD` together with the question that must be answered.

## 4. Inputs Relevant to the Scalar Product Applicability Assessment

Unless `--no-scalardb` is given, Scalar product applicability (ScalarDB / ScalarDB Saga / neither, per business process) is assessed using:

- **Per-business-process transaction consistency requirements** (Strong / Eventual / Local Tx) — confirmed in Stage 4 above. Strong-consistency processes feed the ScalarDB branch; eventual-consistency processes feed the ScalarDB Saga branch (gated on whether a compensation is definable per step)
- Current/planned DB inventory (types, versions, data volume)
- (When linked with product) the `tech-stack-fitness.md` Adopt/Trial/Reject verdict, used as a **prior**

> The assessment is a **recommendation**; the final decision is deferred to `/architect:select-scalardb-edition` / `/architect:start`.

## 5. product → architect Handoff

When product-pipeline artifacts exist, running `/architect:define-requirements` **automatically enters handoff mode** and the following are taken as inputs (confirmed/extended rather than re-elicited).

| product artifact | Use on the architect side |
|------------------|---------------------------|
| `nfr.md` / `sla.md` | NFR table (reuse `NFR-` IDs verbatim) |
| `feature-list.md` | Functional requirements (`FEAT-` → `FR-` conversion, link recorded) |
| `bounded-contexts.md` / `ubiquitous-language.md` | Context scoping and consistency hints |
| `scope-definition.md` / `constraints.md` | Scope |
| `assumptions.md` | Open Questions |
| `tech-stack-fitness.md` | Prior for the ScalarDB applicability verdict |
| `work/traceability.json` | ID trace (maintains the single trace chain from `VIS-`/`NSM-`) |

Three points that are easy to miss:

- **A partial product run still hands off.** `--profile=mvp` stops before `feature-list.md` and
  `nfr.md`; `define-requirements` reports which artifacts it found and which were absent, and any
  `FR-` it elicits fresh is recorded as fresh rather than attributed to a feature that never existed.
- **Open Questions are one store, not two.** `work/context.md` § Open Questions holds every
  plugin's questions; `reports/00_requirements/open-questions.md` is rendered from it. An entry
  product recorded `unasked` is the entry architect answers, under the same `OQ-` ID.
- **New IDs are allocated from the graph.** `NFR-` is minted by both `define-nfr` and
  `define-requirements`, so a new one is `max` over `work/traceability.json` for that prefix `+ 1`
  — never numbered from a single report (see design.md §1.5 rule 4).

What product deliberately does **not** supply — and therefore what elicitation still asks about — is
the binding transaction-consistency class per business process, the physical DB inventory, and the
actor/role/permission matrix (design.md §1.4).


> Items product **deliberately does not supply** (per-business-process transaction consistency, physical DB inventory, actor/role/permission) are confirmed via dialogue on the architect side.

## Summary — Fastest Way to Start

| Goal | Entry command | Minimum to prepare |
|------|---------------|--------------------|
| Analyze / refactor an existing system | `/architect:investigate <path>` | Path to the target codebase |
| Design a new system from requirements | `/architect:define-requirements --input=<materials>` | An RFP / meeting notes / design doc (else dialogue only) |
| Carry product output into implementation design | `/architect:define-requirements` | The product pipeline's artifact set (auto-detected) |
