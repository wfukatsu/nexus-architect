---
description: |
  Design authentication, authorization, secrets management, network security, and the tenant isolation
  model, mapped to OWASP API Security Top 10.
  Invoked via /architect:design-security.
model: sonnet
user_invocable: true
---

# Security Design

## Desired Outcome

- Authentication infrastructure design (OAuth2/OIDC, inter-service mTLS)
- Authorization model (RBAC/ABAC, policy engine) — including **object-level** authorization, not only
  role-level
- Tenant isolation model (see below)
- Secrets management (Vault/KMS, rotation strategy)
- Network security (zero trust, segmentation)
- Data classification — which fields are confidential, and what may appear in an API response, a log,
  or a Problem Details `detail`
- Audit log design (who, what, when)
- Compliance checklist

## Authorization: role-level and object-level

A role check answers "may this kind of caller do this kind of thing". It does not answer "may *this*
caller act on *this* object" — and that second question is the single most common API vulnerability
(OWASP API1, BOLA). The design must therefore state, for every protected resource:

| Element | Content |
|---------|---------|
| Ownership predicate | What makes an object the caller's — the field, the claim it is compared to, and where the comparison happens |
| Enforcement point | Which layer evaluates it. A predicate the design leaves to "the service" is a predicate nobody implements |
| Existence disclosure | Whether an unauthorized caller may learn the object exists. Where existence is confidential the contracted response is **404, not 403** (@rules/api-error-standard.md §4) |
| Function-level rules | Which roles reach which operations (OWASP API5, BFLA) — administrative operations enumerated explicitly rather than assumed unreachable |

Every rule here binds an `operationId` in `reports/03_design/api-specifications/operation-contracts.md`.
An operation with no rule is read downstream as public; if that is the intent, say so explicitly.

## Tenant Isolation

For a multi-tenant system, state the isolation model concretely enough to verify:

- Where `tenant_id` (or equivalent) originates — which token claim, never a request body or query parameter
- How it reaches the data layer, and whether it is part of the **partition key** for ScalarDB tables
- Whether any scan, index lookup, or analytics query can cross a tenant boundary, and what prevents it
- What happens to the isolation guarantee under 2PC, saga compensation, and batch/administrative paths

A tenant identifier the client can influence is a defect regardless of what checks follow it.

## OWASP API Security Top 10 Mapping

The design records how each risk is addressed, so the code-time review has a design baseline to check
against rather than a blank page. Detail in @rules/api-security-checks.md.

| Risk | What the design must state |
|------|----------------------------|
| API1 Broken Object Level Authorization | The ownership predicate and enforcement point per resource |
| API2 Broken Authentication | Token issuance/validation, expiry, revocation, and the Gateway + service double-validation stance |
| API3 Broken Object Property Level Authorization | Which properties are writable per role (mass assignment) and which are readable (excessive data exposure) |
| API4 Unrestricted Resource Consumption | Rate limits, page-size caps, payload-size caps, timeouts, and per-operation cost limits |
| API5 Broken Function Level Authorization | Role-to-operation matrix, with administrative operations enumerated |
| API6 Unrestricted Access to Sensitive Business Flows | Which business flows need abuse protection beyond authentication, and what provides it |
| API7 SSRF | Every place the system fetches a caller-influenced URL, and the allowlist that bounds it |
| API8 Security Misconfiguration | TLS/mTLS posture, CORS policy, error verbosity, default-deny stance |
| API9 Improper Inventory Management | How the API inventory stays current, and how non-production and deprecated versions are prevented from being reachable |
| API10 Unsafe Consumption of Third-Party APIs | Which upstreams are trusted, what is validated on the way back in, and the failure mode |

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/03_design/api-specifications/ | Recommended | /architect:design-api — the operations the authorization rules bind to |
| reports/03_design/target-architecture.md | Recommended | /architect:design-microservices |

## Output

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

| File | Content |
|------|---------|
| `reports/08_infrastructure/security-design.md` | Overall security design, including the authorization model, tenant isolation model, data classification, and the OWASP API Security Top 10 mapping |

## Acceptance Criteria

- Every protected resource has an ownership predicate with a named enforcement point
- Every operation in `operation-contracts.md` is covered by a role-level rule, or is explicitly declared public
- For a multi-tenant system, the tenant identifier's origin is a token claim and its path to the data layer is stated
- Every OWASP API Security Top 10 row is addressed or explicitly marked not-applicable with a reason
- Field-level data classification exists and states what may appear in a response, a log, and a Problem Details `detail`

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:investigate-security | Input source (vulnerability information from existing systems) |
| /architect:design-api | Input source — the operations the rules bind to; output consumer for per-operation `security` |
| /architect:review-api-security | Downstream — checks the design, and later the code, against this baseline |
| /architect:design-infrastructure | Related |
