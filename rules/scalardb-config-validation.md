---
description: ScalarDB configuration validation rules — applies when writing or reviewing ScalarDB properties files
globs:
  - "**/*.properties"
  - "**/database.properties"
  - "**/scalardb*.properties"
---

# ScalarDB Configuration Validation Rules

## Required Properties by Storage Type

### JDBC (MySQL, PostgreSQL, Oracle, SQL Server)

Required:
- `scalar.db.storage=jdbc`
- `scalar.db.contact_points=<JDBC_URL>`
- `scalar.db.username=<user>`
- `scalar.db.password=<password>`

### Cassandra

Required:
- `scalar.db.storage=cassandra`
- `scalar.db.contact_points=<host>`
- `scalar.db.username=<user>`
- `scalar.db.password=<password>`

### DynamoDB

Required:
- `scalar.db.storage=dynamo`
- `scalar.db.contact_points=<region>`
- `scalar.db.username=<AWS_ACCESS_KEY_ID>`
- `scalar.db.password=<AWS_SECRET_ACCESS_KEY>`

For DynamoDB Local, also needed:
- `scalar.db.dynamo.endpoint_override=http://localhost:8000`

### Cosmos DB

Required:
- `scalar.db.storage=cosmos`
- `scalar.db.contact_points=<COSMOS_DB_URI>`
- `scalar.db.password=<COSMOS_DB_KEY>`

## Valid Values

### scalar.db.storage

Valid: `jdbc`, `cassandra`, `dynamo`, `cosmos`, `multi-storage`

### scalar.db.transaction_manager

Valid: `consensus-commit` (default), `single-crud-operation`, `cluster`

### scalar.db.consensus_commit.isolation_level

Valid: `SNAPSHOT` (default), `SERIALIZABLE`, `READ_COMMITTED`

## Cluster Mode Configuration

### CRUD API (Primitive Interface)

Required:
- `scalar.db.transaction_manager=cluster`
- `scalar.db.contact_points=<mode>:<host>`

### SQL/JDBC API

Required:
- `scalar.db.sql.connection_mode=cluster`
- `scalar.db.sql.cluster_mode.contact_points=<mode>:<host>`

## Contact Points Format

The contact points MUST be prefixed with the connection mode:

| Mode | Format | Example |
|------|--------|---------|
| Indirect (load balancer) | `indirect:<host>` | `indirect:lb.example.com` |
| Direct Kubernetes | `direct-kubernetes:<ns>/<ep>` | `direct-kubernetes:scalardb/scalardb-cluster` |
| Direct Kubernetes (default ns) | `direct-kubernetes:<ep>` | `direct-kubernetes:scalardb-cluster` |

Common mistake: omitting the mode prefix.

```properties
# CORRECT:
scalar.db.contact_points=indirect:localhost

# WRONG — missing mode prefix:
scalar.db.contact_points=localhost
```

## Cross-Partition Scan

Using `Scan.newBuilder().all()` requires explicit enablement:

```properties
scalar.db.cross_partition_scan.enabled=true
# Optional:
scalar.db.cross_partition_scan.filtering.enabled=true
scalar.db.cross_partition_scan.ordering.enabled=true
```

## Multi-Storage Configuration

Required:
- `scalar.db.storage=multi-storage`
- `scalar.db.multi_storage.storages=<name1>,<name2>`
- `scalar.db.multi_storage.default_storage=<name>`
- `scalar.db.multi_storage.namespace_mapping=<ns1>:<name1>,<ns2>:<name2>`
- Per-storage properties: `scalar.db.multi_storage.storages.<name>.<property>`

## SQL Authentication Properties

For SQL/JDBC cluster mode, use SQL-specific auth properties:
- `scalar.db.sql.cluster_mode.username` (NOT `scalar.db.username`)
- `scalar.db.sql.cluster_mode.password` (NOT `scalar.db.password`)

## Placeholder Support

Properties support environment variables and system properties:
```properties
scalar.db.username=${env:DB_USER:-defaultUser}
scalar.db.password=${sys:db.password:-defaultPass}
```
