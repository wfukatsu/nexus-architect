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
| `--auto` | Optional | Extract without elicitation; open questions are recorded `unasked` with the options that would have been offered (@rules/open-questions.md §5) |
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
4a. **Story map** — lay the consolidated features out as a User Story Map: the **backbone** is
   the primary persona's journey stages (`JNY-`, in order) with the jobs (`JOB-`) under each; the
   **stories** are the `FEAT-` entries hanging under the stage whose action they serve; the
   **release slices** are the MoSCoW bands, so the first slice (Must) reads as the walking
   skeleton — one feature per stage, end to end. A stage with no Must feature is either out of the
   MVP journey or a gap; say which. Nothing new is decided here: the map is a second view of
   steps 3–4, and a feature that fits no stage is a scope finding, not a new stage.
5. **Trace** — link each `FEAT-` to `JOB-`/`JNY-`/`NSM-`.
6. **Append traceability** — add `FEAT-` nodes to `work/traceability.json` with Upstream
   `SCR-` (the screen whose action this feature is), `JOB-`/`JNY-` and `NSM-` references. The
   `SCR-` edge is what carries the chain across the UI mocks: `/architect:define-requirements`
   derives each `FR-` from a `FEAT-`, so a `FEAT-` with no screen upstream leaves the requirement
   traceable only halfway back (@docs/design.md §1.5).
7. **Record** — write the file; append decisions to `work/context.md`;
   ask remaining unknowns and log only what stays open (@rules/open-questions.md).

## Output

`reports/02_spec/feature-list.md`, with a `FEAT-` ID table (screen, rationale, MoSCoW, Upstream)
and a **User Story Map** section: one table per journey stage (backbone) whose rows are the
features under it in MoSCoW order, plus a `flowchart LR` with the stages as columns and the Must
row highlighted as the walking skeleton. Features that fit no stage are listed after the map as
scope findings.

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
