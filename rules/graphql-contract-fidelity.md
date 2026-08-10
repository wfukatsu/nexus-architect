---
description: GraphQL SDL contract fidelity, field-coordinate resolver binding, schema evolution, error carrier, contract-map shape, and drift protocol. Applies to GraphQL design, generation, tests, review, and verification.
---

# GraphQL Contract Fidelity

## Contract and join key

The `.graphqls`/`.gqls` files under `reports/03_design/api-specifications/graphql/` are the GraphQL
contract. Prose explains them but cannot add fields or soften nullability.

Use the GraphQL field coordinate `<parentType>.<fieldName>` as the stable implementation join key.
`Query.customer`, `Mutation.createCustomer`, and `Customer.orders` each bind to exactly one resolver
or an explicitly declared framework/default resolver. Client `operationName` is an observation and
persisted-document identifier, not the resolver join key.

## Verifiable schema requirements

- Declare nullability deliberately for every field, list and list element.
- Use named input and output types; never bind a persistence/domain entity as a wire input.
- Record validation constraints in a form that maps unambiguously to runtime validation.
- Declare authorization, tenant/ownership predicate, transaction, timeout, idempotency and problem
  types for every root field and protected nested field.
- Give every storage-backed nested field a projection or batch-loading contract.
- Define pagination ordering, cursor contents/integrity and maximum page size.
- Define depth, complexity, aliases, batched operations, document/input size and timeout budgets.

## Code constraints

Code may not add a schema field, argument, input property, enum value, error kind or transport that
the contract does not declare. It may not weaken nullability/validation or return an internal field.
Change the SDL and resolver contracts first, then code and the contract map.

Controllers call application services, never repositories or ScalarDB clients. REST and GraphQL
wire DTOs remain distinct in a hybrid API unless the contract proves exact semantic identity.

## Contract map

Add `protocol: graphql`, `parent_type`, `field`, input/output types and handler to the shared
`reports/06_implementation/api-contract-map.json`. Preserve entries for other protocols. Old map
entries without `protocol` are interpreted as REST for backward compatibility.

Both unmapped arrays remain mandatory. Verification derives resolver inventory from source/runtime
wiring and compares it with the SDL; it never trusts the map's claim by itself.

## Errors

Reuse `reports/03_design/api-specifications/problem-types.md`. GraphQL execution errors carry the
registry URI in `errors[].extensions.type`; transport errors follow the GraphQL-over-HTTP contract.
Do not create an ad-hoc error envelope. Keep partial-data semantics explicit and give unknown
transaction status its own idempotency-aware branch per @rules/api-error-standard.md.

## Evolution

Published schema changes are additive by default. Removing/renaming a field or enum, tightening
nullability/validation, changing an argument default, or changing error semantics is breaking.
Deprecate before removal and record the consumer migration window.

## Drift protocol

Report extra/missing resolvers, schema/type mismatches, runtime wiring not represented in the SDL,
stale test-resource SDL copies and unreachable error mappings. Never rewrite the contract to match
code during verification, and never delete code while only diagnosing drift.
