---
description: |
  Turn the Gherkin scenarios in reports/07_test-specs/bdd-scenarios/ into an executable acceptance
  suite — Cucumber-JVM step definitions bound by RULE-/EX- tag, driven through the API or the
  application service over the Fakes, and an acceptanceTest task the quality gate and the ATDD
  outer loop run.
  /architect:generate-acceptance-tests [--service=<name>] [--feature=<id>] [--driver=api|application] [--out=<path>]
  [--confirm-versions|--no-confirm-versions] [--dry-run] [--auto] [--lang=en|ja] to invoke.
  Runs after generate-test-specs; before the first implement-backlog item of a service, so the
  outer loop has something to be red.
model: sonnet
user_invocable: true
disable-model-invocation: true
---

# Acceptance Test Generation (Gherkin → executable)

## Desired Outcome

The `.feature` files `generate-test-specs` writes are the agreed examples — each `Rule:` a `RULE-`,
each `Scenario:` an `EX-` from the example map. As documents they are read once; as tests they are
the **outer loop** of @rules/tdd-workflow.md §3: red before the first unit of an item is written,
green when the item is done, and the thing that says an acceptance criterion is met rather than
believed met. This skill makes them executable.

Generate, per service:

- **Step definitions** — one Java step class per feature, every `Given` / `When` / `Then` in the
  feature files bound; no scenario left `undefined` or `pending` without an entry in the coverage
  report saying why.
- **A driver** — how the steps reach the system: `api` (HTTP through `@SpringBootTest` +
  `MockMvc` / `WebTestClient`, the contract validator of `generate-contract-tests` attached so an
  acceptance run also validates the contract) or `application` (the application services over the
  in-memory Fakes with a fixed `Clock`, no HTTP). Default `api` when the service has an API surface,
  `application` otherwise; `--driver` overrides.
- **A world / fixture layer** — the test data the `Given` steps set up, built from the value-object
  arbitraries and the aggregate examples so scenario data is valid by construction, reset per
  scenario.
- **The build task** — `acceptanceTest` (Cucumber-JVM on the JUnit Platform, `@Suite` with
  `@SelectClasspathResource("features")`, `failOnNoMatchingTests = true`), and the feature files
  copied into `src/test/resources/features/` so a committed test does not read the git-ignored
  `reports/` tree.
- **A coverage record** — `reports/07_test-specs/acceptance-test-coverage.md`: per feature,
  scenarios bound / total, `RULE-` and `EX-` reached, undefined steps and why, the driver, and
  which scenarios are tagged `@wip` (expected red until their item lands).

## Decision Criteria

- **The feature file is the contract; the step is glue.** Step text is never rewritten to fit an
  implementation — a step that cannot be bound is reported, and the wording question goes back to
  `/product:example-map` / `generate-test-specs`. Expected values in `Then` steps come from the
  scenario, never from running the code.
- **One step, one meaning.** A phrase bound twice with different behaviour, or a regex so loose it
  matches unrelated steps, is a defect; use Cucumber expressions with typed parameters and the
  ubiquitous language's nouns (@rules/tdd-workflow.md §6).
- **Red is the intended first state.** Scenarios whose item has not been implemented are tagged
  `@wip` and excluded from the gate's pass/fail by tag, **counted** in the coverage report, and
  untagged by the `implement-backlog` item that makes them pass (its Step 5 outer loop). A
  scenario that passes before its item exists is asserting nothing — report it.
- **Drive through the outermost stable seam.** `api` when the service has one — an acceptance test
  that bypasses the controller does not prove the criterion is met for a caller.
