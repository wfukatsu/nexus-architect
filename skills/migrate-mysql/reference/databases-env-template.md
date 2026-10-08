# `databases.env` template (MySQL migration)

Read by `/architect:migrate-mysql` at Step 5, on a first run only — when
`.claude/configuration/databases.env` does not exist yet. Write the block below to that file with
every `<...>` placeholder replaced by the value collected in Steps 2-4. The sections of the other
databases are written with their defaults, so that a later migration of one of them finds its keys.

```properties
# =============================================================================
# CONSOLIDATED DATABASE CONFIGURATION
# =============================================================================
# Single configuration file for all database migration skills
# =============================================================================

# ACTIVE DATABASE SELECTION
ACTIVE_DATABASE=mysql

# SHARED OUTPUT CONFIGURATION (ABSOLUTE PATH REQUIRED)
OUTPUT_DIR=<collected_output_dir>

# ScalarDB target version — resolve the current stable release before setting this
# (rules/dependency-versions.md: gh release list -R scalar-labs/scalardb, or
#  repo1.maven.org/maven2/com/scalar-labs/scalardb/maven-metadata.xml)
SCALARDB_TARGET_VERSION=<resolved-stable-version>

# =============================================================================
# POSTGRESQL CONFIGURATION (defaults - not yet configured)
# =============================================================================
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=your_database
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
POSTGRES_SCHEMA=public
POSTGRES_REPORT_FILENAME=postgresql_schema_report.md
POSTGRES_SCALARDB_NAMESPACE=
POSTGRES_INCLUDE_PLPGSQL_SOURCE=true
POSTGRES_PSQL_PATH=
POSTGRES_CONNECTION_TIMEOUT=30
POSTGRES_QUERY_TIMEOUT=300

# =============================================================================
# MYSQL CONFIGURATION
# =============================================================================
MYSQL_HOST=<collected_host>
MYSQL_PORT=<collected_port>
MYSQL_DATABASE=<collected_database>
MYSQL_USER=<collected_user>
MYSQL_PASSWORD=<collected_password>
MYSQL_REPORT_FILENAME=mysql_schema_report.md
MYSQL_SCALARDB_NAMESPACE=<lowercase of collected_database>
MYSQL_INCLUDE_SOURCE=<collected_include_source>
MYSQL_CHARSET=<collected_charset>
MYSQL_CONNECTION_TIMEOUT=30

# =============================================================================
# ORACLE CONFIGURATION (defaults - not yet configured)
# =============================================================================
ORACLE_HOST=localhost
ORACLE_PORT=1521
ORACLE_SERVICE=ORCL
ORACLE_USER=your_username
ORACLE_PASSWORD=your_password
ORACLE_SCHEMA=
ORACLE_REPORT_FILENAME=oracle_schema_report.md
ORACLE_SCALARDB_NAMESPACE=
ORACLE_INCLUDE_PLSQL_SOURCE=false
ORACLE_SQLPLUS_PATH=
ORACLE_HOME=
ORACLE_TNS_ADMIN=

# =============================================================================
# END OF CONFIGURATION
# =============================================================================
```
