---
description: |
  Design a schema-first Spring for GraphQL API after /architect:design-api selects GraphQL or a
  hybrid surface. Produces SDL, resolver contracts, authorization, batching, query-governance and
  transport designs bound to application services and transaction boundaries.
  /architect:design-graphql [--service=<name>] [--lang=en|ja] to invoke.
model: opus
user_invocable: true
---

# Spring GraphQL Design

## Desired Outcome

Turn an approved GraphQL surface into an implementation-ready contract for Spring for GraphQL.
Keep GraphQL as the public/application boundary and keep persistence behind application services:

```text
transport -> Spring Security -> GraphQL controller -> application service -> repository -> database
```

Never select GraphQL merely because ScalarDB is selected. Distinguish the Spring application API
from ScalarDB's edition-gated native GraphQL interface per @rules/api-style-selection.md.

## Entry Condition

Read `reports/03_design/api-style-decisions.md`. Run only when at least one in-scope surface is
`graphql` or `hybrid`. Otherwise mark this conditional phase skipped with its reason.

If the decision artifact is absent, stop and run `/architect:design-api`; do not infer the API style
from an existing `.graphqls` file or from the database product.

## Prerequisites

| File | Requirement |
|------|-------------|
| `reports/03_design/api-style-decisions.md` | Required; selected surfaces and transport choices |
| `reports/03_design/target-architecture.md` | Required |
| `reports/03_design/api-specifications/operation-contracts.md` | Required; business operations, authorization and transaction placement |
| `reports/03_design/api-specifications/problem-types.md` | Required; shared error registry |
| `reports/03_design/scalardb-transaction.md` | Required when ScalarDB is enabled |
| `reports/03_design/data-layer-design.md` | Required when ScalarDB is disabled |
| `reports/01_analysis/actors-roles-permissions.md` | Required |
| `reports/04_quality/sla.md` | Recommended; timeout and availability targets |

Unknown authorization, transaction, tenant, query-budget, or transport decisions are not safe
defaults. Ask and record them through @rules/open-questions.md.

## Knowledge and Version Grounding

- For ScalarDB, pin product, release and edition before reading features. Use the version-pinned OKF
  bundle per @rules/okf-knowledge-bundle.md. Do not treat ScalarDB native GraphQL as a substitute for
  this Spring application boundary without an explicit exception decision.
- Select Spring Boot first and let its BOM manage Spring for GraphQL. Do not write a remembered
  Spring GraphQL version. Apply @rules/dependency-versions.md whenever an artifact pins a version.
- Recheck the target Spring GraphQL release line's official security notes before implementation.

## Steps

### 1. Fix the schema boundary

Design SDL schema-first. For each type and field:

- Decide nullability intentionally; do not use non-null merely to look strict.
- Use dedicated input types; never expose persistence entities as input or output contracts.
- Express validation constraints in SDL directives or the resolver contract where standard SDL
  cannot carry them, with one unambiguous mapping to Bean Validation.
- Define deprecation and additive evolution rules.
- Use cursor connections for large or mutable collections; define a stable logical sort key and
  signed/tamper-resistant cursor. Do not expose a database physical offset.

### 2. Bind every field coordinate

Use `<parentType>.<fieldName>` as the stable join key, for example `Query.customer`,
`Mutation.createCustomer`, or `Customer.orders`. Apply @rules/graphql-contract-fidelity.md.

For every coordinate record exactly one resolver, its input/output types, application-service
method, authorization rule, transaction ID, error types, timeout and requirement IDs. Separate
runtime client `operationName` from this implementation join key.

### 3. Design authorization and context

Record all applicable layers, not only endpoint authentication:

- transport authentication and allowed origins;
- Query/Mutation/Subscription scope or role;
- object ownership and tenant predicate;
- sensitive nested-field authorization;
- repository query predicate enforcing the authenticated tenant.

