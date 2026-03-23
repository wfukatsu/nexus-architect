# ScalarDB Reference Documentation for MySQL Migration

This file contains comprehensive reference information for MySQL to ScalarDB migration, compiled from official documentation.

---

## MANDATORY REFERENCES FOR MIGRATION

The following references MUST be consulted during MySQL -> ScalarDB migration:

### Primary Migration Path: ScalarDB SQL

| Reference | URL | When to Use |
|-----------|-----|-------------|
| **ScalarDB Cluster SQL (JDBC) Getting Started** | https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/getting-started-with-scalardb-cluster-sql-jdbc/ | Initial JDBC setup |
| **ScalarDB SQL Grammar Reference** | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/grammar/ | Query syntax, DDL, DML |
| **ScalarDB SQL Migration Guide** | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/migration-guide | Step-by-step migration |

### Schema and Data Type References

| Reference | URL | When to Use |
|-----------|-----|-------------|
| **MySQL Schema Loader Import** | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import/?databases=MySQL_MariaDB_TiDB | MySQL-specific import |
| **Schema Loader Data Type Mapping** | https://scalardb.scalar-labs.com/docs/latest/schema-loader/#data-type-mapping-between-scalardb-and-other-databases | Type conversion |
| **Decoupling Transaction Metadata** | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import/#decoupling-transaction-metadata | **RECOMMENDED** for migration |

### Analytics (for Complex Queries)

| Reference | URL | When to Use |
|-----------|-----|-------------|
| **ScalarDB Analytics Overview** | https://scalardb.scalar-labs.com/docs/latest/scalardb-analytics/ | Subqueries, window functions |
| **ScalarDB Analytics Quickstart** | https://scalardb.scalar-labs.com/docs/3.16/scalardb-analytics/quickstart/ | Analytics setup |

### Advanced Features

| Reference | URL | When to Use |
|-----------|-----|-------------|
| **Vector Search** | https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/getting-started-with-vector-search/ | RAG, AI use cases (Public Preview) |
| **Object Storage Requirements** | https://scalardb.scalar-labs.com/docs/latest/requirements/#object-storage | Object storage support (Private Preview) |
| **Object Storage (S3)** | https://scalardb.scalar-labs.com/docs/latest/configurations/?databases=S3#storage-related-configurations | S3 backend |
| **Object Storage (Azure Blob)** | https://scalardb.scalar-labs.com/docs/latest/configurations/?databases=Blob_Storage#storage-related-configurations | Azure backend |
| **Object Storage (GCS)** | https://scalardb.scalar-labs.com/docs/latest/configurations/?databases=Cloud_Storage#storage-related-configurations | GCS backend |

### General References

| Reference | URL |
|-----------|-----|
| **Main Documentation** | https://scalardb.scalar-labs.com/docs/latest/ |
| **Supported Databases** | https://scalardb.scalar-labs.com/docs/latest/requirements/#databases |
| **Features Overview** | https://scalardb.scalar-labs.com/docs/latest/features |

---

## 1. What is ScalarDB?

ScalarDB is a **universal hybrid transaction/analytical processing (HTAP) engine** for diverse databases. It functions as middleware that operates across multiple database systems, enabling unified operations without replacing existing infrastructure.

### Key Capabilities

| Capability | Description |
|------------|-------------|
| ACID Transactions | Provides ACID transaction guarantees across different database systems simultaneously |
| Real-Time Analytics | Enables analytical processing without disrupting transactional workloads (HTAP) |
| Database Agnosticism | Integrates with existing databases as middleware, preserving infrastructure investments |
| Virtual Unification | Virtually unifies diverse databases by achieving ACID transactions and real-time analytics across them |

### Editions

| Edition | Features |
|---------|----------|
| Community | Transaction processing across databases using primitive interfaces |
| Enterprise Standard | Clustering, non-transactional storage operations, authentication/authorization |
| Enterprise Premium | SQL interface, GraphQL, data encryption at rest, attribute-based access control, Vector Search |
| ScalarDB Analytics | Analytical query processing across ScalarDB-managed and non-managed data sources |

---

## 2. Supported Databases

### Relational Databases (ScalarDB 3.17+)

