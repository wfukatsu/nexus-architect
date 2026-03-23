---
name: analyze-mysql-schema
description: Analyzes MySQL database schema and generates a comprehensive Markdown report for sharing. Use when you need to document MySQL schema objects including tables, triggers, stored procedures, views, and object dependencies.
---

# MySQL Database Schema Analysis Skill

## Purpose

Generate a comprehensive **Markdown report** (`mysql_schema_report.md`) documenting a MySQL database schema. This report is a pure schema analysis - it describes what exists in the database without any migration-related content or compatibility assessments.

**Important**: This skill produces schema documentation only. Migration analysis (compatibility, conversion requirements, etc.) is handled by a separate skill (migrate-mysql-to-scalardb).

## Output

Files are written to the configured `OUTPUT_DIR` (from `.env`):

| File | Purpose |
|------|---------|
| `mysql_schema_report.md` | **Main deliverable** - Human-readable report to share |
| `raw_mysql_schema_data.json` | Reference file used to build the report |

**Note**: The `OUTPUT_DIR` must be an **absolute path** matching Skill 2's `.env` for seamless integration.

---

## Workflow

```
MySQL Database  ──►  raw_mysql_schema_data.json  ──►  mysql_schema_report.md
                      (intermediate)                   (deliverable)
```

### Step 1: Collect Data

Run the Python script to extract schema metadata from MySQL:

```bash
cd skills/analyze-mysql-schema/scripts
python mysql_db_extractor.py
```

**Options:**
- `--test` - Test database connection only
- `--include-source` - Include full stored procedure/function source code in output

This produces `raw_mysql_schema_data.json` in the configured `OUTPUT_DIR`.

### Step 2: Generate Report

Claude reads the JSON and generates the Markdown report following the template in `analyze-mysql-dbms_report.md`.

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
| `analyze-mysql-dbms_report.md` | Template for the Markdown report with JSON field mappings |
| `requirements.txt` | Python dependencies |
| `scripts/mysql_db_extractor.py` | **Single extraction script** |

**Configuration file** (in `.claude/configuration/`):
| `databases.env` | Consolidated database configuration (Oracle, MySQL, PostgreSQL) |

---

## Configuration

### Centralized Configuration

Configuration is stored in the centralized configuration file:

**Location**: `.claude/configuration/databases.env`

This single file contains all database configuration (Oracle, MySQL, PostgreSQL) for both schema analysis and migration skills.

```properties
# MySQL Database Connection
MYSQL_HOST=your_host
MYSQL_PORT=3306
MYSQL_DATABASE=your_database
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password

# Output directory (ABSOLUTE PATH - shared with migration skill)
OUTPUT_DIR=/absolute/path/to/shared/output

# Report filename
REPORT_FILENAME=mysql_schema_report.md

# ScalarDB migration namespace
SCALARDB_NAMESPACE=your_namespace

# Include stored procedure/function source code (true/false)
INCLUDE_SOURCE=false
```

**Configuration Search Order**:
1. `.claude/configuration/databases.env` (consolidated - **recommended**)
2. Project root directory
3. Current working directory

---

## Data Collected

The script queries MySQL information_schema and other system tables to collect:

### Tables & Constraints
- Tables (regular, partitioned, temporary)
- Columns (including auto_increment, generated columns)
- Partitions and subpartitions
- LOB columns (TEXT, BLOB types)
- Constraints (PK, FK, UK, Check)
- Table DDL via SHOW CREATE TABLE

### Indexes
- All index types (B-tree, Hash, Fulltext, Spatial)
- Index columns
- Composite indexes
- Functional indexes (MySQL 8.0.13+)
- Invisible indexes (MySQL 8.0+)

### Views
- Standard views with source SQL
- View columns and updateability

### Stored Routines
- Stored Procedures
- Stored Functions
- Parameters
- Source code and DDL

### Triggers
- DML triggers
- Trigger ordering (MySQL 5.7.2+)
- Action statements

### Events
- Scheduled events
- Event definitions and schedules

### MySQL-Specific Features
- JSON columns
- Spatial/Geometry columns
- ENUM/SET columns
- Virtual/Generated columns
- CASCADE foreign keys

### Security
- Schema privileges
- Table privileges
- Column privileges
- Routine privileges
- User accounts

### Dependencies
- Foreign key dependencies
- View dependencies
- Trigger dependencies
- Routine dependencies
- Suggested migration order

### Statistics
- Table sizes (rows, data size, index size)
- Index cardinality

---

## JSON Output Structure

The script produces `raw_mysql_schema_data.json` with this structure:

