---
description: ScalarDB Saga rules — cross-service eventually consistent transactions with compensations (SAGA) or reservations (TCC); applies when designing or implementing saga orchestration, saga definitions, or the saga server deployment
globs:
  - "**/*.java"
  - "**/sagas/**/*.json"
  - "**/sagas/**/*.yaml"
  - "**/*saga*.properties"
---

# ScalarDB Saga Rules

Reference snapshot for **ScalarDB Saga 3.19**, from the OKF knowledge bundle
(`products/scalardb-saga/3.19/`). The 3.19 line currently builds `3.19.0-alpha.1`; APIs,
configuration keys and wire contracts can still move between builds, so pin the exact build in any
deliverable and re-verify keys against the branch. Resolve the bundle per
@rules/okf-knowledge-bundle.md.

## What It Is, and When To Choose It

ScalarDB Saga is a saga orchestration engine for microservices. It coordinates eventually consistent
distributed transactions across **services** — where a single ACID transaction is not possible —
using the Saga pattern (steps with compensations) or TCC (try / confirm / cancel). It keeps saga
state durable **through ScalarDB**, so it runs on any database ScalarDB supports and needs no
message broker.

Choose against the strongly consistent options in @rules/scalardb-2pc-patterns.md:

| Requirement | Answer |
|-------------|--------|
| Correctness requires immediate consistency across the services | ScalarDB transaction (shared cluster, Global Transaction API, or 2PC) |
| A step calls an external system, runs long, or cannot hold a transaction open | ScalarDB Saga |
| Compensation is defined and business-acceptable ("refund", "release", "cancel") | ScalarDB Saga |
| No meaningful compensation exists for a step | Not a saga — keep it inside one ScalarDB transaction |

## SAGA vs TCC

| Mode | Shape | Failure behavior |
|------|-------|------------------|
| `SAGA` | Each step executes and has a `compensation` that undoes it | A failed step compensates everything already attempted, in reverse, ending `COMPENSATED` |
| `TCC` | Each step has `reservation`, `confirmation`, `cancellation`. Every step reserves before any confirms | A failed reservation cancels the earlier reservations. A failure **after** the pivot can only roll forward — confirmations are retried until they succeed |

Pick `TCC` when a partial confirm is unacceptable and every participant can hold a reservation; pick
`SAGA` otherwise.

## Non-Negotiable Design Constraints

- **Steps must be idempotent.** A step interrupted between running and being recorded runs again.
  Every execution, compensation, reservation, confirmation and cancellation endpoint must tolerate
  redelivery. The engine stamps `X-Saga-Id` and `X-Saga-Step` on every request — use them as the
  idempotency key.
- **Compensations must be defined for every step that has one.** A step with no compensation makes
  the saga un-rollbackable past that point.
- **Compensations must eventually succeed.** A saga whose compensation keeps failing past
  `recovery.compensation_grace_period_seconds` (default 4h) is escalated to `ESCALATED` and waits
  for an operator. Design compensations so they cannot fail permanently.
- **Retries are classified, not blanket.** Per-step retry policies with exponential backoff apply to
  transient failures (5xx, 408, 429, transport errors) and not to permanent ones (other 4xx). A
  participant that returns 4xx for a retryable condition will not be retried.
- **The state store is production data.** Saga state and its event history live in the ScalarDB store
  configured by `scalar.db.*` — it must be a real, backed-up database, never ephemeral container
  storage.

## Saga Lifecycle and Statuses

`RUNNING` → `COMPLETED` on success; `RUNNING` → `COMPENSATING` → `COMPENSATED` on a compensated
failure; `WAITING` while an async step is parked; `ESCALATED` when compensation cannot make
progress. Terminal sagas are purged after `retention.period_seconds` (default 7 days) — which is
also the window in which a finished saga's history can still be inspected. `ESCALATED` sagas are
never purged.

Every outcome is appended to a durable event log (`STEP_COMPLETED`, `STEP_FAILED`,
`STEP_COMPENSATED`, `SAGA_COMPENSATED`, …), so a crashed coordinator is picked up by another replica
and driven to a terminal state. There is no leader to elect and no standby.

## Definitions

Declarative JSON or YAML, versioned and registered without recompiling. Two kinds of step:

- **Declarative service step** — names a `service` configured on the server and the HTTP call to
  make. Works in both server and embedded mode.
- **Code step** — names a `stepClass` implemented in Java. **Embedded mode only**; the server
  rejects such a definition at startup, because an operator cannot add classes to its image.

Values flow between steps through the saga context: `${...}` reads from it, `output` captures
response fields (JSONPath) back into it.

