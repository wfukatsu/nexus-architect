---
description: |
  Generate a Spring for GraphQL API layer from approved SDL and resolver contracts: annotated
  controllers, input/output DTOs, mappers, tenant context, authorization, batch loading, exception
  resolution, query limits, observations and a field-coordinate contract map.
  /architect:generate-graphql-code [--service=<name>] [--out=<path>]
  [--confirm-versions|--no-confirm-versions] [--dry-run] [--auto] [--lang=en|ja] to invoke.
model: opus
user_invocable: true
disable-model-invocation: true
---

# Spring GraphQL Code Generation

## Desired Outcome

Generate the Spring for GraphQL boundary declared by the SDL and design artifacts, without adding a
field, argument, type, error or transport that the contract did not declare.

## Prerequisites

| File | Requirement |
|------|-------------|
| `reports/03_design/api-style-decisions.md` | Required; target surface is GraphQL or hybrid |
| `reports/03_design/api-specifications/graphql/{service}.graphqls` | Required contract |
| `reports/03_design/api-specifications/graphql/resolver-contracts.md` | Required bindings |
| `reports/03_design/api-specifications/graphql/authorization-matrix.md` | Required controls |
| `reports/03_design/api-specifications/graphql/batch-loading-plan.md` | Required loading plan |
| `reports/03_design/api-specifications/graphql/query-governance.md` | Required limits |
| `reports/03_design/api-specifications/graphql/transport-design.md` | Required execution model |
| `reports/06_implementation/api-layer-spec.md` | Required implementation boundary |
| `reports/03_design/api-specifications/problem-types.md` | Required shared error registry |

Stop on any gap. Do not infer a permissive authorization rule, transaction, nullability decision,
query limit, DTO field, or exception mapping.

## Package Ownership

| Package | Owner |
|---------|-------|
| `…/api/graphql/` | This skill: controllers, GraphQL DTOs/mappers, interceptors, errors, configuration |
| `…/application/` | This skill emits interfaces and calls; domain/data generator owns implementations |
| `…/domain/`, `…/infrastructure/` | ScalarDB or ordinary data-layer generator |

Never import a repository, persistence entity, or ScalarDB type from a GraphQL controller. In a
hybrid service, REST and GraphQL may share application services but do not silently share wire DTOs.

## Version Resolution

Read the existing Spring Boot BOM or parent first. Resolve a new Boot/plugin/Java pin and every
explicit dependency from its registry per @rules/dependency-versions.md. Normally add
`spring-boot-starter-graphql` without a Spring GraphQL version and let Boot manage it. Record the
resolved set in `work/version-decisions.json` and apply the configured confirmation policy.

For ScalarDB, pin product, version and edition through @rules/okf-knowledge-bundle.md before
generating any API signature, exception handling, or configuration.

## Generation Rules

### Schema and handler binding

- Copy the approved SDL to `src/main/resources/graphql/` without semantic changes.
- Generate one annotated method per resolver-bound field coordinate using `@QueryMapping`,
  `@MutationMapping`, `@SubscriptionMapping`, `@SchemaMapping`, or `@BatchMapping` as designed.
- Name explicit `@Argument("name")` values; do not rely on compiler parameter metadata.
- Generate dedicated input/output types and explicit mappers with exactly the SDL fields.
- Derive Bean Validation from declared constraints and validate inputs at the handler boundary.

### Security and tenant context

- Generate the designed Spring Security endpoint/transport policy and enable method security.
- Enforce scope/role and ownership at the declared controller or application-service point.
- Populate GraphQL context through `WebGraphQlInterceptor` only after validating authenticated
  claims or server-managed membership. Never trust a tenant header by itself.
- Carry the tenant predicate into repository/application-service calls.

### Data loading and transactions

- Generate `@BatchMapping` or DataLoader registration exactly as the batch plan declares.
- Keep batch keys/caches within the request and authorization partition; set maximum batch sizes.
- Delegate transaction, rollback and retry to application services. Do not wrap a blocking call in
  `Mono` and call it non-blocking.
- Do not create a request-wide transaction around multiple top-level mutations.

### Errors and resource governance

- Generate `DataFetcherExceptionResolver` or `@GraphQlExceptionHandler` mappings using the shared
  problem type URIs in `errors[].extensions.type`.
