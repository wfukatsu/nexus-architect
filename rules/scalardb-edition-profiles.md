# ScalarDB Edition Profiles

Reference snapshot for **ScalarDB 3.19**, taken from the OKF knowledge bundle
(`products/scalardb/3.19/features.md`, `releases/release-notes.md`,
`releases/release-support-policy.md`, and each concept's frontmatter `editions`).

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
| Consensus Commit, multi-storage transactions, two-phase commit interface | Yes | Yes | Yes | – |
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

**Private Preview** features (ABAC, vector search, remote replication) require contacting Scalar to
enable. Flag the preview status whenever one enters a design — it is not a general-availability
commitment.

The most common mistake this table corrects: **the SQL/JDBC interface is Enterprise Premium, not
Enterprise Standard.** A design that assumes SQL on a Standard contract does not deploy.

## New in 3.19

Source: `products/scalardb/3.19/releases/release-notes.md` (v3.19.0, released 2026-08-02).

| Capability | Edition | Why it changes a design |
|------------|---------|-------------------------|
| **Global Transaction API** (`GlobalTransactionManager`) on the Cluster client SDK | Enterprise Standard / Premium | A single transaction spanning multiple processes — microservice transactions — written against the **one-phase** interface. The Transaction Coordinator drives 2PC underneath. The same application code also runs for single-Cluster transactions; only configuration selects which. See @rules/scalardb-2pc-patterns.md |
| **Transaction Coordinator node** for the separated-cluster deployment pattern | Enterprise Standard / Premium | Removes the need for applications to orchestrate `prepare`/`validate`/`commit` themselves in a separated-cluster topology |
| Consensus Commit recovery: `write_set_logging`, `finishTransaction()`, `recoverRecord()` | Community and above | Operational recovery surface; **not** an application API. See @rules/scalardb-exception-handling.md |
| OpenTelemetry support | Enterprise Standard / Premium | Tracing/metrics export for observability design |
| Attribute-based authentication | Enterprise Standard / Premium | Distinct from ABAC (authorization, Premium Option) |
| Active-transaction cap (`max_active_transactions`, default 10000) | Community and above | Bounds resource growth from resumable transactions |
| `ABORTED` + `google.rpc.ErrorInfo` on the Cluster pause RPC | Enterprise Standard / Premium | A pause failure with reason `TIMED_OUT_STILL_PAUSED` must **not** be followed by an unpause; a lost race is now retryable |
| Bouncy Castle / grpc_health_probe CVE fixes | Enterprise Standard / Premium | Material argument when a project weighs staying on 3.18 or earlier |

The 3.19 guide pages have not caught up with the Global Transaction API and Transaction Coordinator
— `scalardb-cluster/deployment-patterns-for-microservices.md` still describes only the pre-3.19
shared/separated choice. Ground those two on the release notes and say so.

## Version Support (as of 2026-08-05)

Source: `products/scalardb/index.md`, `releases/release-support-policy.md`.

| Line | Newest patch | Maintenance | Maintenance support ends |
|------|--------------|-------------|--------------------------|
| 3.19 (latest) | 3.19.0 | supported | TBD |
| 3.18 | 3.18.1 | supported | 2027-08-02 |
| 3.17 | 3.17.4 | supported | 2027-05-01 |
| 3.16 | 3.16.6 | supported | 2026-11-26 |
| 3.15 | 3.15.9 | **unmaintained** | ended 2026-06-23 |
| 3.14 | 3.14.6 | **unmaintained** | ended earlier |

Greenfield projects target **3.19**. A project on 3.15 or 3.14 is past maintenance support — report
that as a finding and propose the nearest supported line, per @rules/dependency-versions.md.
Re-read `products/scalardb/index.md` rather than trusting this table after a bundle update.

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
| **Shared cluster** — every microservice talks to one Cluster instance | One-phase commit | The documented default. Simplest transaction and error handling, fewest resources; weaker resource isolation and one team owns the shared instance |
| **Separated cluster + Transaction Coordinator** (3.19+) | One-phase commit via `GlobalTransactionManager` | Per-service Cluster instances with the Coordinator driving 2PC underneath — isolation without hand-written 2PC |
| **Separated cluster, application-driven 2PC** | Two-phase commit interface | Pre-3.19, or where the Coordinator node is not deployed. Requires the application to sequence `prepare`/`validate`/`commit` and handle partial failure |

Spring Data JDBC does not support the shared-cluster pattern; it supports the two-phase commit
interface and the separated-cluster pattern only.

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
| Transactions spanning microservices, minimal application complexity | Enterprise Standard+ with the shared-cluster pattern, or 3.19 Global Transaction API |
| Transactions spanning microservices, strict per-service isolation | Enterprise Standard+ with separated cluster + Transaction Coordinator (3.19+) |
| Cross-service consistency where a single ACID transaction is not possible | ScalarDB Saga — see @rules/scalardb-saga-patterns.md |

SLA and support-hour commitments come from the customer's commercial contract
(`scalar-licensing/commercial.md`), not from the edition name. Do not state an SLA figure in a
deliverable unless the project's contract has been confirmed.
