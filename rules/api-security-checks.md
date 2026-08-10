---
description: OWASP API Security Top 10 (2023) as concrete design-time and code-time checks, with the ScalarDB and multi-tenant specifics. Applies when reviewing an API design or API-layer code.
---

# API Security Checks

Applies to `review-api-security` (both modes), `verify-implementation`, `review-issue`, and to any
skill emitting API-layer code. The design-side baseline is `reports/08_infrastructure/security-design.md`
(`/architect:design-security`); this file is what turns that baseline into findings.

For GraphQL surfaces, apply @rules/graphql-security-checks.md as an additional protocol-specific
layer; the general OWASP API checks still apply.

**The premise: a secure design is not a secure implementation.** Every check below has a *design*
question and a *code* question, and they fail independently. A project can hold a correct
Zero-Trust design document and ship a controller that trusts a path parameter.

## Severity

| Severity | Meaning |
|----------|---------|
| **critical** | Exploitable now, by a caller the system already lets in — cross-tenant read/write, missing object-level authorization on a state-changing operation, authentication bypass |
| **major** | Exploitable given a plausible second condition, or a control that exists but is incomplete — one unprotected operation among many, a limit set too high to bound anything |
| **minor** | Defense-in-depth gap with no direct path to exploitation |
| **info** | Hardening suggestion |

Findings carry the `ASEC-` prefix.

## API1 — Broken Object Level Authorization (BOLA)

The single most common API vulnerability, and the one generated code produces most reliably: the
handler validates the *shape* of `orderId` and never asks whether it is the caller's order.

| | Question |
|---|---|
| Design | Does every resource have an ownership predicate with a named enforcement point (`security-design.md`)? |
| Code | For **every** operation taking a resource identifier: is the predicate evaluated against a claim from the **verified token**, before the object is read back to the caller and before any mutation? |

Findings:

- An identifier taken from the path, query, or body and used to load an object with no ownership
  check — **critical** when the operation mutates or returns the object.
- An ownership check performed *after* the response is assembled, or only in the happy path.
- A check comparing against a value the client supplied (a `tenant_id` body field, an
  `X-User-Id` header) rather than a token claim — this is not a check.
- A batch or list operation that filters by a caller-supplied identifier rather than scoping to the
  caller's claim.
- Existence disclosure: returning 403 where the design classified existence as confidential. The
  contracted response is 404 (@rules/api-error-standard.md §4).

## API2 — Broken Authentication

| | Question |
|---|---|
| Design | Token issuance, expiry, revocation, and whether the service re-validates independently of the Gateway |
| Code | Is the token signature, issuer, audience, and expiry verified **in the service**, not assumed because the Gateway is upstream? |

Findings: unverified JWT decoding (`decode` without `verify`), `none` algorithm accepted, missing
`aud`/`iss` checks, no expiry check, secrets or keys hard-coded, an authentication filter whose
matcher leaves paths uncovered, and — a frequent generated-code defect — a permissive `permitAll()`
fallback that catches everything the explicit rules missed.

## API3 — Broken Object Property Level Authorization

Two failure directions from one root cause, and both are contract questions as much as security ones.

**Mass assignment (write side).** Binding a request body onto a domain object or persistence entity
lets a caller set fields the contract never exposed — `role`, `status`, `price`, `tenantId`.

- Request DTO is the entity, or the mapper copies fields reflectively/wholesale — **critical** when
  any privileged field is reachable.
- A field writable by the mapper that the OpenAPI request schema does not declare
  (@rules/api-contract-fidelity.md §5.4).

**Excessive data exposure (read side).** Returning the domain object serializes whatever it holds
now — and whatever it gains later.

- Response DTO is the entity, or the handler returns the domain object directly — **major**, rising
  to **critical** when a field the data classification marks confidential is reachable.
- A response property the OpenAPI response schema does not declare.
- A field the security design classified confidential appearing in a response, a log line, or a
  Problem Details `detail` (@rules/api-error-standard.md §4).

## API4 — Unrestricted Resource Consumption

| Check | Finding when |
|-------|--------------|
| Page size | No maximum, or a maximum the caller can exceed. An unbounded `limit` reaching a ScalarDB `Scan` is **major** |
| Payload size | No request body size limit |
| Rate limits | Declared in the gateway design but absent from configuration, or applied per-IP where the threat is per-account |
| Timeouts | An outbound call with no timeout — every client, every retry |
| Retries | Retry with no bound, or retry without backoff, on a path a caller can trigger |
| Expensive operations | Analytics, export, and report operations with no cost bound |

## API5 — Broken Function Level Authorization (BFLA)

