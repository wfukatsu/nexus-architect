# `databases.env` template (Oracle migration)

Read by `/architect:migrate-oracle` at Step 5, on a first run only — when
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
ACTIVE_DATABASE=oracle

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
# MYSQL CONFIGURATION (defaults - not yet configured)
# =============================================================================
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=your_database
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_REPORT_FILENAME=mysql_schema_report.md
MYSQL_SCALARDB_NAMESPACE=
MYSQL_INCLUDE_SOURCE=false
MYSQL_CHARSET=utf8mb4
MYSQL_CONNECTION_TIMEOUT=30

# =============================================================================
# ORACLE CONFIGURATION
# =============================================================================
ORACLE_HOST=<collected_host>
ORACLE_PORT=<collected_port>
ORACLE_SERVICE=<collected_service>
ORACLE_USER=<collected_user>
ORACLE_PASSWORD=<collected_password>
ORACLE_SCHEMA=<collected_schema>
ORACLE_REPORT_FILENAME=oracle_schema_report.md
ORACLE_SCALARDB_NAMESPACE=<lowercase of collected_user or collected_schema>
ORACLE_INCLUDE_PLSQL_SOURCE=<collected_plsql_source>
ORACLE_SQLPLUS_PATH=
ORACLE_HOME=
ORACLE_TNS_ADMIN=

# =============================================================================
# END OF CONFIGURATION
# =============================================================================
```
