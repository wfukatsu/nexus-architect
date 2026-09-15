# Application-side processing: semantics to keep and helper classes

Applies when a read statement runs neither as ScalarDB SQL nor as an execution plan (H2) and is
rewritten in the application (Java). An `APP_SEMANTICS` finding points at a row of the table below.

The table comes from problems that actually surfaced when an Oracle "monthly sales by area and shop"
report was rewritten for ScalarDB.

## Semantics to keep

| Construct | Oracle behaviour | Typical Java mistake | Helper |
|---|---|---|---|
| `LAG` / `LEAD` | the previous / next **row** in the partition; a month without sales is skipped | compares with the calendar's previous month | `Windows.lag` / `Windows.lead` |
| division | division by zero fails the whole statement with `ORA-01476`; PostgreSQL also errors, MySQL returns NULL | silently yields NULL or infinity | `OracleNumbers.divide` |
| `ROUND` | rounds half away from zero (-2.5 → -3) | rounds `HALF_EVEN` or in `double` | `OracleNumbers.round` |
| `SUM` / `AVG` / `MIN` / `MAX` | ignore NULLs; all NULL gives NULL | returns 0, or counts NULL as 0 | `OracleNumbers.sum` / `avg`, `Windows.movingAverage` |
| `RANK` / `DENSE_RANK` | equal values share a rank; NULLs are equal to each other | advances the rank on ties | `Windows.rank` / `Windows.denseRank` |
| `ORDER BY` (NULL) | NULLs last for ASC, first for DESC (MySQL is the reverse) | comparator ignores NULL | `OracleOrdering.asc` / `desc` |
| `ORDER BY` (strings) | with `NLS_SORT=BINARY`, code-point order (AL32UTF8 byte order) | `String.compareTo` (UTF-16 order) reorders surrogate pairs such as "𠮷" | `OracleOrdering.BINARY` |
| `CONNECT BY` | `LEVEL` of the `START WITH` row is 1; a cycle raises `ORA-01436` | counts depth from 0, loops forever on a cycle | `Hierarchy.connectBy` |
| `SYS_CONNECT_BY_PATH` | prefixes every value with the separator, the first too; a value containing the separator raises `ORA-30004` | drops the leading separator | `Hierarchy.connectBy` (with path) |
| `ADD_MONTHS` | month end stays month end (12 months before 2025-02-28 is 2024-02-29) | uses `LocalDate.plusMonths` as is | `OracleDates.addMonths` |
| `TO_CHAR` (dates) | formats with the session time zone and date language | formats with the JVM time zone and locale | `OracleDates.yearMonth` (`YYYY-MM`) |
| `SYSDATE` | the database server's clock and time zone | uses the JVM clock | — (inject a clock) |
| empty string | Oracle treats `''` as NULL | distinguishes `""` from NULL | — |

All helpers live in the vendored runtime, package `com.scalar.migrate.appside`
(`skills/common/sql-migration/runtime-java/`).

## Rewriting what H2 cannot run

A `RESIDUAL_H2` statement can, instead of an application implementation, be rewritten into SQL that
H2 runs and then planned again.

| Construct | Rewrite |
|---|---|
| `CONNECT BY` / `SYS_CONNECT_BY_PATH` | recursive `WITH`; build the path by string concatenation in the recursive part |
| `ROLLUP` / `CUBE` / `GROUPING SETS` | one `SELECT` per aggregation level combined with `UNION ALL` |
| `PIVOT` | conditional aggregation such as `SUM(CASE WHEN job = 'A' THEN sal END)` |
| `UNPIVOT` | one `SELECT` per column combined with `UNION ALL` |
| `KEEP (DENSE_RANK FIRST ...)` | select the rows where `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...) = 1` |

Run the rewritten SQL through the converter again with `--plan-dir` and confirm it becomes PLANNED.

## Checking an implementation against the source (golden)

An application-side implementation is compared with results captured once from the source database.
Capturing needs the source database once; every later check runs without any database.

- The implementation class implements `com.scalar.migrate.appside.AppSideQuery`: tables keyed by
  lower-case table name, rows by lower-case column name.
- `ordered` in `golden.json` follows whether the top-level query has `ORDER BY`. Rows with equal
  `ORDER BY` values have no defined order even in Oracle, so suspect that first when a diff appears.
- Numbers compare with `BigDecimal.compareTo` (`2.50` equals `2.5`). An Oracle `DATE` comes back as a
  date-time, so a `LocalDate` is treated as that day at 00:00.

The commands are in references/operations.md and in `/architect:verify-sql-migration`.
