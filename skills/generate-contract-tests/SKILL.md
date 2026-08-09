---
description: |
  Turn the API contract into executable tests — OpenAPI request/response validation, Problem Details
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
2. **Generate the validation harness** — the OpenAPI validator wired into the test slice, so every
   request and response in the suite is checked without per-test boilerplate.
3. **Generate per-operation tests** from `contract-test-specs.md`: request validation, response
   conformance, error conformance, authorization, idempotency, indeterminate commit.
4. **Generate the inventory assertion** — every handler present in `api-contract-map.json` maps to a
   specification operation, and both `unmapped` arrays are empty. This is what turns an undocumented
   endpoint into a build failure (@rules/api-security-checks.md API9).
5. **Generate ArchUnit rules** when selected — layer direction, no persistence or ScalarDB type in a
   controller signature, no domain type in a response DTO.
6. **Wire the build** — a test task the quality gate can invoke by name
   (@rules/ai-code-quality-gate.md stage 3), pinning versions per @rules/dependency-versions.md.
7. **Report** — operations covered, operations with no example, assertions skipped and why.

`--dry-run` reports the plan and coverage without writing tests.

## Output

| File | Content |
|------|---------|
| `generated/{service}/src/test/java/**/contract/` | Per-operation contract tests + the validation harness |
| `generated/{service}/src/test/java/**/architecture/` | ArchUnit rules (when selected) |
| `generated/{service}/src/test/resources/contract/` | Fixtures derived from the contract's examples |
| `reports/07_test-specs/contract-test-coverage.md` | Which operations are covered, by which assertions, and what is not |

Write reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).
Test code and identifiers stay in English.

## Acceptance Criteria

- Every `operationId` in the contract map has at least one generated test, or is listed as uncovered
  with the reason
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
