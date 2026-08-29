---
description: |
  Generate the API layer from the OpenAPI contract — controllers, request/response DTOs, Bean Validation,
  DTO↔domain mappers, and the RFC 9457 Problem Details exception handler — bound 1:1 to the contract's
  operationIds, and emit the contract map that downstream verification checks.
  /architect:generate-api-code [--service=<name>] [--out=<path>] [--confirm-versions|--no-confirm-versions]
  [--dry-run] [--auto] [--lang=en|ja] to invoke.
  Runs after design-implementation. Independent of ScalarDB — works on the design-data-layer path too.
model: opus
user_invocable: true
disable-model-invocation: true
---

# API Code Generation

## Desired Outcome

The layer between the wire and the domain, generated from the contract rather than from an idea of
what the contract probably says:

- **Controllers** — one handler method per `operationId`, 1:1, named from it
- **Request DTOs** — from `components/schemas`, with Bean Validation derived from the schema constraints
- **Response DTOs** — carrying exactly the declared properties, and nothing the domain might grow later
- **Mappers** — explicit DTO ↔ domain conversion, field by field
- **Exception handler** — `@RestControllerAdvice` producing RFC 9457 Problem Details for every
  registered problem type
- **The contract map** — `reports/06_implementation/api-contract-map.{md,json}`, the record of what
  was bound to what

This is the layer that closes the loop between `design-api` and the domain code
`generate-scalardb-code` (or the data-layer equivalent) emits. Without it the OpenAPI document is a
report, not a contract.

## Package Ownership (the seam)

Two codegen skills write into one service tree, so the boundary is explicit — neither overwrites the
other's packages:

| Package | Owner |
|---------|-------|
| `…/api/` — controllers, DTOs, mappers, error handling, API configuration | **this skill** |
| `…/domain/`, `…/infrastructure/` — entities, repositories, domain services, transaction management | `/architect:generate-scalardb-code` (or the data-layer generator) |
| `…/application/` — application services (the transaction boundary) | this skill generates the interface and the call from the controller; the implementation body belongs to the domain generator, which is why the two are run together |
| `…/usecase/` + `…/api/presenter/` — when `api-layer-spec.md` declares `layering_style: clean` | this skill generates the input boundary, input/output data records and output boundary per operation, and the presenter under `api/presenter/`; the interactor body belongs to the domain generator. `…/application/` is not created |

A generated controller never imports a persistence or ScalarDB type. That is a rule this skill obeys
and `generate-contract-tests` enforces with ArchUnit.

## Contract Constraints (binding)

@rules/api-contract-fidelity.md §5 governs every file this skill writes. Restated because it is the
whole point of the skill:

1. **Generate only what the specification declares** — no endpoint, parameter, field, header, or
   status code beyond it. Not a health endpoint, not a debug route, not a convenient extra field.
2. **Names come from the specification** — DTO names from `components/schemas` keys, method names
   from `operationId`. Do not re-style them.
3. **Validation is derived, not chosen** — `minLength` → `@Size`, `pattern` → `@Pattern`, `enum` → an
   enum type, `required` → `@NotNull`; the request DTO is `@Valid` at the boundary.
4. **The request DTO is never the domain object or the entity** — an explicit mapper stands between
   them, mapping only declared fields. Binding a body onto an entity is the mass-assignment defect.
5. **The response DTO is never the domain object either.**
6. **Errors leave only through the Problem Details handler** — no ad-hoc `ResponseEntity.status(...)`
   anywhere, and no second error envelope.
7. **Write the contract map last.** A run that emits code and no map is incomplete.

**When the specification is missing something, stop — do not fill it in.** An operation with no
declared authorization, an inline anonymous schema, an undeclared status code: report it as a
contract-quality finding and ask per @rules/open-questions.md. Generating a plausible guess is how
the contract silently stops being the contract.

## Error Handling