| Database | Supported Versions |
|----------|-------------------|
| MySQL | 8.4, 8.0 |
| MariaDB | 11.4, 10.11 |
| TiDB | 8.5, 7.5, 6.5 |
| PostgreSQL | 17, 16, 15, 14, 13 |
| Oracle Database | 23ai, 21c, 19c |
| IBM Db2 | 12.1, 11.5 |
| Aurora MySQL | 3, 2 |
| Aurora PostgreSQL | 17, 16, 15, 14, 13 |
| AlloyDB | 16, 15 |
| SQL Server | 2022, 2019, 2017 |
| SQLite | 3 |
| YugabyteDB | 2 |

### NoSQL Databases

| Database | Notes |
|----------|-------|
| Amazon DynamoDB | All versions supported |
| Apache Cassandra | 5.0, 4.1, 3.11, 3.0 |
| Azure Cosmos DB | NoSQL API |

### Object Storage (Private Preview)

- Amazon S3
- Azure Blob Storage
- Google Cloud Storage

---

## 3. Data Type Mapping: MySQL to ScalarDB

### Official MySQL/MariaDB/TiDB Type Mapping

| MySQL Type | ScalarDB Type | Notes |
|------------|---------------|-------|
| bigint | BIGINT | **Warning**: Range limited to -2^53 to 2^53 |
| binary | BLOB | |
| bit | BOOLEAN | |
| blob | BLOB | **Warning**: Max ~2GB in ScalarDB |
| char | TEXT | **Warning**: ScalarDB may use larger type |
| date | DATE | |
| datetime | TIMESTAMP (default) / TIMESTAMPTZ | TIMESTAMPTZ assumes UTC |
| double | DOUBLE | |
| float | FLOAT | |
| int | INT | |
| int unsigned | BIGINT | **Warning**: ScalarDB may use larger type |
| integer | INT | |
| longblob | BLOB | |
| longtext | TEXT | |
| mediumblob | BLOB | **Warning**: ScalarDB may use larger type |
| mediumint | INT | **Warning**: ScalarDB may use larger type |
| mediumtext | TEXT | **Warning**: ScalarDB may use larger type |
| smallint | INT | **Warning**: ScalarDB may use larger type |
| text | TEXT | **Warning**: ScalarDB may use larger type |
| time | TIME | |
| timestamp | TIMESTAMPTZ | |
| tinyblob | BLOB | **Warning**: ScalarDB may use larger type |
| tinyint | INT | **Warning**: ScalarDB may use larger type |
| tinyint(1) | BOOLEAN | |
| tinytext | TEXT | **Warning**: ScalarDB may use larger type |
| varbinary | BLOB | **Warning**: ScalarDB may use larger type |
| varchar | TEXT | **Warning**: ScalarDB may use larger type |

### NOT Supported Data Types

| MySQL Type | Reason | Workaround |
|------------|--------|------------|
| bigint unsigned | Exceeds ScalarDB BIGINT range | Validate data, use TEXT if needed |
| bit(n) where n > 1 | Not supported | Use BLOB |
| decimal | No exact decimal support | Use DOUBLE (precision loss) or TEXT |
| enum | Not supported | Use TEXT, validate in application |
| geometry | No spatial support | NOT SUPPORTED |
| json | Not supported | Use TEXT, parse in application |
| numeric | No exact decimal support | Use DOUBLE (precision loss) or TEXT |
| set | Not supported | Use TEXT or separate table |
| year | Not supported | Use INT |

---

## 4. Critical Warnings

### Warning 1: BIGINT Range Limitation

The value range of BIGINT in ScalarDB is **-2^53 to 2^53** (-9,007,199,254,740,992 to 9,007,199,254,740,992), regardless of the size of bigint in MySQL.

**Impact**: If data outside this range exists in the imported table, ScalarDB cannot read it.

**Action**: Validate BIGINT columns before migration:
```sql
SELECT COUNT(*) FROM your_table
WHERE bigint_column < -9007199254740992
   OR bigint_column > 9007199254740992;
```

### Warning 2: Larger Data Types

For certain data types, ScalarDB may map a data type larger than that of the underlying database. This means you may see errors when putting a value with a size larger than the size specified in the underlying database.

