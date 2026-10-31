# ScalarDB Edition Profiles

Reference snapshot for **ScalarDB 3.20** from the OKF knowledge bundle (bundle v1.3.0:
`products/scalardb/3.20/features.md`, `releases/release-notes.md`,
`releases/release-support-policy.md`, and each concept's frontmatter `editions`), plus the three
Apache-2.0 products released beside it — ScalarDB Saga 3.20 GA (`products/scalardb-saga/3.20/`),
ScalarDB Native JDBC 3.20 and scalardb-postgres-frontend 3.20 (the last two are outside the bundle;
@rules/okf-knowledge-bundle.md §2). The feature table below is the 3.19 `features.md` layout; the
3.20 `features.md` adds no row for the PostgreSQL wire protocol, which is why that row cites the
release notes.

This file is a digest and it drifts. Before an edition-gated feature reaches a deliverable, verify it
against the project's own pinned release per @rules/okf-knowledge-bundle.md — the concept's
`editions` frontmatter is the binding statement, not the table below.

## Edition Vocabulary

The bundle uses five values; use these names in deliverables rather than "OSS".

| Value | What it is |
|-------|-----------|
| `Community` | ScalarDB Core, the Apache-2.0 library embedded in the application |
| `Enterprise Standard` | ScalarDB Cluster, commercially licensed |
| `Enterprise Premium` | ScalarDB Cluster plus the SQL/GraphQL/vector/encryption surface |
| `Enterprise Option` | Add-on sold separately: ScalarDB Analytics, Scalar Manager |
| `Enterprise Premium Option` | Add-on on top of Premium: attribute-based access control (ABAC) |

`Enterprise Option` and `Enterprise Premium Option` are **not** included in Premium — they are
contracted separately. Treating Analytics or ABAC as "we already have Premium" is a licensing error.

## Feature Availability (3.19)

Source: `products/scalardb/3.19/features.md`.

| Feature | Community (Core) | Enterprise Standard | Enterprise Premium | Analytics (Enterprise Option) |
|---------|:----------------:|:-------------------:|:------------------:|:-----------------------------:|
| Transactions across databases (primitive CRUD interface) | Yes | Yes | Yes | – |
| Consensus Commit, multi-storage transactions, two-phase commit interface (the 2PC interface ≤ 3.19 only) | Yes | Yes | Yes | – |
| Microservice Transaction API — `GlobalTransactionManager` handed out by the runtime | – (classes present, `TransactionFactory` refuses: `UnsupportedOperationException`) | Yes (3.19+) | Yes (3.19+) | – |
| Schema Loader / Data Loader | Yes | Yes | Yes | – |
| Clustering (ScalarDB Cluster) | – | Yes | Yes | – |
| Non-transactional storage operations | – | Yes (3.14+) | Yes (3.14+) | – |
| Authentication / authorization | – | Yes | Yes | – |
| Encryption at rest / wire encryption | – | – | Yes (3.14+) | – |
| Attribute-based access control (ABAC) | – | – | Yes (3.15+), **Enterprise Premium Option**, Private Preview | – |
| SQL interface (SQL API, JDBC, Spring Data JDBC, LINQ) | – | – | Yes | – |
| GraphQL interface | – | – | Yes | – |
| Vector search interface | – | – | Yes (3.15+), Private Preview | – |
| Remote replication | – | – | Yes (3.16+), Private Preview | – |
| Analytical queries over ScalarDB-managed sources | – | – | – | Yes (3.14+) |
| Analytical queries over non-ScalarDB-managed sources | – | – | – | Yes (3.15+) |
| Microservice Transaction API + Transaction Coordinator (separated clusters) | – | Yes (3.19+) | Yes (3.19+) | – |
| **PostgreSQL wire protocol on Cluster nodes** (`scalar.db.postgres.enabled`) | – | Enterprise, 3.20+ — **tier not stated** in the release notes; confirm against the contract | Enterprise, 3.20+ — same caveat | – |

**Private Preview** features (ABAC, vector search, remote replication) require contacting Scalar to
enable. Flag the preview status whenever one enters a design — it is not a general-availability
commitment.

The most common mistake this table corrects: **the SQL/JDBC interface is Enterprise Premium, not
Enterprise Standard.** A design that assumes SQL on a Standard contract does not deploy.

### Apache-2.0 products beside the editions (3.20 wave)

These are not edition features. They are separate Apache-2.0 releases that work with a Community
(Core) deployment as well as with Cluster; none of them unlocks an Enterprise capability.

| Product | What it gives | Needs | Rule |
|---------|---------------|-------|------|
| **ScalarDB Saga 3.20 (GA)** | Saga / TCC orchestration across services, state stored through ScalarDB | Consensus Commit as the transaction manager (the Cluster client-side `cluster` manager is rejected); Java 8+ for the client SDK, Java 25 for the embedded engine and the server image | @rules/scalardb-saga-patterns.md |
| **ScalarDB Native JDBC 3.20** | A legacy SQL application keeps its native SQL on tables ScalarDB also manages, one database per connection, no ScalarDB call | The vendor JDBC driver; `scalardb-native-tools setup` on the database; the same isolation level as every ScalarDB application on those tables; Java 11+ | @rules/scalardb-native-jdbc-patterns.md |
| **scalardb-postgres-frontend 3.20** (standalone) | psql / PostgreSQL drivers / BI over ScalarDB-managed data on ScalarDB Core — **no authentication, no TLS** | A trusted network or localhost binding; Java 17+. The authenticated form is the Cluster feature above | @rules/scalardb-postgres-frontend-patterns.md |

## New in 3.19

Source: `products/scalardb/3.19/releases/release-notes.md` (v3.19.0, released 2026-08-02).

| Capability | Edition | Why it changes a design |
|------------|---------|-------------------------|
| **Microservice Transaction API** (`GlobalTransactionManager` / `GlobalTransaction` / `BranchTransaction`; the release notes call it the Global Transaction API) on the Cluster client SDK | Enterprise Standard / Premium | A single transaction spanning multiple processes — microservice transactions — written against the **one-phase** interface. The Transaction Coordinator drives 2PC underneath. The same application code also runs for single-Cluster transactions; only configuration selects which. See @rules/scalardb-2pc-patterns.md |
| **Transaction Coordinator node** for the separated-cluster deployment pattern | Enterprise Standard / Premium | Removes the need for applications to orchestrate `prepare`/`validate`/`commit` themselves in a separated-cluster topology |
| **Two-phase commit interface deprecated** | all | The docs site states the 2PC interface is deprecated as of 3.19 and will be removed; the SQL `TWO_PHASE_COMMIT_TRANSACTION` mode likewise. New designs use the row above |
| Consensus Commit recovery: `write_set_logging`, `finishTransaction()`, `recoverRecord()` | Community and above | Operational recovery surface; **not** an application API. See @rules/scalardb-exception-handling.md |
| OpenTelemetry support | Enterprise Standard / Premium | Tracing/metrics export for observability design |
| Attribute-based authentication | Enterprise Standard / Premium | Distinct from ABAC (authorization, Premium Option) |
| Active-transaction cap (`max_active_transactions`, default 10000) | Community and above | Bounds resource growth from resumable transactions |
| `ABORTED` + `google.rpc.ErrorInfo` on the Cluster pause RPC | Enterprise Standard / Premium | A pause failure with reason `TIMED_OUT_STILL_PAUSED` must **not** be followed by an unpause; a lost race is now retryable |
| Bouncy Castle / grpc_health_probe CVE fixes | Enterprise Standard / Premium | Material argument when a project weighs staying on 3.18 or earlier |

The 3.19 guide pages never caught up with the Microservice Transaction API and Transaction
Coordinator; the 3.20 pages did — ground those two on
`products/scalardb/3.20/scalardb-cluster/deployment-patterns-for-microservices.md` and
`scalardb-cluster/api-guide.md` § Microservice Transaction API, not on the 3.19 line.

## New in 3.20

Source: `products/scalardb/3.20/releases/release-notes.md` (v3.20.0, released 2026-10-30). The
PostgreSQL wire protocol and its keys appear **only there** in the bundle — `features.md` and
`scalardb-cluster-configurations.md` do not list them yet — so cite the release notes for them.

| Capability | Edition | Why it changes a design |
|------------|---------|-------------------------|
| **PostgreSQL wire protocol** on ScalarDB Cluster nodes — `scalar.db.postgres.enabled`, port `scalar.db.postgres.port` (5432), `scalar.db.postgres.auth` = `userpass` \| `oidc_jwt`, TLS required by default with authentication | Enterprise (tier not stated) | psql, PostgreSQL drivers, ORMs and BI tools reach ScalarDB-managed data without the Java SDK or the Premium SQL surface. Not PostgreSQL semantics — @rules/scalardb-postgres-frontend-patterns.md |
| **Global transactions for ScalarDB SQL** — `GLOBAL_TRANSACTION` session mode, `BEGIN BRANCH` / `END BRANCH`; the Transaction Coordinator drives 2PC when `scalar.db.sql.enabled=true` | Enterprise Premium (SQL) | The one-phase microservice interface reaches SQL; the deprecated SQL 2PC statements have a successor |
| `join()` / `resume()` removed from `DistributedTransactionManager` and the Cluster client managers; **`TwoPhaseCommitTransactionManager` / `TwoPhaseCommitTransaction` absent from the Core 3.20.0 library** (verified by compilation in `samples/scalardb-transaction-tests`); SQL `JOIN` / `SUSPEND` / `RESUME` statements and their Spring Data methods removed; GraphQL `@twoPhaseCommit` removed; `SINGLETON` cluster client mode removed | all | Code on the application-driven 2PC interface or on resume-by-ID does not compile on 3.20 and must move to the Microservice Transaction API first. `active_transaction_management.enabled` was renamed to the two-phase-commit-scoped key; default expiration 60000 ms |
| `BranchTransaction.end(Status)` (SUCCESS \| FAILURE) required; `BranchTransaction.getGlobalTransactionId()` | Enterprise Standard / Premium | Every branch declares its outcome; `getId()` is now the branch's own ID |
| A commit always ends the transaction; later rollback / abort is a no-op | all | Drop the "rollback after a failed commit" idiom; `UnknownTransactionStatusException` handling is unchanged |
| Consensus Commit: parallel consecutive `Get`s (`parallel_batch_get`), parallel rollback, record recovery retries conflicts, writes no longer fail permanently on keys held by unfinished transactions | Community and above | Performance and recovery arguments; not an application API |
| TEXT comparisons in Unicode code-point order; SQL Server string parameters sent as VARCHAR; table import rejects collation-mismatched text types | all | Ordering-sensitive designs on SQL Server / Oracle / Db2 backends must re-check collation |
| SQL Server 2025 supported, 2017 dropped; SQL Server JDBC 13.6.0 (pre-1582 TIMESTAMPTZ values may need migration); Cosmos DB new containers use partition key definition V2; Schema Loader / Data Loader images on Java 21; emSign root CAs removed (CVE-2026-91403 / -114820), grpc_health_probe CVE fixes | all / Enterprise | Platform compatibility and the security argument for upgrading |

## Version Support (as of 2026-10-31)

Source: `products/scalardb/index.md` and `releases/release-support-policy.md` (bundle v1.3.0).

| Line | Newest patch | Maintenance | Maintenance support ends |
|------|--------------|-------------|--------------------------|
| 3.20 (latest) | 3.20.0 (2026-10-30) | supported | TBD |
| 3.19 | 3.19.1 | supported | TBD |
| 3.18 | 3.18.1 | supported | 2027-08-02 |
| 3.17 | 3.17.4 | supported | 2027-05-01 |
| 3.16 | 3.16.6 | supported — **ends 2026-11-26** | 2026-11-26 |
| 3.15 | 3.15.9 | **unmaintained** | ended 2026-06-23 |
| 3.14 | 3.14.6 | **unmaintained** | ended 2026-02-20 |

Greenfield projects target **3.20**; a project pinned to 3.19 is current and need not move. A
project on 3.16 has weeks of support left — raise it; a project on 3.15 or 3.14 is past maintenance
support — report that as a finding and propose the nearest supported line, per
@rules/dependency-versions.md. Re-read `products/scalardb/index.md` rather than trusting this table
after a bundle update.

## Deployment Modes

### Core (Community)
- Embedded in the application, used directly as a library
- No server process to operate
- No clustering, SQL, auth, or encryption

### Cluster (Enterprise Standard / Premium)
- Independent gRPC server cluster, deployed on Kubernetes via the Scalar Helm charts
- Applications connect through the Cluster client SDK (`indirect` or `direct-kubernetes` mode)
- Horizontally scalable; also available in `standalone-mode` for development

### Cluster topologies for microservices
Source: `scalardb-cluster/deployment-patterns-for-microservices.md` plus the 3.19 release notes.

| Topology | Application interface | When |
|----------|----------------------|------|
| **Shared cluster** — every microservice talks to one Cluster instance | One-phase commit (Microservice Transaction API with the Coordinator disabled) | The documented default. Simplest transaction and error handling, fewest resources; weaker resource isolation and one team owns the shared instance |
| **Separated cluster + Transaction Coordinator** (3.19+) | One-phase commit via the Microservice Transaction API (`GlobalTransactionManager`); identical code to the row above | Per-service Cluster instances with the Coordinator driving 2PC underneath — isolation without hand-written 2PC; more components, and the Coordinator table's database reachable from every cluster |
| **Separated cluster, application-driven 2PC** | Two-phase commit interface — **deprecated as of 3.19** | Pre-3.19 only, or an ADR-recorded deviation where the Coordinator node cannot be deployed. Requires the application to sequence `prepare`/`validate`/`commit` and handle partial failure |

Spring Data JDBC does not support the shared-cluster pattern; it supports the two-phase commit
interface and the separated-cluster pattern only — a Spring Data JDBC design that spans services
therefore inherits a deprecated interface, which is a finding to raise.

## Selection Criteria

| Requirement | Recommended edition |
|-------------|---------------------|
| Single-database transactions | Community |
| Transactions across multiple databases from one application | Community (Core) or Enterprise (Cluster) |
| Centralized connection management, auth, horizontal scaling | Enterprise Standard |
| SQL / JDBC / Spring Data JDBC / GraphQL / LINQ interface | **Enterprise Premium** |
| Encryption at rest or wire encryption | Enterprise Premium |
| Attribute-based access control | Enterprise Premium **Option** (Private Preview) |
| Analytical (HTAP) queries | ScalarDB Analytics — **Enterprise Option**, contracted separately |
| Transactions spanning microservices, minimal application complexity | Enterprise Standard+ with the shared-cluster pattern (Microservice Transaction API, 3.19+) |
| Transactions spanning microservices, strict per-service isolation | Enterprise Standard+ with separated cluster + Transaction Coordinator (Microservice Transaction API, 3.19+) |
| Cross-service consistency where a single ACID transaction is not possible | ScalarDB Saga (Apache-2.0, any edition) — see @rules/scalardb-saga-patterns.md |
| SQL tools, psql, BI or non-Java services must query ScalarDB-managed data | PostgreSQL wire protocol on Cluster 3.20+ (Enterprise, tier to confirm), or the standalone Apache-2.0 frontend on a trusted network — @rules/scalardb-postgres-frontend-patterns.md |
| An existing SQL application must keep its native SQL on one database shared with ScalarDB applications | ScalarDB Native JDBC (Apache-2.0; any edition) — @rules/scalardb-native-jdbc-patterns.md |

SLA and support-hour commitments come from the customer's commercial contract
(`scalar-licensing/commercial.md`), not from the edition name. Do not state an SLA figure in a
deliverable unless the project's contract has been confirmed.
