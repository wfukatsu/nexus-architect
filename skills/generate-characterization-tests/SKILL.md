---
description: |
  Pin the current behaviour of a legacy system in executable characterization (golden master)
  tests before it is refactored or strangled — the safety net the transformation plan's steps are
  gated on. Records what the code does, not what it should do.
  /architect:generate-characterization-tests [target_path] [--scope=module|service|repo] [--module=<name>]
  [--out=<path>] [--seam=http|cli|function|db] [--confirm-versions|--no-confirm-versions] [--dry-run] [--auto] [--lang=en|ja] to invoke.
  Runs on the legacy path after investigate (and analyze when it exists); before any
  transformation-plan step touches the module.
model: sonnet
user_invocable: true
disable-model-invocation: true
---

# Characterization Test Generation

## Desired Outcome

A legacy module cannot be refactored safely on the strength of tests it does not have, and it cannot
be developed test-first (@rules/tdd-workflow.md) until its current behaviour is fixed in place.
Characterization tests are that fixation: they record **what the code does today**, observed by
running it, so that a transformation step which changes the observed behaviour fails a build
instead of surviving into production. They are deliberately not a statement of correctness — a bug
the tests pin is a bug the tests will keep pinning until someone decides it is a bug, records that
decision, and changes the expectation.

Generate, per module in scope:

- **A seam inventory** — the points at which the module can be driven and observed without
  modification (an HTTP surface, a CLI, a public function, a database state before/after), and
  the one selected per module with the reason.
- **Golden-master tests** — for each seam, recorded inputs and the outputs the current code
  produced for them, committed as fixtures; a test replays the input and compares against the
  fixture. Non-deterministic fields (timestamps, generated ids, ordering the code does not promise)
  are masked, and the mask is in the fixture, not in the assertion.
- **A coverage record** — which of the module's entry points, and which of the `DEBT-` /
  `SEC-` items from `issues-and-debt.md` that name it, are pinned; which are not and why.

## Decision Criteria

- **Observe, never reason.** Every expected value in a fixture was produced by running the legacy
  code. A value the model wrote from reading the code is a guess wearing a fixture's clothes, and it
  turns the safety net into a second implementation. If the code cannot be run, say so and stop —
  a characterization suite that was not recorded from the system is not one.
- **Pin at the widest stable seam.** Prefer the seam furthest from the code that will change (HTTP
  over a public function, a public function over a private one): the test survives the refactor it
  guards only if it does not reach into what is being refactored.
- **Record the bug, flag the bug.** When a recorded output contradicts the requirements, the
  ubiquitous language or an `issues-and-debt.md` finding, the fixture keeps the observed value and
  the test carries a `@KnownDefect(DEBT-xx)` marker naming it, so the suite still guards the
  transformation and the decision to fix it is a visible edit to one fixture.
- **Coverage is by entry point, not by line.** The measure is how many of the module's ways in are
  pinned; a line-coverage figure over legacy code says little about whether its behaviour is fixed.
- **Non-determinism is masked, never averaged.** A field that differs between two runs of the same
  input is masked and listed; a test that passes "usually" is not a characterization test.
- **Never write a version from memory** — the test runner, the snapshot library and any driver the
  fixtures need are looked up per @rules/dependency-versions.md, and the project's existing test
  stack is binding when it has one.

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| target_path (argument) | Required | The legacy codebase; it must be runnable in-session (build + a way to drive the seam) |
| reports/before/{project}/codebase-structure.md | Required | /architect:investigate — modules and entry points |
| reports/before/{project}/issues-and-debt.md | Required | /architect:investigate — the `DEBT-` / `SEC-` items whose behaviour the suite must pin or flag |
| reports/before/{project}/technology-stack.md | Recommended | /architect:investigate — the test stack already in the project |
| reports/01_analysis/domain-code-mapping.md | Recommended | /architect:analyze — which domain each module serves, to choose modules by transformation order |
| reports/03_design/transformation-plan.md | Recommended | /architect:design-microservices — when present, scope defaults to the modules its next step touches |

