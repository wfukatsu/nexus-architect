#!/usr/bin/env python3
"""
PostgreSQL Schema Analyzer - Single Script Version
Collects comprehensive PostgreSQL database schema metadata and generates JSON output.
"""

import os
import subprocess
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv


# ============================================================================
# DATABASE CONNECTION MODULE
# ============================================================================

def find_env_file(config_path=None):
    """
    Find the .env file by checking multiple locations in order:
    0. Explicit config_path (if provided via --config CLI argument)
    1. Consolidated config (.claude/configuration/databases.env) - RECOMMENDED
    2. CWD-based .claude path (plugin mode)
    3. Project root (where .claude folder is located)
    4. Current working directory
    """
    if config_path:
        path = Path(config_path)
        if path.exists():
            return path
        else:
            print(f"Warning: Specified config file not found: {config_path}")

    # Script location varies:
    #   Plugin mode: <plugin_root>/skills/analyze-postgresql-schema/scripts/postgresql_db_extractor.py
    #   Legacy mode: <project>/.claude/skills/analyze-postgresql-schema/scripts/postgresql_db_extractor.py
    script_dir = Path(__file__).parent  # scripts/
    skill_dir = script_dir.parent  # analyze-postgresql-schema/
    claude_dir = skill_dir.parent.parent  # .claude/ (legacy) or plugin grandparent
    project_root = claude_dir.parent  # project root (legacy layout)

    # List of potential .env locations
    search_paths = [
        claude_dir / "configuration" / "databases.env",  # Consolidated config (preferred)
        Path.cwd() / ".claude" / "configuration" / "databases.env",  # Also search from current working directory (plugin mode)
        project_root / ".env",  # Project root
        Path.cwd() / ".env",  # Current working directory
    ]

    for path in search_paths:
        if path.exists():
            return path

    return None


def find_project_root():
    """Find the project root directory (where .claude folder exists)."""
    # Navigate up to find project root (layout-dependent)
    script_dir = Path(__file__).parent  # scripts/
    skill_dir = script_dir.parent  # analyze-postgresql-schema/
    project_root = skill_dir.parent.parent.parent  # project root (legacy layout)

    # Verify .claude exists at project root
    if (project_root / ".claude").exists():
        return project_root

    # Also check CWD (plugin mode - script may be in plugin dir, not project)
    if (Path.cwd() / ".claude").exists():
        return Path.cwd()

    # Default to skill directory's parent
    return project_root


def load_config(config_path=None):
    """
    Load configuration from .env file.

    The .env file is searched in these locations (in order):
    0. Explicit config_path (if provided via --config CLI argument)
    1. .claude/configuration/databases.env (consolidated - RECOMMENDED)
    2. CWD-based .claude path (plugin mode)
    3. Project root directory
    4. Current working directory
    """
    env_path = find_env_file(config_path)
    if env_path:
        load_dotenv(env_path)
        print(f"Loaded config from: {env_path}")
    else:
        print("WARNING: No .env file found. Using environment variables or defaults.")

    # Determine default output directory
    project_root = find_project_root()
    default_output = str(project_root / ".claude" / "output")

    # Support both consolidated (POSTGRES_*) and legacy (non-prefixed) variable names
    config = {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
        "database": os.getenv("POSTGRES_DATABASE", "postgres"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
        "schema": os.getenv("POSTGRES_SCHEMA", "public"),
        "output_dir": os.getenv("OUTPUT_DIR", default_output),
        "report_filename": os.getenv("POSTGRES_REPORT_FILENAME", os.getenv("REPORT_FILENAME", "postgresql_schema_report.md")),
        "include_plpgsql_source": os.getenv("POSTGRES_INCLUDE_PLPGSQL_SOURCE", os.getenv("INCLUDE_PLPGSQL_SOURCE", "true")).lower() == "true",
        "psql_path": os.getenv("POSTGRES_PSQL_PATH", os.getenv("PSQL_PATH", "psql")),
        "connection_timeout": int(os.getenv("POSTGRES_CONNECTION_TIMEOUT", os.getenv("CONNECTION_TIMEOUT", "30"))),
        "query_timeout": int(os.getenv("POSTGRES_QUERY_TIMEOUT", os.getenv("QUERY_TIMEOUT", "300"))),
    }

    return config


def get_psql_cmd(config=None):
    """Get the psql command with proper path."""
    if config is None:
        config = load_config()

    psql_path = config.get("psql_path", "psql")

    if not psql_path or psql_path == "psql":
        return "psql"

    return psql_path


def execute_psql(sql_query, config=None, parse_output=True):
    """
    Execute a SQL query using psql and return results.

    Args:
        sql_query: The SQL query to execute
        config: Configuration dictionary
        parse_output: If True, parse output into list of dictionaries

    Returns:
        List of dictionaries (if parse_output=True) or raw output string
    """
    if config is None:
        config = load_config()

    # Build psql command with pipe-delimited output
    cmd = [
        get_psql_cmd(config),
        '-h', config['host'],
        '-p', str(config['port']),
        '-d', config['database'],
        '-U', config['user'],
        '-t',  # Tuples only (no headers for data when using -t)
        '-A',  # Unaligned output
        '-F', '|',  # Pipe delimiter
        '-c', sql_query
    ]

    # Set PGPASSWORD environment variable
    env = os.environ.copy()
    env['PGPASSWORD'] = config['password']

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=config.get('query_timeout', 300)
        )

        if result.returncode != 0:
            if result.stderr:
                # Check for common errors that we can ignore
                if 'does not exist' in result.stderr.lower():
                    return [] if parse_output else ""
            raise Exception(f"psql error: {result.stderr or result.stdout}")

        output = result.stdout

        if not parse_output:
            return output

        # Parse the output into list of dictionaries
        return parse_psql_output(output, sql_query)

    except subprocess.TimeoutExpired:
        raise Exception(f"Query timed out after {config.get('query_timeout', 300)} seconds")
    except FileNotFoundError:
        raise Exception("psql not found. Please install PostgreSQL client or set PSQL_PATH in .env")


def execute_psql_with_headers(sql_query, config=None):
    """
    Execute a SQL query using psql WITH headers for proper column name mapping.

    Args:
        sql_query: The SQL query to execute
        config: Configuration dictionary

    Returns:
        List of dictionaries with proper column names
    """
    if config is None:
        config = load_config()

    # Build psql command - note: no -t flag, so we get headers
    cmd = [
        get_psql_cmd(config),
        '-h', config['host'],
        '-p', str(config['port']),
        '-d', config['database'],
        '-U', config['user'],
        '-A',  # Unaligned output
        '-F', '|',  # Pipe delimiter
        '-c', sql_query
    ]

    # Set PGPASSWORD environment variable
    env = os.environ.copy()
    env['PGPASSWORD'] = config['password']

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=config.get('query_timeout', 300)
        )

        if result.returncode != 0:
            if result.stderr:
                if 'does not exist' in result.stderr.lower():
                    return []
            raise Exception(f"psql error: {result.stderr or result.stdout}")

        output = result.stdout.strip()
        if not output:
            return []

        lines = output.split('\n')
        if len(lines) < 2:
            return []

        # First line is headers
        headers = [h.strip().upper() for h in lines[0].split('|')]

        # Parse data rows (skip last line which is row count like "(5 rows)")
        results = []
        for line in lines[1:]:
            if line.startswith('(') and line.endswith(')'):
                continue  # Skip row count line
            if not line.strip():
                continue

            values = line.split('|')
            if len(values) != len(headers):
                continue

            row = {}
            for header, value in zip(headers, values):
                if header:
                    row[header] = value.strip() if value.strip() else None

            if row:
                results.append(row)

        return results

    except subprocess.TimeoutExpired:
        raise Exception(f"Query timed out after {config.get('query_timeout', 300)} seconds")
    except FileNotFoundError:
        raise Exception("psql not found. Please install PostgreSQL client or set PSQL_PATH in .env")


