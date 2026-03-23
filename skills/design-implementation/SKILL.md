---
name: design-implementation
description: |
  Define implementation specifications for domain services, repository interfaces, value objects, and exception mapping.
  Invoked via /architect:design-implementation. Used after the design phase is complete.
model: opus
user_invocable: true
---

# Implementation Design

## Desired Outcome

Generate detailed, coding-ready implementation specifications from design documents:
- Method signatures and responsibility definitions for domain services
- Repository interface specifications (CRUD + custom queries)
- Value object definitions and invariant conditions
- Exception hierarchy and external exception mapping
- Interface contracts for inter-service communication

## Acceptance Criteria

- All entities and aggregates in the design documents are covered
- Interfaces are described at an abstraction level independent of implementation technology
- When using ScalarDB, comply with @rules/scalardb-coding-patterns.md

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/03_design/ | Required | design-* skill group |
| reports/02_evaluation/ | Recommended | integrate-evaluations |

## Output

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

| File | Content |
|------|---------|
| `reports/06_implementation/domain-services-spec.md` | Service specifications |
| `reports/06_implementation/repository-interfaces-spec.md` | Repository specifications |
| `reports/06_implementation/value-objects-spec.md` | Value object definitions |
| `reports/06_implementation/exception-mapping-spec.md` | Exception mapping |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-microservices | Input source |
| /architect:design-scalardb | Input source |
| /architect:generate-test-specs | Output consumer |
| /architect:generate-scalardb-code | Output consumer |
