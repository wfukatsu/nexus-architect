---
status: complete
priority: p1
issue_id: "002"
tags: [code-review, architecture, graphql, pipeline]
dependencies: []
---

# Prevent GraphQL design false completion

## Problem Statement

The pipeline can mark `design-graphql` completed before the skill runs. That allows the design review
phases to execute without the resolver, authorization, batching, query-governance, and transport
artifacts they are intended to review.

## Findings

- `design-api` owns `reports/03_design/api-specifications/graphql/` for its operation inventory.
- `design-graphql` declares that same directory as its only manifest output.
- Pipeline status treats a pending phase with all declared output paths present as derived-completed.
- A fixture containing only `graphql/inventory.md` produced `status=completed`, `source=derived`,
  `written=1/1`, and `runnable=false` for `design-graphql`.

Locations:

- `skills/common/skill-dependencies.yaml:134`
- `skills/common/skill-dependencies.yaml:142`
- `skills/design-api/SKILL.md:111`

## Proposed Solutions

### Option 1: Declare every required GraphQL design artifact

List resolver contracts, authorization matrix, batch plan, query governance, and transport design as
individual manifest outputs; use a schema glob only for the service SDL.

- Pros: accurate completion and partial-progress reporting; matches the skill's Output table.
- Cons: service SDL remains a glob/directory concern.
- Effort: Small.
- Risk: Low.

### Option 2: Add a unique completion marker

Have `design-graphql` write a dedicated summary/manifest file and declare only that file.

- Pros: simple completion signal.
- Cons: hides partial output completeness and adds an administrative artifact.
- Effort: Small.
- Risk: Medium.

## Recommended Action

Use Option 1 and add a regression fixture proving that an inventory-only directory leaves the phase
pending while the full declared set completes it.

## Technical Details

Affected components: architect phase manifest, status derivation tests, GraphQL design output
contract. This is merge-blocking because it bypasses a security-sensitive design phase.

## Acceptance Criteria

- [x] An inventory file written by `design-api` does not complete `design-graphql`.
- [x] Each required GraphQL design Markdown artifact is declared separately.
- [x] Partial outputs render partial progress.
- [x] The phase completes only after all required outputs exist.
- [x] REST-only conditional skipping still passes existing tests.

## Work Log

### 2026-08-10 - Review finding recorded

**By:** Codex

**Actions:** Reproduced the false-completed state with a temporary project fixture.

**Learnings:** Directory-level outputs are unsafe when adjacent phases share the directory.

### 2026-08-10 - Resolved

**By:** Codex

**Actions:** Replaced the shared directory output with the SDL glob and five owned design reports;
added inventory-only and full-output status fixtures.

**Verification:** `python3 tools/lib/pipeline_status_data.test.py` passed.

## Resources

- Review target: `b453885`
- `tools/lib/pipeline_status_data.py`
