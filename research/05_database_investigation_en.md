# Database Investigation

## What is ScalarDB

ScalarDB is a **Universal HTAP (Hybrid Transactional/Analytical Processing) Engine** developed by Scalar, Inc. It operates as middleware on top of diverse databases, enabling cross-database ACID transactions and real-time analytics using the **Consensus Commit** protocol. The latest version is **3.17**.

ScalarDB consists of a storage abstraction layer and a storage-agnostic universal transaction manager, connecting to diverse backends through storage adapters specific to each database.

---

## 1. RDBMS

ScalarDB broadly supports JDBC-compatible relational databases. They are used by specifying the storage type as `scalar.db.storage=jdbc`.

### Official Support List

| Database | Supported Versions | Support Category |
|---|---|---|
| **PostgreSQL** | 17, 16, 15, 14, 13 | Officially supported |
| **MySQL** | 8.4, 8.0 | Officially supported |
| **Oracle Database** | 23ai, 21c, 19c | Officially supported |
| **Microsoft SQL Server** | 2022, 2019, 2017 | Officially supported |
| **MariaDB** | 11.4, 10.11 | Officially supported |
| **IBM Db2** | 12.1, 11.5 (Linux/UNIX/Windows only. z/OS not supported) | Officially supported |
| **SQLite** | 3 | Officially supported |
| **Amazon Aurora MySQL** | 3, 2 | Officially supported |
| **Amazon Aurora PostgreSQL** | 17, 16, 15, 14, 13 | Officially supported |
| **Google AlloyDB** | 16, 15 | Officially supported as PostgreSQL-compatible DB (using PostgreSQL JDBC driver) |
| **TiDB** | 8.5, 7.5, 6.5 | Compatible DB (using MySQL Connector/J) |
| **YugabyteDB** | 2 | Compatible DB (using PostgreSQL JDBC driver) |

### Characteristics of Each Database

#### PostgreSQL

- **Features**: High-functionality open-source RDBMS. Highly extensible with rich features including JSON/GIS/full-text search
- **Strengths**: High SQL standard compliance, rich extensions (pgvector, etc.), active community
- **Weaknesses**: May be inferior to MySQL for large-scale write workloads
- **Use cases**: General-purpose OLTP, geospatial data, systems requiring complex queries
- **Affinity with ScalarDB**: **Very high**. Also supported as an external data source in ScalarDB Analytics. Can be used as a vector search backend through pgvector integration

#### MySQL

- **Features**: The world's most widely used open-source RDBMS
- **Strengths**: High read performance, abundant hosting options, rich ecosystem
- **Weaknesses**: Lower SQL standard compliance than PostgreSQL, limited stored procedure functionality
- **Use cases**: Web applications, CMS, e-commerce sites
- **Affinity with ScalarDB**: **Very high**. Also supported as an external data source in ScalarDB Analytics

#### Oracle Database

- **Features**: Leading enterprise commercial RDBMS
- **Strengths**: High performance and reliability, advanced features (partitioning, RAC, etc.), strong support
- **Weaknesses**: High license costs, complex pricing structure
- **Use cases**: Core business systems, financial systems, large enterprises
- **Affinity with ScalarDB**: **High**. Also supported as an external data source in ScalarDB Analytics

#### Microsoft SQL Server

- **Features**: Microsoft's enterprise RDBMS
- **Strengths**: Integration with Windows/.NET environments, BI features (SSRS/SSIS/SSAS), Azure integration
- **Weaknesses**: Some feature limitations on Linux, license costs
- **Use cases**: Microsoft-centric enterprise environments, BI systems
- **Affinity with ScalarDB**: **High**. Also supported as an external data source in ScalarDB Analytics

#### MariaDB

- **Features**: Open-source RDBMS forked from MySQL
- **Strengths**: High compatibility with MySQL, additional features (Aria/TokuDB storage engines, etc.), truly open source
- **Weaknesses**: Divergence in compatibility with MySQL 8.0 and later
- **Use cases**: MySQL alternative, web applications
- **Affinity with ScalarDB**: **High**

#### IBM Db2

