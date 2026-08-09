---
description: |
  Set service-level targets from customer expectations — per-service SLI/SLO/SLA with error budgets
  and criticality tiers, where SLO = SLA − buffer. /product:design-sla [--auto] [--lang=ja|en].
model: sonnet
user_invocable: true
---

# SLA Design

## Desired Outcome

Produce one deliverable:

1. **SLA** — `reports/04_quality/sla.md` (`SLA-` / `SLO-` IDs): per-service **SLI / SLO / SLA**,
   the **error budget** (`1 − SLO`) and its policy, and **criticality tiers** (critical / standard /
   best-effort). Targets align to customer expectation; SLO is stricter than SLA.

## Invocation

```
/product:design-sla [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--auto` | Optional | Derive without elicitation; missing targets → `TBD` |
| `--lang` | Optional | Override output language |

## Decision Criteria

- **SLO = SLA − buffer.** The internal objective is always stricter than the external promise.
- **Align to customer expectation**, not round numbers — pull expectations from positioning/benefit.
- **Tier by criticality** — not every service needs the same level.
- **State the error budget** (`1 − SLO`) and the freeze/release policy for critical services.
- **Stop condition**: each key service has an SLI, an SLO, an SLA with buffer, an error budget, and
  a criticality tier (numbers may be `TBD`).

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/02_spec/feature-list.md` | Required | `/product:define-features` | block with a message — SLAs attach to services/features |
| `reports/01_ux/positioning.md` | Recommended | `/product:design-positioning` | customer expectation degrades to `TBD` |
| `reports/00_core/benefit-evaluation.md` | Optional | `/product:design-revenue` | use for value/criticality weighting if present |

## Process

1. **Read context** — features, positioning (expectations), benefit eval, `work/traceability.json`.
2. **Define SLIs** — the signals that matter per key service. Apply `@rules/product/sla-nfr.md`.
3. **Set SLOs** — targets aligned to customer expectation, tiered by criticality.
4. **State SLAs** — external promise with a buffer below the SLO.
5. **Error budgets** — compute `1 − SLO`; state the policy.
6. **Append traceability** — add `SLA-`/`SLO-` nodes to `work/traceability.json` with Upstream
   `FEAT-`/`POS-` references.
7. **Record** — write the file; append decisions to `work/context.md`;
   ask remaining unknowns and log only what stays open (@rules/open-questions.md).

## Output

`reports/04_quality/sla.md`, with `SLA-`/`SLO-` tables (Upstream column), error budgets, and tiers.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/sla-nfr.md` | SLI/SLO/SLA, error budgets, criticality tiers |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:define-features` | Upstream — services/features to set levels for |
| `/product:design-positioning` | Upstream — customer expectations |
| `/product:define-nfr` | Downstream — NFRs derive from these SLOs |
| `/product:adapt-change` | Re-runs this skill when expectations change |
