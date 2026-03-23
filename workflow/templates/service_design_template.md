# Microservice Design Document Template

> Create this template for each microservice that uses ScalarDB.
> Fill in the `[...]` placeholders with project-specific information.

---

## 1. Service Overview

| Item | Details |
|------|------|
| Service Name | [Service name] |
| Responsibilities | [Describe this service's responsibilities in 1-2 sentences] |
| Bounded Context | [Bounded context this service belongs to] |
| Owner Team | [Responsible team] |

---

## 2. Domain Model

| Item | Details |
|------|------|
| Aggregate Root | [Aggregate root entity name] |
| Entities | [List of entities] |
| Value Objects | [List of VOs] |
| Domain Events | [List of published events] |

---

## 3. Data Model

| Table Name | Namespace | Backend DB | ScalarDB Managed | Partition Key | Clustering Key | Secondary Index |
|------------|-----------|---------------|-----------------|---------------|----------------|-----------------|
| [Table name] | [namespace] | [MySQL / PostgreSQL / Cassandra / DynamoDB] | [Yes / No] | [Column name] | [Column name ASC/DESC] | [Column name] |
| [Table name] | [namespace] | [MySQL / PostgreSQL / Cassandra / DynamoDB] | [Yes / No] | [Column name] | [Column name ASC/DESC] | [Column name] |
| [Table name] | [namespace] | [MySQL / PostgreSQL / Cassandra / DynamoDB] | [Yes / No] | [Column name] | [Column name ASC/DESC] | [Column name] |

---

## 4. Transaction Design

| Operation Name | Pattern | Scope | Isolation Level | Notes |
|--------|---------|---------|-----------|------|
| Intra-service operation | [Consensus Commit / JDBC] | [Single service] | [SNAPSHOT / SERIALIZABLE] | [...] |
| Cross-service operation (2PC) | [Two-Phase Commit] | [List of target services] | [SNAPSHOT / SERIALIZABLE] | [Coordinator: ...] |
| Asynchronous operation (Saga/Event) | [Saga / Event-Driven] | [List of target services] | [Eventual consistency] | [Compensating transaction: ...] |

---

## 5. API Design

| Method | Endpoint | Description | Authentication | Rate Limit |
|---------|--------------|------|------|-----------|
| [GET / POST / PUT / DELETE] | [/api/v1/...] | [...] | [JWT / mTLS / API Key] | [req/sec] |
| [GET / POST / PUT / DELETE] | [/api/v1/...] | [...] | [JWT / mTLS / API Key] | [req/sec] |
| [GET / POST / PUT / DELETE] | [/api/v1/...] | [...] | [JWT / mTLS / API Key] | [req/sec] |

---

## 6. Inter-Service Communication

| Target Service | Protocol | Pattern (Sync/Async) | Failure Behavior |
|--------------|-----------|----------------------|----------------|
| [Service name] | [gRPC / REST / Message Queue] | [Sync / Async] | [Retry / Circuit Breaker / Fallback] |
| [Service name] | [gRPC / REST / Message Queue] | [Sync / Async] | [Retry / Circuit Breaker / Fallback] |
| [Service name] | [gRPC / REST / Message Queue] | [Sync / Async] | [Retry / Circuit Breaker / Fallback] |

---

## 7. Non-Functional Requirements

| Item | Target Value | Measurement Method |
|------|--------|---------|
| Availability | [99.9% / 99.95% / 99.99%] | [Synthetic monitoring / Health check] |
| Latency (P99) | [ms] | [APM tool / Prometheus histogram] |
| Throughput | [req/sec] | [Load testing / Metrics] |
| Data Retention Period | [Days / Months / Years] | [TTL / Batch deletion / Archiving] |

---

## 8. Security

| Item | Details |
|------|------|
| Authentication Method | [JWT / mTLS / ...] |
| Required ScalarDB RBAC Roles | [Role name] |
| Contains Personal Data | [Yes / No] |
| Encryption Requirements | [Field-level / In-transit / At-rest] |

---

## 9. Monitoring & Alerts

| Metric Name | Threshold | Alert Destination |
|-------------|------|-----------|
| [Error rate] | [> 1%] | [Slack / PagerDuty / Email] |
| [Latency P99] | [> 500ms] | [Slack / PagerDuty / Email] |
| [CPU utilization] | [> 80%] | [Slack / PagerDuty / Email] |
| [ScalarDB transaction conflict rate] | [> 5%] | [Slack / PagerDuty / Email] |
| [2PC timeout rate] | [> 0.1%] | [Slack / PagerDuty / Email] |

**Important Log Patterns:**
- [Transaction retry exceeded: WARN level]
- [2PC coordinator failure: ERROR level]
- [Transaction conflict (OCC Conflict): WARN level]
- [...]

---

## 10. Dependencies

| Dependency | Type (Sync/Async) | Impact on Failure | Fallback |
|--------|-------------------|-----------|--------------|
| [Service name / Infrastructure] | [Sync / Async] | [Critical / Degraded / No impact] | [Return cached value / Default value / Error response] |
| [Service name / Infrastructure] | [Sync / Async] | [Critical / Degraded / No impact] | [Return cached value / Default value / Error response] |
| [Service name / Infrastructure] | [Sync / Async] | [Critical / Degraded / No impact] | [Return cached value / Default value / Error response] |