- Give `UnknownTransactionStatusException` its own mapping and preserve the designed retry/reconcile
  guidance. For an execution error, use HTTP 200 and the GraphQL response envelope: an
  idempotency-protected operation sets `extensions.retryable: true`, `retry_after_ms`, and
  `idempotency_key_reuse: "required"`; an unprotected operation sets `retryable: false` and
  `reconcile_required: true` with no retry delay. Never leak exception messages or raw ScalarDB
  transaction identifiers. Apply the GraphQL override in @rules/api-error-standard.md.
- Generate version-compatible GraphQL Java instrumentation/configuration for depth, complexity and
  other budgets. Look up exact class names for the managed GraphQL Java version; do not copy them
  from examples when the target version differs.
- Configure production GraphiQL, introspection, schema printer, CORS and WebSocket controls exactly
  as the design declares.

### Observability

Use Micrometer Observation when configured. Record low-cardinality operation metadata and safe
identifiers. Do not log raw GraphQL documents or variables by default.

## Contract Map

Write `reports/06_implementation/api-contract-map.{md,json}` last. Extend the existing map, preserve
other protocol entries, and never discard REST entries. Every GraphQL entry uses this shape:

```json
{
  "protocol": "graphql",
  "operation_id": "Mutation.createCustomer",
  "spec_file": "reports/03_design/api-specifications/graphql/customer.graphqls",
  "parent_type": "Mutation",
  "field": "createCustomer",
  "handler": "com.example.api.graphql.CustomerController#createCustomer",
  "input_type": "CreateCustomerInput",
  "output_type": "Customer",
  "problem_types": ["validation-failed", "transaction-status-unknown"],
  "authorization": "scope:customer.write + tenant + ownership",
  "transaction": "TX-004",
  "traces_to": ["FR-012"]
}
```

Include `unmapped.spec_operations_without_handler` and
`unmapped.handlers_without_spec_operation`. Derive scope from the complete GraphQL controller and
runtime-wiring source tree; never claim coverage from generated files alone.

## Output

| File | Content |
|------|---------|
| `generated/{service}/src/main/resources/graphql/` | Approved SDL copied into the Spring Boot schema location |
| `generated/{service}/src/main/java/` | GraphQL API/controller, DTO, mapper, context, security, error, loading and governance code |
| `reports/06_implementation/api-contract-map.md` | Human-readable REST/GraphQL binding map |
| `reports/06_implementation/api-contract-map.json` | Machine-readable combined binding map |
| `reports/06_implementation/graphql-code-generation.md` | This run's inputs, generated inventory, version decisions, quality commands and exit codes; written only after all prior outputs succeed |

## Steps

1. Resolve inputs, source root, existing project conventions and package ownership.
2. Resolve/confirm dependency versions; under `--dry-run`, report without writing.
3. Validate SDL and all field-coordinate contracts before generation.
4. Generate resources, API types, controllers, mappers and application interfaces.
5. Generate security/context, loading, error, governance and observation configuration.
6. Generate unit and slice-test skeletons; leave full contract tests to
   `/architect:generate-contract-tests`.
7. Derive source inventory and write the combined contract map.
8. Run build and relevant tests, recording commands and exit codes.
9. Only after the map and checks succeed, write `graphql-code-generation.md` as this phase's unique
   completion evidence. A failed or interrupted run must not create it.

## Acceptance Criteria

- Every resolver-bound field coordinate has exactly one handler and no extra handler exists.
- Generated DTO fields, nullability and validation match the SDL/contract.
- Controllers depend only on API/application types.
- Authorization, tenant predicates, batch boundaries and transaction calls match the design.
- Error mappings reuse the problem registry and isolate unknown transaction status.
- Query limits and production tooling controls are executable configuration, not comments.
- Contract map coverage is derived from source and preserves other protocol entries.
- Build/test evidence is recorded; failures are not reported as success.
- The unique completion report describes this run and is absent when generation did not finish.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/architect:design-graphql` | Source contract |
| `/architect:design-implementation` | Source layer/application specification |
| `/architect:generate-scalardb-code` | Supplies domain, persistence and application implementations |
| `/architect:generate-contract-tests` | Generates GraphQlTester contract/security tests |
| `/architect:verify-implementation` | Independently derives and verifies bindings |
