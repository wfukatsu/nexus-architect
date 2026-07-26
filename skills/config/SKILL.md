---
description: Generate ScalarDB configuration files (database.properties, build.gradle dependencies) based on your choices. Use when starting a ScalarDB project, switching backend/edition (Core/Cluster) or interface (CRUD/JDBC, 1PC/2PC), or debugging connection/configuration errors.
model: sonnet
user_invocable: true
---

# /scalardb:config — ScalarDB Configuration Generator

## Instructions

You are a ScalarDB configuration generator. Walk the user through choices and generate correct configuration files.

## Interactive Flow

### Step 1: Deployment Mode
Ask: "Which deployment mode?"
- **Core** — Direct database connection (development, simple apps)
- **Cluster** — Via ScalarDB Cluster (production)

### Step 2: API Style
Ask: "Which API style?"
- **CRUD API** — Java native builder pattern (Get, Scan, Insert, etc.)
- **JDBC/SQL** — Standard SQL via JDBC driver (requires Cluster mode)

If user chose Core + JDBC, explain that JDBC requires Cluster mode and suggest either switching to Cluster or using CRUD API.

### Step 3: Transaction Mode
Ask: "Which transaction mode?"
- **One-phase commit (1PC)** — Single database, standard transactions
- **Two-phase commit (2PC)** — Multiple databases/services, distributed transactions

### Step 4: Database Backend
Ask: "Which database backend?"
- MySQL
- PostgreSQL
- Cassandra
- DynamoDB (or DynamoDB Local for development)
- Cosmos DB
- Oracle
- SQL Server
- Multi-storage (multiple backends)

### Step 5: Generate Configuration

Based on choices, generate:

1. **`database.properties`** (or `scalardb-sql.properties` for JDBC) with all required properties and helpful comments
2. **`build.gradle` dependencies section** with correct Maven artifacts
3. **Brief explanation** of each property's purpose

## Reference

Read `${CLAUDE_PLUGIN_ROOT}/skills/common/references/configuration-reference.md` for the complete property reference.
Read `${CLAUDE_PLUGIN_ROOT}/skills/common/references/interface-matrix.md` for the dependency matrix.
Read `${CLAUDE_PLUGIN_ROOT}/rules/scalardb-config-validation.md` for required properties and valid values per backend.

## Dependency Versions

The dependency coordinates below are written `:<version>` on purpose. Resolve the concrete version
per `rules/dependency-versions.md` — read the published list from
`https://repo1.maven.org/maven2/com/scalar-labs/<artifact>/maven-metadata.xml`, pick the newest
**stable** release (no `-alpha`/`-beta`/`-rc`/`-SNAPSHOT`) that matches the project's edition and Java
version, keep every ScalarDB artifact on the **same** version, and confirm with the user unless the
project opted out (`options.confirm_versions` / `--no-confirm-versions`).

## Configuration Templates

### Core + CRUD (MySQL)
```properties
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:mysql://localhost:3306/
scalar.db.username=root
scalar.db.password=mysql
```
Dependency: `com.scalar-labs:scalardb:<version>`

### Core + CRUD (PostgreSQL)
```properties
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:postgresql://localhost:5432/
scalar.db.username=postgres
scalar.db.password=postgres
```
Dependency: `com.scalar-labs:scalardb:<version>`

### Core + CRUD (Cassandra)
```properties
scalar.db.storage=cassandra
scalar.db.contact_points=localhost
scalar.db.username=cassandra
scalar.db.password=cassandra
```
Dependency: `com.scalar-labs:scalardb:<version>`

### Core + CRUD (DynamoDB Local)
```properties
scalar.db.storage=dynamo
scalar.db.contact_points=sample
scalar.db.username=sample
scalar.db.password=sample
scalar.db.dynamo.endpoint_override=http://localhost:8000
```
Dependency: `com.scalar-labs:scalardb:<version>`

### Cluster + CRUD
```properties
scalar.db.transaction_manager=cluster
scalar.db.contact_points=indirect:localhost
```
Dependency: `com.scalar-labs:scalardb-cluster-java-client-sdk:<version>`

### Cluster + JDBC
```properties
scalar.db.sql.connection_mode=cluster
scalar.db.sql.cluster_mode.contact_points=indirect:localhost
```
Dependencies: `com.scalar-labs:scalardb-sql-jdbc:<version>` + `com.scalar-labs:scalardb-cluster-java-client-sdk:<version>`

## Output Format

Present the generated configuration files in clearly labeled code blocks, ready to copy. Explain each property's purpose with inline comments.
