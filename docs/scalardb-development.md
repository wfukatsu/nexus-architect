# ScalarDB Application Development Guide

This guide covers the 11 ScalarDB development skills that help you build, review, and maintain ScalarDB applications.

## Overview

```
/scalardb:model        Design your schema
        ↓
/scalardb:config       Generate configuration
        ↓
/scalardb:scaffold     Generate starter project
        ↓
/scalardb:build-app    Build complete application
        ↓
/scalardb:review-code  Review for correctness
```

## Skills

### Schema Design: `/scalardb:model`

Interactive wizard that walks you through designing a ScalarDB schema step by step.

**What it does:**
1. Gathers your domain entities and attributes
2. Identifies access patterns and common queries
3. Recommends partition keys (with even distribution guidance)
4. Recommends clustering keys and sort directions
5. Suggests secondary indexes (with overhead warnings)
6. Generates `schema.json` and optionally `schema.sql`

**Usage:**
```bash
/scalardb:model
```

**Output:** `schema.json` (Schema Loader format) and/or `schema.sql` (DDL format)

**Key guidance provided:**
- Partition key anti-patterns (hot partitions, monotonically increasing values)
- CRUD API has no JOIN support — schema must be designed for single-table access
- Denormalization strategies for non-JOIN queries
- Data type selection (BOOLEAN, INT, BIGINT, FLOAT, DOUBLE, TEXT, BLOB, DATE, TIME, TIMESTAMP, TIMESTAMPTZ)

---

### Configuration: `/scalardb:config`

Generates correct configuration files for any deployment/API/transaction mode combination.

**What it does:**
1. Asks deployment mode: Core or Cluster
2. Asks API style: CRUD or JDBC/SQL
3. Asks transaction mode: 1PC or 2PC
4. Asks database backend: MySQL, PostgreSQL, Cassandra, DynamoDB, Cosmos DB, Oracle, SQL Server
5. Generates `database.properties` or `scalardb-sql.properties` + `build.gradle` dependencies

**Usage:**
```bash
/scalardb:config
```

**The 6 interface combinations:**

| # | Deployment | API | Transaction | Use Case |
|---|-----------|-----|-------------|----------|
| 1 | Core | CRUD | 1PC | Development, single-DB |
| 2 | Core | CRUD | 2PC | Multi-DB from single app |
| 3 | Cluster | CRUD | 1PC | Production single-DB |
| 4 | Cluster | CRUD | 2PC | Production multi-service |
| 5 | Cluster | JDBC | 1PC | Production with SQL |
| 6 | Cluster | JDBC | 2PC | Production multi-service SQL |

---

### Project Scaffolding: `/scalardb:scaffold`

Generates a complete, runnable starter project for any of the 6 interface combinations.

**What it does:**
Generates all files needed to start development:
- `build.gradle` — Dependencies and plugins
- `database.properties` — Configuration
- `schema.json` / `schema.sql` — Schema definition
- `src/main/java/sample/Sample.java` — Service class with CRUD operations
- `docker-compose.yml` — Local database setup
- `README.md` — Setup and run instructions

**Usage:**
```bash
/scalardb:scaffold
```

**Code quality enforced:**
- Uses Insert/Upsert/Update (not deprecated Put)
- Builder pattern for all operations
- Explicit namespace and table on every operation
- Correct exception catch order
- Retry logic with exponential backoff
- Commit even read-only transactions

---

### Application Builder: `/scalardb:build-app`

Builds a complete ScalarDB application from a domain description.

**What it does:**
1. Understands your requirements (entities, relationships, access patterns)
2. Designs data model with proper keys and indexes
3. Generates configuration and build files
4. Creates service layer with full CRUD, exception handling, retry logic
5. Sets up local development environment
6. Provides integration point (CLI or REST controller)

**Usage:**
```bash
/scalardb:build-app
# Then describe your domain: "I need an e-commerce system with orders, customers, and inventory"
```

---

### CRUD Operations Guide: `/scalardb:crud-ops`

Quick reference for all CRUD API operations with code examples.

**Covers:**
- **Get** — By primary key or secondary index
- **Scan** — Partition scan, range scan, scan all, index scan
- **Insert** — New record only (fails if exists)
- **Upsert** — Insert or update
- **Update** — Existing record only, with optional conditions
- **Delete** — By primary key
- **Batch** — Multiple operations atomically via `mutate()`
- **Key construction** — Single and composite keys

**Usage:**
```bash
/scalardb:crud-ops
# Then ask: "How do I scan with a range condition?"
```

---

### JDBC/SQL Operations Guide: `/scalardb:jdbc-ops`

Quick reference for JDBC/SQL operations with code examples.

