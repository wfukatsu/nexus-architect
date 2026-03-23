# ScalarDB Migration Steps Template

This template is used to generate the **step-by-step migration guide**. Replace all `{{PLACEHOLDER}}` tokens with actual values from the source Oracle schema report and migration analysis.

**Input Source**: This guide consumes `oracle_schema_report.md` from the configured output directory (Skill 1 output).

---

# Oracle to ScalarDB: Step-by-Step Migration Guide

**Generated**: {{TIMESTAMP}}
**Source Database**: {{DATABASE_NAME}}
**Source Schema**: {{SCHEMA_NAME}}
**Target**: ScalarDB 3.17+
**Primary Migration Path**: ScalarDB Java Transaction API

---

## Mandatory Reference Documentation

Before proceeding with migration, review these essential references:

| Reference | URL | Purpose |
|-----------|-----|---------|
| **ScalarDB Java Transaction API** | https://scalardb.scalar-labs.com/docs/latest/api-guide/ | Transaction API (Get/Scan/Insert/Update/Delete) |
| **ScalarDB SQL Grammar Reference** | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/grammar/ | SQL syntax reference |
| **Schema Loader Import** | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import | Table import |
| **Decoupling Transaction Metadata** | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import/#decoupling-transaction-metadata | **RECOMMENDED** - Keep metadata separate |
| **Data Type Mapping** | https://scalardb.scalar-labs.com/docs/latest/schema-loader/#data-type-mapping-between-scalardb-and-other-databases | Type conversion |

---

## ScalarDB Component Strategy

> **ScalarDB Core (Java Transaction API) is the default migration path.** It is open-source/community-supported and provides Get, Scan, Insert, Upsert, Update, and Delete builders with full ACID transaction support.

| Component | When to Use | License |
|-----------|-------------|---------|
| **ScalarDB Core** (Java Transaction API) | Default — CRUD operations, schema import, application access | Open Source / Community |
| **ScalarDB Cluster** (SQL interface) | Only if SQL interface needed, or aggregate functions for small use cases | Enterprise |
| **ScalarDB Analytics** | Complex queries: multi-table JOINs (3+), subqueries, window functions, reporting | Enterprise |

**Migration Workflow:**
1. **Phase 1-4**: Use ScalarDB Core (Schema Loader) for schema and data migration
2. **Phase 5**: Deploy ScalarDB Core for application access; add Cluster only if SQL interface is needed
3. **Phase 5.5**: Deploy ScalarDB Analytics if complex queries exist
4. **Phase 5.6**: Deploy Oracle AQ if triggers/SPs with DML exist (MANDATORY for Oracle)
5. **Phase 6+**: Application uses ScalarDB Java Transaction API

---

## RECOMMENDED: Transaction Metadata Decoupling

> **This is the recommended approach for migration.** It keeps ScalarDB transaction metadata separate from your existing tables, so you don't need to alter your original database structure.

### Why Use Transaction Metadata Decoupling?

| Approach | `transaction: true` | `transaction-metadata-decoupling: true` |
|----------|---------------------|----------------------------------------|
| **Alters existing tables?** | YES - adds metadata columns | NO - tables unchanged |
| **Original data location** | Same table with extra columns | Original table unchanged |
| **ScalarDB metadata location** | In same table | Separate `<table>_scalardb` table |
| **Best for** | New tables | **Migrating existing tables** |
| **Rollback complexity** | High (must remove columns) | Low (just drop metadata table) |

### How It Works

When you enable `transaction-metadata-decoupling: true`:

1. Your original table (e.g., `customers`) remains **completely unchanged**
2. ScalarDB creates a separate table `customers_scalardb` for transaction metadata
3. ScalarDB manages the relationship between them internally
4. Your application accesses data through ScalarDB as `<table_name>_scalardb`

### Configuration Example

**Option A: Transaction Metadata Decoupling (RECOMMENDED for migration)**
```json
{
  "{{NAMESPACE}}.{{TABLE_NAME}}": {
    "transaction-metadata-decoupling": true,
    "partition-key": ["{{PARTITION_KEY}}"],
    "clustering-key": ["{{CLUSTERING_KEY}}"],
    "columns": {
      // column definitions
    }
  }
}
```

**Option B: Standard Transaction (alters existing table)**
```json
{
  "{{NAMESPACE}}.{{TABLE_NAME}}": {
    "transaction": true,
    "partition-key": ["{{PARTITION_KEY}}"],
    "clustering-key": ["{{CLUSTERING_KEY}}"],
    "columns": {
      // column definitions
    }
  }
}
```

> **Note**: Use `transaction-metadata-decoupling: true` OR `transaction: true` - not both. For migration scenarios where you don't want to alter existing tables, use `transaction-metadata-decoupling: true`.

**Important**: When decoupling is enabled, access the table as `<table_name>_scalardb` in your application.

---

## ScalarDB SQL Capabilities and Limitations

> **Reference**: https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/grammar/

### Supported Features

| Feature | ScalarDB SQL Support | Notes |
|---------|---------------------|-------|
| SELECT, INSERT, UPDATE, DELETE | ✅ Supported | Standard DML |
| COUNT, SUM, AVG, MIN, MAX | ✅ Supported | Aggregate functions |
| GROUP BY, HAVING | ✅ Supported | Grouping |
| JOIN (INNER, LEFT, RIGHT) | ⚠️ Limited | See limitations below |
| ORDER BY, LIMIT | ✅ Supported | |
| CREATE/DROP TABLE | ✅ Supported | DDL |
| CREATE INDEX | ✅ Supported | Secondary indexes |

