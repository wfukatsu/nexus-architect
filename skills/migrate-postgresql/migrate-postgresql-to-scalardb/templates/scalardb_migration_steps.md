# ScalarDB Migration Steps Template (PostgreSQL)

This template is used to generate the **step-by-step migration guide** for PostgreSQL to ScalarDB migration. Replace all `{{PLACEHOLDER}}` tokens with actual values from the source PostgreSQL schema report and migration analysis.

**Input Source**: This guide consumes `postgresql_schema_report.md` from the configured output directory (analyze-postgresql-schema output).

---

# PostgreSQL to ScalarDB: Step-by-Step Migration Guide

**Generated**: {{TIMESTAMP}}
**Source Database**: {{DATABASE_NAME}}
**Source Schema**: {{SCHEMA_NAME}}
**Target**: ScalarDB 3.17+
**Primary Migration Path**: ScalarDB SQL (JDBC)

---

## Mandatory Reference Documentation

Before proceeding with migration, review these essential references:

| Reference | URL | Purpose |
|-----------|-----|---------|
| **ScalarDB Cluster SQL (JDBC) Getting Started** | https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/getting-started-with-scalardb-cluster-sql-jdbc/ | JDBC setup |
| **ScalarDB SQL JDBC Guide** | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/jdbc-guide/ | SQL JDBC connection |
| **ScalarDB SQL Grammar Reference** | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/grammar/ | SQL syntax |
| **Schema Loader Import** | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import | Table import |
| **JDBC Data Type Mapping** | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import#data-type-mapping-from-jdbc-databases-to-scalardb | **PostgreSQL type mapping** |
| **Decoupling Transaction Metadata** | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import/#decoupling-transaction-metadata | **RECOMMENDED** - Keep metadata separate |
| **Data Type Mapping** | https://scalardb.scalar-labs.com/docs/latest/schema-loader/#data-type-mapping-between-scalardb-and-other-databases | Type conversion |

---

## IMPORTANT: ScalarDB Core vs ScalarDB Cluster

> **ScalarDB SQL requires ScalarDB Cluster.** The SQL interface is NOT available with ScalarDB Core alone.

| Component | Capabilities | Use For |
|-----------|--------------|---------|
| **ScalarDB Core** | Schema Loader, Core API (Get/Put/Scan) | Schema creation, data import |
| **ScalarDB Cluster** | SQL interface (JDBC), distributed transactions | Application SQL access |

**Migration Workflow:**
1. **Phase 1-4**: Use ScalarDB Core (Schema Loader) for schema and data migration
2. **Phase 5**: Deploy ScalarDB Cluster for application SQL access
3. **Phase 6+**: Application connects to ScalarDB Cluster via SQL JDBC

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

### Critical Limitations (Different from PostgreSQL)

| Limitation | Description | Impact |
|------------|-------------|--------|
| **CTEs (WITH clause)** | ❌ NOT supported | Must rewrite as subqueries or application logic |
| **Cross-partition JOINs** | May trigger full scans | Performance degradation |
| **WHERE clause form** | Must be in DNF or CNF | Complex predicates may fail |
| **Subqueries** | ❌ NOT supported | Use sequential queries or Analytics |
| **Window functions** | ❌ NOT supported | Use ScalarDB Analytics |
| **ARRAY operations** | ❌ NOT supported | Normalize to child tables |
| **JSONB operators** | ❌ NOT supported | Application-level JSON parsing |
| **RETURNING clause** | ❌ NOT supported | Separate SELECT after INSERT/UPDATE |
| **UPSERT (ON CONFLICT)** | ❌ NOT supported | Read-check-write pattern |

### PostgreSQL vs ScalarDB Query Patterns

| PostgreSQL | ScalarDB Equivalent |
|------------|-------------------|
| `INSERT ... RETURNING *` | INSERT then SELECT |
| `INSERT ... ON CONFLICT DO UPDATE` | SELECT, then INSERT or UPDATE |
| `WITH cte AS (...) SELECT ...` | Separate queries or Analytics |
| `SELECT array_agg(col)` | Not supported - use separate table |
| `jsonb -> 'key'` | Application-level JSON parsing |

