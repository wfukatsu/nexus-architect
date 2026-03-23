# ScalarDB Reference Documentation

This file contains comprehensive reference information for ScalarDB migration, compiled from official documentation.

---

## MANDATORY REFERENCES FOR MIGRATION

The following references MUST be consulted during Oracle → ScalarDB migration:

### Primary Migration Path: ScalarDB Java Transaction API

| Reference | URL | When to Use |
|-----------|-----|-------------|
| **ScalarDB Java Transaction API** | https://scalardb.scalar-labs.com/docs/latest/api-guide/ | Transaction API (Get/Scan/Insert/Update/Delete) |
| **ScalarDB SQL Grammar Reference** | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/grammar/ | Query syntax, DDL, DML reference |
| **ScalarDB SQL Migration Guide** | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/migration-guide | Step-by-step migration |

### Schema and Data Type References

| Reference | URL | When to Use |
|-----------|-----|-------------|
| **Schema Loader Data Type Mapping** | https://scalardb.scalar-labs.com/docs/latest/schema-loader/#data-type-mapping-between-scalardb-and-other-databases | Type conversion |
| **Schema Loader Import** | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import | Importing existing tables |
| **Decoupling Transaction Metadata** | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import/#decoupling-transaction-metadata | **RECOMMENDED** for migration |
| **Data Type Mapping (Import)** | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import#data-type-mapping-from-jdbc-databases-to-scalardb | Oracle → ScalarDB types |

### Analytics (for Complex Queries)

| Reference | URL | When to Use |
|-----------|-----|-------------|
| **ScalarDB Analytics Overview** | https://scalardb.scalar-labs.com/docs/latest/scalardb-analytics/ | Subqueries, window functions |
| **ScalarDB Analytics CLI** | https://scalardb.scalar-labs.com/docs/latest/scalardb-analytics/reference-cli-command/ | Analytics configuration |

### Vector Search (AI/ML Use Cases)

| Reference | URL | When to Use |
|-----------|-----|-------------|
| **Vector Search Getting Started** | https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/getting-started-with-vector-search/ | AI/ML similarity search |
| **Vector Search Configuration** | https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/scalardb-cluster-configurations/#scalardb-cluster-node-configurations-for-vector-search | Vector store setup |

### Object Storage (File/Binary Data)

| Reference | URL | When to Use |
|-----------|-----|-------------|
| **Object Storage Requirements** | https://scalardb.scalar-labs.com/docs/latest/requirements/#object-storage | S3, Azure Blob, GCS setup |
| **Storage Configuration** | https://scalardb.scalar-labs.com/docs/latest/configurations/ | Backend configuration |

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
| Enterprise Premium | SQL interface, GraphQL, data encryption at rest, attribute-based access control |
| ScalarDB Analytics | Analytical query processing across ScalarDB-managed and non-managed data sources |

---

## 2. Supported Databases

### Relational Databases (ScalarDB 3.17+)

| Database | Supported Versions |
|----------|-------------------|
| Oracle Database | 23ai, 21c, 19c |
| IBM Db2 | 12.1, 11.5 (Linux/UNIX/Windows only) |
| MySQL | 8.4, 8.0 |
| PostgreSQL | 17, 16, 15, 14, 13 |
| Aurora MySQL | 3, 2 |
| Aurora PostgreSQL | 17, 16, 15, 14, 13 |
| MariaDB | 11.4, 10.11 |
| TiDB | 8.5, 7.5, 6.5 |
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

ScalarDB supports object storage as a storage backend - see **Section 13** for detailed configuration.

| Provider | Configuration Value | Required Permissions |
|----------|--------------------|--------------------|
| Amazon S3 | `scalar.db.storage=s3` | s3:PutObject, s3:GetObject, s3:DeleteObject, s3:ListBucket |
| Azure Blob Storage | `scalar.db.storage=blob-storage` | Access key with full access |
| Google Cloud Storage | `scalar.db.storage=cloud-storage` | roles/storage.objectAdmin |

---

## 3. Data Type Mapping: ScalarDB to Databases

### Complete Mapping Table

