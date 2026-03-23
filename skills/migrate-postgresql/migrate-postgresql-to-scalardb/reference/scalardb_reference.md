# ScalarDB Reference Documentation

This file contains comprehensive reference information for ScalarDB migration, compiled from official documentation.

---

## MANDATORY REFERENCES FOR MIGRATION

The following references MUST be consulted during PostgreSQL → ScalarDB migration:

### Primary Migration Path: ScalarDB SQL

| Reference | URL | When to Use |
|-----------|-----|-------------|
| **ScalarDB Cluster SQL (JDBC) Getting Started** | https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/getting-started-with-scalardb-cluster-sql-jdbc/ | Initial JDBC setup |
| **ScalarDB SQL Grammar Reference** | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/grammar/ | Query syntax, DDL, DML |
| **ScalarDB SQL Migration Guide** | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/migration-guide | Step-by-step migration |

### Schema and Data Type References

| Reference | URL | When to Use |
|-----------|-----|-------------|
| **Schema Loader Data Type Mapping** | https://scalardb.scalar-labs.com/docs/latest/schema-loader/#data-type-mapping-between-scalardb-and-other-databases | Type conversion |
| **Schema Loader Import** | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import | Importing existing tables |
| **Decoupling Transaction Metadata** | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import/#decoupling-transaction-metadata | **RECOMMENDED** for migration |
| **JDBC Data Type Mapping** | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import#data-type-mapping-from-jdbc-databases-to-scalardb | PostgreSQL → ScalarDB types |

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

## 4. Data Type Mapping: PostgreSQL to ScalarDB (Import) - OFFICIAL

> **Reference**: https://scalardb.scalar-labs.com/docs/latest/schema-loader-import#data-type-mapping-from-jdbc-databases-to-scalardb

> ⚠️ **CRITICAL**: Only the data types listed below are officially supported. **Data types NOT listed in the official documentation are NOT SUPPORTED.** This includes any PostgreSQL extensions, custom types, or unlisted built-in types.

### Supported PostgreSQL/YugabyteDB/AlloyDB Data Types (ONLY THESE 14 TYPES)

| PostgreSQL Type | ScalarDB Type | Notes |
|-----------------|---------------|-------|
| bigint | BIGINT | ⚠️ See Warning 1 below |
| boolean | BOOLEAN | Direct mapping |
| bytea | BLOB | Max ~2GB (2^31-1 bytes) |
| character | TEXT | ⚠️ See Warning 2 below |
| character varying | TEXT | ⚠️ See Warning 2 below |
| date | DATE | Direct mapping |
| double precision | DOUBLE | Direct mapping |
| integer | INT | Direct mapping |
| real | FLOAT | Direct mapping |
| smallint | INT | ⚠️ See Warning 2 below |
| text | TEXT | Direct mapping |
| time | TIME | Without timezone only |
| timestamp | TIMESTAMP | Direct mapping |
| timestamp with time zone | TIMESTAMPTZ | Direct mapping |

### NOT Supported Data Types (Official List)

> **Data types not listed above are NOT SUPPORTED.** The following are common data types that are explicitly NOT supported:

| Category | Unsupported Types |
|----------|-------------------|
| **Serial/Sequence** | bigserial, serial, smallserial |
| **Numeric** | numeric, money |
| **Binary** | bit |
| **Date/Time** | interval, time with time zone |
| **JSON** | json, jsonb |
| **UUID** | uuid |
| **XML** | xml |
| **Network** | inet, cidr, macaddr, macaddr8 |
| **Geometric** | point, line, lseg, box, path, polygon, circle |
| **Text Search** | tsvector, tsquery |
| **System** | pg_lsn, pg_snapshot, txid_snapshot |
| **Arrays** | All array types (e.g., integer[], text[]) |
| **Range Types** | All range types (e.g., int4range, daterange) |
| **ENUM Types** | User-defined ENUM types |
| **Composite Types** | User-defined composite types |
| **Domain Types** | User-defined domain types |
| **Extension Types** | PostGIS (geometry, geography), hstore, ltree, citext, etc. |
| **Any Other Types** | Any PostgreSQL type not in the 14 supported types above |

### Critical Warnings (Official Documentation)

> ⚠️ **Warning 1 - BIGINT Range**: The value range of BIGINT in ScalarDB is from **-2^53 to 2^53**, regardless of the size of bigint in the underlying database. Thus, if data outside this range exists in the imported table, ScalarDB cannot read it.

> ⚠️ **Warning 2 - Size Mapping**: For certain data types noted above (character, character varying, smallint), ScalarDB may map a data type larger than that of the underlying database. In that case, you will see errors when putting a value with a size larger than the size specified in the underlying database.

> ⚠️ **Warning 3 - BLOB Size**: The maximum size of BLOB in ScalarDB is about 2GB (precisely 2^31-1 bytes).

### Override Column Types

