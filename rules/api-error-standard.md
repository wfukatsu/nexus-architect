---
description: API error representation standard — RFC 9457 Problem Details, the per-project problem type registry, and the ScalarDB exception to HTTP mapping. Applies when designing an API surface, generating API-layer code, or reviewing either.
---

# API Error Standard (RFC 9457 Problem Details)

Applies whenever a skill **designs, generates, or reviews an HTTP API surface**: `design-api`,
`design-implementation`, `generate-api-code`, `generate-contract-tests`, `verify-implementation`,
`review-api-security`, and the implementation skills that write controllers.

One rule governs everything below: **an error is part of the contract, not an afterthought.** A
response the OpenAPI document does not describe is a contract break even when it carries a
plausible-looking JSON body.

## 1. The standard is RFC 9457

Every non-2xx response body is an RFC 9457 Problem Details object, served as
`Content-Type: application/problem+json`. RFC 9457 obsoletes RFC 7807; the media type and member
names are unchanged, so an existing 7807 implementation conforms — cite 9457 as the reference.

| Member | Required | Content |
|--------|----------|---------|
| `type` | yes | Absolute URI identifying the *problem kind*. Resolved from the project's problem type registry (§2) — never invented at the call site. `about:blank` only when the status code alone fully describes the problem |
| `title` | yes | Short, human-readable, **constant per `type`**. It does not vary with the occurrence |
| `status` | yes | The HTTP status code, duplicated in the body |
| `detail` | recommended | What went wrong *in this occurrence*, in the project's `output_language`. Safe for the caller to read — see §4 |
| `instance` | recommended | URI reference identifying this occurrence (the request path, or a URI naming the failed operation) |

Extension members are how everything else travels. Standardize these three across the project so
clients can rely on them:

| Extension member | When | Content |
|------------------|------|---------|
| `errors` | 400 / 422 validation failures | Array of `{ "pointer": "#/items/0/quantity", "detail": "..." }` — one entry per violated constraint, so a form can be annotated field by field |
| `trace_id` | always | The correlation/trace ID for the request, matching what the observability design (@rules or `reports/08_infrastructure/observability-design.md`) propagates. This is the only identifier support should ever need |
| `retry_after_ms` | retryable problems | Machine-readable companion to the `Retry-After` header. Present **only** when a retry is genuinely safe (§3) |

Never invent a second, parallel error envelope (`{"code": ..., "message": ...}`) alongside this.
Two error shapes in one API is a finding.

## 2. The problem type registry

`type` URIs must be **stable, unique, and enumerable**, because clients branch on them and contract
tests assert them. `design-api` therefore writes one registry per project:

`reports/03_design/api-specifications/problem-types.md`

One row per problem kind:

| `type` URI | `title` | HTTP status | Raised when | Retry safe? | Owning service(s) |
|------------|---------|-------------|-------------|-------------|-------------------|

Rules:

- **URI shape**: `https://{project-error-base}/problems/{kebab-case-slug}`. The base is decided once
  in `design-api` and recorded in the registry header. The URI is an identifier, not a promise of a
  live document — but if it does resolve, it must describe the problem kind, not the occurrence.
- **Allocate from the registry, never from the report you are writing.** Adding a `type` means
  adding the row first. This is the same discipline the Open Questions store and the traceability
  graph follow (@rules/open-questions.md §6, @docs/design.md §1.5) and for the same reason: two
  skills minting the same slug for different problems produces one identifier with two meanings.
- **Every registry row appears in the OpenAPI document** as a named error response, and every error
  response in the OpenAPI document has a registry row. `verify-implementation` checks both
  directions.
- A `type` is **never repurposed**. Retiring one means marking the row retired, not reusing the slug.

## 3. ScalarDB exception mapping

Authoritative for the API layer of a ScalarDB project. It extends
@rules/scalardb-exception-handling.md — that file governs what the *transaction* code does (catch
order, rollback, retry); this table governs what the *caller* sees. Where a project pins a ScalarDB
release whose documented retryability differs, the pinned OKF bundle wins
(@rules/okf-knowledge-bundle.md).

