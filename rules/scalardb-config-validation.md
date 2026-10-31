---
description: ScalarDB configuration validation rules — applies when writing or reviewing ScalarDB properties files
globs:
  - "**/*.properties"
  - "**/database.properties"
  - "**/scalardb*.properties"
---

# ScalarDB Configuration Validation Rules

What to check in a properties file and the mistakes that pass unnoticed. The properties
themselves — every key per backend with its default, the cluster client properties for the CRUD
and SQL/JDBC APIs, the contact-point formats and the placeholder syntax — are
`skills/common/references/configuration-reference.md`; validate against that catalogue, and use
this file for the checks it cannot express.

## Required Keys Are the Backend's Set

Every backend has a fixed required set (`scalar.db.storage`, `scalar.db.contact_points`, and the
credentials the backend takes — Cosmos DB has no username, DynamoDB Local also needs
`scalar.db.dynamo.endpoint_override`); multi-storage adds `storages`, `default_storage`,
`namespace_mapping` and the per-storage `scalar.db.multi_storage.storages.<name>.*` block. Take the
set from the reference's backend section, never from memory, and flag a file missing any key of it.

## Valid Values Are Closed Sets

`scalar.db.storage`, `scalar.db.transaction_manager` (`consensus-commit`, `single-crud-operation`,
or `cluster` through the Cluster client SDK) and `scalar.db.consensus_commit.isolation_level` take
only the values the reference lists. A value outside the set is a defect, not a typo to guess at.

With `single-crud-operation`, every `scalar.db.consensus_commit.*` property is **ignored** — flag a
file that sets both, the settings will not do what the author expects.

## Cluster Mode Mistakes

- **Missing mode prefix.** A cluster contact point is `<mode>:<host>` (`indirect:`,
  `direct-kubernetes:`); a bare host is the most common mistake:

  ```properties
  # CORRECT:
  scalar.db.contact_points=indirect:localhost

  # WRONG — missing mode prefix:
  scalar.db.contact_points=localhost
  ```

- **The wrong API's keys.** The CRUD API connects with `scalar.db.transaction_manager=cluster` and
  `scalar.db.contact_points`; the SQL/JDBC API with `scalar.db.sql.connection_mode=cluster` and
  `scalar.db.sql.cluster_mode.contact_points`. Credentials follow the same split: the SQL/JDBC
  cluster client authenticates with `scalar.db.sql.cluster_mode.username` / `.password`, **not**
  `scalar.db.username` / `.password`.

## Cross-Partition Scan Must Be Enabled Explicitly

Code that calls `Scan.newBuilder().all()` needs `scalar.db.cross_partition_scan.enabled=true`
(filtering and ordering have their own flags). Flag the code when the properties lack it.

## Group Commit Is Incompatible With the 2PC Interface

`scalar.db.consensus_commit.coordinator.group_commit.enabled=true` cannot be used with the
two-phase commit interface. Flag any properties file that sets both.

## Properties Added in 3.19

`scalar.db.consensus_commit.coordinator.write_set_logging.enabled` and
`scalar.db.active_transaction_management.max_active_transactions` (listed with their defaults in
the reference) are documented in `products/scalardb/3.19/releases/release-notes.md` (v3.19.0); the
`configurations.md` reference in the bundle has **not yet** been updated with them. Cite the
release notes, and re-verify against the project's pinned release before writing them into a
properties file (@rules/okf-knowledge-bundle.md).

## ScalarDB Saga Server Properties

Saga server configuration is a separate namespace (`scalar.db.saga.server.*`) with its own rules —
a misspelled key fails startup, and `${file:...}` secret references work there but not in the plain
`scalar.db.*` keys ScalarDB itself resolves. See @rules/scalardb-saga-patterns.md.
