# Task: legacy refactoring of ec-monolith through code generation and the quality gate

**Input.** `samples/ec-monolith` — the Spring Boot / MySQL monolith with its deliberate defects
(`samples/README.md`), the same input as `ec-monolith-legacy`.

**Commands.** The full pipeline, then the extension tier's codegen chain for the Core service:
`design-implementation --layering=ddd`, `generate-test-specs`, `generate-scalardb-code`,
`generate-api-code`, `generate-contract-tests`, `generate-acceptance-tests`, and
`verify-implementation --gate`, every one under `--auto` (nobody answers in a `claude -p` run).
This is the task that measures what `ec-monolith-legacy` cannot: `quality_gate` and
`test_results` exist only after code was generated and gated.

**What the thresholds say.** Every phase ends and every report validates, as in the pipeline-only
task; the ADR directory holds at least twelve records; the run surfaces at least thirty open
questions; the eight-stage gate was run (`quality_gate.stages` ≥ 8) and recorded a verdict — any
verdict, the measurement is that the gate ran, the verdict is the result to read; at least five
hundred unit tests ran under it; the generated suites (`test`, `integrationTest`, `contractTest`,
`acceptanceTest`) hold at least a thousand tests and pass at 95 % or better — contract drift and
acceptance scenarios waiting on open questions are the expected red
(@rules/api-contract-fidelity.md); the run stays under USD 240 and twelve hours. Here every
threshold is **required**: an unmeasured `quality_gate` or `test_results` is a failed run, not an
unmeasured one. Each floor sits below the reference run's number and each cap above it, with room
for a run that answers differently; a rerun that lands outside them has changed something.

**Reference.** The run of 2026-11-15 by `tools/eval-outcomes.sh run ec-monolith-implementation
--permission-mode bypassPermissions --max-budget-usd 60` on toolkit 0.65.2 — eight `claude -p`
sessions, one per command — graded:

| metric | value |
|--------|-------|
| phases | 34: 28 completed, 6 skipped, 0 failed |
| open questions | 48, all `unasked` |
| ADRs | 17 records, 0 errors, all `proposed` |
| report validity | 78 files, 0 failures |
| quality gate | FAIL — 5 passed / 4 failed of 9 stages (unit, contract, integration/acceptance, conformance); 967 unit tests, mutation 98 % |
| tests | 1956 (test 967, contractTest 806, integrationTest 102, acceptanceTest 81), pass rate 0.9969 |
| cost | USD 187.39 at list price (pipeline 64.19, generate-scalardb-code 43.71, generate-api-code 28.95, unassigned 17.01) |
| wall clock | 16,998 s (4 h 43 min) |

`reference-scorecard.json` beside this file is that run graded with these thresholds — the
committed example of a runner scorecard. It reads PASS on every check. The gate's FAIL is the
input's: the four red stages trace to design documents that contradict each other (a second refund
under a new key answering 422 where the registry implies 409, a 12-character example password the
contract accepts, a pre-check that rejects before any charge) and to the unchosen payment provider;
the generated code follows the design in each case, and `verify-implementation` names the open
question behind every red test. Two caveats travel with the reference, under `reference_run.caveats`:
the pipeline session ran at the USD 60 session cap and narrowed its method to fit (`warnings` in
the registry), and `generate-test-specs` and `verify-implementation` did not stamp the registry
(Issue #181), so their USD 17.01 is `cost.unassigned_usd` and the completed-phase count is 28, not 30.

The earlier reference, the 2026-11-01 run of this chain by hand (test 226/226, integrationTest 38/38,
characterization 36/36, contractTest 142/149, acceptanceTest 22/24, mutation 81 %, gate FAIL on
jacoco rules, CVEs in a transitive dependency and no service-to-service credential), had no token
ledger; it set the first thresholds and is history now.

**Comparison.** As for `ec-monolith-legacy`; another toolkit is comparable on `quality_gate` only
when it writes `reports/09_verification/quality-gate.json` in this shape, and on `test_results`
when it leaves JUnit XML under `generated/**/test-results/<suite>/`.
