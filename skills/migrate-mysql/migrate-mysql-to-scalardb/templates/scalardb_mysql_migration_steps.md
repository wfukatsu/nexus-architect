# ScalarDB Migration Steps Template (MySQL)

This template is used to generate the **step-by-step migration guide** for MySQL to ScalarDB migration. Replace all `{{PLACEHOLDER}}` tokens with actual values from the source MySQL schema report and migration analysis.

**Input Source**: This guide consumes `mysql_schema_report.md` from the configured output directory (analyze-mysql-schema output).

---

# MySQL to ScalarDB: Step-by-Step Migration Guide

**Generated**: {{TIMESTAMP}}
**Source Database**: {{DATABASE_NAME}}
**MySQL Version**: {{MYSQL_VERSION}}
**Target**: ScalarDB 3.17+
**Primary Migration Path**: ScalarDB SQL (JDBC)

---

## Mandatory Reference Documentation

Before proceeding with migration, review these essential references:

| Reference | URL | Purpose |
|-----------|-----|---------|
| **MySQL Schema Import** | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import/?databases=MySQL_MariaDB_TiDB | MySQL-specific import |
| **ScalarDB Cluster SQL (JDBC) Getting Started** | https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/getting-started-with-scalardb-cluster-sql-jdbc/ | JDBC setup |
| **ScalarDB SQL JDBC Guide** | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/jdbc-guide/ | SQL JDBC connection |
| **ScalarDB SQL Grammar Reference** | https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/grammar/ | SQL syntax |
| **Schema Loader Import** | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import | Table import |
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

### Critical Limitations (Different from MySQL)

| Limitation | Description | Impact |
|------------|-------------|--------|
| **Cross-partition JOINs** | JOINs across different partition keys may trigger full scans | Performance degradation |
| **Multi-table JOINs** | Not optimized like traditional RDBMS | Use ScalarDB Analytics for complex JOINs |
| **WHERE clause form** | Must be in DNF (OR-of-ANDs) or CNF (AND-of-ORs) | Complex predicates may fail |
| **Subqueries** | ❌ NOT supported | Use sequential queries or Analytics |
| **UNION/INTERSECT/EXCEPT** | ❌ NOT supported | Multiple queries + application merge |
| **Window functions** | ❌ NOT supported | Use ScalarDB Analytics |
| **Cross-partition UPDATE/DELETE** | Requires explicit enable; impacts performance | Include partition key in WHERE |
| **AUTO_INCREMENT** | ❌ NOT supported | Application-level ID generation |
| **ENUM/SET** | ❌ NOT supported | Convert to TEXT + app validation |
| **JSON functions** | ❌ NOT supported | Application-level JSON parsing |
| **Stored procedures** | ❌ NOT supported | Convert to application code |
| **Triggers** | ❌ NOT supported | Convert to application code |
| **Events** | ❌ NOT supported | External scheduler |

### MySQL vs ScalarDB Query Patterns

| MySQL | ScalarDB Equivalent |
|-------|-------------------|
| `INSERT ... ON DUPLICATE KEY UPDATE` | Read-check-write pattern |
| `REPLACE INTO` | DELETE then INSERT |
| `LAST_INSERT_ID()` | Application-generated ID |
| `SELECT ... FOR UPDATE` | ScalarDB handles locking |
| `GROUP_CONCAT()` | Application-level aggregation |
| `JSON_EXTRACT(col, '$.key')` | Application-level JSON parsing |

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

## Official Data Type Mapping (MySQL → ScalarDB)

> **Reference**: https://scalardb.scalar-labs.com/docs/latest/schema-loader-import#data-type-mapping-from-jdbc-databases-to-scalardb

> ⚠️ **CRITICAL**: Only the data types listed below are officially supported. **Data types NOT listed in the official documentation are NOT SUPPORTED.** This includes any MySQL extensions, custom types, or unlisted built-in types.

### Supported MySQL Data Types

