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
outside these common types still require source review. Oracle stores every NOT NULL as a C
constraint; the constraints query excludes those whose `SEARCH_CONDITION_VC` is exactly
`"<column>" IS NOT NULL` (nullability is already `ALL_TAB_COLUMNS.NULLABLE`), so `check` means
a declared CHECK, as in the DDL and the other adapters. The condition is matched in the query and
never returned. A hand-written `CHECK ("A" IS NOT NULL)` has the same stored form and is excluded
too. No ALL_SOURCE or LONG definition bodies are exported.

DBMS_METADATA output (`CREATE OR REPLACE EDITIONABLE PROCEDURE ...`) is recognised as a PL/SQL
block offline, so its body is not split at inner semicolons.

Rows are optimizer estimates with native LAST_ANALYZED timestamps. USER_SEGMENTS is owner-only;
it cannot describe a different owner's capacity using a restricted reader. Partition topology
is not reconstructed. No AWR, ASH, ADDM, DBA_HIST or DBMS_STATS access is part of the adapter.
Management-pack features require separate release/entitlement review if ever added.

Sources:

- [ALL_TAB_COLUMNS scope, type details and hidden columns](https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/ALL_TAB_COLUMNS.html)
- [Existing table statistics](https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/ALL_TAB_STATISTICS.html)
- [Management pack licensing reference](https://docs.oracle.com/en/database/oracle/oracle-database/19/dblic/Licensing-Information.html)
- [Driver cancellation/call timeout](https://python-oracledb.readthedocs.io/en/latest/api_manual/connection.html)
- [Thin driver timeout codes (DPY-4024)](https://python-oracledb.readthedocs.io/en/latest/user_guide/appendix_c.html)

Driver pin source: `https://pypi.org/pypi/oracledb/json`, user-approved 2026-09-15.
Registry image: `gvenzl/oracle-free:23.26.3-slim`, digest
`sha256:6d61d267a3b978c24c5ac1790e62e927416a0aec446bd86e4b3a1527562757bd`.
