# Rules: SLA & Non-Functional Requirements (design-sla, define-nfr)

Reference for the quality layer. `design-sla` sets the service-level targets from customer
expectations; `define-nfr` turns those targets into measurable non-functional requirements. Every
NFR must trace back to an SLO.

## SLI / SLO / SLA (Google SRE)

- **SLI** (Indicator) — a measured signal of service health (e.g. request success rate, p99
  latency, freshness). Define *what* is measured and *how*.
- **SLO** (Objective) — the internal target for an SLI over a window (e.g. 99.9% success over 30
  days). The team operates to the SLO.
- **SLA** (Agreement) — the externally promised level with consequences. **SLO = SLA − buffer**:
  always set the internal objective stricter than the external promise.

Order: derive SLIs → set SLOs aligned to **customer expectation** (from positioning/benefit) →
state the SLA with a safety buffer. Tier by service criticality (critical / standard / best-effort).

## Error budget

`error budget = 1 − SLO` (e.g. 99.9% → 0.1% allowed unavailability). The budget governs the
risk/velocity trade-off: spend it on releases while it lasts; freeze risky changes when exhausted.
State the budget and the policy for each critical service.

## NFR categories (define-nfr)

For each, give a number (or `TBD`) and the **SLO it derives from**:

- **Availability** — uptime % per window (from the availability SLO)
- **Latency** — p95 / p99 response time per key operation
- **Throughput** — sustained/peak requests or jobs per unit time
- **Error rate** — max acceptable failed-request ratio
- **Durability** — data-loss tolerance (e.g. 11 nines)
- **RPO** (Recovery Point Objective) — max acceptable data loss window
- **RTO** (Recovery Time Objective) — max acceptable downtime to recover
- (as needed) scalability, security, compliance, observability targets

## Discipline

- **Every NFR traces to an SLO**; an NFR with no SLO basis is suspect.
- **Numbers may be `TBD`** when no credible basis exists — record the assumption, don't invent.
- Align targets to **customer expectation and criticality**, not to round numbers.

## ID convention & handoff

`SLA-`/`SLO-` for the agreement layer, `NFR-` for requirements; append to
`work/traceability.json` with Upstream `FEAT-`/`POS-`/`CTX-` (and `SLO-`→`NFR-`) references. The
`NFR-` set maps to architect's non-functional inputs (design.md §1.3) → `/architect:define-requirements`.

## Sources

- Google — "Site Reliability Engineering" (SLI/SLO/SLA, error budgets)
- ISO/IEC 25010 — software product quality characteristics (NFR taxonomy)