```json
{
  "metadata": {
    "generated_at": "ISO timestamp",
    "database": "DATABASE_NAME",
    "mysql_version": "8.0.x",
    "server_info": "MySQL Community Server",
    "hostname": "host:port"
  },
  "tables": {
    "tables": [...],
    "columns": [...],
    "auto_increment_columns": [...],
    "generated_columns": [...],
    "partitioned_tables": [...],
    "partitions": [...],
    "constraints": [...],
    "foreign_key_details": [...],
    "check_constraints": [...],
    "constraint_columns": [...],
    "lob_columns": [...],
    "table_ddl": { "TABLE_NAME": "DDL..." }
  },
  "indexes": {
    "indexes": [...],
    "index_columns": [...],
    "fulltext_indexes": [...],
    "spatial_indexes": [...],
    "expression_indexes": [...]
  },
  "views": {
    "views": [...],
    "view_source": [...],
    "view_columns": [...],
    "view_ddl": {...}
  },
  "routines": {
    "procedures": [...],
    "functions": [...],
    "triggers": [...],
    "events": [...],
    "procedure_parameters": [...],
    "function_parameters": [...],
    "procedure_source": {...},
    "function_source": {...},
    "trigger_source": {...},
    "event_source": {...},
    "procedure_ddl": {...},
    "function_ddl": {...},
    "trigger_ddl": {...},
    "event_ddl": {...}
  },
  "security": {
    "schema_privileges": [...],
    "table_privileges": [...],
    "column_privileges": [...],
    "routine_privileges": [...],
    "users": [...]
  },
  "misc": {
    "json_columns": [...],
    "spatial_columns": [...],
    "enum_set_columns": [...],
    "virtual_columns": [...],
    "cascade_fks": [...],
    "server_variables": [...],
    "character_sets": [...],
    "collations": [...],
    "engines": [...],
    "all_objects": [...]
  },
  "dependencies": {
    "fk_dependencies": [...],
    "view_dependencies": [...],
    "trigger_dependencies": [...],
    "routine_dependencies": [...],
    "migration_order": [...]
  },
  "statistics": {
    "table_sizes": [...],
    "index_stats": [...]
  }
}
```

---

## Report Sections

The generated `mysql_schema_report.md` includes:

| Section | Description |
|---------|-------------|
| 1. Executive Summary | Object counts, storage engines, data type distribution |
| 2. Tables | Table properties, columns, auto-increment, generated columns, partitions, LOBs |
| 3. Constraints | Primary keys, foreign keys, unique, check constraints |
| 4. Indexes | All indexes, fulltext, spatial, functional indexes |
| 5. Views | View definitions and columns |
| 6. Stored Routines | Procedures and functions with parameters |
| 7. Triggers | Trigger definitions and ordering |
| 8. Events | Scheduled events |
| 9. Security | Privileges at schema, table, column, routine levels |
| 10. MySQL-Specific Features | JSON, spatial, ENUM/SET, virtual columns |
| 11. Dependencies | FK dependencies, view/trigger/routine dependencies, migration order |
| 12. Statistics | Table and index sizes |
| 13. Database Settings | Server variables, character sets, collations, engines |
| 14. All Objects Summary | Complete object listing |
| Appendix A | DDL Scripts for all objects |
| Appendix B | Stored routine source code (if INCLUDE_SOURCE=true) |

---

## Prerequisites

- Python 3.8+
- `python-dotenv` package
- `mysql-connector-python` package
- Network access to MySQL database
- User with SELECT privilege on information_schema

---

## Usage Example

```bash
# Navigate to scripts folder
cd skills/analyze-mysql-schema/scripts

# Test connection first
python mysql_db_extractor.py --test

# Run full extraction
python mysql_db_extractor.py

# Include stored procedure source code
python mysql_db_extractor.py --include-source
```

After extraction, ask Claude:
> "Generate mysql_schema_report.md from raw_mysql_schema_data.json following the template"

---

## MySQL Version Compatibility

| Feature | Minimum Version | Notes |
|---------|-----------------|-------|
| Core extraction | MySQL 5.7+ | Basic tables, indexes, routines |
| Check constraints | MySQL 8.0.16+ | CHECK_CONSTRAINTS table |
| Functional indexes | MySQL 8.0.13+ | Expression-based indexes |
| Invisible indexes | MySQL 8.0+ | VISIBLE column in STATISTICS |
| Trigger ordering | MySQL 5.7.2+ | FOLLOWS/PRECEDES support |
| JSON columns | MySQL 5.7.8+ | Native JSON type |

---

*Skill Version: 2.0*
*Compatible with: MySQL 5.7+, 8.0+*
