# ScalarDB SQL grammar and conversion rules

What the converter (`scripts/scalardb_migrate/`) applies when it turns a source statement into
ScalarDB SQL. The official grammar is https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/grammar/
— pin the release per @rules/okf-knowledge-bundle.md before relying on a detail here.

## Why the grammar is narrow

ScalarDB virtually unifies several storages and runs transactions across them. Arbitrary subqueries
or joins would make it impossible to decide which storage executes which part, so the grammar is
deliberately limited to what can be routed with certainty.

- The select list holds columns and the aggregates `COUNT` / `SUM` / `AVG` / `MIN` / `MAX` only — no
  expressions or functions.
- A `WHERE` right-hand side is a literal. Column-to-column comparison is only allowed in a join's `ON`.
- `WHERE` must be in DNF (OR of ANDs) or CNF (AND of ORs).
- A join condition must cover the joined table's primary key or a secondary index.
- No subqueries, CTEs, `UNION`, window functions, `DISTINCT`, `OFFSET` or `CASE`.
- No update that references a column (`UPDATE ... SET col = col + 1`).

## Rewritten automatically

| Source construct | ScalarDB SQL |
|---|---|
| `IN (a, b, c)` / `NOT IN` | `(col = a OR col = b OR col = c)` / `col <> a AND col <> b` |
| `NOT (...)` | pushed down by inverting the comparison; `IS NOT NULL` / `NOT LIKE` stay |
| arbitrary AND / OR nesting | normalized to the shorter of DNF and CNF, parenthesized |
| `10 < col` | `col > 10` (literal on the right) |
| `ROWNUM <= n` / `FETCH FIRST n ROWS ONLY` | `LIMIT n` |
| `FROM a, b WHERE a.x = b.y` | `INNER JOIN b ON a.x = b.y` |
| Oracle outer join `a.x = b.y(+)` | `LEFT JOIN b ON a.x = b.y` |
| `JOIN ... USING (c)` | `JOIN ... ON a.c = b.c` |
| `ON CONFLICT DO UPDATE` / `ON DUPLICATE KEY UPDATE` / `REPLACE INTO` / constant-source `MERGE` | `UPSERT INTO` (the semantic difference is a WARN) |

## Type mapping

ScalarDB has 11 types: `BOOLEAN`, `INT`, `BIGINT`, `FLOAT`, `DOUBLE`, `TEXT`, `BLOB`, `DATE`, `TIME`,
`TIMESTAMP`, `TIMESTAMPTZ`.

| Source type | ScalarDB | Severity |
|---|---|---|
| `NUMBER(p)` / `DECIMAL(p, 0)`, p ≤ 9 | `INT` | INFO |
| same, p ≤ 18 | `BIGINT` | INFO |
| `NUMBER(p, s)` / `DECIMAL(p, s)`, s > 0 | `DOUBLE` | WARN (precision loss) |
| `VARCHAR2(n)` / `VARCHAR(n)` / `CLOB` / `TEXT` | `TEXT` | INFO (the length limit disappears) |
| Oracle `DATE` | `DATE` | WARN (an Oracle DATE carries a time; use `TIMESTAMP` when the time matters) |
| `JSON` / `UUID` / `ENUM` | `TEXT` | WARN |
| `ARRAY` / `INTERVAL` / `GEOMETRY` | none | ERROR |

**Money columns need a decision.** ScalarDB has no `DECIMAL`, so they become `DOUBLE` and acquire
rounding error. Prefer a scaled integer in `BIGINT` (yen ×1, dollars ×100) and record the scale.

## Constraints and keys

| Source | Handling |
|---|---|
| `NOT NULL` / `DEFAULT` / `UNIQUE` / `FOREIGN KEY` / `CHECK` | dropped with INFO or WARN; the application enforces them |
| single-column primary key | partition key |
| composite primary key | first column is the partition key, the rest are clustering keys |
| MySQL inline `INDEX (col)` | split out as `CREATE INDEX ON t (col)` |
| multi-column index | ERROR (a ScalarDB secondary index covers one column) |

Override the split with `--keys table=partition_keys/clustering_keys`:

```bash
--keys orders=customer_id/order_no     # partition by customer_id, order by order_no
```

Key design decides post-migration performance more than anything else. A query that cannot be
narrowed by the partition key becomes a cross-partition scan over the whole table.

## Access paths

With a schema (DDL in the input, or `--schema` Schema Loader JSON) the converter classifies how
ScalarDB reads each statement.

