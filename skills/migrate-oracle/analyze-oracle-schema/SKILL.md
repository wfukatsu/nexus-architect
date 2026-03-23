---
name: analyze-oracle-schema
description: Analyzes Oracle database schema and generates a comprehensive Markdown report for sharing. Use when you need to document Oracle schema objects including tables, triggers, custom types, PL/SQL code, and object dependencies.
---

# Oracle Database Schema Analysis Skill

## Purpose

Generate a comprehensive **Markdown report** (`oracle_schema_report.md`) documenting an Oracle database schema. This report is the primary deliverable for sharing with users, stakeholders, or migration teams.

## Output

Files are written to the configured `OUTPUT_DIR` (from `.env`):

| File | Purpose |
|------|---------|
| `oracle_schema_report.md` | **Main deliverable** - Human-readable report to share |
| `raw_schema_data.json` | Reference file used to build the report |

**Note**: The `OUTPUT_DIR` must be an **absolute path** matching Skill 2's `.env` for seamless integration.

---

## Workflow

```
Oracle Database  ──►  raw_schema_data.json  ──►  oracle_schema_report.md
                      (intermediate)              (deliverable)
```

### Step 1: Collect Data

Run the Python script to extract schema metadata from Oracle:

```bash
cd skills/analyze-oracle-schema/scripts
python oracle_db_extractor.py
```

**Options:**
- `--test` - Test database connection only
- `--include-source` - Include full PL/SQL source code in output

This produces `raw_schema_data.json` in the configured `OUTPUT_DIR`.

### Step 2: Generate Report

Claude reads the JSON and generates the Markdown report following the template in `analyze-oracle-dbms_report.md`.

**Rules for report generation:**
- Follow the template structure exactly
- Use the JSON field references indicated in each section
- **Skip sections entirely** if no data exists (no empty tables, no "N/A")
- Calculate summary metrics for the Executive Summary from actual data

---

## Files in This Skill

| File | Description |
|------|-------------|
| `SKILL.md` | This file - skill documentation |
| `analyze-oracle-dbms_report.md` | Template for the Markdown report with JSON field mappings |
| `requirements.txt` | Python dependencies |
| `scripts/oracle_db_extractor.py` | **Single extraction script** |

**Configuration file** (in `.claude/configuration/`):
| `databases.env` | Consolidated database configuration (Oracle, MySQL, PostgreSQL) |

---

## Configuration

### Centralized Configuration

Configuration is stored in the centralized configuration file:

**Location**: `.claude/configuration/databases.env`

This single file contains all database configuration (Oracle, MySQL, PostgreSQL) for both schema analysis and migration skills.

```properties
# Oracle Database Connection
ORACLE_HOST=your_host
ORACLE_PORT=1521
ORACLE_SERVICE=your_service
ORACLE_USER=your_user
ORACLE_PASSWORD=your_password
ORACLE_SCHEMA=YOUR_SCHEMA  # Optional, defaults to connected user

# Output directory (ABSOLUTE PATH - shared with migration skill)
OUTPUT_DIR=/absolute/path/to/shared/output

# Report filename
REPORT_FILENAME=oracle_schema_report.md

# ScalarDB migration namespace
SCALARDB_NAMESPACE=your_namespace

# Include PL/SQL source code (true/false)
INCLUDE_PLSQL_SOURCE=false
```

**Configuration Search Order**:
1. `.claude/configuration/databases.env` (consolidated - **recommended**)
2. Project root directory
3. Current working directory

---

## Data Collected

The script queries Oracle data dictionary views to collect:

### Tables & Constraints
- Tables (regular, partitioned, temporary, IOT, external)
- Columns (including identity, virtual columns)
- Partitions and subpartitions
- LOB columns
- Constraints (PK, FK, UK, Check)
- Table DDL via DBMS_METADATA

### Indexes
- All index types (B-tree, bitmap, function-based)
- Index columns and expressions
- Partitioned indexes

### Views
- Standard views with source SQL
- Materialized views with refresh settings
- Editioning views

### PL/SQL Objects
- Procedures, Functions, Packages
- Triggers (DML, DDL, system)
- Arguments/Parameters
- Source code and DDL
- Compilation errors

### Miscellaneous
- Sequences
- Synonyms (private and public)
- Database links
- Scheduler jobs, programs, schedules
- Directories
- XMLType, JSON, Spatial columns
- Advanced Queuing objects

### Security
- Object privileges
- System privileges
- Role privileges
- VPD policies
- FGA policies

### Dependencies
- Object dependencies
- External dependencies (other schemas)
- SYS package dependencies
- Invalid objects
- Foreign key dependencies
- Suggested migration order

---

## JSON Output Structure

The script produces `raw_schema_data.json` with this structure:

```json
{
  "metadata": {
    "generated_at": "ISO timestamp",
    "schema": "SCHEMA_NAME",
    "database_name": "SERVICE_NAME"
  },
  "types": {
    "object_types": [...],
    "type_attributes": [...],
    "type_methods": [...],
    "collection_types": [...],
    "type_dependencies": [...]
  },
  "tables": {
    "tables": [...],
    "columns": [...],
    "identity_columns": [...],
    "virtual_columns": [...],
    "partitioned_tables": [...],
    "partitions": [...],
    "constraints": [...],
    "foreign_key_details": [...],
    "table_ddl": { "TABLE_NAME": "DDL..." }
  },
  "indexes": {
    "indexes": [...],
    "index_columns": [...],
    "index_expressions": [...],
    "partitioned_indexes": [...]
  },
  "views": {
    "views": [...],
    "view_source": [...],
    "materialized_views": [...],
    "mview_query": [...]
  },
  "plsql": {
    "procedures": [...],
    "functions": [...],
    "packages": [...],
    "triggers": [...],
    "arguments": [...],
    "source": [...],
    "procedure_ddl": {...},
    "function_ddl": {...},
    "package_ddl": {...},
    "trigger_ddl": {...}
  },
  "security": {
    "object_privileges": [...],
    "system_privileges": [...],
    "role_privileges": [...],
    "vpd_policies": [...]
  },
  "misc": {
    "sequences": [...],
    "synonyms": [...],
    "db_links": [...],
    "scheduler_jobs": [...]
  },
  "dependencies": {
    "dependencies": [...],
    "invalid_objects": [...],
    "external_dependencies": [...],
    "sys_dependencies": [...],
    "migration_order": [...]
  }
}
```

---

## Prerequisites

- Python 3.12
- `python-dotenv` package (`pip install -r requirements.txt`)
- SQL*Plus client (Oracle Instant Client)
- Network access to Oracle database

---

## Usage Example

```bash
# Navigate to scripts folder
cd skills/analyze-oracle-schema/scripts

# Test connection first
python oracle_db_extractor.py --test

# Run full extraction
python oracle_db_extractor.py

# Include PL/SQL source code
python oracle_db_extractor.py --include-source
```

After extraction, ask Claude:
> "Generate oracle_schema_report.md from raw_schema_data.json following the template"
