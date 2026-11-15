# Task: legacy refactoring of the ec-monolith sample

**Input.** `samples/ec-monolith` — the Spring Boot monolith with deliberate defects (a God service,
circular imports between `order` and `inventory`, a single MySQL). The fixture's source is never
edited; the run writes `reports/`, `work/` and (in the extension tier) `generated/`.

**Command.** `/architect:pipeline . --profile=full --lang=en` — the core pipeline, unattended, every
question recorded `unasked`.

**What the thresholds say.** Every phase ends (`failed` 0); every report passes the two output
validators; the ADR directory validates and holds at least eight records (the reference run wrote
twenty); the run surfaces at least twenty open questions (an automated run that asks nothing has
hidden its assumptions — the reference run recorded 46); the quality-gate verdict, when the
extension tier was run, is a verdict and not absent; the whole run stays under USD 90 and six hours
(the reference run: USD 71.55, 75 minutes — the cap leaves a quarter of headroom, the way the other
tasks' caps do). `requirement_coverage` is not thresholded on the legacy path —
`define-requirements` is optional there and the graph holds no `FR-` nodes unless documents were
supplied.

**Reference.** The first runner run, 2026-11-15 (toolkit 0.67.0, `--max-budget-usd 120`, one
`claude -p` session), graded:

| metric | value |
|--------|-------|
| phases | 23 completed, 6 skipped, 0 failed (profile `full`) |
| open questions | 46, all `unasked` |
| ADRs | 20 records, 0 errors |
| report validity | 65 files, 1 failure (`mmi-by-module.md`, no ELI5 section — Issue #194) |
| quality gate / tests | not measured: the extension tier is not in this task's command |
| cost | USD 71.55 at list price |
| wall clock | 4,506 s (phase time 8,766 s, three phases at a time) |

The earlier by-hand run of 2026-11-01 (the changelog of 0.52.0; 19 ADRs, 88 open questions, 77
reports with 1 failure, USD 39.24 over 3.6 h) was the reference until this one; its cost missed
every sub-agent session (fixed in 0.65.2) and its quality-gate line came from a hand-driven codegen
chain, so neither is a `run` baseline.

`reference-scorecard.json` beside this file is the runner run graded with these thresholds — the
committed example of a scorecard. It reads FAIL on one check, `report_validity.failures` (one of 65
reports lacks its ELI5 section, a template gap fixed with the registration), which is the honest
result; the quality-gate threshold is `"required": false` because this task's single command never
reaches the extension tier. A rerun that scores above this on coverage or below it on cost is an
improvement the numbers can show; a rerun that scores the same has at least not regressed.
