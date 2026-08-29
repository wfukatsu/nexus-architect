---
description: |
  Verify that the code that exists actually implements the design — API contract, transaction placement,
  security controls, and requirement coverage — and report every divergence instead of smoothing it over.
  Optionally runs the AI code quality gate.
  /architect:verify-implementation [target_path] [--service=<name>] [--scope=changed|service|repo]
  [--source-root=<path>] [--gate] [--item=<backlog-id>] [--auto] [--lang=en|ja] to invoke.
  Runs after code generation or backlog implementation, and as the conformance stage of the quality gate.
model: opus
user_invocable: true
disable-model-invocation: true
---

# Implementation Verification (Design ↕ Code)

For GraphQL, apply @rules/graphql-contract-fidelity.md and
@rules/graphql-security-checks.md. Inventory SDL field coordinates, annotated controller methods and
programmatic runtime wiring independently; the contract map is a claim to verify.

## Desired Outcome

A conformance report that answers one question the rest of the pipeline never asks: **does the code
that exists do what the design said it would?**

Design review checks the design. Code review checks whether the code looks right. Neither compares
them. That gap is where generated code fails — a model produces plausible code far more reliably
than correct code, and plausible code survives reading. This skill executes the comparison.

Four conformance axes, each producing findings with the `VER-` prefix:

1. **Contract conformance** — code against the API specification
2. **Transaction conformance** — code against the transaction and saga design
3. **Security conformance** — code against the security design's declared controls
4. **Requirement conformance** — code and tests against the requirement graph

## Decision Criteria

- **Report drift; never silently reconcile it.** When code and design disagree, this skill does not
  edit either one. It names both sides and the difference. Which one is wrong is a decision the user
  makes — the code may be deliberate work the design has not caught up with
  (@rules/api-contract-fidelity.md §6).
- **Absence of evidence is a finding, not a pass.** An operation with no test, a transaction boundary
  that cannot be located, a security control whose enforcement point cannot be found — each is
  reported as unverifiable at the severity its subject warrants, never omitted.
- **A design that cannot be verified against is a finding against the design.** A specification with
  inline anonymous schemas, undeclared status codes, or operations with no declared authorization
  fails @rules/api-contract-fidelity.md §3; report it as a contract-quality finding rather than
  guessing what was meant.
- **Read the code, not the summary.** Never conclude conformance from a generation run's report of
  what it did.

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| The source tree under verification | Required | `generated/` for a scaffold, the project's real source tree for backlog delivery. Resolved per `--source-root`, then `api-contract-map.json`'s `source_root`, then the project's Output Location |
| reports/03_design/api-specifications/ | Required when an API surface exists | /architect:design-api |
| reports/03_design/api-specifications/problem-types.md | Required when an API surface exists | /architect:design-api |
| reports/03_design/api-specifications/operation-contracts.md | Required when an API surface exists | /architect:design-api |
| reports/06_implementation/api-layer-spec.md | Recommended | /architect:design-implementation |
| reports/06_implementation/api-contract-map.json | Recommended | /architect:generate-api-code or /architect:implement-backlog — when absent, this skill derives the mapping itself and reports that it had to |
| reports/03_design/scalardb-transaction.md | Required when scalardb_enabled | /architect:design-scalardb |
| reports/08_infrastructure/security-design.md | Recommended | /architect:design-security |
| reports/07_test-specs/ | Recommended | /architect:generate-test-specs |
| work/traceability.json | Recommended | requirement graph for axis 4 |

## Knowledge Grounding

Transaction and exception claims are checked against the project's pinned ScalarDB release in the OKF
bundle (@rules/okf-knowledge-bundle.md), not against memory — retryability, available cross-service
mechanisms, and config keys differ by version and edition. Cite the concept `resource` URL when a
finding depends on documented behavior.

## Steps

### Step 1 — Resolve scope and inputs

Resolve the source root (see Prerequisites), the specification set, and the change scope:
`--scope=changed` (default when a working branch exists — diff against the base), `service`, or `repo`.
Record what was in scope; a narrow scope reported as a full verification is the failure mode to avoid.

### Step 2 — Build the contract map

Read `reports/06_implementation/api-contract-map.json` if present, and **verify it against the code**
rather than trusting it — it is an input to check, not a source of truth. When it is absent, derive
the mapping by reading the controllers.

**Derive the route inventory from the whole target tree, every time**, including packages the map's
`scope` excludes. The map is a claim by whoever wrote it, and a generator that mis-scoped produces a
map that passes its own check: the first real run of this pipeline emitted one asserting nothing
unmapped while six routes — among them `/api/admin/users` — were reachable and undeclared. Classify
each reachable route as a mapped operation, an `out_of_scope_handlers` entry, or a finding. An
out-of-scope entry is still reported; the field records that the omission was named, not that it is
acceptable.