### Critical Limitations (Different from MySQL/Oracle)

| Limitation | Description | Impact |
|------------|-------------|--------|
| **Cross-partition JOINs** | JOINs across different partition keys may trigger full scans | Performance degradation |
| **Multi-table JOINs** | Not optimized like traditional RDBMS | Use ScalarDB Analytics for complex JOINs |
| **WHERE clause form** | Must be in DNF (OR-of-ANDs) or CNF (AND-of-ORs) | Complex predicates may fail |
| **Subqueries** | ❌ NOT supported | Use sequential queries or Analytics |
| **UNION/INTERSECT/EXCEPT** | ❌ NOT supported | Multiple queries + application merge |
| **Window functions** | ❌ NOT supported | Use ScalarDB Analytics |
| **Cross-partition UPDATE/DELETE** | Requires explicit enable; impacts performance | Include partition key in WHERE |

### WHERE Clause Requirements

ScalarDB requires predicates in specific forms:

**Valid (DNF - OR of ANDs):**
```sql
WHERE (a = 1 AND b = 2) OR (a = 3 AND b = 4)
```

**Valid (CNF - AND of ORs):**
```sql
WHERE (a = 1 OR a = 2) AND (b = 3 OR b = 4)
```

### Migration Decision Matrix

| Query Pattern | ScalarDB SQL | ScalarDB Analytics |
|---------------|--------------|-------------------|
| Simple CRUD (single table) | ✅ Use | Not needed |
| Single-partition queries | ✅ Use | Not needed |
| 2-table JOINs (same partition) | ✅ Use | Not needed |
| Multi-table JOINs (cross-partition) | ⚠️ May be slow | ✅ **Use Analytics** |
| Subqueries | ❌ Not supported | ✅ **Required** |
| Window functions (ROW_NUMBER, RANK) | ❌ Not supported | ✅ **Required** |
| Analytical/reporting queries | ⚠️ Not optimized | ✅ **Recommended** |

### When ScalarDB Analytics is Required

If your schema uses any of the following, plan for ScalarDB Analytics deployment:
- Subqueries (correlated or non-correlated)
- Window functions (ROW_NUMBER, RANK, DENSE_RANK, LEAD, LAG)
- Complex multi-table JOINs (3+ tables)
- UNION, INTERSECT, EXCEPT operations
- Complex analytical/reporting queries

**Analytics Reference**: https://scalardb.scalar-labs.com/docs/latest/scalardb-analytics/

---

## Migration Overview

This guide provides detailed, step-by-step instructions for migrating the **{{SCHEMA_NAME}}** Oracle schema to ScalarDB.

### Migration Phases

| Phase | Description | Estimated Effort |
|-------|-------------|------------------|
| 1. Preparation | Environment setup, backup, prerequisites | {{PREP_EFFORT}} |
| 2. Schema Conversion | Convert Oracle schema to ScalarDB format | {{SCHEMA_EFFORT}} |
| 3. ScalarDB Core Setup | Configure ScalarDB Core, create schemas (Schema Loader) | {{SETUP_EFFORT}} |
| 4. Data Migration | Import/migrate data to ScalarDB tables using SQL INSERT | {{DATA_EFFORT}} |
| 5. ScalarDB Cluster Deployment | Deploy ScalarDB Cluster for SQL access | {{CLUSTER_EFFORT}} |
| 5.5. ScalarDB Analytics (Conditional) | Deploy if subqueries/window functions needed | {{ANALYTICS_EFFORT}} |
| 5.6. Oracle AQ Setup (Conditional) | Configure AQ queues and deploy Java consumers | {{AQ_EFFORT}} |
| 6. Application Migration | Update application code and queries | {{APP_EFFORT}} |
| 7. Testing & Validation | Verify migration success | {{TEST_EFFORT}} |
| 8. Cutover | Switch to ScalarDB | {{CUTOVER_EFFORT}} |

---

## Phase 1: Preparation

### Step 1.1: Verify Prerequisites

**Java Requirements:**
```bash
# Verify Java version (8, 11, 17, or 21 LTS required)
java -version
```

**Download ScalarDB Schema Loader:**
```bash
# Download from Maven Central or Scalar Labs
wget https://repo1.maven.org/maven2/com/scalar-labs/scalardb-schema-loader/3.17.0/scalardb-schema-loader-3.17.0.jar
```

### Step 1.2: Backup Oracle Database

```bash
# Full export backup
expdp {{ORACLE_USER}}/{{ORACLE_PASSWORD}}@{{ORACLE_SERVICE}} \
  directory=DATA_PUMP_DIR \
  dumpfile={{SCHEMA_NAME}}_backup.dmp \
  schemas={{SCHEMA_NAME}} \
  logfile={{SCHEMA_NAME}}_backup.log
```

### Step 1.3: Document Current State

```sql
-- Record row counts for validation
SELECT table_name, num_rows
FROM all_tables
WHERE owner = '{{SCHEMA_NAME}}';

-- Export to CSV for later comparison
```

---

## Phase 2: Schema Conversion

### Step 2.1: Create ScalarDB Schema JSON

Create file: `scalardb_schema.json`

