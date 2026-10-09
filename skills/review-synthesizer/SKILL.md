---
description: |
  Consolidate parallel review results. Deduplicate findings, classify priorities, and determine
  quality gate verdict. Handles variable input of 2-6 perspectives.
model: sonnet
---

# Review Synthesis

## Expected Outcome

Receive JSON outputs from multiple review perspectives and produce a consolidated review report.

## Step 1: Deduplication

Multiple reviewers may flag the same root cause from different angles.

- **Same location + same root cause** -> Merge into one, record all perspective IDs (e.g., "CON-003, BIZ-007")
- **Same root cause + different locations** -> Keep separate, link via `related_to`
- **Different root causes + same location** -> Keep separate
- When merging, adopt the highest severity
- Consolidate recommendations into a single actionable item

## Step 2: Priority Classification

| Priority | Criteria |
|----------|----------|
| **P0 - Blocker** | Critical severity; causes data loss, security breach, or system failure |
| **P1 - Must Fix** | Major from 2+ perspectives; major from risk, scalardb, or api-security perspective |
| **P2 - Should Fix** | Major from only 1 perspective; minor common across 3+ perspectives |
| **P3 - Consider** | Minor/info severity |

## Step 3: Quality Gate Verdict

Determined based on thresholds in `${CLAUDE_PLUGIN_ROOT}/skills/review-registry.json`:

- **PASS**: aggregate >= 3.5, critical: 0, major <= 3, all perspectives >= 3.0
- **CONDITIONAL PASS**: aggregate >= 2.5, critical <= 2 (with mitigations), major <= 8
- **FAIL**: Below the above thresholds

## Step 4: Report Generation

### JSON Output (`reports/review/review-synthesis.json`)

```json
{
  "review_id": "uuid",
  "generated_at": "ISO8601",
  "verdict": "PASS|CONDITIONAL_PASS|FAIL",
  "aggregate_score": 3.8,
  "perspective_scores": {"consistency": 4.0, "risk": 3.0},
  "gate_evaluation": {
    "PASS": {"met": false, "violations": ["major 5 > 3"]},
    "CONDITIONAL_PASS": {"met": true, "violations": []}
  },
  "findings_summary": {
    "total": 0, "after_dedup": 0, "reported": 0, "active": 0, "resolved_by_revision": 0,
    "by_priority": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
    "by_severity": {"critical": 0, "major": 0, "minor": 0, "info": 0}
  },
  "findings": [{"id": "SYN-001", "priority": "P1", "source_ids": [], "perspectives": []}],
  "conditional_items": []
}
```

The keys above are a contract, because `/architect:report` builds the executive summary from this
file with a script that reads them by name: a key that is absent or shaped differently renders as
`?` or an empty cell, and the build still succeeds. Keep each one as shown:

- `perspective_scores` maps each perspective to its score as a **number**. Weights, dimensions and
  per-perspective finding counts go under a key of their own (for example `perspective_detail`).
- `gate_evaluation` has the two entries `PASS` and `CONDITIONAL_PASS`, each with `met` and the
  `violations` that kept it from being met (empty when it was).
- `findings_summary` counts: `total` is every finding the individual reviews raised,
  `after_dedup` what is left after Step 1, `reported` how many of those this synthesis lists,
  `active` how many are still open, and `resolved_by_revision` how many a document revision
  closed (Step 5); `reported` = `active` + `resolved_by_revision`. `by_priority` and `by_severity`
  count the deduplicated findings and carry every key, zero included.

Further keys are welcome; these are the ones not to rename.

### Markdown Output (`reports/review/review-synthesis.md`)

Headings: Verdict -> Score Summary -> P0 Blockers -> P1 Must Fix -> P2 Should Fix -> P3 Consider

## Step 5: Revision Propagation Check

When a finding is resolved by revising a design document, the retracted claim tends to survive in
*other* artifacts — most dangerously in OpenAPI operation descriptions, which downstream code
generators read as instructions (this shipped once: a retracted "validate() may be skipped" claim
survived in an OpenAPI description after the transaction design was corrected).

For every finding marked resolved-by-revision:

1. Identify the retracted claim's key phrases (in both languages if the project mixes them).
2. Grep **all** of `reports/**` — including `api-specifications/**/*.yaml` and `.graphqls`, not
   only Markdown — for residual occurrences.
3. Any residue is recorded as a new finding attached to the original ID, and the resolution is
   downgraded until the residue is gone. A resolution verified only in the document that was
   edited is not verified.

## Variable Input Handling

Operates with any combination of 2-6 perspectives.
Reads the weights of enabled perspectives from `${CLAUDE_PLUGIN_ROOT}/skills/review-registry.json`, normalizes them, and aggregates scores.