def parse_psql_output(output, sql_query=None):
    """
    Parse psql pipe-delimited output into list of dictionaries.

    Since we use -t flag (tuples only), we don't have headers.
    We need to infer column names from the SQL query or use generic names.
    """
    if not output or not output.strip():
        return []

    lines = output.strip().split('\n')
    results = []

    # Extract column names from SELECT query if possible
    headers = extract_column_names_from_query(sql_query) if sql_query else None

    for line in lines:
        if not line.strip():
            continue

        values = [v.strip() for v in line.split('|')]

        if headers and len(values) == len(headers):
            row = {}
            for header, value in zip(headers, values):
                row[header] = value if value else None
            results.append(row)
        else:
            # Use generic column names if we can't parse headers
            row = {f"col{i}": v if v else None for i, v in enumerate(values)}
            results.append(row)

    return results


def extract_column_names_from_query(sql_query):
    """
    Extract column names/aliases from a SELECT query.
    This is a simple parser that handles common cases.
    """
    if not sql_query:
        return None

    sql_upper = sql_query.upper()
    if 'SELECT' not in sql_upper:
        return None

    try:
        # Find SELECT and FROM positions
        select_pos = sql_upper.index('SELECT') + 6
        from_pos = sql_upper.index('FROM')

        # Extract column list
        columns_str = sql_query[select_pos:from_pos].strip()

        # Split by comma (careful with nested parentheses)
        columns = []
        depth = 0
        current = ""
        for char in columns_str:
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            elif char == ',' and depth == 0:
                columns.append(current.strip())
                current = ""
                continue
            current += char
        if current.strip():
            columns.append(current.strip())

        # Extract column names/aliases
        names = []
        for col in columns:
            col = col.strip()
            # Check for AS alias
            col_upper = col.upper()
            if ' AS ' in col_upper:
                as_pos = col_upper.rindex(' AS ')
                alias = col[as_pos + 4:].strip().strip('"').upper()
                names.append(alias)
            elif '.' in col:
                # table.column - take column name
                parts = col.split('.')
                name = parts[-1].strip().strip('"').upper()
                names.append(name)
            else:
                # Just column name
                name = col.strip().strip('"').upper()
                # Handle function calls - take the whole thing as name
                if '(' in name:
                    # Try to find an alias
                    names.append(name.split('(')[0] + "_RESULT")
                else:
                    names.append(name)

        return names if names else None

    except (ValueError, IndexError):
        return None


def execute_query(sql_query, config=None):
    """
    Execute a SQL query and return results as list of dictionaries.
    This is the main function used by collector scripts.
    """
    return execute_psql_with_headers(sql_query, config)


def get_schema(config=None):
    """Get the schema to analyze."""
    if config is None:
        config = load_config()

    return config.get("schema", "public")


def test_connection():
    """Test database connection and print basic info."""
    config = load_config()

    print(f"psql path: {get_psql_cmd(config)}")
    print(f"Connecting to: {config['host']}:{config['port']}/{config['database']}")
    print(f"User: {config['user']}")
    print()

    try:
        # Test connection with version query
        result = execute_psql("SELECT version();", config, parse_output=False)

        if not result or "PostgreSQL" not in result:
            print("Connection failed!")
            return False

        print("Connection successful!")
        print(f"PostgreSQL Version: {result.strip()}")

        # Get current user
        user_result = execute_query("SELECT current_user AS username;", config)
        if user_result:
            print(f"Connected User: {user_result[0].get('USERNAME', 'Unknown')}")

        # Get current database
        db_result = execute_query("SELECT current_database() AS dbname;", config)
        if db_result:
            print(f"Current Database: {db_result[0].get('DBNAME', 'Unknown')}")

        print(f"Schema to analyze: {get_schema(config)}")

        return True

    except FileNotFoundError:
        print("ERROR: psql not found!")
        print("Please ensure PostgreSQL client is installed and either:")
        print("  1. Add it to your system PATH, or")
        print("  2. Set PSQL_PATH in your .env file")
        return False
    except subprocess.TimeoutExpired:
        print("ERROR: Connection timed out!")
        return False
    except Exception as e:
        print(f"Connection failed: {e}")
        return False


def get_postgres_version(config=None):
    """Get PostgreSQL server version."""
    if config is None:
        config = load_config()

    result = execute_query(
        "SELECT setting FROM pg_settings WHERE name = 'server_version';",
        config
    )
    if result:
        return result[0].get('SETTING', 'Unknown')
    return 'Unknown'


# ============================================================================
# COLLECT TYPES MODULE
# ============================================================================

def collect_enum_types(schema, config=None):
    """Collect ENUM types."""
    query = f"""
        SELECT
            t.typname AS type_name,
            n.nspname AS schema_name,
            array_to_string(array_agg(e.enumlabel ORDER BY e.enumsortorder), ', ') AS labels
        FROM pg_type t
        JOIN pg_namespace n ON t.typnamespace = n.oid
        JOIN pg_enum e ON t.oid = e.enumtypid
        WHERE n.nspname = '{schema}'
        GROUP BY t.typname, n.nspname
        ORDER BY t.typname;
    """
    return execute_query(query, config)


def collect_composite_types(schema, config=None):
    """Collect composite (record) types."""
    query = f"""
        SELECT
            t.typname AS type_name,
            n.nspname AS schema_name,
            pg_catalog.format_type(t.oid, NULL) AS type_definition
        FROM pg_type t
        JOIN pg_namespace n ON t.typnamespace = n.oid
        WHERE t.typtype = 'c'
        AND n.nspname = '{schema}'
        AND NOT EXISTS (SELECT 1 FROM pg_class c WHERE c.reltype = t.oid AND c.relkind IN ('r', 'v', 'm'))
        ORDER BY t.typname;
    """
    return execute_query(query, config)


def collect_composite_type_attributes(schema, config=None):
    """Collect attributes of composite types."""
    query = f"""
        SELECT
            t.typname AS type_name,
            a.attname AS attribute_name,
            a.attnum AS attribute_position,
            pg_catalog.format_type(a.atttypid, a.atttypmod) AS attribute_type,
            a.attnotnull AS not_null
        FROM pg_type t
        JOIN pg_namespace n ON t.typnamespace = n.oid
        JOIN pg_attribute a ON t.typrelid = a.attrelid
        WHERE t.typtype = 'c'
        AND n.nspname = '{schema}'
        AND a.attnum > 0
        AND NOT a.attisdropped
        ORDER BY t.typname, a.attnum;
    """
    return execute_query(query, config)


def collect_domain_types(schema, config=None):
    """Collect domain types."""
    query = f"""
        SELECT
            t.typname AS type_name,
            n.nspname AS schema_name,
            pg_catalog.format_type(t.typbasetype, t.typtypmod) AS base_type,
            t.typnotnull AS not_null,
            t.typdefault AS default_value,
            pg_catalog.pg_get_constraintdef(con.oid, true) AS check_constraint
        FROM pg_type t
        JOIN pg_namespace n ON t.typnamespace = n.oid
        LEFT JOIN pg_constraint con ON con.contypid = t.oid
        WHERE t.typtype = 'd'
        AND n.nspname = '{schema}'
        ORDER BY t.typname;
    """
    return execute_query(query, config)


def collect_range_types(schema, config=None):
    """Collect range types."""
    query = f"""
        SELECT
            t.typname AS type_name,
            n.nspname AS schema_name,
            pg_catalog.format_type(r.rngsubtype, NULL) AS subtype
        FROM pg_type t
        JOIN pg_namespace n ON t.typnamespace = n.oid
        JOIN pg_range r ON r.rngtypid = t.oid
        WHERE n.nspname = '{schema}'
        ORDER BY t.typname;
    """
    return execute_query(query, config)


def collect_array_columns(schema, config=None):
    """Collect columns that use array types."""
    query = f"""
        SELECT
            c.relname AS table_name,
            a.attname AS column_name,
            pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
            t.typname AS element_type
        FROM pg_attribute a
        JOIN pg_class c ON a.attrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        JOIN pg_type t ON a.atttypid = t.oid
        WHERE n.nspname = '{schema}'
        AND a.attnum > 0
        AND NOT a.attisdropped
        AND t.typcategory = 'A'
        ORDER BY c.relname, a.attnum;
    """
    return execute_query(query, config)


