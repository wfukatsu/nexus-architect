# Database Migration Guide

This guide covers the 4 database migration skills that automate the migration of Oracle, MySQL, and PostgreSQL databases to ScalarDB.

## Overview

```
/architect:migrate-database          Unified entry point (auto-detects DB type)
        ↓
┌───────────────────┬───────────────────┬───────────────────┐
│  migrate-oracle   │  migrate-mysql    │ migrate-postgresql │
├───────────────────┼───────────────────┼───────────────────┤
│ 1. Connect & Test │ 1. Connect & Test │ 1. Connect & Test │
│ 2. Extract Schema │ 2. Extract Schema │ 2. Extract Schema │
│ 3. Generate Report│ 3. Generate Report│ 3. Generate Report│
│ 4. Migration Plan │ 4. Migration Plan │ 4. Migration Plan │
│ 5. AQ Integration │ 5. SP/Trigger→Java│ 5. SP/Trigger→Java│
│ 6. SP/Trigger→Java│                   │                   │
└───────────────────┴───────────────────┴───────────────────┘
```

## Quick Start

```bash
# Unified entry point (asks which database)
/architect:migrate-database

# Or go directly to a specific database
/architect:migrate-oracle
/architect:migrate-mysql
/architect:migrate-postgresql
```

The skill will interactively ask for connection details, then run the full migration pipeline automatically using subagents.

## How It Works

### Two-Phase Architecture

**Phase A: Interactive Configuration (main context)**
- Detects or creates configuration file (`.claude/configuration/databases.env`)
- Asks connection details: host, port, database/service, username, password
- Asks schema name, output directory, and options
- Creates output directory

**Phase B: Subagent Processing (isolated contexts)**
Each step runs in its own subagent to preserve context window:

| Step | Subagent | What It Does |
|------|----------|-------------|
| 1 | Connection Tester | Connects to DB, verifies access, gets version |
| 2 | Schema Extractor | Runs Python script to extract full schema as JSON |
| 3 | Report Generator | Converts raw JSON to readable Markdown report |
| 4 | Migration Analyst | Analyzes compatibility, calculates complexity, generates migration plan |
| 5 | AQ Migrator (Oracle only) | Converts triggers/SPs to Oracle AQ + Java consumers |
| 6 | SP/Trigger Migrator | Converts stored procedures/triggers to Java service classes |

### Error Cascading

If a step fails, only dependent downstream steps are skipped:
- Connection fails → everything stops
- Extraction fails → everything stops (but connection verified)
- Report fails → raw JSON preserved on disk
- Migration analysis fails → AQ + SP migration still run
- AQ fails → SP migration still runs

## Skills in Detail

### `/architect:migrate-database`

Unified router that asks which database you want to migrate and delegates to the appropriate skill.

```bash
/architect:migrate-database
# → "Which database are you migrating? Oracle / MySQL / PostgreSQL"
```

---

### `/architect:migrate-oracle`

Full Oracle-to-ScalarDB migration pipeline with 6 subagents.

**Schema Extraction** covers:
- Tables, columns, partitions, LOB columns, constraints
- Indexes (B-tree, bitmap, function-based)
- Views (standard and materialized)
- PL/SQL objects (procedures, functions, packages, triggers)
- Sequences, synonyms, database links, scheduler jobs
- Object types, collections, type dependencies
- Oracle AQ objects (queues, queue tables, subscribers)
- Security (object/system/role privileges, VPD/FGA policies)
- Object dependencies and migration order

**Migration Analysis** includes:
- Data type mapping (Oracle → ScalarDB)
- Complexity scoring (0-10 scale across 4 dimensions)
- Step-by-step migration plan
- ScalarDB SQL limitations impact assessment

**Oracle AQ Integration** (unique to Oracle):
- Converts triggers and stored procedures to event-driven architecture
- Generates Oracle AQ SQL: payload types, queue tables, queues, enqueue SPs, new triggers
- Generates Java consumers with ScalarDB Transaction API
- Exception classification (RETRIABLE / NON_RETRIABLE / UNKNOWN_TX_STATE)
- Idempotent consumer design using Upsert pattern

**SP/Trigger to Java Conversion** (17 feature categories):
- Variables, cursors, control flow, exception handling
- OLD/NEW row access, CRUD operations, conditional writes
- Subqueries, JOINs, aggregations, SQL functions
- Sequences → UUID, temp tables → Java collections
- Dynamic SQL → builder pattern, batch operations

**Output files:**
```
<output-dir>/
├── connection_test_response.json
├── raw_schema_data.json
├── oracle_schema_report.md
├── scalardb_migration_analysis.md
├── scalardb_migration_steps.md
├── aq_setup.sql                    # Oracle AQ infrastructure
├── scalardb_aq_migration_report.md
├── scalardb_sp_migration_report.md
└── generated-java/
    ├── *Consumer.java              # AQ consumers
    ├── *Message.java               # Message POJOs
    ├── AqStructHolder.java         # ojdbc11 compatibility
    ├── ExceptionClassifier.java    # Exception → verdict mapping
    └── *Service.java               # SP/trigger implementations
```

---

### `/architect:migrate-mysql`

MySQL-to-ScalarDB migration pipeline with 5 subagents.

