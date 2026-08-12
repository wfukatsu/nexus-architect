---
description: |
  Consolidate parallel review results. Deduplicate findings, classify priorities, and determine quality gate verdict.
  Handles variable input of 2-6 perspectives.
model: sonnet
user_invocable: true
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
  "verdict": "PASS|CONDITIONAL_PASS|FAIL",
  "aggregate_score": 3.8,
  "perspective_scores": {},
  "findings_summary": {"total": 0, "after_dedup": 0, "by_priority": {}, "by_severity": {}},
  "findings": [{"id": "SYN-001", "priority": "P1", "source_ids": [], "perspectives": []}],
  "conditional_items": []
}
```

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
