# sql-migration-shop

A small existing system for the SQL migration skills (`/architect:design-sql-migration`,
`implement-sql-migration`, `verify-sql-migration`): a PostgreSQL schema, a MyBatis mapper, plain JDBC, Spring Data
JPA and a nightly batch script. Every statement is planted to exercise one decision, and the table below is the
answer key a smoke run is checked against.

| Path | Content |
|---|---|
| `db/schema.sql` | Tables, an index and a sequence (PostgreSQL) |
| `db/seed.sql` | Test data for a disposable source database and for ScalarDB |
| `batch/monthly-report.sql` | A report query and a stock correction |
| `src/main/resources/mapper/OrderMapper.xml` | MyBatis: key reads, a dynamic search, an insert that uses a sequence and the clock |
| `src/main/java/com/shop/OrderDao.java` | JDBC: a resolved constant, a concatenation, SQL from configuration |
| `src/main/java/com/shop/CustomerRepository.java` | JPA: a native query and a JPQL query |

## Answer key

Converted with `--source postgres`, `--edition enterprise_premium`, `--storage jdbc`, and the schema's own keys
(`orders` partitioned by `customer_id`, clustered by `order_no`).

| Statement | Converter | Expected route | Why |
|---|---|---|---|
| `CREATE TABLE customers`, `orders`, `order_items`, `stock`; `CREATE INDEX idx_orders_status` | OK | `schema` | Definitions that become the ScalarDB schema |
| `CREATE SEQUENCE order_no_seq` | ERROR (`DDL`) | `app_side` (`id_generation`) | ScalarDB has no sequences |
| `OrderMapper#findOrder` | OK | `scalardb_sql` | GET by the full primary key |
| `OrderMapper#findByStatus` | OK | `scalardb_sql` | Index scan on `status` |
| `OrderMapper#search` | ERROR (dynamic) | `app_side` or confirmed variants | `<where>` / `<if>`: a family of statements; the user confirms the renderings |
| `OrderMapper#insertOrder` | ERROR (`SEQUENCE`) | `app_side` (`id_generation`) | `nextval` and `CURRENT_DATE` move to the application |
| `OrderDao#customerOrders` | PLANNED | `plan` | `COALESCE` in the select list; a partition scan feeds H2 |
| `OrderDao#sortedOrderNumbers` | ERROR (dynamic) | `app_side` or `redesign` | `ORDER BY` concatenated from a variable |
| `OrderDao#configuredReport` | — | reported as unextracted | The SQL comes from configuration; static reading cannot see it |
| `CustomerRepository#byRegion` | WARN (`CROSS_PARTITION`) | `scalardb_sql` or `redesign` | No key or index on `region`; the cost decides |
| `CustomerRepository#vipCustomers` | ERROR (`JPQL`) | `app_side` or `redesign` | JPQL is not SQL the converter reads |
| monthly report (`batch/monthly-report.sql`) | PLANNED | `plan` | Aggregation over a join whose `ON` does not cover the `orders` key |
| stock correction (`batch/monthly-report.sql`) | ERROR (`RMW`) | `app_side` (`rmw`) | `qty = qty - 1` reads before it writes |

## Verification

The monthly report is the one plan without bind parameters, so a differential test compares it directly against
ScalarDB (Core API). Statements with bind parameters are proven by golden checks or unit tests.

The application-side reads cannot run on the source database as written, so each golden check captures a rendering
the user confirmed. These renderings, with `db/seed.sql` loaded into PostgreSQL 18.6, were verified:

| Statement | Rendering | Values | Expected rows |
|---|---|---|---|
| `CustomerRepository#vipCustomers` | `SELECT customer_id, name, region, vip FROM customers WHERE vip = TRUE` | — | 2 (customers 1 and 4) |
| `OrderDao#sortedOrderNumbers` | `SELECT order_no FROM orders ORDER BY total` | `column=total` | 8, ordered; order 106 (NULL total) last |
| `OrderMapper#search` | `SELECT customer_id, order_no FROM orders WHERE status = :status AND total >= :minTotal` | `status=PAID`, `minTotal=5000` | 2 (orders 104 and 108) |

Other renderings remain unproven until they are captured: another sort column, or `search` with only one `<if>`
branch. The same applies to the application-side writes (the sequence, the insert and the stock correction), which
golden checks do not cover.
