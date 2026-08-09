---
description: |
  Define implementation specifications for the API layer (controller/DTO/validation), domain services,
  repository interfaces, value objects, and exception mapping.
  Invoked via /architect:design-implementation. Used after the design phase is complete.
model: opus
user_invocable: true
---

# Implementation Design

## Desired Outcome

Generate detailed, coding-ready implementation specifications from design documents:
- **API layer specification** — controller / DTO / mapper / application-service layering, bound to the
  API contract operation by operation
- Method signatures and responsibility definitions for domain services
- Repository interface specifications (CRUD + custom queries)
- Value object definitions and invariant conditions
- Exception hierarchy and external exception mapping, including the Problem Details mapping
- Interface contracts for inter-service communication

## API Layer Specification

This is the specification that closes the gap between the API contract and the domain: it says which
class serves which `operationId`, and what happens between the wire and the aggregate. Governed by
@rules/api-contract-fidelity.md.

Specify, per `operationId` in `reports/03_design/api-specifications/`:

| Element | Content |
|---------|---------|
| Handler | The controller class and method that serves this operation, 1:1 (§2). Method name derives from the `operationId` |
| Request DTO | Class name from the `components/schemas` key. **Never the domain object and never the persistence entity** — binding a request body straight onto an entity is the mass-assignment defect |
| Validation | The Bean Validation constraints derived from the schema: `minLength` -> `@Size`, `pattern` -> `@Pattern`, `enum` -> an enum type, `required` -> `@NotNull`. Derived, not hand-chosen; the request DTO is `@Valid` at the handler boundary |
| Mapper | The explicit DTO <-> domain mapping, listing exactly the fields the schema declares |
| Response DTO | Class name from the schema key, carrying exactly the schema's properties — this is what stops an internal field leaking when the domain model later grows |
| Application service | The method the handler delegates to, and **the transaction boundary**: which operations open a transaction, which join one, which are read-only. This must match the transaction placement recorded in `operation-contracts.md` |
| Authorization | Where the operation's declared authorization rule is enforced — the role/scope check and the object-level ownership predicate. An operation with an ownership predicate needs the check named here, not assumed |
| Idempotency | For operations carrying an `Idempotency-Key` obligation: where the key is read, where the record is stored, and the requirement that the record and the business write share **one** transaction (@rules/api-error-standard.md §5) |

The layering is directional and the direction is part of the specification: controller -> application
service -> domain -> repository. No reverse dependency, and no persistence or ScalarDB type appearing
in a controller signature. `generate-contract-tests` turns this into executable ArchUnit rules.

## Exception Mapping

`exception-mapping-spec.md` covers two mappings, not one:

1. **Internal** — infrastructure exceptions to domain exceptions, per @rules/scalardb-exception-handling.md
   (catch order, rollback, retry policy).
2. **External** — domain and infrastructure exceptions to RFC 9457 Problem Details responses, per
   @rules/api-error-standard.md §3. Every row of that table is covered, and
   `UnknownTransactionStatusException` gets its own branch per §3.1 — it is neither a plain 500 nor a
   blanket 503, and folding it into a generic handler is a blocker-severity defect downstream.

The retry policy belongs here too: a conflict exception must not reach the API layer before the
service has applied its own retries, so the specification says where retry lives and how many.

## Acceptance Criteria

- Every `operationId` in the API specifications has exactly one handler specified, and no handler is
  specified that has no `operationId`
- Every request DTO is distinct from the domain object and the persistence entity, with an explicit mapper
- Every DTO field constraint is traceable to a schema constraint — no constraint invented, none dropped
- Every operation's transaction boundary matches its placement in `operation-contracts.md`
- Every operation's authorization enforcement point is named
- Every ScalarDB exception in @rules/api-error-standard.md §3 has a mapped response, with §3.1 handled separately
- All entities and aggregates in the design documents are covered
- Interfaces are described at an abstraction level independent of implementation technology
- When using ScalarDB, comply with @rules/scalardb-coding-patterns.md

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/03_design/ | Required | design-* skill group |
| reports/03_design/api-specifications/ | Required | /architect:design-api — the contract the API layer specification binds to |
| reports/03_design/api-specifications/operation-contracts.md | Required | /architect:design-api — per-operation authorization, idempotency, timeout, transaction placement |
| reports/03_design/api-specifications/problem-types.md | Required | /architect:design-api — the problem type registry the exception mapping resolves against |
| reports/02_evaluation/ | Recommended | integrate-evaluations |

## Output

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

| File | Content |
|------|---------|
| `reports/06_implementation/api-layer-spec.md` | Per-`operationId` handler, DTOs, validation, mapper, application service, transaction boundary, authorization enforcement point, idempotency handling |
| `reports/06_implementation/domain-services-spec.md` | Service specifications |
| `reports/06_implementation/repository-interfaces-spec.md` | Repository specifications |
| `reports/06_implementation/value-objects-spec.md` | Value object definitions |
| `reports/06_implementation/exception-mapping-spec.md` | Exception mapping |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-microservices | Input source |
| /architect:design-scalardb | Input source |
| /architect:design-api | Input source — the contract the API layer specification binds to |
| /architect:generate-test-specs | Output consumer |
| /architect:generate-api-code | Output consumer — generates the API layer from `api-layer-spec.md` |
| /architect:generate-scalardb-code | Output consumer — generates the domain and persistence layers |
| /architect:verify-implementation | Output consumer — verifies the code against this specification |
