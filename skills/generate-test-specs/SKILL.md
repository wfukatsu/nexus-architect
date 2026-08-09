---
description: |
  Generate BDD scenarios, contract test, unit test, integration test, and performance test specifications.
  Invoked via /architect:generate-test-specs. Requires output from design-implementation as a prerequisite.
model: sonnet
user_invocable: true
---

# Test Specification Generation

## Desired Outcome

Generate comprehensive test specifications based on implementation specs:
- **BDD scenarios**: Feature files in Gherkin format
- **Contract test specs**: What must be asserted to prove the code obeys the API contract, and the
  stack that will assert it
- **Unit test specs**: Test cases for services, repositories, and value objects
- **Integration test specs**: Integration tests for inter-service communication and DB operations
- **Performance test specs**: Load conditions and SLO verification

## Contract Test Specification

Contract testing is a **first-class category**, not a subset of integration testing. Integration tests
prove the pieces work together; contract tests prove the running API is the API the specification
promised. They catch a different defect — a plausible response that is not the contracted response —
and that defect is exactly what generated code produces most often.

Specify, per `operationId` in `reports/03_design/api-specifications/`:

| Assertion | Content |
|-----------|---------|
| Request validation | Each schema constraint (`required`, `minLength`, `pattern`, `enum`, `format`) rejected with the contracted 400/422 and a Problem Details body carrying `errors` |
| Response conformance | Every declared status code exercised, and each response validated against its schema — including no undeclared properties and no missing required ones |
| Error conformance | Every problem `type` the operation declares is reachable and returns `application/problem+json` with the registered `title` and `status` (@rules/api-error-standard.md) |
| Authorization | The operation rejects an unauthenticated caller, a caller with the wrong role/scope, and — where an ownership predicate applies — a caller acting on another principal's or another tenant's object |
| Idempotency | Where the operation carries an `Idempotency-Key` obligation: replay returns the original response; the same key with a different body returns `idempotency-key-reuse`; a missing required key returns `idempotency-key-required` |
| Indeterminate commit | Where the operation can raise `UnknownTransactionStatusException`, the contracted §3.1 response is asserted — 503 with `Retry-After` when idempotency-protected, 500 without it otherwise. Not a generic 500 |
| Architecture | The layering rules from `api-layer-spec.md`: controller -> application service -> domain -> repository, no reverse dependency, no persistence or ScalarDB type in a controller signature |

The transaction scenarios belong to the **integration** specs, not here, and they are the ones a
contract suite cannot reach: concurrent writers on one record (exactly one wins, the loser fails
cleanly rather than silently succeeding), a participant whose `prepare()` conflicts (every
participant rolls back, no half-applied state), and a saga whose later step fails (earlier steps
compensate, and the compensation is idempotent under redelivery). Specify each against the
transaction design's own TX- entries, and note that a 2PC scenario needs **one manager per
participant** or it does not exercise 2PC at all (@rules/scalardb-2pc-patterns.md).

Record the **selected stack** per @rules/api-contract-fidelity.md §7 — the Spring default
(`swagger-request-validator` driven from `@WebMvcTest`/`@SpringBootTest` slices) plus any opt-ins
(Schemathesis, Pact, ArchUnit) with the reason each was selected or skipped. `generate-contract-tests`
emits exactly what is recorded here, so an unrecorded stack is one that never gets written.

## Acceptance Criteria

- Every aggregate's CRUD operations are covered by at least one BDD scenario
- Every `operationId` has a contract test specification covering all seven assertion rows above that
  apply to it, and the selected stack is recorded
- Includes test cases for boundary values, error cases, and concurrent processing
- When using ScalarDB, includes OCC conflict scenario tests
- Every acceptance criterion in the requirements is reachable from at least one specified test — an
  untested acceptance criterion is recorded as a gap, not omitted silently

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/06_implementation/ | Required | /architect:design-implementation |
| reports/06_implementation/api-layer-spec.md | Required when an API surface exists | /architect:design-implementation |
| reports/03_design/api-specifications/ | Required when an API surface exists | /architect:design-api |

## Output

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

| File | Content |
|------|---------|
| `reports/07_test-specs/bdd-scenarios/` | Gherkin .feature files |
| `reports/07_test-specs/contract-test-specs.md` | Contract test cases per `operationId`, plus the selected stack |
| `reports/07_test-specs/unit-test-specs.md` | Unit test cases |
| `reports/07_test-specs/integration-test-specs.md` | Integration test cases |
| `reports/07_test-specs/performance-test-specs.md` | Performance test conditions |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-implementation | Input source |
| /architect:design-api | Input source — the contract the contract tests assert against |
| /architect:generate-contract-tests | Output consumer — emits the executable tests from these specs |
| /architect:generate-scalardb-code | Related (test code generation) |
