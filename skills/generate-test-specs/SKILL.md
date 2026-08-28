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
- **BDD scenarios**: Feature files in Gherkin format — when `reports/02_spec/examples/` exists,
  each feature's `RULE-` entries are its `Rule:` blocks and each `EX-` its `Scenario:`, tagged with
  their IDs, so the scenarios are the agreed cases rather than cases invented from the feature's name
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

Specify, per REST `operationId` or GraphQL resolver-bound field coordinate in
`reports/03_design/api-specifications/`:

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

## State Transition Coverage

When `reports/03_design/state-machines/state-machine-manifest.json` exists, the model is a test
oracle, not background reading: it already enumerates every case, so coverage is measurable rather
than judged. Specify per machine (@rules/state-modeling.md §8):

| Coverage | What must be specified |
|----------|------------------------|
| Transition | Every `allow` cell fires: from its source state, the event moves the aggregate to the declared target and performs the declared effect |
| Guard | Every guarded transition is exercised on both branches — the guard true path, and the `else` branch reaching its declared outcome |
| Rejection | Every `reject` cell is attempted and returns the contracted error, not a 500 and not a silent success (@rules/api-error-standard.md) |
| Idempotency | Every `ignore` cell replays cleanly: the event is delivered twice and the second delivery leaves the state and the side effects unchanged |
| Concurrency | Every transition two actors can fire from one state: exactly one commits, the loser re-reads and re-evaluates its guard rather than retrying blindly (an integration test, not a contract test) |
| Terminal | No transition leaves a declared terminal state, attempted from each one |

Unreachable states and undecided cells are not test cases — they are model defects, and belong in
the gap list rather than in a specification that pretends to cover them.

## Acceptance Criteria

- Every aggregate's CRUD operations are covered by at least one BDD scenario
- When an example map exists, every `RULE-` appears as a `Rule:` block and every `EX-` as a scenario under it, both carrying their IDs — a rule with no scenario is a gap, not an omission
- Every `operationId` has a contract test specification covering all seven assertion rows above that
  apply to it, and the selected stack is recorded
- Every GraphQL field coordinate covers schema shape/nullability, validation, authorization, tenant
  isolation, registered errors and query-governance limits; select the GraphQlTester variant from
  the approved transport design
- Includes test cases for boundary values, error cases, and concurrent processing
- When using ScalarDB, includes OCC conflict scenario tests
- When a state transition model exists, every `allow`, `reject` and `ignore` cell of every matrix is
  covered by at least one specified test
- Every acceptance criterion in the requirements is reachable from at least one specified test — an
  untested acceptance criterion is recorded as a gap, not omitted silently

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/06_implementation/ | Required | /architect:design-implementation |
| reports/06_implementation/api-layer-spec.md | Required when an API surface exists | /architect:design-implementation |
| reports/03_design/api-specifications/ | Required when an API surface exists | /architect:design-api |
| reports/03_design/state-machines/state-machine-manifest.json | Optional | /architect:design-state-machine — the matrix is the coverage target above |
| reports/03_design/aggregates/aggregate-manifest.json | Optional | /architect:design-aggregate — one unit test per invariant on both branches, seeded by its concrete examples |
| reports/02_spec/examples/ | Optional | /product:example-map — `RULE-` → `Rule:` blocks, `EX-` → `Scenario:` lines in the BDD feature files |

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
| /architect:design-state-machine | Input source — the state x event matrix the transition tests cover |
| /architect:design-aggregate | Input source — the invariants and their examples the unit tests cover |
| /product:example-map | Input source — the agreed rules and examples the Gherkin is generated from |
| /architect:generate-contract-tests | Output consumer — emits the executable tests from these specs |
| /architect:generate-scalardb-code | Related (test code generation) |