- **Never write a version from memory** — Cucumber-JVM, the JUnit Platform suite engine and any
  driver library are looked up per @rules/dependency-versions.md; the project's existing test
  stack is binding.

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/07_test-specs/bdd-scenarios/ | Required | /architect:generate-test-specs — the `.feature` files |
| reports/06_implementation/api-layer-spec.md | Required for `--driver=api` | /architect:design-implementation |
| reports/06_implementation/api-contract-map.json | Recommended for `--driver=api` | /architect:generate-api-code — which handler each `When` reaches |
| reports/06_implementation/repository-interfaces-spec.md | Required for `--driver=application` | /architect:design-implementation — the ports the Fakes implement |
| reports/03_design/aggregates/aggregate-manifest.json | Recommended | /architect:design-aggregate — examples and value-object rules for the fixture layer |
| reports/02_spec/examples/ | Recommended | /product:example-map — to report `RULE-` / `EX-` reach |

## Steps

1. **Resolve scope, driver and output root** — `--service` / `--feature`, `--driver` (default per
   the API surface), `--out` else the service's `src/test/` under the contract map's `source_root`
   (else `generated/{service}/src/test/`).
2. **Inventory the features** — parse every `.feature` in scope: features, rules, scenarios, tags,
   the distinct step phrases. Present the inventory (scenarios per feature, phrases to bind) and
   confirm, unless `--auto`.
3. **Pin the features into the test tree** — copy to `src/test/resources/features/<service>/`,
   preserving tags.
4. **Generate the fixture layer** — a `World` per feature holding scenario state, builders from the
   aggregate examples and value-object rules, a per-scenario reset (`@Before`), the Fakes or the
   test slice wired according to the driver, `Clock` fixed.
5. **Generate the step definitions** — one class per feature; every distinct phrase bound once
   with a Cucumber expression; `Then` assertions against the scenario's stated outcome (and, for
   `api`, the contracted status / Problem Details type). Tag scenarios whose item is not yet
   implemented `@wip` (from `backlog-manifest.json` when it exists, else all scenarios of a
   service with no code).
6. **Wire the build** — `acceptanceTest` task on the JUnit Platform, `@wip` excluded via
   `cucumber.filter.tags`, `failOnNoMatchingTests = true`; run it and verify the bound scenarios
   execute (a non-`@wip` scenario that fails on existing code is a finding, not a test to weaken).
7. **Report** — `acceptance-test-coverage.md` as above; delegate step-class generation per feature
   to sonnet sub-agents in parallel when features share no steps.

`--dry-run` reports the inventory and the binding plan, writing nothing.

## Output

| File | Content |
|------|---------|
| `<test root>/java/**/acceptance/` | Step definitions, `World`s, the Cucumber suite class |
| `<test root>/resources/features/` | The feature files, pinned |
| `reports/07_test-specs/acceptance-test-coverage.md` | Scenarios bound / total per feature, `RULE-` / `EX-` reached, `@wip` count, undefined steps with reasons, driver |

Write the report in the language configured in `work/pipeline-progress.json`
(`options.output_language`). Step code stays in English; step *text* keeps the language of the
feature files, since it is the agreed example.

## Acceptance Criteria

- Every `Scenario:` in scope is bound (no `undefined` step) or listed with the reason
- Every `RULE-` / `EX-` tag in the feature files is reachable by a bound scenario, and the coverage
  report says which
- The feature files the suite loads are inside the test tree, not under `reports/`
- No step text was rewritten to make binding easier; no `Then` value was read from the code
- `@wip` scenarios are excluded from pass/fail by tag and counted; no scenario passes before its
  item exists without being reported
- The `acceptanceTest` task exists, was run, and matched scenarios
- Every pinned version was looked up and recorded per @rules/dependency-versions.md

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:generate-test-specs | Input source — the feature files |
| /product:example-map | Origin of the rules and examples the scenarios carry |
| /architect:generate-contract-tests | Sibling — the contract validator is attached to the `api` driver |
| /architect:generate-scalardb-code | Sibling — the Fakes the `application` driver uses |
| /architect:implement-backlog | Consumer — the item's scenarios are its outer loop; it removes their `@wip` when they pass |
| /architect:verify-implementation | Runs `acceptanceTest` as part of stage 4 of the quality gate |
