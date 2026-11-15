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
task; the eight-stage gate was run (`quality_gate.stages` ≥ 8) and recorded a verdict — any verdict,
the measurement is that the gate ran, the verdict is the result to read; at least fifty unit tests
ran under it; the generated suites (`test`, `integrationTest`, `contractTest`, `acceptanceTest`)
hold at least a hundred tests and pass at 90 % or better — contract drift and acceptance scenarios
waiting on open questions are the expected red (the reference run had 7 drifts and 2 scenarios
red, @rules/api-contract-fidelity.md); the run stays under USD 120 and twelve hours. Here every
threshold is **required**: an unmeasured `quality_gate` or `test_results` is a failed run, not an
unmeasured one.

**Reference.** The 2026-11-01 run of this chain on this input (not from `tools/eval-outcomes.sh
run`, by hand phase by phase): test 226/226, integrationTest 38/38, characterization 36/36,
contractTest 142/149, acceptanceTest 22/24, mutation 81 %, gate FAIL (jacoco rules, CVEs in a
transitive dependency, no service-to-service credential). A run of `tools/eval-outcomes.sh run
ec-monolith-implementation` is pending; the thresholds above are set from that reference and will
be tightened once a runner run exists.

**Comparison.** As for `ec-monolith-legacy`; another toolkit is comparable on `quality_gate` only
when it writes `reports/09_verification/quality-gate.json` in this shape, and on `test_results`
when it leaves JUnit XML under `generated/**/test-results/<suite>/`.