---

## Official Data Type Mapping (PostgreSQL → ScalarDB)

> **Reference**: https://scalardb.scalar-labs.com/docs/latest/schema-loader-import#data-type-mapping-from-jdbc-databases-to-scalardb

> ⚠️ **CRITICAL**: Only the data types listed below are officially supported. **Data types NOT listed in the official documentation are NOT SUPPORTED.** This includes any PostgreSQL extensions, custom types, or unlisted built-in types.

### Supported PostgreSQL Data Types (ONLY THESE 14 TYPES)

| PostgreSQL Type | ScalarDB Type | Notes |
|-----------------|---------------|-------|
| bigint | BIGINT | ⚠️ Range: -2^53 to 2^53 only |
| boolean | BOOLEAN | Direct mapping |
| bytea | BLOB | Max ~2GB (2^31-1 bytes) |
| character | TEXT | ⚠️ Size mapping warning |
| character varying | TEXT | ⚠️ Size mapping warning |
| date | DATE | Direct mapping |
| double precision | DOUBLE | Direct mapping |
| integer | INT | Direct mapping |
| real | FLOAT | Direct mapping |
| smallint | INT | ⚠️ Maps to larger type |
| text | TEXT | Direct mapping |
| time | TIME | Without timezone |
| timestamp | TIMESTAMP | Direct mapping |
| timestamp with time zone | TIMESTAMPTZ | Direct mapping |

### NOT Supported Data Types

> **Data types not listed above are NOT SUPPORTED.** The following are common data types that are explicitly NOT supported:

| Category | Unsupported Types | Migration Strategy |
|----------|-------------------|-------------------|
| Serial | bigserial, serial, smallserial | UUID or app-level ID |
| Numeric | numeric, money | DOUBLE or TEXT |
| Binary | bit | TEXT |
| Date/Time | interval, time with time zone | Application logic |
| JSON | json, jsonb | TEXT + app parsing |
| UUID | uuid | TEXT (36 chars) |
| XML | xml | TEXT |
| Network | inet, cidr, macaddr, macaddr8 | TEXT |
| Geometric | point, line, lseg, box, path, polygon, circle | Separate columns |
| Text Search | tsvector, tsquery | ScalarDB Vector Search |
| System | pg_lsn, pg_snapshot, txid_snapshot | Not applicable |
| Arrays | All array types (e.g., integer[], text[]) | Normalize to child table |
| Range Types | All range types (e.g., int4range, daterange) | Two boundary columns |
| ENUM Types | User-defined ENUM types | TEXT + app validation |
| Composite Types | User-defined composite types | Flatten to columns |
| Domain Types | User-defined domain types | Base type + app validation |
| Extension Types | PostGIS, hstore, ltree, citext, etc. | Convert to supported types |
| Any Other Types | Any unlisted PostgreSQL type | **Must convert to one of the 14 supported types** |

### Critical Warnings

> ⚠️ **BIGINT Range**: ScalarDB BIGINT range is -2^53 to 2^53. Data outside this range cannot be read.

> ⚠️ **Size Mapping**: For character, character varying, and smallint, ScalarDB may map to a larger type. Errors occur when writing values larger than the source type's limit.

> ⚠️ **BLOB Size**: Maximum BLOB size in ScalarDB is ~2GB (2^31-1 bytes).

---

## Migration Overview

This guide provides detailed, step-by-step instructions for migrating the **{{SCHEMA_NAME}}** PostgreSQL schema to ScalarDB.

### Migration Phases

