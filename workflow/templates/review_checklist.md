# Phase Review Checklist

> Use this checklist when reviewing each phase.
> Confirm all items and check them off before marking the phase as complete.

---

## Phase 1: Requirements & Decisions Review

- [ ] Are business requirements comprehensively organized?
- [ ] Are non-functional requirements (availability, performance, security) quantified?
- [ ] Was the ScalarDB applicability decision made following the decision tree?
- [ ] Was the XA vs ScalarDB comparison conducted objectively?
- [ ] Are bounded contexts appropriately divided (neither too large nor too small)?
- [ ] Is the number of ScalarDB-managed tables minimized?
- [ ] Does the 2PC scope follow the restriction guidelines (maximum 2-3 services)?

---

## Phase 2: Design Review

- [ ] Does the data model account for ScalarDB constraints (PK/CK/SI design)?
- [ ] Has the Partition Key hotspot risk been evaluated?
- [ ] Has the metadata overhead been estimated?
- [ ] Have transaction patterns been appropriately selected?
- [ ] Is the OCC conflict rate within acceptable range (< 5% recommended (design-phase guideline; align with target values in testing strategy `12_testing_strategy.md`))?
- [ ] Is the batch processing chunk size appropriate?
- [ ] Does the API design properly handle ScalarDB transaction exceptions?
- [ ] Has CDC metadata (tx_state) filtering been designed?

---

## Phase 3: Infrastructure Review

- [ ] Does the ScalarDB Cluster replica count meet availability requirements?
- [ ] Are PodDisruptionBudget / Anti-Affinity configured?
- [ ] Is TLS/mTLS enabled on all communication paths?
- [ ] Is RBAC based on the principle of least privilege?
- [ ] Is the Coordinator table protected?
- [ ] Are interim measures for audit logging implemented?
- [ ] Are the three pillars of metrics/logs/traces designed?
- [ ] Are alert thresholds configured?
- [ ] Are RPO/RTO set to realistic values?
- [ ] Have backup and restore procedures been tested?
- [ ] Has a DR runbook been created?

---

## Phase 4: Execution Review

- [ ] Are implementation tasks prioritized?
- [ ] Are ScalarDB-specific implementation patterns correctly applied?
- [ ] Is error handling within transactions (retry, abort) implemented?
- [ ] Are tests created based on the test pyramid?
- [ ] Are 2PC failure scenario tests included?
- [ ] Are performance test targets and results recorded?
- [ ] Does the deployment procedure include rollback steps?
- [ ] Are Go/No-Go decision criteria defined?
- [ ] Does the schema migration procedure consider backward compatibility?

---

## Cross-Cutting Checks

- [ ] Is terminology consistent across all documents (ubiquitous language)?
- [ ] Is the "distributed monolith" risk avoided (no excessive 2PC usage)?
- [ ] Is the principle of minimizing ScalarDB-managed scope maintained?
- [ ] Have DB-specific feature restrictions been communicated to stakeholders?
- [ ] Are ScalarDB 3.17 optimization features utilized (Piggyback Begin, Write Buffering, Batch Operations)?
- [ ] Has the READ latency impact of Transaction Metadata Decoupling been evaluated?
