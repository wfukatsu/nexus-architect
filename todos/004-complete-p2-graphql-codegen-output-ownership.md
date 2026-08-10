---
status: complete
priority: p2
issue_id: "004"
tags: [code-review, architecture, tooling, graphql, codegen]
dependencies: ["002"]
---

# Give GraphQL code generation a unique completion signal

## Problem Statement

`generate-graphql-code` can be reported completed based entirely on pre-existing or sibling-owned
files. This makes the codegen dashboard claim a generation run occurred when it did not.

## Findings

All four declared outputs are non-unique:

- GraphQL resources may pre-exist in an application.
- `src/main/java/` is also written by other generators.
- Both contract-map files are shared with `generate-api-code` and hand implementation.

A temporary fixture with those four paths and no phase registry entry produced
`status=completed`, `source=derived`, `written=4/4`.

Locations:

- `tools/lib/pipeline_status_data.py:454`
- `tools/lib/pipeline_status_data.py:458`
- `skills/generate-graphql-code/SKILL.md:128`

## Proposed Solutions

### Option 1: Emit a protocol-specific generation report

Write `reports/06_implementation/graphql-code-generation.md` with source root, generated bindings,
versions, commands, and test results, and make it the unique required output.

- Pros: reliable completion evidence and useful audit trail.
- Cons: one additional report.
- Effort: Small.
- Risk: Low.

### Option 2: Rely only on explicit progress stamps

Declare no filesystem outputs for this extension phase.

- Pros: no extra artifact.
- Cons: older/manual runs cannot be derived; an omitted stamp hides completed work.
- Effort: Small.
- Risk: Medium.

## Recommended Action

Use Option 1 and keep the current paths as informational outputs if the status model can distinguish
required evidence from shared artifacts.

## Technical Details

The fix should preserve the combined contract map. Do not split it into conflicting REST and GraphQL
maps merely to obtain ownership.

## Acceptance Criteria

- [x] Pre-existing SDL, Java source, and combined map do not complete the generator phase.
- [x] A successful generation emits unique evidence with command/test results.
- [x] Hybrid REST/GraphQL generation remains additive.
- [x] Status and codegen-view tests cover sibling-owned outputs.

## Work Log

### 2026-08-10 - Review finding recorded

**By:** Codex

**Actions:** Reproduced derived completion without running the generator.

**Learnings:** Shared code roots and shared contract maps are unsuitable as sole completion evidence.

### 2026-08-10 - Resolved

**By:** Codex

**Actions:** Made `graphql-code-generation.md` the phase-owned completion evidence while preserving
the combined protocol map; added shared-output-only and owned-report fixtures.

**Verification:** `python3 tools/lib/pipeline_status_data.test.py` passed.

## Resources

- Review target: `b453885`
