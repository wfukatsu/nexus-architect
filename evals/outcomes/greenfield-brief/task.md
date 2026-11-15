# Task: greenfield design from a one-page brief

**Input.** `brief.md` — a one-page brief for a library reservation service: five functional
needs, two invariants (no double hold, no lost queue place), one peak, one availability target,
an existing Oracle ILS to read and a REST API to call, a team and a budget.

**Commands.** `/architect:define-requirements --input=brief.md --auto`, then
`/architect:pipeline . --profile=poc --lang=en` — the requirements baseline from the brief alone,
then the proof-of-concept profile: redesign, target architecture, API contract, two reviews, the
report.

**What the thresholds say.** The brief yields at least eight `FR-`/`NFR-` nodes and at least 80 %
of them are reached by a design node (a requirement no context, aggregate or decision cites was
dropped on the way); every phase ends; every report validates; at least three ADRs validate (the
hold-as-aggregate decision, the ILS integration, the queue's consistency class are the obvious
ones); at least five open questions are recorded (the brief is silent on hold priority between
branches, on what "notified" means, on the retention of expired holds); the run stays under
USD 30 and two hours at `poc` depth.

**Reference.** The run of 2026-11-15 by `tools/eval-outcomes.sh run greenfield-brief
--permission-mode bypassPermissions --max-budget-usd 40` on toolkit 0.66.1 — two `claude -p`
sessions, one per command — graded:

| metric | value |
|--------|-------|
| requirement coverage | 100 % (12 of 12: 7 `FR-`, 5 `NFR-`; 43 graph nodes, none dangling) |
| phases | 29: 8 completed, 21 skipped (greenfield path, depth `minimal`, outside `poc`), 0 failed |
| open questions | 35, all `unasked` — OQ-004 hold priority between branches, OQ-011 what "notified" means, OQ-019 retention of expired holds among them |
| ADRs | 9 records, 0 errors, all `proposed` |
| report validity | 31 files, 0 failures |
| review verdict | FAIL at 3.34 / 5 — 0 critical, 9 major, one over the CONDITIONAL PASS limit, eight of them at the ILS boundary |
| cost | USD 20.63 at list price (define-requirements 5.39, redesign 5.00, design-api 4.84, design-microservices 3.56) |
| wall clock | 2,413 s (40 min) |

`reference-scorecard.json` beside this file is that run graded with these thresholds — PASS on
every check. The review's FAIL is the design's finding, not a failed phase: the brief leaves the
ILS boundary open (how the service learns of returns, whether the ILS can clear an "on hold"
mark), and the risk reviewer counts that against the design. Two caveats travel with the
reference, under `reference_run.caveats`: at depth `minimal` the two reviews scored their
dimensions themselves, as the `poc` profile specifies, and the output language defaulted to
English under `--auto`. The cost cap was raised from USD 25 to 30 after this run: the measured
20.63 left one fifth of headroom, less than the other tasks carry.

**Comparison.** This is the task to run on another toolkit: give it `brief.md`, ask it for the
requirements, the architecture, the API contract and its review, and grade its output directory
with `tools/eval-outcomes.sh grade <dir> greenfield-brief`. The graders read artifacts by the
shapes this toolkit writes (`work/traceability.json`, `work/context.md`, `reports/03_design/adr/`),
so another toolkit's output needs those shapes to be comparable on coverage, questions and
decisions — cost, duration and test results need only `work/token-usage.json`, the registry's
timestamps and JUnit XML. Say which metrics were comparable in the write-up; an unmeasured metric
is not a zero.