## Steps

1. **Resolve scope** — `--module` / `--scope`, else the modules the transformation plan's next
   unfinished step touches, else every module `codebase-structure.md` lists. Resolve the output
   root (`--out`, else the module's own `src/test/` when the project has a test tree, else
   `generated/characterization/{module}/`) — merge-bound when the project's tree is used, and then
   subject to the same `git check-ignore` check as `implement-backlog`'s Output Location.
2. **Build the seam inventory** — per module: the entry points from `codebase-structure.md`, the
   candidate seams for each, the one selected and why. `--seam` forces one kind. Present the
   inventory and confirm, unless `--auto`.
3. **Confirm the system runs** — build it and drive one seam end to end. If this fails, report the
   blocker (missing dependency, no test database, a seam that needs credentials) and stop; do not
   proceed to write fixtures the system did not produce.
4. **Record the golden masters** — per selected seam, a representative input set: the examples in
   `issues-and-debt.md` and `domain-code-mapping.md`, the boundary values the entry point's
   signature admits, and the error paths the code visibly handles. Run each input, capture the
   output, identify non-deterministic fields by running each input **twice** and diffing, write the
   fixture with the masks. Delegate the recording per module to sonnet sub-agents in parallel when
   modules do not share state.
5. **Generate the tests** — one test per fixture (or a parameterized test over a fixture set),
   using the project's test stack (JUnit 5 + a snapshot/approval library for JVM projects; the
   language's equivalent otherwise). Each test names its seam, its fixture, and any `@KnownDefect`.
6. **Wire the build** — a named task the quality gate and the transformation plan can invoke
   (`characterizationTest`), run it, and verify it matched tests and passed against the unchanged
   system — a suite that fails on the code it was recorded from is a recording error, fix it before
   reporting.
7. **Report** — `reports/07_test-specs/characterization-test-coverage.md`: per module, entry points
   pinned / total, seams, fixtures recorded, masked fields, `@KnownDefect` list, and the entry points
   left unpinned with the reason. Append the task name to `transformation-plan.md`'s step gate when
   the plan exists (the plan's owner is `design-microservices`; this skill only fills in the task
   reference the plan left as `TBD`).

`--dry-run` builds the seam inventory and reports what would be recorded, running nothing.

## Output

| File | Content |
|------|---------|
| `<test root>/**/characterization/` | The tests, per module and seam |
| `<test root>/resources/characterization/<module>/` | Recorded fixtures (input, masked output, mask list) |
| `reports/07_test-specs/characterization-test-coverage.md` | Seam inventory, entry points pinned / total per module, `@KnownDefect` list, unpinned entry points with reasons |

Write the report in the language configured in `work/pipeline-progress.json`
(`options.output_language`). Test code, fixtures and identifiers stay in English.

## Acceptance Criteria

- Every fixture value was produced by running the legacy system in this run — none authored from
  reading the code; the run command is recorded in the report
- Every module in scope has a seam inventory with one selected seam and the reason
- Non-deterministic fields were found by a second run and are masked in the fixture, listed in the
  report — no test depends on a value that differed between the two runs
- Every `DEBT-` / `SEC-` item naming a module in scope is either pinned by a test carrying
  `@KnownDefect`, or listed as unpinned with the reason
- The suite passed against the unchanged system, the task the gate invokes matched tests, and the
  task name is recorded in the transformation plan's step gate when the plan exists
- Entry points pinned / total is stated per module; an unpinned entry point has a reason, never an
  omission
- Every pinned version was looked up and recorded per @rules/dependency-versions.md

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:investigate | Input source — modules, entry points, debt items |
| /architect:analyze | Input source — domain-code mapping, to scope by transformation order |
| /architect:design-microservices | Consumer — each transformation-plan step is gated on this suite passing before and after |
| /architect:implement-backlog | Downstream — the refactoring items run under this net; the tests are `characterization`, not `test-after`, in the gate's record (@rules/tdd-workflow.md §5) |
| /architect:verify-implementation | Runs the suite as part of stage 2 on legacy-path items |