Headers such as `X-Tenant-ID` are hints, never authority. Bind the tenant from authenticated claims
or server-managed membership and reject a mismatch before data access. Ensure method security is
enabled; an annotation without its runtime enabler is not enforcement.

### 4. Design loading and database access

For every nested field that reaches storage, choose eager projection, `@BatchMapping`, or a
registered DataLoader. Specify the batch key, maximum batch size, one bulk repository operation,
ordering, missing-key behavior, error behavior, and cache scope.

DataLoader keys and caches must not cross tenant or principal authorization boundaries. Keep
controllers free of repository and ScalarDB types. Put transactions and retries in the application
service. Multiple top-level mutations execute serially but are not one implicit transaction.

### 5. Design transport and execution model

Use Spring MVC by default for synchronous database APIs, including ScalarDB. Select WebFlux only
for an established reactive stack or Subscription need and document how every blocking call is
isolated from the event loop. Enable WebSocket or RSocket only when required.

For subscriptions specify origin checks, connection authentication, credential expiry or
reauthentication, per-principal connection limits, backpressure, cancellation and cleanup.

### 6. Set query-governance budgets

Set numeric limits, traced to NFRs where possible, for depth, complexity/cost, aliases, batched
operations, document/input size, page size, execution timeout and subscription connections. Decide
persisted/allowlisted query policy. Apply @rules/graphql-security-checks.md.

Production GraphiQL, schema printer and introspection are explicit environment decisions, never
defaults. Record CORS and CSWSH controls for browser/WebSocket consumers.

### 7. Design errors and observations

Reuse the project's problem type registry. Execution errors carry its URI in
`errors[].extensions.type`; do not invent a second error taxonomy. Give
`UnknownTransactionStatusException` a dedicated branch consistent with idempotency and reconcile
semantics in @rules/api-error-standard.md.

Observe operation type/name, normalized document hash or persisted query ID, execution ID,
authenticated tenant/principal identifier, duration, complexity and error classification. Do not
log raw documents or variables by default; mask or allowlist recorded values.

## Output

Write reports in `options.output_language`; keep SDL identifiers in English.

| File | Content |
|------|---------|
| `reports/03_design/api-specifications/graphql/{service}.graphqls` | Schema contract |
| `reports/03_design/api-specifications/graphql/resolver-contracts.md` | Field coordinate to resolver/service/transaction/error/requirement map |
| `reports/03_design/api-specifications/graphql/authorization-matrix.md` | Transport, operation, object, row and field controls |
| `reports/03_design/api-specifications/graphql/batch-loading-plan.md` | Projection/DataLoader plan and tenant-safe cache policy |
| `reports/03_design/api-specifications/graphql/query-governance.md` | Numeric resource limits and production tooling policy |
| `reports/03_design/api-specifications/graphql/transport-design.md` | MVC/WebFlux and HTTP/WebSocket/RSocket decisions |

Validate every Markdown output with `hooks/validate-frontmatter.sh` and
`hooks/validate-mermaid.sh` before marking the phase complete.

## Acceptance Criteria

- Every SDL field coordinate has exactly one resolver contract or is explicitly framework-resolved.
- Every storage-backed nested field has a documented N+1 strategy.
- Every operation and protected nested field has authorization and tenant enforcement points.
- Every mutation maps to an explicit transaction boundary and idempotency decision.
- All query-governance limits are numeric or are tracked open questions.
- ScalarDB claims cite the pinned release and edition source.
- No controller is designed to call a repository or ScalarDB API directly.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/architect:design-api` | Selects GraphQL/hybrid and supplies common operation contracts |
| `/architect:design-implementation` | Consumes resolver and application-service bindings |
| `/architect:generate-graphql-code` | Generates the Spring API layer |
| `/architect:generate-contract-tests` | Generates executable GraphQL contract and security tests |
| `/architect:review-api-security` | Reviews the design against GraphQL-specific checks |
| `/architect:verify-implementation` | Verifies SDL, runtime wiring and source code |
