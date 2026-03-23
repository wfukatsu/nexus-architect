---
name: generate-test-specs
description: |
  Generate BDD scenarios, unit test, integration test, and performance test specifications.
  Invoked via /architect:generate-test-specs. Requires output from design-implementation as a prerequisite.
model: sonnet
user_invocable: true
---

# Test Specification Generation

## Desired Outcome

Generate comprehensive test specifications based on implementation specs:
- **BDD scenarios**: Feature files in Gherkin format
- **Unit test specs**: Test cases for services, repositories, and value objects
- **Integration test specs**: Integration tests for inter-service communication and DB operations
- **Performance test specs**: Load conditions and SLO verification

## Acceptance Criteria

- Every aggregate's CRUD operations are covered by at least one BDD scenario
- Includes test cases for boundary values, error cases, and concurrent processing
- When using ScalarDB, includes OCC conflict scenario tests

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/06_implementation/ | Required | /architect:design-implementation |

## Output

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

| File | Content |
|------|---------|
| `reports/07_test-specs/bdd-scenarios/` | Gherkin .feature files |
| `reports/07_test-specs/unit-test-specs.md` | Unit test cases |
| `reports/07_test-specs/integration-test-specs.md` | Integration test cases |
| `reports/07_test-specs/performance-test-specs.md` | Performance test conditions |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-implementation | Input source |
| /architect:generate-scalardb-code | Related (test code generation) |