| ScalarDB | Oracle | MySQL | PostgreSQL | SQL Server | Cassandra | DynamoDB |
|----------|--------|-------|------------|------------|-----------|----------|
| BOOLEAN | NUMBER(1) | boolean | boolean | bit | boolean | BOOL |
| INT | NUMBER(10) | int | int | int | int | N |
| BIGINT | NUMBER(16) | bigint | bigint | bigint | bigint | N |
| FLOAT | BINARY_FLOAT | real | real | float(24) | float | N |
| DOUBLE | BINARY_DOUBLE | double | double precision | float | double | N |
| TEXT | VARCHAR2(4000) | longtext | text | varchar(8000) | text | S |
| BLOB | BLOB | longblob | bytea | varbinary(8000) | blob | B |
| DATE | DATE | date | date | date | date | N |
| TIME | TIMESTAMP | time | time | time | time | N |
| TIMESTAMP | TIMESTAMP | datetime | timestamp | datetime2 | - | N |
| TIMESTAMPTZ | TIMESTAMP WITH TIME ZONE | datetime | timestamp with time zone | datetimeoffset | timestamp | N |

### Primary Key/Index Restrictions

When used as primary key or secondary index key, data types are converted differently:

| ScalarDB Type | Oracle (PK/Index) | MySQL (PK/Index) | PostgreSQL (PK/Index) |
|---------------|-------------------|------------------|----------------------|
| TEXT | VARCHAR2(128) | VARCHAR(128) | VARCHAR(10485760) |
| BLOB | VARBINARY(128) | VARBINARY(128) | VARBINARY(128) |

---

## 4. Data Type Mapping: Oracle to ScalarDB (Import)

### Oracle Data Types → ScalarDB

| Oracle Type | ScalarDB Type | Notes |
|-------------|---------------|-------|
| NUMBER(1) | BOOLEAN | Single digit numbers map to boolean |
| NUMBER(p,0) where p ≤ 9 | INT | Integer without decimal |
| NUMBER(p,0) where p ≤ 18 | BIGINT | Large integer without decimal |
| NUMBER(p,s) where s > 0 | DOUBLE | Numbers with decimal places |
| NUMBER (no precision) | DOUBLE | Unspecified precision |
| VARCHAR2(n) | TEXT | Variable character string |
| CHAR(n) | TEXT | Fixed-length becomes variable |
| NVARCHAR2(n) | TEXT | Unicode variable string |
| NCHAR(n) | TEXT | Unicode fixed-length |
| CLOB | TEXT | Character large object |
| NCLOB | TEXT | Unicode character large object |
| DATE | DATE | Date only (no time in ScalarDB) |
| TIMESTAMP | TIMESTAMP | Timestamp without timezone |
| TIMESTAMP WITH TIME ZONE | TIMESTAMPTZ | Timestamp with timezone (UTC normalized) |
| TIMESTAMP WITH LOCAL TIME ZONE | TIMESTAMPTZ | Local timezone converted |
| BINARY_FLOAT | FLOAT | 32-bit floating point |
| BINARY_DOUBLE | DOUBLE | 64-bit floating point |
| BLOB | BLOB | Binary large object |
| RAW(n) | BLOB | Raw binary data |
| LONG RAW | BLOB | Legacy binary (deprecated) |
| BFILE | NOT SUPPORTED | External file reference |
| XMLTYPE | NOT SUPPORTED | XML data type |
| SDO_GEOMETRY | NOT SUPPORTED | Spatial data type |
| User-defined types | NOT SUPPORTED | Object types, nested tables |

---

## 5. Value Range Limitations

### Critical Limitations

| ScalarDB Type | Range/Limit | Oracle Comparison | Migration Impact |
|---------------|-------------|-------------------|------------------|
| BIGINT | -2^53 to 2^53 | NUMBER: -10^126 to 10^126 | Data validation required |
| BLOB | ~2GB (2^31-1 bytes) | BLOB: (4GB-1) × blocks | Large objects may truncate |
| DATE | 1000-01-01 to 9999-12-31 | 4712 BC to 9999 AD | Historical dates may fail |
| TIME | 00:00:00.000000 to 23:59:59.999999 | N/A | Microsecond precision |
| TIMESTAMP | Millisecond precision | Nanosecond precision | Precision loss possible |

