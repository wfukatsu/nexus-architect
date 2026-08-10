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

## Spring execution model

Use Spring MVC for synchronous database/client APIs by default. Choose WebFlux when the existing
stack is reactive or Subscription requires it, and require an explicit isolation strategy for each
blocking call. Adding `Mono` around blocking work does not make it non-blocking.

## Required decision fields

For every surface record consumers, operations, selected style, client variability, cache needs,
security model, transport, execution model, data access, transaction model, operational readiness,
rejected alternatives and traced requirement IDs. Unknown security or transaction fields become
open questions, never permissive defaults.
