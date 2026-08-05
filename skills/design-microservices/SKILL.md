---
description: |
  Design target microservices architecture and transformation plan.
  /architect:design-microservices to invoke. Requires redesign output as a prerequisite.
model: opus
user_invocable: true
---

# Microservices Design

## Desired Outcome

1. **Target Architecture** -- Service catalog, classification, communication patterns, Mermaid diagrams
2. **Transformation Plan** -- Incremental migration roadmap from legacy

Service classification:
- **Process**: Stateful, participates in cross-service transactions
- **Master**: CRUD-centric, master data management
- **Integration**: External system integration adapters
- **Supporting**: Cross-cutting concerns (authentication, notifications, etc.)

For each cross-service transaction in the target architecture, name the mechanism it uses rather
than defaulting to "Saga/2PC" (@rules/scalardb-2pc-patterns.md):

| Mechanism | Topology |
|-----------|----------|
| One-phase commit | Shared-cluster pattern — every service uses one ScalarDB Cluster instance. The documented recommendation whenever possible |
| Global Transaction API (ScalarDB 3.19+) | Separated clusters with a Transaction Coordinator node driving 2PC underneath; application code stays one-phase |
| Application-driven 2PC | Separated clusters without a Coordinator node, Core-only, or Spring Data JDBC. Keep to 2-3 services |
| ScalarDB Saga | Eventual consistency with compensations or TCC — see @rules/scalardb-saga-patterns.md |

The choice drives the deployment view (one Cluster instance vs several, plus the Coordinator table
owner, plus a saga server if used), so make it here and carry it into `/architect:design-scalardb`.

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/03_design/bounded-contexts-redesign.md | Required | /architect:redesign |
| reports/03_design/context-map.md | Recommended | /architect:redesign |
| reports/03_domain/architecture.md | Optional | /product:design-architecture — when present, treat its `ARCH-` runtime/deployment views as the **candidate architecture to refine** (confirm or override each element with a recorded reason), not as something to re-derive from scratch (@docs/design.md §1.3) |
| reports/03_domain/tech-stack-fitness.md | Optional | /product:design-architecture — Adopt/Conditional/Reject verdicts inform platform-technology placement |

## Output

| File | Content |
|------|---------|
| `reports/03_design/target-architecture.md` | Service catalog, architecture diagrams |
| `reports/03_design/transformation-plan.md` | Incremental migration roadmap |

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:redesign | Input source |
| /architect:design-scalardb | Output destination |
| /architect:design-api | Output destination |
