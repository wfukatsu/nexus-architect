# Test-Driven Development Workflow

Applies whenever a skill **writes application code that will be merged** — `implement-backlog` Step
5 first of all, and `review-issue`'s fix loop — and, in the parts that concern the shape of the
domain layer, to the code generators (`generate-scalardb-code`, `generate-api-code`,
`generate-graphql-code`). The test *specifications* are `generate-test-specs`'s; the quality gate
(@rules/ai-code-quality-gate.md) proves the tests ran. This rule governs the one thing neither of
them can: the **order** in which tests and code are written, and the structure that makes the order
possible.

## 1. Why the order matters here

The generators and the quality gate together prove that tests exist and pass. They cannot prove that
the tests would have failed without the code — and a test written after the code, by the same model
that wrote the code, tends to assert what the code does rather than what the design said. That is
the failure mode `generate-contract-tests` guards against for the API ("assert against the
specification, not the code"), and the same defect reaches the domain layer through the unit tests
unless the order is enforced. A test that has been seen red is evidence; a test that was born green
is a restatement.

## 2. The loop: Red → Green → Refactor, as commits

Every behavioural unit of a work item is implemented as **three commits on the working branch**, in
this order, each referencing the Issue:

| Commit | Content | Must hold |
|--------|---------|-----------|
| `test: … (#<iid>)` — **Red** | The tests for the unit, derived from the specification (§3), and only what is needed for them to compile (interfaces, empty types, a `throw new UnsupportedOperationException()` body). No behaviour | The unit's test task **runs and fails** — assertion failures, not compile errors. Record the command and the failing test names in the commit body |
| `feat: … (#<iid>)` — **Green** | The smallest change that makes the red tests pass. No speculative generality, no second unit | The unit's tests pass, and every test that passed before still passes |
| `refactor: … (#<iid>)` — **Refactor** | Structure only: duplication removed, names aligned to the ubiquitous language, responsibilities moved to where the design put them. No behaviour change, no new test | The same tests pass with no edit to a test. If a test had to change, it was not a refactor — split it |

Two consequences:

- **Test-first is verifiable from history, not from prose.** For each unit, the `test:` commit
  precedes the `feat:` commit. `verify-implementation --gate` reads the branch's log for the item and
  records the sequence as stage-2 evidence (@rules/ai-code-quality-gate.md §Unit tests): a unit whose
  first commit touching production code has no earlier failing-test commit is `test-after`, reported
  per unit. `test-after` is not a failure of the gate — some units legitimately have none (§5) — but
  it is never silent.
- **The Refactor commit is where the model is corrected.** When refactoring reveals that the design
  was wrong — an invariant missing from `aggregate-manifest.json`, a value object that should have
  been an entity, a state the matrix did not have — the finding is recorded (Issue comment, and
  `/architect:capture-followup` when it is out of scope), the manifest is updated by its owning skill,
  and the affected tests are regenerated from the manifest. Code never becomes the model's source of
  truth by being the only place a rule is written down.

A unit is one command on one aggregate, one resolver or operation, one transition, one repository
method — the granularity `generate-test-specs` specifies at. Several units in one commit is
acceptable only when they cannot be tested apart; say so in the commit body.

## 3. The double loop (ATDD outside, TDD inside)

The Gherkin scenarios in `reports/07_test-specs/bdd-scenarios/` are acceptance tests, not
documentation. When the project has a BDD runner (Cucumber-JVM for the Java services this toolkit
generates), the outer loop is:

1. **Red (acceptance)** — the item's scenarios (`@RULE-…` / `@EX-…` tagged) get step definitions and
   fail against the empty implementation. Missing step definitions count as red only until they
   exist; an *undefined* step is not a failing test.
2. **Inner loop** — §2, one unit at a time, until the acceptance scenario's next step can pass.
3. **Green (acceptance)** — the scenario passes end to end.

When no BDD runner is configured, the acceptance test is the item's contract test
(`generate-contract-tests`) for API-facing items, or the example-based invariant test for
domain-only items, and the outer loop runs on that instead. Which one carried the outer loop is
named in the Step 7 progress comment. An item with no acceptance-level test at all is a gap
recorded on the Issue, not an item that skipped the outer loop quietly.

The first item of a new service is the **walking skeleton**: one scenario through every layer —
API → application service → aggregate → repository → real storage — with the thinnest possible
behaviour, so the wiring, the test harness and the CI stages exist before any domain logic does.
`export-backlog` marks it; `implement-backlog` implements it first.

## 4. Structure that makes the order possible

Test-first is impossible when the domain cannot be exercised without infrastructure. These are
design constraints, owned by `design-implementation` and enforced by the generators and ArchUnit:

| Constraint | Rule |
|-----------|------|
| **Domain tests run with no I/O** | The aggregate, value object and domain-service tests import nothing from `infrastructure/`, ScalarDB, Spring or the network, and run under `./gradlew test` in milliseconds. A domain test that needs a database is a design defect: the logic it tests is in the wrong layer |
| **One Fake per repository port** | Every repository interface `repository-interfaces-spec.md` declares has an in-memory implementation under `src/test/java/**/fakes/` — a `Map` keyed by the aggregate id, honouring the port's contract (not-found semantics, version/OCC check where the port declares one). Application-service tests use the Fake; the ScalarDB adapter is tested separately against the real engine (integration stage). Mocking frameworks are for collaborators that are genuinely external (a payment gateway, a clock); a mocked repository re-encodes the implementation's call sequence and breaks on every refactor |
| **Time and identity are injected** | `Clock` (`java.time.Clock`) and the id generator are constructor dependencies of every aggregate factory, application service and saga step that reads them. Tests pass a fixed clock and a sequential id generator; production wires the system ones. `Instant.now()`, `LocalDate.now()`, `UUID.randomUUID()` directly inside domain or application code is an ArchUnit violation |
| **Transactions are boundaries, not collaborators** | The application service opens the ScalarDB transaction and passes it down; domain objects never hold or start one. This is what lets the Fake stand in — the domain does not know a transaction exists (@rules/scalardb-coding-patterns.md) |
| **Randomness in property tests is seeded** | jqwik properties record their seed on failure and the seed is written into the fix commit so the counter-example reproduces; a property whose failure cannot be reproduced is a flaky test, not a found bug |

The Fakes are generated by `generate-scalardb-code` alongside the adapters, and by
`implement-backlog` for a port an item introduces — a port without a Fake is an item that cannot be
developed test-first, and the gap is reported as such.

## 5. What is exempt

- **Configuration, wiring and generated boilerplate** (Spring configuration, DTO records, mappers with
  no logic, build files): no test-first commit; the contract and integration suites cover them.
- **Adapters against real infrastructure** (the ScalarDB repository implementation, HTTP clients):
  test-first against the real engine is welcome but not required — the integration stage holds
  them, and the SQLite-backed harness in `samples/scalardb-transaction-tests` shows the shape.
- **Refactor-only items** (no behaviour change): the existing tests are the red/green guard; the
  item is one `refactor:` series, and the gate's `test-after` count is `not-applicable`.
- **Characterization tests on a legacy tree** (`/architect:generate-characterization-tests`) are
  written *after* the code by definition — they fix current behaviour, not intended behaviour — and
  are recorded as `characterization`, never as `test-after`.

Anything else that skips the order says so in the commit body and the Step 7 comment, with the
reason. The gate reports the count; the reviewer decides whether the reason holds.

## 6. What the gate records

Per work item, from the working branch (@rules/ai-code-quality-gate.md §Unit tests):

| Evidence | Source |
|----------|--------|
| Units and their commit sequence (`test-first` / `test-after` / `refactor-only` / `exempt`) | `git log` on the branch, commits referencing the item |
| Failing-test names from each Red commit body | Commit messages |
| Which test carried the outer loop (scenario / contract / invariant example), and whether it went red → green | Step 7 comment, CI evidence |
| Fake present per repository port the item touched | `src/test/java/**/fakes/` vs `repository-interfaces-spec.md` |
| ArchUnit clock/id/transaction rules ran and passed | Stage 8 |

None of these change the verdict on their own; all of them are reported, so that "tests exist and
pass" is never mistaken for "the tests drove the code".