```json
{
  "name": "order-saga",
  "mode": "SAGA",
  "steps": [
    {
      "name": "charge",
      "service": "payment",
      "execution": {
        "method": "POST",
        "path": "/charge",
        "jsonBody": { "orderId": "${orderId}", "amount": "${amount}" },
        "output": { "paymentId": "$.payment_id" }
      },
      "compensation": {
        "method": "POST",
        "path": "/refund",
        "jsonBody": { "orderId": "${orderId}" }
      }
    }
  ]
}
```

Optional top-level fields seen in the shipped definitions: `version`, `recoveryStrategy`
(`BACKWARD`), `timeoutMillis`; per-step `timeoutMillis`.

## Deployment Modes

| Mode | Artifact | Java | Code steps |
|------|----------|------|:----------:|
| Server | `ghcr.io/scalar-labs/scalardb-saga-server` (container image only, not on Maven Central) | 21 | No |
| Client to a server | `com.scalar-labs:scalardb-saga-java-client-sdk` | 8 | – |
| Embedded engine | `com.scalar-labs:scalardb-saga-core` | 21 | Yes |
| Generated stubs | `com.scalar-labs:scalardb-saga-rpc`, `…-api` | 8 | – |
| Version pinning | `com.scalar-labs:scalardb-saga-bom` | – | – |

Import the BOM to pin every artifact to one version, then declare **one** of
`scalardb-saga-java-client-sdk` (call a server) or `scalardb-saga-core` (embed the engine). They are
alternatives, not a pair — the SDK never depends on `core`, so declaring both drags the whole engine
into an application that only wanted a client. The client SDK targets Java 8, so applications that
cannot move off it can still use server mode.

Transports: REST on `12080` and gRPC on `12051` by default, both enabled. `SagaService` (start,
query) and `AdminService` (list, recover, force-complete, un-escalate) are the gRPC renderings of the
REST contract.

## Server Configuration Rules

Keys live under `scalar.db.saga.server.*`; the ScalarDB store keys are plain `scalar.db.*`. A
misspelled `scalar.db.saga.server.*` key **fails startup** rather than being ignored.

| Concern | Rule |
|---------|------|
| Secrets | Any `scalar.db.saga.*` value may use `${env:NAME}` or `${file:UTF-8:/path}`. Plain `scalar.db.*` keys are resolved by ScalarDB, which supports `${env:...}` but **not** `${file:...}`. API-key secrets must always be a secret reference, never an inline literal |
| Security | Select exactly one provider: `jwt` (OAuth 2.0 resource server; `jwks_url` must be https; `audience` must be this daemon's own identifier) or `apikey`. With no provider and `host=0.0.0.0` the daemon **refuses to start** — do not defeat that with `security.insecure_mode.enabled`, which is local development only |
| Roles | `saga:read`, `saga:write`, `saga:admin`. Every `AdminService` route requires `saga:admin`; the operator identity comes from the authenticated call, never from a request field |
| Instance identity | Set `owner_id` to the pod name (`${env:HOSTNAME}`). The default random UUID is safe but untraceable, and two live instances must never share one — the claim is what stops two replicas driving the same saga |
| Recovery | `recovery.timeout_millis` (default 60000) is the staleness threshold. Set it **below** the longest a healthy instance goes between saga updates and a live saga is stolen from the instance still running it |
| Shutdown | `WAIT_CURRENT_STEP` (default) finishes the running step and leaves the rest for recovery; `WAIT_ALL_SAGAS` needs a timeout sized to the longest saga. Budget `terminationGracePeriodSeconds` for the sum of both shutdown windows |
| Service calls | One block per `service` named in a definition; only `base_url` is required. `X-Saga-Id` / `X-Saga-Step` / `X-Saga-Callback-Url` are stamped by the engine and cannot be overridden — naming one is rejected at startup. `allowed_hosts` is host-name-only defense in depth, not a sandbox |
| Async callbacks | Set `callback.base_url` and `callback.secret` together or neither. Set `callback.max_age_seconds` above the longest a step legitimately stays parked, or genuine late callbacks are rejected |
| Retention | `retention.batch_size` must keep up with the terminal-saga rate over one interval, or the backlog grows |

## Operations

Escalated sagas are the operator's queue. `AdminService` / the REST admin surface offers list by
status, `RecoverSaga` (drives a stuck `RUNNING`/`COMPENSATING` saga in the direction the pivot
chooses), `ForceComplete` (overrides an `ESCALATED` saga to `COMPLETED`), and un-escalate. Wrong-state
preconditions surface as `FAILED_PRECONDITION` (REST 422); a lost compare-and-set as `ABORTED`
(REST 409).

Design the operational runbook alongside the saga: who watches `ESCALATED`, what evidence the event
history gives them, and which interventions are permitted per saga.
