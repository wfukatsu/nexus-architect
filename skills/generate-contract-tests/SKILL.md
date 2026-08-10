---
description: |
  Turn the API contract into executable tests — OpenAPI request/response validation, GraphQlTester
  schema/resolver validation, Problem Details
  conformance, authorization and idempotency assertions, and ArchUnit layering rules — so contract
  breaks fail a build instead of surviving a review.
  /architect:generate-contract-tests [--service=<name>] [--out=<path>] [--stack=default|schemathesis|pact|archunit]
  [--confirm-versions|--no-confirm-versions] [--dry-run] [--auto] [--lang=en|ja] to invoke.
  Runs after generate-api-code (or after an item is implemented by hand).
model: sonnet
user_invocable: true
disable-model-invocation: true
---

# Contract Test Generation

GraphQL surfaces use `GraphQlTester` and schema inspection rather than an OpenAPI validator. Select
`ExecutionGraphQlServiceTester`, `WebGraphQlTester`, `HttpGraphQlTester`,
`WebSocketGraphQlTester`, or `RSocketGraphQlTester` from the approved transport design.

## Desired Outcome

Executable tests that hold the code to the contract. This is the difference between a contract that
is *documented* and one that is *enforced*: acceptance criteria in a skill file are instructions to a
model, and a model that drifts from them produces plausible code that reads fine. A failing assertion
does not read fine.

Generate, per service:

- **Contract validation tests** — every request and response the suite exercises validated in-process
  against the OpenAPI document
- **Problem Details conformance tests** — every registered problem type reachable, correctly shaped
- **Authorization tests** — unauthenticated, wrong role, and (where an ownership predicate applies)
  another principal's or another tenant's object
- **Idempotency tests** — replay, key reuse with a different body, missing required key
- **Indeterminate-commit tests** — the `UnknownTransactionStatusException` contract, which is the one
  most often generated wrong
- **ArchUnit rules** — the layering the API layer specification declares

## Stack

Per @rules/api-contract-fidelity.md §7, and read from `reports/07_test-specs/contract-test-specs.md`
where `generate-test-specs` recorded the selection:

| Tier | Stack | Default |
|------|-------|---------|
| Contract validation | `swagger-request-validator` (Atlassian) driven from `@WebMvcTest` / `@SpringBootTest` slices | **on** for a Spring service |
| Runtime fuzzing | Schemathesis against a running instance | opt-in |
| Consumer-driven | Pact | opt-in |
| Architecture | ArchUnit | opt-in, recommended wherever the API layer specification declares layering |

`--stack` overrides the recorded selection for one run. The default is not optional for a Spring
service — in-process validation of every exercised request and response is what makes the rest of the
suite meaningful. For a non-Spring or non-JVM service, use the framework's equivalent in-process
validator and record which one.

## Decision Criteria

- **Assert against the specification, not against the code.** A test whose expected values were read
  out of the implementation passes whatever the implementation does, which is the failure mode this
  skill exists to remove. Expected status codes, shapes, and problem types come from the OpenAPI
  document and the problem type registry.
- **Use the contract's own examples as fixtures.** They are in the specification for this reason
  (@rules/api-contract-fidelity.md §3). An operation with no example gets a shape test only, and the
  missing example is reported.
- **Never weaken a test to make it pass.** A generated test that fails is the intended outcome when
  the code is wrong; report the failure, do not relax the assertion or mark it disabled.
- **Cover the negative space.** A suite that only exercises declared success paths cannot detect an
  endpoint the contract does not declare — the undeclared-endpoint check comes from
  `api-contract-map.json`, and it is generated as an assertion, not left to review.

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/03_design/api-specifications/ | Required | /architect:design-api — the contract the tests assert against |
| reports/03_design/api-specifications/problem-types.md | Required | /architect:design-api |
| reports/06_implementation/api-contract-map.json | Required | /architect:generate-api-code or /architect:implement-backlog — what to test and where it lives |
| reports/07_test-specs/contract-test-specs.md | Required | /architect:generate-test-specs — the assertions and the stack selection |
| reports/06_implementation/api-layer-spec.md | Recommended | /architect:design-implementation — the layering ArchUnit encodes |
| reports/08_infrastructure/security-design.md | Recommended | /architect:design-security — the authorization rules the tests assert |

## Steps

1. **Resolve the stack and the output root** — the recorded selection, overridden by `--stack`;
   `--out`, else the service's `src/test/` under the contract map's `source_root`.
