---
name: analyze-postgresql-schema
description: Analyzes PostgreSQL database schema and generates a comprehensive Markdown report for sharing. Use when you need to document PostgreSQL schema objects including tables, triggers, custom types, PL/pgSQL code, and object dependencies.
---

# PostgreSQL Database Schema Analysis Skill

## Purpose

Generate a comprehensive **Markdown report** (`postgresql_schema_report.md`) documenting a PostgreSQL database schema. This report is the primary deliverable for sharing with users, stakeholders, or migration teams.

## Output

Files are written to the configured `OUTPUT_DIR` (from `.env`):

| File | Purpose |
|------|---------|
| `postgresql_schema_report.md` | **Main deliverable** - Human-readable report to share |
| `raw_schema_data.json` | Reference file used to build the report |

**Note**: The `OUTPUT_DIR` must be an **absolute path** matching the migrate-postgresql-to-scalardb skill's `.env` for seamless integration.

---

## Workflow

```
PostgreSQL Database  ──►  raw_schema_data.json  ──►  postgresql_schema_report.md
                          (intermediate)              (deliverable)
```

### Step 1: Collect Data

Run the Python script to extract schema metadata from PostgreSQL:

```bash
cd skills/analyze-postgresql-schema/scripts
python postgresql_db_extractor.py
```

**Options:**
- `--test` - Test database connection only
- `--include-source` - Include full PL/pgSQL source code in output

This produces `raw_schema_data.json` in the configured `OUTPUT_DIR`.

### Step 2: Generate Report

Claude reads the JSON and generates the Markdown report following the template in `analyze-postgresql-dbms_report.md`.

**Rules for report generation:**
- Follow the template structure exactly
- Use the JSON field references indicated in each section
- **Skip sections entirely** if no data exists (no empty tables, no "N/A")
- Calculate summary metrics for the Executive Summary from actual data
- **DO NOT add migration commentary** - This skill only extracts and documents
- **DO NOT mark types as "supported" or "not supported"** - That is the job of the `migrate-postgresql-to-scalardb` skill

> **Important**: This skill is purely for **extraction and documentation**. All migration analysis, compatibility judgments, and type mapping decisions are handled by the separate `migrate-postgresql-to-scalardb` skill.

---

## Files in This Skill

| File | Description |
|------|-------------|
| `SKILL.md` | This file - skill documentation |
| `analyze-postgresql-dbms_report.md` | **Report template** - Structure for generating the Markdown report |
| `scripts/postgresql_db_extractor.py` | **Single extraction script** |

**Configuration file** (in `.claude/configuration/`):
| `databases.env` | Consolidated database configuration (Oracle, MySQL, PostgreSQL) |

---

## Configuration

### Centralized Configuration

Configuration is stored in the centralized configuration file:

**Location**: `.claude/configuration/databases.env`

This single file contains all database configuration (Oracle, MySQL, PostgreSQL) for both schema analysis and migration skills.

```properties
# PostgreSQL Database Connection
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=your_database
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
POSTGRES_SCHEMA=public  # Optional, defaults to 'public'

# Output directory (ABSOLUTE PATH - shared with migration skill)
OUTPUT_DIR=/absolute/path/to/shared/output

# Report filename
REPORT_FILENAME=postgresql_schema_report.md

# ScalarDB migration namespace
SCALARDB_NAMESPACE=your_namespace

# Include PL/pgSQL source code (true/false)
INCLUDE_PLPGSQL_SOURCE=true

# Path to psql executable (leave empty if psql is in PATH)
PSQL_PATH=
```

**Configuration Search Order**:
1. `.claude/configuration/databases.env` (consolidated - **recommended**)
2. Project root directory
3. Current working directory

---

## Data Collected

The script queries PostgreSQL system catalogs to collect:

### Tables & Constraints
- Tables (regular, partitioned, temporary, foreign)
- Columns (including identity, generated columns)
- Partitions and inheritance
- Constraints (PK, FK, UK, Check)
- SERIAL/BIGSERIAL columns
- Table DDL

### Indexes
- All index types (B-tree, hash, GiST, GIN, BRIN, etc.)
- Index columns and expressions
- Partial indexes (with WHERE clause)
- Unique indexes

### Views
- Standard views with source SQL
- Materialized views with indexes
- View columns

### Custom Types
- ENUM types
- Composite types
- Domain types
- Range types
- Array columns
- JSON/JSONB columns
- XML columns
- Geometric/Network types