def collect_json_columns(schema, config=None):
    """Collect JSON and JSONB columns."""
    query = f"""
        SELECT
            c.relname AS table_name,
            a.attname AS column_name,
            pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type
        FROM pg_attribute a
        JOIN pg_class c ON a.attrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        JOIN pg_type t ON a.atttypid = t.oid
        WHERE n.nspname = '{schema}'
        AND a.attnum > 0
        AND NOT a.attisdropped
        AND t.typname IN ('json', 'jsonb')
        ORDER BY c.relname, a.attnum;
    """
    return execute_query(query, config)


def collect_xml_columns(schema, config=None):
    """Collect XML columns."""
    query = f"""
        SELECT
            c.relname AS table_name,
            a.attname AS column_name,
            pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type
        FROM pg_attribute a
        JOIN pg_class c ON a.attrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        JOIN pg_type t ON a.atttypid = t.oid
        WHERE n.nspname = '{schema}'
        AND a.attnum > 0
        AND NOT a.attisdropped
        AND t.typname = 'xml'
        ORDER BY c.relname, a.attnum;
    """
    return execute_query(query, config)


def collect_geometric_columns(schema, config=None):
    """Collect geometric type columns (point, line, box, etc.)."""
    query = f"""
        SELECT
            c.relname AS table_name,
            a.attname AS column_name,
            pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type
        FROM pg_attribute a
        JOIN pg_class c ON a.attrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        JOIN pg_type t ON a.atttypid = t.oid
        WHERE n.nspname = '{schema}'
        AND a.attnum > 0
        AND NOT a.attisdropped
        AND t.typname IN ('point', 'line', 'lseg', 'box', 'path', 'polygon', 'circle')
        ORDER BY c.relname, a.attnum;
    """
    return execute_query(query, config)


def collect_network_columns(schema, config=None):
    """Collect network type columns (inet, cidr, macaddr)."""
    query = f"""
        SELECT
            c.relname AS table_name,
            a.attname AS column_name,
            pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type
        FROM pg_attribute a
        JOIN pg_class c ON a.attrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        JOIN pg_type t ON a.atttypid = t.oid
        WHERE n.nspname = '{schema}'
        AND a.attnum > 0
        AND NOT a.attisdropped
        AND t.typname IN ('inet', 'cidr', 'macaddr', 'macaddr8')
        ORDER BY c.relname, a.attnum;
    """
    return execute_query(query, config)


def collect_all_types(config=None):
    """Main function to collect all type information."""
    if config is None:
        config = load_config()

    schema = get_schema(config)

    data = {
        "schema": schema,
        "enum_types": collect_enum_types(schema, config),
        "composite_types": collect_composite_types(schema, config),
        "composite_type_attributes": collect_composite_type_attributes(schema, config),
        "domain_types": collect_domain_types(schema, config),
        "range_types": collect_range_types(schema, config),
        "array_columns": collect_array_columns(schema, config),
        "json_columns": collect_json_columns(schema, config),
        "xml_columns": collect_xml_columns(schema, config),
        "geometric_columns": collect_geometric_columns(schema, config),
        "network_columns": collect_network_columns(schema, config),
    }

    return data


# ============================================================================
# COLLECT TABLES MODULE
# ============================================================================

def collect_tables(schema, config=None):
    """Collect all tables with their properties."""
    query = f"""
        SELECT
            c.relname AS table_name,
            n.nspname AS schema_name,
            pg_catalog.pg_get_userbyid(c.relowner) AS table_owner,
            c.relkind AS table_type,
            c.relhasindex AS has_indexes,
            c.relhasrules AS has_rules,
            c.relhastriggers AS has_triggers,
            c.relrowsecurity AS has_rls,
            c.relforcerowsecurity AS force_rls,
            c.relispartition AS is_partition,
            pg_catalog.obj_description(c.oid, 'pg_class') AS description,
            CASE WHEN c.relpersistence = 'u' THEN true ELSE false END AS unlogged,
            CASE WHEN c.relpersistence = 't' THEN true ELSE false END AS temporary
        FROM pg_class c
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = '{schema}'
        AND c.relkind IN ('r', 'p')
        ORDER BY c.relname;
    """
    return execute_query(query, config)


def collect_columns(schema, config=None):
    """Collect all columns for each table."""
    query = f"""
        SELECT
            c.relname AS table_name,
            a.attname AS column_name,
            a.attnum AS ordinal_position,
            pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
            a.attnotnull AS not_null,
            pg_catalog.pg_get_expr(d.adbin, d.adrelid) AS column_default,
            CASE WHEN a.attidentity = 'a' THEN 'ALWAYS'
                 WHEN a.attidentity = 'd' THEN 'BY DEFAULT'
                 ELSE NULL END AS identity_generation,
            CASE WHEN a.attgenerated = 's' THEN true ELSE false END AS is_generated,
            pg_catalog.col_description(a.attrelid, a.attnum) AS description
        FROM pg_attribute a
        JOIN pg_class c ON a.attrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        LEFT JOIN pg_attrdef d ON a.attrelid = d.adrelid AND a.attnum = d.adnum
        WHERE n.nspname = '{schema}'
        AND c.relkind IN ('r', 'p', 'v', 'm')
        AND a.attnum > 0
        AND NOT a.attisdropped
        ORDER BY c.relname, a.attnum;
    """
    return execute_query(query, config)


def collect_identity_columns(schema, config=None):
    """Collect identity column details."""
    query = f"""
        SELECT
            c.relname AS table_name,
            a.attname AS column_name,
            a.attidentity AS identity_type,
            seq.seqstart AS start_value,
            seq.seqincrement AS increment,
            seq.seqmin AS min_value,
            seq.seqmax AS max_value,
            seq.seqcache AS cache,
            seq.seqcycle AS cycle
        FROM pg_attribute a
        JOIN pg_class c ON a.attrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        LEFT JOIN pg_depend d ON d.refobjid = c.oid AND d.refobjsubid = a.attnum
        LEFT JOIN pg_class seq_class ON d.objid = seq_class.oid AND seq_class.relkind = 'S'
        LEFT JOIN pg_sequence seq ON seq.seqrelid = seq_class.oid
        WHERE n.nspname = '{schema}'
        AND a.attidentity != ''
        ORDER BY c.relname, a.attnum;
    """
    return execute_query(query, config)


def collect_generated_columns(schema, config=None):
    """Collect generated (computed) columns."""
    query = f"""
        SELECT
            c.relname AS table_name,
            a.attname AS column_name,
            pg_catalog.pg_get_expr(d.adbin, d.adrelid) AS generation_expression
        FROM pg_attribute a
        JOIN pg_class c ON a.attrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        JOIN pg_attrdef d ON a.attrelid = d.adrelid AND a.attnum = d.adnum
        WHERE n.nspname = '{schema}'
        AND a.attgenerated = 's'
        ORDER BY c.relname, a.attnum;
    """
    return execute_query(query, config)


def collect_serial_columns(schema, config=None):
    """Detect SERIAL/BIGSERIAL columns (columns with sequence defaults)."""
    query = f"""
        SELECT
            c.relname AS table_name,
            a.attname AS column_name,
            pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
            pg_catalog.pg_get_expr(d.adbin, d.adrelid) AS default_value,
            seq.relname AS sequence_name
        FROM pg_attribute a
        JOIN pg_class c ON a.attrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        JOIN pg_attrdef d ON a.attrelid = d.adrelid AND a.attnum = d.adnum
        LEFT JOIN pg_depend dep ON dep.refobjid = c.oid AND dep.refobjsubid = a.attnum
            AND dep.deptype = 'a'
        LEFT JOIN pg_class seq ON dep.objid = seq.oid AND seq.relkind = 'S'
        WHERE n.nspname = '{schema}'
        AND pg_catalog.pg_get_expr(d.adbin, d.adrelid) LIKE 'nextval%'
        ORDER BY c.relname, a.attnum;
    """
    return execute_query(query, config)


