# Data Model Definition Document Template

> Create this template for each ScalarDB-managed table.
> Fill in the `[...]` placeholders with project-specific information.

---

## 1. Table Overview

| Item | Details |
|------|------|
| Table Name | [namespace.table_name] |
| Owning Service | [Service name] |
| Backend DB | [MySQL / PostgreSQL / Cassandra / DynamoDB] |
| ScalarDB Managed | [Yes / No] |
| Estimated Record Count | [Count] |
| Estimated Growth Rate | [Monthly: +X records / Annually: +X records] |

---

## 2. Column Definitions

| Column Name | ScalarDB Type | Nullable | Default | Description |
|---------|-----------|---------|-----------|------|
| [Column name] | [Type] | [Yes / No] | [Value / None] | [...] |
| [Column name] | [Type] | [Yes / No] | [Value / None] | [...] |
| [Column name] | [Type] | [Yes / No] | [Value / None] | [...] |
| [Column name] | [Type] | [Yes / No] | [Value / None] | [...] |

> **ScalarDB Supported Types:** INT, BIGINT, FLOAT, DOUBLE, TEXT, BOOLEAN, BLOB
>
> - `INT`: 32-bit integer
> - `BIGINT`: 64-bit integer
> - `FLOAT`: Single-precision floating point
> - `DOUBLE`: Double-precision floating point
> - `TEXT`: String (size limit depends on the backend DB)
> - `BOOLEAN`: Boolean value
> - `BLOB`: Binary data

---

## 3. Key Design

| Key Type | Column Name | Selection Rationale |
|---------|---------|---------|
| Partition Key | [Column name] | [...] |
| Clustering Key | [Column name ASC/DESC] | [...] |
| Secondary Index | [Column name] | Usage: [...] |

---

## 4. Key Design Checklist

- [ ] Is the Partition Key cardinality sufficient (hotspot avoidance)?
- [ ] Does the Clustering Key order match the primary query patterns?
- [ ] Is the Secondary Index scan range limited (full scan avoidance)?
- [ ] Can a record be uniquely identified by Partition Key + Clustering Key?

---

## 5. Access Patterns

| Pattern Name | Operation (CRUD) | Condition (WHERE) | Frequency | Latency Requirement |
|-----------|-----------|------------|------|-------------|
| [Pattern name] | [Create / Read / Update / Delete] | [Condition expression] | [High / Medium / Low or req/sec] | [ms] |
| [Pattern name] | [Create / Read / Update / Delete] | [Condition expression] | [High / Medium / Low or req/sec] | [ms] |
| [Pattern name] | [Create / Read / Update / Delete] | [Condition expression] | [High / Medium / Low or req/sec] | [ms] |

---

## 6. Metadata Overhead Estimation

| Item | Value |
|------|-----|
| User data size per record | [bytes] |
| Consensus Commit metadata size | Approximately 200-300 bytes (tx_id, tx_version, tx_state, tx_prepared_at, before_* columns) |
| Overhead ratio | [Metadata size / User data size x 100]% |

> **When using Transaction Metadata Decoupling:**
> Metadata is separated into a different table, reducing the overhead on this table.
> However, since additional table lookups occur during READ operations, evaluate the impact on READ latency.

---

## 7. ScalarDB Schema Definition (Output)

```json
{
  "namespace": "[namespace]",
  "table": "[table_name]",
  "partition_key": ["[column]"],
  "clustering_key": ["[column]"],
  "columns": {
    "[column_name]": "[type]",
    "[column_name]": "[type]",
    "[column_name]": "[type]"
  },
  "secondary_index": ["[column]"]
}
```

---

## 8. Backend DB-Specific Optimizations

### Cassandra

| Item | Setting | Rationale |
|------|--------|------|
| Compaction Strategy | [SizeTiered / Leveled / TimeWindow] | [...] |
| TTL | [Seconds / Disabled] | [...] |
| Bucketing | [Bucketing strategy] | [...] |

### DynamoDB

| Item | Setting | Rationale |
|------|--------|------|
| GSI (Global Secondary Index) | [GSI definition] | [...] |
| Capacity Mode | [On-Demand / Provisioned] | [...] |
| TTL | [Attribute name / Disabled] | [...] |

### MySQL / PostgreSQL

| Item | Setting | Rationale |
|------|--------|------|
| Additional Indexes (other than ScalarDB SI) | [Index definition] | [...] |
| Partitioning | [RANGE / HASH / LIST / None] | [...] |
| Other Optimizations | [...] | [...] |
