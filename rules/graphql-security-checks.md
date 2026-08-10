---
description: GraphQL-specific design and code security checks for authorization, tenants, query denial of service, batching, subscriptions, tooling, errors, and observations. Applies alongside the general API security rules.
---

# GraphQL Security Checks

Apply @rules/api-security-checks.md first, then these GraphQL-specific checks in design and code
modes. A documented control and an executable control pass independently.

## Severity

| Finding | Default severity |
|---------|------------------|
| Cross-tenant/object read or write through root/nested field or DataLoader cache | critical |
| Missing authorization on a state-changing mutation | critical |
| Tenant accepted from an unverified header | critical |
| No depth/complexity/page/batch limits on an exposed API | major |
| Blocking database work on an event loop | major |
| Production GraphiQL/schema printer unintentionally enabled | major |
| Introspection enabled contrary to the recorded policy | major |
| Raw document, variables, token or PII logged | major |
| Missing WebSocket origin/auth/connection controls | major |

## Authorization and tenants

- Endpoint authentication is not operation or field authorization.
- Verify role/scope plus ownership and authenticated tenant predicates at the declared enforcement
  point, including nested PII fields and replay/cache paths.
- Verify Spring method security is enabled; annotations alone do not enforce anything.
- Verify repository reads/writes include the tenant predicate rather than filtering after access.
- Partition DataLoader keys and caches by every authorization dimension that can change visibility.

## Query denial of service

Require numeric limits and executable enforcement for depth, weighted complexity, aliases,
batched operations, variables/document/input size, page size, execution timeout and concurrent
subscriptions. Verify expensive fields have meaningful weights and batch loaders have maximum size.
Gateway rate limiting alone does not limit the cost of one GraphQL request.

## Mutation and transaction safety

- Do not assume multiple top-level mutations share a transaction.
- Require idempotency for retryable state-changing operations and store the idempotency record in
  the business transaction.
- Give `UnknownTransactionStatusException` a dedicated reconcile-don't-blindly-retry path.
- Keep saga/TCC orchestration in application services, not resolvers.

## Browser, WebSocket and tooling

Verify CORS and allowed origins, CSRF/CSWSH posture, WebSocket authentication at connection setup,
credential expiry/reauthentication, per-principal connection limits, cancellation and cleanup.
GraphiQL, schema printer and introspection must match the environment policy. Treat persisted or
allowlisted queries as defense in depth, not replacement authorization.

## Errors and observations

Errors use registered problem type URIs without internal messages, identifiers, SQL, stack traces or
authorization detail. Logs/metrics use operation name/type, persisted query ID or normalized hash,
execution ID, safe tenant/principal identifiers, duration, complexity and classification. Raw
documents and variables are denied by default and values are allowlisted or masked.

## Required tests

Cover unauthenticated, insufficient scope, other tenant, owner, administrator, nested sensitive
field, alias explosion, excessive depth/complexity, oversized page/batch/document, invalid
WebSocket origin, expired subscription authentication and cancellation cleanup.
