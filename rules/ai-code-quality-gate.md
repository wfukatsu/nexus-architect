---
description: The quality gate that generated or AI-written code passes before human review — eight stages, their evidence requirements, and the verdict rules. Applies to implement-backlog, review-issue, verify-implementation, and the CI the infra codegen emits.
---

# AI Code Quality Gate

Applies to `implement-backlog` (Step 5c), `review-issue`, `verify-implementation --gate`, and to the
CI workflow `generate-infra-code` emits. It is the last automated checkpoint before a human is asked
to approve code that a model wrote.

## Why this exists

Design review answers "is this the right design". Code review answers "does this code look right".
Neither answers **"does this code do what the design said"** — and that is the question that matters
for generated code, because a model produces plausible code far more reliably than it produces
correct code. Plausible code passes reading. It fails only when something executes it against the
contract.

So the gate's rule is: **every stage produces evidence, and a stage with no evidence has not passed.**
"I reviewed it and it looks correct" is not a gate result. A command that ran, with its exit status
and output, is.

## The eight stages

Run in this order; the cheap deterministic stages fail fast before the expensive judgment ones.

| # | Stage | Passes when | Evidence |
|---|-------|-------------|----------|
| 1 | **Compile / build** | The project's real build target succeeds | Command + exit code |
| 2 | **Unit tests** | All pass; no test disabled or deleted in this change without a recorded reason; when `reports/03_design/aggregates/aggregate-manifest.json` exists, every invariant it declares is covered by at least one property-based test that drives the aggregate root (`reports/07_test-specs/property-test-specs.md` names the test per invariant); **line coverage of the changed files meets the threshold** and **the domain layer's mutation score meets its threshold** (§Test quality below) | Command + counts (run/passed/skipped) + invariant → test-class map, invariants covered / declared + coverage per changed file + mutation score (killed / total mutants) for `domain/` + the test-first record per unit (@rules/tdd-workflow.md §6) |
| 3 | **Contract tests** | Every REST `operationId` and GraphQL resolver field coordinate the change touches is exercised and validates against the specification (@rules/api-contract-fidelity.md §7) | Command + per-operation/field-coordinate results |
| 4 | **Integration tests** | All pass, including the transaction scenarios the design requires — OCC conflict, 2PC failure, saga compensation; **on the legacy path**, the `characterizationTest` task the transformation-plan step names passes on the modules the change touched (recorded before the change as the baseline and after it as the stage result — a fixture edit in between is a decision on the Issue, never a silent update) | Command + counts; characterization: task, modules, fixtures changed |

**Stage 4 is not substitutable by stages 3 and 8.** Contract tests prove the shape of what the API
returns; conformance review proves the code says what the design said. Neither runs a transaction
against a real engine, and some defects exist only there. Running this pipeline's own reference
implementations against a real ScalarDB instance failed an operation that both a contract suite and
an independent static reviewer had passed over: a `Put` on a record the transaction never read,
which is legal Java, reviews cleanly, and cannot commit
(@rules/scalardb-crud-patterns.md). Where a project has no integration suite, that is
`not-configured` and a reported gap — not a stage the other two cover.

| 5 | **SAST** | No new high/critical finding | Tool + version + finding counts by severity, new vs pre-existing |
| 6 | **Dependency scan** | No new high/critical CVE, and no dependency added that the version rules reject (@rules/dependency-versions.md) | Tool + advisory IDs |
| 7 | **API security** | `review-api-security --mode=code` returns no critical and no unresolved major, including GraphQL-specific checks when applicable (@rules/api-security-checks.md, @rules/graphql-security-checks.md) | `ASEC-` findings with severities |
| 8 | **Architecture / conformance** | `verify-implementation` reports no contract, transaction, or security conformance break; ArchUnit layering rules pass | `VER-` findings + `api-contract-map.json` with both `unmapped` arrays empty |

Stages 1–6 are commands. Stages 7–8 are skills that emit machine-readable findings. All eight write
into one gate result (§4).

## Verdict

| Verdict | Condition |
|---------|-----------|
| **PASS** | Every stage passed |
| **CONDITIONAL** | Stages 1–4 passed; the remaining findings are all `major` or below, each with a recorded owner and decision |
| **FAIL** | Any of stages 1–4 failed, or any `critical` finding in stages 5–8 |

**FAIL blocks the human review request.** It does not become a note on the pull request for someone
to weigh — the point of the gate is that a human is never asked to review code that has not passed
it. `review-issue` treats a FAIL as `[B]` blockers and runs its existing fix loop; when that loop
does not converge it writes the decision-needed note and sets `status::blocked`, which is the correct
outcome and not a failure of the gate.

CONDITIONAL requires an explicit human decision recorded on the Issue, naming what was accepted and
why. It is not a synonym for PASS and never becomes one by default.

## Exit code zero is not evidence of coverage

A stage passes when its command ran **over the intended scope** and exited zero. Exit zero over an
empty scope is a false pass, and it is the most dangerous result the gate can produce, because it
reads as the strongest one.