**Affected Types**: char, mediumblob, mediumint, mediumtext, smallint, text, tinyblob, tinyint, tinytext, varbinary, varchar, int unsigned

### Warning 6: DateTime Timezone

When importing `datetime` as TIMESTAMPTZ, ScalarDB will assume the data is in the UTC time zone.

**Action**: If your data is not in UTC, convert before migration or use TIMESTAMP type.

---

## 5. Value Range Limitations

| ScalarDB Type | Range/Limit | MySQL Comparison | Migration Impact |
|---------------|-------------|------------------|------------------|
| BIGINT | -2^53 to 2^53 | BIGINT: -2^63 to 2^63 | Data validation required |
| BLOB | ~2GB (2^31-1 bytes) | LONGBLOB: 4GB | Large objects may truncate |
| DATE | 1000-01-01 to 9999-12-31 | Same | Compatible |
| TIME | 00:00:00.000000 to 23:59:59.999999 | Same | Compatible |
| TIMESTAMP | Millisecond precision | Microsecond precision | Precision loss possible |

---

## 6. ScalarDB SQL Capabilities (v3.17+)

### Supported Features

| Feature | Support | Notes |
|---------|---------|-------|
| SELECT, INSERT, UPDATE, DELETE | Supported | Full CRUD operations |
| JOIN (INNER, LEFT, RIGHT) | Supported | 2-3 table joins |
| WHERE clauses | Supported | DNF or CNF form |
| ORDER BY | Supported | |
| LIMIT | Supported | |
| GROUP BY | Supported | v3.17+ |
| HAVING | Supported | v3.17+ |
| COUNT, SUM, AVG, MIN, MAX | Supported | Aggregate functions (v3.17+) |

### Features Requiring Workarounds

| Feature | Workaround |
|---------|------------|
| Subqueries | Convert to sequential queries or ScalarDB Analytics |
| UNION / INTERSECT / EXCEPT | Execute separately, merge in application |
| Window functions | Implement in application code or ScalarDB Analytics |
| AUTO_INCREMENT | UUID or application-level ID generator |
| Stored procedures | Convert to application code |
| Triggers | Application-level event handling |
| Events | External scheduler (cron, Kubernetes CronJob) |

### Read-Modify-Write Pattern

```sql
-- NOT SUPPORTED in ScalarDB
UPDATE accounts SET balance = balance + 100 WHERE id = 1;

-- REQUIRED PATTERN
-- Step 1: Read current value
SELECT balance FROM accounts WHERE id = 1;
-- Step 2: Calculate new value in application
-- Step 3: Update with new value
UPDATE accounts SET balance = 200 WHERE id = 1;
```

---

## 7. Schema Loader Commands

### Import Existing MySQL Tables

```bash
java -jar scalardb-schema-loader-<VERSION>.jar \
  --config scalardb.properties \
  --schema-file import_schema.json \
  --import
```

### Import Schema JSON Format

```json
{
  "namespace.existing_table": {
    "transaction": true,
    "override-columns-type": {
      "decimal_column": "TEXT",
      "json_column": "TEXT"
    }
  }
}
```

### With Transaction Metadata Decoupling (RECOMMENDED)

```json
{
  "namespace.existing_table": {
    "transaction-metadata-decoupling": true,
    "partition-key": ["id"],
    "columns": {
      "id": "BIGINT",
      "name": "TEXT"
    }
  }
}
```

---

## 8. Transaction Metadata

### What ScalarDB Adds

When using Consensus Commit transactions, ScalarDB adds metadata columns:

| Column | Purpose |
|--------|---------|
| tx_id | Transaction ID |
| tx_version | Record version |
| tx_state | Transaction state |
| tx_prepared_at | Timestamp when prepared |
| tx_committed_at | Timestamp when committed |
| before_* | Before-image for non-PK columns |

### Transaction Metadata Configuration Options

| Option | Configuration | Effect |
|--------|---------------|--------|
| Standard | `"transaction": true` | Adds metadata columns to existing table |
| Decoupling | `"transaction-metadata-decoupling": true` | Creates separate metadata table |

**RECOMMENDED**: Use `transaction-metadata-decoupling: true` for migrations.

---