The `@RestControllerAdvice` covers every row of @rules/api-error-standard.md §3, and
`UnknownTransactionStatusException` gets **its own branch** — never the generic 500 handler. The
commit may have succeeded, so it is 503 with `Retry-After` when the operation is idempotency-key
protected and 500 with no retry hint otherwise, both carrying the transaction ID as an extension
member, neither rolling back (§3.1). Getting this wrong is a blocker-severity finding in
`verify-implementation`, so generate it deliberately rather than by pattern.

`detail` strings never interpolate a §4-prohibited value — no stack traces, SQL, namespace or table
names, internal hosts, or fields the data classification marks confidential. The operator-facing
detail goes to the log, joined by `trace_id`.

Where an operation declares an `Idempotency-Key` obligation, generate the key handling with the
idempotency record written **inside the business transaction** (@rules/api-error-standard.md §5) —
a record committed separately reintroduces the duplicate the key exists to prevent.

## The Build Must Accept What Was Generated

The API layer brings its own runtime dependencies, and code the project cannot compile is not a
deliverable. Before finishing, add every dependency the generated layer requires and **verify the
module compiles** — a run that emits sources and leaves the build broken has produced nothing usable.

The ones most often missed, because the design implies them without naming them:

| Generated because the design says… | Dependency |
|---|---|
| OIDC / JWT authentication, `@AuthenticationPrincipal Jwt` | `spring-boot-starter-oauth2-resource-server` |
| Bean Validation on DTOs | `spring-boot-starter-validation` |
| `@PreAuthorize` method-level authorization | `spring-boot-starter-security` (and method security enabled — the annotation is silently inert without it) |
| ScalarDB exception types in the handler | the ScalarDB artifact for the pinned edition |

`@PreAuthorize` deserves the emphasis: it compiles, reads as an authorization control, and enforces
nothing until method security is switched on. Generate the enabling configuration alongside it, or
the security review finds an operation whose declared authorization exists only as an annotation.

Run the compile before writing the contract map, and report the command and its exit code in the run
summary — the same evidence standard the quality gate applies (@rules/ai-code-quality-gate.md).

## Dependency Versions

Any build file this skill touches pins versions, so follow @rules/dependency-versions.md: resolve
Spring Boot, Java, the validation implementation, and the OpenAPI tooling from their registries,
choose stable mutually compatible releases, and never copy the illustrative numbers out of
@rules/spring-boot-integration.md. Reuse `work/version-decisions.json` when its entries are fresh
rather than re-resolving and drifting. Confirm per `--confirm-versions` / `--no-confirm-versions` /
`options.confirm_versions`.

## Outbound Clients (the other half of the HTTP surface)

`generate-scalardb-code` emits the outbound ports a service needs (`domain/port/InventoryPort`,
`PaymentPort`, …) and their Fakes; this skill emits their **adapters** under
`infrastructure/client/`, each bound to the *called* service's OpenAPI contract by `operationId`
exactly as the inbound controllers are (@rules/api-contract-fidelity.md), with the Problem Details
of the callee mapped to the port's declared outcomes, timeouts from `operation-contracts.md`, and
the idempotency key forwarded where the callee requires one. The Fake stays the test double; the
adapter replaces it at runtime through Spring wiring, never by editing the application service.

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/03_design/api-specifications/ | Required | /architect:design-api — the contract |
| reports/03_design/api-specifications/problem-types.md | Required | /architect:design-api |
| reports/03_design/api-specifications/operation-contracts.md | Required | /architect:design-api |
| reports/06_implementation/api-layer-spec.md | Required | /architect:design-implementation — its frontmatter `layering_style` (`ddd` default, `clean`) decides the application-layer vocabulary; there is no flag for it here |
| reports/06_implementation/exception-mapping-spec.md | Required | /architect:design-implementation |
| reports/08_infrastructure/security-design.md | Recommended | /architect:design-security — where each authorization check is enforced |
| reports/07_test-specs/contract-test-specs.md | Recommended | /architect:generate-test-specs |

## Steps

