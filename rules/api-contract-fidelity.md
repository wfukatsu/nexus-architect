---
description: OpenAPI as the single API contract — what makes a contract verifiable, the operationId to handler binding, the contract map artifact, and the drift protocol. Applies when designing an API surface, generating API-layer code or tests, and verifying code against the design.
---

# API Contract Fidelity

Applies to `design-api`, `design-implementation`, `generate-api-code`, `generate-contract-tests`,
`verify-implementation`, `review-api-security`, and to `implement-backlog` whenever the item it
implements touches an API surface.

## 1. The contract is the specification file, not the report

The OpenAPI / AsyncAPI / protobuf document under `reports/03_design/api-specifications/` **is** the
contract. The prose in `api-gateway-design.md` and the design reports explains *why* the contract
looks the way it does; it never adds to, overrides, or softens it.

Three consequences, and they are the whole point of this file:

1. **Code may not exceed the contract.** An endpoint, parameter, field, or status code that appears
   in code and not in the specification is a defect — including a "harmless" health endpoint, a
   debug route, or a field someone added because it was convenient.
2. **Code may not contradict the contract.** A differently-shaped DTO, a different status code, a
   different content type, a different required/optional decision.
3. **Changing the behaviour means changing the specification first.** The specification is edited,
   the code is regenerated or amended, and the contract map (§4) is rewritten. Never the reverse
   order, and never the code alone.

A contract the code is allowed to quietly exceed is not a contract — it is documentation, which is
the state this rule exists to end.

## 2. `operationId` is the join key

Every operation declares an `operationId`. It is what binds specification to handler to test to
verification report, so it carries obligations beyond OpenAPI's own requirement of uniqueness:

- **Unique across the entire document**, and across every document in the project — the map in §4 is
  project-wide.
- **`camelCase` verb-noun**, naming the business action, not the HTTP shape: `confirmOrder`,
  `reserveStock`, `listOrdersForCustomer`. Not `postOrdersIdConfirm`, not `getOrders2`.
- **Stable.** Renaming an `operationId` breaks the map, the tests, and any generated client. Rename
  only alongside a deliberate contract version change, and record it.
- **Exactly one handler.** One `operationId` maps to one controller method; one controller method
  serves one `operationId`. A method serving two operations, or two methods serving one, is a
  finding — it is how request handling silently diverges between paths.

For gRPC the join key is the fully-qualified `package.Service/Method`; for AsyncAPI it is the
channel plus operation name. The 1:1 handler rule is identical.

## 3. What makes a contract verifiable

A specification can be perfectly valid OpenAPI and still be impossible to verify code against.
`design-api` must satisfy all of the following, and `verify-implementation` reports each miss as a
contract-quality finding against the *design*, not the code:

| Requirement | Why it is required |
|-------------|--------------------|
| **Every request and response schema is a named `components/schemas` entry**, not an inline anonymous object | The name becomes the DTO name. Inline schemas force the generator to invent names, and invented names cannot be checked |
| **Every operation declares all of its response status codes**, success and error, each with a schema | An undeclared status code is an untestable code path. Error schemas are `application/problem+json` per @rules/api-error-standard.md |
| **Required vs optional is decided for every property**, and `nullable` is used deliberately | This is what Bean Validation is generated from. An undecided field yields an unvalidated field |
| **Constraints are expressed in the schema** — `minLength`, `maximum`, `pattern`, `enum`, `format` | These generate to `@Size`, `@Max`, `@Pattern`, enums. A constraint that lives only in prose is never enforced |
| **At least one success example and one error example per operation** | `generate-contract-tests` uses them as fixtures. An operation with no example gets a shape test only |
| **Authentication and authorization declared per operation** via `security` plus a scope/role statement | This is the input to the BOLA/BFLA checks in @rules/api-security-checks.md. An operation with no declared authorization is assumed public, and that assumption is usually a vulnerability |
| **Idempotency obligations declared per operation** — the `Idempotency-Key` header parameter where @rules/api-error-standard.md §5 requires it | Otherwise the retry contract exists only in someone's head |
| **Pagination, sorting, and filtering follow one project-wide convention**, stated once | Per-operation improvisation is where excessive-data-exposure defects enter |

## 4. The contract map

The map is the machine-readable record of what the code actually binds to what in the contract. It
is written by whichever skill produced the API layer (`generate-api-code`, or `implement-backlog`
when it writes API code by hand) and read by `generate-contract-tests`, `verify-implementation`,
`review-api-security`, and `generate-docs`.

Location — a report artifact, because the code root varies (`generated/` for a scaffold, the real
source tree for backlog delivery):