| Phase | Description | Estimated Effort |
|-------|-------------|------------------|
| 1. Preparation | Environment setup, backup, prerequisites | {{PREP_EFFORT}} |
| 2. Schema Conversion | Convert PostgreSQL schema to ScalarDB format | {{SCHEMA_EFFORT}} |
| 3. ScalarDB Core Setup | Configure ScalarDB Core, create schemas | {{SETUP_EFFORT}} |
| 4. Data Migration | Import/migrate data to ScalarDB tables | {{DATA_EFFORT}} |
| 5. ScalarDB Cluster Deployment | Deploy ScalarDB Cluster for SQL access | {{CLUSTER_EFFORT}} |
| 5.5. ScalarDB Analytics (Conditional) | Deploy if CTEs/subqueries/window functions needed | {{ANALYTICS_EFFORT}} |
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

### Step 1.2: Backup PostgreSQL Database

```bash
# Full database backup
pg_dump -h {{POSTGRES_HOST}} -p {{POSTGRES_PORT}} -U {{POSTGRES_USER}} \
  -d {{POSTGRES_DATABASE}} -n {{SCHEMA_NAME}} \
  -F c -f {{SCHEMA_NAME}}_backup.dump

# Or plain SQL backup
pg_dump -h {{POSTGRES_HOST}} -p {{POSTGRES_PORT}} -U {{POSTGRES_USER}} \
  -d {{POSTGRES_DATABASE}} -n {{SCHEMA_NAME}} \
  -f {{SCHEMA_NAME}}_backup.sql
```

### Step 1.3: Document Current State

```sql
-- Record row counts for validation
SELECT
    schemaname,
    relname AS table_name,
    n_live_tup AS row_count
FROM pg_stat_user_tables
WHERE schemaname = '{{SCHEMA_NAME}}'
ORDER BY relname;

-- Export counts to CSV for later comparison
\COPY (SELECT ...) TO 'table_counts.csv' WITH CSV HEADER;
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

**Original PostgreSQL DDL:**
```sql
{{POSTGRES_DDL}}
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
| PostgreSQL Column | PostgreSQL Type | ScalarDB Column | ScalarDB Type |
|-------------------|-----------------|-----------------|---------------|
{{COLUMN_MAPPINGS}}

**Key Design Rationale:**
- Partition Key: {{PARTITION_KEY_RATIONALE}}
- Clustering Key: {{CLUSTERING_KEY_RATIONALE}}

{{/EACH_TABLE}}

### Step 2.3: Handle ENUM Types

