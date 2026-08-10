---
status: complete
priority: p1
issue_id: "003"
tags: [code-review, security, graphql, scalardb, error-handling]
dependencies: []
---

# Define the GraphQL unknown-transaction-status contract

## Problem Statement

The new GraphQL rules do not specify how ScalarDB's `UnknownTransactionStatusException` maps from
the existing REST-oriented 500/503 and `Retry-After` contract into a GraphQL execution response.
Different agents can generate incompatible HTTP statuses, headers, and `errors[].extensions`, which
is dangerous because a wrong retry instruction can duplicate a committed mutation.

## Findings

- `rules/api-error-standard.md` §3.1 requires HTTP 503 plus `Retry-After` for an idempotency-protected
  operation and HTTP 500 without retry guidance otherwise.
- The GraphQL carrier rule says transport status follows GraphQL over HTTP and execution errors use
  `errors[].extensions.type`.
- `design-graphql` and `generate-graphql-code` only say to preserve idempotency/reconcile semantics;
  neither defines the GraphQL status/header/extensions mapping.
- The apparent contradiction is not resolved by a protocol-specific table or executable assertion.

Locations:

- `rules/api-error-standard.md:98`
- `rules/api-error-standard.md:178`
- `rules/graphql-contract-fidelity.md:46`
- `skills/design-graphql/SKILL.md:123`
- `skills/generate-graphql-code/SKILL.md:85`

## Proposed Solutions

### Option 1: Add a GraphQL-specific mapping table

Define separately for parse/validation/transport failures and execution failures: HTTP status,
headers, `extensions.type`, retryability, retry delay, idempotency-key reuse, transaction ID handling,
and reconciliation guidance.

- Pros: deterministic generation and tests; preserves partial-data semantics explicitly.
- Cons: must be checked against the selected GraphQL-over-HTTP media type/version.
- Effort: Medium.
- Risk: Low after official-spec verification.

### Option 2: Ban this exception from GraphQL mutations

Expose affected commands through REST only.

- Pros: reuses the established contract.
- Cons: unnecessarily restricts GraphQL and hybrid designs.
- Effort: Small.
- Risk: Medium.

## Recommended Action

Use Option 1, grounded in the selected Spring GraphQL/GraphQL-over-HTTP version, and generate contract
tests for both idempotency-protected and unprotected mutations.

## Technical Details

The design must never expose an internal transaction ID to unauthorized callers; if an opaque
reconciliation identifier is needed, specify its authorization and lifetime. The implementation must
not blindly retry an indeterminate commit.

## Acceptance Criteria

- [x] A GraphQL-specific unknown-status table defines status, headers, and error extensions.
- [x] Protected mutations instruct retry with the same idempotency key only.
- [x] Unprotected mutations instruct reconciliation and never advertise retry.
- [x] Partial-data and transport-error behavior are unambiguous.
- [x] Generated tests cover both branches and reject generic exception handling.

## Work Log

### 2026-08-10 - Review finding recorded

**By:** Codex

**Actions:** Traced the error contract from ScalarDB exception mapping through the GraphQL carrier.

**Learnings:** Sharing problem-type URIs is insufficient unless protocol-specific recovery semantics
are also specified.

### 2026-08-10 - Resolved

**By:** Codex

**Actions:** Added a GraphQL execution override grounded in the GraphQL-over-HTTP and Spring
transport behavior, including mutually exclusive retry/reconcile extensions and transaction-ID
non-disclosure; propagated it into design and generation skills.

**Verification:** `python3 tools/graphql_skills.test.py` passed.

## Resources

- Review target: `b453885`
- `rules/api-error-standard.md`