- **Features**: IBM's traditional enterprise RDBMS
- **Strengths**: Affinity with mainframes, AI integration (Watson integration), high reliability
- **Weaknesses**: Learning curve, z/OS version not supported by ScalarDB
- **Use cases**: Existing core systems in banking and insurance
- **Affinity with ScalarDB**: **High**. Only Linux/UNIX/Windows versions supported

#### SQLite

- **Features**: Lightweight embedded RDBMS
- **Strengths**: No server required, zero configuration, ideal for embedded use
- **Weaknesses**: Limited concurrent write performance, not suitable for large-scale data
- **Use cases**: Development/testing environments, lightweight applications

---

## 2. NoSQL

ScalarDB's NoSQL support is achieved through dedicated storage adapters.

### Official Support List

| Database | Supported Versions | Storage Setting | Support Category |
|---|---|---|---|
| **Amazon DynamoDB** | Latest | `scalar.db.storage=dynamo` | Officially supported (dedicated adapter) |
| **Azure Cosmos DB for NoSQL** | Latest | `scalar.db.storage=cosmos` | Officially supported (dedicated adapter) |
| **Apache Cassandra** | 5.0, 4.1, 3.11, 3.0 | `scalar.db.storage=cassandra` | Officially supported (dedicated adapter) |

### Characteristics of Each Database

#### Amazon DynamoDB

- **Data model**: Key-value / document
- **Features**: AWS fully managed, serverless, auto-scaling
- **Scalability**: Virtually unlimited scaling (On-Demand mode)
- **Latency**: Consistent single-digit millisecond performance
- **Availability**: 99.999% SLA (with Global Tables)
- **CAP theorem**: **AP type** (eventual consistency by default, strong consistency option available)
- **Affinity with ScalarDB**: **Very high**. Directly supported with dedicated adapter. Also supported as an external data source in ScalarDB Analytics
- **Use cases**: High-throughput web apps, session management, IoT data

#### Azure Cosmos DB for NoSQL

- **Data model**: Multi-model (document, key-value, graph, column family)
- **Features**: Globally distributed, multiple consistency levels selectable
- **Scalability**: Auto-scaling at global level
- **Latency**: Less than 10 milliseconds at 99th percentile
- **Availability**: 99.999% SLA (multi-region)
- **CAP theorem**: **Variable** (5 consistency levels: Strong, Bounded Staleness, Session, Consistent Prefix, Eventual)
- **Affinity with ScalarDB**: **Very high**. Directly supported with dedicated adapter. Also usable as a vector search backend
- **Use cases**: Globally distributed apps, when multi-model is needed

#### Apache Cassandra

- **Data model**: Wide-column
- **Features**: High availability, linear scalability, masterless architecture
- **Scalability**: Linear scaling by adding nodes
- **Throughput**: Proportional to node count
- **Availability**: No single point of failure due to masterless design
- **CAP theorem**: **AP type** (consistency level is Tunable Consistency)
- **Affinity with ScalarDB**: **Very high**. A major backend supported since ScalarDB's early days. By operating the Coordinator table with replication factor 3, Paxos Commit-equivalent highly available transaction coordination is possible
- **Use cases**: High-volume writes, time-series data, IoT

### Unsupported NoSQL

- **Apache HBase**: Not included in the official support list in the latest version (3.17)
- **MongoDB**: Not supported
- **Google Cloud Bigtable**: Not supported

---

## 3. Object Storage

Object storage support was newly added as **Private Preview** in ScalarDB 3.17.

| Storage | Status | Required Permissions/Roles |
|---|---|---|
| **Amazon S3** | Private Preview | `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`, `s3:ListBucket` |
| **Azure Blob Storage** | Private Preview | Full access key authentication |
| **Google Cloud Storage** | Private Preview | `Storage Object Admin (roles/storage.objectAdmin)` |

### Data Lake Usage Patterns

ScalarDB Analytics enables data lake-like usage through the Apache Spark plugin.

- **ScalarDB Analytics** manages diverse data sources as a unified catalog and can execute cross-database analytical queries through Spark
- Integration with **Databricks** and **Snowflake** is also supported as external analytics platforms
- Direct data persistence to object storage is at the Private Preview stage, and further feature maturity is needed for full-scale data lake construction

---

## 4. Vector Index (Vector Search)

ScalarDB Cluster provides a **vector store abstraction layer**, internally leveraging LangChain4j. It is currently at **Private Preview** status.

