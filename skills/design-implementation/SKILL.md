---
description: |
  Define implementation specifications for the API layer (controller/DTO/validation), domain services,
  repository interfaces, value objects, and exception mapping.
  /architect:design-implementation [--layering=ddd|clean] to invoke. Used after the design phase
  is complete. `--layering=clean` switches the application layer to Clean Architecture vocabulary
  (Use Case / Interactor / Presenter); the default keeps DDD application services.
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
class serves which REST `operationId` or GraphQL field coordinate, and what happens between the wire
and the aggregate. Governed by @rules/api-contract-fidelity.md and
@rules/graphql-contract-fidelity.md.

Specify, per REST `operationId` or GraphQL `<parentType>.<fieldName>` in
`reports/03_design/api-specifications/`:

| Element | Content |
|---------|---------|
| Handler | The controller class and method that serves this operation, 1:1. REST names from `operationId`; GraphQL binds by field coordinate |
| Request DTO | Class name from the `components/schemas` key, even when it collides with a domain simple name — the collision is resolved by package and import, never by re-styling the DTO (`MoneyDto`), which breaks the contract binding @rules/api-contract-fidelity.md relies on. **Never the domain object and never the persistence entity** — binding a request body straight onto an entity is the mass-assignment defect |
| Validation | The Bean Validation constraints derived from the schema: `minLength` -> `@Size`, `pattern` -> `@Pattern`, `enum` -> an enum type, `required` -> `@NotNull`. Derived, not hand-chosen; the request DTO is `@Valid` at the handler boundary. A `required` scalar is a **boxed** type (`Integer`, `Long`) — `@NotNull` on a primitive can never fire, and the constraint is silently dropped |
| Mapper | The explicit DTO <-> domain mapping, listing exactly the fields the schema declares. Under `clean` the row names two halves with two owners: `Request` -> `InputData` in `api/` (`generate-api-code`), domain -> `OutputData` in the interactor or a `usecase/` assembler (`generate-scalardb-code`) |
| Response DTO | Class name from the schema key, carrying exactly the schema's properties — this is what stops an internal field leaking when the domain model later grows |
| Application service | The method the handler delegates to, and **the transaction boundary**: which operations open a transaction, which join one, which are read-only. This must match the transaction placement recorded in `operation-contracts.md` |
| Authorization | Where the operation's declared authorization rule is enforced — the role/scope check and the object-level ownership predicate. An operation with an ownership predicate needs the check named here, not assumed |
| Idempotency | For operations carrying an `Idempotency-Key` obligation: where the key is read, where the record is stored, and the requirement that the record and the business write share **one** transaction (@rules/api-error-standard.md §5) |

The layering is directional and the direction is part of the specification: controller -> application
service -> domain -> repository (under `--layering=clean`: controller -> use case boundary ->
interactor -> domain -> repository, with the presenter behind the output boundary — see Layering
Style). No reverse dependency, and no persistence or ScalarDB type appearing in a controller
signature. `generate-contract-tests` turns this into executable ArchUnit rules.

## Layering Style (`--layering=ddd|clean`)

The layering above is the same under either style; the option decides the **names, granularity and
packages** the application layer and its wire adapters take. Precedence: `--layering` ->
`options.layering_style` in `work/pipeline-progress.json` -> `ddd`. The chosen style is recorded
once, as `layering_style: ddd|clean` in the frontmatter of `reports/06_implementation/api-layer-spec.md`,
and mirrored to `options.layering_style` so a later run defaults to it. Every downstream generator
(`generate-api-code`, `generate-graphql-code`, `generate-scalardb-code`, `generate-contract-tests`,
`generate-acceptance-tests`) and `verify-implementation` read it from that frontmatter — none takes a
flag of its own, so every generator in a run agrees on the vocabulary.

**Switching the style of an already-generated service is a migration, not a regeneration**, and the
tree is legitimately transitional between the two generator runs: `generate-api-code` runs first and
adds `usecase/` boundaries beside the existing `application/`; `generate-scalardb-code` then moves
`application/` (`tx/`, `view/`, `worker/`, shared collaborators) to `usecase/`, writes the
interactors by splitting the existing services, deletes the replaced services, and repairs what
still names the old package — the JaCoCo includes, the ArchUnit rules, the component scan. A tree
that still holds both packages after that second run is the `verify-implementation` finding, and
the first run's summary names the transitional state rather than reporting a finished service.

