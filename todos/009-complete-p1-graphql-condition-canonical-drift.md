---
status: complete
priority: p1
issue_id: "009"
tags: [code-review, architecture, graphql, pipeline, security]
dependencies: []
---

# Derive the GraphQL phase condition from the canonical decision

## Problem Statement

`api-style-decisions.json` is now the canonical API-style contract, but the pipeline still enables
`design-graphql` from a separately written boolean in `pipeline-progress.json`. If that boolean is
missing or false, the security-sensitive detailed GraphQL design is skipped even when canonical JSON
selects GraphQL or hybrid.

## Findings

- `skills/design-api/SKILL.md:43` instructs the agent to copy the decision into
  `options.api_style_graphql`.
- `skills/pipeline/SKILL.md:37` and `skills/start/SKILL.md:98` consume the copied option rather than
  canonical JSON.
- `tools/lib/pipeline_status_data.py:790` evaluates conditions only from progress options.
- A fixture with valid `selected_style: graphql` JSON and `api_style_graphql: false` produces
  `status=skipped`, `excluded=condition`, and `runnable=false` for `design-graphql`.
- Current tests verify option behavior but do not assert agreement with the canonical decision.

## Proposed Solutions

### Option 1: Derive the condition from canonical JSON

Have pipeline orchestration and status derivation compute GraphQL enablement from any canonical
surface whose `selected_style` is `graphql` or `hybrid`. Treat a conflicting progress option as
drift or remove the option.

**Pros:** One source of truth; cannot silently bypass detailed design.

**Cons:** Status derivation must safely parse the decision file and surface malformed input.

**Effort:** Medium

**Risk:** Low

### Option 2: Validate and synchronize the copied option

Keep the option but make the validator update it atomically and reject later disagreement.

**Pros:** Smaller change to condition evaluation.

**Cons:** Retains duplicated state and couples a report validator to pipeline mutation.

**Effort:** Medium

**Risk:** Medium

## Recommended Action

Use Option 1. Canonical JSON should directly control both orchestration and dashboard status; a
malformed or unreadable canonical decision should block rather than select REST by default.

## Technical Details

Affected files include `tools/lib/pipeline_status_data.py`, its fixtures, `skills/pipeline/SKILL.md`,
`skills/start/SKILL.md`, and `skills/design-api/SKILL.md`.

## Acceptance Criteria

- [x] A GraphQL or hybrid canonical surface enables `design-graphql` without a copied option.
- [x] A REST-only canonical document skips it even if a stale option says true.
- [x] A disagreement is removed or reported as drift, never silently accepted.
- [x] Invalid canonical JSON blocks the phase and surfaces an actionable error.
- [x] Inventory-only and full-output completion fixtures continue to pass.

## Work Log

### 2026-08-10 - Review finding recorded

**By:** Codex

**Actions:** Built a temporary project with canonical GraphQL selection and a false copied option;
observed conditional skipping.

**Learnings:** Moving a contract to a canonical artifact is incomplete while control flow remains
bound to its old shadow field.

### 2026-08-10 - Resolved

**By:** Codex

**Actions:** Derived GraphQL enablement from validated canonical JSON, retained the option only as a
pre-artifact fallback, warned on stale disagreement, and represented invalid canonical input as a
non-runnable condition failure.

**Verification:** `python3 tools/lib/pipeline_status_data.test.py` passed.

## Resources

- Review target: `a57f666`
- `tools/lib/pipeline_status_data.py:790`