### Supported Vector Stores (Embedding Store)

| Vector Store | Description | Use Case |
|---|---|---|
| **pgvector** (PostgreSQL extension) | PostgreSQL-based vector similarity search | Vector search in PostgreSQL environments |
| **OpenSearch** | Supports local cluster/AWS managed service | Large-scale vector search |
| **Azure Cosmos DB for NoSQL** | Azure-native vector search | Vector search in Azure environments |
| **Azure AI Search** | Leverages Azure's search service | Advanced search in Azure environments |
| **In-Memory** | Basic in-memory implementation | Prototyping purposes |

### Supported Embedding Models

| Model | Provider | Description |
|---|---|---|
| **In-Process (ONNX Runtime)** | Local execution | Runs within the ScalarDB Cluster process |
| **Amazon Bedrock** | AWS | Titan models, etc. |
| **Azure OpenAI** | Microsoft | OpenAI model usage via Azure |
| **Google Vertex AI** | GCP | Google Cloud's AI platform |
| **OpenAI** | OpenAI | Direct connection to OpenAI API |

### Integration with AI/ML Use Cases

- **RAG (Retrieval-Augmented Generation)**: By combining ScalarDB Cluster's database abstraction and vector store abstraction, the entire process of data extraction -> vectorization -> vector storage -> search can be implemented in a unified manner
- Multiple named instances can be configured, allowing switching between vector stores and embedding models based on use case
- Configuration is enabled with `scalar.db.embedding.enabled=true`, and instances are defined with `scalar.db.embedding.stores` and `scalar.db.embedding.models`

### Unsupported Dedicated Vector Databases

Dedicated vector databases such as Pinecone, Weaviate, Milvus, Chroma, and Qdrant are not currently included in ScalarDB's official support. However, since the design is based on LangChain4j, there is room for future expansion.

---

## 5. Search Index

### OpenSearch

- **OpenSearch is supported** as a vector store backend for ScalarDB Cluster
- Supports both local clusters and **AWS OpenSearch Service**
- Configuration items: Server URL, API key, username, password, index name
- Use: Used as a backend for vector similarity search (as an Embedding Store)

### Elasticsearch

- Not currently included in ScalarDB's official support
- OpenSearch is a project forked from Elasticsearch, but ScalarDB explicitly supports only OpenSearch

---

## 6. Cloud-Specific Support Status

### AWS

| Service | Type | ScalarDB Support | Notes |
|---|---|---|---|
| **Amazon Aurora MySQL** | Managed RDBMS | **Officially supported** | v3, v2 |
| **Amazon Aurora PostgreSQL** | Managed RDBMS | **Officially supported** | v17, 16, 15, 14, 13 |
| **Amazon RDS (MySQL/PostgreSQL, etc.)** | Managed RDBMS | Available via JDBC | Uses the same driver as the base DB |
| **Amazon DynamoDB** | NoSQL | **Officially supported (dedicated adapter)** | |
| **Amazon S3** | Object storage | **Private Preview** | v3.17~ |
| **Amazon EKS** | Kubernetes | **Officially supported** (deployment target) | |
| **AWS OpenSearch Service** | Search/vector | **Officially supported** (Embedding Store) | |
| **Amazon Bedrock** | AI/ML | **Officially supported** (Embedding model) | |
| **Databricks on AWS** | Analytics | **Officially supported** (Analytics integration) | |

### Azure

| Service | Type | ScalarDB Support | Notes |
|---|---|---|---|
| **Azure Cosmos DB for NoSQL** | NoSQL | **Officially supported (dedicated adapter)** | Transaction + vector search |
| **Azure SQL Database** | Managed RDBMS | Available via JDBC | Uses SQL Server driver |
| **Azure Database for MySQL** | Managed RDBMS | Available via JDBC | Uses MySQL driver |
| **Azure Database for PostgreSQL** | Managed RDBMS | Available via JDBC | Uses PostgreSQL driver |
| **Azure Blob Storage** | Object storage | **Private Preview** | v3.17~ |
| **Azure AKS** | Kubernetes | **Officially supported** (deployment target) | |
| **Azure AI Search** | Search/vector | **Officially supported** (Embedding Store) | |
| **Azure OpenAI** | AI/ML | **Officially supported** (Embedding model) | |