**Covers:**
- SELECT with WHERE, ORDER BY, LIMIT
- INSERT, UPSERT, UPDATE, DELETE
- JOIN (INNER, LEFT, RIGHT — not FULL)
- Aggregate functions (COUNT, SUM, AVG, MIN, MAX)
- GROUP BY / HAVING
- 2PC via SQL statements (PREPARE, VALIDATE, COMMIT)
- Error code 301 (UnknownTransactionStatusException) handling

**SQL limitations documented:**
- No DISTINCT, subqueries, CTEs, window functions
- No FULL OUTER JOIN, UNION, INTERSECT, EXCEPT
- JOIN predicates must reference primary key or secondary index
- WHERE must be in DNF or CNF

**Usage:**
```bash
/scalardb:jdbc-ops
# Then ask: "How do I do a LEFT JOIN with aggregation?"
```

---

### Exception Handling: `/scalardb:error-handler`

Generates exception handling code and reviews existing code for correctness.

**Two modes:**
1. **Generate** — Produces complete try/catch patterns with retry logic for any interface combination
2. **Review** — Validates existing code for 16 categories of exception handling issues

**Critical patterns enforced:**
- Catch order: `CrudConflictException` before `CrudException` (specific before parent)
- `UnknownTransactionStatusException`: Do NOT retry or rollback
- Always commit read-only transactions
- Always rollback in catch blocks (except error code 301)
- Retry with exponential backoff (max 3-5 attempts)
- Log transaction ID from all exceptions

**Usage:**
```bash
/scalardb:error-handler
# Choose: "Generate exception handling code" or "Review my existing code"
```

---

### Code Review: `/scalardb:review-code`

Reviews Java code for ScalarDB correctness across 16 check categories.

**Check categories:**

| Severity | Checks |
|----------|--------|
| **Critical** | Exception catch order, transaction lifecycle, UnknownTransactionStatusException handling |
| **Major** | Deprecated API usage (Put), builder pattern compliance, result handling, retry logic |
| **Minor** | Configuration completeness, schema validity, Java best practices |
| **JDBC-specific** | setAutoCommit, resource management, SQL injection, error code 301, 2PC protocol |

**Usage:**
```bash
/scalardb:review-code
# Then provide your Java file or paste code
```

---

### Local Environment: `/scalardb:local-env`

Sets up local development environment with Docker Compose.

**Supported backends:** MySQL, PostgreSQL, Cassandra, DynamoDB Local, Multi-storage (MySQL + Cassandra)

**Usage:**
```bash
/scalardb:local-env
# Choose your database backend
```

**Output:** `docker-compose.yml` with health checks, volume management, and schema loading commands.

---

### Documentation Search: `/scalardb:docs`

Searches ScalarDB documentation and provides answers with code examples.

**Usage:**
```bash
/scalardb:docs
# Ask: "How do I configure cross-partition scan?"
```

**Sources:** Official documentation (scalardb.scalar-labs.com) + local reference files.

---

### Migration Advisor: `/scalardb:migrate`

Guides migrations between interface combinations with concrete diffs.

**Supported paths:**
- Core → Cluster (dependency, config, schema loader changes)
- CRUD → JDBC/SQL (complete code rewrite guide)
- 1PC → 2PC (new exception types, prepare/validate/commit)

**Usage:**
```bash
/scalardb:migrate
# Describe: "I need to migrate from Core+CRUD+1PC to Cluster+JDBC+2PC"
```

---

## Rules (Always-On Guidance)

These rules are automatically loaded and provide guidance whenever you work with ScalarDB code:

| Rule | Key Content |
|------|-------------|
| `scalardb-exception-handling` | Catch order, retry logic, UnknownTransactionStatusException |
| `scalardb-crud-patterns` | Builder pattern, deprecated Put, key construction, result handling |
| `scalardb-jdbc-patterns` | setAutoCommit, PreparedStatement, error code 301, JOIN/aggregate syntax |
| `scalardb-2pc-patterns` | Coordinator/participant protocol, request routing, group commit |
| `scalardb-config-validation` | Required properties by storage, contact points format, cross-partition scan |
| `scalardb-schema-design` | Partition key design, clustering keys, anti-patterns, data types |
| `scalardb-java-best-practices` | Thread safety, transaction lifecycle, SLF4J, try-with-resources |

## Reference Documents

Located in `skills/common/references/`:

| Document | Content |
|----------|---------|
| `api-reference.md` | Complete ScalarDB API (TransactionManager, CRUD operations, Result, Key, Conditions) |
| `interface-matrix.md` | All 6 interface combinations with decision guide, dependencies, config, code patterns |
| `exception-hierarchy.md` | Exception tree, decision flowchart, retry patterns, JDBC error code mapping |
| `sql-reference.md` | SQL grammar (DDL, DML, TCL, DCL), JOIN rules, aggregate functions, limitations |
| `schema-format.md` | JSON and SQL schema format, data types, Schema Loader commands |
| `code-patterns/` | Complete working examples for all 6 interface combinations |