1. **Resolve the contract set and the output root.** `--out`, else `generated/{service}/`. Read every
   specification file and the operation contracts; build the operation inventory.
2. **Check the contract is generatable.** Apply @rules/api-contract-fidelity.md §3 to every operation
   before writing anything. Report every miss; ask about the ones that block generation. Do not
   proceed on a guess.
3. **Generate DTOs and validation** from `components/schemas`, one class per named schema.
4. **Generate mappers** — explicit, field by field, declared fields only.
5. **Generate controllers** — one method per `operationId`, delegating to the application service the
   API layer specification names, with the authorization check at the point the security design named.
   Under `layering_style: clean` the controller builds the `<Operation>InputData`, calls the
   `<Operation>UseCase` boundary — never the interactor class — and returns what the
   `<Operation>Presenter` produced; the presenter, boundaries and data records are generated here.
6. **Generate the exception handler and the problem type constants** from the registry.
7. **Enumerate every route that already exists in the target tree** — not only the ones generated —
   and classify each as a mapped operation or an `out_of_scope_handlers` entry
   (@rules/api-contract-fidelity.md §4). A brownfield tree contains controllers that predate the
   contract; reporting an empty `handlers_without_spec_operation` because only the generated package
   was scanned is a map that passes its own check while hiding real endpoints.
8. **Compile.** Run the project's build target and report the exit code.
9. **Write the contract map** — `reports/06_implementation/api-contract-map.{md,json}` per
   @rules/api-contract-fidelity.md §4, with the declared scope and both `unmapped` arrays populated
   from what actually happened, never emptied for appearance.
10. **Report.** Operations generated, operations skipped and why, routes found out of scope,
    contract-quality findings, the compile result, and the version decision table.

`--dry-run` performs steps 1–2 and reports the plan and findings, writing no code.

## Output

| File | Content |
|------|---------|
| `generated/{service}/src/main/java/**/api/controller/` | One controller method per `operationId` |
| `generated/{service}/src/main/java/**/api/dto/` | Request/response DTOs with derived Bean Validation |
| `generated/{service}/src/main/java/**/api/mapper/` | Explicit DTO ↔ domain mappers |
| `generated/{service}/src/main/java/**/api/error/` | `@RestControllerAdvice`, Problem Details types, problem type constants |
| `reports/06_implementation/api-contract-map.md` | The binding table, human-readable |
| `reports/06_implementation/api-contract-map.json` | The binding, machine-readable — consumed by verify-implementation, generate-contract-tests, review-api-security, generate-docs |

Write reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).
Code identifiers, schema names and `operationId`s stay in English.

## Acceptance Criteria

- Every `operationId` in the contract has exactly one generated handler; no handler exists that has none
- No endpoint, parameter, field, header, or status code was generated that the specification does not declare
- Every DTO validation annotation traces to a schema constraint — none invented, none dropped
- Request and response DTOs are distinct from domain objects and entities, with explicit mappers
- No controller imports a persistence or ScalarDB type
- Every problem type in the registry is reachable from the exception handler, and
  `UnknownTransactionStatusException` is handled by its own branch per §3.1
- No error path bypasses the Problem Details handler
- `api-contract-map.json` exists with its `scope` declared and both `unmapped` arrays derived from a
  scan of the whole target tree — every reachable route appears in `operations` or `out_of_scope_handlers`
- The module compiles after generation, with the command and exit code reported, and every dependency
  the generated layer needs was added
- Every pinned version was looked up, is stable, and is recorded in the version decision table

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-api | Input source — the contract |
| /architect:design-implementation | Input source — the API layer specification |
| /architect:generate-scalardb-code | Sibling — owns `domain/` and `infrastructure/`; run both for a complete service |
| /architect:generate-contract-tests | Downstream — turns the contract into executable tests over this code |
| /architect:verify-implementation | Downstream — verifies this code against the contract |
| /architect:generate-docs | Downstream — documents the emitted API surface |
