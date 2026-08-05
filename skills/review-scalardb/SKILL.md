---
description: |
  Review ScalarDB-specific constraints (2PC scope, OCC contention, schema compatibility).
  For ScalarDB-enabled projects only. Used as one perspective within the parallel review system.
model: sonnet
user_invocable: true
---

# ScalarDB Constraint Review

## Knowledge Grounding

Constraint claims (version-specific limits, config keys, edition-gated features) are verified
against the project's pinned ScalarDB release in the OKF knowledge bundle
(@rules/okf-knowledge-bundle.md), not against memory. Cite the concept's `resource` URL as
evidence when a finding depends on documented behavior.

## Review Dimensions

### 1. Cross-Service Transaction Mechanism (weight: 0.40)
- Whether the design names a mechanism per cross-service transaction rather than defaulting to 2PC
- Whether a simpler mechanism was available and skipped (shared-cluster one-phase commit; the
  Global Transaction API on ScalarDB 3.19+ Cluster)
- Whether hand-written 2PC transactions are contained within a maximum of 2-3 services
- Detection of transactions spanning 4+ services
- Application points for ScalarDB Saga, and whether compensations are defined and idempotent

### 2. OCC Contention Analysis (weight: 0.35)
- Identification of write hotspots
- Whether the design can achieve an OCC conflict rate below 5%
- Contention mitigation strategies (partitioning, CQRS, etc.)

### 3. Schema and API Compatibility (weight: 0.25)
- Validity of partition/clustering key design
- Necessity of secondary indexes and their performance impact
- Compliance with the constraints of the release the project pinned
- Whether edition-gated features are within the project's contracted edition (SQL/JDBC and GraphQL
  are Enterprise **Premium**; Analytics is an Enterprise **Option**; ABAC is an Enterprise Premium
  Option and in Private Preview) — see @rules/scalardb-edition-profiles.md
- Whether the pinned version line is still under maintenance support

## Execution

### Step 1: Collect Input File Paths

Glob for all available ScalarDB design documents:
- `reports/03_design/scalardb-*.md`
- `reports/03_design/target-architecture.md`
- `reports/03_design/transformation-plan.md`
- `reports/03_design/api-specifications/**/*.md` (if exists)

Record the full list of found file paths — these will be passed to sub-agents.

### Step 2: Spawn Three Parallel Dimension Reviewers

In a **single message**, issue all three Task() calls simultaneously so they run in parallel:

