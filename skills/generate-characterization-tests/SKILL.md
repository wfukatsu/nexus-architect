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
  guards only if it does not reach into what is being refactored. **When the widest seam is itself
  defective** — the HTTP layer serializes recursively, authentication is misconfigured — pin it
  anyway (its brokenness is current behaviour) *and* pin the next seam in, so the transformation
  that repairs the transport has a net underneath it; say which seam each fixture observed.
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
| target_path (argument) | Required | The legacy codebase; it must be buildable in-session. A database or daemon it needs is supplied by the user's environment or substituted test-only per Step 3 — a `docker-compose` dependency is the common case and is not by itself a blocker |
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
3. **Confirm the system runs** — build it and drive one seam end to end. **A test-only substitution
   of the environment is not a modification of the system**: a test profile that swaps the
   datasource for an in-process engine (H2 in the dialect's compatibility mode for a JPA/MySQL
   project, SQLite for ScalarDB), a stub for a credential the seam needs, a disabled scheduler —
   added as `testRuntimeOnly` dependencies and test-scope configuration, never as a change under
   `src/main/`. Use it when the documented environment (a `docker-compose` database, a daemon)
   is not available in-session, and **state the boundary in the report**: which behaviours the
   substitute engine cannot reproduce faithfully (dialect-specific SQL, isolation, collation) are
   listed, and fixtures that depend on them are marked. If no substitution makes the seam
   drivable, report the blocker (missing dependency, credentials, a transport that is itself
   broken) and stop; do not proceed to write fixtures the system did not produce.
4. **Record the golden masters** — per selected seam, a representative input set: the examples in
   `issues-and-debt.md` and `domain-code-mapping.md`, the boundary values the entry point's
   signature admits, and the error paths the code visibly handles. The mechanism is **the test
   class itself in recording mode**: the generated tests take a `-Precord=<dir>` (or equivalent)
   property under which they write what they observed instead of asserting; run the suite twice
   into two directories, diff the two recordings with a small script emitted next to the tests
   (`tools/derive_masks.py` or the language's equivalent) that turns every differing leaf into a
   `masks` entry, and write the fixtures (`{seam, input, observed, masks}`) from run 1 plus the
   derived masks. Non-determinism **inside a string** (a proxy class name with a random suffix in
   an exception message, a truncated response body whose cut point moves) cannot be masked at the
   leaf: normalize it at observation time with a named rule (`observed` keeps the normalized
   form, the rule is listed in the fixture's `masks`), and list every such rule in the report.
   Delegate the recording per module to sonnet sub-agents in parallel when modules do not share
   state.
5. **Generate the tests** — one test per fixture (or a parameterized test over a fixture set),
   using the project's test stack: the assertion library the project already has (JSONAssert,
   AssertJ, …) is binding — add a snapshot/approval library only when the project has no way to
   compare structured output. Each test names its seam, its fixture, and any `@KnownDefect`.
   A recorded behaviour that is a defect **with no `DEBT-` / `SEC-` / `ISSUE-` id yet** is still
   pinned: mark it `@ObservedDefect("CHAR-<module>-<n>")`, list every `CHAR-` in the report's
   own table with what was observed and what the requirements say, and queue each as a follow-up
   via `/architect:capture-followup --queue-only` so it reaches `investigate`'s debt list. A
   defect is never left unmarked because it has no number.
6. **Wire the build** — a named task the quality gate and the transformation plan can invoke
   (`characterizationTest`), run it, and verify it matched tests and passed against the unchanged
   system — a suite that fails on the code it was recorded from is a recording error, fix it before
   reporting.
7. **Report** — `reports/07_test-specs/characterization-test-coverage.md`: per module, entry points
   pinned / total, seams, fixtures recorded, masked fields and normalization rules, the
   environment substitution and its boundary, `@KnownDefect` and `CHAR-` lists, and the entry
   points left unpinned with the reason. Then record the task in `transformation-plan.md`: the
   plan's owner is `design-microservices`, which writes a `characterization gate: TBD (OQ-…)`
   placeholder per step — replace the placeholder for the steps whose modules are now pinned;
   when a plan written before that contract has no placeholder, append one line to the step's
   row naming the task and say in the report that the plan was amended.

`--dry-run` builds the seam inventory and reports what would be recorded, running nothing.

## Output

| File | Content |
|------|---------|
| `<test root>/**/characterization/` | The tests, per module and seam (recording mode via `-Precord`), plus the mask-derivation script |
| `<test root>/resources/characterization/<module>/` | Recorded fixtures (`seam`, `input`, `observed`, `masks`) |

`<test root>` is the project's own `src/test/` when it has a test tree; otherwise
`generated/characterization/<module>/` is a **standalone Gradle project** whose main source set
points read-only at the legacy `src/main/` with the legacy dependency set, and `<test root>` is its
`src/test/` — the legacy tree is never written to.
| `reports/07_test-specs/characterization-test-coverage.md` | Seam inventory, entry points pinned / total per module, `@KnownDefect` list, unpinned entry points with reasons |

Write the report in the language configured in `work/pipeline-progress.json`
(`options.output_language`). Test code, fixtures and identifiers stay in English.

## Acceptance Criteria

- Every fixture value was produced by running the legacy system in this run — none authored from
  reading the code; the run command is recorded in the report
- Every module in scope has a seam inventory with one selected seam and the reason (two when the widest seam is defective)
- Any environment substitution is test-scope only, `src/main/` of the legacy tree is untouched, and the substitution's boundary is stated in the report
- Every defect without an id is marked `@ObservedDefect("CHAR-…")`, tabled, and queued as a follow-up
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
