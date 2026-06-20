---
description: |
  Take in constraints, normalize them, and decide product scope — explicitly what the product
  will and will not do — using MoSCoW and RICE, anchored to success metrics when available.
  /product:define-scope [--constraints=<file|text>] [--input=<file|dir>] [--auto] [--lang=ja|en].
model: sonnet
user_invocable: true
---

# Constraints & Scope

## Desired Outcome

Produce two deliverables:

1. **Constraints** — `reports/00_core/constraints.md` (`CON-` IDs): budget, deadline, technical,
   legal/regulatory, organizational constraints, normalized and classified.
2. **Scope definition** — `reports/00_core/scope-definition.md` (`SCP-` IDs):
   - **In-Scope / Out-of-Scope** table — the "won't do" list is mandatory (prevents scope creep)
   - MoSCoW classification (Must / Should / Could / Won't)
   - RICE scores for candidate items (Impact references `NSM-` success metrics when present)

## Invocation

```
/product:define-scope [--constraints=<file|text>] [--input=<file|dir>]... [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--constraints=<file\|text>` | Recommended | Budget / deadline / tech / legal / org constraints |
| `--input=<file\|dir>` | Optional, repeatable | Additional source material |
| `--auto` | Optional | Skip elicitation; unknowns → `TBD` |
| `--lang` | Optional | Override output language |

## Decision Criteria

- **Out-of-Scope is mandatory.** Always state explicitly what the product will *not* do.
- **No scope item may violate a constraint.** If it does, it is rejected or deferred with reason.
- **RICE Impact ties to a metric, not a feeling** — reference `NSM-` IDs from
  `success-metrics.md` when it exists; otherwise note Impact is provisional (`TBD` basis).
- **Never fabricate.** Unknown constraints become `TBD` in Open Questions.
- **Stop condition**: constraints are classified, and every candidate item is placed in
  In/Out-of-Scope with a MoSCoW band.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/00_core/vision-mission-value.md` | Required | `/product:define-vision` | block with a message — scope needs the vision |
| `reports/00_core/success-metrics.md` | Optional | `/product:define-success-metrics` (may be absent) | RICE Impact provisional; mark basis `TBD` |
| `--constraints` | Recommended | User | elicit interactively or `TBD` |

## Process

1. **Read context** — vision, success metrics (if any), `work/traceability.json`.
2. **Intake constraints** — normalize and classify (`CON-` IDs).
3. **Elicit / derive candidates** — list candidate capabilities from the vision and inputs.
4. **Prioritize** — MoSCoW bands; RICE scores (Impact → `NSM-` when available).
   Apply `@rules/product/scope-prioritization.md`.
5. **Draw boundary** — In-Scope / Out-of-Scope table; the Won't list is explicit.
6. **Append traceability** — add `CON-`/`SCP-` nodes to `work/traceability.json` with upstream
   `VIS-`/`NSM-` references.
7. **Record** — write both files; append decisions to `work/context.md`; log `TBD`s.

## Output

`reports/00_core/constraints.md` and `reports/00_core/scope-definition.md`, each with an ID table
including an Upstream rationale column.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/scope-prioritization.md` | MoSCoW, RICE, Kano, in/out-of-scope discipline |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:define-vision` | Upstream — provides the vision |
| `/product:define-success-metrics` | Upstream (optional) — anchors RICE Impact |
| `/product:validate-assumptions` | Downstream — validates scope assumptions |
| `/product:define-features` | Downstream — features must fit In-Scope |
| `/product:adapt-change` | Re-runs this skill when constraints change |
