# Physical Data Model Investigation

## 1. Partition Key (PT) Design

### 1.1 Role and Importance of Partition Key

ScalarDB's data model is an "extended key-value model inspired by Bigtable," and the data hierarchy consists of **Namespace > Table > Partition > Record > Column**. The Partition Key is the most important design element that **uniquely identifies a partition and determines the unit of data distribution**.

ScalarDB distributes data using hash-based partitioning, so the Partition Key value determines which node (partition) a record is placed on. Consequently, Partition Key design directly impacts:

- **Read/write efficiency**: Single partition lookup is the most efficient
- **Load distribution**: Poor Partition Key selection causes hotspots
- **Scalability**: Since scale-out occurs at the partition level, even distribution is essential

Reference: [Model Your Data | ScalarDB Documentation](https://scalardb.scalar-labs.com/docs/latest/data-modeling/)

### 1.2 Design Best Practices

**Principle: Query-Driven Modeling**

In ScalarDB, instead of normalization as in relational models, the table structure is determined based on the application's access patterns.

**Example: Banking Application**

| Design Pattern | Partition Key | Clustering Key | Evaluation |
|---|---|---|---|
| Good design | `account_id` | `transaction_date` | Access is distributed per account |
| Bad design | `branch_id` | `account_id` | All accounts in a branch concentrate in one partition |

```json
{
  "banking.account_transactions": {
    "transaction": true,
    "partition-key": ["account_id"],
    "clustering-key": ["transaction_date DESC"],
    "columns": {
      "account_id": "TEXT",
      "transaction_date": "BIGINT",
      "amount": "INT",
      "description": "TEXT"
    }
  }
}
```

### 1.3 Hotspot Avoidance

A hotspot is a phenomenon where access concentrates on a specific partition, making that node a bottleneck.

**Avoidance Strategies:**

| Method | Description | Use Case |
|---|---|---|
| Select high-cardinality columns | Use highly unique columns such as user ID, order ID | General OLTP workloads |
| Composite Partition Key | Increase distribution by combining multiple columns | When a single column has significant skew |
| Bucketing (artificial partitioning) | Append a hash suffix to the original value for distribution | Time-series data or other cases where concentration on specific keys is unavoidable |

**Bucketing Example:**
```
# Original design: sensor_id is the Partition Key but concentrates on specific sensors
# Improved: Split into 10 using sensor_id + bucket_id(0-9)
partition-key: ["sensor_id", "bucket_id"]
```

### 1.4 Cardinality Considerations

| Cardinality | Examples | Risk | Recommendation |
|---|---|---|---|
| Very high (millions+) | UUID, user ID | Partition count becomes enormous but evenly distributed | Optimal |
| Medium (thousands to tens of thousands) | Store ID, product category ID | Moderate distribution achieved | Appropriate |
| Low (tens or fewer) | Prefecture code, status values | A few large partitions form, causing load concentration | Should be avoided |
| Extremely low (1 to a few) | Boolean values, fixed classification values | Effectively a single partition. Scalability is lost | Not acceptable |

**Guideline criteria:**
- It is desirable to have at least 10x more partitions than nodes
- Design so that the number of records per partition stays below tens of thousands

---

## 2. Clustering Key (CK) Design

### 2.1 Role of Clustering Key

The Clustering Key **uniquely identifies records within a partition and determines their sort order**. In ScalarDB, records within a partition are (logically) stored sorted by the Clustering Key columns.

Primary roles:
- Guarantee record uniqueness within a partition (Partition Key + Clustering Key = Primary Key)
- Optimization of range scans
- Control of sort order within a partition

### 2.2 Determining Sort Order

You can specify `ASC` (ascending) or `DESC` (descending) when defining the schema.

```json
{
  "order.order_items": {
    "transaction": true,
    "partition-key": ["order_id"],
    "clustering-key": ["item_seq ASC"],
    "columns": {
      "order_id": "TEXT",
      "item_seq": "INT",
      "product_id": "TEXT",
      "quantity": "INT",
      "price": "INT"
    }
  }
}
```

**Guidelines for determining sort order:**

| Access Pattern | Recommended Sort Order | Reason |
|---|---|---|
| Retrieve latest data first | `DESC` | Latest record comes first, efficient with Limit |
| Time-series sequential scan | `ASC` | Natural chronological traversal |
| Pagination | Direction with higher access frequency | Optimizes scan start position |

### 2.3 Range Scan Optimization

ScalarDB's range scan (Scan) **can only be executed efficiently within a partition**. Performing a scan without specifying the partition key results in a cross-partition scan, which is inefficient and executes at a low isolation level (`SNAPSHOT` for non-JDBC databases).

**Conditions for efficient scans:**
1. Exact match specification of the Partition Key is required
2. Narrow the range by specifying boundary values (start/end) of the Clustering Key
3. Control boundary handling with inclusive/exclusive specification

```java
// Efficient intra-partition scan
Scan scan = Scan.newBuilder()
    .namespace("ns")
    .table("order_items")
    .partitionKey(Key.ofText("order_id", "ORD-001"))
    .start(Key.ofInt("item_seq", 1), true)   // inclusive
    .end(Key.ofInt("item_seq", 100), true)    // inclusive
    .orderings(Scan.Ordering.asc("item_seq"))
    .limit(50)
    .build();
```

### 2.4 Using Composite Clustering Keys

When using composite Clustering Keys, **the declaration order of columns is important**, and during scans, only consecutive columns from the beginning can be specified in that order.

```json
{
  "log.access_logs": {
    "transaction": true,
    "partition-key": ["user_id"],
    "clustering-key": ["access_date DESC", "access_time DESC", "log_seq ASC"],
    "columns": {
      "user_id": "TEXT",
      "access_date": "TEXT",
      "access_time": "TEXT",
      "log_seq": "INT",
      "action": "TEXT",
      "resource": "TEXT"
    }
  }
}
```

**Valid scan conditions:**
- `user_id` + range on `access_date` --> Valid
- `user_id` + range on `access_date` + `access_time` --> Valid
- `user_id` + `access_time` only (skipping `access_date`) --> Invalid (cannot skip leading columns)

**Composite CK design guidelines:**
- Place the most frequently filtered column first
- For time-series data, the typical order is date > time > sequence number
- Aim for 2-3 columns; do not add excessively

---

## 3. Secondary Index (SI) Design

### 3.1 Purpose and Limitations of Secondary Index

ScalarDB's Secondary Index enables searching by columns other than the Partition Key. However, there are the following important limitations.

**Limitations:**
| Limitation | Details |
|---|---|
| Single column only | Composite indexes (multi-column indexes) are not supported |
| Full partition scan | Index key searches span all partitions, making them inefficient |
| Performance degradation with low selectivity | Particularly inefficient when selectivity is low (many records match) |

Reference: [ScalarDB Java API Guide](https://scalardb.scalar-labs.com/docs/3.16/api-guide/)

### 3.2 Impact on Performance

**Impact on reads:**
- Searches using Secondary Index scan all partitions, so cost increases proportionally to the number of partitions
- Can be orders of magnitude slower compared to scans with Partition Key specification

**Impact on writes:**
- Write performance degrades due to index maintenance costs
- Additional overhead from index updates on the underlying database side

**Consensus Commit metadata overhead:**
- ScalarDB attaches transaction metadata (`tx_id`, `tx_state`, `tx_version`, previous version data, etc.) to each record
- Read/write access to the underlying database roughly doubles
- Overhead increases further when combined with Secondary Index

### 3.3 When to Use and When to Avoid

**When to use:**
- Low-frequency lookups (such as admin panel searches)
- High selectivity (search results are approximately 0.1% or less of all records)
- Searches where the Partition Key cannot be known in advance

**When to avoid:**
- High-frequency query paths (such as main API endpoints)
- Columns with low selectivity (status flags, boolean values, etc.)
- Searches that may return large numbers of records

**Recommended alternative: Index Table Pattern**

Instead of Secondary Index, create a separate table with the column you want to search as the Partition Key.

```
# Base table: search by user ID
user_table(user_id[PK], email, name, status)

# Index table: search by email address
user_by_email(email[PK], user_id, name, status)
```

Trade-offs of this pattern:
- Reads are efficient (single partition lookup)
- Writes require updates to two tables (consistency can be guaranteed with ScalarDB transactions)
- Increased storage consumption due to data duplication

---

## 4. Database Selection Criteria

### 4.1 Selection Based on Functional Requirements

Since ScalarDB is a "universal transaction manager" that abstracts multiple databases and provides unified access, the selection of the underlying database remains important.

Reference: [ScalarDB Overview](https://scalardb.scalar-labs.com/docs/3.13/overview/), [ScalarDB Configurations](https://scalardb.scalar-labs.com/docs/latest/configurations/)

#### Transaction Requirements

| Requirement | ScalarDB Support | Underlying DB Selection Considerations |
|---|---|---|
| ACID required (strict serializability) | Set `SERIALIZABLE` with Consensus Commit | Underlying DB's transaction features are not needed (ScalarDB manages them) |
| Snapshot Isolation is sufficient | Consensus Commit with `SNAPSHOT` (default) | NoSQL systems are also suitable when prioritizing performance |
| Single record operations only | `single-crud-operation` mode is also available | Leverage the underlying DB's native transactions |
| Cross-database transactions | Achieved with Multi-storage configuration | Optimal DB can be selected per namespace |

#### Data Structure

| Data Characteristics | Recommended Underlying DB | Reason |
|---|---|---|
| Relational (normalized, heavy JOIN usage) | PostgreSQL, MySQL, Aurora | JOINs possible with ScalarDB SQL. Most feature-rich via JDBC |
| Wide-column (many columns, sparse data) | Cassandra | High affinity with ScalarDB's data model |
| Large-scale key-value | DynamoDB | Scalability as a managed service |
| Global distribution | Cosmos DB | Ease of multi-region deployment |

#### Query Patterns

| Query Pattern | Required Capability | Recommended Configuration |
|---|---|---|
| PK exact match Get | Basic Get operation | Any underlying DB is OK |
| Intra-partition range scan | Scan with CK range | Any underlying DB is OK |
| Cross-partition scan | `cross_partition_scan.enabled=true` | JDBC-based preferred (supports filtering and sorting) |
| Complex JOINs | ScalarDB SQL | JDBC-based DB required |
| Full-text search | Mechanism outside ScalarDB needed | Use in combination with Elasticsearch, etc. |

### 4.2 Selection Based on Non-Functional Requirements

#### Read/Write Ratio

| Ratio | Recommended Underlying DB | Reason |
|---|---|---|
| Read-heavy (Read 80%+) | PostgreSQL, Aurora Reader, DynamoDB (with DAX) | Leverage read replicas and caching |
| Write-heavy (Write 50%+) | Cassandra, DynamoDB | Architecture optimized for writes |
| Balanced read/write | PostgreSQL, MySQL | Balanced performance |

#### Latency Requirements

| Requirement Level | Target Value | Recommended Configuration |
|---|---|---|
| Ultra-low latency | p99 < 10ms | DynamoDB (same region), with local cache |
| Low latency | p99 < 50ms | PostgreSQL/MySQL (same AZ), Cassandra (LOCAL_QUORUM) |
| Medium | p99 < 200ms | General JDBC-based DB |
| Relaxed | p99 < 1s | Cross-region configurations are acceptable |

**Note:** ScalarDB's Consensus Commit requires approximately 2x the access to the underlying DB, so plan for approximately 2-3x overhead over the underlying DB's standalone latency.

#### Scalability Requirements

According to the VLDB 2023 paper, ScalarDB achieved **4.6x throughput** in a 15-node environment compared to a 3-node environment, achieving **92% scalability efficiency**.

| Scale | Recommended Underlying DB | Reason |
|---|---|---|
| Small (up to 1 million records) | PostgreSQL, MySQL, SQLite | Simplicity of operations |
| Medium (up to 1 billion records) | PostgreSQL (with partitioning), Aurora, Cassandra | Starting point for horizontal distribution |
| Large (over 1 billion records) | Cassandra, DynamoDB | Nearly unlimited scalability |
| Multi-region | DynamoDB Global Tables, Cosmos DB | Native support for global distribution |

Reference: [ScalarDB: Universal Transaction Manager for Polystores (VLDB'23)](https://dl.acm.org/doi/10.14778/3611540.3611563)

#### Data Size

| Data Size | Recommendation | Considerations |
|---|---|---|
| Up to 100GB | Single JDBC DB | Minimum operational cost |
| 100GB-1TB | Aurora, small Cassandra cluster | Leverage auto-scaling |
| 1TB-10TB | Medium Cassandra cluster, DynamoDB | Partition design is critical |
| Over 10TB | DynamoDB, large Cassandra cluster + S3 (cold data) | Leverage ScalarDB's object storage support |

#### Availability Requirements (RPO/RTO)

| SLA | RPO | RTO | Recommended Configuration |
|---|---|---|---|
| 99.9% | < 1 hour | < 1 hour | Single region, multi-AZ redundancy |
| 99.95% | < 15 minutes | < 30 minutes | Aurora multi-AZ, Cassandra RF=3 |
| 99.99% | < 1 minute | < 5 minutes | Multi-region configuration, DynamoDB Global Tables |
| 99.999% | 0 (zero data loss) | < 1 minute | Cosmos DB multi-region + synchronous replication |

---

## 5. Consensus Commit Metadata Overhead

ScalarDB's Consensus Commit protocol attaches transaction metadata to each record.

**Attached metadata:**
- `tx_id`: Transaction ID
- `tx_state`: Transaction state
- `tx_version`: Version number
- `tx_prepared_at`: Prepare timestamp
- `tx_committed_at`: Commit timestamp
- `before_*` columns: Previous version data (for rollback)

**Overhead impact:**
- Read/write access to the underlying database roughly doubles
- Additional access occurs for recording transaction state in the Coordinator table
- Overhead increases further when combined with Secondary Index

**Configuration for performance optimization:**

| Setting | Default | Effect |
|---|---|---|
| `parallel_executor_count` | 128 | Number of parallel execution threads. Target is 2-4x the number of CPU cores |
| `async_commit.enabled` | false | Reduce write latency with asynchronous commit |
| `async_rollback.enabled` | false | Reduce latency on errors with asynchronous rollback |
| `coordinator.group_commit.enabled` | false | Improve write throughput with group commit |
| `scan_fetch_size` | 10 | Batch fetch count during scans. Consider increasing for bulk reads |

Reference: [Consensus Commit Protocol | ScalarDB Documentation](https://scalardb.scalar-labs.com/docs/latest/consensus-commit/), [ScalarDB Configurations](https://scalardb.scalar-labs.com/docs/latest/configurations/)

### Storage Overhead (Consensus Commit Metadata)

ScalarDB's Consensus Commit adds transaction management metadata columns to each record. This overhead should be considered during capacity planning.

#### Metadata Column Structure

| Column | Type | Estimated Size | Purpose |
|--------|------|------------|------|
| `tx_id` | VARCHAR | ~40-60 bytes | Transaction ID |
| `tx_state` | INT | 4 bytes | Transaction state |
| `tx_version` | INT | 4 bytes | Version number |
| `tx_prepared_at` | BIGINT | 8 bytes | Prepare timestamp |
| `tx_committed_at` | BIGINT | 8 bytes | Commit timestamp |
| `before_*` columns | Same type as each column | Same size as app data | Before-update image |

**Fixed metadata overhead**: ~80-100 bytes/record
**Before-image overhead**: App data size x 1.0 (for all columns)

#### Storage Increase Rate Estimates

| App Data Size/Record | Including Metadata | Increase Rate |
|--------------------------|---------------|--------|
| 100 bytes | ~300 bytes | Approx. 3x |
| 500 bytes | ~1,100 bytes | Approx. 2.2x |
| 2,000 bytes | ~4,100 bytes | Approx. 2x |

#### Coordinator Table Storage

The Coordinator table records the state of committed transactions.

- 1 record/transaction: ~100 bytes
- Example: 1 million Tx/day = ~100MB/day = ~3GB/month
- **A TTL setting or archiving strategy must be established** (automatic purge functionality is not currently provided)

#### When Using 3.17 Transaction Metadata Decoupling

Since metadata is separated into a different table, the application data table itself is kept clean. However:
- Total storage usage remains equivalent
- I/O volume may increase due to JOIN via VIEW during reads

---

## 6. Performance and Availability Requirements

### 6.1 Latency (p50, p95, p99)

In ScalarDB's Consensus Commit protocol, a single transaction makes multiple accesses to the underlying DB. The following are general reference values.

**Single Record Get Operation (Partition Key specified):**

| Percentile | JDBC (PostgreSQL, same AZ) | Cassandra (LOCAL_QUORUM) | DynamoDB (same region) |
|---|---|---|---|
| p50 | 3-8ms | 3-10ms | 5-15ms |
| p95 | 10-30ms | 15-40ms | 15-50ms |
| p99 | 20-80ms | 30-100ms | 30-100ms |

**Single Record Write Operation (Insert/Update):**

| Percentile | JDBC (PostgreSQL) | Cassandra | DynamoDB |
|---|---|---|---|
| p50 | 10-30ms | 10-25ms | 15-40ms |
| p95 | 30-80ms | 30-70ms | 40-100ms |
| p99 | 50-200ms | 50-150ms | 60-200ms |

**Note:** The above are general estimates only. Actual values depend heavily on hardware configuration, network, data size, and concurrency level. For official benchmark results, refer to [How to Benchmark ScalarDB with TPC-C](https://medium.com/scalar-engineering/tpc-c%E3%81%AB%E3%82%88%E3%82%8Bscalardb%E3%81%AE%E3%83%99%E3%83%B3%E3%83%81%E3%83%9E%E3%83%BC%E3%82%AF%E6%96%B9%E6%B3%95%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6-263b660ba028).

### 6.2 Throughput (TPS/QPS)

Metrics based on the VLDB 2023 paper benchmark results:

| Configuration | Workload | Reference Throughput | Scalability |
|---|---|---|---|
| 3-node Cassandra | TPC-C | Baseline | - |
| 15-node Cassandra | TPC-C | Approx. 4.6x (92% efficiency) | Nearly linear scaling |
| With optimizations applied | MariaDB | Up to 87% performance improvement | - |
| With optimizations applied | PostgreSQL | Up to 48% performance improvement | - |

### OCC Conflict Rate Modeling

ScalarDB's Consensus Commit employs Optimistic Concurrency Control (OCC). In environments with high conflict rates, retries increase and throughput drops sharply.

#### Conflict Probability Approximation Formula

```
P(conflict) ≈ 1 - (1 - k/N)^(C-1)

k: Number of write records per transaction
N: Total number of records subject to conflict (hot records)
C: Number of concurrent transactions
```

#### Practical Thresholds

| Conflict Rate | Status | Action |
|--------|------|-----------|
| < 5% | Good | Retry overhead is negligible |
| 5% - 15% | Caution | Latency increase from frequent retries becomes apparent. Consider reviewing PK design |
| 15% - 30% | Danger | Throughput drops sharply. Consider partition splitting, reducing transaction scope |
| > 30% | Design change required | Eliminate hotspots, implement bucketing, fundamentally review access patterns |

#### Monitoring Metrics

- Monitor the frequency of `TransactionConflictException` occurrences
- Threshold alerts: Warning at >10%, Critical at >20% (consider pausing batch processing)

### Consensus Commit Latency Breakdown (Estimates)

Typical latency decomposition for 1 transaction (1 Read + 1 Write):

| Phase | Processing | Estimate |
|---------|---------|------|
| Begin | Transaction ID generation | ~0.1ms (Piggyback Begin enabled: 0ms) |
| Read | gRPC RTT + DB Read + metadata verification | ~6-14ms |
| Write | Local workspace recording | ~0.1ms (Write Buffering enabled: buffer accumulation only) |
| Prepare | Conditional write + previous version backup | ~8-23ms |
| Validate | Re-verification of Read Set (Serializable only) | ~3-10ms |
| Commit | Coordinator table recording + record state update | ~6-16ms |
| **Total (SI, no optimization)** | | **~20-53ms** |
| **Total (SI, all optimizations)** | | **~14-35ms** |
| **Total (Serializable, all optimizations)** | | **~17-45ms** |

* Estimates for same-AZ, underlying DB is RDBMS (PostgreSQL/MySQL)

### 6.3 Availability (99.9%, 99.99%, etc.)

| SLA Target | Annual Allowed Downtime | Recommended Configuration |
|---|---|---|
| 99.9% | Approx. 8.76 hours | Single region, multi-AZ. Cassandra RF=3 or Aurora multi-AZ |
| 99.95% | Approx. 4.38 hours | Multi-AZ + automatic failover |
| 99.99% | Approx. 52.6 minutes | Multi-region configuration. DynamoDB Global Tables or Cosmos DB |
| 99.999% | Approx. 5.26 minutes | Multi-region + active-active. Operational maturity is also required |

**ScalarDB Cluster deployment:**
- Runs on Kubernetes 1.31-1.34 (EKS, AKS, OpenShift supported)
- Ports: 60053 (API), 8080 (GraphQL), 9080 (metrics)
- Throughput can be improved through horizontal Pod scaling

Reference: [Requirements | ScalarDB Documentation](https://scalardb.scalar-labs.com/docs/latest/requirements/)

### 6.4 Data Durability

| Requirement | Approach | Target |
|---|---|---|
| Node failure tolerance | Cassandra RF=3, PostgreSQL streaming replication | No data loss even with one node lost |
| AZ failure tolerance | Multi-AZ deployment, Aurora multi-AZ | No data loss even with AZ failure |
| Region failure tolerance | Cross-region replication | Settings based on RPO |
| Logical corruption tolerance | Point-in-Time Recovery (PITR) | Recovery to any point in time |

**Consensus Commit data integrity guarantees:**
- Records transaction state in the Coordinator table
- Automatic recovery from transaction state during failures
- Guarantees Serializable (when set to `SERIALIZABLE`)

> **Note**: Whether ScalarDB achieves Strict Serializability depends on the clock synchronization accuracy of the underlying storage. Since Strict Serializability requires real-time ordering guarantees, it may not be guaranteed in environments with large clock skew between nodes.

### 6.5 Recovery Time

| Scenario | Typical RTO | Recommended Measures |
|---|---|---|
| Single node failure | Seconds to minutes | Cassandra: automatic repair, JDBC: failover |
| AZ failure | Minutes to tens of minutes | Automatic switchover to multi-AZ replica |
| Region failure | Tens of minutes to hours | DNS-based switchover, multi-region configuration |
| Data corruption | Hours | Recovery from PITR |
| ScalarDB Cluster Pod failure | Seconds to tens of seconds | Kubernetes automatic Pod restart |

---

## 7. Virtual Tables (ScalarDB 3.17 New Feature)

**Virtual Tables** introduced in ScalarDB 3.17 is a feature that supports logical joining of two tables by primary key in the storage abstraction layer.

### Overview

Virtual Tables allow data that physically exists in different tables (potentially on different databases) to be treated logically as a single table. This enables efficient handling of the following use cases.

**Applicable scenarios:**
- Logical integration of master data that needs to be shared across microservices
- Unified view of base table and index table in the index table pattern
- Transparent access to old and new tables during gradual data migration

**Constraints:**
- Join conditions are limited to primary keys
- Currently only supports joining two tables
- Write operations are performed against the original tables

---

## 8. Design Decision Flowchart

The following order is recommended for data model design in ScalarDB.

1. **Enumerate access patterns** -- Identify which queries are executed most frequently
2. **Determine Partition Key** -- Select the search condition of the most frequent query as the Partition Key. Choose a column with high cardinality
3. **Determine Clustering Key** -- Decide based on range search and sorting requirements within the partition
4. **Consider index tables** -- Prioritize the alternative table approach over Secondary Index
5. **Select underlying database** -- Decide based on non-functional requirements (latency, scalability, availability)
6. **Consider multi-storage configuration** -- Place data with different characteristics on different underlying DBs

**Key points:**
- ScalarDB adopts a NoSQL-like query-driven design philosophy
- Prioritize single partition lookups in design
- Use Secondary Index as a last resort; prefer the index table pattern
- Incorporate Consensus Commit metadata overhead (approximately 2x DB access) into performance estimates
- As demonstrated in the VLDB 2023 paper, nearly linear scalability is achievable, but partition design is a prerequisite

---

## Expected Functional Requirements

### CRUD Operations

ScalarDB provides the following CRUD APIs (see Java API Guide).

| Operation | ScalarDB API | Description | Performance Characteristics |
|---|---|---|---|
| Create | `Insert`, `Put` | Insert a record. `Insert` returns an error if the record already exists | O(1) with Partition Key specification |
| Read (single) | `Get` | Retrieve one record by Primary Key | Most efficient. p50 < a few ms |
| Read (multiple) | `Scan` | Range search within a partition | Efficient with CK range specification |
| Update | `Update`, `Upsert` | Update a record. `Upsert` inserts if not exists | Requires prior Get (for Put) |
| Delete | `Delete` | Delete by Primary Key | Implicit pre-read is enabled |

**Important:** The `Put` operation was **deprecated in ScalarDB 3.13**. For new development, the following distinction is required:
- `Insert`: Create a new record (error if record already exists)
- `Update`: Update an existing record (error if not exists)
- `Upsert`: Update if exists, insert if not exists

If existing code uses `Put`, gradual migration to the above APIs is recommended.

Reference: [ScalarDB Java API Guide](https://scalardb.scalar-labs.com/docs/3.16/api-guide/)

### Search and Filtering

| Search Pattern | Implementation | Efficiency | Recommendation |
|---|---|---|---|
| PK exact match | `Get` | Highest | Always recommended |
| PK + CK range | `Scan` with boundaries | High | Recommended within partitions |
| Secondary Index | `Get`/`Scan` with indexKey | Medium to low | Low frequency only |
| Cross-partition scan + filter | `Scan.all()` + `where()` | Low | Last resort |
| Compound condition filtering | `ConditionBuilder` (CNF/DNF format) | DB-dependent | Effective for JDBC-based |

Filtering conditions must be specified in **Conjunctive Normal Form (CNF: AND of ORs)** or **Disjunctive Normal Form (DNF: OR of ANDs)**.

### Aggregation and Analytics

ScalarDB alone has limited direct support for real-time aggregation, but the following approaches are available.

| Method | Description | Use Case |
|---|---|---|
| ScalarDB Analytics (Spark integration) | Execute analytical queries via integration with Spark 3.4/3.5 | Large-scale batch aggregation |
| ScalarDB SQL | Leverage SQL aggregate functions | Small to medium-scale aggregation |
| Application-side aggregation | Retrieve via Scan, then aggregate in application | Simple aggregation |
| Materialized view (manual) | Store aggregation results in a separate table | When real-time aggregation is needed |

### Batch Processing

| Method | Description | Throughput Estimate |
|---|---|---|
| Transaction batch | Execute multiple operations within a single transaction | Hundreds to thousands ops/tx |
| ScalarDB Analytics | Large-scale batch processing via Spark jobs | Millions of records/job |
| Parallel transactions | Execute independent transactions in parallel from multiple threads | Controlled by `parallel_executor_count` (default 128) |

### Real-time Processing

| Requirement | ScalarDB Support | Notes |
|---|---|---|
| OLTP (single record operations) | Get/Put/Insert/Update/Delete | ScalarDB's strongest area |
| Event-driven processing | Not supported by ScalarDB alone. Integration with external queues required | Combination of Kafka + ScalarDB |
| Stream processing | ScalarDB is used as the persistence layer | Combine with Flink/Spark Streaming |

---

## Key References

- [Model Your Data | ScalarDB Documentation](https://scalardb.scalar-labs.com/docs/latest/data-modeling/)
- [Model Your Data | ScalarDB Documentation (Japanese)](https://scalardb.scalar-labs.com/ja-jp/docs/3.14/data-modeling/)
- [ScalarDB Java API Guide](https://scalardb.scalar-labs.com/docs/3.16/api-guide/)
- [Consensus Commit Protocol | ScalarDB Documentation](https://scalardb.scalar-labs.com/docs/latest/consensus-commit/)
- [ScalarDB Configurations](https://scalardb.scalar-labs.com/docs/latest/configurations/)
- [ScalarDB Schema Loader](https://scalardb.scalar-labs.com/docs/3.13/schema-loader/)
- [ScalarDB Overview](https://scalardb.scalar-labs.com/docs/3.13/overview/)
- [Multi-Storage Transactions](https://scalardb.scalar-labs.com/docs/latest/multi-storage-transactions/)
- [Requirements | ScalarDB Documentation](https://scalardb.scalar-labs.com/docs/latest/requirements/)
- [ScalarDB: Universal Transaction Manager for Polystores (VLDB'23)](https://dl.acm.org/doi/10.14778/3611540.3611563)
- [How to Benchmark ScalarDB with TPC-C](https://medium.com/scalar-engineering/tpc-c%E3%81%AB%E3%82%88%E3%82%8Bscalardb%E3%81%AE%E3%83%99%E3%83%B3%E3%83%81%E3%83%9E%E3%83%BC%E3%82%AF%E6%96%B9%E6%B3%95%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6-263b660ba028)
- [ScalarDB Benchmark Tools (GitHub)](https://github.com/scalar-labs/scalardb-benchmarks)