| ScalarDB exception | Status | `type` slug | Retry safe for the client? |
|--------------------|--------|-------------|----------------------------|
| `CrudConflictException`, `CommitConflictException`, `PreparationConflictException`, `ValidationConflictException` — **after the service's own retries are exhausted** | 409 | `transaction-conflict` | Yes — set `Retry-After` / `retry_after_ms` |
| `UnsatisfiedConditionException` where the condition came from a **client-supplied precondition** (`If-Match`, a version field) | 412 | `precondition-failed` | No — the client must re-read and re-decide |
| `UnsatisfiedConditionException` otherwise (server-side invariant not met) | 409 | `state-conflict` | No |
| `UnknownTransactionStatusException` | **§3.1 — has its own rule** | `transaction-status-unknown` | **No, unless idempotency-protected** |
| `TransactionNotFoundException` (2PC participant, expired or unknown transaction) | 404 | `transaction-not-found` | No — the coordinator aborts |
| `CrudException`, `CommitException`, `PreparationException`, `ValidationException` (non-conflict) | 500 | `transaction-failed` | No |
| `TransactionException` (unclassified) | 500 | `transaction-failed` | No |
| Connectivity / cluster unavailable | 503 | `service-unavailable` | Yes — set `Retry-After` |
| `IllegalStateException` from 2PC protocol misuse (commit before prepare, reusing a finished transaction) | 500 | `internal-error` | No |

The last row is easy to miss and the handler must cover it explicitly: 2PC protocol misuse throws an
**unchecked** `IllegalStateException`, not a `TransactionException`
(@rules/scalardb-2pc-patterns.md). A handler written as `catch (TransactionException e)` never sees
it, so it escapes as an unhandled 500 with a framework error page — which is also a §4 disclosure
problem. It is a server defect rather than a transaction outcome: map it to a generic internal error,
never to `transaction-failed`, and alert on it rather than filing it with the retryable family.

A conflict exception must **not** reach the API layer before the service has applied its own retry
policy. A 409 that a single retry would have cleared is an implementation defect, not an error
response — `verify-implementation` reports it as one.

### 3.1 `UnknownTransactionStatusException` is not a 500 and not a 503

The commit **may have succeeded**. Blind retry duplicates data; reporting plain failure tells the
caller something that may be false. The response therefore depends on whether the operation is
idempotency-protected (§5):

| The operation | Status | Body |
|---------------|--------|------|
| **Is** idempotency-key protected | 503 | `type: …/transaction-status-unknown`, `Retry-After` set, `retry_after_ms` set. Retrying with the **same** `Idempotency-Key` is safe and is the documented recovery — say so in `detail` |
| Is **not** idempotency-key protected | 500 | `type: …/transaction-status-unknown`, **no** `Retry-After`, **no** `retry_after_ms`. `detail` must state that the outcome is indeterminate and that the caller must reconcile rather than retry, naming the reconciliation endpoint or process |

Both carry the ScalarDB transaction ID as the `transaction_id` extension member and log it
server-side. Neither rolls the transaction back.

Read the ID from the accessor that is **not deprecated on the pinned release** — on ScalarDB 3.19
that is the inherited **`TransactionException#getTransactionId()`**: `getUnknownTransactionId()`
is `@Deprecated` there (part of the 3.19 deprecation of the application-driven 2PC surface,
@rules/scalardb-2pc-patterns.md) and returns the same value. On older releases the dedicated
`getUnknownTransactionId()` is the documented accessor. Verify against the pinned release before
generating the handler (@rules/okf-knowledge-bundle.md) — both compile and pass tests, so only the
version check catches the wrong choice.

This is the single most consequential row in this file. A generated `@RestControllerAdvice` that
folds `UnknownTransactionStatusException` into a generic 500 handler, or that maps it to a
`Retry-After`-bearing 503 on an unprotected operation, is a **blocker-severity** finding for
`verify-implementation` and `review-api-security`.

### 3.2 GraphQL execution override for unknown transaction status

Section 3.1 defines the REST/Problem Details carrier. When the same exception occurs after a
well-formed GraphQL mutation has entered execution, it is a **field execution error**, not a
transport or request error. Return a GraphQL response with HTTP 200 and put the registered
`transaction-status-unknown` URI in `errors[].extensions.type`; do not translate the REST 500/503
status into the HTTP status of this execution response. Parse, validation, authentication-before-
execution, malformed HTTP, and unsupported-media-type failures keep their distinct statuses under
the project's GraphQL-over-HTTP contract.

The execution-error extensions are fixed by idempotency protection:

| The mutation | Required extensions | Forbidden extensions/headers |
|--------------|---------------------|------------------------------|
| **Is** idempotency-key protected | `type`, `retryable: true`, numeric `retry_after_ms`, `idempotency_key_reuse: "required"`, `reconcile_required: false` | Do not echo the key; do not use HTTP `Retry-After` on the 200 response |
| Is **not** idempotency-key protected | `type`, `retryable: false`, `reconcile_required: true` and an opaque documented reconciliation reference or process | No `retry_after_ms`, no `idempotency_key_reuse`, no HTTP `Retry-After` |