Produce, per @rules/api-contract-fidelity.md §4, the full operation list plus both `unmapped` arrays.
Rewrite the map file with what was actually found.

For GraphQL derive `@QueryMapping`, `@MutationMapping`, `@SubscriptionMapping`, `@SchemaMapping`,
`@BatchMapping`, and programmatically registered DataFetchers. Compare every resolver-bound field
coordinate with the SDL, preserve other protocols when rewriting, and interpret old entries without
`protocol` as REST.

### Step 3 — Contract conformance (`VER-1xx`)

Per operation, against the specification:

| Check | Finding when |
|-------|--------------|
| Handler binding | An `operationId` has no handler, has more than one, or a handler serves no operation (`unmapped`) — the second is **critical**, the third is both a contract and an inventory finding (@rules/api-security-checks.md API9) |
| Authorization actually enforced | A declared control that exists only as an inert annotation — `@PreAuthorize` without method security enabled, a filter chain whose matcher leaves the route uncovered. It reads as a control and enforces nothing |
| Test spec freshness | The specification copy under the test tree differs from the design copy under `reports/` — the contract tests are asserting against a stale contract (@rules/api-contract-fidelity.md §7) |
| Method and path | The route the code registers differs from the specification |
| Request shape | A DTO field the schema does not declare, a declared field absent, a required/optional mismatch, a type mismatch |
| Validation | A schema constraint with no corresponding Bean Validation annotation, or the request DTO not validated at the boundary |
| Response shape | Same checks on the response DTO; a property the schema does not declare is also an excessive-data-exposure finding |
| Status codes | A status the code can return that the contract does not declare, or a declared status unreachable in code |
| Error envelope | Any non-2xx response that is not RFC 9457 Problem Details, any `type` with no registry row, any registry row unreachable (@rules/api-error-standard.md §7) |
| `UnknownTransactionStatusException` | Handled by a generic branch, mapped to a `Retry-After`-bearing 503 on an operation with no idempotency protection, or rolled back — **blocker severity** (@rules/api-error-standard.md §3.1) |
| GraphQL unknown transaction status | An execution error does not use HTTP 200 and the registered `errors[].extensions.type`; protected and unprotected mutations mix retry/reconcile fields; or a raw ScalarDB transaction ID is exposed — **blocker severity** (@rules/api-error-standard.md §3.2) |
| Idempotency | An operation with a declared `Idempotency-Key` obligation whose key is not read, or whose idempotency record is written outside the business transaction |

When `api-layer-spec.md` declares `layering_style: clean`, the handler-binding check is read through
the use case: one input boundary and one interactor per operation, the controller bound to the
boundary rather than the interactor, and the presenter the specification names present. A service
whose packages mix `application/` services and `usecase/` interactors is a conformance finding —
the specification chose one vocabulary.

GraphQL adds SDL/resolver 1:1 coverage, nullability/input validation, registered
`errors[].extensions.type`, nested-field and tenant authorization, DataLoader cache partitioning,
N+1/batch behavior, query-governance enforcement, production tooling policy, safe observations and
subscription origin/authentication/lifecycle checks.

### Step 4 — Transaction conformance (`VER-2xx`)

Against `scalardb-transaction.md` (or the data-layer design) and the saga definitions:

- An operation the design places inside **one** transaction implemented as two or more, or as
  non-transactional writes — **critical**, this is silent data corruption.
- **A transaction that omits a participant the design named.** The inverse of the split above and
  easier to miss, because the code looks clean: the design says TX-003 spans order + inventory +
  payment, the implementation writes order only, and nothing about the code signals the absence.
  Read the design's participant list per transaction and check each one is actually written —
  **critical**, since it commits a state the rest of the system contradicts (an order confirmed
  against unreserved stock).
- A replay path — idempotency, cache, short-circuit — that returns before the authorization the
  full path performs (@rules/api-error-standard.md §5).
- A transaction boundary in code that does not exist in the design.
- A read-modify-write with no transaction, or a transaction never committed (including read-only
  transactions, which must still commit).
- **A `Put`/mutation on a record the transaction never read.** Consensus Commit infers insert-vs-update
  from read history, so a blind `Put` on an existing record fails at `commit()` with a *conflict*
  error that reads like contention and no retry can clear (@rules/scalardb-crud-patterns.md).
  **major**, rising to critical where the write is on the success path of a state-changing operation —
  the operation simply cannot succeed.
- Conflict exceptions reaching the API layer with no retry applied first
  (@rules/api-error-standard.md §3).
- Catch order wrong — a parent caught before its conflict subclass, making the conflict branch
  unreachable (@rules/scalardb-exception-handling.md).
- A saga step with no compensation, a compensation that is not idempotent, or a compensation that
  drops the authorization or tenant scoping its forward step applied.