def collect_partitioned_tables(schema, config=None):
    """Collect partitioned table details."""
    query = f"""
        SELECT
            c.relname AS table_name,
            pg_catalog.pg_get_partkeydef(c.oid) AS partition_key,
            pt.partstrat AS partition_strategy
        FROM pg_class c
        JOIN pg_namespace n ON c.relnamespace = n.oid
        JOIN pg_partitioned_table pt ON pt.partrelid = c.oid
        WHERE n.nspname = '{schema}'
        ORDER BY c.relname;
    """
    return execute_query(query, config)


def collect_partitions(schema, config=None):
    """Collect partition information."""
    query = f"""
        SELECT
            parent.relname AS parent_table,
            child.relname AS partition_name,
            pg_catalog.pg_get_expr(child.relpartbound, child.oid) AS partition_bound
        FROM pg_inherits i
        JOIN pg_class parent ON i.inhparent = parent.oid
        JOIN pg_class child ON i.inhrelid = child.oid
        JOIN pg_namespace n ON parent.relnamespace = n.oid
        WHERE n.nspname = '{schema}'
        AND parent.relkind = 'p'
        ORDER BY parent.relname, child.relname;
    """
    return execute_query(query, config)


def collect_inheritance(schema, config=None):
    """Collect table inheritance relationships."""
    query = f"""
        SELECT
            parent.relname AS parent_table,
            child.relname AS child_table,
            i.inhseqno AS inheritance_order
        FROM pg_inherits i
        JOIN pg_class parent ON i.inhparent = parent.oid
        JOIN pg_class child ON i.inhrelid = child.oid
        JOIN pg_namespace n ON parent.relnamespace = n.oid
        WHERE n.nspname = '{schema}'
        AND parent.relkind = 'r'
        ORDER BY parent.relname, i.inhseqno;
    """
    return execute_query(query, config)


def collect_constraints(schema, config=None):
    """Collect all constraints."""
    query = f"""
        SELECT
            con.conname AS constraint_name,
            con.contype AS constraint_type,
            c.relname AS table_name,
            pg_catalog.pg_get_constraintdef(con.oid, true) AS definition,
            con.condeferrable AS deferrable,
            con.condeferred AS deferred,
            con.convalidated AS validated
        FROM pg_constraint con
        JOIN pg_class c ON con.conrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = '{schema}'
        ORDER BY c.relname, con.contype, con.conname;
    """
    return execute_query(query, config)


def collect_check_constraints(schema, config=None):
    """Collect CHECK constraints with details."""
    query = f"""
        SELECT
            con.conname AS constraint_name,
            c.relname AS table_name,
            pg_catalog.pg_get_constraintdef(con.oid, true) AS check_clause
        FROM pg_constraint con
        JOIN pg_class c ON con.conrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = '{schema}'
        AND con.contype = 'c'
        ORDER BY c.relname, con.conname;
    """
    return execute_query(query, config)


def collect_foreign_keys(schema, config=None):
    """Collect foreign key constraints with referenced table info."""
    query = f"""
        SELECT
            con.conname AS constraint_name,
            c.relname AS table_name,
            a.attname AS column_name,
            ref_c.relname AS referenced_table,
            ref_a.attname AS referenced_column,
            con.confupdtype AS update_action,
            con.confdeltype AS delete_action,
            con.condeferrable AS deferrable,
            con.condeferred AS deferred
        FROM pg_constraint con
        JOIN pg_class c ON con.conrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        JOIN pg_class ref_c ON con.confrelid = ref_c.oid
        CROSS JOIN LATERAL unnest(con.conkey, con.confkey) WITH ORDINALITY AS cols(conkey, confkey, ord)
        JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = cols.conkey
        JOIN pg_attribute ref_a ON ref_a.attrelid = ref_c.oid AND ref_a.attnum = cols.confkey
        WHERE n.nspname = '{schema}'
        AND con.contype = 'f'
        ORDER BY c.relname, con.conname, cols.ord;
    """
    return execute_query(query, config)


def collect_table_ddl(tables, schema, config=None):
    """
    Collect DDL for all tables using pg_dump or reconstructed DDL.
    """
    ddl_dict = {}
    for table in tables:
        table_name = table.get('TABLE_NAME')
        if table_name:
            # Get basic CREATE TABLE statement
            query = f"""
                SELECT
                    'CREATE TABLE ' || quote_ident('{schema}') || '.' || quote_ident('{table_name}') || ' (' ||
                    string_agg(
                        quote_ident(a.attname) || ' ' ||
                        pg_catalog.format_type(a.atttypid, a.atttypmod) ||
                        CASE WHEN a.attnotnull THEN ' NOT NULL' ELSE '' END ||
                        CASE WHEN d.adbin IS NOT NULL THEN ' DEFAULT ' || pg_catalog.pg_get_expr(d.adbin, d.adrelid) ELSE '' END,
                        ', '
                        ORDER BY a.attnum
                    ) || ')' AS ddl
                FROM pg_attribute a
                JOIN pg_class c ON a.attrelid = c.oid
                JOIN pg_namespace n ON c.relnamespace = n.oid
                LEFT JOIN pg_attrdef d ON a.attrelid = d.adrelid AND a.attnum = d.adnum
                WHERE n.nspname = '{schema}'
                AND c.relname = '{table_name}'
                AND a.attnum > 0
                AND NOT a.attisdropped
                GROUP BY c.oid;
            """
            result = execute_query(query, config)
            if result and result[0].get('DDL'):
                ddl_dict[table_name] = result[0]['DDL']

    return ddl_dict


def collect_all_tables(config=None):
    """Main function to collect all table information."""
    if config is None:
        config = load_config()

    schema = get_schema(config)

    # First collect basic table info
    tables = collect_tables(schema, config)

    data = {
        "schema": schema,
        "tables": tables,
        "columns": collect_columns(schema, config),
        "identity_columns": collect_identity_columns(schema, config),
        "generated_columns": collect_generated_columns(schema, config),
        "serial_columns": collect_serial_columns(schema, config),
        "partitioned_tables": collect_partitioned_tables(schema, config),
        "partitions": collect_partitions(schema, config),
        "inheritance": collect_inheritance(schema, config),
        "constraints": collect_constraints(schema, config),
        "check_constraints": collect_check_constraints(schema, config),
        "foreign_keys": collect_foreign_keys(schema, config),
    }

    # Collect DDL for all tables
    print("  Collecting table DDL statements...")
    data["table_ddl"] = collect_table_ddl(tables, schema, config)

    return data


# ============================================================================
# COLLECT INDEXES MODULE
# ============================================================================

def collect_indexes(schema, config=None):
    """Collect all indexes with their properties."""
    query = f"""
        SELECT
            i.relname AS index_name,
            t.relname AS table_name,
            am.amname AS index_type,
            ix.indisunique AS is_unique,
            ix.indisprimary AS is_primary,
            ix.indisvalid AS is_valid,
            ix.indisclustered AS is_clustered,
            pg_catalog.pg_get_indexdef(i.oid) AS index_definition,
            pg_catalog.obj_description(i.oid, 'pg_class') AS description
        FROM pg_index ix
        JOIN pg_class i ON ix.indexrelid = i.oid
        JOIN pg_class t ON ix.indrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        JOIN pg_am am ON i.relam = am.oid
        WHERE n.nspname = '{schema}'
        ORDER BY t.relname, i.relname;
    """
    return execute_query(query, config)


def collect_index_columns(schema, config=None):
    """Collect index column mappings."""
    query = f"""
        SELECT
            i.relname AS index_name,
            t.relname AS table_name,
            a.attname AS column_name,
            k.ord AS column_position,
            CASE WHEN ix.indoption[k.ord - 1] & 1 = 1 THEN 'DESC' ELSE 'ASC' END AS sort_order,
            CASE WHEN ix.indoption[k.ord - 1] & 2 = 2 THEN 'NULLS FIRST' ELSE 'NULLS LAST' END AS nulls_order
        FROM pg_index ix
        JOIN pg_class i ON ix.indexrelid = i.oid
        JOIN pg_class t ON ix.indrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        CROSS JOIN LATERAL unnest(ix.indkey) WITH ORDINALITY AS k(attnum, ord)
        LEFT JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum
        WHERE n.nspname = '{schema}'
        AND k.attnum > 0
        ORDER BY i.relname, k.ord;
    """
    return execute_query(query, config)