The underlying storage type can be mapped to several ScalarDB data types. To override the default mapping, use the `override-columns-type` field in the import schema file:

```json
{
  "namespace.table_name": {
    "transaction": true,
    "override-columns-type": {
      "special_column": "TEXT"
    }
  }
}
```

### Migration Strategies for Unsupported Types

| Unsupported Type | Migration Strategy |
|------------------|-------------------|
| serial/bigserial | Use UUID or application-level ID generation |
| numeric | Convert to DOUBLE (precision loss) or store as TEXT |
| json/jsonb | Store as TEXT, parse in application |
| uuid | Store as TEXT (36 characters) |
| inet/cidr/macaddr | Store as TEXT |
| Arrays | Normalize to separate child table |
| Range types | Store as two boundary columns |
| ENUM | Store as TEXT + application validation |
| Composite types | Flatten to individual columns |
| tsvector/tsquery | Use ScalarDB Vector Search or external search |
| Geometric types | Store coordinates as separate columns |

---

## 5. Value Range Limitations

### Critical Limitations

| ScalarDB Type | Range/Limit | PostgreSQL Comparison | Migration Impact |
|---------------|-------------|----------------------|------------------|
| BIGINT | -2^53 to 2^53 | BIGINT: -2^63 to 2^63-1 | Data validation required |
| BLOB | ~2GB (2^31-1 bytes) | BYTEA: 1GB | Usually compatible |
| DATE | 1000-01-01 to 9999-12-31 | 4713 BC to 5874897 AD | Historical dates may fail |
| TIME | 00:00:00.000000 to 23:59:59.999999 | 00:00:00 to 24:00:00 | Microsecond precision |
| TIMESTAMP | Millisecond precision | Microsecond precision | Precision loss possible |

### Database-Specific Restrictions

| Database | Restriction |
|----------|-------------|
| PostgreSQL | BYTEA (BLOB) cannot be used in WHERE clause conditions |
| PostgreSQL | BLOB cannot be partition key, clustering key, or secondary index key |
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
| CTEs (WITH clause) | Convert to subqueries or application logic |
| Recursive CTEs | Implement in application code |
| RETURNING clause | SELECT after INSERT/UPDATE |
| ON CONFLICT (UPSERT) | Check existence first, then INSERT or UPDATE |

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

> **IMPORTANT**: ScalarDB SQL interface requires ScalarDB Cluster. The SQL JDBC connection is NOT available with ScalarDB Core alone.

| Component | Use For | SQL Support |
|-----------|---------|-------------|
| **ScalarDB Core** | Schema Loader, Core API (Get/Put/Scan) | NO |
| **ScalarDB Cluster** | Application SQL access via JDBC | YES |

**References**:
- https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/getting-started-with-scalardb-cluster-sql-jdbc/
- https://github.com/scalar-labs/scalardb-samples/tree/main/scalardb-sql-jdbc-sample

---

## 10. Configuration Examples

### ScalarDB Core Configuration (for Schema Loader)

Use this configuration with `scalardb-schema-loader` for schema creation and data import:

```properties
# scalardb.properties (for Schema Loader - Core only)
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:postgresql://localhost:5432/mydb
scalar.db.username=scalardb_user
scalar.db.password=scalardb_password

# Transaction settings
scalar.db.consensus_commit.isolation_level=SERIALIZABLE
scalar.db.consensus_commit.serializable_strategy=EXTRA_READ
```

### ScalarDB Cluster Configuration (for SQL Access)

First, deploy ScalarDB Cluster, then configure the SQL client:

**Application SQL Client Configuration** (`scalardb-sql.properties`):
```properties
scalar.db.sql.connection_mode=cluster
scalar.db.sql.cluster_mode.contact_points=indirect:localhost
```

**Java JDBC Connection:**
```java
private Connection getConnection() throws SQLException {
    Connection connection = DriverManager.getConnection("jdbc:scalardb:scalardb-sql.properties");
    connection.setAutoCommit(false);
    return connection;
}
```

**Reference**: https://github.com/scalar-labs/scalardb-samples/tree/main/scalardb-sql-jdbc-sample

---

## 11. Unsupported PostgreSQL Features

### PL/pgSQL Features

| Feature | Status | Workaround |
|---------|--------|------------|
| Stored Procedures | NOT SUPPORTED | Convert to application methods |
| Functions | NOT SUPPORTED | Convert to application methods |
| Triggers | NOT SUPPORTED | Application-level event handling |
| Event Triggers | NOT SUPPORTED | Application-level monitoring |
| Aggregate Functions (custom) | NOT SUPPORTED | Application-level aggregation |
| Operators (custom) | NOT SUPPORTED | Application-level logic |

### PostgreSQL-Specific Features