This is not theoretical. On the first real run of this pipeline, `gitleaks detect` in a directory
that was not a git repository reported `0 commits scanned … no leaks found` and exited **0** — a
clean secrets scan that examined nothing. Run in directory mode over the same tree it scanned 239 KB
and found a leak.

Every scanning stage therefore records **what it covered**, and the coverage is asserted:

| Stage | Coverage evidence required |
|-------|---------------------------|
| Unit / contract / integration / acceptance / characterization | Number of tests **run** — a suite that ran 0 tests is `not-configured`, never `passed` |
| Property (invariants) | Invariants covered / declared, and the number of generated cases per property — a property that ran 0 tries, or an invariant with no test class, is a stage-2 failure, not a pass |
| SAST | Files or rules scanned |
| Dependency scan | Number of dependencies or manifests examined |
| Secrets scan | Bytes or files scanned |
| Image scan | The image reference actually pulled |

A stage whose coverage is zero is recorded as `not-configured` with the reason, never as `passed`.
The same applies to a filtered test task that matched nothing: `--tests '*ContractTest'` with no
matching class is a green task and an ungated build.

## Test quality: coverage and mutation score

A passing suite proves the tests do not fail. It does not prove they would fail if the code were
wrong — and when the same model wrote both the code and the tests in one sitting, that is the
question that matters. Stage 2 therefore measures two more things, both **on the change**, not on
the whole repository, so an old low-coverage module cannot fail a new item and a new untested class
cannot hide behind a well-tested repository:

| Measure | Scope | Threshold | Tool (JVM default) |
|---------|-------|-----------|---------------------|
| **Line + branch coverage** | Every production file the change touched | `domain/` and `application/`: **90 % line, 80 % branch**. Other packages: **70 % line**. Files the tdd-workflow rule exempts (§5 — configuration, DTO records, mappers with no logic) are excluded by package pattern, and the exclusion list is in the gate result | JaCoCo (`jacocoTestCoverageVerification` with per-package rules) |
| **Mutation score** | `domain/` packages the change touched | **80 % killed**, no surviving mutant on a line that enforces a declared invariant or a state-machine guard (those are listed by name; one survivor there fails the stage regardless of the aggregate score) | PIT (`pitest` Gradle plugin with `targetClasses` set to the touched domain packages, `mutators = DEFAULTS`, `junit5` plugin; jqwik properties included via the JUnit platform) |
| **Suite budget and quarantine** | Every test task the gate ran | Wall-clock per task against the layer budget of @rules/tdd-workflow.md §6 (over budget = `major`, slowest ten named); quarantined (`@Tag("flaky")`) tests counted, listed with their age, older than 14 days = `major`; no retry setting on any gate task | Task output, test inventory |
| **Test-first record** | Every behavioural unit of the item | Reported, not thresholded: units by `test-first` / `test-after` / `refactor-only` / `exempt`, the failing tests each Red commit named, and the acceptance-level test that carried the outer loop | `git log` on the working branch, per @rules/tdd-workflow.md §6 |

Rules:

- **Thresholds are project settings, defaults above.** A project's `build.gradle` rule or
  `pipeline-progress.json` `options.quality_gate` overrides them, and the value in force is recorded
  in the gate result. Lowering a threshold to pass an item is a recorded decision on the Issue, not
  a build edit.
- **Mutation testing is scoped to keep it cheap.** Running PIT over a whole service on every item is
  minutes to hours; over the touched `domain/` packages it is seconds to a minute, and the domain is
  where the invariants live. Widening the scope is a project choice; narrowing it below the touched
  domain packages is `skipped-by-user` with the reason.
- **A survivor is a finding, not a number.** The gate result lists surviving mutants by
  file:line and mutator, so the fix is a test to write, not a score to argue with. A survivor on an
  invariant-enforcing line means the property test for that invariant does not actually pin it —
  which is the defect §Exit code zero describes, seen from the other side.
- **Coverage over zero tests is not coverage.** JaCoCo reports 0 % for a task that ran no tests;
  the run-count rule above catches that first, and the coverage figure is recorded only when the
  count is non-zero.
- **The Node default** is Istanbul/`c8` thresholds via `nyc`/`vitest --coverage` for coverage and
  Stryker for mutation, with the same scopes and thresholds.

## Stage-skipping is recorded, never silent

A project without an API surface has no stage 3 or 7. A project with no SAST tool configured has no
stage 5. That is legitimate — **and it is reported**, per stage, with the reason:

| Reason | Meaning |
|--------|---------|
| `not-applicable` | The change has no surface this stage examines |
| `not-configured` | The stage applies but the project has no tool for it. Raise it as a gap once, so the answer is a decision rather than a habit |
| `skipped-by-user` | Explicitly waived for this run, with who waived it |

A gate result that silently omits a stage reads as "eight stages passed" when six ran. That is worse
than no gate, and `verify-implementation` treats a missing stage with no reason as a FAIL.

## Tooling

Resolve the project's actual tools first — a configured tool always wins over the default below, and
the versions are looked up per @rules/dependency-versions.md rather than recalled.