- `reports/06_implementation/api-contract-map.md` — the human-readable table
- `reports/06_implementation/api-contract-map.json` — the machine-readable form

```json
{
  "schema_version": 1,
  "generated_at": "2026-08-09T00:00:00Z",
  "spec_files": ["reports/03_design/api-specifications/openapi/order-service.yaml"],
  "source_root": "services/order-service/src/main/java",
  "operations": [
    {
      "operation_id": "confirmOrder",
      "spec_file": "reports/03_design/api-specifications/openapi/order-service.yaml",
      "method": "POST", "path": "/orders/{orderId}/confirm",
      "handler": "com.example.order.api.OrderController#confirm",
      "request_dto": "com.example.order.api.dto.ConfirmOrderRequest",
      "response_dtos": {"200": "com.example.order.api.dto.OrderResponse"},
      "problem_types": ["state-conflict", "transaction-status-unknown", "not-found"],
      "idempotency_key": "required",
      "authorization": "role:order.writer + owner(orderId)",
      "transaction": "TX-004",
      "traces_to": ["FR-012", "FEAT-007"]
    }
  ],
  "unmapped": {
    "spec_operations_without_handler": [],
    "handlers_without_spec_operation": []
  }
}
```

`unmapped` is the part that matters. It is **never omitted and never silently empty** — a generator
that cannot bind an operation records it there rather than dropping it.

### The map has a scope, and the scope is declared

`handlers_without_spec_operation` is only meaningful against a stated scope. A greenfield scaffold
emits one service and legitimately reports an empty array; a brownfield tree — the legacy-refactoring
case this toolkit exists for — contains controllers that predate the contract, and there the same
empty array is a lie. Declare the scope so the two cases are distinguishable:

```jsonc
"scope": {
  "packages": ["com.example.ec.order.api"],      // what this map claims to cover
  "route_prefixes": ["/orders"],
  "out_of_scope_handlers": [                      // reachable, deliberately not covered here
    {"handler": "com.example.ec.catalog.ProductController", "routes": ["/api/products/**"],
     "why": "pre-existing monolith surface; no contract yet"}
  ]
}
```

Rules:

1. **`out_of_scope_handlers` is derived from the source tree, not from intent.** Enumerate the
   routes that actually exist, then classify. A handler that appears in neither `operations` nor
   `out_of_scope_handlers` is a bug in the map.
2. **Out of scope is not absolved.** Each entry is still reported — as a contract gap by
   `verify-implementation` and as an inventory finding by `review-api-security`
   (@rules/api-security-checks.md API9, where an undocumented endpoint is an unreviewed one). The
   field records that the omission was *seen and named*, not that it is acceptable.
3. **Both `unmapped` arrays empty, with every reachable route accounted for by `operations` or
   `out_of_scope_handlers`, is the only passing state** — and it is an assertion, not a hope.

**A consumer must never conclude coverage from the map alone.** The map is a claim by whoever wrote
it; `verify-implementation` and the generated inventory test both derive the route list from the code
and compare, because a generator that mis-scoped produces a map that passes its own check. This is
not hypothetical: it is the defect the first end-to-end run of this pipeline produced.

The `transaction` field joins each operation to the transaction design (`scalardb-transaction.md` /
the saga definition), and `traces_to` joins it to the requirement graph. Together they are what let
verification check that an operation the design put inside one transaction is implemented inside
one transaction.

## 5. Generation constraints

Binding on any skill that emits API-layer code:

1. **Generate only what the specification declares.** No extra endpoint, parameter, field, header, or
   status code. If something is genuinely needed and absent, stop and add it to the specification
   first — do not add it to the code and mention it in a summary.
2. **Name from the specification.** DTO names come from `components/schemas` keys; handler method
   names from `operationId`. Do not re-style them.
3. **Validation is generated from the schema**, not hand-chosen: schema constraints become Bean
   Validation annotations on the DTO, and the request DTO is validated (`@Valid`) at the handler
   boundary.
4. **The request DTO is not the domain object and not the persistence entity.** Binding a request
   body straight onto an entity is the mass-assignment defect (OWASP API3); an explicit mapper
   between DTO and domain is mandatory, and the mapper only maps fields the specification declares.
5. **The response DTO is not the domain object either.** It carries exactly the schema's properties —
   this is what keeps an internal field from leaking when the domain model grows.
6. **Errors are produced only through the Problem Details handler** (@rules/api-error-standard.md).
   No ad-hoc `ResponseEntity.status(500).body("...")` anywhere.
7. **Write the contract map** (§4) as the final step. A generation run that emits code and no map is
   incomplete.