def collect_index_expressions(schema, config=None):
    """Collect expression (function-based) indexes."""
    query = f"""
        SELECT
            i.relname AS index_name,
            t.relname AS table_name,
            pg_catalog.pg_get_indexdef(i.oid) AS index_definition
        FROM pg_index ix
        JOIN pg_class i ON ix.indexrelid = i.oid
        JOIN pg_class t ON ix.indrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        WHERE n.nspname = '{schema}'
        AND ix.indexprs IS NOT NULL
        ORDER BY t.relname, i.relname;
    """
    return execute_query(query, config)


def collect_partial_indexes(schema, config=None):
    """Collect partial indexes (indexes with WHERE clause)."""
    query = f"""
        SELECT
            i.relname AS index_name,
            t.relname AS table_name,
            pg_catalog.pg_get_expr(ix.indpred, ix.indrelid) AS predicate,
            pg_catalog.pg_get_indexdef(i.oid) AS index_definition
        FROM pg_index ix
        JOIN pg_class i ON ix.indexrelid = i.oid
        JOIN pg_class t ON ix.indrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        WHERE n.nspname = '{schema}'
        AND ix.indpred IS NOT NULL
        ORDER BY t.relname, i.relname;
    """
    return execute_query(query, config)


def collect_unique_indexes(schema, config=None):
    """Collect unique indexes (not from constraints)."""
    query = f"""
        SELECT
            i.relname AS index_name,
            t.relname AS table_name,
            pg_catalog.pg_get_indexdef(i.oid) AS index_definition
        FROM pg_index ix
        JOIN pg_class i ON ix.indexrelid = i.oid
        JOIN pg_class t ON ix.indrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        WHERE n.nspname = '{schema}'
        AND ix.indisunique
        AND NOT ix.indisprimary
        ORDER BY t.relname, i.relname;
    """
    return execute_query(query, config)


def collect_all_indexes(config=None):
    """Main function to collect all index information."""
    if config is None:
        config = load_config()

    schema = get_schema(config)

    data = {
        "schema": schema,
        "indexes": collect_indexes(schema, config),
        "index_columns": collect_index_columns(schema, config),
        "index_expressions": collect_index_expressions(schema, config),
        "partial_indexes": collect_partial_indexes(schema, config),
        "unique_indexes": collect_unique_indexes(schema, config),
    }

    return data


# ============================================================================
# COLLECT VIEWS MODULE
# ============================================================================

def collect_views(schema, config=None):
    """Collect all views with their properties."""
    query = f"""
        SELECT
            c.relname AS view_name,
            n.nspname AS schema_name,
            pg_catalog.pg_get_userbyid(c.relowner) AS view_owner,
            pg_catalog.pg_get_viewdef(c.oid, true) AS view_definition,
            CASE WHEN c.relkind = 'm' THEN true ELSE false END AS is_materialized,
            pg_catalog.obj_description(c.oid, 'pg_class') AS description
        FROM pg_class c
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = '{schema}'
        AND c.relkind = 'v'
        ORDER BY c.relname;
    """
    return execute_query(query, config)


def collect_view_columns(schema, config=None):
    """Collect view column details."""
    query = f"""
        SELECT
            c.relname AS view_name,
            a.attname AS column_name,
            a.attnum AS ordinal_position,
            pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type
        FROM pg_attribute a
        JOIN pg_class c ON a.attrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = '{schema}'
        AND c.relkind = 'v'
        AND a.attnum > 0
        AND NOT a.attisdropped
        ORDER BY c.relname, a.attnum;
    """
    return execute_query(query, config)


def collect_materialized_views(schema, config=None):
    """Collect materialized view details."""
    query = f"""
        SELECT
            c.relname AS mview_name,
            n.nspname AS schema_name,
            pg_catalog.pg_get_userbyid(c.relowner) AS mview_owner,
            pg_catalog.pg_get_viewdef(c.oid, true) AS view_definition,
            c.relispopulated AS is_populated,
            pg_catalog.obj_description(c.oid, 'pg_class') AS description
        FROM pg_class c
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = '{schema}'
        AND c.relkind = 'm'
        ORDER BY c.relname;
    """
    return execute_query(query, config)


def collect_mview_indexes(schema, config=None):
    """Collect indexes on materialized views."""
    query = f"""
        SELECT
            mv.relname AS mview_name,
            i.relname AS index_name,
            am.amname AS index_type,
            ix.indisunique AS is_unique,
            pg_catalog.pg_get_indexdef(i.oid) AS index_definition
        FROM pg_index ix
        JOIN pg_class i ON ix.indexrelid = i.oid
        JOIN pg_class mv ON ix.indrelid = mv.oid
        JOIN pg_namespace n ON mv.relnamespace = n.oid
        JOIN pg_am am ON i.relam = am.oid
        WHERE n.nspname = '{schema}'
        AND mv.relkind = 'm'
        ORDER BY mv.relname, i.relname;
    """
    return execute_query(query, config)


def collect_all_views(config=None):
    """Main function to collect all view information."""
    if config is None:
        config = load_config()

    schema = get_schema(config)

    data = {
        "schema": schema,
        "views": collect_views(schema, config),
        "view_columns": collect_view_columns(schema, config),
        "materialized_views": collect_materialized_views(schema, config),
        "mview_indexes": collect_mview_indexes(schema, config),
    }

    return data


# ============================================================================
# COLLECT PLPGSQL MODULE
# ============================================================================

def collect_functions(schema, config=None):
    """Collect stored functions."""
    query = f"""
        SELECT
            p.proname AS function_name,
            n.nspname AS schema_name,
            pg_catalog.pg_get_userbyid(p.proowner) AS owner,
            l.lanname AS language,
            p.prokind AS kind,
            p.provolatile AS volatility,
            p.proisstrict AS is_strict,
            p.prosecdef AS security_definer,
            p.proretset AS returns_set,
            pg_catalog.format_type(p.prorettype, NULL) AS return_type,
            pg_catalog.pg_get_function_arguments(p.oid) AS arguments,
            pg_catalog.pg_get_function_identity_arguments(p.oid) AS identity_arguments,
            pg_catalog.obj_description(p.oid, 'pg_proc') AS description
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        JOIN pg_language l ON p.prolang = l.oid
        WHERE n.nspname = '{schema}'
        AND p.prokind = 'f'
        ORDER BY p.proname;
    """
    return execute_query(query, config)


def collect_procedures(schema, config=None):
    """Collect stored procedures (PostgreSQL 11+)."""
    query = f"""
        SELECT
            p.proname AS procedure_name,
            n.nspname AS schema_name,
            pg_catalog.pg_get_userbyid(p.proowner) AS owner,
            l.lanname AS language,
            p.prosecdef AS security_definer,
            pg_catalog.pg_get_function_arguments(p.oid) AS arguments,
            pg_catalog.obj_description(p.oid, 'pg_proc') AS description
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        JOIN pg_language l ON p.prolang = l.oid
        WHERE n.nspname = '{schema}'
        AND p.prokind = 'p'
        ORDER BY p.proname;
    """
    try:
        return execute_query(query, config)
    except:
        # PostgreSQL < 11 doesn't have procedures
        return []