| Access path | Condition | Result |
|---|---|---|
| GET | the full primary key is specified | fine |
| partition SCAN | the partition key is specified | fine |
| index SCAN | a secondary index narrows the read | fine |
| cross-partition SCAN | no predicate covers a key | WARN (cost grows with the row count) |

## Not convertible (ERROR)

| Construct | Application-side handling |
|---|---|
| expressions or functions in the select list (`NVL`, `UPPER`, `col * 2`, `CASE`) | compute them after fetching |
| subqueries, CTEs, `UNION`, window functions, `DISTINCT`, `OFFSET` | process after fetching |
| column-to-column or function predicates in `WHERE` | move to a join's `ON`, or filter after fetching |
| `UPDATE SET col = col + 1` | read → compute → update with a literal, in one transaction |
| `UPDATE ... JOIN` / `DELETE ... USING` / `INSERT ... SELECT` / `RETURNING` | read the target rows, then write from the application |
| `AUTO_INCREMENT` / `SERIAL` / `IDENTITY` / sequences | generate the ID in the application |
| `ON CONFLICT DO NOTHING` / `INSERT IGNORE` / table-source `MERGE` | existence check and write in one transaction |
| views, triggers, stored procedures, multi-column indexes | change the design |

A read-only ERROR statement can usually be decomposed into an **execution plan**: fetch rows through
ScalarDB, then run the original SQL in in-memory H2. `--plan-dir` enables it.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/common/sql-migration/scripts/convert.py" <input.sql> --source oracle \
  --out-dir <out> --plan-dir <out>/plans
```

Each fetch in a plan lists `index_columns` — the primary key and the join, correlation and IN-subquery
columns — that would speed up joins if indexed in H2. Building them is optional and off by default.
`--h2-indexes` writes `build_indexes: true` into the plan and the runtime creates the indexes before
the query (`residual-runner run --h2-indexes` does the same). A batch job joining tens of thousands of
rows drops from tens of seconds to seconds; a one-table plan or a small request becomes slower by the
build time (about the load time) and memory (about 1.6× the rows). See references/architecture.md,
Performance.

## Application-side finding codes

A read-only ERROR statement carries the result of inspecting the whole statement, including CTE bodies
and subqueries.

| Code | Severity | Meaning |
|---|---|---|
| `CTE` / `SUBQUERY` / `SET_OP` | ERROR | `WITH`, subqueries, `UNION` and similar are evaluated by the application |
| `HIERARCHICAL` | ERROR | `START WITH` / `CONNECT BY`: walk the tree in the application, or precompute the hierarchy into a table |
| `WINDOW` / `KEEP` | ERROR | window functions, `KEEP (DENSE_RANK FIRST/LAST)` |
| `PROJECTION` / `GROUP` / `PRED` / `ORDER` | ERROR | expressions and functions in the select list, `GROUP BY`, `WHERE`, `ORDER BY`; lists which function in which scope |
| `PIVOT` / `DISTINCT` / `OFFSET` / `NOW` | ERROR | the named construct; `NOW` means compute the time in the application and bind it |
| `RESIDUAL_H2` | ERROR | a construct the plan's H2 cannot run (`CONNECT BY`, `ROLLUP` / `CUBE` / `GROUPING SETS`, `PIVOT` / `UNPIVOT`, `KEEP`); no plan is built |
| `FULL_SCAN` | ERROR | with `--storage cassandra`, a table readable by neither key nor index; every table is listed with a way to read it through a joined table's key (following CTE columns too) |
| `APP_SEMANTICS` | WARN | what an application rewrite must keep so results do not change; not attached to plans, because H2 runs the original SQL |
| `DESIGN` | INFO | summary tables, precomputed hierarchies, keys and indexes on join columns, ScalarDB Analytics |
| `COST` | INFO | read-cost estimate: ~25 µs per scanned row, ~5 ms per key access; `SERIALIZABLE` doubles scans |
| `ROW_LIMIT` | WARN | the plan is expected to exceed its row limit (10,000 by default) |
| `COST_DEADLINE` | WARN | the estimate exceeds the ScalarDB Cluster gRPC deadline (60 s by default) |
| `CONFIG` | INFO | read-only transactions, `scan_fetch_size`, cross-partition scan settings, isolation effects |

With `--storage cassandra`, `FULL_SCAN` suggests "read X first, then Y" only when the joined table can
be read by key. When it cannot either (the dependency is circular), the message says the design needs
to start from a key the application already holds.

## Licensing

ScalarDB SQL is an Enterprise Premium capability and needs ScalarDB Cluster and a license
(@rules/scalardb-edition-profiles.md). Conversion, plan validation and the Core API fetch path need no
license.
