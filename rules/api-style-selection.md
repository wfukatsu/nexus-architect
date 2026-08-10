---
description: Select REST, GraphQL, hybrid, gRPC, or AsyncAPI per API surface without deriving the choice from the database product. Applies to API design and architecture decisions.
---

# API Style Selection

## Decision unit

Choose per consumer-facing or service-facing surface, not once for the whole system. Record one of
`rest`, `graphql`, `hybrid`, `grpc`, or `asyncapi` in
`reports/03_design/api-style-decisions.md`, together with evidence and rejected alternatives.

## Selection criteria

| Prefer GraphQL when | Prefer REST or another style when |
|---------------------|-----------------------------------|
| Consumers need materially different projections | Operations are fixed, command-oriented contracts |
| One view aggregates several related resources | HTTP caching, CDN and URL semantics dominate |
| Under-fetching creates repeated client round trips | File transfer, webhook, callback or streaming semantics dominate |
| Additive schema evolution fits consumer governance | Query-cost and field-authorization operations cannot be supported |
| The team can operate N+1, cost and schema controls | Public API retry/status semantics must be explicit and simple |

Use `hybrid` when flexible reads benefit from GraphQL but commands, files, webhooks, or externally
governed operations fit REST/gRPC/events better. Do not duplicate a business operation across
surfaces unless authorization, transaction, error and idempotency parity can be verified.

## Database independence

The database does not select the API style. PostgreSQL, MySQL, ScalarDB and external APIs can all
back either REST or GraphQL through application services. Record separately:

- `access_surface`: the API exposed to consumers;
- `application_framework`: Spring for GraphQL, Spring MVC, gRPC, etc.;
- `data_access`: repository/JDBC/ScalarDB client/native interface;
- `transaction`: local, ScalarDB transaction, saga or 2PC.

## ScalarDB boundary

Treat these as different products and threat surfaces:

1. **Spring for GraphQL application API** — Spring Security and business authorization, application
   services, audit, query governance and ScalarDB repositories.
2. **ScalarDB native GraphQL interface** — an edition- and release-gated ScalarDB feature.

Default external and business APIs to the Spring application boundary. Do not expose the native
interface directly unless the user approves a documented exception after the pinned OKF bundle
confirms availability, edition, authentication/authorization, audit, query limits and network
isolation. Database convenience is not sufficient justification.

Every ScalarDB-backed surface records the following machine-readable fields in
`reports/03_design/api-style-decisions.json`:

| Field | Allowed value or requirement |
|-------|------------------------------|
| `graphql_provider` | `spring-for-graphql`, `scalardb-native`, or `not-applicable` |
| `native_exposure` | `none`, `internal`, or `external` |
| `approval` | `not-required`, `approved:<decision-id>`, or `rejected` |
| `pinned_product` | Exact product name from the OKF decision |
| `pinned_release` | Exact verified release; never inferred from an example |
| `contracted_edition` | Edition whose entitlement and controls were verified |
| `control_evidence` | References for authentication, authorization, audit, query limits, and network isolation |
| `rationale` | Evidence for the selected boundary and rejected alternative |

`scalardb-native` with `internal` or `external` exposure requires `approved:<decision-id>`, all
five control-evidence references, and a matching pinned product/release/edition. Missing evidence
is an open question and blocks design completion. External native exposure is a critical security
review finding unless the documented exception demonstrates every control; prose approval without
these structured fields is not approval.

## Spring execution model

Use Spring MVC for synchronous database/client APIs by default. Choose WebFlux when the existing
stack is reactive or Subscription requires it, and require an explicit isolation strategy for each
blocking call. Adding `Mono` around blocking work does not make it non-blocking.

## Required decision fields

For every surface record a stable `surface_id`, consumers, operations, selected style, client
variability, cache needs, security model, transport, execution model, data access, transaction
model, operational readiness, rejected alternatives and traced requirement IDs. The Markdown and
JSON decisions must agree. ScalarDB-backed surfaces also include every structured field in the
ScalarDB boundary table above. Unknown security, transaction, version, edition, exposure, approval,
or control fields become open questions, never permissive defaults.