def collect_function_arguments(schema, config=None):
    """Collect function/procedure argument details."""
    query = f"""
        SELECT
            p.proname AS function_name,
            unnest(p.proargnames) AS argument_name,
            unnest(p.proargtypes::regtype[]) AS argument_type,
            unnest(p.proargmodes) AS argument_mode
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = '{schema}'
        AND p.proargnames IS NOT NULL
        ORDER BY p.proname;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_function_source(schema, config=None):
    """Collect function/procedure source code."""
    query = f"""
        SELECT
            p.proname AS function_name,
            p.prokind AS kind,
            l.lanname AS language,
            p.prosrc AS source_code
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        JOIN pg_language l ON p.prolang = l.oid
        WHERE n.nspname = '{schema}'
        ORDER BY p.proname;
    """
    return execute_query(query, config)


def collect_triggers(schema, config=None):
    """Collect all triggers."""
    query = f"""
        SELECT
            t.tgname AS trigger_name,
            c.relname AS table_name,
            n.nspname AS schema_name,
            CASE
                WHEN t.tgtype & 2 = 2 THEN 'BEFORE'
                WHEN t.tgtype & 64 = 64 THEN 'INSTEAD OF'
                ELSE 'AFTER'
            END AS timing,
            CASE
                WHEN t.tgtype & 4 = 4 THEN 'INSERT'
                WHEN t.tgtype & 8 = 8 THEN 'DELETE'
                WHEN t.tgtype & 16 = 16 THEN 'UPDATE'
                WHEN t.tgtype & 32 = 32 THEN 'TRUNCATE'
                ELSE 'UNKNOWN'
            END AS event,
            CASE WHEN t.tgtype & 1 = 1 THEN 'ROW' ELSE 'STATEMENT' END AS orientation,
            t.tgenabled AS enabled,
            pg_catalog.pg_get_triggerdef(t.oid, true) AS definition
        FROM pg_trigger t
        JOIN pg_class c ON t.tgrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = '{schema}'
        AND NOT t.tgisinternal
        ORDER BY c.relname, t.tgname;
    """
    return execute_query(query, config)


def collect_trigger_functions(schema, config=None):
    """Collect trigger function definitions."""
    query = f"""
        SELECT
            p.proname AS function_name,
            n.nspname AS schema_name,
            l.lanname AS language,
            p.prosrc AS source_code,
            pg_catalog.obj_description(p.oid, 'pg_proc') AS description
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        JOIN pg_language l ON p.prolang = l.oid
        WHERE n.nspname = '{schema}'
        AND p.prorettype = 'trigger'::regtype
        ORDER BY p.proname;
    """
    return execute_query(query, config)


def collect_event_triggers(config=None):
    """Collect event triggers (database-level)."""
    query = """
        SELECT
            evtname AS trigger_name,
            evtevent AS event,
            evtenabled AS enabled,
            evtowner::regrole AS owner,
            evtfoid::regproc AS function_name,
            evttags AS tags
        FROM pg_event_trigger
        ORDER BY evtname;
    """
    return execute_query(query, config)


def collect_aggregates(schema, config=None):
    """Collect custom aggregate functions."""
    query = f"""
        SELECT
            p.proname AS aggregate_name,
            n.nspname AS schema_name,
            pg_catalog.format_type(a.aggtranstype, NULL) AS state_type,
            a.agginitval AS initial_value,
            sf.proname AS state_function,
            ff.proname AS final_function
        FROM pg_aggregate a
        JOIN pg_proc p ON a.aggfnoid = p.oid
        JOIN pg_namespace n ON p.pronamespace = n.oid
        JOIN pg_proc sf ON a.aggtransfn = sf.oid
        LEFT JOIN pg_proc ff ON a.aggfinalfn = ff.oid
        WHERE n.nspname = '{schema}'
        ORDER BY p.proname;
    """
    return execute_query(query, config)


def collect_operators(schema, config=None):
    """Collect custom operators."""
    query = f"""
        SELECT
            o.oprname AS operator_name,
            n.nspname AS schema_name,
            pg_catalog.format_type(o.oprleft, NULL) AS left_type,
            pg_catalog.format_type(o.oprright, NULL) AS right_type,
            pg_catalog.format_type(o.oprresult, NULL) AS result_type,
            o.oprcode::regproc AS function_name,
            o.oprcom::regoper AS commutator,
            o.oprnegate::regoper AS negator
        FROM pg_operator o
        JOIN pg_namespace n ON o.oprnamespace = n.oid
        WHERE n.nspname = '{schema}'
        ORDER BY o.oprname;
    """
    return execute_query(query, config)


def collect_all_plpgsql(config=None):
    """Main function to collect all PL/pgSQL information."""
    if config is None:
        config = load_config()

    schema = get_schema(config)
    include_source = config.get("include_plpgsql_source", True)

    data = {
        "schema": schema,
        "functions": collect_functions(schema, config),
        "procedures": collect_procedures(schema, config),
        "function_arguments": collect_function_arguments(schema, config),
        "triggers": collect_triggers(schema, config),
        "trigger_functions": collect_trigger_functions(schema, config),
        "event_triggers": collect_event_triggers(config),
        "aggregates": collect_aggregates(schema, config),
        "operators": collect_operators(schema, config),
    }

    if include_source:
        print("  Collecting PL/pgSQL source code...")
        data["function_source"] = collect_function_source(schema, config)

    return data


# ============================================================================
# COLLECT SEQUENCES MODULE
# ============================================================================

def collect_sequences(schema, config=None):
    """Collect sequences."""
    query = f"""
        SELECT
            c.relname AS sequence_name,
            n.nspname AS schema_name,
            pg_catalog.pg_get_userbyid(c.relowner) AS owner,
            s.seqstart AS start_value,
            s.seqmin AS min_value,
            s.seqmax AS max_value,
            s.seqincrement AS increment,
            s.seqcache AS cache,
            s.seqcycle AS cycle,
            pg_catalog.format_type(s.seqtypid, NULL) AS data_type
        FROM pg_sequence s
        JOIN pg_class c ON s.seqrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = '{schema}'
        ORDER BY c.relname;
    """
    return execute_query(query, config)


def collect_sequence_usage(schema, config=None):
    """Collect which columns use which sequences."""
    query = f"""
        SELECT
            seq.relname AS sequence_name,
            tab.relname AS table_name,
            a.attname AS column_name,
            pg_catalog.pg_get_serial_sequence(quote_ident(n.nspname) || '.' || quote_ident(tab.relname), a.attname) AS serial_sequence
        FROM pg_depend d
        JOIN pg_class seq ON d.objid = seq.oid AND seq.relkind = 'S'
        JOIN pg_class tab ON d.refobjid = tab.oid AND tab.relkind = 'r'
        JOIN pg_namespace n ON tab.relnamespace = n.oid
        JOIN pg_attribute a ON a.attrelid = tab.oid AND a.attnum = d.refobjsubid
        WHERE n.nspname = '{schema}'
        AND d.deptype IN ('a', 'i')
        ORDER BY tab.relname, a.attname;
    """
    return execute_query(query, config)


def collect_all_sequences(config=None):
    """Main function to collect all sequence information."""
    if config is None:
        config = load_config()

    schema = get_schema(config)

    data = {
        "schema": schema,
        "sequences": collect_sequences(schema, config),
        "sequence_usage": collect_sequence_usage(schema, config),
    }

    return data


# ============================================================================
# COLLECT SECURITY MODULE
# ============================================================================

def collect_table_privileges(schema, config=None):
    """Collect table-level privileges."""
    query = f"""
        SELECT
            c.relname AS table_name,
            grantee.rolname AS grantee,
            grantor.rolname AS grantor,
            p.privilege_type,
            p.is_grantable
        FROM pg_class c
        JOIN pg_namespace n ON c.relnamespace = n.oid
        CROSS JOIN LATERAL aclexplode(c.relacl) AS p
        JOIN pg_roles grantee ON p.grantee = grantee.oid
        JOIN pg_roles grantor ON p.grantor = grantor.oid
        WHERE n.nspname = '{schema}'
        AND c.relkind IN ('r', 'v', 'm', 'p')
        ORDER BY c.relname, grantee.rolname;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_column_privileges(schema, config=None):
    """Collect column-level privileges."""
    query = f"""
        SELECT
            table_name,
            column_name,
            grantee,
            privilege_type,
            is_grantable
        FROM information_schema.column_privileges
        WHERE table_schema = '{schema}'
        ORDER BY table_name, column_name, grantee;
    """
    return execute_query(query, config)


def collect_rls_policies(schema, config=None):
    """Collect Row Level Security policies."""
    query = f"""
        SELECT
            schemaname AS schema_name,
            tablename AS table_name,
            policyname AS policy_name,
            permissive,
            roles,
            cmd AS command,
            qual AS using_expression,
            with_check AS with_check_expression
        FROM pg_policies
        WHERE schemaname = '{schema}'
        ORDER BY tablename, policyname;
    """
    return execute_query(query, config)