**Task A — Cross-Service Transaction Mechanism (SDB-1xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Cross-service transaction mechanism dimension review",
  prompt: """
You are a ScalarDB architect reviewing designs for the CROSS-SERVICE TRANSACTION MECHANISM.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

ScalarDB offers four mechanisms for a transaction that spans services, in order of preference:
1. Shared-cluster pattern with the one-phase commit interface — every service uses one ScalarDB
   Cluster instance. This is the documented recommendation "whenever possible".
2. Global Transaction API (`GlobalTransactionManager`, ScalarDB 3.19+ Cluster) — separated Cluster
   instances with a Transaction Coordinator node driving 2PC underneath; application code stays
   one-phase. Available only if the project pins 3.19 or later on an Enterprise edition.
3. Application-driven two-phase commit — required pre-3.19, without a Coordinator node, on Core
   (Community) only, or with Spring Data JDBC. ScalarDB recommends such transactions span at most
   2-3 services.
4. ScalarDB Saga — eventual consistency with compensations (SAGA) or reservations (TCC), for cases
   where a single ACID transaction is not possible or not wanted.

Evaluate ONLY the Cross-Service Transaction Mechanism dimension:
- Does the design name a mechanism for each cross-service transaction, with a recorded reason?
- Was a simpler mechanism available and skipped (shared cluster, or Global Transaction API when the
  pinned version and edition allow it)?
- Are hand-written 2PC transactions contained within 2-3 services maximum?
- Are there transactions spanning 4+ services that should use Saga instead?
- Where Saga is used, is a compensation defined for every step, and are the steps idempotent?

Score 1-5: 5=Exemplary (mechanism chosen and justified per transaction, simplest viable option
used), 4=Good, 3=Acceptable, 2=Concerning, 1=Critical (wide hand-written 2PC scope, or no
mechanism stated)

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Cross-Service Transaction Mechanism",
  "weight": 0.40,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "SDB-1<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<mechanism or scope issue and its impact on transaction reliability and complexity>",
      "recommendation": "<the mechanism to switch to, or the scope reduction to make>"
    }
  ]
}
"""
)
```

**Task B — OCC Contention Analysis (SDB-2xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "OCC contention analysis dimension review",
  prompt: """
You are a ScalarDB architect reviewing designs for OCC CONTENTION ANALYSIS.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

ScalarDB uses Optimistic Concurrency Control (OCC). Conflict rates above 5% degrade performance significantly.

Evaluate ONLY the OCC Contention Analysis dimension:
- Which tables/partitions are write hotspots (multiple concurrent writes to the same partition key)?
- Can the design achieve an OCC conflict rate below 5% under expected load?
- Are contention mitigation strategies applied (partitioning, CQRS, event sourcing, etc.)?

Score 1-5: 5=Exemplary (minimal hotspots, clear mitigation), 4=Good, 3=Acceptable, 2=Concerning, 1=Critical (high contention)

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "OCC Contention Analysis",
  "weight": 0.35,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "SDB-2<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<hotspot or contention pattern and its performance impact>",
      "recommendation": "<specific partitioning or design change>"
    }
  ]
}
"""
)
```

**Task C — Schema and API Compatibility (SDB-3xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Schema and API compatibility dimension review",
  prompt: """
You are a ScalarDB architect reviewing designs for SCHEMA AND API COMPATIBILITY.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate ONLY the Schema and API Compatibility dimension, against the constraints of the ScalarDB
release the design pins (state the version you assumed if the design does not name one):
- Partition key design (even distribution, no hot partitions, no monotonically increasing sole partition keys)
- Clustering key design (appropriate sort order for access patterns)
- Secondary indexes (only where necessary; avoid high-cardinality indexes on some backends)
- API usage (Put is deprecated since 3.13; use Insert/Upsert/Update instead)
- Exception handling (specific conflict exceptions caught before parent classes). The 3.19 recovery
  APIs — finishTransaction(), recoverRecord() — are low-level operational APIs; flag any design
  that calls them from application error handling
- Edition fit: SQL / JDBC / Spring Data JDBC / GraphQL require Enterprise **Premium** (not
  Standard); ScalarDB Analytics is a separately contracted Enterprise **Option**; ABAC is an
  Enterprise Premium **Option** and in Private Preview. Flag any feature used outside the
  project's stated edition
- Version support: flag a design pinned to ScalarDB 3.15 or 3.14, which are past maintenance support

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Schema and API Compatibility",
  "weight": 0.25,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "SDB-3<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<schema or API issue and its constraint violation>",
      "recommendation": "<specific fix per ScalarDB constraints>"
    }
  ]
}
"""
)
```

### Step 3: Merge and Write Output

After all three Tasks complete, compute the weighted score and write output:

```
weighted_score = round(0.40 × scoreA + 0.35 × scoreB + 0.25 × scoreC, 2)
```

Write `reports/review/individual/review-scalardb.json`:
```json
{
  "perspective": "scalardb",
  "reviewer": "review-scalardb",
  "timestamp": "<ISO-8601 now>",
  "dimensions": [<Task A result>, <Task B result>, <Task C result>],
  "weighted_score": <computed>,
  "summary": "<2-3 sentences synthesizing ScalarDB constraint compliance and key risks>"
}
```

## Output Format

Finding ID prefix: **SDB-**
- SDB-1xx: Cross-Service Transaction Mechanism
- SDB-2xx: OCC Contention Analysis
- SDB-3xx: Schema and API Compatibility