### GCP

| Service | Type | ScalarDB Support | Notes |
|---|---|---|---|
| **Google AlloyDB** | Managed RDBMS | **Officially supported as PostgreSQL-compatible DB** | v16, v15 (using PostgreSQL JDBC driver) |
| **Google Cloud SQL (MySQL/PostgreSQL)** | Managed RDBMS | Available via JDBC | Uses respective DB drivers |
| **Google Cloud Storage** | Object storage | **Private Preview** | v3.17~ |
| **Google Vertex AI** | AI/ML | **Officially supported** (Embedding model) | |
| **Cloud Spanner** | NewSQL | **Not supported** | |
| **Cloud Bigtable** | NoSQL | **Not supported** | |

### On-Premises

| Database | Type | ScalarDB Support | Notes |
|---|---|---|---|
| **PostgreSQL** | RDBMS | **Officially supported** | |
| **MySQL** | RDBMS | **Officially supported** | |
| **Oracle Database** | RDBMS | **Officially supported** | |
| **SQL Server** | RDBMS | **Officially supported** | |
| **MariaDB** | RDBMS | **Officially supported** | |
| **IBM Db2** | RDBMS | **Officially supported** | Linux/UNIX/Windows only |
| **SQLite** | RDBMS | **Officially supported** | Development/testing purposes |
| **Apache Cassandra** | NoSQL | **Officially supported** | |
| **YugabyteDB** | NewSQL | **Compatible support** | Uses PostgreSQL driver |
| **TiDB** | NewSQL | **Compatible support** | Uses MySQL driver |
| **OpenSearch** | Search/vector | **Officially supported** (Embedding Store) | |

---

## 7. Tier Ranking for Database Selection

### Tier 1: Highest Affinity (Dedicated Adapter / Full Official Support)

| Database | Reason |
|---|---|
| **Apache Cassandra** | Major backend since ScalarDB's early days. Has dedicated adapter |
| **Amazon DynamoDB** | Dedicated adapter (dynamo). High scalability |
| **Azure Cosmos DB for NoSQL** | Dedicated adapter (cosmos) + vector store support |
| **PostgreSQL / MySQL** | JDBC adapter + Analytics support + pgvector integration |
| **Amazon Aurora (MySQL/PostgreSQL)** | Officially tested managed service |

### Tier 2: Officially Supported (via JDBC)

> **Note**: The tier classification in this document is an independent classification based on adapter type. Tier 1 includes databases with dedicated adapters, and Tier 2 includes databases via JDBC adapters. Oracle and SQL Server are via JDBC but are officially supported databases by ScalarDB, and their use in production environments is fully supported.

| Database | Reason |
|---|---|
| **Oracle Database** | Via JDBC adapter, officially tested. Analytics supported |
| **SQL Server** | Via JDBC adapter, officially tested. Analytics supported |
| **MariaDB** | Via JDBC adapter, officially tested |
| **IBM Db2** | Via JDBC adapter, officially tested |
| **Google AlloyDB** | Listed officially as compatible DB. Uses PostgreSQL driver |
| **TiDB** | Listed officially as compatible DB. Uses MySQL driver |
| **YugabyteDB** | Listed officially as compatible DB. Uses PostgreSQL driver |

### Tier 3: New Features (Private Preview)

| Database/Service | Reason |
|---|---|
| **Amazon S3** | Object storage (v3.17~) |
| **Azure Blob Storage** | Object storage (v3.17~) |
| **Google Cloud Storage** | Object storage (v3.17~) |
| **pgvector / OpenSearch / Azure AI Search / Cosmos DB** | Vector search backend (Private Preview) |

### Tier 4: Indirect Integration Only / Not Supported

| Database/Service | Status |
|---|---|
| **Elasticsearch** | No direct support (OpenSearch only) |
| **Pinecone, Weaviate, Milvus, Chroma** | Not supported |
| **Google Cloud Spanner** | Not supported |
| **Google Cloud Bigtable** | Not supported |
| **Apache HBase** | Not supported in latest version |
| **MongoDB** | Not supported |

---

## 8. Database Characteristics Comparison

### RDBMS Comparison