| Element | `ddd` (default) | `clean` (Clean Architecture vocabulary) |
|---------|-----------------|-----------------------------------------|
| Application package | `…/application/` | `…/usecase/` |
| Unit of the application layer | one application service per aggregate or operation group (`OrderApplicationService`) | one **use case per `operationId`** (or GraphQL field coordinate): the input boundary `PlaceOrderUseCase` and its `PlaceOrderInteractor` |
| What the handler passes in | request DTO mapped to domain values / a command | `PlaceOrderInputData` — an immutable record in `usecase/`, built by the controller's mapper |
| What comes back | a domain value or result object the controller maps to the response DTO | `PlaceOrderOutputData`, handed to the **output boundary** `PlaceOrderOutputBoundary`; `PlaceOrderPresenter` in `…/api/presenter/` implements it and produces the view model — the response DTO |
| Wire package | `…/api/` (controllers, DTOs, mappers, exception handler) | `…/api/` unchanged, plus `…/api/presenter/`; the response DTO doubles as the view model |
| Repository port | `domain/…/<Root>Repository` | **unchanged** — Clean Architecture's *gateway* is this same domain-owned interface. The toolkit keeps the DDD name because the aggregate manifest, the Fakes (@rules/tdd-workflow.md §4) and the coverage / mutation thresholds are keyed on it |
| Transaction boundary | the application service opens it and passes it down | the interactor opens it and passes it down — same rule, same place |
| Dependency rule | controller -> application service -> domain -> repository; no reverse edge | controller -> input boundary; interactor -> domain, repository ports, output boundary; presenter <- output boundary. The interactor never imports `api/` or `infrastructure/`; the controller never imports an interactor class, only its boundary; the presenter never imports a domain type |
| Cross-service outbound port | `domain/port/<X>Port` + Fake | unchanged |

Under `clean`, the per-operation table above names the use case (boundary + interactor), the input
data, the output boundary and the presenter in place of the single "Application service" row; every
other row is unchanged. The naming is Robert C. Martin's (*Clean Architecture*, ch. 22); the layering
it describes is the one `evaluate-ddd` already scores as criteria 10–12, so choosing `clean` changes
vocabulary and granularity, not the architecture. Existing hand-written source that already has
application services is not asked to rename them; the specification this skill writes, however, is
entirely in the chosen vocabulary — one document never mixes the two.

One behaviour-visible consequence follows from the presenter holding no business judgment: an outcome
the `ddd` mapper could decide from a returned read model (a declined payment returned as a
`CANCELLED` order and mapped to 402) must under `clean` be decided in the interactor — it throws the
exception the problem type registry maps — so the status the caller sees can change with the style.
Name such cases in the specification instead of discovering them in the contract tests.

### `clean` — the details the table leaves open

- **Boundary method.** The input boundary declares one method, `execute(<Op>InputData)`. Wire-facing
  use cases return `void`; the result travels through the output boundary.
- **Output boundary.** `void present(<Op>OutputData)`. The boundary lives in `usecase/` and therefore
  cannot name a response DTO, so the presenter is **request-scoped and stateful**: it stores the view
  model it built, and the controller reads it back after `execute` returns.
