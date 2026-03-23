#!/usr/bin/env python3
"""
MySQL Schema Analyzer - Single Script Version
Collects comprehensive MySQL database schema metadata and generates JSON output.
"""

import os
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

try:
    import mysql.connector
    from mysql.connector import Error
except ImportError:
    print("Error: mysql-connector-python not installed.")
    print("Run: pip install mysql-connector-python")
    sys.exit(1)


# ============================================================================
# CONFIGURATION MODULE
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

    script_dir = Path(__file__).parent  # scripts/
    skill_dir = script_dir.parent  # analyze-mysql-schema/
    claude_dir = skill_dir.parent.parent  # .claude/
    project_root = claude_dir.parent  # project root

    search_paths = [
        claude_dir / "configuration" / "databases.env",  # Consolidated config (preferred)
        Path.cwd() / ".claude" / "configuration" / "databases.env",  # Also search from current working directory (plugin mode)
        project_root / ".env",
        Path.cwd() / ".env",
    ]

    for path in search_paths:
        if path.exists():
            return path

    return None


def find_project_root():
    """Find the project root directory (where .claude folder exists)."""
    script_dir = Path(__file__).parent
    skill_dir = script_dir.parent
    project_root = skill_dir.parent.parent.parent

    # Verify .claude exists at project root
    if (project_root / ".claude").exists():
        return project_root

    # Also check CWD (plugin mode - script may be in plugin dir, not project)
    if (Path.cwd() / ".claude").exists():
        return Path.cwd()

    # Default to computed project root
    return project_root


def load_config(config_path=None):
    """Load configuration from .env file.

    Supports both consolidated (MYSQL_*) and legacy (non-prefixed) variable names.
    Consolidated format takes precedence when available.
    """
    env_path = find_env_file(config_path)
    if env_path:
        print(f"Loading configuration from: {env_path}")
        load_dotenv(env_path)
    else:
        print("Warning: No .env file found. Using environment variables.")

    config = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "database": os.getenv("MYSQL_DATABASE", ""),
        "user": os.getenv("MYSQL_USER", ""),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "output_dir": os.getenv("OUTPUT_DIR", "./output"),
        # Support both prefixed (MYSQL_*) and legacy (non-prefixed) variable names
        "report_filename": os.getenv("MYSQL_REPORT_FILENAME", os.getenv("REPORT_FILENAME", "mysql_schema_report.md")),
        "include_source": os.getenv("MYSQL_INCLUDE_SOURCE", os.getenv("INCLUDE_SOURCE", "false")).lower() == "true",
        "charset": os.getenv("MYSQL_CHARSET", "utf8mb4"),
        "connection_timeout": int(os.getenv("MYSQL_CONNECTION_TIMEOUT", os.getenv("CONNECTION_TIMEOUT", "30"))),
        "scalardb_namespace": os.getenv("MYSQL_SCALARDB_NAMESPACE", os.getenv("MYSQL_DATABASE", "")),
    }

    # Handle relative output directory
    if not os.path.isabs(config["output_dir"]):
        project_root = find_project_root()
        config["output_dir"] = str(project_root / config["output_dir"])

    return config


# ============================================================================
# DATABASE CONNECTION MODULE
# ============================================================================

