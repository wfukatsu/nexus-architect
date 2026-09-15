# MySQL adapter

Tested: MySQL 8.4.11, PyMySQL 1.2.0, Python 3.14, restricted reader, 2026-09-15.
The numeric major floor is not a promise that every release/compatible product works.
MariaDB, TiDB and Aurora require separately verified adapters.

Database equals schema. Preserve table/column spelling: do not infer identifier folding
without the target's lower_case_table_names and SQL mode. MySQL routine DELIMITER blocks are
recognized offline; executable version comments are marked unsupported rather than discarded.
Indexes are table-qualified in live object IDs since index names are table-local.

The integration reader has SELECT and SHOW VIEW on its fixture database. Extra monitoring
privileges are optional. Never enable instruments or consumers to complete a report.
InnoDB TABLE_ROWS and allocated size values are estimates; information_schema values can be
cached and their collection time is not their measurement time. No data samples or histogram
values are fetched. Routine definitions and default expressions are withheld.

Sources:

- [INFORMATION_SCHEMA tables](https://dev.mysql.com/doc/refman/8.4/en/information-schema-table-reference.html)
- [TABLES estimates and statistics cache](https://dev.mysql.com/doc/refman/8.4/en/information-schema-tables-table.html)
- [Performance Schema index I/O summaries](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-table-wait-summary-tables.html)
- [PyMySQL TLS and connection/read/write timeouts](https://pymysql.readthedocs.io/en/latest/modules/connections.html)

Driver pin source: `https://pypi.org/pypi/PyMySQL/json`, user-approved 2026-09-15.
Registry image: `mysql:8.4.11`, digest
`sha256:85b9bf2e29cf836ecb8c2a15a935d4ba0c606631dff1dd79531a11983c638f2a`.
