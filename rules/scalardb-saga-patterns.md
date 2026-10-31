---
description: ScalarDB Saga rules — cross-service eventually consistent transactions with compensations (SAGA) or reservations (TCC); applies when designing or implementing saga orchestration, saga definitions, or the saga server deployment
globs:
  - "**/*.java"
  - "**/sagas/**/*.json"
  - "**/sagas/**/*.yaml"
  - "**/*saga*.properties"
---

# ScalarDB Saga Rules

Reference snapshot for **ScalarDB Saga 3.20.0 — the first GA release** (2026-10-29, Apache-2.0),
from the OKF knowledge bundle `products/scalardb-saga/3.20/` (bundle v1.3.0: `overview.md`,
`getting-started.md`, `guides/configurations.md`, `guides/run-saga-transactions.md`,
`guides/model-your-workflow.md`, `guides/rest-api.md`, `guides/scalardb-saga-status-codes.md`,
`server-deployment.md`, `reference/`, `releases/release-notes.md`). The bundle's **3.19** line is
the `3.19.0-alpha.1` snapshot with a different `reference/`-only layout and older key names — never
mix it into a 3.20 answer. Resolve the bundle per @rules/okf-knowledge-bundle.md and cite the
concept's `resource` URL.

## What It Is, and When To Choose It

ScalarDB Saga is a saga orchestration engine for microservices. It coordinates eventually consistent
distributed transactions across **services** — where a single ACID transaction is not possible —
using the Saga pattern (steps with compensations) or TCC (try / confirm / cancel). It keeps saga
state durable **through ScalarDB**, so it runs on any database ScalarDB supports and needs no
message broker. No edition or licence is involved: the engine is Apache-2.0 and stores its state
through ScalarDB Core's Consensus Commit.

Choose against the strongly consistent options in @rules/scalardb-2pc-patterns.md:

| Requirement | Answer |
|-------------|--------|
| Correctness requires immediate consistency across the services | ScalarDB transaction (shared cluster or the Microservice Transaction API on separated clusters; the 2PC interface only as a recorded deviation) |
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
- **Saga IDs are idempotency keys too.** Start a saga with your own ID derived from a business key
  (`PUT /sagas/{id}`; up to 128 characters of letters, digits, `.`, `_`, `-`). When a start's
  outcome is unknown, start again with the same ID — `SagaAlreadyExistsException` / `409` means the
  earlier attempt exists. A generated ID plus a retry after a failure that reached the server
  starts a second saga. Retention deletes finished sagas, so a later start with the same ID runs
  the saga again — deduplicate in the application if retries can arrive after the retention window.
- **Compensations must be defined for every step that has one.** A step with no compensation makes
  the saga un-rollbackable past that point.
- **Compensations must eventually succeed.** A saga whose recovery keeps failing past
  `recovery.escalation_grace_period_seconds` (default 14400 s = 4 h) is escalated to `ESCALATED`
  and waits for an operator. Design compensations so they cannot fail permanently.
- **Retries are classified, not blanket.** Per-step retry policies with exponential backoff apply to
  transient failures (5xx, 408, 429, transport errors) and not to permanent ones (other 4xx — a
  `422` is final). A participant that returns 4xx for a retryable condition will not be retried.
- **The state store is production data.** Saga state and its event history live in the ScalarDB
  store configured by `scalar.db.*` (namespace `saga`) — it must be a real, backed-up database,
  never ephemeral container storage.

## Store Requirements (ScalarDB side)

