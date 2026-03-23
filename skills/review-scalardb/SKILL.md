---
name: review-scalardb
description: |
  Review ScalarDB-specific constraints (2PC scope, OCC contention, schema compatibility).
  For ScalarDB-enabled projects only. Used as one perspective within the parallel review system.
model: sonnet
user_invocable: true
---

# ScalarDB Constraint Review

## Review Dimensions

### 1. 2PC Scope Compliance (weight: 0.40)
- Whether 2PC transactions are contained within a maximum of 2-3 services
- Detection of transactions spanning 4+ services
- Application points for the Saga pattern

### 2. OCC Contention Analysis (weight: 0.35)
- Identification of write hotspots
- Whether the design can achieve an OCC conflict rate below 5%
- Contention mitigation strategies (partitioning, CQRS, etc.)

### 3. Schema and API Compatibility (weight: 0.25)
- Validity of partition/clustering key design
- Necessity of secondary indexes and their performance impact
- Compliance with ScalarDB v3.17+ constraints

## Output Format

JSON (same schema as review-consistency). Finding ID prefix: **SDB-**
