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
| 2 | **Unit tests** | All pass; no test disabled or deleted in this change without a recorded reason | Command + counts (run/passed/skipped) |
| 3 | **Contract tests** | Every `operationId` the change touches is exercised and validates against the specification (@rules/api-contract-fidelity.md §7) | Command + per-operation results |
| 4 | **Integration tests** | All pass, including the transaction scenarios the design requires — OCC conflict, 2PC failure, saga compensation | Command + counts |
| 5 | **SAST** | No new high/critical finding | Tool + version + finding counts by severity, new vs pre-existing |
| 6 | **Dependency scan** | No new high/critical CVE, and no dependency added that the version rules reject (@rules/dependency-versions.md) | Tool + advisory IDs |
| 7 | **API security** | `review-api-security --mode=code` returns no critical, and no unresolved major (@rules/api-security-checks.md) | `ASEC-` findings with severities |
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
| Unit | `./gradlew test` | `npm test` |
| Contract | `./gradlew test --tests '*ContractTest'` (swagger-request-validator) | project's contract suite |
| Integration | `./gradlew integrationTest` | `npm run test:integration` |
| SAST | Semgrep (`--config auto`), or SpotBugs + `find-sec-bugs` | Semgrep |
| Dependency | OSV-Scanner, or OWASP Dependency-Check | `npm audit --audit-level=high` / OSV-Scanner |
| Secrets | Gitleaks over the change | Gitleaks |
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
    {"stage": "contract", "status": "failed",
     "command": "./gradlew test --tests '*ContractTest'", "exit_code": 1,
     "detail": "confirmOrder returned 500 for the transaction-status-unknown case; contract declares 503"},
    {"stage": "sast", "status": "skipped", "reason": "not-configured"},
    {"stage": "api-security", "status": "passed", "findings": {"critical": 0, "major": 1, "minor": 3}}
  ],
  "blocking": ["VER-004", "ASEC-011"]
}
```

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