### Database-Specific Restrictions

| Database | Restriction |
|----------|-------------|
| Oracle | BLOB cannot be used in WHERE clause conditions |
| Oracle | BLOB cannot be partition key, clustering key, or secondary index key |
| YugabyteDB | Floating-point types cannot be primary/clustering keys |
| Object Storage | BLOB limited to 1.5 GiB maximum |

---

## 6. ScalarDB SQL Capabilities (v3.17+)

### Supported Features

| Feature | Support | Notes |
|---------|---------|-------|
| SELECT, INSERT, UPDATE, DELETE | ✅ Supported | Full CRUD operations |
| JOIN (INNER, LEFT, RIGHT) | ✅ Supported | 2-3 table joins |
| WHERE clauses | ✅ Supported | DNF or CNF form |
| ORDER BY | ✅ Supported | |
| LIMIT | ✅ Supported | |
| GROUP BY | ✅ Supported | Added in v3.17 |
| HAVING | ✅ Supported | Added in v3.17 |
| COUNT, SUM, AVG, MIN, MAX | ✅ Supported | Aggregate functions (v3.17+) |

### Features Requiring Workarounds

| Feature | Workaround |
|---------|------------|
| Subqueries | Convert to sequential queries or ScalarDB Analytics |
| UNION / INTERSECT / EXCEPT | Execute separately, merge in application |
| Window functions | Implement in application code or ScalarDB Analytics |
| Recursive CTEs | Implement in application code |
| PL/SQL blocks | Convert to application code |

### SQL Syntax Notes

#### JOIN Operations

ScalarDB requires JOINs to be written with explicit syntax:

```sql
-- ScalarDB preferred syntax
SELECT * FROM orders o INNER JOIN customers c ON o.customer_id = c.id
```

#### WHERE Clause Restrictions

Predicates must follow either:
- **Disjunctive Normal Form (DNF)**: OR of ANDs
- **Conjunctive Normal Form (CNF)**: AND of ORs

```sql
-- DNF Example (OR of ANDs)
WHERE (a = 1 AND b = 2) OR (a = 3 AND b = 4)

-- CNF Example (AND of ORs)
WHERE (a = 1 OR a = 3) AND (b = 2 OR b = 4)
```

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

### Create New Schema

```bash
java -jar scalardb-schema-loader-<VERSION>.jar \
  --config scalardb.properties \
  --schema-file scalardb_schema.json \
  --coordinator
```

### Import Existing Tables

```bash
java -jar scalardb-schema-loader-<VERSION>.jar \
  --config scalardb.properties \
  --schema-file import_schema.json \
  --import
```

### Schema JSON Format

```json
{
  "namespace.table_name": {
    "transaction": true,
    "partition-key": ["pk_column"],
    "clustering-key": ["ck_column ASC"],
    "columns": {
      "pk_column": "BIGINT",
      "ck_column": "TEXT",
      "data_column": "TEXT"
    },
    "secondary-index": ["indexed_column"]
  }
}
```

### Import Schema JSON Format