- **Consensus Commit is mandatory.** `scalar.db.transaction_manager` must resolve to
  `consensus-commit` (unset passes, because that is ScalarDB's default); the store refuses to start
  on any other manager, **including the Cluster client-side `cluster` manager**. The reason is
  structural: a status transition deletes the old state row and inserts the new one, and the "at
  most one visible state row per saga" guarantee holds only because both writes commit atomically
  under Consensus Commit's snapshot isolation.
- **`scalar.db.consensus_commit.one_phase_commit.enabled=true` is the recommended performance
  option** (the getting-started server sets it). It lets a transaction whose writes the storage can
  apply in one atomic operation — an event appended to its own saga's partition, for example — skip
  the separate coordinator write. It is ScalarDB's storage-level optimisation, **not** the one-phase
  application interface of the Microservice Transaction API (@rules/scalardb-2pc-patterns.md); do
  not conflate them in a design document.
- On Cassandra the `saga` namespace defaults to `SimpleStrategy` with replication factor 1; set
  `scalar.db.saga.store.scalardb.creation_options.replication-factor` before the first start.
  `scalar.db.saga.store.scalardb.num_buckets` (default 16, the sweep-table partitions) cannot change
  once the table holds data.
- Pin the ScalarDB version the store runs on alongside the Saga version and check both
  (@rules/dependency-versions.md).

## Saga Lifecycle and Statuses

`RUNNING` → `COMPLETED` on success; `RUNNING` → `COMPENSATING` → `COMPENSATED` on a compensated
failure; `WAITING` while an async step is parked for a callback; `ESCALATED` when recovery cannot
make progress. Terminal sagas are purged after `retention.period_seconds` (default 604800 s =
7 days) — which is also the window in which a finished saga's history can still be inspected.
`ESCALATED` sagas are never purged.

Every outcome is appended to a durable event log (`SAGA_STARTED`, `STEP_COMPLETED`, `STEP_FAILED`,
`SAGA_COMPENSATING`, `STEP_COMPENSATED`, `SAGA_COMPENSATED`, …), so a crashed orchestrator is picked
up by another replica once `recovery.staleness_threshold_millis` passes and driven to a terminal
state. There is no leader to elect and no standby. Every error carries a `DB-SAGA-` status code
(`guides/scalardb-saga-status-codes.md`); admission-control rejections are `DB-SAGA-20004`
(rate) and `DB-SAGA-20006` (concurrency).

## Definitions

Declarative JSON or YAML, versioned (`name` + `version`) and registered without recompiling.
Definitions are immutable once registered — change one by bumping its `version`. Two kinds of step:

- **Declarative service step** — names a `service` configured on the server and the HTTP call to
  make. Works in both server and embedded mode.
- **Code step** — names a `stepClass` implemented in Java. **Embedded mode only**; the server
  rejects such a definition, because an operator cannot add classes to its image.

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

Optional fields seen in the shipped definitions: top-level `version`, `recoveryStrategy`
(`BACKWARD`), `timeoutMillis`; per-step `timeoutMillis`, `retryPolicy`, and `async` for a step
that parks the saga until a callback (requires `callback.base_url` + `callback.secret`).

## Deployment Modes

| Mode | Artifact | Java | Code steps |
|------|----------|------|:----------:|
| Server | `ghcr.io/scalar-labs/scalardb-saga-server` (container image only, not on Maven Central) | 25 (in the image) | No |
| Client to a server | `com.scalar-labs:scalardb-saga-java-client-sdk` | 8+ | – |
| Embedded engine | `com.scalar-labs:scalardb-saga-core` | **25** (virtual-thread behaviour on the async, recovery and retention paths, JEP 491) | Yes |
| Generated stubs | `com.scalar-labs:scalardb-saga-rpc`, `…-api` | 8+ | – |
| Version pinning | `com.scalar-labs:scalardb-saga-bom` | – | – |

Import the BOM to pin every artifact to one version, then declare **one** of
`scalardb-saga-java-client-sdk` (call a server) or `scalardb-saga-core` (embed the engine). They are
alternatives, not a pair — the SDK never depends on `core`, so declaring both drags the whole engine
into an application that only wanted a client. An application that cannot run Java 25 uses server
mode through the Java 8 client SDK. JDBC drivers that load native libraries trigger a JDK 24+
warning; `--enable-native-access=ALL-UNNAMED` silences it (the image sets it).

Client classes: `GrpcSagaOrchestratorClient` (start / startAsync / await), `GrpcSagaAdminClient`
(list, recover, force-complete, reset), `SagaCallback`, `SagaStateSnapshot`, `SagaDetail`,
`TimelineEvent`, `SagaErrorCode`. Embedded: `DefaultSagaOrchestrator` implements
`SagaOrchestrator`; call `startBackgroundTasks()` for recovery and retention, and supply a
callback-URL provider or async steps need the server. The SDK retries connection failures of
`start` / `startAsync` under the same saga ID until `defaultDeadlineMillis` (default `0` = no
limit); past the deadline `start` throws `SagaTimeoutException` and the outcome is unknown. It does
**not** retry `SagaOverloadedException` or rate-limit errors — the application decides.

Transports: REST on `12080` and gRPC on `12051` by default, both enabled (they cannot both be off).
`SagaService` (start, query) and `AdminService` are the gRPC renderings of the REST contract.

| REST | Meaning |
|------|---------|
| `POST /sagas` | Start and wait for a terminal status (`202` with the current state once `sync.max_wait_millis` passes) |
| `POST /sagas?async=true` | Start without waiting (`202`, `RUNNING`) |
| `PUT /sagas/{id}[?async=true]` | Start with your own ID (`409` if it exists) |
| `GET /sagas/{id}`, `GET /sagas/{id}/detail` | State; state plus timeline (truncated at `detail.max_timeline_events`) |
| `GET /health` (12080), `grpc.health.v1.Health` (12051) | Liveness / readiness, no credential |

## Server Configuration Rules

Keys live under `scalar.db.saga.server.*` and `scalar.db.saga.store.*`; the ScalarDB store keys are
plain `scalar.db.*`. An unknown or misspelled `scalar.db.saga.*` key **fails startup** rather than
being ignored. `--validate-config` checks the server keys, definitions and service files without
connecting to anything (exit `0` ok, `1` rejected, `2` bad command line, `3` check did not run) — it
does **not** check the `scalar.db.*` store keys. Run it in CI and before every deployment.

| Concern | Rule |
|---------|------|
| Secrets | Any `scalar.db.saga.*` value may use `${env:NAME}`, `${env:NAME:-fallback}` or `${file:UTF-8:/path}`. Plain `scalar.db.*` keys are resolved by ScalarDB, which supports `${env:...}` but **not** `${file:...}`. API-key secrets (`security.apikey.key.<name>.secret`) and `callback.secret` must always be a secret reference, never an inline literal |
| Security | `security.provider` is exactly one of `noop` (default), `apikey` or `jwt` (`jwt.jwks_url` must be https; `issuer` and `audience` required; roles from `roles_claim`, default `scope`). With `noop` and a non-loopback `host` the daemon **refuses to start** — do not defeat that with `security.insecure_mode.enabled`, which is local development only |
| Roles | `saga:read` ⊂ `saga:write` ⊂ `saga:admin`. Every admin operation requires `saga:admin`; the operator identity comes from the authenticated call (`principal`), never from a request field |
| Instance identity | Set `owner_id` to the pod name (`${env:HOSTNAME}`). The default random UUID is safe but untraceable, and two live instances must never share one — the claim is what stops two replicas driving the same saga |
| Recovery | `recovery.staleness_threshold_millis` (default 60000) is the "no progress" threshold. Set it **above the longest step timeout**, or a live saga is stolen from the instance still running it. `recovery.interval_seconds` (30), `recovery.max_recoveries_per_sweep` (1000, keep well above 200), `recovery.max_concurrent_recoveries` (10) |
| Admission control | `max_concurrent_saga_starts` and `max_start_requests_per_minute` (both default `0` = unlimited) protect the store; size them from the participants' capacity and surface `DB-SAGA-20004` / `20006` to callers as retryable |
| Synchronous starts | `sync.max_wait_millis` (60000) caps one blocking request; the client keeps watching after a `202`. `default_saga_timeout_millis` (0) applies to definitions without their own timeout |
| Shutdown | `shutdown.mode=WAIT_CURRENT_STEP` (default) finishes the running step and leaves the rest for recovery; `WAIT_ALL_SAGAS` needs `shutdown.timeout_millis` (30000) sized to the longest saga. Budget `terminationGracePeriodSeconds` above the drain budget |
| Service files | One `<service>.properties` in `services_path` per `service` named in a definition; only `base_url` is required. `header.<name>` adds a header to every call; `X-Saga-Id` / `X-Saga-Step` / `X-Saga-Callback-Url` / `X-Saga-Failure-Url` are reserved — naming one is rejected. `allowed_hosts` (bounded by `egress.allowed_hosts_ceiling`) is host-name-only defense in depth, not a sandbox; `max_body_bytes` 1 MiB default, 64 MiB max. `${file:...}` in a service file must stay under `secrets_root` (`/run/secrets`) |
| TLS | `tls.enabled` must be set explicitly whenever a cert or key is configured or present at the default path; one PEM chain + unencrypted PKCS#8 key covers REST and gRPC, TLS 1.3/1.2, no mTLS. Files must be readable by uid `201`. Kubernetes `grpc` probes cannot reach a TLS listener — use `httpGet` with `scheme: HTTPS` on `/health` |
| Async callbacks | Set `callback.base_url` and `callback.secret` together or neither; without them, definitions with `async` steps are rejected. `callback.max_age_seconds` (0 = unlimited) must exceed the longest a step legitimately stays parked. Use `https` when TLS is on |
| Reload | `reload.interval_seconds` (30) re-reads definitions, service files, TLS material and egress CAs; the whole candidate set is validated before anything applies, and the apply log line carries a SHA-256 for comparing replicas. Removing a definition makes new starts fail with `422` / `SAGA_DEFINITION_NOT_SERVED`; running sagas finish. Rollback is roll-forward only (re-register the old content as a new version). The properties file itself is never reloaded |
| Retention | `retention.period_seconds` (604800), `retention.interval_seconds` (60), `retention.max_purges_per_pass` (10000) must keep up with the terminal-saga rate over one interval, or the backlog grows |
| Store | `scalar.db.saga.store.max_event_payload_bytes` (1 MiB; also the gRPC max message size), `transaction_max_attempts` (3) |

## Operations

Escalated sagas are the operator's queue. `AdminService` / `GrpcSagaAdminClient` offers list by
status, `recoverSaga` (drives a stuck `RUNNING` / `COMPENSATING` saga now, in the direction the
pivot chooses), `forceComplete` (marks an `ESCALATED` saga `COMPLETED` without running its remaining
steps) and `resetEscalated` (returns it to the engine). Wrong-state preconditions surface as
`FAILED_PRECONDITION` (REST 422); a lost compare-and-set as `ABORTED` (REST 409).

Design the operational runbook alongside the saga: who watches `ESCALATED`, what evidence the event
history gives them (`GET /sagas/{id}/detail`), which interventions are permitted per saga, and which
`DB-SAGA-` codes page someone.
