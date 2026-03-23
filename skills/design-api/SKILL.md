---
name: design-api
description: |
  Generate REST/GraphQL/gRPC/AsyncAPI specifications.
  /architect:design-api to invoke. Requires design-microservices output as a prerequisite.
model: opus
user_invocable: true
---

# API Design

## Desired Outcome

Design API specifications for inter-service and client-facing communication:
- REST API (OpenAPI 3.0 specification)
- GraphQL schema (as needed)
- gRPC protobuf definitions (inter-service communication)
- AsyncAPI (event-driven communication)
- API Gateway design (routing, authentication, rate limiting)

## Decision Criteria

- Select protocol based on service classification (Process -> gRPC, Master -> REST, Integration -> AsyncAPI)
- Authentication/authorization patterns (OAuth2/OIDC + RBAC/ABAC)
- API versioning strategy
- Error response standardization

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/03_design/target-architecture.md | Required | /architect:design-microservices |

## Output

| File | Content |
|------|---------|
| `reports/03_design/api-specifications/openapi/` | REST API specifications |
| `reports/03_design/api-specifications/graphql/` | GraphQL schemas |
| `reports/03_design/api-specifications/grpc/` | Protobuf definitions |
| `reports/03_design/api-specifications/asyncapi/` | Event specifications |
| `reports/03_design/api-gateway-design.md` | Gateway design |

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-microservices | Input source |
| /architect:review-consistency | Review target |
