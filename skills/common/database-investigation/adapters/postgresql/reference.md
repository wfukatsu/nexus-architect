# PostgreSQL adapter

Tested: PostgreSQL 18.6, psycopg 3.3.5, Python 3.14, restricted reader, 2026-09-15.
Older major versions at/above the probe floor are candidates, not integration-tested claims.

Unquoted SQL identifiers fold to lowercase; quoted spelling is preserved. Use an explicit
database and exact schema. SQL table columns exclude views. Constraints use ordinality to
align composite FK columns, including foreign schemas. Routine names include argument types.

Catalog visibility is not blanket authorization to application data. The integration reader
has schema USAGE and SELECT on the fixture tables/views. No superuser or extension installation
is required. Permission failures remain partial collection. Default sessions are read-only.

Partitions (`relispartition`) are not listed as tables, and their cloned constraints, indexes
and triggers are not repeated; the partitioned parent carries the declared structure. Their
statistics are kept with `granularity: partition` / `partition_index`, so a partition is never
counted as a table. Partition bounds and topology are not reconstructed.

The probe also returns `compatible_product`: the names of Aurora (`aurora_version`) or
YugabyteDB (`yb_servers`) functions when present. Both report a PostgreSQL `version()`, so the
probe fails closed on them instead of trusting the version string; `compatible_markers` adds
the version-string forms (`-YB-`). Other forks remain undetected — treat an unexpected build
string as a question for the user.

Metrics: estimated live rows, measured total relation bytes, cumulative index scans. PostgreSQL
partitioned parent storage and counters are not necessarily a recursive total over partitions;
do not sum or compare these blindly. Empty/null statistics do not prove a table is empty.
Definition bodies, pg_stats value arrays, query text and activity details are not collected.

Sources (consult the target release before adding a query):

- [Catalog constraints and composite keys](https://www.postgresql.org/docs/18/catalog-pg-constraint.html)
- [Cumulative statistics, delays, resets and visibility](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [Column statistics and value-bearing fields excluded from collection](https://www.postgresql.org/docs/18/view-pg-stats.html)
- [Psycopg connection parameters](https://www.psycopg.org/psycopg3/docs/api/connections.html)

Driver pin source: `https://pypi.org/pypi/psycopg/json`, user-approved 2026-09-15.
Registry image: `postgres:18.6`, digest
`sha256:4ef4dbc939d61acea57712655ddb4b4ab27419c913f94cca0cd57cb3ea3c2280`.