def collect_roles(config=None):
    """Collect roles used in the schema."""
    query = """
        SELECT
            rolname AS role_name,
            rolsuper AS is_superuser,
            rolinherit AS inherit,
            rolcreaterole AS can_create_role,
            rolcreatedb AS can_create_db,
            rolcanlogin AS can_login,
            rolreplication AS replication,
            rolconnlimit AS connection_limit,
            rolvaliduntil AS valid_until
        FROM pg_roles
        WHERE rolname NOT LIKE 'pg_%'
        ORDER BY rolname;
    """
    return execute_query(query, config)


def collect_all_security(config=None):
    """Main function to collect all security information."""
    if config is None:
        config = load_config()

    schema = get_schema(config)

    data = {
        "schema": schema,
        "table_privileges": collect_table_privileges(schema, config),
        "column_privileges": collect_column_privileges(schema, config),
        "rls_policies": collect_rls_policies(schema, config),
        "roles": collect_roles(config),
    }

    return data


# ============================================================================
# COLLECT EXTENSIONS MODULE
# ============================================================================

def collect_extensions(config=None):
    """Collect installed extensions."""
    query = """
        SELECT
            e.extname AS extension_name,
            e.extversion AS version,
            n.nspname AS schema_name,
            e.extrelocatable AS relocatable,
            pg_catalog.obj_description(e.oid, 'pg_extension') AS description
        FROM pg_extension e
        JOIN pg_namespace n ON e.extnamespace = n.oid
        ORDER BY e.extname;
    """
    return execute_query(query, config)


def collect_extension_objects(schema, config=None):
    """Collect objects created by extensions."""
    query = f"""
        SELECT
            e.extname AS extension_name,
            c.relname AS object_name,
            c.relkind AS object_type
        FROM pg_extension e
        JOIN pg_depend d ON d.refobjid = e.oid
        JOIN pg_class c ON d.objid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = '{schema}'
        ORDER BY e.extname, c.relname;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_all_extensions(config=None):
    """Main function to collect all extension information."""
    if config is None:
        config = load_config()

    schema = get_schema(config)

    data = {
        "schema": schema,
        "extensions": collect_extensions(config),
        "extension_objects": collect_extension_objects(schema, config),
    }

    return data


# ============================================================================
# COLLECT MISC MODULE
# ============================================================================

def collect_schemas(config=None):
    """Collect schema information."""
    query = """
        SELECT
            n.nspname AS schema_name,
            pg_catalog.pg_get_userbyid(n.nspowner) AS owner,
            pg_catalog.obj_description(n.oid, 'pg_namespace') AS description
        FROM pg_namespace n
        WHERE n.nspname NOT LIKE 'pg_%'
        AND n.nspname != 'information_schema'
        ORDER BY n.nspname;
    """
    return execute_query(query, config)


def collect_foreign_tables(schema, config=None):
    """Collect foreign tables (FDW)."""
    query = f"""
        SELECT
            c.relname AS table_name,
            n.nspname AS schema_name,
            s.srvname AS server_name,
            pg_catalog.array_to_string(ARRAY(
                SELECT pg_catalog.quote_ident(option_name) || ' ' ||
                       pg_catalog.quote_literal(option_value)
                FROM pg_catalog.pg_options_to_table(ft.ftoptions)
            ), ', ') AS options
        FROM pg_foreign_table ft
        JOIN pg_class c ON ft.ftrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        JOIN pg_foreign_server s ON ft.ftserver = s.oid
        WHERE n.nspname = '{schema}'
        ORDER BY c.relname;
    """
    return execute_query(query, config)


def collect_foreign_servers(config=None):
    """Collect foreign servers."""
    query = """
        SELECT
            s.srvname AS server_name,
            s.srvowner::regrole AS owner,
            f.fdwname AS fdw_name,
            pg_catalog.array_to_string(ARRAY(
                SELECT pg_catalog.quote_ident(option_name) || ' ' ||
                       pg_catalog.quote_literal(option_value)
                FROM pg_catalog.pg_options_to_table(s.srvoptions)
            ), ', ') AS options
        FROM pg_foreign_server s
        JOIN pg_foreign_data_wrapper f ON s.srvfdw = f.oid
        ORDER BY s.srvname;
    """
    return execute_query(query, config)


def collect_publications(config=None):
    """Collect logical replication publications."""
    query = """
        SELECT
            pubname AS publication_name,
            pubowner::regrole AS owner,
            puballtables AS all_tables,
            pubinsert AS publish_insert,
            pubupdate AS publish_update,
            pubdelete AS publish_delete,
            pubtruncate AS publish_truncate
        FROM pg_publication
        ORDER BY pubname;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_subscriptions(config=None):
    """Collect logical replication subscriptions."""
    query = """
        SELECT
            subname AS subscription_name,
            subowner::regrole AS owner,
            subenabled AS enabled,
            subconninfo AS connection_info,
            subslotname AS slot_name,
            subsynccommit AS sync_commit,
            subpublications AS publications
        FROM pg_subscription
        ORDER BY subname;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_rules(schema, config=None):
    """Collect rewrite rules."""
    query = f"""
        SELECT
            r.rulename AS rule_name,
            c.relname AS table_name,
            r.ev_type AS event,
            r.is_instead AS instead,
            pg_catalog.pg_get_ruledef(r.oid, true) AS definition
        FROM pg_rewrite r
        JOIN pg_class c ON r.ev_class = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = '{schema}'
        AND r.rulename != '_RETURN'
        ORDER BY c.relname, r.rulename;
    """
    return execute_query(query, config)


def collect_policies(schema, config=None):
    """Collect RLS policies (alias for collect_rls_policies)."""
    return collect_rls_policies(schema, config)


def collect_all_misc(config=None):
    """Main function to collect all miscellaneous information."""
    if config is None:
        config = load_config()

    schema = get_schema(config)

    data = {
        "schema": schema,
        "schemas": collect_schemas(config),
        "foreign_tables": collect_foreign_tables(schema, config),
        "foreign_servers": collect_foreign_servers(config),
        "publications": collect_publications(config),
        "subscriptions": collect_subscriptions(config),
        "rules": collect_rules(schema, config),
        "policies": collect_policies(schema, config),
    }

    return data


# ============================================================================
# COLLECT FULL-TEXT SEARCH MODULE
# ============================================================================

def collect_text_search_configs(schema, config=None):
    """Collect text search configurations."""
    query = f"""
        SELECT
            c.cfgname AS config_name,
            n.nspname AS schema_name,
            pg_catalog.pg_get_userbyid(c.cfgowner) AS owner,
            p.prsname AS parser_name,
            pg_catalog.obj_description(c.oid, 'pg_ts_config') AS description
        FROM pg_ts_config c
        JOIN pg_namespace n ON c.cfgnamespace = n.oid
        JOIN pg_ts_parser p ON c.cfgparser = p.oid
        WHERE n.nspname = '{schema}'
        ORDER BY c.cfgname;
    """
    return execute_query(query, config)


def collect_tsvector_columns(schema, config=None):
    """Collect columns with tsvector type."""
    query = f"""
        SELECT
            c.relname AS table_name,
            a.attname AS column_name,
            pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type
        FROM pg_attribute a
        JOIN pg_class c ON a.attrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        JOIN pg_type t ON a.atttypid = t.oid
        WHERE n.nspname = '{schema}'
        AND a.attnum > 0
        AND NOT a.attisdropped
        AND t.typname = 'tsvector'
        ORDER BY c.relname, a.attnum;
    """
    return execute_query(query, config)


def collect_all_full_text_search(config=None):
    """Main function to collect all full-text search information."""
    if config is None:
        config = load_config()

    schema = get_schema(config)

    data = {
        "schema": schema,
        "text_search_configs": collect_text_search_configs(schema, config),
        "tsvector_columns": collect_tsvector_columns(schema, config),
    }

    return data


# ============================================================================
# COLLECT DEPENDENCIES MODULE
# ============================================================================

def collect_dependencies(schema, config=None):
    """Collect object dependencies within the schema."""
    query = f"""
        SELECT
            dep.classid::regclass AS dependent_class,
            dep.objid::regclass AS dependent_object,
            dep.refclassid::regclass AS referenced_class,
            dep.refobjid::regclass AS referenced_object,
            dep.deptype AS dependency_type
        FROM pg_depend dep
        JOIN pg_class c1 ON dep.objid = c1.oid
        JOIN pg_namespace n1 ON c1.relnamespace = n1.oid
        WHERE n1.nspname = '{schema}'
        AND dep.deptype IN ('n', 'a', 'i')
        ORDER BY dependent_object, referenced_object;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_invalid_objects(schema, config=None):
    """Check for invalid objects (mainly indexes)."""
    query = f"""
        SELECT
            i.relname AS object_name,
            'INDEX' AS object_type,
            'INVALID' AS status
        FROM pg_index ix
        JOIN pg_class i ON ix.indexrelid = i.oid
        JOIN pg_class t ON ix.indrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        WHERE n.nspname = '{schema}'
        AND NOT ix.indisvalid;
    """
    return execute_query(query, config)


