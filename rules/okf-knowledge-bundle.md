# OKF Knowledge Bundle (ScalarDB / ScalarDL / ScalarDB Saga)

Version-pinned official documentation for ScalarDB, ScalarDL and ScalarDB Saga, vendored as the
[OKF-ScalarDB-ScalarDL](https://github.com/wfukatsu/OKF-ScalarDB-ScalarDL) bundle. It contains the
complete developers.scalar-labs.com docs — plus the documentation ScalarDB Saga keeps in its source
repository — split **per product and per version** (2,370 concepts, 4 products, 24 version lines),
so implementation decisions can be grounded in exactly the release a project runs — not in model
memory and not in "latest".

Applies whenever a skill **designs, implements, reviews, or migrates anything ScalarDB, ScalarDL or
ScalarDB Saga**: schema/transaction design, cross-service transaction and saga design, code
generation, configuration files, exception handling, edition selection, analytics, deployment, and
DB migration.

## 1. Locate the bundle

One command performs the whole resolution below — prefer it over manual steps:

```bash
${CLAUDE_PLUGIN_ROOT}/tools/update-okf-bundle.sh          # ensure available (fetches only if absent)
${CLAUDE_PLUGIN_ROOT}/tools/update-okf-bundle.sh update   # pull the newest bundle from remote
${CLAUDE_PLUGIN_ROOT}/tools/update-okf-bundle.sh status   # resolved path, commits, bundled versions
```

Also exposed as `/architect:update-knowledge` (`--latest` = update, `--status` = status).
Manually, resolve in this order and use the first hit:

1. `${CLAUDE_PLUGIN_ROOT}/knowledge/okf-scalardb-scalardl/okf/` — the git submodule. If the
   directory exists but is empty, initialize it:
   `git -C ${CLAUDE_PLUGIN_ROOT} submodule update --init knowledge/okf-scalardb-scalardl`
2. `~/.cache/nexus-architect/okf-scalardb-scalardl/okf/` — local cache. If absent, create it:
   `git clone --depth 1 https://github.com/wfukatsu/OKF-ScalarDB-ScalarDL.git ~/.cache/nexus-architect/okf-scalardb-scalardl`

If neither is obtainable (offline, no git), fall back to Context7 MCP / WebFetch as before, and
say explicitly that the answer is **not version-pinned**.

All paths below are relative to the resolved `okf/` root. Read
`guides/how-ai-agents-use-this-bundle.md` once per session before first use — it is the bundle's
own operating manual and its rules are binding.

## 2. Pin product, version, edition — before reading anything else

Never read concept pages until all three are fixed. Decision guide:
`guides/product-and-version-selection.md`.

| Question | How to decide |
|----------|---------------|
| **Product** | `scalardb` for all current ScalarDB work (Core, Cluster, SQL/GraphQL, Analytics, Data Loader). `scalardb-saga` when the requirement is a **cross-service** transaction that cannot be one ACID transaction — saga steps with compensations, or TCC. `scalardl` when tamper-evidence / execution-proof is a requirement (Ledger/Auditor, Contract/Function). `scalardb-community` only to investigate legacy ≤3.13 Community systems — never as a basis for new design. |
| **Version** | Existing project: read it from `build.gradle`/`pom.xml` (`com.scalar-labs` deps) or the Helm `image.tag`; the minor version (`3.19`) selects `products/<product>/<version>/`. New project: newest version whose `maintenance` is `supported` in `products/<product>/index.md`. Reuse/record the answer in `work/version-decisions.json` per @rules/dependency-versions.md; when pinning a dependency, use the `patch_version` from the concept frontmatter, not the directory name. |
| **Edition** | Confirm the project's contracted edition first (see @rules/scalardb-edition-profiles.md). Each concept's frontmatter `editions` lists where it applies — never propose an Enterprise-only feature to a Community project. Note the bundle uses five edition values: `Community`, `Enterprise Standard`, `Enterprise Premium`, `Enterprise Option` (add-on: Analytics, Scalar Manager) and `Enterprise Premium Option` (add-on on Premium: ABAC). If the edition is unknown, say so and ask before proposing edition-gated features. |

Current supported lines, as of bundle commit `e374f05` (bundle release v1.3.0, 2026-10-31):
**ScalarDB 3.20 (latest), 3.19, 3.18, 3.17, 3.16** — 3.15 is `unmaintained`, 3.14 `archived`;
**ScalarDL 3.14 (latest), 3.13, 3.12** — 3.11 and 3.10 `unmaintained`; **ScalarDB Saga 3.20
(latest, first GA)** — 3.19 is the `pre-release` alpha. Read the `maintenance` field in
`products/<product>/index.md` rather than trusting this line after an update.

**Outside the bundle** (as of 2026-10-31): **ScalarDB Native JDBC 3.20.0** and
**scalardb-postgres-frontend 3.20.0** (both new, Apache-2.0, no bundle product). The PostgreSQL
wire protocol on Cluster and its `scalar.db.postgres.*` keys appear in the bundle **only in
`products/scalardb/3.20/releases/release-notes.md`** — the 3.20 `features.md` and
`scalardb-cluster-configurations.md` do not list them yet. For these, ground on the release notes
and the upstream repositories through the digests @rules/scalardb-edition-profiles.md § New in
3.20, @rules/scalardb-native-jdbc-patterns.md and @rules/scalardb-postgres-frontend-patterns.md,
cite the upstream URL, and state which part of the answer is **not bundle-pinned**.

ScalarDB + ScalarDL combined architectures: verify the two pinned versions are mutually
compatible via each product's `requirements` / compatibility concepts. ScalarDB Saga stores its
state through ScalarDB, so pin its ScalarDB version too and check both.

## 3. Read the right concepts for the phase

Enter through `products/<product>/<version>/index.md` (concepts listed by lifecycle phase) and
open only what the task needs. Filter by frontmatter `lifecycle_phase`:

| nexus-architect skills | `lifecycle_phase` | Typical entry concepts |
|------------------------|-------------------|------------------------|
| define-requirements, select-scalardb-edition, design-scalardb, design-scalardb-analytics, scalardb:model | `design` | `design.md`, `data-modeling.md`, `consensus-commit.md`, `requirements.md` |
| generate-scalardb-code, implement-backlog, scalardb:build-app / config / crud-ops / jdbc-ops / error-handler / scaffold | `implement` | `api-guide.md`, `configurations.md`, `two-phase-commit-transactions.md`, `scalardb-samples/` |
| design-infrastructure, design-observability, design-disaster-recovery, generate-infra-code, migrate-* | `operate` | `scalar-kubernetes/`, `helm-charts/`, `backup-restore.md`, `*-status-codes.md`, `releases/release-notes.md` |

Cross-service transaction work reads two extra entry points:

| Question | Concepts |
|----------|----------|
| Which ScalarDB Cluster deployment pattern for microservices? | `products/scalardb/3.20/scalardb-cluster/deployment-patterns-for-microservices.md` (shared / separated on the Microservice Transaction API) and `scalardb-cluster/api-guide.md` § Microservice Transaction API; `scalardb-samples/microservice-transaction-sample-with-cluster/` for the configurations; `two-phase-commit-transactions.md` only for the deprecated interface (its 3.20 page carries the deprecation notice; the 3.19 page predates it). Digest: @rules/scalardb-2pc-patterns.md |
| Saga / TCC across services | `products/scalardb-saga/3.20/`: `overview.md` + `guides/model-your-workflow.md` (design), `getting-started.md` + `guides/run-saga-transactions.md` + `guides/rest-api.md` + `reference/saga-definitions.md` (implement), `guides/configurations.md` + `reference/server-configuration.md` + `server-deployment.md` + `guides/scalardb-saga-status-codes.md` + `reference/grpc-admin-api.md` + `releases/release-notes.md` (operate). The 3.19 line is the alpha with the old `reference/`-only layout — do not mix its key names into a 3.20 answer |
| A legacy SQL application sharing tables with ScalarDB on one database | Outside the bundle: `scalar-labs/scalardb-native-jdbc` `docs/` via @rules/scalardb-native-jdbc-patterns.md |
| psql / PostgreSQL drivers / BI over ScalarDB-managed data | `products/scalardb/3.20/releases/release-notes.md` (the only bundle page naming the wire protocol) plus, outside the bundle, `scalar-labs/scalardb-postgres-frontend` `LIMITATIONS.md` via @rules/scalardb-postgres-frontend-patterns.md |

**`releases/release-notes.md` is part of the reference, not an afterthought.** A capability
introduced in the newest minor is described there before the guide pages catch up — ScalarDB
3.20's PostgreSQL wire protocol and its `scalar.db.postgres.*` keys are in the 3.20 release notes
while `features.md` and `scalardb-cluster-configurations.md` do not list them (3.19's Transaction
Coordinator went through the same lag, closed in the 3.20 guide pages). When only the release
notes cover a capability, say so and treat the guide pages as stale rather than as a
contradiction.

## 4. Hard rules (from the bundle's operating manual)

- **Never answer across versions.** Config keys, error codes, and API signatures change between
  minors. One `products/<product>/<version>/` directory is the sole basis for an answer.
- **Config keys and API signatures come from the pinned reference, never from memory.**
- **Exception handling is grounded in the pinned `api-guide.md`** — retryability differs per
  exception (`UnknownTransactionStatusException` must not be blindly rolled back/retried).
- **Cross-service transactions use the one-phase Microservice Transaction API**; the 2PC interface
  is deprecated as of 3.19 — the 3.20 `two-phase-commit-transactions.md` opens with the notice,
  the 3.19 page predates it. Never use 2PC within a single service, and record any remaining 2PC
  use as an ADR deviation.
- **Skip `status: deprecated` concepts and `feature_status: [Deprecated]` features** for new
  design; flag Preview features before proposing them for production.
- **State the release when a concept is `prerelease: true`.** ScalarDB Saga 3.19 is the
  `3.19.0-alpha.1` snapshot; **3.20.0 is the first GA release** and renamed several server keys.
  Design on `products/scalardb-saga/3.20/`, take key names from its `guides/configurations.md`
  (digest: @rules/scalardb-saga-patterns.md), and do not present a 3.19 alpha key as settled.
- **Cite the frontmatter `resource` URL** when the answer relies on a concept. If the bundle has
  no grounds for a claim, say "not covered by the documentation" instead of guessing.

## 5. Precedence among sources

1. **This bundle** (pinned to the project's version) — authoritative for behavior, config, APIs.
2. **Local `rules/scalardb-*.md`** — fast pattern digests; keep using them for code shape, but
   when they disagree with the pinned bundle version, the bundle wins (the digests track one
   snapshot and drift).
3. **Context7 MCP / WebFetch (`llms-full.txt`)** — unpinned "latest"; use only when the bundle is
   unavailable or the topic is genuinely absent from it, and label the answer as unpinned.