def get_connection(config=None):
    """Create and return a MySQL database connection."""
    if config is None:
        config = load_config()

    try:
        connection = mysql.connector.connect(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            user=config["user"],
            password=config["password"],
            charset=config["charset"],
            connection_timeout=config["connection_timeout"],
            use_pure=True
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None


def test_connection(config=None):
    """Test database connection."""
    if config is None:
        config = load_config()

    print(f"Testing connection to MySQL at {config['host']}:{config['port']}...")
    print(f"Database: {config['database']}")
    print(f"User: {config['user']}")

    connection = get_connection(config)
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT VERSION(), @@version_comment")
            version_info = cursor.fetchone()
            print(f"Connected successfully!")
            print(f"MySQL Version: {version_info[0]}")
            print(f"Server: {version_info[1]}")
            cursor.close()
            connection.close()
            return True
        except Error as e:
            print(f"Error: {e}")
            return False
    return False


def execute_query(query, config=None):
    """Execute a query and return results as list of dictionaries."""
    if config is None:
        config = load_config()

    connection = get_connection(config)
    if not connection:
        return []

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        connection.close()
        return results
    except Error as e:
        print(f"Query error: {e}")
        print(f"Query: {query[:200]}...")
        return []


# ============================================================================
# COLLECT TABLES MODULE
# ============================================================================

def collect_tables(database, config=None):
    """Collect all tables with their properties."""
    query = f"""
        SELECT
            TABLE_NAME,
            TABLE_TYPE,
            ENGINE,
            ROW_FORMAT,
            TABLE_ROWS,
            AVG_ROW_LENGTH,
            DATA_LENGTH,
            INDEX_LENGTH,
            AUTO_INCREMENT,
            CREATE_TIME,
            UPDATE_TIME,
            TABLE_COLLATION,
            TABLE_COMMENT
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = '{database}'
        AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME;
    """
    return execute_query(query, config)


def collect_columns(database, config=None):
    """Collect all columns for each table."""
    query = f"""
        SELECT
            TABLE_NAME,
            COLUMN_NAME,
            ORDINAL_POSITION,
            COLUMN_DEFAULT,
            IS_NULLABLE,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH,
            CHARACTER_OCTET_LENGTH,
            NUMERIC_PRECISION,
            NUMERIC_SCALE,
            DATETIME_PRECISION,
            CHARACTER_SET_NAME,
            COLLATION_NAME,
            COLUMN_TYPE,
            COLUMN_KEY,
            EXTRA,
            PRIVILEGES,
            COLUMN_COMMENT,
            GENERATION_EXPRESSION
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = '{database}'
        ORDER BY TABLE_NAME, ORDINAL_POSITION;
    """
    return execute_query(query, config)


def collect_auto_increment_columns(database, config=None):
    """Collect auto_increment columns."""
    query = f"""
        SELECT
            TABLE_NAME,
            COLUMN_NAME,
            DATA_TYPE,
            COLUMN_TYPE
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = '{database}'
        AND EXTRA LIKE '%auto_increment%'
        ORDER BY TABLE_NAME;
    """
    return execute_query(query, config)


def collect_generated_columns(database, config=None):
    """Collect generated/virtual columns."""
    query = f"""
        SELECT
            TABLE_NAME,
            COLUMN_NAME,
            DATA_TYPE,
            GENERATION_EXPRESSION,
            EXTRA
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = '{database}'
        AND GENERATION_EXPRESSION IS NOT NULL
        AND GENERATION_EXPRESSION != ''
        ORDER BY TABLE_NAME;
    """
    return execute_query(query, config)


def collect_partitioned_tables(database, config=None):
    """Collect partitioning details."""
    query = f"""
        SELECT DISTINCT
            TABLE_NAME,
            PARTITION_METHOD,
            PARTITION_EXPRESSION,
            SUBPARTITION_METHOD,
            SUBPARTITION_EXPRESSION
        FROM information_schema.PARTITIONS
        WHERE TABLE_SCHEMA = '{database}'
        AND PARTITION_NAME IS NOT NULL
        ORDER BY TABLE_NAME;
    """
    return execute_query(query, config)


def collect_partitions(database, config=None):
    """Collect individual partitions."""
    query = f"""
        SELECT
            TABLE_NAME,
            PARTITION_NAME,
            SUBPARTITION_NAME,
            PARTITION_ORDINAL_POSITION,
            SUBPARTITION_ORDINAL_POSITION,
            PARTITION_METHOD,
            SUBPARTITION_METHOD,
            PARTITION_EXPRESSION,
            PARTITION_DESCRIPTION,
            TABLE_ROWS,
            AVG_ROW_LENGTH,
            DATA_LENGTH,
            INDEX_LENGTH
        FROM information_schema.PARTITIONS
        WHERE TABLE_SCHEMA = '{database}'
        AND PARTITION_NAME IS NOT NULL
        ORDER BY TABLE_NAME, PARTITION_ORDINAL_POSITION;
    """
    return execute_query(query, config)


def collect_constraints(database, config=None):
    """Collect all constraints."""
    query = f"""
        SELECT
            tc.CONSTRAINT_NAME,
            tc.CONSTRAINT_TYPE,
            tc.TABLE_NAME,
            tc.ENFORCED
        FROM information_schema.TABLE_CONSTRAINTS tc
        WHERE tc.TABLE_SCHEMA = '{database}'
        ORDER BY tc.TABLE_NAME, tc.CONSTRAINT_TYPE, tc.CONSTRAINT_NAME;
    """
    return execute_query(query, config)


def collect_constraint_columns(database, config=None):
    """Collect constraint column mappings."""
    query = f"""
        SELECT
            CONSTRAINT_NAME,
            TABLE_NAME,
            COLUMN_NAME,
            ORDINAL_POSITION
        FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = '{database}'
        ORDER BY CONSTRAINT_NAME, ORDINAL_POSITION;
    """
    return execute_query(query, config)


def collect_foreign_key_details(database, config=None):
    """Collect foreign key reference details."""
    query = f"""
        SELECT
            kcu.CONSTRAINT_NAME,
            kcu.TABLE_NAME,
            kcu.COLUMN_NAME,
            kcu.ORDINAL_POSITION,
            kcu.REFERENCED_TABLE_SCHEMA,
            kcu.REFERENCED_TABLE_NAME,
            kcu.REFERENCED_COLUMN_NAME,
            rc.UPDATE_RULE,
            rc.DELETE_RULE
        FROM information_schema.KEY_COLUMN_USAGE kcu
        JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
            ON kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
            AND kcu.TABLE_SCHEMA = rc.CONSTRAINT_SCHEMA
        WHERE kcu.TABLE_SCHEMA = '{database}'
        AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
        ORDER BY kcu.TABLE_NAME, kcu.CONSTRAINT_NAME, kcu.ORDINAL_POSITION;
    """
    return execute_query(query, config)


def collect_check_constraints(database, config=None):
    """Collect check constraints (MySQL 8.0.16+)."""
    query = f"""
        SELECT
            cc.CONSTRAINT_NAME,
            tc.TABLE_NAME,
            cc.CHECK_CLAUSE,
            cc.ENFORCED
        FROM information_schema.CHECK_CONSTRAINTS cc
        JOIN information_schema.TABLE_CONSTRAINTS tc
            ON cc.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
            AND cc.CONSTRAINT_SCHEMA = tc.TABLE_SCHEMA
        WHERE cc.CONSTRAINT_SCHEMA = '{database}'
        ORDER BY tc.TABLE_NAME, cc.CONSTRAINT_NAME;
    """
    try:
        return execute_query(query, config)
    except:
        return []


def collect_table_ddl(tables, database, config=None):
    """Collect DDL for all tables using SHOW CREATE TABLE."""
    if config is None:
        config = load_config()

    ddl_dict = {}
    connection = get_connection(config)
    if not connection:
        return ddl_dict

    try:
        cursor = connection.cursor()
        for table in tables:
            table_name = table.get('TABLE_NAME')
            if table_name:
                try:
                    cursor.execute(f"SHOW CREATE TABLE `{database}`.`{table_name}`")
                    result = cursor.fetchone()
                    if result:
                        ddl_dict[table_name] = result[1]
                except Error as e:
                    print(f"  Warning: Could not get DDL for {table_name}: {e}")
        cursor.close()
        connection.close()
    except Error as e:
        print(f"Error collecting DDL: {e}")

    return ddl_dict


def collect_all_tables(config=None):
    """Main function to collect all table information."""
    if config is None:
        config = load_config()

    database = config["database"]
    tables = collect_tables(database, config)

    data = {
        "database": database,
        "tables": tables,
        "columns": collect_columns(database, config),
        "auto_increment_columns": collect_auto_increment_columns(database, config),
        "generated_columns": collect_generated_columns(database, config),
        "partitioned_tables": collect_partitioned_tables(database, config),
        "partitions": collect_partitions(database, config),
        "constraints": collect_constraints(database, config),
        "constraint_columns": collect_constraint_columns(database, config),
        "foreign_key_details": collect_foreign_key_details(database, config),
        "check_constraints": collect_check_constraints(database, config),
    }

    # Collect DDL for all tables
    print("  Collecting table DDL statements...")
    data["table_ddl"] = collect_table_ddl(tables, database, config)

    return data


# ============================================================================
# COLLECT INDEXES MODULE
# ============================================================================

def collect_indexes(database, config=None):
    """Collect all indexes with their properties."""
    query = f"""
        SELECT
            TABLE_NAME,
            INDEX_NAME,
            NON_UNIQUE,
            SEQ_IN_INDEX,
            COLUMN_NAME,
            COLLATION,
            CARDINALITY,
            SUB_PART,
            PACKED,
            NULLABLE,
            INDEX_TYPE,
            COMMENT,
            INDEX_COMMENT,
            VISIBLE,
            EXPRESSION
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = '{database}'
        ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;
    """
    return execute_query(query, config)


def collect_fulltext_indexes(database, config=None):
    """Collect fulltext indexes."""
    query = f"""
        SELECT
            TABLE_NAME,
            INDEX_NAME,
            COLUMN_NAME,
            SEQ_IN_INDEX
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = '{database}'
        AND INDEX_TYPE = 'FULLTEXT'
        ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;
    """
    return execute_query(query, config)


def collect_spatial_indexes(database, config=None):
    """Collect spatial indexes."""
    query = f"""
        SELECT
            TABLE_NAME,
            INDEX_NAME,
            COLUMN_NAME,
            SEQ_IN_INDEX
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = '{database}'
        AND INDEX_TYPE = 'SPATIAL'
        ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;
    """
    return execute_query(query, config)


def collect_all_indexes(config=None):
    """Main function to collect all index information."""
    if config is None:
        config = load_config()

    database = config["database"]

    data = {
        "database": database,
        "indexes": collect_indexes(database, config),
        "fulltext_indexes": collect_fulltext_indexes(database, config),
        "spatial_indexes": collect_spatial_indexes(database, config),
    }

    return data


# ============================================================================
# COLLECT VIEWS MODULE
# ============================================================================

def collect_views(database, config=None):
    """Collect all views with their properties."""
    query = f"""
        SELECT
            TABLE_NAME AS VIEW_NAME,
            VIEW_DEFINITION,
            CHECK_OPTION,
            IS_UPDATABLE,
            DEFINER,
            SECURITY_TYPE,
            CHARACTER_SET_CLIENT,
            COLLATION_CONNECTION
        FROM information_schema.VIEWS
        WHERE TABLE_SCHEMA = '{database}'
        ORDER BY TABLE_NAME;
    """
    return execute_query(query, config)


def collect_view_columns(database, config=None):
    """Collect view column details."""
    query = f"""
        SELECT
            c.TABLE_NAME AS VIEW_NAME,
            c.COLUMN_NAME,
            c.DATA_TYPE,
            c.COLUMN_TYPE,
            c.IS_NULLABLE,
            c.ORDINAL_POSITION
        FROM information_schema.COLUMNS c
        JOIN information_schema.VIEWS v
            ON c.TABLE_SCHEMA = v.TABLE_SCHEMA
            AND c.TABLE_NAME = v.TABLE_NAME
        WHERE c.TABLE_SCHEMA = '{database}'
        ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION;
    """
    return execute_query(query, config)


def collect_all_views(config=None):
    """Main function to collect all view information."""
    if config is None:
        config = load_config()

    database = config["database"]

    data = {
        "database": database,
        "views": collect_views(database, config),
        "view_columns": collect_view_columns(database, config),
    }

    return data


# ============================================================================
# COLLECT ROUTINES MODULE
# ============================================================================

def collect_procedures(database, config=None):
    """Collect stored procedures."""
    query = f"""
        SELECT
            ROUTINE_NAME,
            ROUTINE_TYPE,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH,
            NUMERIC_PRECISION,
            NUMERIC_SCALE,
            DTD_IDENTIFIER,
            ROUTINE_BODY,
            EXTERNAL_NAME,
            EXTERNAL_LANGUAGE,
            PARAMETER_STYLE,
            IS_DETERMINISTIC,
            SQL_DATA_ACCESS,
            SQL_PATH,
            SECURITY_TYPE,
            CREATED,
            LAST_ALTERED,
            SQL_MODE,
            ROUTINE_COMMENT,
            DEFINER,
            CHARACTER_SET_CLIENT,
            COLLATION_CONNECTION,
            DATABASE_COLLATION
        FROM information_schema.ROUTINES
        WHERE ROUTINE_SCHEMA = '{database}'
        AND ROUTINE_TYPE = 'PROCEDURE'
        ORDER BY ROUTINE_NAME;
    """
    return execute_query(query, config)


def collect_functions(database, config=None):
    """Collect stored functions."""
    query = f"""
        SELECT
            ROUTINE_NAME,
            ROUTINE_TYPE,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH,
            NUMERIC_PRECISION,
            NUMERIC_SCALE,
            DTD_IDENTIFIER,
            ROUTINE_BODY,
            EXTERNAL_NAME,
            EXTERNAL_LANGUAGE,
            PARAMETER_STYLE,
            IS_DETERMINISTIC,
            SQL_DATA_ACCESS,
            SQL_PATH,
            SECURITY_TYPE,
            CREATED,
            LAST_ALTERED,
            SQL_MODE,
            ROUTINE_COMMENT,
            DEFINER,
            CHARACTER_SET_CLIENT,
            COLLATION_CONNECTION,
            DATABASE_COLLATION
        FROM information_schema.ROUTINES
        WHERE ROUTINE_SCHEMA = '{database}'
        AND ROUTINE_TYPE = 'FUNCTION'
        ORDER BY ROUTINE_NAME;
    """
    return execute_query(query, config)


def collect_routine_parameters(database, config=None):
    """Collect procedure/function parameters."""
    query = f"""
        SELECT
            SPECIFIC_NAME,
            ORDINAL_POSITION,
            PARAMETER_MODE,
            PARAMETER_NAME,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH,
            NUMERIC_PRECISION,
            NUMERIC_SCALE,
            DTD_IDENTIFIER,
            ROUTINE_TYPE
        FROM information_schema.PARAMETERS
        WHERE SPECIFIC_SCHEMA = '{database}'
        ORDER BY SPECIFIC_NAME, ORDINAL_POSITION;
    """
    return execute_query(query, config)


def collect_triggers(database, config=None):
    """Collect all triggers."""
    query = f"""
        SELECT
            TRIGGER_NAME,
            EVENT_MANIPULATION,
            EVENT_OBJECT_TABLE,
            ACTION_ORDER,
            ACTION_CONDITION,
            ACTION_STATEMENT,
            ACTION_ORIENTATION,
            ACTION_TIMING,
            ACTION_REFERENCE_OLD_TABLE,
            ACTION_REFERENCE_NEW_TABLE,
            ACTION_REFERENCE_OLD_ROW,
            ACTION_REFERENCE_NEW_ROW,
            CREATED,
            SQL_MODE,
            DEFINER,
            CHARACTER_SET_CLIENT,
            COLLATION_CONNECTION,
            DATABASE_COLLATION
        FROM information_schema.TRIGGERS
        WHERE TRIGGER_SCHEMA = '{database}'
        ORDER BY EVENT_OBJECT_TABLE, ACTION_TIMING, EVENT_MANIPULATION, ACTION_ORDER;
    """
    return execute_query(query, config)


def collect_events(database, config=None):
    """Collect scheduled events."""
    query = f"""
        SELECT
            EVENT_NAME,
            DEFINER,
            TIME_ZONE,
            EVENT_BODY,
            EVENT_DEFINITION,
            EVENT_TYPE,
            EXECUTE_AT,
            INTERVAL_VALUE,
            INTERVAL_FIELD,
            SQL_MODE,
            STARTS,
            ENDS,
            STATUS,
            ON_COMPLETION,
            CREATED,
            LAST_ALTERED,
            LAST_EXECUTED,
            EVENT_COMMENT,
            ORIGINATOR,
            CHARACTER_SET_CLIENT,
            COLLATION_CONNECTION,
            DATABASE_COLLATION
        FROM information_schema.EVENTS
        WHERE EVENT_SCHEMA = '{database}'
        ORDER BY EVENT_NAME;
    """
    return execute_query(query, config)


def collect_routine_source(routines, routine_type, database, config=None):
    """Collect source code for routines using SHOW CREATE."""
    if config is None:
        config = load_config()

    source_dict = {}
    connection = get_connection(config)
    if not connection:
        return source_dict

    try:
        cursor = connection.cursor()
        for routine in routines:
            routine_name = routine.get('ROUTINE_NAME')
            if routine_name:
                try:
                    if routine_type == 'PROCEDURE':
                        cursor.execute(f"SHOW CREATE PROCEDURE `{database}`.`{routine_name}`")
                    else:
                        cursor.execute(f"SHOW CREATE FUNCTION `{database}`.`{routine_name}`")
                    result = cursor.fetchone()
                    if result:
                        # Index 2 contains the CREATE statement
                        source_dict[routine_name] = result[2] if len(result) > 2 else result[1]
                except Error as e:
                    print(f"  Warning: Could not get source for {routine_name}: {e}")
        cursor.close()
        connection.close()
    except Error as e:
        print(f"Error collecting routine source: {e}")

    return source_dict


def collect_all_routines(config=None):
    """Main function to collect all routine information."""
    if config is None:
        config = load_config()

    database = config["database"]

    procedures = collect_procedures(database, config)
    functions = collect_functions(database, config)

    data = {
        "database": database,
        "procedures": procedures,
        "functions": functions,
        "parameters": collect_routine_parameters(database, config),
        "triggers": collect_triggers(database, config),
        "events": collect_events(database, config),
    }

    # Collect source code if enabled
    if config.get("include_source", False):
        print("  Collecting procedure source code...")
        data["procedure_source"] = collect_routine_source(procedures, 'PROCEDURE', database, config)
        print("  Collecting function source code...")
        data["function_source"] = collect_routine_source(functions, 'FUNCTION', database, config)

    return data


# ============================================================================
# COLLECT SECURITY MODULE
# ============================================================================

def collect_user_privileges(database, config=None):
    """Collect user privileges on database objects."""
    query = f"""
        SELECT
            GRANTEE,
            TABLE_SCHEMA,
            PRIVILEGE_TYPE,
            IS_GRANTABLE
        FROM information_schema.SCHEMA_PRIVILEGES
        WHERE TABLE_SCHEMA = '{database}'
        ORDER BY GRANTEE, PRIVILEGE_TYPE;
    """
    return execute_query(query, config)


def collect_table_privileges(database, config=None):
    """Collect table-level privileges."""
    query = f"""
        SELECT
            GRANTEE,
            TABLE_NAME,
            PRIVILEGE_TYPE,
            IS_GRANTABLE
        FROM information_schema.TABLE_PRIVILEGES
        WHERE TABLE_SCHEMA = '{database}'
        ORDER BY TABLE_NAME, GRANTEE, PRIVILEGE_TYPE;
    """
    return execute_query(query, config)


def collect_column_privileges(database, config=None):
    """Collect column-level privileges."""
    query = f"""
        SELECT
            GRANTEE,
            TABLE_NAME,
            COLUMN_NAME,
            PRIVILEGE_TYPE,
            IS_GRANTABLE
        FROM information_schema.COLUMN_PRIVILEGES
        WHERE TABLE_SCHEMA = '{database}'
        ORDER BY TABLE_NAME, COLUMN_NAME, GRANTEE;
    """
    return execute_query(query, config)


def collect_all_security(config=None):
    """Main function to collect all security information."""
    if config is None:
        config = load_config()

    database = config["database"]

    data = {
        "database": database,
        "user_privileges": collect_user_privileges(database, config),
        "table_privileges": collect_table_privileges(database, config),
        "column_privileges": collect_column_privileges(database, config),
    }

    return data


# ============================================================================
# COLLECT STATISTICS MODULE
# ============================================================================

def collect_table_sizes(database, config=None):
    """Collect table size statistics."""
    query = f"""
        SELECT
            TABLE_NAME,
            TABLE_ROWS,
            AVG_ROW_LENGTH,
            DATA_LENGTH,
            MAX_DATA_LENGTH,
            INDEX_LENGTH,
            DATA_FREE,
            (DATA_LENGTH + INDEX_LENGTH) AS TOTAL_SIZE
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = '{database}'
        AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC;
    """
    return execute_query(query, config)


def collect_all_statistics(config=None):
    """Main function to collect all statistics."""
    if config is None:
        config = load_config()

    database = config["database"]

    data = {
        "database": database,
        "table_sizes": collect_table_sizes(database, config),
    }

    return data


# ============================================================================
# COLLECT MISC MODULE
# ============================================================================

def collect_character_sets(config=None):
    """Collect available character sets."""
    query = """
        SELECT
            CHARACTER_SET_NAME,
            DEFAULT_COLLATE_NAME,
            DESCRIPTION,
            MAXLEN
        FROM information_schema.CHARACTER_SETS
        ORDER BY CHARACTER_SET_NAME;
    """
    return execute_query(query, config)


def collect_collations(database, config=None):
    """Collect collations used in the database."""
    query = f"""
        SELECT DISTINCT
            c.COLLATION_NAME,
            c.CHARACTER_SET_NAME,
            c.IS_DEFAULT
        FROM information_schema.COLUMNS col
        JOIN information_schema.COLLATIONS c
            ON col.COLLATION_NAME = c.COLLATION_NAME
        WHERE col.TABLE_SCHEMA = '{database}'
        ORDER BY c.COLLATION_NAME;
    """
    return execute_query(query, config)


def collect_engines(database, config=None):
    """Collect storage engines used."""
    query = f"""
        SELECT DISTINCT
            ENGINE,
            COUNT(*) as TABLE_COUNT
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = '{database}'
        AND TABLE_TYPE = 'BASE TABLE'
        GROUP BY ENGINE
        ORDER BY TABLE_COUNT DESC;
    """
    return execute_query(query, config)


def collect_server_variables(config=None):
    """Collect relevant server variables."""
    query = """
        SHOW VARIABLES WHERE Variable_name IN (
            'version',
            'version_comment',
            'version_compile_machine',
            'innodb_version',
            'character_set_server',
            'collation_server',
            'max_connections',
            'default_storage_engine',
            'sql_mode',
            'time_zone',
            'lower_case_table_names'
        );
    """
    if config is None:
        config = load_config()

    connection = get_connection(config)
    if not connection:
        return []

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        connection.close()
        return results
    except Error as e:
        print(f"Error collecting variables: {e}")
        return []


def collect_all_misc(config=None):
    """Main function to collect all miscellaneous information."""
    if config is None:
        config = load_config()

    database = config["database"]

    data = {
        "database": database,
        "character_sets": collect_character_sets(config),
        "collations": collect_collations(database, config),
        "engines": collect_engines(database, config),
        "server_variables": collect_server_variables(config),
    }

    return data


# ============================================================================
# MAIN ORCHESTRATION MODULE
# ============================================================================

def collect_server_info(config=None):
    """Collect MySQL server information."""
    if config is None:
        config = load_config()

    connection = get_connection(config)
    if not connection:
        return {}

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT VERSION(), @@version_comment, @@hostname")
        result = cursor.fetchone()
        cursor.close()
        connection.close()

        return {
            "version": result[0],
            "version_comment": result[1],
            "hostname": result[2]
        }
    except Error as e:
        print(f"Error getting server info: {e}")
        return {}


def collect_all_data(config=None):
    """Run all collectors and return combined data."""
    print("Starting MySQL schema analysis...")
    print("-" * 50)

    data = {}

    collectors = [
        ("Tables & Constraints", "tables", collect_all_tables),
        ("Indexes", "indexes", collect_all_indexes),
        ("Views", "views", collect_all_views),
        ("Routines", "routines", collect_all_routines),
        ("Security", "security", collect_all_security),
        ("Statistics", "statistics", collect_all_statistics),
        ("Miscellaneous", "misc", collect_all_misc),
    ]

    for name, key, collector in collectors:
        print(f"Collecting {name}...", end=" ", flush=True)
        try:
            result = collector(config)
            if result and any(v for v in result.values() if v):
                data[key] = result
                print("Done")
            else:
                print("Skipped (no data)")
        except Exception as e:
            print(f"Error: {e}")

    print("-" * 50)
    return data


def save_raw_data(data, config=None):
    """Save raw collected data as JSON."""
    if config is None:
        config = load_config()

    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    # Add metadata
    server_info = collect_server_info(config)
    data["metadata"] = {
        "generated_at": datetime.now().isoformat(),
        "database": config["database"],
        "mysql_version": server_info.get("version", "Unknown"),
        "server_info": server_info.get("version_comment", "Unknown"),
        "hostname": server_info.get("hostname", "Unknown"),
    }

    json_path = output_dir / "raw_mysql_schema_data.json"

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
        ("Tables", len(data.get("tables", {}).get("tables", []))),
        ("Columns", len(data.get("tables", {}).get("columns", []))),
        ("Auto-increment Columns", len(data.get("tables", {}).get("auto_increment_columns", []))),
        ("Generated Columns", len(data.get("tables", {}).get("generated_columns", []))),
        ("Partitioned Tables", len(data.get("tables", {}).get("partitioned_tables", []))),
        ("Constraints", len(data.get("tables", {}).get("constraints", []))),
        ("Foreign Keys", len(data.get("tables", {}).get("foreign_key_details", []))),
        ("Indexes", len(set(i.get("INDEX_NAME", "") for i in data.get("indexes", {}).get("indexes", [])))),
        ("Views", len(data.get("views", {}).get("views", []))),
        ("Procedures", len(data.get("routines", {}).get("procedures", []))),
        ("Functions", len(data.get("routines", {}).get("functions", []))),
        ("Triggers", len(data.get("routines", {}).get("triggers", []))),
        ("Events", len(data.get("routines", {}).get("events", []))),
    ]

    for name, count in summaries:
        if count > 0:
            print(f"  {name}: {count}")

    print("=" * 50 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Collect MySQL database schema metadata"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test database connection only"
    )
    parser.add_argument(
        "--include-source",
        action="store_true",
        help="Include stored procedure/function source code in output"
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
        config["include_source"] = True

    # Test connection
    print("\nTesting database connection...")
    if not test_connection(config):
        print("\nFailed to connect to database. Please check your .env configuration.")
        sys.exit(1)

    if args.test:
        print("\nConnection test successful!")
        sys.exit(0)

    # Collect all data
    print(f"\nAnalyzing database: {config['database']}")
    data = collect_all_data(config)

    # Print summary
    print_summary(data)

    # Save raw data
    json_path = save_raw_data(data, config)

    print("\n" + "=" * 50)
    print("PHASE 1 COMPLETE")
    print("=" * 50)
    print(f"JSON data saved to: {json_path}")
    print("\nNext step (Phase 2):")
    print("Ask Claude to generate the Markdown report from the JSON file.")
    print("Example: 'Generate mysql_schema_report.md from raw_mysql_schema_data.json'")


if __name__ == "__main__":
    main()
