# Design Notes: Product ↔ Architect Integration

Internal design reference for how the **product** plugin hands its artifacts to the
**architect** plugin. This file is the single source of truth for the handoff mapping;
SKILL.md and rule files reference its section numbers (notably **§1.3**) instead of
duplicating the table.

This document is internal engineering documentation (English, per repository
convention). It describes the *contract* between plugins, not generated report content.

## 1. Product → Architect Handoff Contract

### 1.1 Overview

The two plugins form one continuous chain:

```
/product:start (vision → … → define-nfr / map-domains / design-api / design-architecture)
      │   product reports/ + work/traceability.json
      ▼
/architect:define-requirements   (requirements baseline)
      ▼
/architect:start | :investigate → :analyze → … → :design-* → :review-* → :report
```

The product pipeline produces a **logical, business-facing** specification (vision,
scope, personas, journeys, features, a logical data model, bounded contexts, a logical
API surface, SLO/NFR targets, and a candidate architecture). The architect pipeline
turns that into a **physical, implementation-facing** design (actor/role/permission
matrix, physical DB inventory, transaction-consistency classification, ScalarDB schema
and edition, infrastructure, security, operations).

`/architect:define-requirements` is the **single entry point** that ingests product
output. Product artifacts are passed to it as `--input` documents and/or auto-detected
from the shared `reports/` tree (see §1.2).

### 1.2 Handoff Mechanism

Two complementary paths:

1. **Auto-detection (preferred when co-located).** When product and architect run under
   the same project root, `define-requirements` auto-detects product reports under
   `reports/00_core/`, `reports/01_ux/`, `reports/02_spec/`, `reports/03_domain/`,
   `reports/04_quality/` and adds them to the intake set (alongside `work/traceability.json`).
   See the `define-requirements` Prerequisites / Step 1. The **orchestrators**
   (`/architect:start`, `/architect:pipeline`) run the same detection up front: when product
   artifacts are present they announce the handoff and route to the greenfield path with the
   reports fed in, so the bridge is visible rather than implicit.

2. **Explicit `--input`.** When the product output lives elsewhere, pass the relevant
   files (or their directory) explicitly, e.g.
   `/architect:define-requirements --input=reports/04_quality/nfr.md --input=reports/03_domain/`.

Two artifacts bypass `define-requirements` and bridge directly into later architect
skills:

- `reports/03_domain/tech-stack-fitness.md` — a ScalarDB / ScalarDL **Adopt** verdict
  bridges to `/architect:select-scalardb-edition` → `/architect:design-scalardb`
  (and `/architect:design-scalardb-analytics`). `define-requirements` should treat an
  existing Adopt verdict as the prior for its own ScalarDB applicability step (§1.3,
  scalardb-applicability row) rather than re-deriving it from scratch.
- `reports/03_domain/architecture.md` — a candidate runtime architecture that
  `/architect:design-microservices` refines.

**ID continuity.** Product maintains `work/traceability.json` with the ID scheme in
§1.3. `define-requirements` should ingest that graph and **carry product IDs forward**
rather than minting unrelated ones: a `FEAT-` becomes the source of one or more `FR-`
(record the `FEAT-→FR-` link), and a product `NFR-` is **reused verbatim** (same ID,
same meaning) instead of being re-numbered. This keeps a single trace chain from
`VIS-`/`NSM-` down to the physical design. The mechanics are §1.5.

### 1.3 Artifact Mapping Table

Product output → architect `define-requirements` deliverable. The **non-functional
inputs** rows (SLA/NFR) and the **bounded-context inputs** rows (domain) are the two
that other files cite by name.

