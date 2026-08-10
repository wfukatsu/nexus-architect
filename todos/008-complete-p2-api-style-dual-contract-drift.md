---
status: complete
priority: p2
issue_id: "008"
tags: [code-review, architecture, contract, graphql, security]
dependencies: ["006"]
---

# Prevent Markdown and JSON API-style decision drift

## Problem Statement

The rules call the Markdown and JSON API-style decisions equivalent contracts, but the validator
only reads JSON and no deterministic join compares them. Downstream skills can therefore consume
different provider, exposure, framework, or transaction decisions without any failure.

## Findings

- `rules/api-style-selection.md:80` requires the Markdown and JSON decisions to agree.
- `design-graphql` reads `api-style-decisions.md` as its entry condition.
- `review-api-security` runs the JSON validator and relies on JSON for native-exposure controls.
- `tools/validate-api-style-decisions.py` accepts only one JSON path and cannot compare the
  human-readable artifact.
- A JSON decision selecting the Spring facade and a Markdown row selecting native GraphQL can both
  satisfy their respective consumers.

## Proposed Solutions

### Option 1: Make JSON canonical and render Markdown

Declare JSON as the sole decision contract and generate the Markdown view deterministically from
it; downstream skills read JSON for decisions and Markdown only for presentation.

**Pros:** One source of truth; simplest machine verification.

**Cons:** Requires a small renderer and migration of skill wording.

**Effort:** Medium

**Risk:** Low

### Option 2: Compare stable IDs and security fields

Keep both authored artifacts but extend validation to parse a rigid Markdown table and compare all
contract-bearing fields by `surface_id`.

**Pros:** Preserves the current authoring model.

**Cons:** Markdown parsing is brittle and creates two sources of truth.

**Effort:** Medium

**Risk:** Medium

## Recommended Action

Use Option 1. Treat `api-style-decisions.json` as canonical, render the Markdown report, and make all
downstream conditional logic read the JSON decision.

## Technical Details

Affected components: API design outputs, `design-graphql` entry condition, security review inputs,
documentation generation, and the pipeline condition stamp.

## Acceptance Criteria

- [x] Exactly one artifact is named as the canonical decision source.
- [x] The Markdown report is generated from, or deterministically checked against, that source.
- [x] GraphQL conditional execution and security review consume the same provider/exposure values.
- [x] A modified Markdown projection cannot change detailed design or review decisions because all
      consumers read canonical JSON and the next design run regenerates the projection.
- [x] Stable `surface_id` values are unique and preserved in both representations.

## Work Log

### 2026-08-10 - Review finding recorded

**By:** Codex

**Actions:** Followed each decision artifact into its downstream consumers and identified the split.

**Learnings:** Stating that duplicated contracts agree is not enforcement; one must be derived from
the other or compared mechanically.

### 2026-08-10 - Resolved

**By:** Codex

**Actions:** Declared JSON canonical, moved downstream skill inputs to JSON, added deterministic
English/Japanese Markdown rendering with a canonical-source hash, and required the full base
decision field set.

**Verification:** The generated report passed both Markdown validation hooks in the external-CWD
fixture; `python3 tools/graphql_skills.test.py` passed.

## Resources

- Review target: `24a3325`
- `rules/api-style-selection.md:78`
