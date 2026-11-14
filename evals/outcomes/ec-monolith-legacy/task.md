# Task: legacy refactoring of the ec-monolith sample

**Input.** `samples/ec-monolith` — the Spring Boot monolith with deliberate defects (a God service,
circular imports between `order` and `inventory`, a single MySQL). The fixture's source is never
edited; the run writes `reports/`, `work/` and (in the extension tier) `generated/`.

**Command.** `/architect:pipeline . --profile=full --lang=en` — the core pipeline, unattended, every
question recorded `unasked`.

**What the thresholds say.** Every phase ends (`failed` 0); every report passes the two output
validators; the ADR directory validates and holds at least eight records (the 2026-11-01 run
wrote nineteen); the run surfaces at least twenty open questions (an automated run that asks
nothing has hidden its assumptions — the reference run recorded 88); the quality-gate verdict, when
the extension tier was run, is a verdict and not absent; the whole run stays under USD 60 and six
hours (the reference run: USD 39.24, 3.6 h on Opus phases). `requirement_coverage` is not
thresholded on the legacy path — `define-requirements` is optional there and the graph holds no
`FR-` nodes unless documents were supplied.

**Reference.** The run of 2026-11-01 (recorded in the changelog of 0.52.0) graded:

| metric | value |
|--------|-------|
| open questions | 88, all `unasked` |
| ADRs | 19 records, 0 errors |
| report validity | 77 files, 1 failure |
| quality gate | FAIL — 2 passed / 6 failed (jacoco rules, CVEs, missing service credential) |
| tests | 473, pass rate 0.981 |
| cost | USD 39.24 |
| wall clock | 12,977 s |

A rerun that scores above this on coverage or below it on cost is an improvement the numbers can
show; a rerun that scores the same has at least not regressed.
