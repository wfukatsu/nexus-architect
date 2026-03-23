#!/usr/bin/env python3
"""
Oracle Schema Analyzer - Single Script Version
Collects comprehensive Oracle database schema metadata and generates JSON output.
"""

import os
import subprocess
import tempfile
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
    #   Plugin mode: <plugin_root>/skills/analyze-oracle-schema/scripts/oracle_db_extractor.py
    #   Legacy mode: <project>/.claude/skills/analyze-oracle-schema/scripts/oracle_db_extractor.py
    script_dir = Path(__file__).parent  # scripts/
    skill_dir = script_dir.parent  # analyze-oracle-schema/
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
    skill_dir = script_dir.parent  # analyze-oracle-schema/
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

    Supports both consolidated (ORACLE_*) and legacy (non-prefixed) variable names.
    Consolidated format takes precedence when available.

    The .env file is searched in these locations (in order):
    0. Explicit config_path (if provided via --config CLI argument)
    1. .claude/configuration/databases.env (consolidated config - RECOMMENDED)
    2. CWD-based .claude path (plugin mode)
    3. Project root directory (where .claude folder is located)
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

    config = {
        "host": os.getenv("ORACLE_HOST", "localhost"),
        "port": os.getenv("ORACLE_PORT", "1521"),
        "service": os.getenv("ORACLE_SERVICE", "ORCL"),
        "user": os.getenv("ORACLE_USER"),
        "password": os.getenv("ORACLE_PASSWORD"),
        "schema": os.getenv("ORACLE_SCHEMA", ""),
        "output_dir": os.getenv("OUTPUT_DIR", default_output),
        # Support both prefixed (ORACLE_*) and legacy (non-prefixed) variable names
        "report_filename": os.getenv("ORACLE_REPORT_FILENAME", os.getenv("REPORT_FILENAME", "oracle_schema_report.md")),
        "include_plsql_source": os.getenv("ORACLE_INCLUDE_PLSQL_SOURCE", os.getenv("INCLUDE_PLSQL_SOURCE", "false")).lower() == "true",
        "sqlplus_path": os.getenv("ORACLE_SQLPLUS_PATH", os.getenv("SQLPLUS_PATH", "sqlplus")),
        "oracle_home": os.getenv("ORACLE_HOME", ""),
        "tns_admin": os.getenv("ORACLE_TNS_ADMIN", os.getenv("TNS_ADMIN", "")),
        "scalardb_namespace": os.getenv("ORACLE_SCALARDB_NAMESPACE", os.getenv("ORACLE_SCHEMA", "")),
    }

    return config


def get_connection_string(config=None):
    """Build Oracle connection string for SQL*Plus."""
    if config is None:
        config = load_config()

    user = config["user"]
    password = config["password"]
    host = config["host"]
    port = config["port"]
    service = config["service"]

    # Format: user/password@host:port/service
    return f"{user}/{password}@{host}:{port}/{service}"


def get_sqlplus_cmd(config=None):
    """Get the SQL*Plus command with proper path."""
    if config is None:
        config = load_config()

    sqlplus_path = config.get("sqlplus_path", "sqlplus")

    if not sqlplus_path or sqlplus_path == "sqlplus":
        return "sqlplus"

    return sqlplus_path


def get_sqlplus_env(config=None):
    """Get environment variables for SQL*Plus execution."""
    if config is None:
        config = load_config()

    env = os.environ.copy()

    if config.get("oracle_home"):
        env["ORACLE_HOME"] = config["oracle_home"]
        # Add to PATH
        if os.name == "nt":  # Windows
            env["PATH"] = f"{config['oracle_home']}\\bin;{env.get('PATH', '')}"
        else:  # Linux/Mac
            env["PATH"] = f"{config['oracle_home']}/bin:{env.get('PATH', '')}"
            env["LD_LIBRARY_PATH"] = f"{config['oracle_home']}/lib:{env.get('LD_LIBRARY_PATH', '')}"

    if config.get("tns_admin"):
        env["TNS_ADMIN"] = config["tns_admin"]

    return env