| Feature | Status | Workaround |
|---------|--------|------------|
| Sequences | NOT SUPPORTED | UUID or app-level ID generator |
| SERIAL/BIGSERIAL | NOT SUPPORTED | UUID or app-level ID generator |
| IDENTITY columns | NOT SUPPORTED | UUID or app-level ID generator |
| Materialized Views | NOT SUPPORTED | App-level caching |
| Views | PARTIAL | Import as table or implement as query |
| Table Inheritance | NOT SUPPORTED | Flatten to separate tables |
| Partitioning | PARTIAL | Handled by underlying DB |
| Row Level Security | NOT SUPPORTED | App-level security |
| Rules | NOT SUPPORTED | Convert to application logic |
| Foreign Data Wrappers | NOT SUPPORTED | Import data first |
| Generated Columns | NOT SUPPORTED | Compute in application |
| Full-Text Search (tsvector) | NOT SUPPORTED | ScalarDB Vector Search or Elasticsearch |
| JSONB Operators | NOT SUPPORTED | App-level JSON parsing |

### Data Types

| Feature | Status | Workaround |
|---------|--------|------------|
| ENUM Types | NOT SUPPORTED | TEXT + app validation |
| Array Types | NOT SUPPORTED | Normalize to child table |
| Range Types | NOT SUPPORTED | Two boundary columns |
| Composite Types | NOT SUPPORTED | Flatten to columns |
| Domain Types | NOT SUPPORTED | Base type + app validation |
| Geometric Types | NOT SUPPORTED | Custom solution needed |
| Network Types (INET, CIDR) | NOT SUPPORTED | Store as TEXT |
| XML Type | NOT SUPPORTED | Store as TEXT |

---

## 12. ScalarDB Analytics (Separate Component)

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
| CTEs | ❌ | ✅ Use |

**Note**: Analytics CLI is NOT required for basic schema migration. It's used for complex analytical workloads.

---

## 13. Vector Search (AI/ML Capabilities)

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

### Migration Relevance

| Source Database Feature | Vector Search Opportunity |
|------------------------|--------------------------|
| Full-text search (PostgreSQL tsvector) | Replace with semantic vector search |
| BYTEA columns with documents | Extract text → generate embeddings |
| Product catalogs | Enable similarity-based recommendations |
| Log/event data | Semantic log analysis |

---

## 14. Object Storage as ScalarDB Backend

> **Status**: Object Storage support is currently in **Private Preview** (ScalarDB 3.17+). Contact Scalar Labs for access.

### Overview

ScalarDB supports cloud object storage (Amazon S3, Azure Blob Storage, Google Cloud Storage) as a **storage backend**. This means you use the **same ScalarDB API** (Get, Put, Scan) - the storage layer is abstracted away through configuration.

### Supported Providers

| Provider | `scalar.db.storage` Value | Reference |
|----------|--------------------------|-----------|
| **Amazon S3** | `s3` | [S3 Configuration](https://scalardb.scalar-labs.com/docs/latest/configurations/?databases=S3#storage-related-configurations) |
| **Azure Blob Storage** | `blob-storage` | [Azure Configuration](https://scalardb.scalar-labs.com/docs/latest/configurations/?databases=Blob_Storage#storage-related-configurations) |
| **Google Cloud Storage** | `cloud-storage` | [GCS Configuration](https://scalardb.scalar-labs.com/docs/latest/configurations/?databases=Cloud_Storage#storage-related-configurations) |

### Limitations

| Limitation | Details |
|------------|---------|
| **BLOB Size** | Maximum 1.5 GiB per object |
| **Private Preview** | Contact Scalar Labs for access |
| **Use Cases** | Best for file/document storage scenarios |

---

## 15. Java Requirements

| Component | Java Versions |
|-----------|---------------|
| ScalarDB Core | Oracle JDK or OpenJDK 8, 11, 17, 21 (LTS) |
| ScalarDB Cluster | Oracle JDK or OpenJDK 8, 11, 17, 21 (LTS) |
| ScalarDB Analytics (Spark) | Oracle JDK or OpenJDK 8, 11, 17 (LTS) |
| ScalarDB Analytics CLI | Oracle JDK or OpenJDK 8, 11, 17, 21 (LTS) |

---

## 16. Quick Reference: Migration Complexity

### Low Complexity (Direct Migration)

- Tables with INTEGER, VARCHAR, BOOLEAN, TIMESTAMP columns
- Simple primary keys
- Basic indexes
- Simple CRUD queries
- Queries with GROUP BY and aggregations (v3.17+)

### Medium Complexity (Requires Adjustment)

- Tables with BYTEA columns
- Composite primary keys
- Foreign key relationships
- Check constraints
- Queries with JOINs
- JSON/JSONB columns (store as TEXT)

### High Complexity (Significant Rework)

- Tables using ENUM types
- Array columns
- Heavy use of PL/pgSQL
- Triggers for business logic
- Materialized views for performance
- Sequences/SERIAL for ID generation
- Queries with subqueries, CTEs, or window functions
- Table inheritance
- Row Level Security policies
- Full-text search (tsvector/tsquery)

---

*Reference compiled from ScalarDB official documentation (version 3.17)*