def collect_fk_dependencies(schema, config=None):
    """Collect foreign key dependencies for table migration order."""
    query = f"""
        SELECT DISTINCT
            c.relname AS table_name,
            con.conname AS constraint_name,
            ref_c.relname AS referenced_table
        FROM pg_constraint con
        JOIN pg_class c ON con.conrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        JOIN pg_class ref_c ON con.confrelid = ref_c.oid
        WHERE n.nspname = '{schema}'
        AND con.contype = 'f'
        ORDER BY c.relname;
    """
    return execute_query(query, config)


def calculate_migration_order(fk_dependencies, tables):
    """Calculate suggested migration order based on foreign key dependencies."""
    # Build dependency graph
    dep_graph = {}
    table_names = set()

    for table in tables:
        name = table.get("TABLE_NAME")
        if name:
            table_names.add(name)
            if name not in dep_graph:
                dep_graph[name] = set()

    for dep in fk_dependencies:
        table = dep.get("TABLE_NAME")
        ref = dep.get("REFERENCED_TABLE")
        if table and ref and table in table_names and ref in table_names:
            dep_graph[table].add(ref)

    # Topological sort
    visited = set()
    temp_visited = set()
    order = []

    def visit(node):
        if node in temp_visited:
            return  # Cycle detected
        if node in visited:
            return
        temp_visited.add(node)
        for dep in dep_graph.get(node, []):
            visit(dep)
        temp_visited.remove(node)
        visited.add(node)
        order.append(node)

    for table in table_names:
        if table not in visited:
            visit(table)

    return order


def collect_all_dependencies(config=None):
    """Main function to collect all dependency information."""
    if config is None:
        config = load_config()

    schema = get_schema(config)

    # Get tables first for migration order calculation
    tables = collect_tables(schema, config)
    fk_deps = collect_fk_dependencies(schema, config)

    data = {
        "schema": schema,
        "dependencies": collect_dependencies(schema, config),
        "invalid_objects": collect_invalid_objects(schema, config),
        "fk_dependencies": fk_deps,
        "migration_order": calculate_migration_order(fk_deps, tables),
    }

    return data


# ============================================================================
# MAIN ORCHESTRATION MODULE
# ============================================================================

def collect_all_data(config=None):
    """Run all collectors and return combined data."""
    print("Starting PostgreSQL schema analysis...")
    print("-" * 50)

    data = {}

    collectors = [
        ("Custom Types", "types", collect_all_types),
        ("Tables & Constraints", "tables", collect_all_tables),
        ("Indexes", "indexes", collect_all_indexes),
        ("Views", "views", collect_all_views),
        ("PL/pgSQL Objects", "plpgsql", collect_all_plpgsql),
        ("Sequences", "sequences", collect_all_sequences),
        ("Security", "security", collect_all_security),
        ("Extensions", "extensions", collect_all_extensions),
        ("Miscellaneous", "misc", collect_all_misc),
        ("Full-Text Search", "full_text_search", collect_all_full_text_search),
        ("Dependencies", "dependencies", collect_all_dependencies),
    ]

    for name, key, collector in collectors:
        print(f"Collecting {name}...", end=" ", flush=True)
        try:
            result = collector(config)
            # Only include non-empty results
            if result and any(v for v in result.values() if v):
                data[key] = result
                print("Done")
            else:
                print("Skipped (no data)")
        except Exception as e:
            print(f"Error: {e}")
            # Don't add empty or error data to output

    print("-" * 50)
    return data


def save_raw_data(data, config=None):
    """Save raw collected data as JSON."""
    if config is None:
        config = load_config()

    output_dir = Path(config.get("output_dir", "./output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    # Add metadata
    schema = get_schema(config)
    data["metadata"] = {
        "generated_at": datetime.now().isoformat(),
        "schema": schema,
        "database_name": config.get("database", "Unknown"),
        "database_type": "postgresql",
        "version": get_postgres_version(config),
    }

    json_path = output_dir / "raw_schema_data.json"

    with open(json_path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"Raw data saved to: {json_path}")
    return json_path


def print_summary(data):
    """Print a quick summary of collected objects."""
    print("\n" + "=" * 50)
    print("COLLECTION SUMMARY")
    print("=" * 50)

    summaries = [
        ("ENUM Types", len(data.get("types", {}).get("enum_types", []))),
        ("Composite Types", len(data.get("types", {}).get("composite_types", []))),
        ("Domain Types", len(data.get("types", {}).get("domain_types", []))),
        ("Tables", len(data.get("tables", {}).get("tables", []))),
        ("Partitioned Tables", len(data.get("tables", {}).get("partitioned_tables", []))),
        ("Constraints", len(data.get("tables", {}).get("constraints", []))),
        ("Foreign Keys", len(data.get("tables", {}).get("foreign_keys", []))),
        ("Indexes", len(data.get("indexes", {}).get("indexes", []))),
        ("Views", len(data.get("views", {}).get("views", []))),
        ("Materialized Views", len(data.get("views", {}).get("materialized_views", []))),
        ("Functions", len(data.get("plpgsql", {}).get("functions", []))),
        ("Procedures", len(data.get("plpgsql", {}).get("procedures", []))),
        ("Triggers", len(data.get("plpgsql", {}).get("triggers", []))),
        ("Sequences", len(data.get("sequences", {}).get("sequences", []))),
        ("Extensions", len(data.get("extensions", {}).get("extensions", []))),
        ("RLS Policies", len(data.get("security", {}).get("rls_policies", []))),
        ("Invalid Objects", len(data.get("dependencies", {}).get("invalid_objects", []))),
    ]

    for name, count in summaries:
        if count > 0:
            print(f"  {name}: {count}")

    print("=" * 50 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Collect PostgreSQL database schema metadata"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test database connection only"
    )
    parser.add_argument(
        "--include-source",
        action="store_true",
        help="Include PL/pgSQL source code in output"
    )
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to databases.env configuration file'
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(config_path=args.config)

    # Override config with command line args
    if args.include_source:
        config["include_plpgsql_source"] = True

    # Test connection
    print("\nTesting database connection...")
    if not test_connection():
        print("\nFailed to connect to database. Please check your .env configuration.")
        sys.exit(1)

    if args.test:
        print("\nConnection test successful!")
        sys.exit(0)

    # Collect all data
    print(f"\nAnalyzing schema: {get_schema(config)}")
    data = collect_all_data(config)

    # Print summary
    print_summary(data)

    # Always save raw data (required for Phase 2)
    json_path = save_raw_data(data, config)

    print("\n" + "=" * 50)
    print("PHASE 1 COMPLETE")
    print("=" * 50)
    print(f"JSON data saved to: {json_path}")
    print("\nNext step (Phase 2):")
    print("Ask Claude to generate the Markdown report from the JSON file.")
    print("Example: 'Generate postgresql_schema_report.md from raw_schema_data.json'")


if __name__ == "__main__":
    main()
