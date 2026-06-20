---
description: |
  Extract and define features from the UI mocks — each screen action becomes a Command/feature,
  reconciled against scope and prioritized with MoSCoW, with every feature traced to a job, journey,
  and success metric. Stops if the mocks are empty. /product:define-features [--auto] [--lang=ja|en].
model: sonnet
user_invocable: true
---

# Feature Definition

## Desired Outcome

Produce one deliverable:

1. **Feature list** — `reports/02_spec/feature-list.md` (`FEAT-` IDs): for each feature — name,
   description, corresponding screen(s), rationale (tracing `JOB-` / `JNY-` / `NSM-`), and MoSCoW
   priority. Out-of-Scope items are excluded by construction.

## Invocation

```
/product:define-features [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--auto` | Optional | Extract without elicitation; record open questions as `TBD` |
| `--lang` | Optional | Override output language |

## Decision Criteria

- **Action → Command.** Each screen action yields a candidate feature, named verb-first.
- **Respect scope.** Anything in Out-of-Scope (`SCP-` Won't) is excluded; Should/Could are deferred,
  not dropped silently.
- **Everything traces up.** Each `FEAT-` references a `JOB-`/`JNY-`/`NSM-`; a feature that traces to
  nothing is suspect.
- **Empty-input guard**: if `ui-mocks/` is empty, **stop and report** — never emit an empty feature
  list (prevents empty propagation).
- **Stop condition**: every screen action is mapped to a feature or explicitly excluded, duplicates
  merged, and all features carry MoSCoW + rationale.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/02_spec/ui-mocks/` | Required | `/product:generate-ui-mock` | **stop and report** — cannot define features without mocks |
| `reports/00_core/scope-definition.md` | Required | `/product:define-scope` | block with a message — needed to reconcile In/Out |
| `reports/01_ux/journey-maps.md` | Recommended | `/product:map-journey` | rationale `JNY-` links degrade to `TBD` |
| `reports/00_core/success-metrics.md` | Recommended | `/product:define-success-metrics` | `NSM-` rationale degrades to `TBD` |

## Process

1. **Read context** — mocks, scope, journeys, success metrics, `work/traceability.json`.
   If `ui-mocks/` is empty, stop and report.
2. **Extract** — each screen action → a Command (candidate feature). Apply
   `@rules/product/ui-to-domain.md`.
3. **Reconcile scope** — drop Out-of-Scope; defer Should/Could.
4. **Consolidate** — merge duplicates across screens; assign MoSCoW.
5. **Trace** — link each `FEAT-` to `JOB-`/`JNY-`/`NSM-`.
6. **Append traceability** — add `FEAT-` nodes to `work/traceability.json` with Upstream references.
7. **Record** — write the file; append decisions to `work/context.md`; log `TBD`s.

## Output

`reports/02_spec/feature-list.md`, with a `FEAT-` ID table (screen, rationale, MoSCoW, Upstream).

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/ui-to-domain.md` | Action→Command extraction, scope reconciliation, MoSCoW |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:generate-ui-mock` | Upstream — features are read out of the mocks |
| `/product:define-scope` | Upstream — In/Out-of-Scope gate the features |
| `/product:define-data-model` | Downstream — entities derive from features + mocks |
| `/product:design-api` | Downstream — API operations realize the features |
| `/product:adapt-change` | Re-runs this skill when scope or mocks change |