def execute_sqlplus(sql_query, config=None, parse_output=True):
    """
    Execute a SQL query using SQL*Plus and return results.

    Args:
        sql_query: The SQL query to execute
        config: Configuration dictionary
        parse_output: If True, parse output into list of dictionaries

    Returns:
        List of dictionaries (if parse_output=True) or raw output string
    """
    if config is None:
        config = load_config()

    # Build the full SQL script with formatting settings
    # Using CSV markup for clean output with proper headers
    sql_script = f"""
SET PAGESIZE 50000
SET LINESIZE 32767
SET LONG 1000000
SET LONGCHUNKSIZE 1000000
SET FEEDBACK OFF
SET HEADING ON
SET TRIMSPOOL ON
SET TRIMOUT ON
SET TAB OFF
SET NUMWIDTH 20
SET NULL '<NULL>'
SET MARKUP CSV ON DELIMITER '|' QUOTE OFF

{sql_query}

EXIT;
"""

    # Write SQL to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        f.write(sql_script)
        sql_file = f.name

    try:
        # Build SQL*Plus command
        sqlplus_cmd = get_sqlplus_cmd(config)
        conn_string = get_connection_string(config)
        env = get_sqlplus_env(config)

        # Execute SQL*Plus
        result = subprocess.run(
            [sqlplus_cmd, "-S", conn_string, f"@{sql_file}"],
            capture_output=True,
            text=True,
            env=env,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            raise Exception(f"SQL*Plus error: {result.stderr or result.stdout}")

        output = result.stdout

        if not parse_output:
            return output

        # Parse the output into list of dictionaries
        return parse_sqlplus_output(output)

    finally:
        # Clean up temporary file
        try:
            os.unlink(sql_file)
        except:
            pass


def parse_sqlplus_output(output):
    """
    Parse SQL*Plus CSV output into list of dictionaries.

    Handles pipe-delimited CSV format from SET MARKUP CSV ON.
    """
    lines = output.strip().split('\n')

    if not lines:
        return []

    # Find the header line (first non-empty line)
    header_idx = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith('SQL>'):
            header_idx = i
            break

    if header_idx == -1:
        return []

    # Parse headers (pipe-delimited)
    header_line = lines[header_idx].strip()
    if '|' in header_line:
        headers = [h.strip() for h in header_line.split('|')]
    else:
        # Single column - header is the whole line
        headers = [header_line.strip()]

    # Parse data rows (starting from line after header)
    results = []
    for line in lines[header_idx + 1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith('SQL>'):
            continue

        if '|' in header_line:
            values = [v.strip() for v in line.split('|')]
        else:
            # Single column - value is the whole line
            values = [stripped]

        # Skip if number of values doesn't match headers
        if len(values) != len(headers):
            continue

        row = {}
        for header, value in zip(headers, values):
            if header:  # Skip empty headers
                # Convert <NULL> back to None
                if value == '<NULL>':
                    row[header] = None
                else:
                    row[header] = value

        if row:  # Only add non-empty rows
            results.append(row)

    return results


def execute_query(sql_query, config=None):
    """
    Execute a SQL query and return results as list of dictionaries.
    This is the main function used by collector scripts.
    """
    return execute_sqlplus(sql_query, config, parse_output=True)


def get_schema(config=None):
    """Get the schema to analyze. Returns connected user if not specified."""
    if config is None:
        config = load_config()

    schema = config.get("schema", "")
    if not schema:
        result = execute_sqlplus("SELECT USER FROM DUAL;", config)
        if result:
            schema = result[0].get("USER", "")

    return schema.upper()


def test_connection():
    """Test database connection and print basic info."""
    config = load_config()

    print(f"SQL*Plus path: {get_sqlplus_cmd(config)}")
    print(f"Connecting to: {config['host']}:{config['port']}/{config['service']}")
    print(f"User: {config['user']}")
    print()

    try:
        # Test connection with version query
        result = execute_sqlplus("""
            SELECT BANNER FROM V$VERSION WHERE ROWNUM = 1;
        """, config, parse_output=False)

        if "ORA-" in result:
            print(f"Connection failed!")
            print(result)
            return False

        print("Connection successful!")
        print(f"Oracle Version: {result.strip()}")

        # Get current user
        user_result = execute_query("SELECT USER FROM DUAL;", config)
        if user_result:
            print(f"Connected User: {user_result[0].get('USER', 'Unknown')}")

        # Get character set
        charset_result = execute_query("""
            SELECT VALUE FROM NLS_DATABASE_PARAMETERS
            WHERE PARAMETER = 'NLS_CHARACTERSET';
        """, config)
        if charset_result:
            print(f"Character Set: {charset_result[0].get('VALUE', 'Unknown')}")

        print(f"Schema to analyze: {get_schema(config)}")

        return True

    except FileNotFoundError:
        print("ERROR: SQL*Plus not found!")
        print("Please ensure SQL*Plus is installed and either:")
        print("  1. Add it to your system PATH, or")
        print("  2. Set SQLPLUS_PATH in your .env file")
        return False
    except subprocess.TimeoutExpired:
        print("ERROR: Connection timed out!")
        return False
    except Exception as e:
        print(f"Connection failed: {e}")
        return False


def get_ddl(object_type, object_name, schema, config=None):
    """
    Get DDL for a database object using DBMS_METADATA.

    Args:
        object_type: Type of object (TABLE, INDEX, TRIGGER, PROCEDURE, etc.)
        object_name: Name of the object
        schema: Schema/owner of the object
        config: Configuration dictionary

    Returns:
        DDL string or None if error
    """
    if config is None:
        config = load_config()

    query = f"""
SET LONG 1000000
SET LONGCHUNKSIZE 1000000
SET PAGESIZE 0
SET LINESIZE 32767
SET FEEDBACK OFF
SET HEADING OFF
SET TRIMSPOOL ON

SELECT DBMS_METADATA.GET_DDL('{object_type}', '{object_name}', '{schema}') FROM DUAL;
"""
    try:
        result = execute_sqlplus(query, config, parse_output=False)
        # Clean up the result
        if result:
            # Remove leading/trailing whitespace and any SQL*Plus artifacts
            ddl = result.strip()
            # Remove any trailing semicolon artifacts
            if ddl.endswith(';'):
                ddl = ddl[:-1].strip()
            return ddl
        return None
    except Exception as e:
        print(f"Warning: Could not get DDL for {object_type} {schema}.{object_name}: {e}")
        return None


def get_trigger_ddl(trigger_name, schema, config=None):
    """
    Get full trigger DDL including CREATE OR REPLACE statement.

    Args:
        trigger_name: Name of the trigger
        schema: Schema/owner of the trigger
        config: Configuration dictionary

    Returns:
        Trigger DDL string or None if error
    """
    return get_ddl('TRIGGER', trigger_name, schema, config)


def get_procedure_ddl(procedure_name, schema, config=None):
    """
    Get full procedure DDL including CREATE OR REPLACE statement.

    Args:
        procedure_name: Name of the procedure
        schema: Schema/owner of the procedure
        config: Configuration dictionary

    Returns:
        Procedure DDL string or None if error
    """
    return get_ddl('PROCEDURE', procedure_name, schema, config)


def get_function_ddl(function_name, schema, config=None):
    """
    Get full function DDL including CREATE OR REPLACE statement.

    Args:
        function_name: Name of the function
        schema: Schema/owner of the function
        config: Configuration dictionary

    Returns:
        Function DDL string or None if error
    """
    return get_ddl('FUNCTION', function_name, schema, config)


def get_package_ddl(package_name, schema, config=None):
    """
    Get full package spec and body DDL.

    Args:
        package_name: Name of the package
        schema: Schema/owner of the package
        config: Configuration dictionary

    Returns:
        Dictionary with 'spec' and 'body' DDL strings
    """
    spec = get_ddl('PACKAGE', package_name, schema, config)
    body = get_ddl('PACKAGE_BODY', package_name, schema, config)
    return {'spec': spec, 'body': body}


def get_table_ddl(table_name, schema, config=None):
    """
    Get full table DDL including constraints and indexes.

    Args:
        table_name: Name of the table
        schema: Schema/owner of the table
        config: Configuration dictionary

    Returns:
        Table DDL string or None if error
    """
    return get_ddl('TABLE', table_name, schema, config)


def get_view_ddl(view_name, schema, config=None):
    """
    Get full view DDL.

    Args:
        view_name: Name of the view
        schema: Schema/owner of the view
        config: Configuration dictionary

    Returns:
        View DDL string or None if error
    """
    return get_ddl('VIEW', view_name, schema, config)


# ============================================================================
# COLLECT DEPENDENCIES MODULE
# ============================================================================

def collect_dependencies(schema, config=None):
    """Collect object dependencies within the schema."""
    query = f"""
        SELECT
            NAME AS OBJECT_NAME,
            TYPE AS OBJECT_TYPE,
            REFERENCED_OWNER,
            REFERENCED_NAME,
            REFERENCED_TYPE,
            REFERENCED_LINK_NAME,
            DEPENDENCY_TYPE
        FROM ALL_DEPENDENCIES
        WHERE OWNER = '{schema}'
        ORDER BY NAME, REFERENCED_NAME;
    """
    return execute_query(query, config)


def collect_invalid_objects(schema, config=None):
    """Collect invalid objects that need recompilation."""
    query = f"""
        SELECT
            OBJECT_NAME,
            OBJECT_TYPE,
            STATUS,
            CREATED,
            LAST_DDL_TIME
        FROM ALL_OBJECTS
        WHERE OWNER = '{schema}'
        AND STATUS = 'INVALID'
        ORDER BY OBJECT_TYPE, OBJECT_NAME;
    """
    return execute_query(query, config)


def collect_object_errors(schema, config=None):
    """Collect compilation errors for invalid objects."""
    query = f"""
        SELECT
            NAME AS OBJECT_NAME,
            TYPE AS OBJECT_TYPE,
            LINE,
            POSITION,
            TEXT AS ERROR_MESSAGE,
            ATTRIBUTE,
            MESSAGE_NUMBER
        FROM ALL_ERRORS
        WHERE OWNER = '{schema}'
        ORDER BY NAME, TYPE, SEQUENCE;
    """
    return execute_query(query, config)


def collect_external_dependencies(schema, config=None):
    """Collect dependencies on objects outside the schema."""
    query = f"""
        SELECT
            NAME AS OBJECT_NAME,
            TYPE AS OBJECT_TYPE,
            REFERENCED_OWNER,
            REFERENCED_NAME,
            REFERENCED_TYPE
        FROM ALL_DEPENDENCIES
        WHERE OWNER = '{schema}'
        AND REFERENCED_OWNER != '{schema}'
        AND REFERENCED_OWNER NOT IN ('SYS', 'PUBLIC', 'SYSTEM')
        ORDER BY REFERENCED_OWNER, REFERENCED_NAME;
    """
    return execute_query(query, config)


def collect_sys_dependencies(schema, config=None):
    """Collect dependencies on SYS/built-in packages."""
    query = f"""
        SELECT
            NAME AS OBJECT_NAME,
            TYPE AS OBJECT_TYPE,
            REFERENCED_NAME AS SYS_OBJECT,
            REFERENCED_TYPE AS SYS_OBJECT_TYPE
        FROM ALL_DEPENDENCIES
        WHERE OWNER = '{schema}'
        AND REFERENCED_OWNER = 'SYS'
        AND REFERENCED_TYPE IN ('PACKAGE', 'TYPE', 'FUNCTION', 'PROCEDURE')
        ORDER BY REFERENCED_NAME, NAME;
    """
    return execute_query(query, config)


def collect_fk_dependencies(schema, config=None):
    """Collect foreign key dependencies for table migration order."""
    query = f"""
        SELECT
            c.TABLE_NAME,
            c.CONSTRAINT_NAME,
            rc.TABLE_NAME AS REFERENCED_TABLE
        FROM ALL_CONSTRAINTS c
        JOIN ALL_CONSTRAINTS rc ON c.R_OWNER = rc.OWNER
            AND c.R_CONSTRAINT_NAME = rc.CONSTRAINT_NAME
        WHERE c.OWNER = '{schema}'
        AND c.CONSTRAINT_TYPE = 'R'
        ORDER BY c.TABLE_NAME;
    """
    return execute_query(query, config)


def collect_type_dependencies(schema, config=None):
    """Collect type dependencies for type migration order."""
    query = f"""
        SELECT
            TYPE_NAME,
            SUPERTYPE_OWNER,
            SUPERTYPE_NAME
        FROM ALL_TYPES
        WHERE OWNER = '{schema}'
        AND SUPERTYPE_NAME IS NOT NULL
        ORDER BY TYPE_NAME;
    """
    return execute_query(query, config)


def collect_all_objects(schema, config=None):
    """Collect all objects for comprehensive listing."""
    query = f"""
        SELECT
            OBJECT_NAME,
            OBJECT_TYPE,
            STATUS,
            CREATED,
            LAST_DDL_TIME,
            TIMESTAMP,
            GENERATED,
            SECONDARY,
            NAMESPACE,
            EDITION_NAME,
            EDITIONABLE
        FROM ALL_OBJECTS
        WHERE OWNER = '{schema}'
        AND OBJECT_TYPE NOT IN ('INDEX PARTITION', 'INDEX SUBPARTITION',
            'TABLE PARTITION', 'TABLE SUBPARTITION', 'LOB', 'LOB PARTITION')
        ORDER BY OBJECT_TYPE, OBJECT_NAME;
    """
    return execute_query(query, config)


def calculate_migration_order(dependencies, objects):
    """Calculate suggested migration order based on dependencies."""
    dep_graph = {}
    for dep in dependencies:
        obj = dep.get("OBJECT_NAME")
        ref = dep.get("REFERENCED_NAME")
        if obj not in dep_graph:
            dep_graph[obj] = set()
        if ref:
            dep_graph[obj].add(ref)

    visited = set()
    order = []

    def visit(node):
        if node in visited:
            return
        visited.add(node)
        for dep in dep_graph.get(node, []):
            visit(dep)
        order.append(node)

    for obj in dep_graph:
        visit(obj)

    return order


def collect_all_dependencies(config=None):
    """Main function to collect all dependency information."""
    if config is None:
        config = load_config()

    schema = get_schema(config)

    dependencies = collect_dependencies(schema, config)
    all_objects = collect_all_objects(schema, config)

    data = {
        "schema": schema,
        "dependencies": dependencies,
        "invalid_objects": collect_invalid_objects(schema, config),
        "object_errors": collect_object_errors(schema, config),
        "external_dependencies": collect_external_dependencies(schema, config),
        "sys_dependencies": collect_sys_dependencies(schema, config),
        "fk_dependencies": collect_fk_dependencies(schema, config),
        "type_dependencies": collect_type_dependencies(schema, config),
        "all_objects": all_objects,
        "migration_order": calculate_migration_order(dependencies, all_objects),
    }

    return data


# ============================================================================
# COLLECT INDEXES MODULE
# ============================================================================

def collect_indexes(schema, config=None):
    """Collect all indexes with their properties."""
    query = f"""
        SELECT
            INDEX_NAME,
            INDEX_TYPE,
            TABLE_NAME,
            TABLE_OWNER,
            UNIQUENESS,
            COMPRESSION,
            PREFIX_LENGTH,
            LOGGING,
            STATUS,
            PARTITIONED,
            TEMPORARY,
            GENERATED,
            SECONDARY,
            FUNCIDX_STATUS,
            JOIN_INDEX,
            DROPPED,
            VISIBILITY,
            DOMIDX_STATUS,
            DOMIDX_OPSTATUS,
            ITYP_OWNER,
            ITYP_NAME,
            PARAMETERS
        FROM ALL_INDEXES
        WHERE OWNER = '{schema}'
        ORDER BY TABLE_NAME, INDEX_NAME;
    """
    return execute_query(query, config)


def collect_index_columns(schema, config=None):
    """Collect index column mappings."""
    query = f"""
        SELECT
            INDEX_NAME,
            TABLE_NAME,
            COLUMN_NAME,
            COLUMN_POSITION,
            COLUMN_LENGTH,
            DESCEND
        FROM ALL_IND_COLUMNS
        WHERE INDEX_OWNER = '{schema}'
        ORDER BY INDEX_NAME, COLUMN_POSITION;
    """
    return execute_query(query, config)


def collect_index_expressions(schema, config=None):
    """Collect function-based index expressions."""
    query = f"""
        SELECT
            INDEX_NAME,
            TABLE_NAME,
            COLUMN_EXPRESSION,
            COLUMN_POSITION
        FROM ALL_IND_EXPRESSIONS
        WHERE INDEX_OWNER = '{schema}'
        ORDER BY INDEX_NAME, COLUMN_POSITION;
    """
    return execute_query(query, config)


def collect_partitioned_indexes(schema, config=None):
    """Collect partitioned index details."""
    query = f"""
        SELECT
            INDEX_NAME,
            TABLE_NAME,
            PARTITIONING_TYPE,
            SUBPARTITIONING_TYPE,
            PARTITION_COUNT,
            DEF_SUBPARTITION_COUNT,
            PARTITIONING_KEY_COUNT,
            SUBPARTITIONING_KEY_COUNT,
            LOCALITY,
            ALIGNMENT
        FROM ALL_PART_INDEXES
        WHERE OWNER = '{schema}'
        ORDER BY TABLE_NAME, INDEX_NAME;
    """
    return execute_query(query, config)


def collect_index_partitions(schema, config=None):
    """Collect index partitions."""
    query = f"""
        SELECT
            INDEX_NAME,
            PARTITION_NAME,
            PARTITION_POSITION,
            HIGH_VALUE,
            STATUS,
            SUBPARTITION_COUNT,
            COMPRESSION
        FROM ALL_IND_PARTITIONS
        WHERE INDEX_OWNER = '{schema}'
        ORDER BY INDEX_NAME, PARTITION_POSITION;
    """
    return execute_query(query, config)


def collect_index_subpartitions(schema, config=None):
    """Collect index subpartitions."""
    query = f"""
        SELECT
            INDEX_NAME,
            PARTITION_NAME,
            SUBPARTITION_NAME,
            SUBPARTITION_POSITION,
            HIGH_VALUE,
            STATUS
        FROM ALL_IND_SUBPARTITIONS
        WHERE INDEX_OWNER = '{schema}'
        ORDER BY INDEX_NAME, PARTITION_NAME, SUBPARTITION_POSITION;
    """
    return execute_query(query, config)


def collect_domain_indexes(schema, config=None):
    """Collect domain index details (Oracle Text, Spatial, etc.)."""
    query = f"""
        SELECT
            INDEX_NAME,
            TABLE_NAME,
            ITYP_OWNER AS INDEXTYPE_OWNER,
            ITYP_NAME AS INDEXTYPE_NAME,
            PARAMETERS,
            DOMIDX_STATUS,
            DOMIDX_OPSTATUS
        FROM ALL_INDEXES
        WHERE OWNER = '{schema}'
        AND INDEX_TYPE = 'DOMAIN'
        ORDER BY TABLE_NAME, INDEX_NAME;
    """
    return execute_query(query, config)


def collect_text_indexes(schema, config=None):
    """Collect Oracle Text index details."""
    query = """
        SELECT
            IDX_NAME,
            IDX_TABLE,
            IDX_KEY_NAME,
            IDX_TEXT_NAME,
            IDX_DOCID_COUNT,
            IDX_STATUS,
            IDX_SYNC_TYPE,
            IDX_SYNC_MEMORY,
            IDX_SYNC_PARA_DEGREE
        FROM CTX_USER_INDEXES
        ORDER BY IDX_NAME;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_spatial_indexes(schema, config=None):
    """Collect spatial index details."""
    query = """
        SELECT
            SDO_INDEX_NAME,
            SDO_INDEX_TABLE,
            SDO_INDEX_PRIMARY,
            SDO_INDEX_TYPE,
            SDO_LEVEL,
            SDO_NUMTILES,
            SDO_FIXED_LEVEL,
            SDO_NON_LEAF_RATIO,
            SDO_INDEX_STATUS
        FROM USER_SDO_INDEX_INFO
        ORDER BY SDO_INDEX_NAME;
    """
    try:
        return execute_query(query, config)
    except:
        return []


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
        "partitioned_indexes": collect_partitioned_indexes(schema, config),
        "index_partitions": collect_index_partitions(schema, config),
        "index_subpartitions": collect_index_subpartitions(schema, config),
        "domain_indexes": collect_domain_indexes(schema, config),
        "text_indexes": collect_text_indexes(schema, config),
        "spatial_indexes": collect_spatial_indexes(schema, config),
    }

    return data


# ============================================================================
# COLLECT MISC MODULE
# ============================================================================

def collect_sequences(schema, config=None):
    """Collect sequences."""
    query = f"""
        SELECT
            SEQUENCE_NAME,
            MIN_VALUE,
            MAX_VALUE,
            INCREMENT_BY,
            CYCLE_FLAG,
            ORDER_FLAG,
            CACHE_SIZE,
            LAST_NUMBER
        FROM ALL_SEQUENCES
        WHERE SEQUENCE_OWNER = '{schema}'
        ORDER BY SEQUENCE_NAME;
    """
    return execute_query(query, config)


def collect_synonyms(schema, config=None):
    """Collect private synonyms."""
    query = f"""
        SELECT
            SYNONYM_NAME,
            TABLE_OWNER,
            TABLE_NAME,
            DB_LINK
        FROM ALL_SYNONYMS
        WHERE OWNER = '{schema}'
        ORDER BY SYNONYM_NAME;
    """
    return execute_query(query, config)


def collect_public_synonyms(schema, config=None):
    """Collect public synonyms pointing to schema objects."""
    query = f"""
        SELECT
            SYNONYM_NAME,
            TABLE_OWNER,
            TABLE_NAME,
            DB_LINK
        FROM ALL_SYNONYMS
        WHERE OWNER = 'PUBLIC'
        AND TABLE_OWNER = '{schema}'
        ORDER BY SYNONYM_NAME;
    """
    return execute_query(query, config)


def collect_db_links(schema, config=None):
    """Collect database links."""
    query = f"""
        SELECT
            DB_LINK,
            USERNAME,
            HOST,
            CREATED
        FROM ALL_DB_LINKS
        WHERE OWNER = '{schema}' OR OWNER = 'PUBLIC'
        ORDER BY DB_LINK;
    """
    return execute_query(query, config)


def collect_scheduler_jobs(schema, config=None):
    """Collect DBMS_SCHEDULER jobs."""
    query = f"""
        SELECT
            JOB_NAME,
            JOB_SUBNAME,
            JOB_STYLE,
            JOB_CREATOR,
            CLIENT_ID,
            GLOBAL_UID,
            PROGRAM_OWNER,
            PROGRAM_NAME,
            JOB_TYPE,
            JOB_ACTION,
            NUMBER_OF_ARGUMENTS,
            SCHEDULE_OWNER,
            SCHEDULE_NAME,
            SCHEDULE_TYPE,
            START_DATE,
            REPEAT_INTERVAL,
            END_DATE,
            JOB_CLASS,
            ENABLED,
            AUTO_DROP,
            RESTARTABLE,
            STATE,
            JOB_PRIORITY,
            RUN_COUNT,
            FAILURE_COUNT,
            RETRY_COUNT,
            LAST_START_DATE,
            LAST_RUN_DURATION,
            NEXT_RUN_DATE,
            MAX_RUN_DURATION,
            COMMENTS,
            CREDENTIAL_NAME,
            DESTINATION
        FROM ALL_SCHEDULER_JOBS
        WHERE OWNER = '{schema}'
        ORDER BY JOB_NAME;
    """
    return execute_query(query, config)


def collect_scheduler_programs(schema, config=None):
    """Collect DBMS_SCHEDULER programs."""
    query = f"""
        SELECT
            PROGRAM_NAME,
            PROGRAM_TYPE,
            PROGRAM_ACTION,
            NUMBER_OF_ARGUMENTS,
            ENABLED,
            DETACHED,
            SCHEDULE_LIMIT,
            PRIORITY,
            WEIGHT,
            MAX_RUNS,
            MAX_FAILURES,
            MAX_RUN_DURATION,
            COMMENTS
        FROM ALL_SCHEDULER_PROGRAMS
        WHERE OWNER = '{schema}'
        ORDER BY PROGRAM_NAME;
    """
    return execute_query(query, config)


def collect_scheduler_schedules(schema, config=None):
    """Collect DBMS_SCHEDULER schedules."""
    query = f"""
        SELECT
            SCHEDULE_NAME,
            SCHEDULE_TYPE,
            START_DATE,
            REPEAT_INTERVAL,
            END_DATE,
            COMMENTS
        FROM ALL_SCHEDULER_SCHEDULES
        WHERE OWNER = '{schema}'
        ORDER BY SCHEDULE_NAME;
    """
    return execute_query(query, config)


def collect_legacy_jobs(schema, config=None):
    """Collect legacy DBMS_JOB jobs."""
    query = f"""
        SELECT
            JOB,
            LOG_USER,
            PRIV_USER,
            SCHEMA_USER,
            LAST_DATE,
            LAST_SEC,
            THIS_DATE,
            THIS_SEC,
            NEXT_DATE,
            NEXT_SEC,
            TOTAL_TIME,
            BROKEN,
            INTERVAL,
            FAILURES,
            WHAT,
            NLS_ENV,
            MISC_ENV,
            INSTANCE
        FROM ALL_JOBS
        WHERE LOG_USER = '{schema}' OR SCHEMA_USER = '{schema}'
        ORDER BY JOB;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_directories(schema, config=None):
    """Collect directory objects."""
    query = """
        SELECT
            DIRECTORY_NAME,
            DIRECTORY_PATH
        FROM ALL_DIRECTORIES
        ORDER BY DIRECTORY_NAME;
    """
    return execute_query(query, config)


def collect_directory_privileges(schema, config=None):
    """Collect directory privileges."""
    query = f"""
        SELECT
            GRANTEE,
            TABLE_NAME AS DIRECTORY_NAME,
            PRIVILEGE,
            GRANTABLE
        FROM ALL_TAB_PRIVS
        WHERE TYPE = 'DIRECTORY'
        AND (GRANTEE = '{schema}' OR OWNER = '{schema}')
        ORDER BY TABLE_NAME, GRANTEE;
    """
    return execute_query(query, config)


def collect_xmltype_columns(schema, config=None):
    """Collect XMLType column details."""
    query = f"""
        SELECT
            TABLE_NAME,
            COLUMN_NAME,
            XMLSCHEMA,
            SCHEMA_OWNER,
            ELEMENT_NAME,
            STORAGE_TYPE,
            ANYSCHEMA,
            NONSCHEMA
        FROM ALL_XML_TAB_COLS
        WHERE OWNER = '{schema}'
        ORDER BY TABLE_NAME, COLUMN_NAME;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_json_columns(schema, config=None):
    """Collect columns with JSON constraints."""
    query = f"""
        SELECT
            c.TABLE_NAME,
            c.COLUMN_NAME,
            cc.CONSTRAINT_NAME,
            cc.SEARCH_CONDITION
        FROM ALL_TAB_COLUMNS c
        JOIN ALL_CONS_COLUMNS col ON c.OWNER = col.OWNER
            AND c.TABLE_NAME = col.TABLE_NAME AND c.COLUMN_NAME = col.COLUMN_NAME
        JOIN ALL_CONSTRAINTS cc ON col.OWNER = cc.OWNER
            AND col.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
        WHERE c.OWNER = '{schema}'
        AND cc.CONSTRAINT_TYPE = 'C'
        AND UPPER(cc.SEARCH_CONDITION_VC) LIKE '%IS JSON%'
        ORDER BY c.TABLE_NAME, c.COLUMN_NAME;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_spatial_columns(schema, config=None):
    """Collect SDO_GEOMETRY columns."""
    query = f"""
        SELECT
            TABLE_NAME,
            COLUMN_NAME,
            SRID
        FROM ALL_SDO_GEOM_METADATA
        WHERE OWNER = '{schema}'
        ORDER BY TABLE_NAME, COLUMN_NAME;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_aq_queue_tables(schema, config=None):
    """Collect Advanced Queuing queue tables."""
    query = f"""
        SELECT
            QUEUE_TABLE,
            TYPE,
            OBJECT_TYPE,
            SORT_ORDER,
            RECIPIENTS,
            MESSAGE_GROUPING,
            COMPATIBLE,
            PRIMARY_INSTANCE,
            SECONDARY_INSTANCE,
            OWNER_INSTANCE,
            USER_COMMENT,
            SECURE
        FROM ALL_QUEUE_TABLES
        WHERE OWNER = '{schema}'
        ORDER BY QUEUE_TABLE;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_aq_queues(schema, config=None):
    """Collect Advanced Queuing queues."""
    query = f"""
        SELECT
            NAME AS QUEUE_NAME,
            QUEUE_TABLE,
            QID,
            QUEUE_TYPE,
            MAX_RETRIES,
            RETRY_DELAY,
            ENQUEUE_ENABLED,
            DEQUEUE_ENABLED,
            RETENTION,
            USER_COMMENT
        FROM ALL_QUEUES
        WHERE OWNER = '{schema}'
        ORDER BY NAME;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_editions(schema, config=None):
    """Collect edition information."""
    query = """
        SELECT
            EDITION_NAME,
            PARENT_EDITION_NAME,
            USABLE
        FROM ALL_EDITIONS
        ORDER BY EDITION_NAME;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_flashback_archives(schema, config=None):
    """Collect flashback data archive info."""
    query = """
        SELECT
            FLASHBACK_ARCHIVE_NAME,
            RETENTION_IN_DAYS,
            CREATE_TIME,
            LAST_PURGE_TIME,
            STATUS
        FROM USER_FLASHBACK_ARCHIVE
        ORDER BY FLASHBACK_ARCHIVE_NAME;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_flashback_archive_tables(schema, config=None):
    """Collect tables with flashback archive enabled."""
    query = """
        SELECT
            TABLE_NAME,
            OWNER_NAME,
            FLASHBACK_ARCHIVE_NAME,
            ARCHIVE_TABLE_NAME,
            STATUS
        FROM USER_FLASHBACK_ARCHIVE_TABLES
        ORDER BY TABLE_NAME;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_all_misc(config=None):
    """Main function to collect all miscellaneous information."""
    if config is None:
        config = load_config()

    schema = get_schema(config)

    data = {
        "schema": schema,
        "sequences": collect_sequences(schema, config),
        "synonyms": collect_synonyms(schema, config),
        "public_synonyms": collect_public_synonyms(schema, config),
        "db_links": collect_db_links(schema, config),
        "scheduler_jobs": collect_scheduler_jobs(schema, config),
        "scheduler_programs": collect_scheduler_programs(schema, config),
        "scheduler_schedules": collect_scheduler_schedules(schema, config),
        "legacy_jobs": collect_legacy_jobs(schema, config),
        "directories": collect_directories(schema, config),
        "directory_privileges": collect_directory_privileges(schema, config),
        "xmltype_columns": collect_xmltype_columns(schema, config),
        "json_columns": collect_json_columns(schema, config),
        "spatial_columns": collect_spatial_columns(schema, config),
        "aq_queue_tables": collect_aq_queue_tables(schema, config),
        "aq_queues": collect_aq_queues(schema, config),
        "editions": collect_editions(schema, config),
        "flashback_archives": collect_flashback_archives(schema, config),
        "flashback_archive_tables": collect_flashback_archive_tables(schema, config),
    }

    return data


# ============================================================================
# COLLECT PLSQL MODULE
# ============================================================================

def collect_procedures(schema, config=None):
    """Collect stored procedures."""
    query = f"""
        SELECT
            OBJECT_NAME AS PROCEDURE_NAME,
            PROCEDURE_NAME AS SUBPROGRAM_NAME,
            OVERLOAD,
            AGGREGATE,
            PIPELINED,
            PARALLEL,
            INTERFACE,
            DETERMINISTIC,
            AUTHID,
            RESULT_CACHE
        FROM ALL_PROCEDURES
        WHERE OWNER = '{schema}'
        AND OBJECT_TYPE = 'PROCEDURE'
        ORDER BY OBJECT_NAME;
    """
    return execute_query(query, config)


def collect_functions(schema, config=None):
    """Collect stored functions."""
    query = f"""
        SELECT
            OBJECT_NAME AS FUNCTION_NAME,
            PROCEDURE_NAME AS SUBPROGRAM_NAME,
            OVERLOAD,
            AGGREGATE,
            PIPELINED,
            PARALLEL,
            INTERFACE,
            DETERMINISTIC,
            AUTHID,
            RESULT_CACHE
        FROM ALL_PROCEDURES
        WHERE OWNER = '{schema}'
        AND OBJECT_TYPE = 'FUNCTION'
        ORDER BY OBJECT_NAME;
    """
    return execute_query(query, config)


def collect_packages(schema, config=None):
    """Collect packages (spec and body status)."""
    query = f"""
        SELECT
            p.OBJECT_NAME AS PACKAGE_NAME,
            p.AUTHID,
            NVL(s.STATUS, 'VALID') AS SPEC_STATUS,
            NVL(b.STATUS, 'NO BODY') AS BODY_STATUS
        FROM ALL_PROCEDURES p
        LEFT JOIN ALL_OBJECTS s ON p.OWNER = s.OWNER
            AND p.OBJECT_NAME = s.OBJECT_NAME AND s.OBJECT_TYPE = 'PACKAGE'
        LEFT JOIN ALL_OBJECTS b ON p.OWNER = b.OWNER
            AND p.OBJECT_NAME = b.OBJECT_NAME AND b.OBJECT_TYPE = 'PACKAGE BODY'
        WHERE p.OWNER = '{schema}'
        AND p.OBJECT_TYPE = 'PACKAGE'
        AND p.PROCEDURE_NAME IS NULL
        ORDER BY p.OBJECT_NAME;
    """
    return execute_query(query, config)


def collect_package_procedures(schema, config=None):
    """Collect procedures within packages."""
    query = f"""
        SELECT
            OBJECT_NAME AS PACKAGE_NAME,
            PROCEDURE_NAME,
            OVERLOAD,
            AGGREGATE,
            PIPELINED,
            PARALLEL,
            DETERMINISTIC
        FROM ALL_PROCEDURES
        WHERE OWNER = '{schema}'
        AND OBJECT_TYPE = 'PACKAGE'
        AND PROCEDURE_NAME IS NOT NULL
        ORDER BY OBJECT_NAME, PROCEDURE_NAME;
    """
    return execute_query(query, config)


def collect_arguments(schema, config=None):
    """Collect procedure/function arguments."""
    query = f"""
        SELECT
            OBJECT_NAME,
            PACKAGE_NAME,
            ARGUMENT_NAME,
            POSITION,
            SEQUENCE,
            DATA_LEVEL,
            DATA_TYPE,
            DEFAULTED,
            DEFAULT_VALUE,
            DEFAULT_LENGTH,
            IN_OUT,
            DATA_LENGTH,
            DATA_PRECISION,
            DATA_SCALE,
            TYPE_OWNER,
            TYPE_NAME,
            TYPE_SUBNAME,
            PLS_TYPE,
            CHAR_LENGTH
        FROM ALL_ARGUMENTS
        WHERE OWNER = '{schema}'
        ORDER BY PACKAGE_NAME NULLS FIRST, OBJECT_NAME, OVERLOAD, SEQUENCE;
    """
    return execute_query(query, config)


def collect_source(schema, config=None):
    """Collect PL/SQL source code (always collected)."""
    query = f"""
        SELECT
            NAME,
            TYPE,
            LINE,
            TEXT
        FROM ALL_SOURCE
        WHERE OWNER = '{schema}'
        AND TYPE IN ('PROCEDURE', 'FUNCTION', 'PACKAGE', 'PACKAGE BODY', 'TRIGGER')
        ORDER BY NAME, TYPE, LINE;
    """
    return execute_query(query, config)


def collect_procedure_ddl(procedures, schema, config=None):
    """
    Collect DDL for all procedures using DBMS_METADATA.

    Args:
        procedures: List of procedure dictionaries
        schema: Schema name
        config: Configuration dictionary

    Returns:
        Dictionary mapping procedure names to their DDL
    """
    ddl_dict = {}
    for proc in procedures:
        proc_name = proc.get('PROCEDURE_NAME')
        if proc_name:
            print(f"  Getting DDL for procedure {proc_name}...", end=" ", flush=True)
            ddl = get_procedure_ddl(proc_name, schema, config)
            if ddl:
                ddl_dict[proc_name] = ddl
                print("OK")
            else:
                print("SKIP")
    return ddl_dict


def collect_function_ddl(functions, schema, config=None):
    """
    Collect DDL for all functions using DBMS_METADATA.

    Args:
        functions: List of function dictionaries
        schema: Schema name
        config: Configuration dictionary

    Returns:
        Dictionary mapping function names to their DDL
    """
    ddl_dict = {}
    for func in functions:
        func_name = func.get('FUNCTION_NAME')
        if func_name:
            print(f"  Getting DDL for function {func_name}...", end=" ", flush=True)
            ddl = get_function_ddl(func_name, schema, config)
            if ddl:
                ddl_dict[func_name] = ddl
                print("OK")
            else:
                print("SKIP")
    return ddl_dict


def collect_package_ddl_all(packages, schema, config=None):
    """
    Collect DDL for all packages using DBMS_METADATA.

    Args:
        packages: List of package dictionaries
        schema: Schema name
        config: Configuration dictionary

    Returns:
        Dictionary mapping package names to their DDL (spec and body)
    """
    ddl_dict = {}
    for pkg in packages:
        pkg_name = pkg.get('PACKAGE_NAME')
        if pkg_name:
            print(f"  Getting DDL for package {pkg_name}...", end=" ", flush=True)
            ddl = get_package_ddl(pkg_name, schema, config)
            if ddl and (ddl.get('spec') or ddl.get('body')):
                ddl_dict[pkg_name] = ddl
                print("OK")
            else:
                print("SKIP")
    return ddl_dict


def collect_trigger_ddl_all(triggers, schema, config=None):
    """
    Collect DDL for all triggers using DBMS_METADATA.

    Args:
        triggers: List of trigger dictionaries
        schema: Schema name
        config: Configuration dictionary

    Returns:
        Dictionary mapping trigger names to their DDL
    """
    ddl_dict = {}
    for trig in triggers:
        trig_name = trig.get('TRIGGER_NAME')
        if trig_name:
            print(f"  Getting DDL for trigger {trig_name}...", end=" ", flush=True)
            ddl = get_trigger_ddl(trig_name, schema, config)
            if ddl:
                ddl_dict[trig_name] = ddl
                print("OK")
            else:
                print("SKIP")
    return ddl_dict


def collect_triggers(schema, config=None):
    """Collect all triggers."""
    query = f"""
        SELECT
            TRIGGER_NAME,
            TRIGGER_TYPE,
            TRIGGERING_EVENT,
            TABLE_OWNER,
            BASE_OBJECT_TYPE,
            TABLE_NAME,
            STATUS,
            ACTION_TYPE,
            CROSSEDITION,
            BEFORE_STATEMENT,
            BEFORE_ROW,
            AFTER_ROW,
            AFTER_STATEMENT,
            INSTEAD_OF_ROW,
            FIRE_ONCE,
            APPLY_SERVER_ONLY
        FROM ALL_TRIGGERS
        WHERE OWNER = '{schema}'
        ORDER BY TABLE_NAME NULLS LAST, TRIGGER_NAME;
    """
    return execute_query(query, config)


def collect_trigger_source(schema, config=None):
    """Collect trigger body source code (always collected)."""
    query = f"""
        SELECT
            TRIGGER_NAME,
            TRIGGER_BODY
        FROM ALL_TRIGGERS
        WHERE OWNER = '{schema}'
        ORDER BY TRIGGER_NAME;
    """
    return execute_query(query, config)


def collect_trigger_columns(schema, config=None):
    """Collect trigger column dependencies (for UPDATE OF triggers)."""
    query = f"""
        SELECT
            TRIGGER_NAME,
            TABLE_OWNER,
            TABLE_NAME,
            COLUMN_NAME,
            COLUMN_LIST,
            COLUMN_USAGE
        FROM ALL_TRIGGER_COLS
        WHERE TRIGGER_OWNER = '{schema}'
        ORDER BY TRIGGER_NAME, COLUMN_NAME;
    """
    return execute_query(query, config)


def collect_trigger_ordering(schema, config=None):
    """Collect trigger ordering (FOLLOWS/PRECEDES)."""
    query = f"""
        SELECT
            TRIGGER_NAME,
            REFERENCED_TRIGGER_OWNER,
            REFERENCED_TRIGGER_NAME,
            ORDERING_TYPE
        FROM ALL_TRIGGER_ORDERING
        WHERE TRIGGER_OWNER = '{schema}'
        ORDER BY TRIGGER_NAME;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_errors(schema, config=None):
    """Collect compilation errors for PL/SQL objects."""
    query = f"""
        SELECT
            NAME,
            TYPE,
            SEQUENCE,
            LINE,
            POSITION,
            TEXT AS ERROR_TEXT,
            ATTRIBUTE,
            MESSAGE_NUMBER
        FROM ALL_ERRORS
        WHERE OWNER = '{schema}'
        ORDER BY NAME, TYPE, SEQUENCE;
    """
    return execute_query(query, config)


def collect_plsql_object_settings(schema, config=None):
    """Collect PL/SQL compiler settings."""
    query = f"""
        SELECT
            NAME,
            TYPE,
            PLSQL_OPTIMIZE_LEVEL,
            PLSQL_CODE_TYPE,
            PLSQL_DEBUG,
            PLSQL_WARNINGS,
            NLS_LENGTH_SEMANTICS,
            PLSQL_CCFLAGS,
            PLSCOPE_SETTINGS
        FROM ALL_PLSQL_OBJECT_SETTINGS
        WHERE OWNER = '{schema}'
        ORDER BY NAME, TYPE;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_all_plsql(config=None):
    """Main function to collect all PL/SQL information including source code and DDL."""
    if config is None:
        config = load_config()

    schema = get_schema(config)

    # Collect basic object info first
    procedures = collect_procedures(schema, config)
    functions = collect_functions(schema, config)
    packages = collect_packages(schema, config)
    triggers = collect_triggers(schema, config)

    data = {
        "schema": schema,
        "procedures": procedures,
        "functions": functions,
        "packages": packages,
        "package_procedures": collect_package_procedures(schema, config),
        "arguments": collect_arguments(schema, config),
        "triggers": triggers,
        "trigger_columns": collect_trigger_columns(schema, config),
        "trigger_ordering": collect_trigger_ordering(schema, config),
        "errors": collect_errors(schema, config),
        "plsql_settings": collect_plsql_object_settings(schema, config),
    }

    # Always collect source code from ALL_SOURCE
    print("  Collecting PL/SQL source code...")
    data["source"] = collect_source(schema, config)
    data["trigger_source"] = collect_trigger_source(schema, config)

    # Collect DDL using DBMS_METADATA for complete CREATE statements
    print("  Collecting procedure DDL statements...")
    data["procedure_ddl"] = collect_procedure_ddl(procedures, schema, config)

    print("  Collecting function DDL statements...")
    data["function_ddl"] = collect_function_ddl(functions, schema, config)

    print("  Collecting package DDL statements...")
    data["package_ddl"] = collect_package_ddl_all(packages, schema, config)

    print("  Collecting trigger DDL statements...")
    data["trigger_ddl"] = collect_trigger_ddl_all(triggers, schema, config)

    return data


# ============================================================================
# COLLECT SECURITY MODULE
# ============================================================================

def collect_object_privileges(schema, config=None):
    """Collect object privileges granted on schema objects."""
    query = f"""
        SELECT
            GRANTEE,
            OWNER,
            TABLE_NAME AS OBJECT_NAME,
            GRANTOR,
            PRIVILEGE,
            GRANTABLE,
            HIERARCHY,
            TYPE
        FROM ALL_TAB_PRIVS
        WHERE OWNER = '{schema}' OR GRANTEE = '{schema}'
        ORDER BY TABLE_NAME, GRANTEE, PRIVILEGE;
    """
    return execute_query(query, config)


def collect_column_privileges(schema, config=None):
    """Collect column-level privileges."""
    query = f"""
        SELECT
            GRANTEE,
            OWNER,
            TABLE_NAME,
            COLUMN_NAME,
            GRANTOR,
            PRIVILEGE,
            GRANTABLE
        FROM ALL_COL_PRIVS
        WHERE OWNER = '{schema}' OR GRANTEE = '{schema}'
        ORDER BY TABLE_NAME, COLUMN_NAME, GRANTEE;
    """
    return execute_query(query, config)


def collect_system_privileges(schema, config=None):
    """Collect system privileges granted to schema."""
    query = """
        SELECT
            PRIVILEGE,
            ADMIN_OPTION
        FROM USER_SYS_PRIVS
        ORDER BY PRIVILEGE;
    """
    return execute_query(query, config)


def collect_role_privileges(schema, config=None):
    """Collect roles granted to schema."""
    query = """
        SELECT
            GRANTED_ROLE,
            ADMIN_OPTION,
            DEFAULT_ROLE
        FROM USER_ROLE_PRIVS
        ORDER BY GRANTED_ROLE;
    """
    return execute_query(query, config)


def collect_roles(schema, config=None):
    """Collect roles used by schema objects."""
    query = """
        SELECT DISTINCT GRANTED_ROLE AS ROLE_NAME
        FROM USER_ROLE_PRIVS
        ORDER BY 1;
    """
    return execute_query(query, config)


def collect_vpd_policies(schema, config=None):
    """Collect Virtual Private Database (VPD) policies."""
    query = f"""
        SELECT
            OBJECT_OWNER,
            OBJECT_NAME,
            POLICY_GROUP,
            POLICY_NAME,
            PF_OWNER,
            PACKAGE,
            FUNCTION,
            SEL,
            INS,
            UPD,
            DEL,
            IDX,
            CHK_OPTION,
            ENABLE,
            STATIC_POLICY,
            POLICY_TYPE,
            LONG_PREDICATE
        FROM ALL_POLICIES
        WHERE OBJECT_OWNER = '{schema}'
        ORDER BY OBJECT_NAME, POLICY_NAME;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_policy_contexts(schema, config=None):
    """Collect policy context associations."""
    query = f"""
        SELECT
            OBJECT_OWNER,
            OBJECT_NAME,
            NAMESPACE,
            ATTRIBUTE
        FROM ALL_POLICY_CONTEXTS
        WHERE OBJECT_OWNER = '{schema}'
        ORDER BY OBJECT_NAME;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_fga_policies(schema, config=None):
    """Collect Fine-Grained Auditing (FGA) policies."""
    query = f"""
        SELECT
            OBJECT_SCHEMA,
            OBJECT_NAME,
            POLICY_NAME,
            POLICY_TEXT,
            POLICY_COLUMN,
            PF_SCHEMA,
            PF_PACKAGE,
            PF_FUNCTION,
            ENABLED,
            SEL,
            INS,
            UPD,
            DEL,
            AUDIT_TRAIL,
            POLICY_COLUMN_OPTIONS
        FROM DBA_AUDIT_POLICIES
        WHERE OBJECT_SCHEMA = '{schema}'
        ORDER BY OBJECT_NAME, POLICY_NAME;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_contexts(schema, config=None):
    """Collect application contexts."""
    query = f"""
        SELECT
            NAMESPACE,
            SCHEMA,
            PACKAGE,
            TYPE
        FROM ALL_CONTEXT
        WHERE SCHEMA = '{schema}'
        ORDER BY NAMESPACE;
    """
    return execute_query(query, config)


def collect_all_security(config=None):
    """Main function to collect all security information."""
    if config is None:
        config = load_config()

    schema = get_schema(config)

    data = {
        "schema": schema,
        "object_privileges": collect_object_privileges(schema, config),
        "column_privileges": collect_column_privileges(schema, config),
        "system_privileges": collect_system_privileges(schema, config),
        "role_privileges": collect_role_privileges(schema, config),
        "roles": collect_roles(schema, config),
        "vpd_policies": collect_vpd_policies(schema, config),
        "policy_contexts": collect_policy_contexts(schema, config),
        "fga_policies": collect_fga_policies(schema, config),
        "contexts": collect_contexts(schema, config),
    }

    return data


# ============================================================================
# COLLECT TABLES MODULE
# ============================================================================

def collect_tables(schema, config=None):
    """Collect all tables with their properties."""
    query = f"""
        SELECT
            TABLE_NAME,
            NUM_ROWS,
            PARTITIONED,
            TEMPORARY,
            SECONDARY,
            NESTED,
            IOT_TYPE,
            IOT_NAME,
            CLUSTER_NAME,
            COMPRESSION,
            COMPRESS_FOR,
            LOGGING,
            ROW_MOVEMENT,
            DEPENDENCIES
        FROM ALL_TABLES
        WHERE OWNER = '{schema}'
        ORDER BY TABLE_NAME;
    """
    return execute_query(query, config)


def collect_columns(schema, config=None):
    """Collect all columns for each table."""
    query = f"""
        SELECT
            TABLE_NAME,
            COLUMN_NAME,
            DATA_TYPE,
            DATA_TYPE_OWNER,
            DATA_LENGTH,
            DATA_PRECISION,
            DATA_SCALE,
            NULLABLE,
            COLUMN_ID,
            DEFAULT_LENGTH,
            CHAR_LENGTH,
            CHAR_USED,
            IDENTITY_COLUMN
        FROM ALL_TAB_COLUMNS
        WHERE OWNER = '{schema}'
        ORDER BY TABLE_NAME, COLUMN_ID;
    """
    return execute_query(query, config)


def collect_identity_columns(schema, config=None):
    """Collect identity column details."""
    query = f"""
        SELECT
            TABLE_NAME,
            COLUMN_NAME,
            GENERATION_TYPE,
            IDENTITY_OPTIONS
        FROM ALL_TAB_IDENTITY_COLS
        WHERE OWNER = '{schema}'
        ORDER BY TABLE_NAME;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_virtual_columns(schema, config=None):
    """Collect virtual columns (using ALL_TAB_COLS for virtual column info)."""
    query = f"""
        SELECT
            TABLE_NAME,
            COLUMN_NAME
        FROM ALL_TAB_COLS
        WHERE OWNER = '{schema}'
        AND VIRTUAL_COLUMN = 'YES'
        ORDER BY TABLE_NAME, COLUMN_NAME;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_partitioned_tables(schema, config=None):
    """Collect partitioning details for partitioned tables."""
    query = f"""
        SELECT
            TABLE_NAME,
            PARTITIONING_TYPE,
            SUBPARTITIONING_TYPE,
            PARTITION_COUNT,
            DEF_SUBPARTITION_COUNT,
            PARTITIONING_KEY_COUNT,
            SUBPARTITIONING_KEY_COUNT,
            INTERVAL,
            IS_NESTED,
            DEF_TABLESPACE_NAME
        FROM ALL_PART_TABLES
        WHERE OWNER = '{schema}'
        ORDER BY TABLE_NAME;
    """
    return execute_query(query, config)


def collect_partition_keys(schema, config=None):
    """Collect partition key columns."""
    query = f"""
        SELECT
            NAME AS TABLE_NAME,
            COLUMN_NAME,
            COLUMN_POSITION,
            OBJECT_TYPE
        FROM ALL_PART_KEY_COLUMNS
        WHERE OWNER = '{schema}'
        ORDER BY NAME, COLUMN_POSITION;
    """
    return execute_query(query, config)


def collect_partitions(schema, config=None):
    """Collect individual partitions."""
    query = f"""
        SELECT
            TABLE_NAME,
            PARTITION_NAME,
            PARTITION_POSITION,
            HIGH_VALUE,
            SUBPARTITION_COUNT,
            COMPRESSION,
            NUM_ROWS
        FROM ALL_TAB_PARTITIONS
        WHERE TABLE_OWNER = '{schema}'
        ORDER BY TABLE_NAME, PARTITION_POSITION;
    """
    return execute_query(query, config)


def collect_subpartitions(schema, config=None):
    """Collect subpartitions."""
    query = f"""
        SELECT
            TABLE_NAME,
            PARTITION_NAME,
            SUBPARTITION_NAME,
            SUBPARTITION_POSITION,
            HIGH_VALUE,
            COMPRESSION,
            NUM_ROWS
        FROM ALL_TAB_SUBPARTITIONS
        WHERE TABLE_OWNER = '{schema}'
        ORDER BY TABLE_NAME, PARTITION_NAME, SUBPARTITION_POSITION;
    """
    return execute_query(query, config)


def collect_external_tables(schema, config=None):
    """Collect external table details."""
    query = f"""
        SELECT
            TABLE_NAME,
            TYPE_OWNER,
            TYPE_NAME,
            DEFAULT_DIRECTORY_OWNER,
            DEFAULT_DIRECTORY_NAME,
            REJECT_LIMIT,
            ACCESS_TYPE,
            ACCESS_PARAMETERS
        FROM ALL_EXTERNAL_TABLES
        WHERE OWNER = '{schema}'
        ORDER BY TABLE_NAME;
    """
    return execute_query(query, config)


def collect_external_locations(schema, config=None):
    """Collect external table file locations."""
    query = f"""
        SELECT
            TABLE_NAME,
            LOCATION,
            DIRECTORY_OWNER,
            DIRECTORY_NAME
        FROM ALL_EXTERNAL_LOCATIONS
        WHERE OWNER = '{schema}'
        ORDER BY TABLE_NAME;
    """
    return execute_query(query, config)


def collect_nested_tables(schema, config=None):
    """Collect nested table storage details."""
    query = f"""
        SELECT
            TABLE_NAME AS STORAGE_TABLE,
            PARENT_TABLE_NAME,
            PARENT_TABLE_COLUMN,
            TABLE_TYPE_NAME AS ELEMENT_TYPE,
            TABLE_TYPE_OWNER,
            RETURN_TYPE
        FROM ALL_NESTED_TABLES
        WHERE OWNER = '{schema}'
        ORDER BY PARENT_TABLE_NAME;
    """
    return execute_query(query, config)


def collect_object_tables(schema, config=None):
    """Collect object tables."""
    query = f"""
        SELECT
            TABLE_NAME,
            TABLE_TYPE,
            TABLE_TYPE_OWNER,
            OBJECT_ID_TYPE
        FROM ALL_OBJECT_TABLES
        WHERE OWNER = '{schema}'
        ORDER BY TABLE_NAME;
    """
    return execute_query(query, config)


def collect_clusters(schema, config=None):
    """Collect cluster information."""
    query = f"""
        SELECT
            CLUSTER_NAME,
            CLUSTER_TYPE,
            FUNCTION,
            HASHKEYS,
            KEY_SIZE,
            SINGLE_TABLE
        FROM ALL_CLUSTERS
        WHERE OWNER = '{schema}'
        ORDER BY CLUSTER_NAME;
    """
    return execute_query(query, config)


def collect_cluster_columns(schema, config=None):
    """Collect cluster key columns."""
    query = f"""
        SELECT
            CLUSTER_NAME,
            CLU_COLUMN_NAME,
            TABLE_NAME,
            TAB_COLUMN_NAME
        FROM ALL_CLU_COLUMNS
        WHERE OWNER = '{schema}'
        ORDER BY CLUSTER_NAME, TABLE_NAME;
    """
    return execute_query(query, config)


def collect_lob_columns(schema, config=None):
    """Collect LOB column details."""
    query = f"""
        SELECT
            TABLE_NAME,
            COLUMN_NAME,
            SEGMENT_NAME,
            INDEX_NAME,
            CHUNK,
            PCTVERSION,
            RETENTION,
            FREEPOOLS,
            CACHE,
            LOGGING,
            IN_ROW,
            ENCRYPT,
            COMPRESSION,
            DEDUPLICATION,
            SECUREFILE
        FROM ALL_LOBS
        WHERE OWNER = '{schema}'
        ORDER BY TABLE_NAME, COLUMN_NAME;
    """
    return execute_query(query, config)


def collect_constraints(schema, config=None):
    """Collect all constraints."""
    query = f"""
        SELECT
            CONSTRAINT_NAME,
            CONSTRAINT_TYPE,
            TABLE_NAME,
            SEARCH_CONDITION,
            R_OWNER,
            R_CONSTRAINT_NAME,
            DELETE_RULE,
            STATUS,
            DEFERRABLE,
            DEFERRED,
            VALIDATED,
            GENERATED,
            INDEX_OWNER,
            INDEX_NAME,
            RELY
        FROM ALL_CONSTRAINTS
        WHERE OWNER = '{schema}'
        ORDER BY TABLE_NAME, CONSTRAINT_TYPE, CONSTRAINT_NAME;
    """
    return execute_query(query, config)


def collect_constraint_columns(schema, config=None):
    """Collect constraint column mappings."""
    query = f"""
        SELECT
            CONSTRAINT_NAME,
            TABLE_NAME,
            COLUMN_NAME,
            POSITION
        FROM ALL_CONS_COLUMNS
        WHERE OWNER = '{schema}'
        ORDER BY CONSTRAINT_NAME, POSITION;
    """
    return execute_query(query, config)


def collect_foreign_key_details(schema, config=None):
    """Collect foreign key reference details."""
    query = f"""
        SELECT
            c.CONSTRAINT_NAME,
            c.TABLE_NAME,
            cc.COLUMN_NAME,
            c.R_OWNER,
            c.R_CONSTRAINT_NAME,
            rc.TABLE_NAME AS REF_TABLE_NAME,
            rcc.COLUMN_NAME AS REF_COLUMN_NAME,
            c.DELETE_RULE
        FROM ALL_CONSTRAINTS c
        JOIN ALL_CONS_COLUMNS cc ON c.OWNER = cc.OWNER AND c.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
        JOIN ALL_CONSTRAINTS rc ON c.R_OWNER = rc.OWNER AND c.R_CONSTRAINT_NAME = rc.CONSTRAINT_NAME
        JOIN ALL_CONS_COLUMNS rcc ON rc.OWNER = rcc.OWNER AND rc.CONSTRAINT_NAME = rcc.CONSTRAINT_NAME
            AND cc.POSITION = rcc.POSITION
        WHERE c.OWNER = '{schema}'
        AND c.CONSTRAINT_TYPE = 'R'
        ORDER BY c.TABLE_NAME, c.CONSTRAINT_NAME, cc.POSITION;
    """
    return execute_query(query, config)


def collect_table_ddl(tables, schema, config=None):
    """
    Collect DDL for all tables using DBMS_METADATA.

    Args:
        tables: List of table dictionaries from collect_tables()
        schema: Schema name
        config: Configuration dictionary

    Returns:
        Dictionary mapping table names to their DDL
    """
    ddl_dict = {}
    for table in tables:
        table_name = table.get('TABLE_NAME')
        if table_name:
            print(f"  Getting DDL for table {table_name}...", end=" ", flush=True)
            ddl = get_table_ddl(table_name, schema, config)
            if ddl:
                ddl_dict[table_name] = ddl
                print("OK")
            else:
                print("SKIP")
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
        "virtual_columns": collect_virtual_columns(schema, config),
        "partitioned_tables": collect_partitioned_tables(schema, config),
        "partition_keys": collect_partition_keys(schema, config),
        "partitions": collect_partitions(schema, config),
        "subpartitions": collect_subpartitions(schema, config),
        "external_tables": collect_external_tables(schema, config),
        "external_locations": collect_external_locations(schema, config),
        "nested_tables": collect_nested_tables(schema, config),
        "object_tables": collect_object_tables(schema, config),
        "clusters": collect_clusters(schema, config),
        "cluster_columns": collect_cluster_columns(schema, config),
        "lob_columns": collect_lob_columns(schema, config),
        "constraints": collect_constraints(schema, config),
        "constraint_columns": collect_constraint_columns(schema, config),
        "foreign_key_details": collect_foreign_key_details(schema, config),
    }

    # Collect DDL for all tables
    print("  Collecting table DDL statements...")
    data["table_ddl"] = collect_table_ddl(tables, schema, config)

    return data


# ============================================================================
# COLLECT TYPES MODULE
# ============================================================================

def collect_object_types(schema, config=None):
    """Collect object types with their attributes and methods."""
    query = f"""
        SELECT
            TYPE_NAME,
            TYPECODE,
            ATTRIBUTES,
            METHODS,
            SUPERTYPE_OWNER,
            SUPERTYPE_NAME,
            FINAL,
            INSTANTIABLE,
            INCOMPLETE
        FROM ALL_TYPES
        WHERE OWNER = '{schema}'
        AND TYPECODE = 'OBJECT'
        ORDER BY TYPE_NAME;
    """
    return execute_query(query, config)


def collect_type_attributes(schema, config=None):
    """Collect attributes for each object type."""
    query = f"""
        SELECT
            TYPE_NAME,
            ATTR_NAME,
            ATTR_TYPE_NAME,
            LENGTH,
            PRECISION,
            SCALE,
            ATTR_NO
        FROM ALL_TYPE_ATTRS
        WHERE OWNER = '{schema}'
        ORDER BY TYPE_NAME, ATTR_NO;
    """
    return execute_query(query, config)


def collect_type_methods(schema, config=None):
    """Collect methods for each object type."""
    query = f"""
        SELECT
            TYPE_NAME,
            METHOD_NAME,
            METHOD_TYPE,
            PARAMETERS,
            RESULTS,
            FINAL,
            INSTANTIABLE,
            OVERRIDING
        FROM ALL_TYPE_METHODS
        WHERE OWNER = '{schema}'
        ORDER BY TYPE_NAME, METHOD_NO;
    """
    return execute_query(query, config)


def collect_collection_types(schema, config=None):
    """Collect VARRAY and nested table types."""
    query = f"""
        SELECT
            t.TYPE_NAME,
            t.TYPECODE,
            c.COLL_TYPE,
            c.ELEM_TYPE_NAME,
            c.ELEM_TYPE_OWNER,
            c.UPPER_BOUND,
            c.LENGTH,
            c.PRECISION,
            c.SCALE
        FROM ALL_TYPES t
        JOIN ALL_COLL_TYPES c ON t.OWNER = c.OWNER AND t.TYPE_NAME = c.TYPE_NAME
        WHERE t.OWNER = '{schema}'
        ORDER BY t.TYPE_NAME;
    """
    return execute_query(query, config)


def collect_type_dependencies_for_types(schema, config=None):
    """Collect which objects use each type."""
    query = f"""
        SELECT
            NAME AS DEPENDENT_OBJECT,
            TYPE AS DEPENDENT_TYPE,
            REFERENCED_NAME AS TYPE_NAME
        FROM ALL_DEPENDENCIES
        WHERE OWNER = '{schema}'
        AND REFERENCED_TYPE = 'TYPE'
        AND REFERENCED_OWNER = '{schema}'
        ORDER BY REFERENCED_NAME, NAME;
    """
    return execute_query(query, config)


def collect_type_source(schema, config=None, include_source=False):
    """Collect type DDL source code."""
    if not include_source:
        return []

    query = f"""
        SELECT
            NAME AS TYPE_NAME,
            TYPE,
            LINE,
            TEXT
        FROM ALL_SOURCE
        WHERE OWNER = '{schema}'
        AND TYPE IN ('TYPE', 'TYPE BODY')
        ORDER BY NAME, TYPE, LINE;
    """
    return execute_query(query, config)


def collect_all_types(config=None):
    """Main function to collect all type information."""
    if config is None:
        config = load_config()

    schema = get_schema(config)
    include_source = config.get("include_plsql_source", False)

    data = {
        "schema": schema,
        "object_types": collect_object_types(schema, config),
        "type_attributes": collect_type_attributes(schema, config),
        "type_methods": collect_type_methods(schema, config),
        "collection_types": collect_collection_types(schema, config),
        "type_dependencies": collect_type_dependencies_for_types(schema, config),
    }

    if include_source:
        data["type_source"] = collect_type_source(schema, config, True)

    return data


# ============================================================================
# COLLECT VIEWS MODULE
# ============================================================================

def collect_views(schema, config=None):
    """Collect all views with their properties."""
    query = f"""
        SELECT
            VIEW_NAME,
            TEXT_LENGTH,
            TYPE_TEXT_LENGTH,
            TYPE_TEXT,
            OID_TEXT_LENGTH,
            OID_TEXT,
            VIEW_TYPE_OWNER,
            VIEW_TYPE,
            SUPERVIEW_NAME,
            EDITIONING_VIEW,
            READ_ONLY
        FROM ALL_VIEWS
        WHERE OWNER = '{schema}'
        ORDER BY VIEW_NAME;
    """
    return execute_query(query, config)


def collect_view_source(schema, config=None):
    """Collect view SQL text."""
    query = f"""
        SELECT
            VIEW_NAME,
            TEXT
        FROM ALL_VIEWS
        WHERE OWNER = '{schema}'
        ORDER BY VIEW_NAME;
    """
    return execute_query(query, config)


def collect_view_columns(schema, config=None):
    """Collect view column details."""
    query = f"""
        SELECT
            TABLE_NAME AS VIEW_NAME,
            COLUMN_NAME,
            DATA_TYPE,
            DATA_LENGTH,
            DATA_PRECISION,
            DATA_SCALE,
            NULLABLE,
            COLUMN_ID,
            INSERTABLE,
            UPDATABLE,
            DELETABLE
        FROM ALL_TAB_COLUMNS
        WHERE OWNER = '{schema}'
        AND TABLE_NAME IN (SELECT VIEW_NAME FROM ALL_VIEWS WHERE OWNER = '{schema}')
        ORDER BY TABLE_NAME, COLUMN_ID;
    """
    return execute_query(query, config)


def collect_updatable_columns(schema, config=None):
    """Collect updatable column info for views."""
    query = f"""
        SELECT
            TABLE_NAME AS VIEW_NAME,
            COLUMN_NAME,
            INSERTABLE,
            UPDATABLE,
            DELETABLE
        FROM ALL_UPDATABLE_COLUMNS
        WHERE OWNER = '{schema}'
        ORDER BY TABLE_NAME, COLUMN_NAME;
    """
    return execute_query(query, config)


def collect_materialized_views(schema, config=None):
    """Collect materialized view details."""
    query = f"""
        SELECT
            MVIEW_NAME,
            CONTAINER_NAME,
            QUERY_LEN,
            UPDATABLE,
            UPDATE_LOG,
            MASTER_ROLLBACK_SEG,
            MASTER_LINK,
            REWRITE_ENABLED,
            REWRITE_CAPABILITY,
            REFRESH_MODE,
            REFRESH_METHOD,
            BUILD_MODE,
            FAST_REFRESHABLE,
            LAST_REFRESH_TYPE,
            LAST_REFRESH_DATE,
            LAST_REFRESH_END_TIME,
            STALENESS,
            AFTER_FAST_REFRESH,
            UNKNOWN_PREBUILT,
            UNKNOWN_PLSQL_FUNC,
            UNKNOWN_EXTERNAL_TABLE,
            UNKNOWN_CONSIDER_FRESH,
            UNKNOWN_IMPORT,
            UNKNOWN_TRUSTED_FD,
            COMPILE_STATE,
            USE_NO_INDEX,
            STALE_SINCE
        FROM ALL_MVIEWS
        WHERE OWNER = '{schema}'
        ORDER BY MVIEW_NAME;
    """
    return execute_query(query, config)


def collect_mview_query(schema, config=None):
    """Collect materialized view query text separately."""
    query = f"""
        SELECT
            MVIEW_NAME,
            QUERY
        FROM ALL_MVIEWS
        WHERE OWNER = '{schema}'
        ORDER BY MVIEW_NAME;
    """
    return execute_query(query, config)


def collect_mview_refresh_times(schema, config=None):
    """Collect materialized view refresh schedule."""
    query = f"""
        SELECT
            NAME AS MVIEW_NAME,
            RNAME AS REFRESH_GROUP,
            REFINT AS REFRESH_INTERVAL,
            NEXT_DATE AS NEXT_REFRESH,
            START_WITH,
            ROLLBACK_SEG,
            PUSH_DEFERRED_RPC,
            REFRESH_AFTER_ERRORS,
            PURGE_OPTION,
            PARALLELISM,
            HEAP_SIZE
        FROM ALL_REFRESH_CHILDREN
        WHERE OWNER = '{schema}'
        ORDER BY NAME;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_mview_logs(schema, config=None):
    """Collect materialized view log details."""
    query = f"""
        SELECT
            LOG_OWNER,
            MASTER,
            LOG_TABLE,
            LOG_TRIGGER,
            ROWIDS,
            PRIMARY_KEY,
            OBJECT_ID,
            FILTER_COLUMNS,
            SEQUENCE,
            INCLUDE_NEW_VALUES,
            PURGE_ASYNCHRONOUS,
            PURGE_DEFERRED,
            PURGE_START,
            PURGE_INTERVAL,
            LAST_PURGE_DATE,
            LAST_PURGE_STATUS,
            NUM_ROWS_PURGED,
            COMMIT_SCN_BASED
        FROM ALL_MVIEW_LOGS
        WHERE LOG_OWNER = '{schema}'
        ORDER BY MASTER;
    """
    return execute_query(query, config)


def collect_mview_detail_relations(schema, config=None):
    """Collect materialized view base table relationships."""
    query = f"""
        SELECT
            MVIEW_NAME,
            DETAILOBJ_OWNER,
            DETAILOBJ_NAME,
            DETAILOBJ_TYPE,
            DETAILOBJ_ALIAS
        FROM ALL_MVIEW_DETAIL_RELATIONS
        WHERE OWNER = '{schema}'
        ORDER BY MVIEW_NAME, DETAILOBJ_NAME;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_editioning_views(schema, config=None):
    """Collect editioning view details."""
    query = f"""
        SELECT
            VIEW_NAME,
            EDITIONING_VIEW
        FROM ALL_VIEWS
        WHERE OWNER = '{schema}'
        AND EDITIONING_VIEW = 'Y'
        ORDER BY VIEW_NAME;
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
        "view_source": collect_view_source(schema, config),
        "view_columns": collect_view_columns(schema, config),
        "updatable_columns": collect_updatable_columns(schema, config),
        "materialized_views": collect_materialized_views(schema, config),
        "mview_query": collect_mview_query(schema, config),
        "mview_refresh_times": collect_mview_refresh_times(schema, config),
        "mview_logs": collect_mview_logs(schema, config),
        "mview_detail_relations": collect_mview_detail_relations(schema, config),
        "editioning_views": collect_editioning_views(schema, config),
    }

    return data


# ============================================================================
# MAIN ORCHESTRATION MODULE
# ============================================================================

def collect_all_data(config=None):
    """Run all collectors and return combined data."""
    print("Starting Oracle schema analysis...")
    print("-" * 50)

    data = {}

    collectors = [
        ("Custom Types", "types", collect_all_types),
        ("Tables & Constraints", "tables", collect_all_tables),
        ("Indexes", "indexes", collect_all_indexes),
        ("Views", "views", collect_all_views),
        ("PL/SQL Objects", "plsql", collect_all_plsql),
        ("Security", "security", collect_all_security),
        ("Miscellaneous", "misc", collect_all_misc),
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
        "database_name": config.get("service", "Unknown"),
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
        ("Object Types", len(data.get("types", {}).get("object_types", []))),
        ("Collection Types", len(data.get("types", {}).get("collection_types", []))),
        ("Tables", len(data.get("tables", {}).get("tables", []))),
        ("Partitioned Tables", len(data.get("tables", {}).get("partitioned_tables", []))),
        ("Constraints", len(data.get("tables", {}).get("constraints", []))),
        ("Indexes", len(data.get("indexes", {}).get("indexes", []))),
        ("Views", len(data.get("views", {}).get("views", []))),
        ("Materialized Views", len(data.get("views", {}).get("materialized_views", []))),
        ("Procedures", len(data.get("plsql", {}).get("procedures", []))),
        ("Functions", len(data.get("plsql", {}).get("functions", []))),
        ("Packages", len(data.get("plsql", {}).get("packages", []))),
        ("Triggers", len(data.get("plsql", {}).get("triggers", []))),
        ("Sequences", len(data.get("misc", {}).get("sequences", []))),
        ("Synonyms", len(data.get("misc", {}).get("synonyms", []))),
        ("DB Links", len(data.get("misc", {}).get("db_links", []))),
        ("Scheduler Jobs", len(data.get("misc", {}).get("scheduler_jobs", []))),
        ("Invalid Objects", len(data.get("dependencies", {}).get("invalid_objects", []))),
    ]

    for name, count in summaries:
        if count > 0:
            print(f"  {name}: {count}")

    print("=" * 50 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Collect Oracle database schema metadata (Phase 1)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test database connection only"
    )
    parser.add_argument(
        "--include-source",
        action="store_true",
        help="Include PL/SQL source code in output"
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
        config["include_plsql_source"] = True

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
    print("Example: 'Generate oracle_schema_report.md from raw_schema_data.json'")


if __name__ == "__main__":
    main()