```json
{
  "namespace.existing_table": {
    "transaction": true,
    "override-columns-type": {
      "special_column": "TEXT"
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

There are **two mutually exclusive** ways to handle transaction metadata:

| Option | Configuration | Effect |
|--------|---------------|--------|
| Standard | `"transaction": true` | Adds metadata columns **directly to existing table** |
| Decoupling | `"transaction-metadata-decoupling": true` | Creates **separate metadata table** |

> **Important**: Use one OR the other - they cannot be used together on the same table.

### RECOMMENDED: Transaction Metadata Decoupling

**For migration scenarios, `transaction-metadata-decoupling: true` is strongly recommended** because it does NOT alter your existing tables.

**Reference**: https://scalardb.scalar-labs.com/docs/latest/schema-loader-import/#decoupling-transaction-metadata

#### Why Use Decoupling for Migration?

| Benefit | Description |
|---------|-------------|
| **No table alterations** | Original tables remain completely unchanged |
| **Easy rollback** | Simply drop the `_scalardb` metadata table to revert |
| **Data isolation** | Business data separate from infrastructure metadata |
| **Lower risk** | No schema changes to production tables |

#### Configuration Example

```json
{
  "namespace.table_name": {
    "transaction-metadata-decoupling": true,
    "partition-key": ["id"],
    "columns": {
      "id": "BIGINT",
      "name": "TEXT"
    }
  }
}
```

#### What Gets Created

When you enable `transaction-metadata-decoupling: true`:

| Table | Contents |
|-------|----------|
| `table_name` | **Unchanged** - original data |
| `table_name_scalardb` | Transaction metadata only |

**Application Access**: Use `<table_name>_scalardb` in your ScalarDB queries.

#### Comparison: Standard vs Decoupling

**Standard (`transaction: true`):**
```
Original Table (ALTERED)
├── id (PK)
├── name
├── tx_id (ADDED)
├── tx_version (ADDED)
├── tx_state (ADDED)
├── tx_prepared_at (ADDED)
├── tx_committed_at (ADDED)
└── before_name (ADDED)
```

**Decoupling (`transaction-metadata-decoupling: true`):**
```
Original Table (UNCHANGED)      Metadata Table (NEW)
├── id (PK)                     ├── id (PK)
└── name                        ├── tx_id
                                ├── tx_version
                                ├── tx_state
                                ├── tx_prepared_at
                                ├── tx_committed_at
                                └── before_name
```

---

## 9. ScalarDB Core vs ScalarDB Cluster

> **The ScalarDB Java Transaction API is available in both Core and Cluster.** Use Core for development/testing and Cluster for production distributed deployments.

| Component | Use For | Transaction API | SQL Support |
|-----------|---------|-----------------|-------------|
| **ScalarDB Core** | Schema Loader, Java Transaction API (Get/Scan/Insert/Update/Delete) | YES | NO |
| **ScalarDB Cluster** | Production deployment, distributed transactions, SQL (optional) | YES | YES |

**References**:
- https://scalardb.scalar-labs.com/docs/latest/api-guide/
- https://scalardb.scalar-labs.com/docs/latest/getting-started-with-scalardb/

---

## 10. Configuration Examples

### ScalarDB Core Configuration (for Schema Loader)

Use this configuration with `scalardb-schema-loader` for schema creation and data import:

```properties
# scalardb.properties (for Schema Loader - Core only)
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:oracle:thin:@//localhost:1521/ORCL
scalar.db.username=scalardb_user
scalar.db.password=scalardb_password

# Transaction settings
scalar.db.consensus_commit.isolation_level=SERIALIZABLE
scalar.db.consensus_commit.serializable_strategy=EXTRA_READ
```

### ScalarDB Java Transaction API Connection

Use the same `scalardb.properties` configuration for both Schema Loader and application access:

**Java Transaction API Connection:**
```java
import com.scalar.db.api.*;
import com.scalar.db.io.Key;
import com.scalar.db.service.TransactionFactory;

// Initialize (do once at startup)
TransactionFactory factory = TransactionFactory.create("scalardb.properties");
DistributedTransactionManager txManager = factory.getTransactionManager();

