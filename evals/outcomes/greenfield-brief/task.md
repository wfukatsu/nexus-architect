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
USD 25 and two hours at `poc` depth.

**Comparison.** This is the task to run on another toolkit: give it `brief.md`, ask it for the
requirements, the architecture, the API contract and its review, and grade its output directory
with `tools/eval-outcomes.sh grade <dir> greenfield-brief`. The graders read artifacts by the
shapes this toolkit writes (`work/traceability.json`, `work/context.md`, `reports/03_design/adr/`),
so another toolkit's output needs those shapes to be comparable on coverage, questions and
decisions — cost, duration and test results need only `work/token-usage.json`, the registry's
timestamps and JUnit XML. Say which metrics were comparable in the write-up; an unmeasured metric
is not a zero.