- **Domain-free data records.** `InputData`, `OutputData` and every nested record (`MoneyData`,
  `PrincipalData` for the caller's identity and scopes) carry primitives, strings, and their own
  enums only — never a domain type — because the presenter imports no domain type. The interactor
  (or an assembler in `usecase/` when several interactors share one shape) copies domain → output
  data; the `api/` mapper keeps the request side only (`Request` → `InputData`). This moves half of
  the `ddd` mapper out of `generate-api-code`'s package into `generate-scalardb-code`'s — record the
  transfer in the Mapper row.
- **Entries without an `operationId`** — saga confirm / compensate, recovery and expiry workers,
  outbox relays: still one use case each (input boundary + interactor, `execute`) with **no output
  boundary and no presenter**; there is nothing to present to. When a caller inside `usecase/` (a
  worker) needs the outcome, `execute` returns a domain-free result record; a `ddd` `boolean` that
  would otherwise vanish is specified this way, or the caller reads the outcome from state.
- **Shared collaborators are allowed in `usecase/`.** Splitting one application service into N
  interactors leaves shared logic (a settlement step, an unknown-status resolver, an assembler, the
  workers and relays) that is not an interactor and has no boundary. It lives in `usecase/`, is
  called only from `usecase/`, and may open a transaction. The "who opens a transaction" rule is
  therefore stated **by package** (`usecase..` only), never by class-name suffix — a suffix rule is
  the one that goes red on the first shared collaborator.
- **Transactions.** The interactor of the orchestrating operation opens the transaction and passes
  it down; a participant operation (`reserveStock`, `recordPayment`, …) joins the transaction it is
  handed and never calls `begin()`. Carry the participant carve-out from the `ddd` specification
  over verbatim.
- **Exception types the handler branches on** (a contract's 402 / 409 / 422 problem types) live in
  `usecase/`, since `usecase/` never imports `api/`; the transaction exceptions live in
  `usecase/tx/`. The `api/` exception handler imports them from there.
- **Component scan.** `clean` introduces the `api/` package; state that the Spring application
  scans it (or lists its configuration) — a `ddd`-era `scanBasePackages` that names only
  `infrastructure.config` starts an application with no controller in it.
- **Rule ids.** Give the clean dependency rules numbers that continue the sequence the `ddd`
  specification already declared (the test specifications cite rule ids), and state each rule so
  ArchUnit can express it: "controller never references an `*Interactor`", "`usecase` never
  imports `api` or `infrastructure`", "`api.presenter` and the data records import no domain type",
  "exactly one input boundary and one interactor per `operationId`, each output boundary implemented
  exactly once, in `api.presenter`". "The presenter reaches the interactor only through the output
  boundary" is a description, not a rule — the presenter never reaches the interactor at all.

## Testability Constraints (specify them — the generators and ArchUnit enforce them)

The specifications decide whether the code can be written test-first (@rules/tdd-workflow.md §4).
State, in `repository-interfaces-spec.md` and `domain-services-spec.md`:

- every repository interface is a **port** the domain owns, with an in-memory Fake named next to it
  (`InMemory<Root>Repository`), and its not-found / version-check contract stated so the Fake and the
  ScalarDB adapter can be held to the same behaviour;
- `Clock` and the id generator are **constructor dependencies** of every factory, application
  service and saga step that reads time or mints an id — no `now()` / `randomUUID()` inside domain or
  application code;
- the transaction is opened by the application service (the interactor, under `clean`) and passed
  down; no domain type holds one.

These become ArchUnit rules in `generate-contract-tests` and are checked at stage 8 of the gate.

## Repository Exception Strategy (specify it — do not leave it to codegen)

`repository-interfaces-spec.md` MUST state one exception-propagation strategy for the whole
project, because "technology-independent interfaces" and "single-point retry classification"
pull in opposite directions and every code generator otherwise invents its own bridge:

- **Standard form**: domain repository interfaces throw no checked infrastructure exceptions;
  infrastructure implementations wrap ScalarDB's checked exceptions in one project-wide
  **unchecked wrapper** carrying the original as its cause; the application layer's retry
  template unwraps the cause and performs the *only* conflict/condition/permanent classification
  in the project (@rules/scalardb-exception-handling.md catch-order rules apply there, once).
- A project may instead declare `throws TransactionException` on the interfaces — but that is a
  recorded decision in the spec, not a per-service improvisation. Either way, `TxContext` (or an
  equivalent wrapper) keeps transaction objects out of interface signatures, and conditional
  mutations may return `boolean` so `UnsatisfiedConditionException` never escapes a repository.

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
- Every GraphQL resolver-bound field coordinate has exactly one handler specified, with no extra
  annotated or runtime-wired handler
- Every request DTO is distinct from the domain object and the persistence entity, with an explicit mapper
- Every DTO field constraint is traceable to a schema constraint — no constraint invented, none dropped
- Every operation's transaction boundary matches its placement in `operation-contracts.md`
- Under `layering_style: clean`, every `operationId` has exactly one input boundary and one interactor, and every interactor that returns data names its output boundary and presenter
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
| reports/03_design/api-specifications/graphql/resolver-contracts.md | Required when GraphQL is selected | /architect:design-graphql |
| reports/03_design/aggregates/aggregate-manifest.json | Optional | /architect:design-aggregate — the domain layer skeleton: root, interior entities, value objects, factory, specifications, one repository interface per aggregate |
| reports/02_evaluation/ | Recommended | integrate-evaluations |

## Output

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

| File | Content |
|------|---------|
| `reports/06_implementation/api-layer-spec.md` | `layering_style: ddd\|clean` in the frontmatter; per-`operationId` handler, DTOs, validation, mapper, application service (or use case / interactor / presenter), transaction boundary, authorization enforcement point, idempotency handling |
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