| MySQL Type | ScalarDB Type | Notes |
|------------|---------------|-------|
| bigint | BIGINT | ⚠️ Range: -2^53 to 2^53 only |
| int, integer | INT | Direct mapping |
| mediumint | INT | Maps to larger type |
| smallint | INT | Maps to larger type |
| tinyint | INT | Maps to larger type |
| float | FLOAT | Direct mapping |
| double | DOUBLE | Direct mapping |
| boolean, bool | BOOLEAN | Direct mapping |
| char | TEXT | Fixed-length to TEXT |
| varchar | TEXT | Variable-length to TEXT |
| text, tinytext, mediumtext, longtext | TEXT | Direct mapping |
| binary, varbinary | BLOB | Direct mapping |
| blob, tinyblob, mediumblob, longblob | BLOB | Max ~2GB (2^31-1 bytes) |
| date | DATE | Direct mapping |
| time | TIME | Without timezone |
| datetime | TIMESTAMP | Direct mapping |
| timestamp | TIMESTAMPTZ | With timezone awareness |

### NOT Supported Data Types

> **Data types not listed above are NOT SUPPORTED.** The following are common data types that are explicitly NOT supported:

| Category | Unsupported Types | Migration Strategy |
|----------|-------------------|-------------------|
| Numeric | decimal, numeric | DOUBLE or TEXT |
| Numeric | bit | TEXT |
| Serial | auto_increment | UUID or app-level ID |
| Temporal | year | INT |
| JSON | json | TEXT + app parsing |
| Spatial | geometry, point, linestring, polygon, etc. | Separate columns or TEXT |
| ENUM | enum | TEXT + app validation |
| SET | set | TEXT or normalize to table |
| Custom | User-defined types | Flatten to columns |
| Any Other | Any unlisted MySQL type | **Must convert to supported types** |

### Critical Warnings

> ⚠️ **BIGINT Range**: ScalarDB BIGINT range is -2^53 to 2^53. Data outside this range cannot be read.

> ⚠️ **DECIMAL Precision**: DECIMAL/NUMERIC types lose precision when converted to DOUBLE. Use TEXT for exact precision.

> ⚠️ **BLOB Size**: Maximum BLOB size in ScalarDB is ~2GB (2^31-1 bytes).

---

## Migration Overview

This guide provides detailed, step-by-step instructions for migrating the **{{DATABASE_NAME}}** MySQL database to ScalarDB.

### Migration Phases

| Phase | Description | Estimated Effort |
|-------|-------------|------------------|
| 1. Preparation | Environment setup, backup, prerequisites | {{PREP_EFFORT}} |
| 2. Schema Conversion | Convert MySQL schema to ScalarDB format | {{SCHEMA_EFFORT}} |
| 3. ScalarDB Core Setup | Configure ScalarDB Core, create schemas | {{SETUP_EFFORT}} |
| 4. Data Migration | Import/migrate data to ScalarDB tables | {{DATA_EFFORT}} |
| 5. ScalarDB Cluster Deployment | Deploy ScalarDB Cluster for SQL access | {{CLUSTER_EFFORT}} |
| 5.5. ScalarDB Analytics (Conditional) | Deploy if subqueries/window functions needed | {{ANALYTICS_EFFORT}} |
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

### Step 1.2: Backup MySQL Database

```bash
# Full backup with all objects
mysqldump -h {{MYSQL_HOST}} -u {{MYSQL_USER}} -p \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  {{DATABASE_NAME}} > {{DATABASE_NAME}}_backup.sql

# Or compressed backup
mysqldump -h {{MYSQL_HOST}} -u {{MYSQL_USER}} -p \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  {{DATABASE_NAME}} | gzip > {{DATABASE_NAME}}_backup.sql.gz
```

### Step 1.3: Document Current State

```sql
-- Record row counts for validation
SELECT TABLE_NAME, TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = '{{DATABASE_NAME}}'
ORDER BY TABLE_NAME;

-- Export to CSV for later comparison
SELECT TABLE_NAME, TABLE_ROWS
INTO OUTFILE '/tmp/table_counts.csv'
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = '{{DATABASE_NAME}}';
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

**Original MySQL DDL:**
```sql
{{MYSQL_DDL}}
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
| MySQL Column | MySQL Type | ScalarDB Column | ScalarDB Type |
|--------------|------------|-----------------|---------------|
{{COLUMN_MAPPINGS}}

**Key Design Rationale:**
- Partition Key: {{PARTITION_KEY_RATIONALE}}
- Clustering Key: {{CLUSTERING_KEY_RATIONALE}}