| | Question |
|---|---|
| Design | Is there a role-to-operation matrix, with administrative operations enumerated? |
| Code | Does each operation enforce the role/scope the contract declares? |

Findings: an administrative operation reachable by a standard role — **critical**; an operation whose
declared `security` has no corresponding check; authorization asserted by URL prefix convention
(`/admin/**`) with an operation living outside the prefix; a method-level annotation missing on one
handler in a class where its siblings have it.

## API6 — Unrestricted Access to Sensitive Business Flows

Authentication does not stop abuse of a flow that is *working as designed*: bulk reservation, coupon
redemption, account enumeration through a signup or password-reset path, scripted checkout.

Findings: a flow the design flagged as abuse-sensitive with no corresponding control (velocity limit,
proof-of-work, human verification, per-account quota); an enumeration oracle — differing responses or
timings for existing vs non-existing accounts.

## API7 — Server Side Request Forgery

Findings: any outbound request whose URL derives from caller input without an allowlist — **critical**
when the environment exposes a cloud metadata endpoint; a webhook or callback URL accepted without
validation; a redirect target taken from a parameter; an allowlist applied to the pre-redirect URL only.

## API8 — Security Misconfiguration

Findings: TLS not enforced, or mTLS declared between services and absent from configuration; CORS with
`*` alongside credentials, or reflecting the `Origin` header; stack traces or framework error pages
reachable (this is where @rules/api-error-standard.md §4 is enforced in code); debug, actuator, and management
endpoints exposed without authentication; default credentials; security headers absent where the
gateway design requires them.

## API9 — Improper Inventory Management

Findings: a reachable endpoint absent from the OpenAPI document — this is
@rules/api-contract-fidelity.md §6's `handlers_without_spec_operation`, and it is a security finding
as well as a contract one, because an undocumented endpoint is an unreviewed one; a deprecated API
version still routable with no sunset date; non-production endpoints reachable from production
configuration.

## API10 — Unsafe Consumption of Third-Party APIs

Findings: a response from an upstream service deserialized into a trusted type with no validation;
an upstream redirect followed blindly; an upstream failure that opens the operation rather than
closing it (fail-open); upstream data flowing into a response or a persisted record unvalidated.

## Injection and traversal

Not a separate 2023 category, still the most direct route in:

- **ScalarDB SQL / JDBC**: string-concatenated SQL, or caller input reaching a table or namespace
  name. Prepared statements with bound parameters are the only acceptable shape
  (@rules/scalardb-jdbc-patterns.md).
- **ScalarDB CRUD API**: caller input used as a partition or clustering key value is normal and safe;
  caller input used to *choose* a namespace, table, or index is not.
- **Path traversal**: a file path, object key, or resource name built from caller input without
  canonicalization and containment.
- **Log injection**: unescaped caller input written to logs.

## Multi-tenant isolation

Checked on every operation of a multi-tenant system, and the findings here are **critical** by default
because a single miss compromises every tenant:

1. `tenant_id` originates from a **verified token claim**. A tenant identifier read from a body,
   query parameter, or unverified header is a finding regardless of what checks follow it.
2. It reaches the data layer on every path — including administrative endpoints, batch jobs, saga
   compensations, and 2PC participant operations, which are the paths that get forgotten.
3. For ScalarDB, the tenant identifier is part of the **partition key** where the schema design says
   it is; a `Scan` whose range does not pin it can cross tenants.
4. Analytics and export paths are scoped too — a read-only cross-tenant leak is still a leak.
5. Cache keys, idempotency keys, and rate-limit keys include the tenant, so one tenant cannot read or
   exhaust another's.

## Transaction-boundary security

Specific to this toolkit, and invisible to a generic API scanner:

- An authorization check performed **outside** the transaction that then acts on data read **inside**
  it — the decision is made on state that may have changed. Check and act inside one transaction.
- A saga compensation that skips the authorization or tenant scoping its forward step applied.
- A 2PC participant operation reachable without the coordinator's authorization context.
- An idempotency record stored outside the business transaction, letting a replay bypass a check
  (@rules/api-error-standard.md §5).
- **A replay path that returns before the authorization check runs.** The early return on a stored
  idempotency record is the one code path with no ownership predicate on it unless the predicate was
  put there deliberately — and a record keyed only on `(tenant_id, key)` is readable by every caller
  in the tenant. **critical**: it is object-level authorization bypass (API1) reached through a
  header. Check the replay branch specifically; the non-replay branch being correct proves nothing
  about it.

## Evidence

Every finding names the file and line, the operation (`operationId`) it belongs to, the OWASP
category, the severity, and the concrete failure scenario — the request a caller would send and what
they would get back. A finding that cannot state that scenario is reported as `info`, not inflated.