```json
{{SCALARDB_SCHEMA_JSON}}
```

### Step 2.2: Table-by-Table Conversion Details

{{#EACH_TABLE}}
#### Table: {{TABLE_NAME}}

**Original Oracle DDL:**
```sql
{{ORACLE_DDL}}
```

**ScalarDB Schema Entry (using Transaction Metadata Decoupling - RECOMMENDED):**
```json
{
  "{{NAMESPACE}}.{{TABLE_NAME}}": {
    "transaction-metadata-decoupling": true,
    "partition-key": [{{PARTITION_KEY}}],
    "clustering-key": [{{CLUSTERING_KEY}}],
    "columns": {
      {{COLUMN_DEFINITIONS}}
    }{{#IF_SECONDARY_INDEX}},
    "secondary-index": [{{SECONDARY_INDEXES}}]{{/IF_SECONDARY_INDEX}}
  }
}
```

> Access as `{{TABLE_NAME}}_scalardb` in your application (original table unchanged).

**Column Mapping:**
| Oracle Column | Oracle Type | ScalarDB Column | ScalarDB Type |
|---------------|-------------|-----------------|---------------|
{{COLUMN_MAPPINGS}}

**Key Design Rationale:**
- Partition Key: {{PARTITION_KEY_RATIONALE}}
- Clustering Key: {{CLUSTERING_KEY_RATIONALE}}

{{/EACH_TABLE}}

### Step 2.3: Handle Custom Types (Flattening)

{{#IF_CUSTOM_TYPES}}
#### Flattening Object Type: {{TYPE_NAME}}

**Original Type:**
```sql
CREATE TYPE {{TYPE_NAME}} AS OBJECT (
  {{TYPE_ATTRIBUTES}}
);
```

**Flattened Columns:**
| Original Attribute | Flattened Column Name | ScalarDB Type |
|-------------------|----------------------|---------------|
{{FLATTENED_MAPPINGS}}

**Update Schema JSON:**
Add these columns to the parent table's column definitions:
```json
{{FLATTENED_JSON}}
```
{{/IF_CUSTOM_TYPES}}

### Step 2.4: Handle Nested Tables

{{#IF_NESTED_TABLES}}
#### Converting Nested Table: {{NESTED_TABLE_NAME}}

**Original Structure:**
- Parent Table: {{PARENT_TABLE}}
- Nested Column: {{NESTED_COLUMN}}
- Storage Table: {{STORAGE_TABLE}}

**ScalarDB Approach:**
Create a separate table with foreign key relationship:

```json
{
  "{{NAMESPACE}}.{{CHILD_TABLE_NAME}}": {
    "transaction-metadata-decoupling": true,
    "partition-key": ["parent_{{PARENT_PK}}"],
    "clustering-key": ["item_id ASC"],
    "columns": {
      "parent_{{PARENT_PK}}": "{{PARENT_PK_TYPE}}",
      "item_id": "BIGINT",
      {{NESTED_COLUMNS}}
    }
  }
}
```

> Access as `{{CHILD_TABLE_NAME}}_scalardb` in your application.

**Data Migration Query:**
```sql
-- Extract nested table data with parent reference
SELECT
  t.{{PARENT_PK}} as parent_{{PARENT_PK}},
  ROWNUM as item_id,
  nt.*
FROM {{PARENT_TABLE}} t, TABLE(t.{{NESTED_COLUMN}}) nt;
```
{{/IF_NESTED_TABLES}}

---

## Phase 3: ScalarDB Setup

### Step 3.1: Create ScalarDB Configuration

Create file: `scalardb.properties`

```properties
# ScalarDB Configuration for Oracle Backend
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:oracle:thin:@//{{ORACLE_HOST}}:{{ORACLE_PORT}}/{{ORACLE_SERVICE}}
scalar.db.username={{SCALARDB_USER}}
scalar.db.password={{SCALARDB_PASSWORD}}

# Transaction settings
scalar.db.consensus_commit.isolation_level=SERIALIZABLE
scalar.db.consensus_commit.serializable_strategy=EXTRA_READ

# Optional: Connection pool settings
scalar.db.jdbc.connection_pool.min_idle=5
scalar.db.jdbc.connection_pool.max_idle=10
scalar.db.jdbc.connection_pool.max_total=25
```

### Step 3.2: Test ScalarDB Connection

```bash
# Test connection (creates coordinator table if needed)
java -jar scalardb-schema-loader-3.17.0.jar \
  --config scalardb.properties \
  --coordinator
```

**Expected Output:**
```
Creating coordinator tables...
Coordinator tables created successfully.
```

### Step 3.3: Create ScalarDB Schema

**Option A: Create New Tables**
```bash
java -jar scalardb-schema-loader-3.17.0.jar \
  --config scalardb.properties \
  --schema-file scalardb_schema.json \
  --coordinator
```

**Option B: Import Existing Tables**

Create file: `import_schema.json`
```json
{{IMPORT_SCHEMA_JSON}}
```

```bash
java -jar scalardb-schema-loader-3.17.0.jar \
  --config scalardb.properties \
  --schema-file import_schema.json \
  --import
```

### Step 3.4: Verify Schema Creation

```sql
-- Connect to Oracle and verify metadata tables
SELECT table_name
FROM all_tables
WHERE owner = 'SCALARDB'
ORDER BY table_name;

-- Expected: coordinator, namespaces_table, etc.
```

---

## Phase 4: Data Migration

### Step 4.1: Choose Migration Strategy

| Strategy | Best For | Downtime |
|----------|----------|----------|
| Import Existing | Production data, minimal changes | Low |
| ETL Migration | Complex transformations | Medium |
| Dual-Write | Gradual migration | None |

### Step 4.2: Import Existing Tables (Recommended)

For tables that can be imported directly:

```bash
java -jar scalardb-schema-loader-3.17.0.jar \
  --config scalardb.properties \
  --schema-file import_schema.json \
  --import
```

**Note:** This adds ScalarDB metadata to existing tables without moving data.

### Step 4.3: Migrate Transformed Data

For tables requiring transformation (custom types, nested tables):

{{#IF_TRANSFORMATION_NEEDED}}
#### Migrate {{TABLE_NAME}} Data

**Step 1: Export from Oracle**
```sql
-- Create staging view with flattened data
CREATE OR REPLACE VIEW {{TABLE_NAME}}_export AS
SELECT
  {{EXPORT_COLUMNS}}
FROM {{TABLE_NAME}};

-- Export to CSV
SET COLSEP ','
SET PAGESIZE 0
SET TRIMSPOOL ON
SET LINESIZE 32767
SPOOL {{TABLE_NAME}}_data.csv
SELECT * FROM {{TABLE_NAME}}_export;
SPOOL OFF
```

**Step 2: Insert into ScalarDB Table Using Transaction API**

> **IMPORTANT**: Use the ScalarDB Java Transaction API for data migration. It provides full ACID transaction support with Insert/Upsert builders.

**Using ScalarDB Java Transaction API (RECOMMENDED)**
```java
import com.scalar.db.api.*;
import com.scalar.db.io.Key;
import com.scalar.db.service.TransactionFactory;

public class DataMigration {

    private static final String NAMESPACE = "{{NAMESPACE}}";
    private final DistributedTransactionManager txManager;

    public DataMigration(String configFile) throws Exception {
        TransactionFactory factory = TransactionFactory.create(configFile);
        this.txManager = factory.getTransactionManager();
    }

    public void migrateData(long idValue, String nameValue) throws TransactionException {
        DistributedTransaction tx = txManager.start();
        try {
            Insert insert = Insert.newBuilder()
                .namespace(NAMESPACE)
                .table("{{TABLE_NAME}}")
                .partitionKey(Key.ofBigInt("id", idValue))
                .textValue("name", nameValue)
                // ... set other columns
                .build();

            tx.insert(insert);
            tx.commit();
        } catch (Exception e) {
            tx.rollback();
            throw e;
        }
    }

    public void migrateBatch(List<DataRow> rows) throws TransactionException {
        int batchSize = 1000;
        for (int i = 0; i < rows.size(); i += batchSize) {
            DistributedTransaction tx = txManager.start();
            try {
                List<DataRow> batch = rows.subList(i, Math.min(i + batchSize, rows.size()));
                List<Mutation> mutations = new ArrayList<>();

                for (DataRow row : batch) {
                    Insert insert = Insert.newBuilder()
                        .namespace(NAMESPACE)
                        .table("{{TABLE_NAME}}")
                        .partitionKey(Key.ofBigInt("id", row.getId()))
                        .textValue("name", row.getName())
                        // ... set other columns
                        .build();
                    mutations.add(insert);
                }

                tx.mutate(mutations);
                tx.commit();
            } catch (Exception e) {
                tx.rollback();
                throw e;
            }
        }
    }

    public void close() {
        txManager.close();
    }
}
```

**Option B: Direct Oracle SQL*Plus (for existing tables with metadata decoupling)**
```sql
-- If using transaction-metadata-decoupling, data stays in original table
-- Just verify the import was successful
SELECT COUNT(*) FROM {{TABLE_NAME}};
```
{{/IF_TRANSFORMATION_NEEDED}}

### Step 4.4: Validate Data Migration

```sql
-- Compare row counts
SELECT '{{TABLE_NAME}}' as table_name, COUNT(*) as scalardb_count
FROM {{NAMESPACE}}.{{TABLE_NAME}};

-- Compare with original Oracle count: {{ORIGINAL_COUNT}}
```

---

## Phase 5: Deploy ScalarDB for Application Access

> **ScalarDB Core (Java Transaction API) is the default.** It is embedded in your application as a library — no separate server needed. Use ScalarDB Cluster only if a SQL interface or aggregate functions are needed for specific use cases.

**Reference**: https://scalardb.scalar-labs.com/docs/latest/api-guide/

### Step 5.1: ScalarDB Core Setup (Default)

ScalarDB Core runs as an embedded library in your Java application. No separate server or container is needed.

**ScalarDB Core Configuration** (`scalardb.properties`):
```properties
# Backend database configuration
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:oracle:thin:@//{{ORACLE_HOST}}:{{ORACLE_PORT}}/{{ORACLE_SERVICE}}
scalar.db.username={{SCALARDB_USER}}
scalar.db.password={{SCALARDB_PASSWORD}}

# Transaction settings
scalar.db.consensus_commit.isolation_level=SERIALIZABLE
scalar.db.consensus_commit.serializable_strategy=EXTRA_READ

# Connection pool settings
scalar.db.jdbc.connection_pool.min_idle=5
scalar.db.jdbc.connection_pool.max_idle=10
scalar.db.jdbc.connection_pool.max_total=25
```

### Step 5.1b: ScalarDB Cluster Setup (Only If SQL Interface Needed)

> **Only deploy ScalarDB Cluster if your application requires a SQL interface or you need aggregate functions (GROUP BY, HAVING) for specific use cases.**

ScalarDB Cluster deployment options for production:
- **Kubernetes with Helm charts** (recommended for production)
- **Standalone Java process** (for single-node environments)

> **Docker Compose is NOT suitable for production environments.** Use it only for local development and testing.

**ScalarDB Cluster Configuration** (`scalardb-cluster.properties`):
```properties
# Backend database configuration
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:oracle:thin:@//{{ORACLE_HOST}}:{{ORACLE_PORT}}/{{ORACLE_SERVICE}}
scalar.db.username={{SCALARDB_USER}}
scalar.db.password={{SCALARDB_PASSWORD}}

# Cluster settings
scalar.db.cluster.node.standalone_mode.enabled=true

# SQL settings (the reason to use Cluster)
scalar.db.sql.enabled=true
```

### Step 5.2: Verify ScalarDB is Running

```java
// Test ScalarDB Core Transaction API connection
TransactionFactory factory = TransactionFactory.create("scalardb.properties");
DistributedTransactionManager txManager = factory.getTransactionManager();
DistributedTransaction tx = txManager.start();
// If no exception, ScalarDB is connected successfully
tx.abort();
txManager.close();
```

---

## Phase 5.5: Deploy ScalarDB Analytics (If Required)

> **When Required**: Deploy ScalarDB Analytics if your schema uses subqueries, window functions, complex multi-table JOINs, or UNION/INTERSECT/EXCEPT operations.

{{#IF_ANALYTICS_REQUIRED}}

### Step 5.5.1: Determine Analytics Requirements

Based on schema analysis, ScalarDB Analytics is required for:

| Feature | Tables/Queries Affected |
|---------|------------------------|
| {{FEATURE}} | {{AFFECTED_QUERIES}} |

### Step 5.5.2: Add Analytics Dependencies

**Maven (pom.xml):**
```xml
<dependency>
    <groupId>com.scalar-labs</groupId>
    <artifactId>scalardb-analytics</artifactId>
    <version>3.17.0</version>
</dependency>
```

### Step 5.5.3: Deploy ScalarDB Analytics

**Reference**: https://scalardb.scalar-labs.com/docs/latest/scalardb-analytics/

Deploy ScalarDB Analytics alongside your ScalarDB Core/Cluster environment. Use the same deployment approach as your main ScalarDB deployment (Kubernetes for production, standalone for single-node).

> **Docker Compose is NOT suitable for production environments.** Use it only for local development and testing.

**Analytics Configuration** (`scalardb-analytics.properties`):
```properties
# Connect to ScalarDB (adjust based on your deployment)
scalar.db.analytics.cluster.contact_points=<scalardb_host>:60053
```

### Step 5.5.4: Configure Query Routing

Your application must route queries appropriately:

```java
public class QueryRouter {
    private final Connection sqlConnection;      // For standard queries
    private final AnalyticsClient analyticsClient; // For complex queries

    public ResultSet executeQuery(String sql) throws SQLException {
        if (requiresAnalytics(sql)) {
            return analyticsClient.execute(sql);
        } else {
            return sqlConnection.createStatement().executeQuery(sql);
        }
    }

    private boolean requiresAnalytics(String sql) {
        // Check for subqueries, window functions, etc.
        return sql.contains("SELECT") && sql.contains("(SELECT")  // Subquery
            || sql.matches(".*\\b(ROW_NUMBER|RANK|DENSE_RANK|LAG|LEAD)\\b.*")  // Window functions
            || sql.matches(".*\\b(UNION|INTERSECT|EXCEPT)\\b.*");  // Set operations
    }
}
```

### Architecture with Analytics

```
Application Layer
       │
       ├──► ScalarDB Java Transaction API
       │       │
       │       └──► Simple CRUD, basic JOINs, aggregations
       │
       └──► ScalarDB Analytics
               │
               └──► Subqueries, window functions, complex JOINs
```

{{/IF_ANALYTICS_REQUIRED}}

{{#IF_ANALYTICS_NOT_REQUIRED}}

### Analytics Not Required

Based on schema analysis, ScalarDB Analytics is **NOT required** for this migration.

Standard ScalarDB SQL supports all identified query patterns:
- Simple CRUD operations
- Basic JOINs (within partitions)
- Aggregations (COUNT, SUM, AVG, MIN, MAX)
- GROUP BY with HAVING

**Note**: If complex analytical queries are added later, revisit this decision.

{{/IF_ANALYTICS_NOT_REQUIRED}}

---

## Phase 5.6: Oracle AQ Setup (MANDATORY When Triggers/SPs With DML Exist)

> **Oracle AQ is MANDATORY when the source Oracle database contains triggers or stored procedures that perform DML on other tables.** This ensures existing database behavior is preserved — the application continues to work exactly as before, with ScalarDB handling the underlying data layer.

> **IMPORTANT**: The database must be imported into ScalarDB FIRST (Phase 3). ScalarDB consumer code cannot modify the database unless the tables are migrated and managed through ScalarDB.

{{#IF_AQ_REQUIRED}}

### Step 5.6.1: Import Target Tables into ScalarDB

Before running the AQ setup or deploying consumers, ensure all target tables that the consumer will write to are imported into ScalarDB:

```bash
# Import existing Oracle tables into ScalarDB
java -jar scalardb-schema-loader-3.17.0.jar \
  --config scalardb.properties \
  --schema-file import_schema.json \
  --import
```

Use `transaction-metadata-decoupling: true` in the import schema to keep original tables unchanged.

### Step 5.6.2: Run AQ Setup SQL

Execute the generated `aq_setup.sql` file against the Oracle database. This file creates:
- Payload types (Oracle Object Types for message data)
- Queue tables and queues (with retry and exception queue settings)
- Enqueue stored procedures (replacing direct DML SPs)
- New AQ triggers (replacing original triggers — originals are disabled, not dropped)
- Verification queries

```bash
sqlplus {{ORACLE_USER}}/{{ORACLE_PASSWORD}}@//{{ORACLE_HOST}}:{{ORACLE_PORT}}/{{ORACLE_SERVICE}} @aq_setup.sql
```

### Step 5.6.3: Verify AQ Setup

```sql
-- Verify queues are running
SELECT name, queue_table, max_retries, retry_delay
FROM dba_queues
WHERE owner = '{{SCHEMA_NAME}}' AND queue_type = 'NORMAL_QUEUE';

-- Verify trigger status (originals DISABLED, new AQ triggers ENABLED)
SELECT trigger_name, status, triggering_event, table_name
FROM all_triggers
WHERE owner = '{{SCHEMA_NAME}}'
ORDER BY trigger_name;

-- Test: execute a DML to trigger an enqueue, then check the queue
SELECT MSG_STATE, RETRY_COUNT, t.user_data.operation_type
FROM aq${{QUEUE_TABLE}} t
WHERE MSG_STATE IN ('WAITING', 'READY');
```

### Step 5.6.4: Add Required Dependencies for Java Consumer

The AQ consumer requires JAR files that may not be in Maven Central:

| Dependency | Source | Notes |
|------------|--------|-------|
| `aqapi.jar` | `$ORACLE_HOME/rdbms/jlib/aqapi.jar` | **Must extract from Oracle DB** — not in Maven Central |
| `javax.jms-api-2.0.1.jar` | Maven Central | `javax.jms:javax.jms-api:2.0.1` |
| `ojdbc11` | Maven Central | `com.oracle.database.jdbc:ojdbc11:23.4.0.24.05` |
| `scalardb` | Maven Central | `com.scalar-labs:scalardb:3.17.1` |

**Extract `aqapi.jar` from Oracle Docker container:**
```bash
docker cp oracle-db:$ORACLE_HOME/rdbms/jlib/aqapi.jar ./libs/
```

**Gradle:**
```groovy
dependencies {
    implementation fileTree(dir: 'libs', include: ['*.jar'])  // aqapi.jar
    implementation 'javax.jms:javax.jms-api:2.0.1'
    implementation 'com.oracle.database.jdbc:ojdbc11:23.4.0.24.05'
    implementation 'com.scalar-labs:scalardb:3.17.1'
}
```

### Step 5.6.5: Deploy Java Consumer

1. Add the generated Java files (consumer classes, message POJOs, `AqStructHolder.java`) to your application source tree
2. Initialize the ScalarDB transaction manager in your application
3. Create the JMS consumer loop using the generated consumer's `processMessage()` and `parseMessage()` methods
4. The consumer uses a dual-transaction pattern: ScalarDB commits first, then AQ session commits
5. `Upsert` is recommended for idempotent message redelivery handling

Refer to `scalardb_aq_migration_report.md` for the complete integration guide with code examples.

### Architecture with AQ

```
Oracle Database (Producer)              Java Application (Consumer)
  DML triggers fire                       JMS polling loop
       │                                       │
       v                                       v
  Enqueue SPs called                    receiver.receive()
  DBMS_AQ.ENQUEUE(ON_COMMIT)                  │
       │                                       v
  COMMIT → messages READY ──────────►   parseMessage() → POJO
                                               │
                                               v
                                        ScalarDB tx.upsert()
                                        tx.commit()
                                               │
                                               v
                                        session.commit() (msg removed)
```

{{/IF_AQ_REQUIRED}}

{{#IF_AQ_NOT_REQUIRED}}

### AQ Not Required

Based on schema analysis, Oracle AQ is **NOT required** for this migration — no triggers or stored procedures with cross-table DML were found. Any validation-only logic can be migrated directly to Java service classes using the ScalarDB Transaction API.

{{/IF_AQ_NOT_REQUIRED}}

---

## Phase 6: Application Migration

### Step 6.1: Update Dependencies

**Maven (pom.xml):**
```xml
<dependency>
    <groupId>com.scalar-labs</groupId>
    <artifactId>scalardb</artifactId>
    <version>3.17.0</version>
</dependency>
```

**Gradle (build.gradle):**
```groovy
implementation 'com.scalar-labs:scalardb:3.17.0'
```

### Step 6.2: Create ScalarDB Configuration

Create file: `scalardb.properties`

```properties
# ScalarDB Core configuration pointing to Oracle backend
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:oracle:thin:@//{{ORACLE_HOST}}:{{ORACLE_PORT}}/{{ORACLE_SERVICE}}
scalar.db.username={{SCALARDB_USER}}
scalar.db.password={{SCALARDB_PASSWORD}}

# Transaction settings
scalar.db.consensus_commit.isolation_level=SERIALIZABLE
scalar.db.consensus_commit.serializable_strategy=EXTRA_READ
```

### Step 6.3: Update Connection Configuration

**Before (Oracle JDBC):**
```java
String url = "jdbc:oracle:thin:@//{{ORACLE_HOST}}:{{ORACLE_PORT}}/{{ORACLE_SERVICE}}";
Connection conn = DriverManager.getConnection(url, "{{USER}}", "{{PASSWORD}}");
```

**After (ScalarDB Java Transaction API):**
```java
import com.scalar.db.api.*;
import com.scalar.db.io.Key;
import com.scalar.db.service.TransactionFactory;

// Initialize Transaction Manager (do once at startup)
TransactionFactory factory = TransactionFactory.create("scalardb.properties");
DistributedTransactionManager txManager = factory.getTransactionManager();
```

> **Note**: The Transaction API uses `TransactionFactory.create()` with a properties file. Each transaction is started via `txManager.start()` and must be explicitly committed or rolled back.

**Complete Helper Class:**
```java
import com.scalar.db.api.*;
import com.scalar.db.service.TransactionFactory;

public class ScalarDbConnectionHelper {
    private static final String CONFIG_FILE = "scalardb.properties";
    private static DistributedTransactionManager txManager;

    public static synchronized DistributedTransactionManager getTransactionManager() throws Exception {
        if (txManager == null) {
            TransactionFactory factory = TransactionFactory.create(CONFIG_FILE);
            txManager = factory.getTransactionManager();
        }
        return txManager;
    }

    public static void close() {
        if (txManager != null) {
            txManager.close();
        }
    }
}
```

### Step 6.4: Update SQL Queries

{{#EACH_QUERY_CHANGE}}
#### Query Change: {{QUERY_NAME}}

**Original Oracle SQL:**
```sql
{{ORIGINAL_SQL}}
```

**ScalarDB SQL:**
```sql
{{SCALARDB_SQL}}
```

**Notes:** {{QUERY_NOTES}}
{{/EACH_QUERY_CHANGE}}

### Step 6.5: Replace Sequences

{{#IF_SEQUENCES}}
**Original Oracle Pattern:**
```sql
INSERT INTO {{TABLE_NAME}} (id, ...)
VALUES ({{SEQUENCE_NAME}}.NEXTVAL, ...);
```

**ScalarDB Pattern (UUID):**
```java
String id = UUID.randomUUID().toString();
Insert insert = Insert.newBuilder()
    .namespace("{{NAMESPACE}}")
    .table("{{TABLE_NAME}}")
    .partitionKey(Key.ofText("id", id))
    // ... set other columns
    .build();
tx.insert(insert);
```

**ScalarDB Pattern (Snowflake-like ID):**
```java
// Use a distributed ID generator
long id = IdGenerator.nextId();
Insert insert = Insert.newBuilder()
    .namespace("{{NAMESPACE}}")
    .table("{{TABLE_NAME}}")
    .partitionKey(Key.ofBigInt("id", id))
    // ... set other columns
    .build();
tx.insert(insert);
```
{{/IF_SEQUENCES}}

### Step 6.6: Implement Trigger Logic in Application

{{#IF_TRIGGERS}}
#### Trigger: {{TRIGGER_NAME}}

**Original Oracle Trigger:**
```sql
{{TRIGGER_DDL}}
```

**Java Implementation (Transaction API):**
```java
public void {{METHOD_NAME}}(DistributedTransaction tx, {{PARAMETERS}}) throws TransactionException {
    // Original operation
    {{ORIGINAL_OPERATION}}

    // Trigger logic (was in database, now in application)
    {{TRIGGER_LOGIC}}
}
```
{{/IF_TRIGGERS}}

### Step 6.7: Convert Stored Procedures

{{#IF_PROCEDURES}}
#### Procedure: {{PROCEDURE_NAME}}

**Original Oracle Procedure:**
```sql
{{PROCEDURE_DDL}}
```

**Java Method (Transaction API):**
```java
public {{RETURN_TYPE}} {{METHOD_NAME}}(DistributedTransaction tx, {{PARAMETERS}})
        throws TransactionException {
    {{JAVA_LOGIC}}

    return {{RETURN_VALUE}};
}
```
{{/IF_PROCEDURES}}

### Step 6.8: Implement Foreign Key Validation

**Application-Level FK Enforcement (Transaction API):**
```java
public void insertWithFKCheck(DistributedTransaction tx, {{PARAMETERS}}) throws TransactionException {
    // Check FK exists using Get
    Get fkCheck = Get.newBuilder()
        .namespace("{{NAMESPACE}}")
        .table("{{PARENT_TABLE}}")
        .partitionKey(Key.of{{TYPE}}("{{PARENT_PK}}", {{FK_VALUE}}))
        .build();

    Optional<Result> parent = tx.get(fkCheck);
    if (parent.isEmpty()) {
        throw new IllegalStateException("Foreign key constraint violation: " +
            "{{PARENT_TABLE}}.{{PARENT_PK}} = " + {{FK_VALUE}} + " does not exist");
    }

    // Proceed with insert
    Insert insert = Insert.newBuilder()
        .namespace("{{NAMESPACE}}")
        .table("{{CHILD_TABLE}}")
        // ... set partition key and values
        .build();
    tx.insert(insert);
}
```

---

## Phase 7: Testing & Validation

### Step 7.1: Schema Validation Checklist

- [ ] All tables created in ScalarDB
- [ ] Primary keys correctly mapped to partition-key/clustering-key
- [ ] Secondary indexes created where needed
- [ ] Column data types correctly mapped
- [ ] Coordinator table exists

### Step 7.2: Data Validation Checklist

- [ ] Row counts match between Oracle and ScalarDB
- [ ] Sample data spot-checks pass
- [ ] NULL values handled correctly
- [ ] Date/timestamp values preserved
- [ ] LOB data intact

### Step 7.3: CRUD Operations Testing

```java
// Test INSERT
@Test
public void testInsert() {
    // Insert record
    // Verify record exists
}

// Test SELECT
@Test
public void testSelect() {
    // Query record
    // Verify data correct
}

// Test UPDATE
@Test
public void testUpdate() {
    // Update record
    // Verify changes
}

// Test DELETE
@Test
public void testDelete() {
    // Delete record
    // Verify removal
}
```

### Step 7.4: Transaction Testing

```java
// Test commit
@Test
public void testTransactionCommit() {
    // Begin transaction
    // Make changes
    // Commit
    // Verify changes persisted
}

// Test rollback
@Test
public void testTransactionRollback() {
    // Begin transaction
    // Make changes
    // Rollback
    // Verify changes reverted
}

// Test isolation
@Test
public void testTransactionIsolation() {
    // Concurrent transactions
    // Verify isolation
}
```

### Step 7.5: Performance Testing

- [ ] Query response times within acceptable range
- [ ] Throughput meets requirements
- [ ] No deadlocks under concurrent load
- [ ] Memory usage stable

---

## Phase 8: Cutover

### Step 8.1: Pre-Cutover Checklist

- [ ] All tests passing
- [ ] Rollback plan documented
- [ ] Team notified
- [ ] Maintenance window scheduled

### Step 8.2: Cutover Steps

1. **Stop application write operations**
2. **Final data sync** (if using dual-write)
3. **Switch connection configuration**
4. **Verify application connects to ScalarDB**
5. **Run smoke tests**
6. **Enable write operations**
7. **Monitor closely**

### Step 8.3: Rollback Plan

If issues arise:

1. **Stop application**
2. **Revert connection configuration to Oracle**
3. **Restart application**
4. **Verify Oracle connectivity**
5. **Analyze failure logs**
6. **Plan remediation**

---

## Appendix A: Complete ScalarDB Schema JSON

```json
{{COMPLETE_SCHEMA_JSON}}
```

---

## Appendix B: Complete Import Schema JSON

```json
{{COMPLETE_IMPORT_SCHEMA_JSON}}
```

---

## Appendix C: ScalarDB Configuration File

```properties
{{COMPLETE_SCALARDB_PROPERTIES}}
```

---

## Appendix D: SQL Query Migration Reference

| Operation | Oracle SQL | ScalarDB SQL |
|-----------|------------|--------------|
{{SQL_MIGRATION_TABLE}}

---

## Appendix E: Testing Scripts

### Data Validation Script

```sql
-- Oracle vs ScalarDB comparison
{{VALIDATION_SCRIPT}}
```

### Smoke Test Script

```java
{{SMOKE_TEST_CODE}}
```

---

## References

### Primary Migration Path: ScalarDB Java Transaction API

| Reference | URL |
|-----------|-----|
| ScalarDB Java Transaction API | https://scalardb.scalar-labs.com/docs/latest/api-guide/ |
| ScalarDB SQL Grammar Reference | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/grammar/ |
| ScalarDB SQL Migration Guide | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/migration-guide |

### Schema and Data Types

| Reference | URL |
|-----------|-----|
| Schema Loader Guide | https://scalardb.scalar-labs.com/docs/latest/schema-loader/ |
| Data Type Mapping | https://scalardb.scalar-labs.com/docs/latest/schema-loader/#data-type-mapping-between-scalardb-and-other-databases |
| Schema Loader Import | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import |
| **Decoupling Transaction Metadata (RECOMMENDED)** | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import/#decoupling-transaction-metadata |
| Oracle Import Mapping | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import#data-type-mapping-from-jdbc-databases-to-scalardb |

### ScalarDB Analytics (for Complex Queries)

| Reference | URL |
|-----------|-----|
| ScalarDB Analytics Overview | https://scalardb.scalar-labs.com/docs/latest/scalardb-analytics/ |
| ScalarDB Analytics CLI | https://scalardb.scalar-labs.com/docs/latest/scalardb-analytics/reference-cli-command/ |

### General References

| Reference | URL |
|-----------|-----|
| ScalarDB Main Documentation | https://scalardb.scalar-labs.com/docs/latest/ |
| Supported Databases | https://scalardb.scalar-labs.com/docs/latest/requirements/#databases |
| Features Overview | https://scalardb.scalar-labs.com/docs/latest/features |

### Support

| Resource | URL |
|----------|-----|
| Scalar Labs Support | https://www.scalar-labs.com/support |
| GitHub Issues | https://github.com/scalar-labs/scalardb/issues |

---

*Migration guide generated by Migrate to ScalarDB Schema Skill*
*Input consumed from: ${ORACLE_SCHEMA_REPORT_MD}*