## 9. ScalarDB Core vs ScalarDB Cluster

> **IMPORTANT**: ScalarDB SQL interface requires ScalarDB Cluster.

| Component | Use For | SQL Support |
|-----------|---------|-------------|
| **ScalarDB Core** | Schema Loader, Core API (Get/Put/Scan) | NO |
| **ScalarDB Cluster** | Application SQL access via JDBC | YES |

---

## 10. Configuration Examples

### ScalarDB Core Configuration (for Schema Loader)

```properties
# scalardb.properties (for Schema Loader)
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:mysql://localhost:3306/mydb
scalar.db.username=scalardb_user
scalar.db.password=scalardb_password

# Transaction settings
scalar.db.consensus_commit.isolation_level=SERIALIZABLE
scalar.db.consensus_commit.serializable_strategy=EXTRA_READ
```

### ScalarDB Cluster SQL Client Configuration

```properties
# scalardb-sql.properties
scalar.db.sql.connection_mode=cluster
scalar.db.sql.cluster_mode.contact_points=indirect:localhost
```

### Java JDBC Connection

```java
private Connection getConnection() throws SQLException {
    Connection connection = DriverManager.getConnection("jdbc:scalardb:scalardb-sql.properties");
    connection.setAutoCommit(false);
    return connection;
}
```

---

## 11. Unsupported MySQL Features

### Data Types

| Feature | Status | Workaround |
|---------|--------|------------|
| DECIMAL/NUMERIC | NOT SUPPORTED | Use DOUBLE or TEXT |
| ENUM | NOT SUPPORTED | Use TEXT |
| SET | NOT SUPPORTED | Use TEXT or separate table |
| JSON | NOT SUPPORTED | Use TEXT |
| Spatial types | NOT SUPPORTED | No workaround |
| YEAR | NOT SUPPORTED | Use INT |

### Schema Features

| Feature | Status | Workaround |
|---------|--------|------------|
| AUTO_INCREMENT | NOT SUPPORTED | UUID or app-level ID generator |
| Generated columns | NOT SUPPORTED | Compute in application |
| Foreign keys | NOT ENFORCED | Application-level validation |
| Check constraints | NOT ENFORCED | Application-level validation |
| Unique constraints | NOT ENFORCED | Application-level validation |
| Views | NOT SUPPORTED | Execute query or materialize as table |
| Triggers | NOT SUPPORTED | Application event handling |
| Events | NOT SUPPORTED | External scheduler |

### Stored Programs

| Feature | Status | Workaround |
|---------|--------|------------|
| Stored Procedures | NOT SUPPORTED | Convert to application methods |
| Stored Functions | NOT SUPPORTED | Convert to application methods |
| Triggers | NOT SUPPORTED | Application-level event handling |
| Events | NOT SUPPORTED | Kubernetes CronJob or cron |

---

## 12. Quick Reference: Migration Complexity

### Low Complexity (Direct Migration)

- Tables with INT, BIGINT, VARCHAR, TEXT, DATE, DATETIME columns
- Simple primary keys
- Basic indexes
- Simple CRUD queries
- Queries with GROUP BY and aggregations (v3.17+)

### Medium Complexity (Requires Adjustment)

- Tables with DECIMAL (precision loss)
- Tables with BLOB/TEXT columns
- Foreign key relationships
- CHECK constraints
- AUTO_INCREMENT
- Queries with JOINs

### High Complexity (Significant Rework)

- Stored procedures and functions
- Triggers
- Events (scheduler jobs)
- Views
- Subqueries and CTEs
- Window functions
- JSON columns with JSON functions
- ENUM and SET types
- Full-text search (consider Vector Search)

---

## 13. ScalarDB Vector Search (Public Preview)

> **Status**: Public Preview - requires Enterprise Premium license

ScalarDB Cluster provides a vector store abstraction for AI and RAG (Retrieval-Augmented Generation) use cases, leveraging **LangChain4j** for unified application interaction across different implementations.

### Supported Vector Stores

| Vector Store | Description |
|--------------|-------------|
| In-memory | Development/testing |
| OpenSearch | Local and AWS OpenSearch |
| Azure Cosmos DB | NoSQL API |
| Azure AI Search | Azure cognitive search |
| pgvector | PostgreSQL extension |