- 2PC: prepare / validate / commit / abort not all present on a participant; a 2PC transaction
  spanning more services than the design allows.
- A cross-service transaction using a mechanism the pinned release or edition does not provide.

### Step 5 — Security conformance (`VER-3xx`) — delegate

Spawn `review-api-security --mode=code` over the same scope and adopt its `ASEC-` findings as this
axis, rather than re-deriving them. Report the delegation, and report explicitly when it could not
run — a security axis that silently did not execute is the failure this skill exists to prevent.

### Step 6 — Requirement conformance (`VER-4xx`)

Against `work/traceability.json` and the test specs: every `FR-` in scope reachable to code; every
acceptance criterion reachable to at least one test; every REST `operationId` and GraphQL resolver
field coordinate covered by a contract test.
A requirement with no implementation and an implementation with no requirement are both findings.

### Step 7 — Quality gate (`--gate` only)

Run the eight stages of @rules/ai-code-quality-gate.md, using axes 1–4 above as stage 8 and the
delegated `ASEC-` findings as stage 7. Execute stages 1–6 as real commands **from a clean build
state** (`./gradlew clean` first or `--rerun-tasks` per task — an UP-TO-DATE task exits 0 having run
nothing) and record exit codes and the counts the gate's own run produced.
Write `reports/09_verification/quality-gate.{json,md}`.

Never report a stage as passed without its evidence, and never omit a stage without its reason.
For stage 2, when `reports/03_design/aggregates/aggregate-manifest.json` exists, join each invariant
to the property test `property-test-specs.md` names for it and record covered / declared; an
invariant with no test class fails the stage even when every test that exists passed. Stage 2
also runs the coverage verification and the mutation run scoped to the touched `domain/` packages
(@rules/ai-code-quality-gate.md §Test quality — resolve the project's thresholds first, defaults
otherwise), records coverage per changed file and surviving mutants by file:line, and — under
`--item` — reads the working branch's log for the item to record the test-first sequence per unit
(@rules/tdd-workflow.md §6): `test:` before `feat:`, the failing tests named in the Red commit body,
and which acceptance-level test carried the outer loop. The record is reported, never a verdict; without `--item` and a working branch it is
`not-applicable`. A surviving mutant on an invariant line is a stage-2 failure unless it is recorded
as `equivalent` with evidence (§Test quality). When the API layer has not been generated, stage 3
and stage 7 are `not-applicable`, the contract map's unmapped operations are `info` with reason
`api-layer-absent`, and Step 3's "operation with no handler = critical" does not apply — it is
the whole layer that is absent, not a handler.
Stage 4 runs the `integrationTest` task and, when the project has them, the `acceptanceTest` and
`characterizationTest` tasks; on a transformation-step item the characterization result is compared
with the baseline `implement-backlog` recorded before the change, and any fixture edited between
the two is listed as a decision to confirm, not absorbed. An acceptance scenario red because two
design artefacts contradict each other is a `VER-1xx` finding naming both, and the verdict stays
FAIL until the design decides (§A stage-4 failure caused by the design).

### Step 8 — Write the report

Write both outputs, then print a summary: verdict, finding counts by severity and axis, and the
blocking IDs.

## Output

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

| File | Content |
|------|---------|
| `reports/09_verification/design-code-conformance.md` | Findings by axis, each with file:line, the design statement it contradicts, the failure scenario, and the fix |
| `reports/09_verification/design-code-conformance.json` | The same findings, machine-readable, for the gate and the fix loop |
| `reports/06_implementation/api-contract-map.json` | Rewritten with what the code actually binds (Step 2) |
| `reports/09_verification/quality-gate.json`, `reports/09_verification/quality-gate.md` | `--gate` only — the eight-stage gate result (@rules/ai-code-quality-gate.md §Gate result artifact) |

## Acceptance Criteria

- Every finding names a file and line, the design artifact and statement it contradicts, and a
  concrete failure scenario — a finding that cannot state one is reported as `info`, not inflated
- Both `unmapped` arrays in the contract map are present and populated from the code
- No design artifact and no source file was edited by this skill
- Every axis reports a result, including "not applicable" with its reason — an axis that did not run
  is never absent from the report
- Under `--gate`, every stage carries either evidence or a recorded skip reason

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-api | Input source — the contract |
| /architect:design-implementation | Input source — the API layer specification |
| /architect:design-scalardb | Input source — transaction placement |
| /architect:design-security | Input source — declared controls |
| /architect:review-api-security | Delegated to for the security axis |
| /architect:generate-api-code | Verification target |
| /architect:generate-scalardb-code | Verification target |
| /architect:implement-backlog | Calls this as Step 5c |
| /architect:review-issue | Consumes the findings as `[B]` blockers |