| Stage | JVM / Gradle default | Node default |
|-------|----------------------|--------------|
| Build | `./gradlew build -x test` | `npm run build` |
| Unit | `./gradlew test jacocoTestCoverageVerification` | `npm test -- --coverage` (thresholds in the coverage config) |
| Mutation (domain, part of stage 2) | `./gradlew pitest` scoped to the touched `domain/` packages | `npx stryker run` scoped the same way |
| Contract | `./gradlew test --tests '*ContractTest'` (OpenAPI validator and/or GraphQlTester) | project's contract suite |
| Integration | `./gradlew integrationTest` (SQLite-backed in-process engine, `*IT`) | `npm run test:integration` |
| Acceptance (part of stage 4 when the project has a BDD runner) | `./gradlew acceptanceTest` (Cucumber-JVM over `bdd-scenarios/`) | `npm run test:acceptance` |
| Characterization (legacy path, part of stage 4) | `./gradlew characterizationTest` | `npm run test:characterization` |
| SAST | Semgrep (`--config auto`), or SpotBugs + `find-sec-bugs` | Semgrep |
| Dependency | OSV-Scanner, or OWASP Dependency-Check | `npm audit --audit-level=high` / OSV-Scanner |
| Secrets | Gitleaks (`gitleaks dir <path>` when the tree is not a git repository — `detect` silently scans nothing there) | Gitleaks |
| Container image (when one is built) | Trivy | Trivy |

Never invent a command. If the documented build target does not exist, that is a stage-1 failure to
report, not a reason to substitute a command that happens to work — the same discipline
`generate-docs` applies when it verifies documented commands against real build targets.

## Gate result artifact

Written to `reports/09_verification/quality-gate.json`, and summarized in
`reports/09_verification/quality-gate.md`:

```json
{
  "schema_version": 1,
  "run_at": "2026-08-09T00:00:00Z",
  "item": "I1.2",
  "source_root": "services/order-service",
  "verdict": "FAIL",
  "stages": [
    {"stage": "build", "status": "passed",
     "command": "./gradlew build -x test", "exit_code": 0},
    {"stage": "unit", "status": "failed",
     "command": "./gradlew test", "exit_code": 0, "tests": {"run": 212, "passed": 212, "skipped": 0},
     "invariants": {"declared": 6, "covered": 5,
                    "uncovered": ["AGG-001/INV-3"], "tries_per_property": 1000},
     "coverage": {"tool": "jacoco", "scope": "changed", "thresholds": {"domain": {"line": 90, "branch": 80}, "other": {"line": 70}},
                  "files": [{"path": "domain/order/Order.java", "line": 96, "branch": 88}],
                  "excluded": ["**/config/**", "**/dto/**"], "passed": true},
     "mutation": {"tool": "pitest", "scope": ["com.example.order.domain"], "threshold": 80,
                  "mutants": {"total": 142, "killed": 121, "survived": 21}, "score": 85,
                  "invariant_survivors": [{"file": "domain/order/Order.java", "line": 88, "mutator": "NEGATE_CONDITIONALS", "invariant": "AGG-001/INV-3"}],
                  "passed": false},
     "test_first": {"units": {"test-first": 4, "test-after": 1, "refactor-only": 0, "exempt": 2},
                    "outer_loop": "bdd:@EX-014", "outer_loop_went_red": true},
     "detail": "every test passed, but INV-3 (order total equals the sum of line totals) has no property test, and a NEGATE_CONDITIONALS mutant on the line that enforces it survived — an exit-zero suite over an unchecked invariant is not a pass"},
    {"stage": "contract", "status": "failed",
     "command": "./gradlew test --tests '*ContractTest'", "exit_code": 1,
     "detail": "confirmOrder returned 500 for the transaction-status-unknown case; contract declares 503"},
    {"stage": "sast", "status": "skipped", "reason": "not-configured"},
    {"stage": "secrets", "status": "skipped", "reason": "not-configured",
     "detail": "gitleaks present, but `detect` scanned 0 bytes here — a zero-coverage pass is not a pass"},
    {"stage": "api-security", "status": "passed", "findings": {"critical": 0, "major": 1, "minor": 3}}
  ],
  "blocking": ["VER-004", "ASEC-011"]
}
```

`invariants` appears on the unit stage only when an aggregate manifest exists; `uncovered` is the
work list for `generate-scalardb-code`, and `tries_per_property` is what makes "the property ran"
a checkable claim. `coverage` and `mutation` carry the thresholds in force and the survivors by
line (§Test quality); `test_first` is the record @rules/tdd-workflow.md §6 asks for, reported and
never thresholded.

`blocking` lists the finding IDs that produced the verdict, so the fix loop has an explicit work list
rather than a report to re-read.

## Where the gate runs

Twice, deliberately:

1. **In the session**, as `implement-backlog` Step 5c — so the model fixes its own output before a
   human is involved.
2. **In CI**, from the workflow `generate-infra-code` emits — so the gate holds for hand-written
   changes, for later changes, and when nobody thought to run it.

The in-session run is the fast feedback loop; the CI run is the one that is actually enforced. A gate
that exists only as a checklist a model is asked to follow is the weakness this file exists to
remove, so the CI half is not optional once the project has CI.
