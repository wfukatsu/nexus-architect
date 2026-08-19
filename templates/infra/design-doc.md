# Infrastructure Design Document — Template

Used by `/infra:design`. Copy the structure; write the content in the project's
`options.output_language`. Every output file starts with the frontmatter block below
(@rules/output-conventions.md).

```yaml
---
title: "<system> Infrastructure Design"
schema_version: 1
phase: "Infrastructure"
skill: infra-design
generated_at: "<ISO8601>"
input_files:
  - reports/03_design/target-architecture.md
---
```

---

# <system> Infrastructure Design

- Target clouds: AWS / Azure / GCP (as applicable)
- Target environments: local / test / staging / production (as applicable)
- Created / updated:
- Source bundle: `okf-k8s-tf` (investigation commits: `aidd-infrastructure@ed2689dc`,
  `aidd-ci-templates@44139cad`)

## 1. Requirements

| Item | Value | Grounds / why provisional if undecided |
|------|-------|----------------------------------------|
| Availability target | | |
| RTO / RPO | | |
| Performance (throughput / latency) | | |
| Data retention | | |
| Budget | | |
| Regulatory / data residency | | |

## 2. Multi-cloud premise

| Item | Decision |
|------|----------|
| Clouds and environments in scope | |
| Purpose of multi-cloud | portability / customer requirement / DR / lock-in avoidance / separate engagements |
| Concurrent operation | |
| How far commonality goes | interfaces only / implementations too |

### Portability boundary

| Layer | Policy for this system |
|-------|------------------------|
| L1 cloud-specific | |
| L2 Kubernetes abstraction | |
| L3 platform components | |
| L4 applications | |

## 2.5 Environments

Either attach `templates/infra/env-matrix.md` as a separate document or expand it here.

| Aspect | local | test | staging | production |
|--------|-------|------|---------|------------|
| Purpose | | | | |
| Applied by | | | | |
| Where the declaration lives | | | | |
| Data | synthetic only | synthetic only | | real |
| Change approval | none | | | |
| Bundle coverage | **out of scope** | observed implementation | observed implementation | **no observed implementation** |

### Cloud × environment grid

| | local | test | staging | production |
|---|---|---|---|---|
| AWS | | | | |
| Azure | | | | |
| GCP | | | | |

### Identical across environments / allowed to differ

| | Items |
|---|---|
| Identical | image digest, Kubernetes base, chart version, label names, secrets-never-committed rule |
| May differ | replicas, resources, storage, hostname, retention, alert routing, sampling, scaling |

### Not reproduced locally

| Not reproduced | Substitute | Where it is verified instead |
|----------------|-----------|------------------------------|

## 3. Ownership split

| Resource | Where the declaration lives | Applied by | State / history |
|----------|-----------------------------|------------|-----------------|

> Confirmed that every resource has exactly one owner: yes / no (if no, state why)

## 4. Configuration

### 4.1 Cloud foundation (L1)
### 4.2 Kubernetes (L2)
### 4.3 Shared components (L3)
### 4.4 Delivery (L4)
### 4.5 Secrets
### 4.6 Observability
### 4.7 Policy

(Each section carries a diagram, the chosen technology, its version, and the bundle document
that grounds it.)

## 5. Apply flow and promotion path

### Apply flow

1.
2.
3.

### Promotion path

```
local ──▶ test ──E2E──▶ staging ──▶ production
```

| Segment | Unit of promotion | Trigger | Approval | Evidence |
|---------|-------------------|---------|----------|----------|
| test → staging | | | | |
| staging → production | | | | |

> What is promoted is a digest. The bundle has no implementation fact for the production apply
> path, so the decision made here is recorded as an ADR.

## 6. Change-impact matrix

| Change | What must be checked at the same time |
|--------|---------------------------------------|
| Kubernetes version | |
| Provider version | |
| Helm chart version | |
| ServiceAccount / namespace | |
| Image repository / tag | |
| Secret path | |

## 7. Failure and recovery

| Scenario | Detection | Impact | Recovery procedure | Test frequency | Test environment |
|----------|-----------|--------|--------------------|----------------|------------------|

> Restore is not the same thing as having a backup. State the environment (usually staging) and
> the frequency at which restore is actually exercised.

## 8. Design decisions (ADR index)

| ID | Decision | Options | Chosen | Recorded in |
|----|----------|---------|--------|-------------|

## 9. Open questions (unresolved)

| # | Item | Who decides | By when |
|---|------|-------------|---------|

## 10. Bundle addendum candidates

| Item | Document it belongs in |
|------|------------------------|
