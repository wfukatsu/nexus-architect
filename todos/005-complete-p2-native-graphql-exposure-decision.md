---
status: complete
priority: p2
issue_id: "005"
tags: [code-review, security, graphql, scalardb, architecture]
dependencies: []
---

# Make ScalarDB native GraphQL exposure machine-verifiable

## Problem Statement

The rules require explicit approval before directly exposing ScalarDB's native GraphQL interface,
but the API-style decision schema and security review do not require a named field or finding for
that exception. An agent can produce prose that omits the decision while still satisfying the
current static tests.

## Findings

- `api-style-selection.md` says direct native exposure needs user approval plus release/edition,
  authentication, authorization, audit, query limits, and network-isolation checks.
- Its required decision fields do not include native exposure mode, approval, or evidence.
- `design-api` requires the choices to be distinct but does not define a structured row/field.
- `tools/graphql_skills.test.py` checks only that phrases exist in source files, not that the
  generated decision artifact or security review must carry the exception evidence.

Locations:

- `rules/api-style-selection.md:37`
- `rules/api-style-selection.md:56`
- `skills/design-api/SKILL.md:130`
- `tools/graphql_skills.test.py:59`

## Proposed Solutions

### Option 1: Add required structured decision fields

Require `graphql_provider`, `native_exposure`, `approval`, `pinned_release`, `edition`, control
evidence, and rationale in `api-style-decisions.md`; make missing/unsafe direct exposure a critical
review finding.

- Pros: deterministic and reviewable; directly enforces the stated default.
- Cons: expands the decision table.
- Effort: Small.
- Risk: Low.

### Option 2: Prohibit direct native exposure entirely

- Pros: simplest and safest.
- Cons: removes explicitly intended internal/admin exceptions.
- Effort: Small.
- Risk: Medium product limitation.

## Recommended Action

Use Option 1 and add a fixture for Spring facade, approved internal native exposure, and rejected
external native exposure.

## Technical Details

The review must consult the pinned OKF release and contracted edition. Approval alone must not bypass
missing authentication, authorization, auditing, query governance, or network isolation.

## Acceptance Criteria

- [x] The decision artifact has explicit provider/exposure/approval/evidence fields.
- [x] Missing approval or control evidence for native exposure is critical.
- [x] The pinned release and edition are recorded and checked.
- [x] Static/project tests validate the structured contract, not only prose substrings.

## Work Log

### 2026-08-10 - Review finding recorded

**By:** Codex

**Actions:** Compared the native-exposure prohibition with required decision fields and tests.

**Learnings:** A security exception stated only in prose is not a verifiable guardrail.

### 2026-08-10 - Resolved

**By:** Codex

**Actions:** Added the JSON decision artifact and validator, made invalid native exposure a critical
security finding, and covered Spring facade, approved internal, and unsafe external fixtures.

**Verification:** `python3 tools/graphql_skills.test.py` passed.

## Resources

- Review target: `b453885`
- `rules/okf-knowledge-bundle.md`
