---
description: |
  Synthesize bounded contexts, API layers, the data model and NFRs into a runtime architecture
  (Mermaid container view + critical-path sequence + deployment/scaling view), then assess the
  fitness of a standing platform-technology checklist — Kong (API Gateway), ScalarDB, ScalarDB
  Analytics, ScalarDL — and emit an Adopt/Conditional/Reject decision with rationale for each.
  /product:design-architecture [--auto] [--lang=ja|en].
model: opus
user_invocable: true
---

# System Architecture & Technology Fitness

## Desired Outcome

Produce two deliverables:

1. **Architecture** — `reports/03_domain/architecture.md` (`ARCH-` IDs):
   - A **runtime / container view** (Mermaid `flowchart`): external systems → edge → Experience →
     Process → System APIs → stores, grouped by bounded context and tagged Core/Supporting/Generic
   - A **critical-path view** (Mermaid `sequence`): the most differentiating / highest-risk flow,
     with latency and failure-mode defaults explicit
   - A **deployment / scaling view** (table or flowchart): contexts → deployable services, scale
     characteristics per service, each tied to its `NFR-`/`SLO-`
   - A trace mapping: every diagram node → an existing `CTX-`/`API-`/`ENT-`/`NFR-` id

2. **Technology fitness** — `reports/03_domain/tech-stack-fitness.md` (`TECH-` IDs): for each of
   **Kong, ScalarDB, ScalarDB Analytics, ScalarDL** — fitness (High/Medium/Low/None), the triggering
   signals (cited `NFR-`/`CTX-`/`ENT-`/`API-`/`CON-`/`SCP-` ids), a **decision (Adopt/Conditional/
   Reject)**, the **adoption rationale** (and where it slots into the architecture if adopted), and
   conditions/risks. A scored matrix summarizes all four.

## Invocation

```
/product:design-architecture [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--auto` | Optional | Synthesize without elicitation; undecided boundaries/numbers → `TBD` |
| `--lang` | Optional | Override output language |

## Decision Criteria

- **Architecture is synthesis, not invention.** Every diagram node maps to an existing
  `CTX-`/`API-`/`ENT-`/`NFR-` id; a node with no upstream is a gap to flag, not a new capability.
- **Tech fitness is evidence-driven.** A High fitness cites ≥1 concrete artifact id; no citation →
  Low/None. "Reject with a reason" is a valid, valuable output — never fabricate adoption.
- **Honor constraints.** A technology conflicting with a `CON-` is Conditional/Reject with the
  conflict named.
- **Bridge to architect.** A ScalarDB/ScalarDL **Adopt** points forward to the `architect` plugin's
  ScalarDB pipeline.
- **Stop condition**: the runtime view plus at least one of {critical-path, deployment} view exist,
  all nodes trace to ids, and all four standing technologies carry a fitness + decision + rationale.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/03_domain/api-design.md` | Required | `/product:design-api` | block with a message — the architecture is built from the API layers |
| `reports/03_domain/bounded-contexts.md` | Required | `/product:map-domains` | block — contexts group the components |
| `reports/02_spec/data-model.md` | Required | `/product:define-data-model` | block — stores/entities and transaction boundaries inform ScalarDB fitness |
| `reports/04_quality/nfr.md` | Recommended | `/product:define-nfr` | scaling view + integrity/consistency signals degrade to `TBD` |
| `reports/00_core/constraints.md` | Recommended | `/product:define-scope` | constraint conflicts for tech fitness degrade to `TBD` |

## Process

1. **Read context** — api-design, bounded-contexts, domain-map, data-model, nfr, constraints,
   `work/traceability.json`.
2. **Synthesize diagrams** — build the runtime/container, critical-path, and deployment/scaling views.
   Apply `@rules/product/architecture-and-tech-fitness.md` (Part 1). Tag tiers; mark differentiators
   and failure-mode defaults; record `TBD`s.
3. **Assess technology fitness** — run the standing checklist (Kong, ScalarDB, ScalarDB Analytics,
   ScalarDL) against the artifacts; cite signals; decide Adopt/Conditional/Reject with rationale and
   architecture placement. Apply the rule (Part 2). Add project-relevant extras only when a signal
   demands it.
4. **Trace** — map every diagram node to an id; link each `TECH-` decision to the signals it cites.
5. **Append traceability** — add `ARCH-`/`TECH-` nodes to `work/traceability.json` with Upstream
   `CTX-`/`API-`/`ENT-`/`NFR-`/`CON-`/`SCP-` references.
6. **Record** — write both files; append decisions to `work/context.md`; log `TBD`s. If ScalarDB/
   ScalarDL is Adopt, note the handoff to the architect plugin.

## Handoff

A ScalarDB / ScalarDL **Adopt** bridges to the **architect** plugin:
`/architect:select-scalardb-edition`, `/architect:design-scalardb`,
`/architect:design-scalardb-analytics`. The `ARCH-` views also feed `/product:report`.

## Output

`reports/03_domain/architecture.md` (Mermaid diagrams + trace mapping) and
`reports/03_domain/tech-stack-fitness.md` (scored matrix + per-technology decision & rationale).

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/architecture-and-tech-fitness.md` | Three architecture views; evidence-driven fitness rubric for Kong / ScalarDB / ScalarDB Analytics / ScalarDL |
| `@rules/product/api-led-connectivity.md` | The API layers the runtime view is built from |
| `@rules/product/ddd-strategic.md` | Bounded-context tiers (Core/Supporting/Generic) |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:design-api` | Upstream — API layers are the architecture's spine |
| `/product:map-domains` | Upstream — contexts and tiers |
| `/product:define-nfr` | Upstream (soft) — scaling/consistency/integrity signals |
| `/product:report` | Downstream — consolidates the architecture views |
| `/architect:design-scalardb` | Handoff — when ScalarDB/ScalarDL is Adopt |
| `/product:adapt-change` | Re-runs this skill when contexts, NFRs, or constraints change |