| Metric | PostgreSQL | MySQL | Oracle | SQL Server | MariaDB | Db2 |
|---|---|---|---|---|---|---|
| **Throughput** | High | High (read-optimized) | Very high | High | High | High |
| **Latency** | Low | Very low | Low | Low | Very low | Low |
| **Scalability** | Medium to high | Medium to high | Very high | High | Medium to high | High |
| **Availability** | High (replication) | High | Very high (RAC) | High (Always On) | High | Very high |
| **Cost** | Free (OSS) | Free (OSS) | High (commercial) | Medium to high (commercial) | Free (OSS) | Medium to high (commercial) |
| **ScalarDB Affinity** | Very high | Very high | High | High | High | High |

### NoSQL Comparison

| Metric | DynamoDB | Cosmos DB | Cassandra |
|---|---|---|---|
| **Throughput** | Very high (automatic) | Very high (RU-controlled) | Very high (linear scaling) |
| **Latency** | Single-digit ms | Under 10ms (99th percentile) | Low (configuration-dependent) |
| **Scalability** | Virtually unlimited | Global automatic | Linear scaling |
| **Availability** | 99.999% SLA | 99.999% SLA | Masterless (no SPOF) |
| **CAP Theorem** | AP (default) | Variable (5 levels) | AP (Tunable) |
| **Cost** | Pay-per-use | RU-based billing | Free (OSS) / operational cost |
| **ScalarDB Affinity** | Very high | Very high | Very high |

---

## 9. ScalarDB 3.17 New Features (Database-Related)

- **AlloyDB**: Added support for versions 15, 16 (using PostgreSQL JDBC driver)
- **TiDB**: Added support for versions 6.5, 7.5, 8.5 (using MySQL Connector/J)
- **Cassandra**: Added integration tests for versions 4, 5
- **Object storage**: Added support for Amazon S3, Azure Blob Storage, Google Cloud Storage (Private Preview)
- **Vector search**: Support for configuring Embedding Store/Model with multiple named instances
- **Virtual Tables**: Introduced virtual tables to the storage abstraction layer. Supports logical joining of two tables by primary key
- **RBAC**: Added role-based access control (ScalarDB Cluster)
- **Aggregate functions**: SUM, MIN, MAX, AVG and HAVING clause (ScalarDB SQL)

---

## 10. Kubernetes / Deployment Requirements

### ScalarDB Cluster

- **Kubernetes**: 1.31 - 1.34 (EKS, AKS supported)
- **Red Hat OpenShift**: 4.18 - 4.20
- **Helm**: 3.5+
- **Key ports**: 60053 (API), 8080 (GraphQL), 9080 (metrics)

### ScalarDB Analytics Server

- **Kubernetes**: 1.31 - 1.34 (EKS, AKS supported)
- **Red Hat OpenShift**: Support "TBD"
- **Helm**: 3.5+
- **Key ports**: 11051, 11052

---

## Sources

- [ScalarDB Overview](https://scalardb.scalar-labs.com/docs/latest/overview/)
- [ScalarDB Requirements (3.13)](https://scalardb.scalar-labs.com/docs/3.13/requirements/)
- [ScalarDB Requirements (latest/3.17)](https://scalardb.scalar-labs.com/docs/latest/requirements/)
- [ScalarDB Supported Databases (GitHub)](https://github.com/scalar-labs/scalardb/blob/master/docs/scalardb-supported-databases.md)
- [ScalarDB 3.17 Release Notes](https://scalardb.scalar-labs.com/docs/latest/releases/release-notes/)
- [Multi-Storage Transactions](https://scalardb.scalar-labs.com/docs/latest/multi-storage-transactions/)
- [ScalarDB Analytics Design](https://scalardb.scalar-labs.com/docs/latest/scalardb-analytics/design/)
- [Getting Started with Vector Search](https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/getting-started-with-vector-search/)
- [Consensus Commit Protocol](https://scalardb.scalar-labs.com/docs/latest/consensus-commit/)
- [ScalarDB GitHub Repository](https://github.com/scalar-labs/scalardb)
- [Scalar, Inc. ScalarDB Product Page](https://www.scalar-labs.com/scalardb)
- [Getting Started with ScalarDB](https://scalardb.scalar-labs.com/docs/latest/getting-started-with-scalardb/)
