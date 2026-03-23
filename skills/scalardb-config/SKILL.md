---
description: Generate ScalarDB configuration files (database.properties, build.gradle dependencies) based on your choices.
user_invocable: true
---

# /scalardb-config — ScalarDB Configuration Generator

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

Read `.claude/docs/configuration-reference.md` for the complete property reference.
Read `.claude/docs/interface-matrix.md` for the dependency matrix.

## Configuration Templates

### Core + CRUD (MySQL)
```properties
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:mysql://localhost:3306/
scalar.db.username=root
scalar.db.password=mysql
```
Dependency: `com.scalar-labs:scalardb:3.16.0`

### Core + CRUD (PostgreSQL)
```properties
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:postgresql://localhost:5432/
scalar.db.username=postgres
scalar.db.password=postgres
```
Dependency: `com.scalar-labs:scalardb:3.16.0`

### Core + CRUD (Cassandra)
```properties
scalar.db.storage=cassandra
scalar.db.contact_points=localhost
scalar.db.username=cassandra
scalar.db.password=cassandra
```
Dependency: `com.scalar-labs:scalardb:3.16.0`

### Core + CRUD (DynamoDB Local)
```properties
scalar.db.storage=dynamo
scalar.db.contact_points=sample
scalar.db.username=sample
scalar.db.password=sample
scalar.db.dynamo.endpoint_override=http://localhost:8000
```
Dependency: `com.scalar-labs:scalardb:3.16.0`

### Cluster + CRUD
```properties
scalar.db.transaction_manager=cluster
scalar.db.contact_points=indirect:localhost
```
Dependency: `com.scalar-labs:scalardb-cluster-java-client-sdk:3.16.0`

### Cluster + JDBC
```properties
scalar.db.sql.connection_mode=cluster
scalar.db.sql.cluster_mode.contact_points=indirect:localhost
```
Dependencies: `com.scalar-labs:scalardb-sql-jdbc:3.16.0` + `com.scalar-labs:scalardb-cluster-java-client-sdk:3.16.0`

## Output Format

Present the generated configuration files in clearly labeled code blocks, ready to copy. Explain each property's purpose with inline comments.
