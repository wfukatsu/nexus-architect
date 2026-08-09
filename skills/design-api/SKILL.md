---
description: |
  Generate REST/GraphQL/gRPC/AsyncAPI specifications as the project's single, verifiable API contract —
  named schemas, every status code declared, RFC 9457 error responses, and per-operation authorization,
  idempotency and timeout obligations.
  /architect:design-api to invoke. Requires design-microservices output as a prerequisite.
model: opus
user_invocable: true
---

# API Design

## Desired Outcome

Design the API surface for inter-service and client-facing communication, as specification files that
downstream skills can generate code from and verify code against:

- REST API — OpenAPI 3.1 (or 3.0 where a toolchain requires it) specification per service
- GraphQL schema (as needed)
- gRPC protobuf definitions (inter-service communication)
- AsyncAPI (event-driven communication)
- A problem type registry — the enumerable set of error kinds the API can return
- API Gateway design (routing, authentication, rate limiting)

The specification is the **contract**, not an illustration of one. @rules/api-contract-fidelity.md §1
governs the relationship between it and every downstream artifact: code may not exceed it, may not
contradict it, and changing behaviour means changing the specification first.

## Decision Criteria

### Protocol and surface
- Select protocol by service classification (Process -> gRPC, Master -> REST, Integration -> AsyncAPI)
- API versioning strategy, and what counts as a breaking change (@rules/api-contract-fidelity.md §8)
- One project-wide convention for pagination, sorting and filtering — decided here, once

### Transaction-shaped operations
The transaction design is an **input**, not a downstream concern. Each operation is placed against it:
- Which operations sit inside one ACID transaction, which participate in a saga, which are local
- For 2PC surfaces, the participant operations (prepare / validate / commit / abort) are contract
  operations like any other and get the same treatment
- Every non-idempotent operation that a client may retry — anything that creates or moves money,
  stock, or state — declares an `Idempotency-Key` obligation (@rules/api-error-standard.md §5)
- A per-operation timeout and retry budget, consistent with the SLOs in `reports/04_quality/sla.md`
  when the product pipeline supplied them

### Authorization
- Authentication scheme per operation (OAuth2/OIDC), and the **authorization rule per operation**:
  the role/scope required, plus the object-level ownership predicate where one applies
- An operation whose authorization is undeclared is read downstream as public. Decide it here — this
  is the input to the BOLA/BFLA review, and the most common source of API vulnerabilities

### Errors
- Error responses are RFC 9457 Problem Details, per @rules/api-error-standard.md. No second error
  envelope anywhere in the project
- The problem type registry is allocated here and every error response references a registered `type`

## Knowledge Grounding

For a ScalarDB project, the transaction mechanism an operation depends on (shared cluster, Global
Transaction API, application-driven 2PC, Saga) is resolved against the project's pinned release per
@rules/okf-knowledge-bundle.md before it is written into the contract — the available mechanisms
differ by version and edition, and an operation designed around one the project cannot run is a
contract that cannot be implemented.

## Contract Verifiability (mandatory)

Every operation this skill emits satisfies @rules/api-contract-fidelity.md §3. Restated as the
checklist to apply before writing each specification file:

- [ ] `operationId` on every operation — `camelCase` verb-noun, unique project-wide, naming the
      business action (§2)
- [ ] Every request and response schema is a **named** `components/schemas` entry, never inline
- [ ] Every response status code declared, success **and** error, each with a schema
- [ ] Error responses use `application/problem+json` and a registered `type`
- [ ] Required vs optional decided for every property; `nullable` used deliberately
- [ ] Constraints in the schema (`minLength`, `maximum`, `pattern`, `enum`, `format`) — not in prose
- [ ] At least one success example and one error example per operation
- [ ] `security` declared per operation, with the role/scope and ownership predicate recorded
- [ ] `Idempotency-Key` parameter declared where §5 of the error standard requires it

These are not style preferences: each one is what makes a specific downstream check possible.
`generate-api-code` generates DTO names from schema names and Bean Validation from schema
constraints; `generate-contract-tests` uses the examples as fixtures; `verify-implementation` cannot
report a status-code break the contract never declared.

## Open Questions

Where an operation's authorization rule, idempotency obligation, timeout budget, or consistency
placement cannot be resolved from the inputs, ask the user per @rules/open-questions.md rather than
writing a permissive default. A silently-public operation and a silently-unbounded timeout are both
defects that surface much later and much more expensively.

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/03_design/target-architecture.md | Required | /architect:design-microservices |
| reports/03_design/scalardb-transaction.md | Required when scalardb_enabled | /architect:design-scalardb — which operations sit in one transaction, which are saga steps, which are 2PC participants |
| reports/03_design/data-layer-design.md | Required when scalardb_disabled | /architect:design-data-layer |
| reports/04_quality/sla.md | Optional | /product:design-sla — per-operation timeout and retry budgets derive from the SLOs (`SLO-`) |
| reports/03_domain/api-design.md | Optional | /product:design-api — when present, use the logical API-Led surface (`API-` System/Process/Experience layers) as the starting inventory to be made physical (protocols, specs), keeping `API-` ID traceability (@docs/design.md §1.3) |

## Output

| File | Content |
|------|---------|
| `reports/03_design/api-specifications/openapi/` | REST API specifications — one per service |
| `reports/03_design/api-specifications/graphql/` | GraphQL schemas |
| `reports/03_design/api-specifications/grpc/` | Protobuf definitions |
| `reports/03_design/api-specifications/asyncapi/` | Event specifications |
| `reports/03_design/api-specifications/problem-types.md` | Problem type registry (@rules/api-error-standard.md §2) — every error kind, its `type` URI, status, and whether retry is safe |
| `reports/03_design/api-specifications/operation-contracts.md` | Per-operation table: `operationId`, authorization rule, idempotency obligation, timeout/retry budget, transaction placement, traced requirement IDs |
| `reports/03_design/api-gateway-design.md` | Gateway design — routing, authentication, rate limiting |

`operation-contracts.md` is what `generate-api-code` and `verify-implementation` join against; it is
the human-readable half of the contract map they later produce (@rules/api-contract-fidelity.md §4).

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).
Specification files themselves — schema names, `operationId`s, enum values — stay in English regardless.

## Acceptance Criteria

- Every operation passes the Contract Verifiability checklist above
- Every error response references a `type` that has a row in `problem-types.md`, and every row in
  `problem-types.md` appears in at least one operation
- Every operation in `operation-contracts.md` has a declared authorization rule — none left blank
- Every operation is placed against the transaction design (one transaction / saga step / 2PC
  participant / local), and no operation contradicts that design
- Every ScalarDB exception kind reachable from an operation has a mapped problem type
  (@rules/api-error-standard.md §3), including the `transaction-status-unknown` branch (§3.1)
- No second error envelope exists anywhere in the specifications

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-microservices | Input source |
| /architect:design-scalardb | Input source — transaction placement per operation |
| /architect:design-implementation | Downstream — turns the contract into the API layer specification |
| /architect:generate-api-code | Downstream — generates the API layer bound to this contract |
| /architect:generate-contract-tests | Downstream — turns this contract into executable tests |
| /architect:verify-implementation | Downstream — verifies code against this contract |
| /architect:review-consistency | Review target |