## 6. Drift protocol

When the code and the contract disagree, the correct behaviour is to **report the disagreement, not
to erase it** — the same discipline `generate-docs` already follows for design-vs-code drift.

| Situation | Action |
|-----------|--------|
| Handler exists, no spec operation | Record in `unmapped.handlers_without_spec_operation`, raise a finding. **Do not delete the handler** and do not invent a spec entry for it — it may be deliberate work the specification has not caught up with, and that decision is the user's |
| Spec operation exists, no handler | Record in `unmapped.spec_operations_without_handler`, raise a finding. Generate a stub **only** when explicitly generating a scaffold; never when verifying |
| Shapes differ | Raise a finding naming both shapes and the field-level differences. Never rewrite the specification to match the code |
| Status codes differ | Raise a finding. A code returning a status the contract does not declare is a break even if the status is "more correct" |

Findings carry the `VER-` prefix and land in `reports/09_verification/design-code-conformance.{md,json}`.

## 7. Contract test stack

A contract is only enforced to the extent something executable checks it. One default, three opt-ins:

| Tier | Stack | When |
|------|-------|------|
| **Default (Spring)** | Atlassian's OpenAPI request validator, MockMvc integration, driven from `@WebMvcTest` / `@SpringBootTest` slices | Always, for a Spring service. Every request and response the tests exercise is validated against the OpenAPI document in-process — no running server, no separate pipeline stage, and it fails at the assertion rather than in review |
| Opt-in: runtime fuzzing | Schemathesis against a running instance | When the API is externally exposed, or the schema has enough constraint surface that property-based generation finds cases the examples do not |
| Opt-in: consumer-driven | Pact | When named internal consumers exist and their expectations must gate the provider's deploy — inter-service surfaces, not public ones |
| Opt-in: architecture | ArchUnit | Layering and dependency-direction rules from the API layer specification. Not contract testing strictly, but it is what stops a controller reaching past the application service into a repository, and it runs in the same suite |

The default is not negotiable in the sense that a Spring service always gets it; the opt-ins are
selected per project and recorded with the reason. `generate-contract-tests` emits the default plus
whichever opt-ins the project selected; `generate-test-specs` records the selection at specification
time so the two agree.

For a non-Spring or non-JVM service, choose the equivalent in-process OpenAPI validator for the
framework and record it the same way — the requirement is in-process validation of every exercised
request and response, not a specific library.

### Resolving the validator coordinate (do not write it from memory)

Two traps, both hit on the first real run of this pipeline. Resolve per
@rules/dependency-versions.md and check **both** before pinning:

1. **The artifact was renamed.** Atlassian publishes the same library under two coordinate families —
   the original `com.atlassian.oai:swagger-request-validator-*` and the newer
   `com.atlassian.oai:openapi-request-validator-*`. The MockMvc integration is the `-mockmvc`
   artifact; there is **no** `-spring-mvc` artifact under either name, and pinning one yields an
   unresolvable dependency. List the group directory rather than assuming the module name.
2. **Check the artifact's JDK baseline against the project's.** The `3.x` line is compiled for
   Java 21 (class file major 65); a Java 17 project fails to compile against it with
   `bad class file … version 65.0 … should be 61.0`. The `2.x` line is a Java 8 baseline and is the
   correct pin for a Java 17 service. This is @rules/dependency-versions.md §2 "compatibility gates
   the choice" in its most literal form — the newest release is not the compatible one.

Verify the baseline mechanically rather than by assumption: the two bytes at offset 6 of any
`.class` in the jar are the major version (61 = Java 17, 65 = Java 21), and it must be **≤** the
project's target release.

### The spec the tests load must be inside the test tree

The design copy of the contract lives under `reports/`, which is **git-ignored**. A committed test
that loads it from there passes locally and fails on a fresh checkout — which means the CI contract
stage fails for everyone but the author. Copy the specification into the service's test resources
(`src/test/resources/contract/openapi/<service>.yaml`) and load it from the classpath, recording in
the contract map which design file the copy came from. Refresh the copy whenever the contract
changes; a stale copy is drift the tests cannot see, so `verify-implementation` compares the two.

## 8. Versioning

Within a published major version the contract is **additive-only**: new optional fields, new
operations, new optional headers, new enum values *only where the consumer contract says unknown
values are tolerated*. Removing a field, tightening a constraint, making an optional field required,
changing a status code, or renaming an `operationId` is a breaking change and requires a new version
plus a recorded migration path. `verify-implementation` compares against the contract version the
project pins, not against whatever is newest on disk.
