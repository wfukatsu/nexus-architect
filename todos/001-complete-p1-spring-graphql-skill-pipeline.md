---
status: complete
priority: p1
issue_id: "001"
tags: [graphql, spring, scalardb, architecture, security]
dependencies: []
---

# Spring for GraphQL skill pipeline

## Problem Statement

The toolkit can design a GraphQL SDL, but its implementation, contract testing, security review,
and design-to-code verification paths are REST/OpenAPI-specific. It also does not distinguish a
Spring for GraphQL application facade from ScalarDB's edition-gated GraphQL interface.

## Findings

- `design-api` declares a GraphQL output directory without a GraphQL-specific downstream design.
- `generate-api-code`, contract tests, and verification use HTTP routes and OpenAPI operation IDs.
- GraphQL-specific authorization, query-cost, DataLoader, and subscription risks are not enforced.
- Architect extension phases are registered in `tools/lib/pipeline_status_data.py`, not the YAML.

## Proposed Solutions

1. Add only a code generator. Low effort, but leaves selection, contract, and security gaps.
2. Add a GraphQL design and generation chain while extending existing cross-cutting quality skills.
3. Create a separate GraphQL plugin. Strong isolation, but duplicates architecture workflow.

## Recommended Action

Use option 2. Keep `design-api` as the protocol decision point, add `design-graphql` as a conditional
core design phase and `generate-graphql-code` as an extension phase, and extend shared contract,
security, testing, verification, and documentation artifacts.

## Acceptance Criteria

- [x] API style selection is explicit and independent from the database product.
- [x] Spring for GraphQL and ScalarDB native GraphQL are separate design choices.
- [x] GraphQL SDL fields bind 1:1 to resolvers through stable field coordinates.
- [x] GraphQL design and code-generation skills are discoverable by Claude and Codex.
- [x] Contract tests, security review, and implementation verification cover GraphQL.
- [x] REST-only behavior and existing tests remain compatible.
- [x] Documentation and model recommendations include the new skills.

## Work Log

### 2026-08-10 - Implementation started

**By:** Codex

**Actions:**
- Created `feat/spring-graphql-skills` from `main`.
- Reviewed the approved plan, skill conventions, plugin metadata, phase manifest, and status tests.

**Learnings:**
- Core design phases live in the manifest; manual implementation phases are registered separately.
- GraphQL selection must be materialized as pipeline options after `design-api`.

### 2026-08-10 - Implementation completed

**By:** Codex

**Actions:**
- Added conditional GraphQL design and Spring code-generation skills plus three protocol rules.
- Extended contract tests, security review, verification, backlog implementation, documentation,
  quality-gate guidance, plugin metadata, status dashboard and user documentation.
- Added `tools/graphql_skills.test.py` and expanded pipeline status tests.
- Ran every repository test suite and JSON/diff validation successfully.

**Learnings:**
- The repository's Claude-compatible skill frontmatter intentionally includes keys rejected by the
  generic Codex skill validator, so project-native tests are the validation authority.