| Product output (ID prefix) | Source skill | → `define-requirements` deliverable / section | Fit |
|----------------------------|--------------|-----------------------------------------------|-----|
| `00_core/vision-mission-value.md`, `pr-faq.md` (`VIS-`) | define-vision | requirements-definition.md → Business context | ✓ |
| `00_core/success-metrics.md` (`NSM-`) | define-success-metrics | requirements-definition.md → Business goals / success criteria | ✓ |
| `00_core/scope-definition.md`, `constraints.md` (`SCP-`) | define-scope | requirements-definition.md → Scope (in/out), Constraints | ✓ |
| `00_core/assumptions.md`, `validation-plan.md` (`ASM-`) | validate-assumptions | open-questions.md → unresolved items / open risks | ✓ |
| `01_ux/personas.md` (`PER-`, `JOB-`) | generate-persona | requirements-definition.md → Actor list (**seed only**; personas are JTBD user segments, not a role/permission matrix — architect derives roles/permissions in `:analyze`) | △ |
| `02_spec/feature-list.md` (`FEAT-`) | define-features | requirements-definition.md → Functional Requirements (`FEAT-`→`FR-`, record the link) | ✓ |
| `02_spec/examples/example-map-*.md` (`RULE-`, `EX-`) | example-map | requirements-definition.md → acceptance criteria per `FR-` (the `RULE-` entries of its `FEAT-`); `EX-` bridges to `/architect:design-aggregate` (invariant examples) and `/architect:generate-test-specs` (Gherkin scenarios) | ✓ |
| `02_spec/data-model.md` (`ENT-`) | define-data-model | data-transaction-requirements.md → data requirements (**logical ER**, not a physical DB inventory with versions/volumes) | △ |
| `03_domain/bounded-contexts.md`, `domain-map.md`, `ubiquitous-language.md` (`CTX-`) | map-domains | **Bounded-context inputs** — requirements-definition.md scoping + feeds `/architect:analyze` ubiquitous language; the per-`CTX-` consistency hint (`Strong`/`Eventual`/`TBD`) **seeds** the transaction matrix (see §1.4) | ✓ |
| `03_domain/api-design.md` (`API-`) | design-api | reference for downstream `/architect:design-api`; informs FR scope | ✓ |
| `04_quality/sla.md` (`SLO-`, `SLA-`) | design-sla | **Non-functional inputs** — NFR targets: availability, RPO/RTO source | ✓ |
| `04_quality/nfr.md` (`NFR-`) | define-nfr | **Non-functional inputs** — requirements-definition.md NFR table (reuse `NFR-` IDs verbatim) | ✓✓ |
| `03_domain/architecture.md` (`ARCH-`) | design-architecture | bridges to `/architect:design-microservices` (not define-requirements) | → |
| `03_domain/tech-stack-fitness.md` (`TECH-`) | design-architecture | scalardb-applicability.md → **prior** for the applicability verdict; Adopt bridges to `/architect:select-scalardb-edition` | → |

Fit legend: ✓✓ near 1:1 · ✓ covers · △ partial (architect must extend) · → bridges to a
later architect skill, not define-requirements.

