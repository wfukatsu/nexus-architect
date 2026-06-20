---
description: |
  Turn SLOs into measurable non-functional requirements — availability, latency (p95/p99),
  throughput, error rate, durability, RPO/RTO — each traced to the SLO it derives from. Bridges to
  nexus-architect. /product:define-nfr [--auto] [--lang=ja|en].
model: sonnet
user_invocable: true
---

# Non-Functional Requirements

## Desired Outcome

Produce one deliverable:

1. **NFR** — `reports/04_quality/nfr.md` (`NFR-` IDs): availability, latency (p95/p99), throughput,
   error rate, durability, **RPO / RTO** (plus scalability/security/observability as needed). Each
   NFR carries a number (or `TBD`) and the **SLO it derives from**.

## Invocation

```
/product:define-nfr [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--auto` | Optional | Derive without elicitation; missing numbers → `TBD` |
| `--lang` | Optional | Override output language |

## Decision Criteria

- **Every NFR traces to an SLO.** An NFR with no SLO basis is suspect.
- **Numbers may be `TBD`** when no credible basis exists — record the assumption, never invent.
- **Per bounded context** — scope NFRs to the contexts that carry them, not globally by default.
- **Stop condition**: the core NFR categories are covered, each with a value (or `TBD`) and an
  Upstream `SLO-` reference.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/04_quality/sla.md` | Required | `/product:design-sla` | block with a message — NFRs derive from SLOs |
| `reports/03_domain/bounded-contexts.md` | Recommended | `/product:map-domains` | scope NFRs globally; note `TBD` per-context |

## Process

1. **Read context** — SLA/SLO, bounded contexts, `work/traceability.json`.
2. **Derive NFRs** — translate each SLO into measurable requirements across the categories. Apply
   `@rules/product/sla-nfr.md`.
3. **Scope** — attach NFRs to the relevant bounded contexts.
4. **Trace** — link each `NFR-` to its source `SLO-`.
5. **Append traceability** — add `NFR-` nodes to `work/traceability.json` with Upstream `SLO-`/`CTX-`
   references.
6. **Record** — write the file; append decisions to `work/context.md`; log `TBD`s.

## Handoff

The `NFR-` set maps to architect's non-functional inputs (`docs/design.md` §1.3) — pass via
`/architect:define-requirements --input`.

## Output

`reports/04_quality/nfr.md`, with an `NFR-` table (value/`TBD`, source `SLO-`, bounded context).

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/sla-nfr.md` | NFR taxonomy, RPO/RTO, NFR→SLO traceability |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:design-sla` | Upstream — SLOs are the basis for NFRs |
| `/product:map-domains` | Upstream — contexts scope the NFRs |
| `/architect:define-requirements` | Handoff — consumes the NFR set |
| `/product:adapt-change` | Re-runs this skill when SLOs change |