**Schema Extraction** covers:
- Tables, columns (auto_increment, generated), partitions
- Indexes (B-tree, hash, fulltext, spatial, composite, functional)
- Views, stored procedures/functions, triggers, events
- JSON columns, spatial/geometry columns, ENUM/SET columns
- User privileges, character sets, collations, storage engines
- Dependencies (FK, view, trigger, routine)

**Data Type Mapping highlights:**
- `tinyint(1)` → BOOLEAN
- `int unsigned` → BIGINT
- `decimal/numeric` → DOUBLE (with precision loss warning)
- `json` → TEXT (serialize/deserialize in application)
- `enum/set` → TEXT (validate in application)
- `bigint` → BIGINT (with -2^53 to 2^53 range warning)

**Output files:**
```
<output-dir>/
├── mysql_connection_test_response.json
├── raw_mysql_schema_data.json
├── mysql_schema_report.md
├── scalardb_mysql_migration_analysis.md
├── scalardb_mysql_migration_steps.md
├── scalardb_mysql_sp_migration_report.md
└── generated-java/
    └── *Service.java
```

---

### `/architect:migrate-postgresql`

PostgreSQL-to-ScalarDB migration pipeline with 5 subagents.

**Schema Extraction** covers:
- Tables (regular, partitioned, temporary, foreign), inheritance
- Indexes (B-tree, hash, GiST, GIN, BRIN), partial/unique indexes
- Custom types (ENUM, composite, domain, range)
- PL/pgSQL functions/procedures, triggers, event triggers
- Sequences, extensions, foreign tables (FDW)
- RLS policies, publications/subscriptions, text search
- JSON/JSONB, XML, geometric/network types

**PostgreSQL-specific notes:**
- Only 14 data types are officially supported by ScalarDB
- `serial/bigserial` → INT/BIGINT (manage sequences in application)
- `numeric/money` → NOT SUPPORTED (use DOUBLE with precision loss)
- `json/jsonb` → TEXT (serialize/deserialize)
- `uuid` → TEXT
- `inet/cidr` → TEXT
- Arrays, ranges, geometric types → NOT SUPPORTED

**Output files:**
```
<output-dir>/
├── postgres_connection_test_response.json
├── raw_schema_data.json
├── postgresql_schema_report.md
├── scalardb_migration_analysis.md
├── scalardb_migration_steps.md
├── scalardb_sp_migration_report.md
└── generated-java/
    └── *Service.java
```

## Complexity Scoring

Each migration receives a complexity score (0-10) based on 4 weighted dimensions:

| Dimension | Weight | Low (0-2) | Medium (3-6) | High (7-10) |
|-----------|--------|-----------|--------------|-------------|
| Data Types | 20% | Standard types | LOBs, some custom | Object types, nested |
| Schema | 25% | Simple tables | FKs, views | Partitions, materialized views |
| Procedural Code | 25% | None or few | 10-50 objects | 50+ with heavy logic |
| Application Impact | 30% | Simple CRUD | JOINs, transactions | Window functions, heavy DB logic |

**Ratings:**
- 0-2: LOW complexity
- 3-4: MEDIUM
- 5-7: HIGH
- 8-10: VERY HIGH

## Configuration

All database connections are stored in `.claude/configuration/databases.env`. The migration skills create and manage this file automatically through interactive prompts.

```properties
# Shared
ACTIVE_DATABASE=oracle|mysql|postgresql
OUTPUT_DIR=/absolute/path/to/output

# Oracle
ORACLE_HOST=localhost
ORACLE_PORT=1521
ORACLE_SERVICE=ORCL
ORACLE_USER=scott
ORACLE_PASSWORD=tiger
ORACLE_SCHEMA=SCOTT

# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=myapp
MYSQL_USER=root
MYSQL_PASSWORD=mysql

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=myapp
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_SCHEMA=public
```

## Prerequisites

| Database | Required Tools |
|----------|---------------|
| Oracle | Python 3.9+, SQL*Plus, `python-dotenv` |
| MySQL | Python 3.9+, `mysql-connector-python`, `python-dotenv` |
| PostgreSQL | Python 3.9+, `psycopg2`, `python-dotenv` |

Install Python dependencies:
```bash
pip install python-dotenv mysql-connector-python psycopg2-binary
```

## Internal Architecture

### Python Extractors

Each database has a dedicated Python extractor script:
- `skills/migrate-oracle/analyze-oracle-schema/scripts/oracle_db_extractor.py`
- `skills/migrate-mysql/analyze-mysql-schema/scripts/mysql_db_extractor.py`
- `skills/migrate-postgresql/analyze-postgresql-schema/scripts/postgresql_db_extractor.py`

### Subagent Templates

Reusable prompt templates for each pipeline step:
- `skills/common/subagents/oracle/` (6 templates: test, extract, report, analysis, AQ, SP)
- `skills/common/subagents/mysql/` (5 templates)
- `skills/common/subagents/postgresql/` (5 templates)

### Reference Documents

Each migration skill includes database-specific references:
- Data type mapping tables
- ScalarDB SQL limitations
- Complexity scoring model
- Migration strategy guides (AQ, SP/trigger conversion)