**The ID prefixes are not documented here — they are declared.** Each phase's `id_prefix` in
`skills/product/common/skill-dependencies.yaml` (and `skills/common/skill-dependencies.yaml`
for architect's `define-requirements`) is the registry: one place that says which skill owns
which prefix, machine-readable so `tools/lib/pipeline_status_data.test.py` can assert that
every graph-writing skill declares one, that its SKILL.md actually uses it, and that no two
skills within a manifest claim the same prefix. The table above lists only the prefixes that
cross the plugin boundary; the registry lists all of them. `NFR-` is deliberately claimed by
both manifests — that is the §1.5 carry-over rule (product `NFR-` IDs are reused verbatim,
never re-numbered), not a collision.

### 1.4 Designed Gaps (product does **not** supply these)

These are intentionally left to `define-requirements` elicitation / later architect
phases — they are physical concerns the logical product spec does not decide. Listed so
they are understood as *by-design*, not accidental omissions:

| Gap | Owner | Note |
|-----|-------|------|
| **Transaction-consistency per business process** (Strong/ACID · Eventual/Saga · Local Tx) | define-requirements Step 3 | The spine of `data-transaction-requirements.md`. Product emits no *binding* per-process classification, but `map-domains` now seeds a coarse per-`CTX-` `Strong`/`Eventual`/`TBD` hint; architect confirms/overrides it and makes the binding ACID/Saga/Local-Tx call. |
| **Physical DB inventory** (engines, versions, volumes) | define-requirements Step 3 | Product `data-model.md` is a logical ER only. |
| **Actor / role / permission matrix** | `/architect:analyze` | Product personas are JTBD segments; system roles/permissions are derived downstream. |
| **Numeric NFR targets not yet decided** | define-requirements (TBD → the Open Questions store) | Product records `TBD`s in `work/context.md` § Open Questions with their `OQ-` IDs. That file is **the** store for both plugins, so nothing is "carried across": architect **re-asks the ones it needs** in its Step 2 elicitation and updates each entry in place under its existing ID, then renders `reports/00_requirements/open-questions.md` as a view of it (@rules/open-questions.md §6–7). An answer recorded there is therefore visible to a later product rerun — which is the point of not keeping two files. |

### 1.5 Cross-Plugin Traceability Write-Back

The single trace graph is preserved by having `define-requirements` **append its nodes
to the same `work/traceability.json`** that product wrote, using the existing node shape
(no schema change — the node is already generic):

```json
{ "id": "FR-007", "type": "requirement", "title": "...", "skill": "define-requirements",
  "source_file": "reports/00_requirements/requirements-definition.md",
  "upstream": ["FEAT-012"] }
```

Rules:

1. **Locate or create.** If `work/traceability.json` exists (product ran), append to it.
   If it is absent (pure-architect path), create it as `{ "schema_version": 1, "nodes": [] }`
   first, then append. Never start a second graph file.
2. **`FR-` nodes** — one per functional requirement, `type: "requirement"`,
   `upstream: ["FEAT-…"]` for every product feature it derives from (empty `upstream`
   only when the FR was elicited fresh, i.e. has no product origin).
3. **`NFR-` nodes** — when an NFR is carried over from product, **do not create a second
   node**; the product `NFR-` node already exists and is reused verbatim. Create a node
   only for NFRs that originate in architect (elicited targets product never set),
   `type: "nfr"`, `upstream` pointing to the `SLO-`/`CTX-` or business driver.
4. **Allocate every new ID as `max` over the graph, per prefix, `+ 1`.** `NFR-` is minted by
   two skills — product's `define-nfr` and architect's `define-requirements` — and numbering
   from your own report instead of from the graph collides. It is not hypothetical: a product
   run that stops before `define-nfr` (`--profile=mvp`) hands off to `define-requirements`,
   which finds no `NFR-` and mints `NFR-001`; when the product pipeline is later resumed,
   `define-nfr` mints `NFR-001` too, and the graph carries one ID with two meanings. Read the
   graph, take the highest existing number for the prefix, and continue from there — the same
   rule the Open Questions store follows for `OQ-` (@rules/open-questions.md §6).
4. **Physical-only nodes** (transaction-consistency classes, DB-inventory entries,
   actor/role/permission — the §1.4 gaps) have **no product upstream**; record them with
   empty `upstream` so the graph shows them as architect-originated.

**Verification (this is what makes the contract more than prose).** The product
`review` (traceability lens) and architect `review-consistency` check the joined graph
for: every `FR-` reachable from a `FEAT-` or flagged as fresh; no product `NFR-`
silently re-numbered; **no ID appearing twice in the graph** (rule 4 — the check that catches
two skills having minted the same `NFR-` from their own reports); no dangling `upstream` IDs
across the plugin boundary. A break is a consistency finding, not a silent drift.

> Sections 2–6 (other plugin internals) are not yet migrated into this document. Section 7
> is the canonical specification for the product adaptation engine; `rules/product/adaptation-engine.md`
> is its operational reference and points back here.

## 7. Adaptation / Re-propagation Engine (product `adapt-change`)

Canonical specification for `/product:adapt-change`. The engine takes a change, computes the
affected scope from `work/traceability.json`, has a human (or `--auto`) confirm it, re-runs **only**
the affected skills, and checks coherence. The governing principle is **minimal re-run** — never
touch a skill the change does not reach. The operational reference (change-type hints, prompts) is
`@rules/product/adaptation-engine.md`.

### 7.1 The Edge Store

`work/traceability.json` is the single source of dependency edges. Every skill appends its IDs as
its final step (§1.5 extends this across the product→architect boundary), so the engine reads one
file. The node shape is in §1.5; the key field is `upstream`:

```jsonc
{ "id": "FEAT-012", "type": "feature", "skill": "define-features",
  "source_file": "reports/02_spec/feature-list.md",
  "upstream": ["JOB-003", "JNY-005", "NSM-001"] }
```

`upstream` points to the nodes a node derives from. The **downstream** direction (who depends on
me) is the reverse of `upstream`, and that is the direction propagation follows.

### 7.2 Engine Steps

1. **Intake** — record the change in `reports/05_adaptation/change-log.md` (description, `--type`,
   timestamp passed in — scripts cannot read the clock, so the orchestrator supplies it).
2. **Candidate blast radius (deterministic)** — find the nodes the change directly touches (seeded
   by the `--type` hint, §7.4), then compute their **downstream transitive closure** by walking
   `upstream` edges in reverse. Pure graph work — no judgment yet; it only proposes candidates.
3. **Judgment pass (opus)** — examine each candidate and decide whether its upstream reference
   *still holds* despite the change, **expanding or shrinking** the set. The graph proposes; the
   judgment pass decides. Record "change → impacted ID → re-evaluate? + reason" in
   `reports/05_adaptation/impact-analysis.md`.
4. **Human confirmation** — present the confirmed impact set via `AskUserQuestion` (skipped under
   `--auto`).
5. **Minimal re-run** — re-run only the confirmed affected **product** skills, feeding existing
   artifacts as input, and update the corresponding edges in `traceability.json`.
6. **Coherence check** — run `/product:review` (consistency + traceability lenses) to catch
   contradictions introduced by the re-propagation. When the change reaches the architect boundary,
   the §1.5 cross-plugin check applies too.
7. **Report the architect-side impact** — see §7.5. The engine stops at the plugin boundary.

### 7.3 Principles

- **Minimal re-run** — transitive closure + judgment prevents both over-reach (touching unaffected
  skills) and under-reach (missing a real dependent).
- **Reversibility** — `change-log.md` records a before/after diff summary for every re-run artifact,
  so a change can be understood and undone.
- **Human checkpoint** — the impact set is confirmed before any artifact is rewritten (unless
  `--auto`).
- **Idempotent edges** — after re-run, `traceability.json` reflects the new reality; re-running the
  same change is a no-op.

### 7.4 Change-Type Entry Points

`--type=constraint | market | competitor | tech | regulation` hints where the change enters the
graph, seeding step 2's "directly touched" set:

| `--type` | Entry nodes |
|----------|-------------|
| `constraint` | `CON-` / `SCP-` (constraints, scope) |
| `market` / `competitor` | `MKT-` (market-landscape findings) / `POS-` (positioning) |
| `tech` | `TECH-` / `ARCH-` (tech-fitness, architecture) |
| `regulation` | constraints / `NFR-` |

`RULE-` (upstream: `FEAT-` / `CON-` / `SCP-` / `ENT-`) and `EX-` (upstream: `RULE-`) are reached
through the closure from any of these entries; the re-run is `/product:example-map --feature=…` for
the features whose rules moved.

### 7.5 The Architect Boundary

§1.5 puts architect's nodes in the same graph, so after a handoff the step-2 closure reaches
them: `FR-` derived from a `FEAT-`, architect-originated `NFR-`, the physical-only nodes. That
is deliberate — the point of one graph is that the chain stays visible across the boundary.

What the engine does with them is **report, not re-run**:

| | Product-owned nodes | Architect-owned nodes |
|---|---|---|
| In the closure | yes | yes |
| Judged (step 3) | yes | yes |
| Re-run (step 5) | yes | **no** |
| Artifact rewritten | yes | **no** |
| Result | updated artifact + diff | a row in `impact-analysis.md` § Architect-Side Impact, naming the owning skill and the command to act on it |

Ownership is read off the node: its `skill` field, corroborated by `source_file`
(`reports/00_requirements/…` and later architect directories are architect's).

The reason is authority, not capability. A product-side change is grounds to revise the product
spec; it is not grounds for a product skill to silently rewrite a requirements or architecture
document that implementation, backlog items and possibly shipped code depend on. Re-running that
side is the user's decision, taken with `/architect:define-requirements` (or the later architect
skill the node names) once they have seen what moved. An empty section is reported explicitly —
"the change does not cross the boundary" — so its absence means the check ran, not that it was
forgotten.
