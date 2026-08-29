---
description: |
  Generic database design for non-ScalarDB projects.
  /architect:design-data-layer to invoke. For projects not using ScalarDB.
  Do NOT use for ScalarDB projects (use /architect:design-scalardb instead).
model: opus
user_invocable: true
---

# Data Layer Design

## Desired Outcome

Generic data layer design for projects not using ScalarDB:
- Database selection and configuration (RDB/NoSQL/hybrid)
- Connection pool design
- Migration strategy
- Transaction management patterns
- ORM/data access patterns
- The read model / CQRS / event sourcing decision per aggregate — default *neither*; adopt for a
  named reason with the projection lag and rebuild cost stated (the same table
  `/architect:design-scalardb` records; `review-data-integrity` reads it as *undecided* when absent)

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/03_design/target-architecture.md | Required | /architect:design-microservices |
| reports/03_design/aggregates/aggregate-manifest.json | Optional | /architect:design-aggregate — the aggregate as the concurrency scope and the unit one transaction writes, one repository per root |
| reports/03_design/state-machines/state-machine-manifest.json | Optional | /architect:design-state-machine — the state column, its concurrency scope, and whether transition history is recorded (@rules/state-modeling.md §6) |
| reports/04_quality/nfr.md | Optional | /product:define-nfr — read-latency and reporting targets for the Read Model / CQRS / Event Sourcing decision; absent, take them from `requirements-definition.md`'s NFR table, and ask what neither states (@rules/open-questions.md) |

## Output

| File | Content |
|------|---------|
| `reports/03_design/data-layer-design.md` | DB design, transaction management, migration, the Read Model / CQRS / Event Sourcing decision per aggregate |

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

## Architecture Decision Records

The decisions this skill makes that a later phase depends on — the storage engine and consistency mechanism, and the CQRS / Event Sourcing adoption verdicts — are each recorded as
`reports/03_design/adr/adr-NNN-<slug>.md` under @rules/architecture-decision-records.md: allocate
`ADR-` as `max + 1` over `work/traceability.json` and the directory (`redesign` registers the
prefix; this skill appends), cite what drove the decision in `upstream` — typically `AGG-` / `STM-` / `NFR-` nodes, or `reports/` paths on the legacy path, per the rule's §2 (never
empty), list the alternatives rejected, append one `{ "type": "decision" }` node per record to
the graph, regenerate `index.md`, and run
`python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/adr_records.py" <project_dir>` before completing. A
record you disagree with is superseded by a new one, never edited.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-microservices | Input source |
| /architect:review-data-integrity | Review target |