### PL/pgSQL Objects
- Functions (all languages)
- Procedures (PostgreSQL 11+)
- Triggers
- Trigger functions
- Event triggers
- Custom aggregates
- Custom operators

### Sequences
- Sequence definitions
- Sequence usage by columns

### Security
- Table privileges
- Column privileges
- Row Level Security (RLS) policies
- Roles

### Extensions
- Installed extensions
- Extension objects

### Miscellaneous
- Schemas
- Foreign tables (FDW)
- Foreign servers
- Publications (logical replication)
- Subscriptions
- Rules
- Policies

### Full-Text Search
- Text search configurations
- tsvector columns

### Dependencies
- Object dependencies
- Invalid objects
- Migration order calculation

---

## JSON Output Structure

The script produces `raw_schema_data.json` with this structure:

```json
{
  "metadata": {
    "generated_at": "ISO timestamp",
    "schema": "SCHEMA_NAME",
    "database_name": "DATABASE_NAME",
    "database_type": "postgresql",
    "version": "16.1"
  },
  "types": {
    "enum_types": [...],
    "composite_types": [...],
    "domain_types": [...],
    "range_types": [...],
    "array_columns": [...],
    "json_columns": [...],
    "xml_columns": [],
    "geometric_columns": [],
    "network_columns": []
  },
  "tables": {
    "tables": [...],
    "columns": [...],
    "identity_columns": [...],
    "generated_columns": [...],
    "serial_columns": [...],
    "partitioned_tables": [...],
    "partitions": [...],
    "inheritance": [...],
    "constraints": [...],
    "check_constraints": [...],
    "foreign_keys": [...],
    "table_ddl": {}
  },
  "indexes": {
    "indexes": [...],
    "index_columns": [...],
    "index_expressions": [...],
    "partial_indexes": [...],
    "unique_indexes": []
  },
  "views": {
    "views": [...],
    "view_columns": [...],
    "materialized_views": [...],
    "mview_indexes": []
  },
  "plpgsql": {
    "functions": [...],
    "procedures": [...],
    "function_arguments": [...],
    "function_source": [...],
    "triggers": [...],
    "trigger_functions": [...],
    "event_triggers": [...],
    "aggregates": [...],
    "operators": []
  },
  "sequences": {
    "sequences": [...],
    "sequence_usage": []
  },
  "security": {
    "table_privileges": [...],
    "column_privileges": [...],
    "rls_policies": [...],
    "roles": []
  },
  "extensions": {
    "extensions": [...],
    "extension_objects": []
  },
  "misc": {
    "schemas": [...],
    "foreign_tables": [...],
    "foreign_servers": [...],
    "publications": [...],
    "subscriptions": [...],
    "rules": [...],
    "policies": []
  },
  "full_text_search": {
    "text_search_configs": [...],
    "tsvector_columns": []
  },
  "dependencies": {
    "dependencies": [...],
    "invalid_objects": [...],
    "migration_order": []
  }
}
```

---

## Prerequisites

- Python 3.8+
- `python-dotenv` package (`pip install python-dotenv`)
- PostgreSQL client (psql)
- Network access to PostgreSQL database

---

## Usage Example

```bash
# Navigate to scripts folder
cd skills/analyze-postgresql-schema/scripts

# Test connection first
python postgresql_db_extractor.py --test

# Run full extraction
python postgresql_db_extractor.py

# Include PL/pgSQL source code
python postgresql_db_extractor.py --include-source
```

After extraction, ask Claude:
> "Generate postgresql_schema_report.md from raw_schema_data.json following the template"

---

## PostgreSQL-Specific Features

### Key Differences from Oracle

| Feature | PostgreSQL | Oracle |
|---------|------------|--------|
| Identity | SERIAL, IDENTITY | IDENTITY, SEQUENCE |
| Arrays | Native array types | VARRAY, nested table |
| JSON | JSON, JSONB | JSON type |
| Full-text | tsvector/tsquery | Oracle Text |
| Inheritance | Table inheritance | N/A |
| Partitioning | Declarative, inheritance | RANGE, LIST, HASH |
| Extensions | pg_extension | Cartridges |
| RLS | pg_policy | VPD |

### Supported PostgreSQL Versions

- PostgreSQL 12+ (recommended)
- PostgreSQL 11 (limited procedure support)
- PostgreSQL 10 (limited features)

---

*Skill Version: 1.0*
*Compatible with: PostgreSQL 12+*