// Use in application code
DistributedTransaction tx = txManager.start();
try {
    // Get, Scan, Insert, Update, Delete operations
    tx.commit();
} catch (Exception e) {
    tx.rollback();
    throw e;
}
```

**Reference**: https://scalardb.scalar-labs.com/docs/latest/api-guide/

---

## 10. Unsupported Oracle Features

### Object-Relational Features

| Feature | Status | Workaround |
|---------|--------|------------|
| Object Types | NOT SUPPORTED | Flatten to columns |
| Nested Tables | NOT SUPPORTED | Separate table with FK |
| VARRAYs | NOT SUPPORTED | Separate table or JSON |
| REF Types | NOT SUPPORTED | Store ID reference |
| Object Views | NOT SUPPORTED | N/A |

### PL/SQL Features

| Feature | Status | Workaround |
|---------|--------|------------|
| Stored Procedures | NOT SUPPORTED | Convert to application methods |
| Functions | NOT SUPPORTED | Convert to application methods |
| Packages | NOT SUPPORTED | Convert to application classes |
| Triggers | NOT SUPPORTED | Application-level event handling |
| AUTONOMOUS_TRANSACTION | NOT SUPPORTED | Separate transaction in app |
| BULK COLLECT | NOT SUPPORTED | Batch processing in app |
| FORALL | NOT SUPPORTED | Batch processing in app |
| PIPELINED functions | NOT SUPPORTED | Streaming in app |
| %TYPE / %ROWTYPE | NOT SUPPORTED | Explicit types in app |

### Other Features

| Feature | Status | Workaround |
|---------|--------|------------|
| Sequences | NOT SUPPORTED | UUID or app-level ID generator |
| Materialized Views | NOT SUPPORTED | App-level caching |
| Views | PARTIAL | Import as table or implement as query |
| Synonyms | NOT SUPPORTED | Update references directly |
| Database Links | NOT SUPPORTED | Configure multiple connections |
| VPD Policies | NOT SUPPORTED | App-level security |
| Partitioning | NOT SUPPORTED | Handled by underlying DB |
| IOT (Index-Organized Tables) | NOT SUPPORTED | Regular table |
| External Tables | NOT SUPPORTED | Import data first |
| XMLType | NOT SUPPORTED | Store as TEXT |
| Spatial (SDO_GEOMETRY) | NOT SUPPORTED | Custom solution needed |
| JSON columns | NOT SUPPORTED | Store as TEXT |

---

## 11. ScalarDB Analytics (Separate Component)

### Overview

ScalarDB Analytics is a **separate component** from core ScalarDB transaction processing. It provides:
- Analytical query processing across ScalarDB-managed data sources
- Analytical query processing across non-ScalarDB-managed data sources
- Integration with Spark (3.5, 3.4) and Scala (2.13, 2.12)

### When to Use Analytics

| Scenario | ScalarDB SQL | ScalarDB Analytics |
|----------|--------------|-------------------|
| Simple CRUD | ✅ Use | Not needed |
| JOINs | ✅ Use | Not needed |
| GROUP BY + Aggregations | ✅ Use (v3.17+) | Not needed |
| Subqueries | ❌ | ✅ Use |
| Window functions | ❌ | ✅ Use |

**Note**: Analytics CLI is NOT required for basic schema migration. It's used for complex analytical workloads.

---

## 12. Vector Search (AI/ML Capabilities)

> **License Required**: Vector Search requires a ScalarDB Enterprise trial or commercial license.

### Overview

ScalarDB Cluster provides **vector search capabilities** for AI-driven use cases such as semantic search, recommendation systems, and RAG (Retrieval-Augmented Generation) applications. Vector search enables similarity-based queries on high-dimensional embedding vectors.

**Reference**: https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/getting-started-with-vector-search/

### Supported Vector Store Backends

| Backend | Description | Use Case |
|---------|-------------|----------|
| **In-memory** | Built-in memory-based store | Development, small datasets |
| **OpenSearch** | Elasticsearch-compatible | Production, large-scale |
| **Azure Cosmos DB NoSQL** | Microsoft cloud-native | Azure environments |
| **Azure AI Search** | Microsoft cognitive search | Azure AI workloads |
| **pgvector** | PostgreSQL extension | Existing PostgreSQL infrastructure |

### Supported Embedding Models

| Provider | Models | Notes |
|----------|--------|-------|
| **In-process (ONNX)** | ONNX runtime-based | No external API calls |
| **Amazon Bedrock** | Titan embedding models | AWS integration |
| **Azure OpenAI** | Ada, text-embedding-3 | Azure integration |
| **Google Vertex AI** | text-embedding-gecko | GCP integration |
| **OpenAI** | text-embedding-ada-002, text-embedding-3 | Direct OpenAI API |

### Integration Approach

ScalarDB Vector Search uses the **LangChain4j** abstraction through the Java Client SDK:

```java
// Example: Creating a vector store instance
EmbeddingStore<TextSegment> embeddingStore = ScalarDbEmbeddingStoreFactory
    .create(scalarDbConfig)
    .embeddingStore("my_vector_store");

// Adding embeddings
embeddingStore.add(embedding, textSegment);