### Supported Embedding Models

| Provider | Models |
|----------|--------|
| In-process | ONNX runtime-based embeddings |
| Amazon Bedrock | Titan embedding models |
| Azure OpenAI | Azure-hosted OpenAI models |
| Google Vertex AI | Google embedding models |
| OpenAI | OpenAI embedding models |

### Vector Search Configuration

```properties
# Vector store configuration
scalar.db.embedding.stores=my-store
scalar.db.embedding.stores.my-store.type=opensearch
scalar.db.embedding.stores.my-store.host=localhost
scalar.db.embedding.stores.my-store.port=9200

# Embedding model configuration
scalar.db.embedding.models=my-model
scalar.db.embedding.models.my-model.type=openai
scalar.db.embedding.models.my-model.api_key=${OPENAI_API_KEY}
```

### Java Client Integration

```java
ScalarDbEmbeddingClientFactory factory =
  ScalarDbEmbeddingClientFactory.builder()
    .withProperty("scalar.db.embedding.client.contact_points",
      "indirect:localhost")
    .build();
```

**Reference**: https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/getting-started-with-vector-search/

---

## 14. ScalarDB Object Storage Backend (Private Preview)

> **Status**: Private Preview - contact Scalar for access

ScalarDB 3.17+ supports object storage as a database backend for specific use cases.

### Supported Providers

| Provider | Status (3.17) |
|----------|---------------|
| Amazon S3 | Supported |
| Azure Blob Storage | Supported |
| Google Cloud Storage | Supported |

### Amazon S3 Configuration

```properties
# Storage type
scalar.db.storage=s3

# Bucket configuration (region/bucket-name)
scalar.db.contact_points=us-east-1/my-bucket

# AWS credentials
scalar.db.username=<AWS_ACCESS_KEY>
scalar.db.password=<AWS_SECRET_KEY>

# Performance tuning (optional)
scalar.db.s3.multipart_upload_part_size_bytes=<size>
scalar.db.s3.multipart_upload_max_concurrency=<concurrency>
scalar.db.s3.multipart_upload_threshold_size_bytes=<threshold>
scalar.db.s3.request_timeout_secs=<timeout>
```

**Required IAM Permissions**: `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`, `s3:ListBucket`

### Azure Blob Storage Configuration

```properties
# Storage type
scalar.db.storage=blob-storage

# Endpoint with container
scalar.db.contact_points=https://<ACCOUNT>.blob.core.windows.net/my-container

# Azure credentials
scalar.db.username=<STORAGE_ACCOUNT_NAME>
scalar.db.password=<STORAGE_ACCOUNT_KEY>

# Performance tuning (optional)
scalar.db.blob_storage.parallel_upload_block_size_bytes=<size>
scalar.db.blob_storage.parallel_upload_max_concurrency=<concurrency>
scalar.db.blob_storage.parallel_upload_threshold_size_bytes=<threshold>
scalar.db.blob_storage.request_timeout_secs=<timeout>
```

**Required Permission**: Access key with full storage access

### Google Cloud Storage Configuration

```properties
# Storage type
scalar.db.storage=cloud-storage

# Bucket name
scalar.db.contact_points=my-bucket

# GCP credentials
scalar.db.username=<PROJECT_ID>
scalar.db.password=<SERVICE_ACCOUNT_KEY_JSON>

# Performance tuning (optional)
scalar.db.cloud_storage.upload_chunk_size_bytes=<size>
```

**Required Role**: `Storage Object Admin (roles/storage.objectAdmin)`

### References

| Topic | URL |
|-------|-----|
| Object Storage Requirements | https://scalardb.scalar-labs.com/docs/latest/requirements/#object-storage |
| S3 Configuration | https://scalardb.scalar-labs.com/docs/latest/configurations/?databases=S3 |
| Azure Blob Configuration | https://scalardb.scalar-labs.com/docs/latest/configurations/?databases=Blob_Storage |
| GCS Configuration | https://scalardb.scalar-labs.com/docs/latest/configurations/?databases=Cloud_Storage |

---

*Reference compiled from ScalarDB official documentation (version 3.17)*