The client message says the outcome is indeterminate. The protected branch permits only a retry
with the same idempotency key after the declared delay; the unprotected branch says reconcile and
do not retry. Log the ScalarDB transaction ID against the execution/trace ID, but do not expose the
raw transaction ID in GraphQL extensions by default. An explicitly designed, authorization-checked
reconciliation API may return its own opaque reference. This GraphQL exception to the §3.1
`transaction_id` carrier prevents an internal database identifier from becoming a field-level API.

## 4. What `detail` may never contain

`detail` is attacker-readable. Excluding these is an OWASP API Security concern
(@rules/api-security-checks.md), not a style preference:

- Stack traces, exception class names, framework internals
- SQL, ScalarDB namespace/table names, partition key values
- Internal hostnames, ports, IP addresses, file paths, cloud resource IDs
- Any value from another tenant, or any field the security design classified as confidential
- Whether a *resource* exists, when existence itself is confidential — an object the caller is not
  authorized to see is **404 `not-found`, not 403** (OWASP API1/BOLA). 403 is correct only when the
  caller may know the resource exists but not act on it

The operator-facing detail goes to the log, joined to the response by `trace_id`. `detail` says what
the caller can act on; the log says what the operator needs.

## 5. Idempotency and its errors

Any operation the API design marks non-idempotent but retryable — every `POST` that creates or moves
money, stock, or state — accepts an `Idempotency-Key` request header, and `design-api` records that
obligation per operation. The error surface that comes with it:

| Situation | Status | `type` slug |
|-----------|--------|-------------|
| Same key, same request body, original completed | Replay the **original** response verbatim (2xx), with `Idempotency-Replayed: true` | — |
| Same key, **different** request body | 422 | `idempotency-key-reuse` |
| Same key, original still in flight | 409 | `idempotency-key-in-flight` — retryable, set `Retry-After` |
| Key required by the contract but absent | 400 | `idempotency-key-required` |

The stored idempotency record and the business write must land in the **same** ScalarDB transaction.
A record committed separately reintroduces exactly the duplicate the key exists to prevent, and it is
what makes the §3.1 503 path safe.

### The replay path is an authorization path

A replay returns the original response **without re-running the operation** — which means it returns
it without re-running the operation's authorization unless you make it. Two rules, both violated by
the obvious implementation:

1. **Scope the record to the caller, not only to the tenant.** A record keyed on
   `(tenant_id, idempotency_key)` is readable by every caller in the tenant. Key it on the
   principal too, or store the principal in the record and compare.
2. **Evaluate the ownership predicate before returning a replay**, exactly as the original request
   did. The natural shape — check for a stored record first, return early if found — puts the replay
   *ahead* of the ownership read, so the early return is the one path with no authorization on it.

Get this wrong and the key becomes an object-level authorization bypass (@rules/api-security-checks.md
API1): a caller who obtains another customer's key and order ID reads back that order's outcome. It
is not a hypothetical — an independent review of this pipeline's own reference implementation found
exactly this, in code whose non-replay path checked ownership correctly.

## 6. Non-HTTP protocols

The same problem kinds carry across protocols; only the envelope changes. Use one mapping per
project and record it in the registry header:

| Protocol | Carrier |
|----------|---------|
| gRPC | `google.rpc.Status` with the registry `type` URI in an `ErrorInfo.reason`/`domain` pair; status code per the gRPC mapping recorded in the registry |
| AsyncAPI / events | A `problem` object with the same members inside the message envelope; the `type` URI is identical to the REST one |
| GraphQL execution error | `errors[].extensions.type` carries the registry URI; transport status follows the GraphQL-over-HTTP contract. Parse/validation/transport failures and field execution failures remain distinct |

A problem kind that exists on REST and on gRPC uses **one** registry row and one `type` URI. Two
rows for the same problem is a finding.

## 7. Verification hooks

These are the assertions the downstream skills implement, listed here so all of them agree:

1. Every non-2xx response in the OpenAPI document declares `application/problem+json` with a schema
   derived from §1.
2. Every `type` value appearing in code or in the OpenAPI document has a registry row (§2).
3. Every registry row appears in at least one operation's responses.
4. The generated exception handler covers every row in §3, with §3.1 handled by its own branch.
5. No error envelope other than Problem Details appears in any response schema.
6. No `detail` string in the generated code interpolates a §4-prohibited value.
7. GraphQL unknown-status execution tests assert §3.2's HTTP 200 envelope and both mutually
   exclusive extension sets, including absence of raw transaction IDs and invalid retry guidance.

`generate-contract-tests` emits 1–5 and 7 as executable tests; `verify-implementation` checks all
seven against the code that exists.