2. **Pin the contract into the test tree** — copy the specification to
   `src/test/resources/contract/openapi/<service>.yaml` and load it from the classpath. The design
   copy lives under `reports/`, which is git-ignored: a committed test that reads it there passes for
   its author and fails the CI contract stage on a fresh checkout
   (@rules/api-contract-fidelity.md §7).
3. **Generate the validation harness** — the OpenAPI validator wired into the test slice, so every
   request and response in the suite is checked without per-test boilerplate. Resolve the validator
   coordinate per @rules/api-contract-fidelity.md §7: the module is `-mockmvc` (there is no
   `-spring-mvc` artifact), and its JDK baseline must be at or below the project's target release —
   the `3.x` line is Java 21 and will not compile into a Java 17 service.
   For GraphQL, copy the approved SDL to test resources, configure the selected `GraphQlTester`,
   inspect the executable schema, and derive resolver inventory independently. Test success shape,
   nullability, validation, registered `errors[].extensions.type`, authorization, tenant isolation,
   N+1 query count, query limits, and subscription controls per @rules/graphql-security-checks.md.
3. **Generate per-operation tests** from `contract-test-specs.md`: request validation, response
   conformance, error conformance, authorization, idempotency, indeterminate commit.
4. **Generate the inventory assertion — derived from the code, not read from the map.** Walk the
   source tree for mapped routes and assert every one is declared by the specification or listed in
   the map's `out_of_scope_handlers`. An assertion that only re-reads `api-contract-map.json` passes
   whenever the map is wrong, which is exactly when it needs to fail: the first real run of this
   pipeline produced a map claiming nothing unmapped while ten routes — including an unauthenticated
   `/api/admin/users` — were reachable and undeclared (@rules/api-security-checks.md API9).

   **The unit of comparison is `(HTTP method, normalized path)`, and normalization renames path
   variables positionally.** Both halves matter, and getting either wrong under-counts silently:

   - Rewrite each path variable to its **position** — `/api/orders/{id}` and `/orders/{orderId}`
     both become `/api/orders/{1}` and `/orders/{1}`. Rewriting to a *fixed name* instead makes
     genuinely different paths collide and vanish into a dedup.
   - Key on the method too. `GET /orders` and `POST /orders` are two operations; deduping on path
     alone counts them once.

   An independent reviewer of that same first run counted ten undeclared operations where the
   generated assertion reported six — the whole gap was these two mistakes. State the counting rule
   in the generated test so a reader can check it, and report the count alongside the list.
5. **Generate ArchUnit rules** when selected — layer direction, no persistence or ScalarDB type in a
   controller signature, no domain type in a response DTO.
6. **Wire the build** — a test task the quality gate can invoke by name
   (@rules/ai-code-quality-gate.md stage 3), pinning versions per @rules/dependency-versions.md.
7. **Report** — operations covered, operations with no example, assertions skipped and why.

`--dry-run` reports the plan and coverage without writing tests.

## Output

| File | Content |
|------|---------|
| `generated/{service}/src/test/java/**/contract/` | Per-operation/field-coordinate tests plus OpenAPI or GraphQlTester validation harness |
| `generated/{service}/src/test/java/**/architecture/` | ArchUnit rules (when selected) |
| `generated/{service}/src/test/resources/contract/` | Fixtures derived from the contract's examples |
| `reports/07_test-specs/contract-test-coverage.md` | Which operations are covered, by which assertions, and what is not |

Write reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).
Test code and identifiers stay in English.

## Acceptance Criteria

- Every `operationId` in the contract map has at least one generated test, or is listed as uncovered
  with the reason
- Every GraphQL resolver-bound field coordinate has a generated test or an explicit uncovered entry;
  SDL fields and source resolvers have no silent unmapped entries
- The generated suite compiles and runs, and the task the gate invokes actually matched tests — a
  filter matching nothing is a green task and an ungated build (@rules/ai-code-quality-gate.md)
- The specification the tests load is inside the test tree, not under `reports/`
- Every expected value in a generated test traces to the specification or the problem type registry —
  none read from the implementation
- Every registered problem type has a conformance assertion
- The `UnknownTransactionStatusException` contract is asserted for every operation that can raise it,
  including which of the two responses applies
- The inventory assertion exists and fails when `api-contract-map.json` reports anything unmapped
- The build exposes a named task the quality gate can invoke, and it was verified to run
- No generated test was disabled or weakened to make the suite green

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:generate-test-specs | Input source — the assertions and the stack selection |
| /architect:generate-api-code | Input source — the code under test and the contract map |
| /architect:design-api | Input source — the contract |
| /architect:verify-implementation | Runs this suite as stage 3 of the quality gate |
| /architect:generate-infra-code | Downstream — the CI workflow that runs this suite outside the session |
