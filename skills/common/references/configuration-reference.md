# ScalarDB Configuration Reference

## General Properties

| Property | Description | Default |
|----------|-------------|---------|
| `scalar.db.storage` | Storage type: `cassandra`, `cosmos`, `dynamo`, `jdbc`, `multi-storage` | — |
| `scalar.db.contact_points` | Connection endpoint (format varies by backend) | — |
| `scalar.db.contact_port` | Connection port | Backend-specific |
| `scalar.db.username` | Username / access key | — |
| `scalar.db.password` | Password / secret key | — |
| `scalar.db.transaction_manager` | `consensus-commit`, `single-crud-operation`, `cluster` | `consensus-commit` |
| `scalar.db.default_namespace_name` | Default namespace | — |
| `scalar.db.metadata.cache_expiration_time_secs` | Metadata cache expiration (`-1` = no expiration) | `60` |
| `scalar.db.active_transaction_management.expiration_time_millis` | Idle transaction expiration (`-1` = disable) | `-1` (core), `60000` (cluster) |

## Backend-Specific Properties

### JDBC (MySQL, PostgreSQL, Oracle, SQL Server, DB2, SQLite)

```properties
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:mysql://localhost:3306/
scalar.db.username=root
scalar.db.password=mysql
```

Contact point formats:
- **MySQL**: `jdbc:mysql://host:3306/`
- **PostgreSQL**: `jdbc:postgresql://host:5432/`
- **Oracle**: `jdbc:oracle:thin:@//host:1521/FREEPDB1`
- **SQL Server**: `jdbc:sqlserver://host:1433;encrypt=true;trustServerCertificate=true`
- **DB2**: `jdbc:db2://host:50000/sample`
- **SQLite**: `jdbc:sqlite:path/to/db`

JDBC connection pool:

| Property | Default |
|----------|---------|
| `scalar.db.jdbc.connection_pool.min_idle` | `20` |
| `scalar.db.jdbc.connection_pool.max_idle` | `50` |
| `scalar.db.jdbc.connection_pool.max_total` | `200` |
| `scalar.db.jdbc.prepared_statements_pool.enabled` | `false` |
| `scalar.db.jdbc.prepared_statements_pool.max_open` | `-1` (unlimited) |
| `scalar.db.jdbc.isolation_level` | DB-specific |

### Cassandra

```properties
scalar.db.storage=cassandra
scalar.db.contact_points=localhost
scalar.db.contact_port=9042
scalar.db.username=cassandra
scalar.db.password=cassandra
```

Schema options: `replication-strategy` (SimpleStrategy/NetworkTopologyStrategy), `replication-factor` (default 1), `compaction-strategy` (LCS/STCS/TWCS)

### DynamoDB

```properties
scalar.db.storage=dynamo
scalar.db.contact_points=us-east-1
scalar.db.username=<AWS_ACCESS_KEY_ID>
scalar.db.password=<AWS_SECRET_ACCESS_KEY>
```

| Property | Description |
|----------|-------------|
| `scalar.db.dynamo.endpoint_override` | Endpoint URL (for DynamoDB Local: `http://localhost:8000`) |
| `scalar.db.dynamo.namespace.prefix` | Prefix for namespace names |

Schema options: `ru` (default 10), `no-scaling`, `no-backup`

### Cosmos DB

```properties
scalar.db.storage=cosmos
scalar.db.contact_points=<COSMOS_DB_URI>
scalar.db.password=<COSMOS_DB_KEY>
```

| Property | Default |
|----------|---------|
| `scalar.db.cosmos.consistency_level` (`STRONG`, `BOUNDED_STALENESS`) | `STRONG` |

Schema options: `ru` (default 400), `no-scaling`

### Multi-Storage

```properties
scalar.db.storage=multi-storage
scalar.db.multi_storage.storages=mysql,cassandra
scalar.db.multi_storage.default_storage=mysql
scalar.db.multi_storage.namespace_mapping=ns1:mysql,ns2:cassandra

# Per-storage properties
scalar.db.multi_storage.storages.mysql.storage=jdbc
scalar.db.multi_storage.storages.mysql.contact_points=jdbc:mysql://localhost:3306/
scalar.db.multi_storage.storages.mysql.username=root
scalar.db.multi_storage.storages.mysql.password=mysql

scalar.db.multi_storage.storages.cassandra.storage=cassandra
scalar.db.multi_storage.storages.cassandra.contact_points=localhost
scalar.db.multi_storage.storages.cassandra.username=cassandra
scalar.db.multi_storage.storages.cassandra.password=cassandra
```

