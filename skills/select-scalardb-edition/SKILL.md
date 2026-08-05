---
description: |
  Interactive selection of the optimal ScalarDB edition (Community/Enterprise Standard/Premium,
  plus the separately contracted Enterprise Option add-ons), deployment mode, and cluster topology.
  /architect:select-scalardb-edition to invoke.
model: sonnet
user_invocable: true
---

# ScalarDB Edition Selection

## Desired Outcome

Select the optimal ScalarDB edition, deployment mode, and — when the system is microservices — the
cluster topology and cross-service transaction mechanism, based on project requirements.

## Decision Criteria

Use AskUserQuestion to confirm the following step by step:
1. Need for multi-DB distributed transactions
2. Whether an SQL / JDBC / Spring Data JDBC / GraphQL interface is required (**Enterprise Premium**,
   not Standard — this is the most common mis-scoping)
3. Whether analytical queries (HTAP) are required (ScalarDB Analytics is an **Enterprise Option**,
   contracted separately from Premium — not included in it)
4. Whether encryption at rest / wire encryption, or attribute-based access control, is required
   (Premium; ABAC is an **Enterprise Premium Option** and in Private Preview)
5. Whether transactions must span microservices, and if so which mechanism — shared cluster
   (one-phase), Global Transaction API with a Transaction Coordinator (3.19+), application-driven
   2PC, or ScalarDB Saga for eventual consistency. See @rules/scalardb-2pc-patterns.md
6. Support level requirements — SLA figures come from the commercial contract, not the edition name;
   do not state one that has not been confirmed

Also pin the **version line** as part of the selection: 3.15 and 3.14 are past maintenance support.

Edition comparison, feature matrix, version support windows: @rules/scalardb-edition-profiles.md
Cross-service mechanism selection: @rules/scalardb-2pc-patterns.md, @rules/scalardb-saga-patterns.md
Version-pinned feature/edition facts: @rules/okf-knowledge-bundle.md — verify each edition-gated
feature against the pinned release's concepts (frontmatter `editions` / `feature_status`) before
recommending it, and flag Private Preview features explicitly.

## Output

| File | Content |
|------|---------|
| `reports/03_design/scalardb-edition-selection.md` | Selection result and rationale — edition, version line, deployment mode, cluster topology, and any separately contracted Option add-ons |

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-scalardb | Output destination (uses edition information as input) |
