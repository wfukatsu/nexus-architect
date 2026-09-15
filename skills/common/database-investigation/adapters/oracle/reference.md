# Oracle adapter

Tested: Oracle Free 23.26.3.0.0 (gvenzl/oracle-free distribution), python-oracledb 26.0.0
thin mode, Python 3.14, restricted reader, 2026-09-15. Enterprise releases/editions, older
servers, Wallet/TCPS authentication and CDB-wide discovery are not integration-tested here.

Unquoted design identifiers fold to uppercase; quoted spelling is preserved. The profile's
schema is an exact owner, service identifies the PDB endpoint, and observed catalog records
CON_NAME. The product probe accepts Oracle Database and Oracle AI Database branding.

ALL_ views list objects visible to the connected reader. Integration grants CREATE SESSION
plus SELECT on the fixture tables/views, not DBA privileges. ALL_TAB_COLUMNS includes views
and clusters, so the query explicitly restricts table columns to ALL_TABLES.
NUMBER precision/scale and character length semantics are retained; vendor type extensions
outside these common types still require source review. Oracle C constraints include NOT NULL
constraints as well as explicit CHECKs; expressions are withheld, so do not distinguish them
without additional source evidence. No ALL_SOURCE or LONG definition bodies are exported.

Rows are optimizer estimates with native LAST_ANALYZED timestamps. USER_SEGMENTS is owner-only;
it cannot describe a different owner's capacity using a restricted reader. Partition topology
is not reconstructed. No AWR, ASH, ADDM, DBA_HIST or DBMS_STATS access is part of the adapter.
Management-pack features require separate release/entitlement review if ever added.

Sources:

- [ALL_TAB_COLUMNS scope, type details and hidden columns](https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/ALL_TAB_COLUMNS.html)
- [Existing table statistics](https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/ALL_TAB_STATISTICS.html)
- [Management pack licensing reference](https://docs.oracle.com/en/database/oracle/oracle-database/19/dblic/Licensing-Information.html)
- [Driver cancellation/call timeout](https://python-oracledb.readthedocs.io/en/latest/api_manual/connection.html)

Driver pin source: `https://pypi.org/pypi/oracledb/json`, user-approved 2026-09-15.
Registry image: `gvenzl/oracle-free:23.26.3-slim`, digest
`sha256:6d61d267a3b978c24c5ac1790e62e927416a0aec446bd86e4b3a1527562757bd`.
