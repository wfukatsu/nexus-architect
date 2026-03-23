---
name: review-data-integrity
description: |
  Review data integrity, transaction safety, and schema design quality independent of ScalarDB.
  For projects not using ScalarDB. Used as one perspective within the parallel review system.
model: sonnet
user_invocable: true
---

# Data Integrity Review

## Review Dimensions

### 1. Transaction Safety (weight: 0.40)
- Appropriateness of transaction boundaries
- ACID property guarantees
- Deadlock avoidance design

### 2. Data Consistency (weight: 0.35)
- Acceptable range for eventual consistency
- Conflict resolution strategies
- Referential integrity constraints

### 3. Schema Design Quality (weight: 0.25)
- Appropriateness of normalization level
- Index design
- Migration safety

## Output Format

JSON (same schema as review-consistency). Finding ID prefix: **DIN-**