// Searching for similar vectors
List<EmbeddingMatch<TextSegment>> matches = embeddingStore
    .findRelevant(queryEmbedding, maxResults);
```

### Migration Relevance

| Source Database Feature | Vector Search Opportunity |
|------------------------|--------------------------|
| Full-text search (Oracle Text, PostgreSQL tsvector) | Replace with semantic vector search |
| BLOB columns with documents | Extract text → generate embeddings |
| Product catalogs | Enable similarity-based recommendations |
| Log/event data | Semantic log analysis |

### When to Consider Vector Search

| Scenario | Recommendation |
|----------|----------------|
| Replacing keyword-based search | ✅ Strong candidate for vector search |
| Building AI/ML features | ✅ Native integration available |
| Simple text matching | ⚠️ May be overkill, consider LIKE queries |
| Exact lookups only | ❌ Not needed, use standard queries |

---

## 13. Object Storage as ScalarDB Backend

> **Status**: Object Storage support is currently in **Private Preview** (ScalarDB 3.17+). Contact Scalar Labs for access.

### Overview

ScalarDB supports cloud object storage (Amazon S3, Azure Blob Storage, Google Cloud Storage) as a **storage backend**. This means you use the **same ScalarDB API** (Get, Put, Scan) - the storage layer is abstracted away through configuration.

**Key Insight**: Object storage is NOT a separate integration - it's configured as the backend, and your application code uses standard ScalarDB operations.

### Supported Providers

| Provider | `scalar.db.storage` Value | Reference |
|----------|--------------------------|-----------|
| **Amazon S3** | `s3` | [S3 Configuration](https://scalardb.scalar-labs.com/docs/latest/configurations/?databases=S3#storage-related-configurations) |
| **Azure Blob Storage** | `blob-storage` | [Azure Configuration](https://scalardb.scalar-labs.com/docs/latest/configurations/?databases=Blob_Storage#storage-related-configurations) |
| **Google Cloud Storage** | `cloud-storage` | [GCS Configuration](https://scalardb.scalar-labs.com/docs/latest/configurations/?databases=Cloud_Storage#storage-related-configurations) |

### Required Permissions

| Provider | Required Permissions/Roles |
|----------|---------------------------|
| **Amazon S3** | `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`, `s3:ListBucket` |
| **Azure Blob Storage** | Access key with full access to Azure Blob Storage |
| **Google Cloud Storage** | `roles/storage.objectAdmin` (Storage Object Admin) |

### Configuration: Amazon S3

```properties
# scalardb.properties for S3 backend
scalar.db.storage=s3
scalar.db.contact_points=<REGION>/<BUCKET_NAME>
scalar.db.username=<AWS_ACCESS_KEY>
scalar.db.password=<AWS_SECRET_KEY>

# Optional performance tuning
scalar.db.s3.multipart_upload_part_size_bytes=<SIZE>
scalar.db.s3.multipart_upload_max_concurrency=<CONCURRENCY>
scalar.db.s3.multipart_upload_threshold_size_bytes=<THRESHOLD>
scalar.db.s3.request_timeout_secs=<TIMEOUT>
```

**Example:**
```properties
scalar.db.storage=s3
scalar.db.contact_points=us-east-1/my-scalardb-bucket
scalar.db.username=AKIAIOSFODNN7EXAMPLE
scalar.db.password=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

### Configuration: Azure Blob Storage

```properties
# scalardb.properties for Azure Blob Storage backend
scalar.db.storage=blob-storage
scalar.db.contact_points=https://<ACCOUNT_NAME>.blob.core.windows.net/<CONTAINER_NAME>
scalar.db.username=<ACCOUNT_NAME>
scalar.db.password=<ACCOUNT_KEY>

# Optional performance tuning
scalar.db.blob_storage.parallel_upload_block_size_bytes=<SIZE>
scalar.db.blob_storage.parallel_upload_max_concurrency=<CONCURRENCY>
scalar.db.blob_storage.parallel_upload_threshold_size_bytes=<THRESHOLD>
scalar.db.blob_storage.request_timeout_secs=<TIMEOUT>
```