## Consensus Commit Properties

| Property | Default |
|----------|---------|
| `scalar.db.consensus_commit.isolation_level` | `SNAPSHOT` |
| `scalar.db.consensus_commit.serializable_strategy` | `EXTRA_READ` |
| `scalar.db.consensus_commit.coordinator.namespace` | `coordinator` |
| `scalar.db.consensus_commit.include_metadata.enabled` | `false` |
| `scalar.db.consensus_commit.parallel_executor_count` | `128` |
| `scalar.db.consensus_commit.parallel_preparation.enabled` | `true` |
| `scalar.db.consensus_commit.parallel_commit.enabled` | `true` |
| `scalar.db.consensus_commit.parallel_rollback.enabled` | follows `parallel_commit` |
| `scalar.db.consensus_commit.async_commit.enabled` | `false` |
| `scalar.db.consensus_commit.async_rollback.enabled` | follows `async_commit` |
| `scalar.db.consensus_commit.one_phase_commit.enabled` | `false` |

Isolation levels: `SNAPSHOT`, `SERIALIZABLE`, `READ_COMMITTED`

## Cross-Partition Scan Properties

| Property | Default |
|----------|---------|
| `scalar.db.cross_partition_scan.enabled` | `false` |
| `scalar.db.cross_partition_scan.filtering.enabled` | `false` |
| `scalar.db.cross_partition_scan.ordering.enabled` | `false` |

## Cluster Client Properties (CRUD API)

```properties
scalar.db.transaction_manager=cluster
scalar.db.contact_points=indirect:<CLUSTER_HOST>
```

| Property | Default |
|----------|---------|
| `scalar.db.contact_port` | `60053` |
| `scalar.db.cluster.grpc.deadline_duration_millis` | `60000` |
| `scalar.db.cluster.grpc.max_inbound_message_size` | gRPC default |
| `scalar.db.cluster.grpc.max_inbound_metadata_size` | gRPC default |
| `scalar.db.cluster.client.scan_fetch_size` | `10` |
| `scalar.db.cluster.client.piggyback_begin.enabled` | `false` |
| `scalar.db.cluster.client.write_buffering.enabled` | `false` |

Auth:

| Property | Default |
|----------|---------|
| `scalar.db.cluster.auth.enabled` | `false` |
| `scalar.db.username` | — |
| `scalar.db.password` | — |

TLS:

| Property | Default |
|----------|---------|
| `scalar.db.cluster.tls.enabled` | `false` |
| `scalar.db.cluster.tls.ca_root_cert_pem` | — |
| `scalar.db.cluster.tls.ca_root_cert_path` | — |
| `scalar.db.cluster.tls.override_authority` | — |

## Cluster Client Properties (SQL/JDBC API)

```properties
scalar.db.sql.connection_mode=cluster
scalar.db.sql.cluster_mode.contact_points=indirect:<CLUSTER_HOST>
```

| Property | Default |
|----------|---------|
| `scalar.db.sql.cluster_mode.contact_port` | `60053` |
| `scalar.db.sql.default_transaction_mode` | `TRANSACTION` |
| `scalar.db.sql.default_namespace_name` | — |
| `scalar.db.sql.cluster_mode.username` | — |
| `scalar.db.sql.cluster_mode.password` | — |

JDBC-specific:

| Property | Default |
|----------|---------|
| `scalar.db.sql.jdbc.default_auto_commit` | `true` |
| `scalar.db.sql.jdbc.default_read_only` | `false` |
| `scalar.db.sql.jdbc.sql_session_factory_cache.expiration_time_millis` | `10000` |

## Contact Points Format (Cluster Mode)

| Mode | Format | Description |
|------|--------|-------------|
| Indirect | `indirect:<hostname>` | Through load balancer |
| Direct-Kubernetes | `direct-kubernetes:<namespace>/<endpoint>` | Direct to K8s pods |
| Direct-Kubernetes | `direct-kubernetes:<endpoint>` | Default namespace |

## Placeholder Support

Properties support environment variables and system properties:
```properties
scalar.db.username=${env:DB_USER:-defaultUser}
scalar.db.password=${sys:db.password:-defaultPass}
```
