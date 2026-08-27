---
description: |
  Design ScalarDB schema, transaction boundaries, and storage backend.
  /architect:design-scalardb to invoke. For ScalarDB projects only.
  Do NOT use for projects not using ScalarDB (use /architect:design-data-layer instead).
model: opus
user_invocable: true
---

# ScalarDB Design

## Desired Outcome

Design a data architecture leveraging ScalarDB:
1. **Schema Design** -- Partition keys, clustering keys, secondary indexes
2. **Transaction Boundaries** -- Selection and boundary definition across the four cross-service mechanisms (one-phase shared cluster / Global Transaction API / 2PC / ScalarDB Saga)
3. **Migration Plan** -- Migration strategy from existing databases to ScalarDB

## Decision Criteria

- Ground the design in the version-pinned OKF knowledge bundle (@rules/okf-knowledge-bundle.md): pin the project's ScalarDB version and edition first, then read the `design`-phase concepts (`design.md`, `data-modeling.md`, `consensus-commit.md`) of that release only. Context7 MCP is the fallback when the bundle is unavailable
- **Choose the cross-service mechanism before designing any transaction that spans services**, in this order (@rules/scalardb-2pc-patterns.md):
  1. Shared-cluster pattern with the one-phase interface — the documented recommendation whenever possible
  2. Global Transaction API + Transaction Coordinator (ScalarDB 3.19+, Cluster) — separated clusters without hand-written 2PC
  3. Application-driven 2PC — pre-3.19, no Coordinator node, Core-only, or Spring Data JDBC. Limit to a maximum of 2-3 services
  4. ScalarDB Saga (@rules/scalardb-saga-patterns.md) — when a single ACID transaction is not possible or not wanted and compensation is business-acceptable
  Record which option was chosen and why in `scalardb-transaction.md`
- Design keys targeting an OCC conflict rate below 5%
- Select storage backend based on requirements (JDBC/Cassandra/DynamoDB, etc.)
- Do not use DB-specific features on ScalarDB-managed tables

### Saga design checklist (mandatory when any process uses a saga)

Every saga in `scalardb-transaction.md` MUST specify all five of the following — each was a
blocker-or-major finding the first time it was left implicit:

1. **Durable start**: the saga state row is committed **in the same transaction** as the business
   write that triggers it (or via an outbox). An in-process async handoff after commit loses the
   saga on a crash.
2. **Enumeration**: an index table (or equivalent) from which non-terminal sagas
   (RUNNING/COMPENSATING/ESCALATED) can be listed without a cross-partition scan.
3. **Recovery ownership**: a recovery worker with a lease (owner_id/lease_until CAS takeover
   semantics) — a dead orchestrator cannot escalate itself.
4. **Pivot definition**: which step is the pivot, what compensates before/at it, and what rolls
   forward after it.
5. **Idempotency guard semantics**: the guard suppresses re-execution of EXECUTED steps only —
   FAILED steps must remain retryable (a bare conditional-insert-per-step blocks legitimate
   transient retries).

### TCC / expiring-state checklist (mandatory when any process uses TCC or timed reservations)

1. **Sweeper exclusivity**: the expiry sweeper acquires a lease (CAS on a checkpoint row) so
   multiple instances cannot double-run.
2. **Catch-up**: the sweeper resumes from a persisted checkpoint, not from "now" — a scheduler
   outage must not permanently strand expired state.
3. **Clock skew**: expiry and lease comparisons declare an explicit grace window and the NTP
   assumption.
4. **In-transaction expiry races**: state consumed inside another transaction (e.g. a reservation
   consumed by a 2PC) re-checks expiry in-tx and documents how the OCC conflict with the sweeper
   resolves.

Detailed patterns: @rules/scalardb-coding-patterns.md
Cross-service transactions: @rules/scalardb-2pc-patterns.md
Saga / TCC: @rules/scalardb-saga-patterns.md
Edition comparison and version support: @rules/scalardb-edition-profiles.md

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/03_design/target-architecture.md | Required | /architect:design-microservices |
| reports/01_analysis/data-model-analysis.md | Recommended | /architect:analyze-data-model |
| reports/03_design/state-machines/state-machine-manifest.json | Optional | /architect:design-state-machine — the state column and its OCC scope, the transition history store, and the per-transition consistency class that fixes which transitions sit in one transaction (@rules/state-modeling.md §5–6) |

## Available Resources

- **OKF knowledge bundle** -- Version-pinned official ScalarDB/ScalarDL docs at `knowledge/okf-scalardb-scalardl/okf/` (resolution and usage: @rules/okf-knowledge-bundle.md) — primary source
- **Context7 MCP** -- Fetch latest ScalarDB documentation (libraryId: /llmstxt/scalardb_scalar-labs_llms-full_txt) — fallback, not version-pinned
- **research/** -- Pre-research materials (16 documents)

## Output

| File | Content |
|------|---------|
| `reports/03_design/scalardb-schema.md` | Table design, key strategy |
| `reports/03_design/scalardb-transaction.md` | Transaction boundaries, pattern selection |
| `reports/03_design/scalardb-migration.md` | Data migration plan |

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

Before marking the phase complete, run the cross-reference lint and fix its findings — it catches
table-count drift and namespace-name variants at the source:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/validate-cross-references.py" .
```

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-microservices | Input source |
| /architect:review-scalardb | Review target |
| /architect:design-api | Related |