{{#IF_ENUM_TYPES}}
#### Converting ENUM Type: {{ENUM_NAME}}

**Original Type:**
```sql
CREATE TYPE {{ENUM_NAME}} AS ENUM ({{ENUM_VALUES}});
```

**Migration Strategy:**
1. Change column type from ENUM to TEXT in ScalarDB schema
2. Add application-level validation

**Application Validation Example (Java):**
```java
public enum {{ENUM_CLASS_NAME}} {
    {{ENUM_JAVA_VALUES}};

    public static {{ENUM_CLASS_NAME}} fromString(String value) {
        return valueOf(value.toUpperCase());
    }

    public static boolean isValid(String value) {
        try {
            fromString(value);
            return true;
        } catch (IllegalArgumentException e) {
            return false;
        }
    }
}
```
{{/IF_ENUM_TYPES}}

### Step 2.4: Handle Array Columns (Normalization)

{{#IF_ARRAY_COLUMNS}}
#### Normalizing Array Column: {{TABLE_NAME}}.{{ARRAY_COLUMN}}

**Original Structure:**
```sql
CREATE TABLE {{TABLE_NAME}} (
    {{PK_COLUMN}} {{PK_TYPE}} PRIMARY KEY,
    {{ARRAY_COLUMN}} {{ELEMENT_TYPE}}[]
);
```

**ScalarDB Normalized Structure:**

Parent table:
```json
{
  "{{NAMESPACE}}.{{TABLE_NAME}}": {
    "transaction-metadata-decoupling": true,
    "partition-key": ["{{PK_COLUMN}}"],
    "columns": {
      "{{PK_COLUMN}}": "{{SCALARDB_PK_TYPE}}"
    }
  }
}
```

Child table (for array elements):
```json
{
  "{{NAMESPACE}}.{{TABLE_NAME}}_{{ARRAY_COLUMN}}": {
    "transaction-metadata-decoupling": true,
    "partition-key": ["parent_id"],
    "clustering-key": ["item_index ASC"],
    "columns": {
      "parent_id": "{{SCALARDB_PK_TYPE}}",
      "item_index": "INT",
      "value": "{{SCALARDB_ELEMENT_TYPE}}"
    }
  }
}
```

**Data Migration Query:**
```sql
-- Extract array elements with index
SELECT
    {{PK_COLUMN}} AS parent_id,
    ordinality AS item_index,
    elem AS value
FROM {{TABLE_NAME}},
     unnest({{ARRAY_COLUMN}}) WITH ORDINALITY AS elem;
```
{{/IF_ARRAY_COLUMNS}}

### Step 2.5: Handle Composite Types (Flattening)

{{#IF_COMPOSITE_TYPES}}
#### Flattening Composite Type: {{TYPE_NAME}}

**Original Type:**
```sql
CREATE TYPE {{TYPE_NAME}} AS (
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
{{/IF_COMPOSITE_TYPES}}

### Step 2.6: Handle SERIAL/IDENTITY Columns

{{#IF_SERIAL_COLUMNS}}
#### Replacing SERIAL Column: {{TABLE_NAME}}.{{SERIAL_COLUMN}}

**Original:**
```sql
CREATE TABLE {{TABLE_NAME}} (
    {{SERIAL_COLUMN}} SERIAL PRIMARY KEY,
    ...
);
```

**ScalarDB Schema:**
```json
{
  "{{NAMESPACE}}.{{TABLE_NAME}}": {
    "partition-key": ["{{SERIAL_COLUMN}}"],
    "columns": {
      "{{SERIAL_COLUMN}}": "BIGINT"
    }
  }
}
```

**ID Generation in Application:**
```java
// Option 1: UUID (recommended for distributed systems)
String id = UUID.randomUUID().toString();

// Option 2: Snowflake-like ID
long id = IdGenerator.nextId();

// Option 3: ULID (time-sortable)
String id = UlidCreator.getUlid().toString();
```
{{/IF_SERIAL_COLUMNS}}

---

## Phase 3: ScalarDB Setup

### Step 3.1: Create ScalarDB Configuration

Create file: `scalardb.properties`

```properties
# ScalarDB Configuration for PostgreSQL Backend
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:postgresql://{{POSTGRES_HOST}}:{{POSTGRES_PORT}}/{{POSTGRES_DATABASE}}
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
-- Connect to PostgreSQL and verify metadata tables
SELECT table_name
FROM information_schema.tables
WHERE table_schema = '{{SCHEMA_NAME}}'
ORDER BY table_name;

-- Check for ScalarDB metadata tables
SELECT table_name
FROM information_schema.tables
WHERE table_name LIKE '%_scalardb%'
ORDER BY table_name;
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

For tables requiring transformation (arrays, composite types):

{{#IF_TRANSFORMATION_NEEDED}}
#### Migrate {{TABLE_NAME}} Data

**Step 1: Export from PostgreSQL**
```sql
-- Create staging view with flattened/normalized data
CREATE OR REPLACE VIEW {{TABLE_NAME}}_export AS
SELECT
    {{EXPORT_COLUMNS}}
FROM {{TABLE_NAME}};

-- Export to CSV
\COPY {{TABLE_NAME}}_export TO '{{TABLE_NAME}}_data.csv' WITH CSV HEADER;
```

**Step 2: Insert into ScalarDB Table Using SQL**

> **IMPORTANT**: Use SQL INSERT statements for data migration. ScalarDB SQL JDBC provides full DML support.

**Using ScalarDB SQL JDBC (RECOMMENDED)**
```java
public class DataMigration {

    private Connection getConnection() throws SQLException {
        Connection connection = DriverManager.getConnection("jdbc:scalardb:scalardb-sql.properties");
        connection.setAutoCommit(false);  // Required for transactions
        return connection;
    }

    public void migrateData() throws SQLException {
        try (Connection conn = getConnection()) {
            String insertSql = """
                INSERT INTO {{NAMESPACE}}.{{TABLE_NAME}} (
                    {{COLUMN_LIST}}
                ) VALUES ({{PLACEHOLDERS}})
                """;

            try (PreparedStatement stmt = conn.prepareStatement(insertSql)) {
                // Set parameters for each row
                stmt.setLong(1, idValue);
                stmt.setString(2, nameValue);
                // ... set other columns

                stmt.executeUpdate();
            }

            conn.commit();  // Commit the transaction
        }
    }

    public void migrateBatch(List<DataRow> rows) throws SQLException {
        try (Connection conn = getConnection()) {
            String insertSql = """
                INSERT INTO {{NAMESPACE}}.{{TABLE_NAME}} (
                    {{COLUMN_LIST}}
                ) VALUES ({{PLACEHOLDERS}})
                """;

            try (PreparedStatement stmt = conn.prepareStatement(insertSql)) {
                int batchSize = 1000;
                int count = 0;

                for (DataRow row : rows) {
                    stmt.setLong(1, row.getId());
                    stmt.setString(2, row.getName());
                    // ... set other columns
                    stmt.addBatch();

                    if (++count % batchSize == 0) {
                        stmt.executeBatch();
                        conn.commit();
                    }
                }

                // Execute remaining
                stmt.executeBatch();
                conn.commit();
            }
        }
    }
}
```

**Migrating Array Data to Child Table:**
```java
public void migrateArrayData() throws SQLException {
    // First, read array data from PostgreSQL
    String selectSql = """
        SELECT {{PK_COLUMN}} AS parent_id,
               ordinality AS item_index,
               elem AS value
        FROM {{TABLE_NAME}}, unnest({{ARRAY_COLUMN}}) WITH ORDINALITY AS elem
        """;

    // Then insert into ScalarDB child table
    String insertSql = """
        INSERT INTO {{NAMESPACE}}.{{TABLE_NAME}}_{{ARRAY_COLUMN}}
        (parent_id, item_index, value) VALUES (?, ?, ?)
        """;

    // ... batch insert logic
}
```
{{/IF_TRANSFORMATION_NEEDED}}

### Step 4.4: Validate Data Migration

```sql
-- Compare row counts
SELECT '{{TABLE_NAME}}' as table_name, COUNT(*) as scalardb_count
FROM {{NAMESPACE}}.{{TABLE_NAME}};

-- Compare with original PostgreSQL count: {{ORIGINAL_COUNT}}
```

---

## Phase 5: Deploy ScalarDB Cluster (Required for SQL Access)

> **IMPORTANT**: ScalarDB SQL interface requires ScalarDB Cluster to be running.
> The JDBC SQL connection is NOT available with ScalarDB Core alone.

**Reference**: https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/getting-started-with-scalardb-cluster-sql-jdbc/

### Step 5.1: Deploy ScalarDB Cluster

ScalarDB Cluster can be deployed using:
- Kubernetes (recommended for production)
- Docker Compose (for development/testing)
- Standalone Java process

**Example: Docker Compose deployment**
```yaml
# docker-compose.yml
version: '3.8'
services:
  scalardb-cluster:
    image: ghcr.io/scalar-labs/scalardb-cluster-node:3.17.0
    ports:
      - "60053:60053"  # gRPC port
      - "60052:60052"  # SQL port
    volumes:
      - ./scalardb-cluster.properties:/scalardb-cluster/scalardb-cluster.properties
    environment:
      - SCALAR_DB_CLUSTER_MEMBERSHIP_KUBERNETES_ENABLED=false
```

**ScalarDB Cluster Configuration** (`scalardb-cluster.properties`):
```properties
# Backend database configuration
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:postgresql://{{POSTGRES_HOST}}:{{POSTGRES_PORT}}/{{POSTGRES_DATABASE}}
scalar.db.username={{SCALARDB_USER}}
scalar.db.password={{SCALARDB_PASSWORD}}

# Cluster settings
scalar.db.cluster.node.standalone_mode.enabled=true

# SQL settings
scalar.db.sql.enabled=true
```

### Step 5.2: Verify Cluster is Running

```bash
# Check cluster health
curl http://localhost:60053/health

# Or test SQL connection
java -jar scalardb-sql-cli.jar --config scalardb-sql.properties
```

---

## Phase 5.5: Deploy ScalarDB Analytics (If Required)

> **When Required**: Deploy ScalarDB Analytics if your schema uses CTEs, subqueries, window functions, or UNION/INTERSECT/EXCEPT operations.

{{#IF_ANALYTICS_REQUIRED}}

### Step 5.5.1: Determine Analytics Requirements

Based on schema analysis, ScalarDB Analytics is required for:

| Feature | Queries Affected |
|---------|-----------------|
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
        String upperSql = sql.toUpperCase();
        // Check for CTEs
        if (upperSql.contains("WITH ") && upperSql.contains(" AS ")) return true;
        // Check for subqueries (simple heuristic)
        if (upperSql.contains("(SELECT")) return true;
        // Check for window functions
        if (upperSql.matches(".*\\b(ROW_NUMBER|RANK|DENSE_RANK|LAG|LEAD|FIRST_VALUE|LAST_VALUE)\\b.*")) return true;
        // Check for set operations
        if (upperSql.matches(".*\\b(UNION|INTERSECT|EXCEPT)\\b.*")) return true;
        return false;
    }
}
```

{{/IF_ANALYTICS_REQUIRED}}

{{#IF_ANALYTICS_NOT_REQUIRED}}

### Analytics Not Required

Based on schema analysis, ScalarDB Analytics is **NOT required** for this migration.

Standard ScalarDB SQL supports all identified query patterns.

{{/IF_ANALYTICS_NOT_REQUIRED}}

---

## Phase 6: Application Migration

### Step 6.1: Update Dependencies

**Maven (pom.xml):**
```xml
<!-- Remove PostgreSQL driver if no longer needed directly -->
<!-- <dependency>
    <groupId>org.postgresql</groupId>
    <artifactId>postgresql</artifactId>
</dependency> -->

<!-- Add ScalarDB SQL JDBC -->
<dependency>
    <groupId>com.scalar-labs</groupId>
    <artifactId>scalardb-sql-jdbc</artifactId>
    <version>3.17.0</version>
</dependency>
```

**Gradle (build.gradle):**
```groovy
// implementation 'org.postgresql:postgresql:42.x.x'  // Remove if not needed
implementation 'com.scalar-labs:scalardb-sql-jdbc:3.17.0'
```

### Step 6.2: Create ScalarDB SQL Client Configuration

Create file: `scalardb-sql.properties`

```properties
# Connect to ScalarDB Cluster (NOT directly to PostgreSQL)
scalar.db.sql.connection_mode=cluster
scalar.db.sql.cluster_mode.contact_points=indirect:localhost
```

### Step 6.3: Update Connection Configuration

**Before (PostgreSQL JDBC):**
```java
String url = "jdbc:postgresql://{{POSTGRES_HOST}}:{{POSTGRES_PORT}}/{{POSTGRES_DATABASE}}";
Connection conn = DriverManager.getConnection(url, "{{USER}}", "{{PASSWORD}}");
conn.setAutoCommit(true);  // PostgreSQL default
```

**After (ScalarDB Cluster SQL JDBC):**
```java
// Connect via properties file (RECOMMENDED)
private Connection getConnection() throws SQLException {
    Connection connection = DriverManager.getConnection("jdbc:scalardb:scalardb-sql.properties");
    connection.setAutoCommit(false);  // Required for ScalarDB
    return connection;
}
```

> **Note**: AutoCommit must be disabled for ScalarDB transactions.

### Step 6.4: Update SQL Queries

#### Common PostgreSQL to ScalarDB Query Changes

**RETURNING clause:**
```sql
-- PostgreSQL
INSERT INTO users (name, email) VALUES ('John', 'john@example.com') RETURNING id;

-- ScalarDB: Two separate statements
INSERT INTO {{NAMESPACE}}.users (id, name, email) VALUES (?, ?, ?);
-- Then SELECT if needed
SELECT * FROM {{NAMESPACE}}.users WHERE id = ?;
```

**UPSERT (ON CONFLICT):**
```sql
-- PostgreSQL
INSERT INTO users (id, name) VALUES (1, 'John')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;

-- ScalarDB: Read-check-write pattern
```
```java
public void upsert(long id, String name) throws SQLException {
    try (Connection conn = getConnection()) {
        // Check if exists
        String selectSql = "SELECT id FROM {{NAMESPACE}}.users WHERE id = ?";
        try (PreparedStatement stmt = conn.prepareStatement(selectSql)) {
            stmt.setLong(1, id);
            ResultSet rs = stmt.executeQuery();

            if (rs.next()) {
                // Update
                String updateSql = "UPDATE {{NAMESPACE}}.users SET name = ? WHERE id = ?";
                try (PreparedStatement updateStmt = conn.prepareStatement(updateSql)) {
                    updateStmt.setString(1, name);
                    updateStmt.setLong(2, id);
                    updateStmt.executeUpdate();
                }
            } else {
                // Insert
                String insertSql = "INSERT INTO {{NAMESPACE}}.users (id, name) VALUES (?, ?)";
                try (PreparedStatement insertStmt = conn.prepareStatement(insertSql)) {
                    insertStmt.setLong(1, id);
                    insertStmt.setString(2, name);
                    insertStmt.executeUpdate();
                }
            }
        }
        conn.commit();
    }
}
```

**CTE (WITH clause):**
```sql
-- PostgreSQL
WITH recent_orders AS (
    SELECT * FROM orders WHERE created_at > NOW() - INTERVAL '7 days'
)
SELECT * FROM recent_orders WHERE status = 'pending';

-- ScalarDB: Use ScalarDB Analytics OR convert to application logic
```

**Array operations:**
```sql
-- PostgreSQL
SELECT * FROM users WHERE 'admin' = ANY(roles);

-- ScalarDB: Query normalized child table
SELECT DISTINCT u.*
FROM {{NAMESPACE}}.users u
JOIN {{NAMESPACE}}.users_roles ur ON u.id = ur.user_id
WHERE ur.role = 'admin';
```

**JSONB operators:**
```sql
-- PostgreSQL
SELECT * FROM products WHERE metadata->>'category' = 'electronics';

-- ScalarDB: Application-level JSON parsing
```
```java
public List<Product> findByCategory(String category) throws SQLException {
    List<Product> results = new ArrayList<>();
    String sql = "SELECT id, metadata FROM {{NAMESPACE}}.products";
    try (Connection conn = getConnection();
         Statement stmt = conn.createStatement();
         ResultSet rs = stmt.executeQuery(sql)) {
        while (rs.next()) {
            String metadata = rs.getString("metadata");
            JsonObject json = JsonParser.parseString(metadata).getAsJsonObject();
            if (category.equals(json.get("category").getAsString())) {
                results.add(new Product(rs.getLong("id"), metadata));
            }
        }
        conn.commit();
    }
    return results;
}
```

### Step 6.5: Replace Sequences

{{#IF_SEQUENCES}}
**Original PostgreSQL Pattern:**
```sql
INSERT INTO {{TABLE_NAME}} (id, name)
VALUES (nextval('{{SEQUENCE_NAME}}'), 'John');
```

**ScalarDB Pattern (UUID):**
```java
String id = UUID.randomUUID().toString();
String sql = "INSERT INTO {{NAMESPACE}}.{{TABLE_NAME}} (id, name) VALUES (?, ?)";
PreparedStatement pstmt = conn.prepareStatement(sql);
pstmt.setString(1, id);
pstmt.setString(2, "John");
```
{{/IF_SEQUENCES}}

### Step 6.6: Implement Trigger Logic in Application

{{#IF_TRIGGERS}}
#### Trigger: {{TRIGGER_NAME}}

**Original PostgreSQL Trigger:**
```sql
{{TRIGGER_DDL}}
```

**Java Implementation:**
```java
public void {{METHOD_NAME}}({{PARAMETERS}}) throws SQLException {
    try (Connection conn = getConnection()) {
        // Original operation
        {{ORIGINAL_OPERATION}}

        // Trigger logic (was in database)
        {{TRIGGER_LOGIC}}

        conn.commit();
    }
}
```
{{/IF_TRIGGERS}}

### Step 6.7: Convert Functions to Application Code

{{#IF_FUNCTIONS}}
#### Function: {{FUNCTION_NAME}}

**Original PostgreSQL Function:**
```sql
{{FUNCTION_DDL}}
```

**Java Method:**
```java
public {{RETURN_TYPE}} {{METHOD_NAME}}({{PARAMETERS}}) throws SQLException {
    try (Connection conn = getConnection()) {
        {{JAVA_LOGIC}}

        conn.commit();
        return {{RETURN_VALUE}};
    }
}
```
{{/IF_FUNCTIONS}}

---

## Phase 7: Testing & Validation

### Step 7.1: Schema Validation Checklist

- [ ] All tables created in ScalarDB
- [ ] Primary keys correctly mapped to partition-key/clustering-key
- [ ] Secondary indexes created where needed
- [ ] Column data types correctly mapped
- [ ] Coordinator table exists
- [ ] Array columns normalized to child tables
- [ ] ENUM columns converted to TEXT

### Step 7.2: Data Validation Checklist

- [ ] Row counts match between PostgreSQL and ScalarDB
- [ ] Sample data spot-checks pass
- [ ] NULL values handled correctly
- [ ] Date/timestamp values preserved
- [ ] BYTEA data intact
- [ ] JSON data preserved (as TEXT)

### Step 7.3: Query Validation

```java
// Test basic CRUD
@Test
public void testInsert() { ... }

@Test
public void testSelect() { ... }

@Test
public void testUpdate() { ... }

@Test
public void testDelete() { ... }

// Test transaction semantics
@Test
public void testTransactionCommit() { ... }

@Test
public void testTransactionRollback() { ... }
```

### Step 7.4: Performance Testing

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
2. **Revert connection configuration to PostgreSQL**
3. **Restart application**
4. **Verify PostgreSQL connectivity**
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

| Operation | PostgreSQL SQL | ScalarDB SQL |
|-----------|---------------|--------------|
{{SQL_MIGRATION_TABLE}}

---

## References

### Primary Migration Path: ScalarDB SQL (MANDATORY)

| Reference | URL |
|-----------|-----|
| ScalarDB Cluster SQL (JDBC) Getting Started | https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/getting-started-with-scalardb-cluster-sql-jdbc/ |
| ScalarDB SQL Grammar Reference | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/grammar/ |
| ScalarDB SQL Migration Guide | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/migration-guide |

### Schema and Data Types

| Reference | URL |
|-----------|-----|
| Schema Loader Guide | https://scalardb.scalar-labs.com/docs/latest/schema-loader/ |
| Data Type Mapping | https://scalardb.scalar-labs.com/docs/latest/schema-loader/#data-type-mapping-between-scalardb-and-other-databases |
| Schema Loader Import | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import |
| **Decoupling Transaction Metadata (RECOMMENDED)** | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import/#decoupling-transaction-metadata |

### ScalarDB Analytics (for Complex Queries)

| Reference | URL |
|-----------|-----|
| ScalarDB Analytics Overview | https://scalardb.scalar-labs.com/docs/latest/scalardb-analytics/ |
| ScalarDB Analytics CLI | https://scalardb.scalar-labs.com/docs/latest/scalardb-analytics/reference-cli-command/ |

### Support

| Resource | URL |
|----------|-----|
| Scalar Labs Support | https://www.scalar-labs.com/support |
| GitHub Issues | https://github.com/scalar-labs/scalardb/issues |

---

*Migration guide generated by Migrate PostgreSQL to ScalarDB Schema Skill*
*Input consumed from: ${POSTGRESQL_SCHEMA_REPORT_MD}*