**Example:**
```properties
scalar.db.storage=blob-storage
scalar.db.contact_points=https://mystorageaccount.blob.core.windows.net/my-container
scalar.db.username=mystorageaccount
scalar.db.password=<base64-encoded-account-key>
```

### Configuration: Google Cloud Storage

```properties
# scalardb.properties for GCS backend
scalar.db.storage=cloud-storage
scalar.db.contact_points=<BUCKET_NAME>
scalar.db.username=<PROJECT_ID>
scalar.db.password=<SERVICE_ACCOUNT_KEY_JSON>

# Optional performance tuning
scalar.db.cloud_storage.upload_chunk_size_bytes=<SIZE>
```

**Example:**
```properties
scalar.db.storage=cloud-storage
scalar.db.contact_points=my-gcs-bucket
scalar.db.username=my-gcp-project-id
scalar.db.password={"type":"service_account","project_id":"...","private_key":"..."}
```

### Application Code Pattern

**Important**: Your application code remains the **same** regardless of backend. ScalarDB abstracts the storage layer:

```java
// Same ScalarDB API for all backends (relational, NoSQL, or Object Storage)
DistributedStorage storage = new DistributedStorageFactory().create(config);

// Put operation - works identically on S3, Azure Blob, GCS, or traditional DB
Put put = Put.newBuilder()
    .namespace("my_namespace")
    .table("my_table")
    .partitionKey(Key.ofText("pk", "document-123"))
    .textValue("content", documentContent)
    .blobValue("file_data", fileBytes)  // Binary data
    .build();
storage.put(put);

// Get operation
Get get = Get.newBuilder()
    .namespace("my_namespace")
    .table("my_table")
    .partitionKey(Key.ofText("pk", "document-123"))
    .build();
Optional<Result> result = storage.get(get);

// Scan operation
Scan scan = Scan.newBuilder()
    .namespace("my_namespace")
    .table("my_table")
    .all()
    .build();
List<Result> results = storage.scan(scan);
```

### Limitations

| Limitation | Details |
|------------|---------|
| **BLOB Size** | Maximum 1.5 GiB per object |
| **Private Preview** | Contact Scalar Labs for access |
| **Use Cases** | Best for file/document storage scenarios |

### Migration Use Cases

| Source Database Scenario | Object Storage Benefit |
|-------------------------|----------------------|
| Files stored in BLOB columns | Cost-effective, scalable storage |
| Large document management | Native cloud storage integration |
| Archive data | Cold storage tier support |
| Distributed file access | CDN-friendly object URLs |

### When to Use Object Storage Backend

| Scenario | Recommended Backend |
|----------|-------------------|
| Transactional data with files | Relational DB (PostgreSQL/Oracle) + Object Storage for files |
| Document-heavy workloads | Object Storage as primary |
| Archival/backup data | Object Storage |
| High-performance OLTP | Relational or NoSQL backends |

---

## 14. Java Requirements

| Component | Java Versions |
|-----------|---------------|
| ScalarDB Core | Oracle JDK or OpenJDK 8, 11, 17, 21 (LTS) |
| ScalarDB Cluster | Oracle JDK or OpenJDK 8, 11, 17, 21 (LTS) |
| ScalarDB Analytics (Spark) | Oracle JDK or OpenJDK 8, 11, 17 (LTS) |
| ScalarDB Analytics CLI | Oracle JDK or OpenJDK 8, 11, 17, 21 (LTS) |

---

## 15. Quick Reference: Migration Complexity

### Low Complexity (Direct Migration)

- Tables with NUMBER, VARCHAR2, DATE, TIMESTAMP columns
- Simple primary keys
- Basic indexes
- Simple CRUD queries
- Queries with GROUP BY and aggregations (v3.17+)

### Medium Complexity (Requires Adjustment)

- Tables with CLOB/BLOB columns
- Composite primary keys
- Foreign key relationships
- Check constraints
- Queries with JOINs

### High Complexity (Significant Rework)

- Tables using object types
- Nested tables and collections
- Heavy use of PL/SQL
- Triggers for business logic
- Materialized views for performance
- Sequences for ID generation
- Queries with subqueries or window functions

---

*Reference compiled from ScalarDB official documentation (version 3.17)*