{{/EACH_TABLE}}

### Step 2.3: Handle Unsupported Data Types

{{#IF_DECIMAL_COLUMNS}}
#### DECIMAL/NUMERIC Columns

| Table Name | Column Name | MySQL Type | Action |
|------------|-------------|------------|--------|
{{DECIMAL_COLUMNS_TABLE}}

**Option 1**: Convert to DOUBLE (accept precision loss)
**Option 2**: Convert to TEXT (preserve exact value)

```sql
-- Example: Convert DECIMAL to DOUBLE
ALTER TABLE {{TABLE_NAME}} MODIFY {{COLUMN_NAME}} DOUBLE;

-- Or convert to TEXT
ALTER TABLE {{TABLE_NAME}} MODIFY {{COLUMN_NAME}} VARCHAR(50);
```
{{/IF_DECIMAL_COLUMNS}}

{{#IF_JSON_COLUMNS}}
#### JSON Columns

| Table Name | Column Name | Action |
|------------|-------------|--------|
{{JSON_COLUMNS_TABLE}}

```sql
-- Convert JSON to TEXT
ALTER TABLE {{TABLE_NAME}} MODIFY {{COLUMN_NAME}} LONGTEXT;
```

**Application Change**: Parse JSON using application library (Jackson, Gson, etc.)
{{/IF_JSON_COLUMNS}}

### Step 2.4: Handle ENUM/SET Types

{{#IF_ENUM_SET_COLUMNS}}
#### Converting ENUM/SET Columns

| Table Name | Column Name | Type | Values | Action |
|------------|-------------|------|--------|--------|
{{ENUM_SET_COLUMNS_TABLE}}

**Migration Strategy:**
1. Change column type from ENUM/SET to TEXT in ScalarDB schema
2. Add application-level validation

```sql
-- Convert ENUM to VARCHAR
ALTER TABLE {{TABLE_NAME}} MODIFY {{COLUMN_NAME}} VARCHAR(50);
```

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
{{/IF_ENUM_SET_COLUMNS}}

### Step 2.5: Handle AUTO_INCREMENT Columns

{{#IF_AUTO_INCREMENT}}
#### Replacing AUTO_INCREMENT: {{TABLE_NAME}}.{{AUTO_INCREMENT_COLUMN}}

**Original:**
```sql
CREATE TABLE {{TABLE_NAME}} (
    {{AUTO_INCREMENT_COLUMN}} INT AUTO_INCREMENT PRIMARY KEY,
    ...
);
```

**ScalarDB Schema:**
```json
{
  "{{NAMESPACE}}.{{TABLE_NAME}}": {
    "partition-key": ["{{AUTO_INCREMENT_COLUMN}}"],
    "columns": {
      "{{AUTO_INCREMENT_COLUMN}}": "BIGINT"
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
{{/IF_AUTO_INCREMENT}}

---

## Phase 3: ScalarDB Setup

### Step 3.1: Create ScalarDB Configuration

Create file: `scalardb.properties`

```properties
# ScalarDB Configuration for MySQL Backend
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:mysql://{{MYSQL_HOST}}:{{MYSQL_PORT}}/{{DATABASE_NAME}}
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
-- Connect to MySQL and verify metadata tables
SELECT table_name
FROM information_schema.tables
WHERE table_schema = '{{DATABASE_NAME}}'
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

For tables requiring transformation (ENUM, JSON, etc.):

{{#IF_TRANSFORMATION_NEEDED}}
#### Migrate {{TABLE_NAME}} Data

**Step 1: Export from MySQL**
```sql
-- Create staging view with transformed data
CREATE OR REPLACE VIEW {{TABLE_NAME}}_export AS
SELECT
    {{EXPORT_COLUMNS}}
FROM {{TABLE_NAME}};

-- Export to CSV
SELECT * FROM {{TABLE_NAME}}_export
INTO OUTFILE '/tmp/{{TABLE_NAME}}_data.csv'
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n';
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
{{/IF_TRANSFORMATION_NEEDED}}

### Step 4.4: Validate Data Migration

```sql
-- Compare row counts
SELECT '{{TABLE_NAME}}' as table_name, COUNT(*) as scalardb_count
FROM {{NAMESPACE}}.{{TABLE_NAME}};

-- Compare with original MySQL count: {{ORIGINAL_COUNT}}
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
scalar.db.contact_points=jdbc:mysql://{{MYSQL_HOST}}:{{MYSQL_PORT}}/{{DATABASE_NAME}}
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

> **When Required**: Deploy ScalarDB Analytics if your schema uses subqueries, window functions, complex multi-table JOINs, or UNION/INTERSECT/EXCEPT operations.

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

**Docker Compose (add to existing deployment):**
```yaml
  scalardb-analytics:
    image: ghcr.io/scalar-labs/scalardb-analytics:3.17.0
    ports:
      - "60054:60054"
    volumes:
      - ./scalardb-analytics.properties:/scalardb-analytics/scalardb-analytics.properties
```

**Analytics Configuration** (`scalardb-analytics.properties`):
```properties
# Connect to ScalarDB Cluster
scalar.db.analytics.cluster.contact_points=localhost:60053
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
        String upperSql = sql.toUpperCase();
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

### Architecture with Analytics

```
Application Layer
       │
       ├──► ScalarDB SQL (JDBC)
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

## Phase 6: Application Migration

### Step 6.1: Update Dependencies

**Maven (pom.xml):**
```xml
<!-- Remove MySQL driver if no longer needed directly -->
<!-- <dependency>
    <groupId>mysql</groupId>
    <artifactId>mysql-connector-java</artifactId>
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
// implementation 'mysql:mysql-connector-java:8.x.x'  // Remove if not needed
implementation 'com.scalar-labs:scalardb-sql-jdbc:3.17.0'
```

### Step 6.2: Create ScalarDB SQL Client Configuration

Create file: `scalardb-sql.properties`

```properties
# Connect to ScalarDB Cluster (NOT directly to MySQL)
scalar.db.sql.connection_mode=cluster
scalar.db.sql.cluster_mode.contact_points=indirect:localhost
```

### Step 6.3: Update Connection Configuration

**Before (MySQL JDBC):**
```java
String url = "jdbc:mysql://{{MYSQL_HOST}}:{{MYSQL_PORT}}/{{DATABASE_NAME}}";
Connection conn = DriverManager.getConnection(url, "{{USER}}", "{{PASSWORD}}");
conn.setAutoCommit(true);  // MySQL default
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

**Reference**: https://github.com/scalar-labs/scalardb-samples/tree/main/scalardb-sql-jdbc-sample

**Complete Helper Method:**
```java
public class ScalarDbConnectionHelper {
    private static final String PROPERTIES_FILE = "scalardb-sql.properties";

    public static Connection getConnection() throws SQLException {
        Connection connection = DriverManager.getConnection("jdbc:scalardb:" + PROPERTIES_FILE);
        connection.setAutoCommit(false);  // Required for ScalarDB transactions
        return connection;
    }
}
```

### Step 6.4: Update SQL Queries

#### Common MySQL to ScalarDB Query Changes

**INSERT ... ON DUPLICATE KEY UPDATE:**
```sql
-- MySQL
INSERT INTO users (id, name, email) VALUES (1, 'John', 'john@example.com')
ON DUPLICATE KEY UPDATE name = VALUES(name), email = VALUES(email);

-- ScalarDB: Read-check-write pattern
```
```java
public void upsert(long id, String name, String email) throws SQLException {
    try (Connection conn = getConnection()) {
        // Check if exists
        String selectSql = "SELECT id FROM {{NAMESPACE}}.users WHERE id = ?";
        try (PreparedStatement stmt = conn.prepareStatement(selectSql)) {
            stmt.setLong(1, id);
            ResultSet rs = stmt.executeQuery();

            if (rs.next()) {
                // Update
                String updateSql = "UPDATE {{NAMESPACE}}.users SET name = ?, email = ? WHERE id = ?";
                try (PreparedStatement updateStmt = conn.prepareStatement(updateSql)) {
                    updateStmt.setString(1, name);
                    updateStmt.setString(2, email);
                    updateStmt.setLong(3, id);
                    updateStmt.executeUpdate();
                }
            } else {
                // Insert
                String insertSql = "INSERT INTO {{NAMESPACE}}.users (id, name, email) VALUES (?, ?, ?)";
                try (PreparedStatement insertStmt = conn.prepareStatement(insertSql)) {
                    insertStmt.setLong(1, id);
                    insertStmt.setString(2, name);
                    insertStmt.setString(3, email);
                    insertStmt.executeUpdate();
                }
            }
        }
        conn.commit();
    }
}
```

**REPLACE INTO:**
```sql
-- MySQL
REPLACE INTO users (id, name) VALUES (1, 'John');

-- ScalarDB: DELETE then INSERT (within same transaction)
```
```java
public void replaceInto(long id, String name) throws SQLException {
    try (Connection conn = getConnection()) {
        // Delete if exists
        String deleteSql = "DELETE FROM {{NAMESPACE}}.users WHERE id = ?";
        try (PreparedStatement deleteStmt = conn.prepareStatement(deleteSql)) {
            deleteStmt.setLong(1, id);
            deleteStmt.executeUpdate();
        }

        // Insert
        String insertSql = "INSERT INTO {{NAMESPACE}}.users (id, name) VALUES (?, ?)";
        try (PreparedStatement insertStmt = conn.prepareStatement(insertSql)) {
            insertStmt.setLong(1, id);
            insertStmt.setString(2, name);
            insertStmt.executeUpdate();
        }

        conn.commit();
    }
}
```

**LAST_INSERT_ID():**
```sql
-- MySQL
INSERT INTO users (name) VALUES ('John');
SELECT LAST_INSERT_ID();

-- ScalarDB: Generate ID before insert
```
```java
public long insertUser(String name) throws SQLException {
    long id = IdGenerator.nextId();  // Generate ID first

    try (Connection conn = getConnection()) {
        String insertSql = "INSERT INTO {{NAMESPACE}}.users (id, name) VALUES (?, ?)";
        try (PreparedStatement stmt = conn.prepareStatement(insertSql)) {
            stmt.setLong(1, id);
            stmt.setString(2, name);
            stmt.executeUpdate();
        }
        conn.commit();
    }

    return id;  // Return the generated ID
}
```

**JSON functions:**
```sql
-- MySQL
SELECT * FROM products WHERE JSON_EXTRACT(metadata, '$.category') = 'electronics';

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

**GROUP_CONCAT:**
```sql
-- MySQL
SELECT user_id, GROUP_CONCAT(role) as roles FROM user_roles GROUP BY user_id;

-- ScalarDB: Application-level aggregation
```
```java
public Map<Long, String> getUserRoles() throws SQLException {
    Map<Long, List<String>> roleMap = new HashMap<>();
    String sql = "SELECT user_id, role FROM {{NAMESPACE}}.user_roles ORDER BY user_id";

    try (Connection conn = getConnection();
         Statement stmt = conn.createStatement();
         ResultSet rs = stmt.executeQuery(sql)) {
        while (rs.next()) {
            long userId = rs.getLong("user_id");
            String role = rs.getString("role");
            roleMap.computeIfAbsent(userId, k -> new ArrayList<>()).add(role);
        }
        conn.commit();
    }

    // Convert to comma-separated string
    Map<Long, String> result = new HashMap<>();
    for (Map.Entry<Long, List<String>> entry : roleMap.entrySet()) {
        result.put(entry.getKey(), String.join(",", entry.getValue()));
    }
    return result;
}
```

### Step 6.5: Replace AUTO_INCREMENT

{{#IF_AUTO_INCREMENT}}
**Original MySQL Pattern:**
```sql
INSERT INTO {{TABLE_NAME}} (name, ...) VALUES ('value', ...);
-- id auto-generated via AUTO_INCREMENT
```

**ScalarDB Pattern (UUID):**
```java
String id = UUID.randomUUID().toString();
String sql = "INSERT INTO {{NAMESPACE}}.{{TABLE_NAME}} (id, name, ...) VALUES (?, ?, ...)";
PreparedStatement pstmt = conn.prepareStatement(sql);
pstmt.setString(1, id);
pstmt.setString(2, "value");
```

**ScalarDB Pattern (Snowflake-like ID):**
```java
long id = IdGenerator.nextId();
String sql = "INSERT INTO {{NAMESPACE}}.{{TABLE_NAME}} (id, name, ...) VALUES (?, ?, ...)";
PreparedStatement pstmt = conn.prepareStatement(sql);
pstmt.setLong(1, id);
```
{{/IF_AUTO_INCREMENT}}

### Step 6.6: Implement Trigger Logic in Application

{{#IF_TRIGGERS}}
#### Trigger: {{TRIGGER_NAME}}

**Original MySQL Trigger:**
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

### Step 6.7: Convert Stored Procedures to Application Code

{{#IF_PROCEDURES}}
#### Procedure: {{PROCEDURE_NAME}}

**Original MySQL Procedure:**
```sql
{{PROCEDURE_DDL}}
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
{{/IF_PROCEDURES}}

### Step 6.8: Implement Foreign Key Validation

**Application-Level FK Enforcement:**
```java
public void insertWithFKCheck({{PARAMETERS}}) throws SQLException {
    try (Connection conn = getConnection()) {
        // Check FK exists
        String checkSql = "SELECT 1 FROM {{PARENT_TABLE}} WHERE {{PARENT_PK}} = ?";
        PreparedStatement checkStmt = conn.prepareStatement(checkSql);
        checkStmt.set{{TYPE}}(1, {{FK_VALUE}});
        ResultSet rs = checkStmt.executeQuery();

        if (!rs.next()) {
            throw new SQLException("Foreign key constraint violation: " +
                "{{PARENT_TABLE}}.{{PARENT_PK}} = " + {{FK_VALUE}} + " does not exist");
        }

        // Proceed with insert
        String insertSql = "INSERT INTO {{CHILD_TABLE}} (...) VALUES (...)";
        // ...

        conn.commit();
    }
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
- [ ] ENUM columns converted to TEXT
- [ ] AUTO_INCREMENT replaced with application ID generation

### Step 7.2: Data Validation Checklist

- [ ] Row counts match between MySQL and ScalarDB
- [ ] Sample data spot-checks pass
- [ ] NULL values handled correctly
- [ ] Date/timestamp values preserved
- [ ] BLOB data intact
- [ ] JSON data preserved (as TEXT)

### Step 7.3: Query Validation

```java
// Test basic CRUD
@Test
public void testInsert() {
    // Insert record
    // Verify record exists
}

@Test
public void testSelect() {
    // Query record
    // Verify data correct
}

@Test
public void testUpdate() {
    // Update record
    // Verify changes
}

@Test
public void testDelete() {
    // Delete record
    // Verify removal
}

// Test transaction semantics
@Test
public void testTransactionCommit() {
    // Begin transaction
    // Make changes
    // Commit
    // Verify changes persisted
}

@Test
public void testTransactionRollback() {
    // Begin transaction
    // Make changes
    // Rollback
    // Verify changes reverted
}

@Test
public void testTransactionIsolation() {
    // Concurrent transactions
    // Verify isolation
}
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
2. **Revert connection configuration to MySQL**
3. **Restart application**
4. **Verify MySQL connectivity**
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

| Operation | MySQL SQL | ScalarDB SQL |
|-----------|-----------|--------------|
| Simple SELECT | `SELECT * FROM users` | `SELECT * FROM namespace.users` |
| INSERT | `INSERT INTO users (id, name) VALUES (1, 'John')` | `INSERT INTO namespace.users (id, name) VALUES (1, 'John')` |
| UPDATE | `UPDATE users SET name = 'Jane' WHERE id = 1` | `UPDATE namespace.users SET name = 'Jane' WHERE id = 1` |
| DELETE | `DELETE FROM users WHERE id = 1` | `DELETE FROM namespace.users WHERE id = 1` |
| JOIN | `SELECT * FROM a JOIN b ON a.id = b.a_id` | `SELECT * FROM ns.a JOIN ns.b ON a.id = b.a_id` |
| COUNT | `SELECT COUNT(*) FROM users` | `SELECT COUNT(*) FROM namespace.users` |
| GROUP BY | `SELECT status, COUNT(*) FROM orders GROUP BY status` | `SELECT status, COUNT(*) FROM namespace.orders GROUP BY status` |
| LIMIT | `SELECT * FROM users LIMIT 10` | `SELECT * FROM namespace.users LIMIT 10` |
| AUTO_INCREMENT | `INSERT INTO users (name) VALUES ('John')` | Generate ID in app, then INSERT |
| ON DUPLICATE KEY | `INSERT ... ON DUPLICATE KEY UPDATE` | Check-then-insert/update pattern |
| REPLACE INTO | `REPLACE INTO users ...` | DELETE then INSERT |
| LAST_INSERT_ID | `SELECT LAST_INSERT_ID()` | Track ID in application |

---

## Appendix E: Testing Scripts

### Data Validation Script

```sql
-- MySQL vs ScalarDB row count comparison
-- Run on MySQL:
SELECT TABLE_NAME, TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = '{{DATABASE_NAME}}'
ORDER BY TABLE_NAME;

-- Run on ScalarDB (via JDBC):
SELECT '{{TABLE_NAME}}' as table_name, COUNT(*) as row_count
FROM {{NAMESPACE}}.{{TABLE_NAME}};
```

### Smoke Test Script

```java
public class SmokeTest {

    private Connection getConnection() throws SQLException {
        Connection conn = DriverManager.getConnection("jdbc:scalardb:scalardb-sql.properties");
        conn.setAutoCommit(false);
        return conn;
    }

    @Test
    public void testConnectionAndBasicQuery() throws SQLException {
        try (Connection conn = getConnection()) {
            Statement stmt = conn.createStatement();
            ResultSet rs = stmt.executeQuery("SELECT 1");
            assertTrue(rs.next());
            assertEquals(1, rs.getInt(1));
            conn.commit();
        }
    }

    @Test
    public void testTableAccess() throws SQLException {
        try (Connection conn = getConnection()) {
            Statement stmt = conn.createStatement();
            ResultSet rs = stmt.executeQuery("SELECT COUNT(*) FROM {{NAMESPACE}}.{{TABLE_NAME}}");
            assertTrue(rs.next());
            assertTrue(rs.getInt(1) >= 0);
            conn.commit();
        }
    }

    @Test
    public void testInsertUpdateDelete() throws SQLException {
        try (Connection conn = getConnection()) {
            String testId = UUID.randomUUID().toString();

            // Insert
            PreparedStatement insertStmt = conn.prepareStatement(
                "INSERT INTO {{NAMESPACE}}.test_table (id, name) VALUES (?, ?)");
            insertStmt.setString(1, testId);
            insertStmt.setString(2, "test");
            insertStmt.executeUpdate();
            conn.commit();

            // Update
            PreparedStatement updateStmt = conn.prepareStatement(
                "UPDATE {{NAMESPACE}}.test_table SET name = ? WHERE id = ?");
            updateStmt.setString(1, "updated");
            updateStmt.setString(2, testId);
            updateStmt.executeUpdate();
            conn.commit();

            // Delete
            PreparedStatement deleteStmt = conn.prepareStatement(
                "DELETE FROM {{NAMESPACE}}.test_table WHERE id = ?");
            deleteStmt.setString(1, testId);
            deleteStmt.executeUpdate();
            conn.commit();
        }
    }
}
```

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
| **MySQL Import** | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import/?databases=MySQL_MariaDB_TiDB |
| **Decoupling Transaction Metadata (RECOMMENDED)** | https://scalardb.scalar-labs.com/docs/latest/schema-loader-import/#decoupling-transaction-metadata |

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

### Advanced Features

| Reference | URL |
|-----------|-----|
| Vector Search | https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/getting-started-with-vector-search/ |
| Object Storage (S3) | https://scalardb.scalar-labs.com/docs/latest/configurations/?databases=S3#storage-related-configurations |
| Object Storage (Azure) | https://scalardb.scalar-labs.com/docs/latest/configurations/?databases=Blob_Storage#storage-related-configurations |
| Object Storage (GCS) | https://scalardb.scalar-labs.com/docs/latest/configurations/?databases=Cloud_Storage#storage-related-configurations |

### Support

| Resource | URL |
|----------|-----|
| Scalar Labs Support | https://www.scalar-labs.com/support |
| GitHub Issues | https://github.com/scalar-labs/scalardb/issues |

---

*Migration guide generated by Migrate MySQL to ScalarDB Schema Skill*
*Input consumed from: ${MYSQL_SCHEMA_REPORT_MD}*
