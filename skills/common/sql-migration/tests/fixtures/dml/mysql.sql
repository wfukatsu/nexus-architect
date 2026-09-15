-- DML and practical SELECT patterns for the SQL migration tests (source dialect: MySQL)
-- The first half prepares tables and data (the same data in all three dialects). The second half holds the statements
-- under test; statements with the same @id do the same thing in every dialect.
-- Annotations:
--   @id               number shared by the three dialects (I = INSERT, U = UPDATE, D = DELETE, S = SELECT, T = transaction)
--   @note             what the statement exercises
--   @check            query run after the DML to compare results
--   @expect-scalardb  expected ScalarDB SQL conversion (OK / WARN / PLANNED / ERROR), asserted by tests/dml_examples.test.py
-- Origin: github.com/wfukatsu/sql-migration skills/sql-transpile/examples/dml (commit 1d2e4db), translated to English

CREATE TABLE customers (customer_id INT PRIMARY KEY, name VARCHAR(40), email VARCHAR(60), region VARCHAR(10), vip TINYINT(1), created_at DATE);
CREATE TABLE products (product_id INT PRIMARY KEY, name VARCHAR(40), category VARCHAR(20), price DECIMAL(9,2), active TINYINT(1));
CREATE TABLE orders (order_id INT PRIMARY KEY, customer_id INT, order_date DATE, status VARCHAR(10) DEFAULT 'NEW', total DECIMAL(10,2), note VARCHAR(100));
CREATE INDEX idx_orders_customer ON orders (customer_id);
CREATE TABLE order_items (order_id INT, line_no INT, product_id INT, qty INT, unit_price DECIMAL(9,2), PRIMARY KEY (order_id, line_no));
CREATE TABLE stock (warehouse_id INT, product_id INT, qty INT, updated_at DATETIME, PRIMARY KEY (warehouse_id, product_id));
CREATE TABLE audit_log (log_id BIGINT AUTO_INCREMENT PRIMARY KEY, table_name VARCHAR(30), action VARCHAR(10), logged_at DATETIME) AUTO_INCREMENT = 100;
CREATE TABLE seq_counter (name VARCHAR(30) PRIMARY KEY, next_val BIGINT);
INSERT INTO customers VALUES (1, 'Alice Smith', 'alice@example.com', 'EAST', TRUE, '2024-01-10');
INSERT INTO customers VALUES (2, 'Bob Jones', 'bob@example.com', 'WEST', FALSE, '2024-02-15');
INSERT INTO customers VALUES (3, 'Carol White', NULL, 'EAST', FALSE, '2024-03-01');
INSERT INTO customers VALUES (4, 'Dave Brown', 'dave_b@example.com', 'NORTH', TRUE, '2024-03-20');
INSERT INTO customers VALUES (5, 'Eve Black', 'eve%promo@example.com', 'WEST', FALSE, '2024-04-05');
INSERT INTO customers VALUES (6, 'frank green', 'frank@example.com', NULL, FALSE, '2024-05-12');
INSERT INTO products VALUES (101, 'Keyboard', 'PERIPHERAL', 49.99, TRUE);
INSERT INTO products VALUES (102, 'Mouse', 'PERIPHERAL', 19.50, TRUE);
INSERT INTO products VALUES (103, 'Monitor', 'DISPLAY', 199.00, TRUE);
INSERT INTO products VALUES (104, 'Laptop', 'COMPUTER', 1200.00, TRUE);
INSERT INTO products VALUES (105, 'USB Cable', 'ACCESSORY', 5.25, FALSE);
INSERT INTO products VALUES (106, 'Webcam', 'PERIPHERAL', NULL, TRUE);
INSERT INTO orders VALUES (1001, 1, '2024-06-01', 'SHIPPED', 69.49, NULL);
INSERT INTO orders VALUES (1002, 1, '2024-06-15', 'NEW', 199.00, 'gift');
INSERT INTO orders VALUES (1003, 2, '2024-06-20', 'CANCELLED', 19.50, NULL);
INSERT INTO orders VALUES (1004, 3, '2024-07-02', 'SHIPPED', 1249.99, NULL);
INSERT INTO orders VALUES (1005, 4, '2024-07-10', 'NEW', 10.50, 'rush');
INSERT INTO orders VALUES (1006, 4, '2024-07-11', 'PAID', 398.00, NULL);
INSERT INTO orders VALUES (1007, 5, '2024-08-01', 'PAID', 1200.00, NULL);
INSERT INTO orders VALUES (1008, 2, '2024-08-15', 'NEW', 0, NULL);
INSERT INTO order_items VALUES (1001, 1, 101, 1, 49.99);
INSERT INTO order_items VALUES (1001, 2, 102, 1, 19.50);
INSERT INTO order_items VALUES (1002, 1, 103, 1, 199.00);
INSERT INTO order_items VALUES (1003, 1, 102, 1, 19.50);
INSERT INTO order_items VALUES (1004, 1, 104, 1, 1200.00);
INSERT INTO order_items VALUES (1004, 2, 101, 1, 49.99);
INSERT INTO order_items VALUES (1005, 1, 105, 2, 5.25);
INSERT INTO order_items VALUES (1006, 1, 103, 2, 199.00);
INSERT INTO order_items VALUES (1007, 1, 104, 1, 1200.00);
INSERT INTO stock VALUES (1, 101, 50, '2024-08-01 09:00:00');
INSERT INTO stock VALUES (1, 102, 120, '2024-08-01 09:00:00');
INSERT INTO stock VALUES (1, 103, 15, '2024-08-01 09:00:00');
INSERT INTO stock VALUES (1, 104, 5, '2024-08-01 09:00:00');
INSERT INTO stock VALUES (2, 101, 30, '2024-08-01 09:00:00');
INSERT INTO stock VALUES (2, 103, 0, '2024-08-01 09:00:00');
INSERT INTO stock VALUES (2, 104, 8, '2024-08-01 09:00:00');
INSERT INTO stock VALUES (2, 105, 200, '2024-08-01 09:00:00');
INSERT INTO audit_log (log_id, table_name, action, logged_at) VALUES (1, 'orders', 'INSERT', '2024-08-01 10:00:00');
INSERT INTO audit_log (log_id, table_name, action, logged_at) VALUES (2, 'stock', 'UPDATE', '2024-08-01 11:00:00');
INSERT INTO seq_counter VALUES ('order_seq', 5000);

-- @tests
-- @id: I01
-- @note: Single-row INSERT with a column list (primary key included)
-- @check: SELECT customer_id, name, email, region FROM customers WHERE customer_id = 7
-- @expect-scalardb: OK
INSERT INTO customers (customer_id, name, email, region, vip, created_at) VALUES (7, 'Grace Lee', 'grace@example.com', 'SOUTH', FALSE, '2024-09-01');
-- @id: I02
-- @note: INSERT without a column list (depends on the table's column order)
-- @check: SELECT product_id, name, category, price FROM products WHERE product_id = 107
-- @expect-scalardb: WARN
INSERT INTO products VALUES (107, 'Headset', 'PERIPHERAL', 79.00, TRUE);
-- @id: I03
-- @note: Multi-row INSERT (Oracle uses INSERT ALL; PostgreSQL and MySQL list several VALUES rows)
-- @check: SELECT order_id, line_no, product_id, qty FROM order_items WHERE order_id = 1008 ORDER BY line_no
-- @expect-scalardb: OK
INSERT INTO order_items (order_id, line_no, product_id, qty, unit_price) VALUES (1008, 1, 102, 2, 19.50), (1008, 2, 105, 3, 5.25);
-- @id: I04
-- @note: INSERT ... SELECT (copies rows from another table)
-- @check: SELECT log_id, table_name, action FROM audit_log WHERE action = 'ARCHIVE' ORDER BY log_id
-- @expect-scalardb: ERROR
INSERT INTO audit_log (log_id, table_name, action, logged_at) SELECT order_id, 'orders', 'ARCHIVE', order_date FROM orders WHERE status = 'CANCELLED';
-- @id: I05
-- @note: DEFAULT inside VALUES (uses the column default; ScalarDB has no column defaults)
-- @check: SELECT order_id, status, note FROM orders WHERE order_id = 1009
-- @expect-scalardb: ERROR
INSERT INTO orders (order_id, customer_id, order_date, status, total, note) VALUES (1009, 6, '2024-09-02', DEFAULT, 0, NULL);
-- @id: I06
-- @note: Inserts the current time (SYSTIMESTAMP / CURRENT_TIMESTAMP / NOW())
-- @check: SELECT COUNT(*) AS n FROM audit_log WHERE log_id = 3 AND logged_at IS NOT NULL
-- @expect-scalardb: ERROR
INSERT INTO audit_log (log_id, table_name, action, logged_at) VALUES (3, 'customers', 'LOGIN', NOW());
-- @id: I07
-- @note: Omits the primary key and relies on a generated column (IDENTITY / AUTO_INCREMENT). The table conversion fails with AUTO_INC, so the converter cannot detect the missing primary key
-- @check: SELECT COUNT(*) AS n FROM audit_log WHERE action = 'EXPORT'
-- @expect-scalardb: OK
INSERT INTO audit_log (table_name, action, logged_at) VALUES ('orders', 'EXPORT', '2024-09-03 12:00:00');
-- @id: I08
-- @note: Generates the primary key from a sequence (MySQL has no sequences, so it updates a counter table)
-- @check: SELECT next_val FROM seq_counter WHERE name = 'order_seq'
-- @expect-scalardb: ERROR
UPDATE seq_counter SET next_val = LAST_INSERT_ID(next_val + 1) WHERE name = 'order_seq';
-- @id: I09
-- @note: Upsert that adds to an existing row or inserts a new one (an update that references a column)
-- @check: SELECT qty FROM stock WHERE warehouse_id = 1 AND product_id = 102
-- @expect-scalardb: ERROR
INSERT INTO stock (warehouse_id, product_id, qty) VALUES (1, 102, 10) ON DUPLICATE KEY UPDATE qty = qty + VALUES(qty);
-- @id: I10
-- @note: Upsert that overwrites some columns of an existing row or inserts a new one (UPSERT overwrites every column)
-- @check: SELECT product_id, name, category, price FROM products WHERE product_id = 102
-- @expect-scalardb: WARN
INSERT INTO products (product_id, name, category, price, active) VALUES (102, 'Mouse Pro', 'PERIPHERAL', 24.00, TRUE) ON DUPLICATE KEY UPDATE name = VALUES(name), price = VALUES(price);
-- @id: I11
-- @note: Inserts only when the row is absent (Oracle uses NOT EXISTS, PostgreSQL ON CONFLICT DO NOTHING, MySQL INSERT IGNORE)
-- @check: SELECT customer_id, name FROM customers WHERE customer_id = 1
-- @expect-scalardb: ERROR
INSERT IGNORE INTO customers (customer_id, name, email, region, vip, created_at) VALUES (1, 'Alice Duplicate', NULL, 'EAST', FALSE, '2024-09-04');
-- @id: I12
-- @note: Scalar subquery inside VALUES (looks up the unit price in another table)
-- @check: SELECT order_id, line_no, unit_price FROM order_items WHERE order_id = 1005 ORDER BY line_no
-- @expect-scalardb: ERROR
INSERT INTO order_items (order_id, line_no, product_id, qty, unit_price) VALUES (1005, 2, 103, 1, (SELECT price FROM products WHERE product_id = 103));
-- @id: U01
-- @note: Single-row UPDATE by primary key
-- @check: SELECT order_id, status FROM orders WHERE order_id = 1002
-- @expect-scalardb: OK
UPDATE orders SET status = 'SHIPPED' WHERE order_id = 1002;
-- @id: U02
-- @note: UPDATE by composite primary key (timestamp literal)
-- @check: SELECT qty, updated_at FROM stock WHERE warehouse_id = 1 AND product_id = 101
-- @expect-scalardb: OK
UPDATE stock SET qty = 45, updated_at = '2024-09-01 10:00:00' WHERE warehouse_id = 1 AND product_id = 101;
-- @id: U03
-- @note: Multi-row UPDATE on a non-key condition (becomes a cross-partition scan)
-- @check: SELECT order_id, note FROM orders WHERE status = 'NEW' ORDER BY order_id
-- @expect-scalardb: WARN
UPDATE orders SET note = 'check' WHERE status = 'NEW';
-- @id: U04
-- @note: UPDATE that uses the current value (decrements stock; needs read, compute, write)
-- @check: SELECT qty FROM stock WHERE warehouse_id = 1 AND product_id = 103
-- @expect-scalardb: ERROR
UPDATE stock SET qty = qty - 5 WHERE warehouse_id = 1 AND product_id = 103;
-- @id: U05
-- @note: Conditionally updates several columns with CASE
-- @check: SELECT product_id, price, active FROM products ORDER BY product_id
-- @expect-scalardb: ERROR
UPDATE products SET price = CASE WHEN category = 'PERIPHERAL' THEN price * 0.9 ELSE price END, active = CASE WHEN price IS NULL THEN FALSE ELSE active END WHERE category IN ('PERIPHERAL', 'ACCESSORY');
-- @id: U06
-- @note: Correlated subquery in SET (recomputes the order total from its line items)
-- @check: SELECT order_id, total FROM orders WHERE order_id IN (1001, 1004) ORDER BY order_id
-- @expect-scalardb: ERROR
UPDATE orders o SET o.total = (SELECT COALESCE(SUM(i.qty * i.unit_price), 0) FROM order_items i WHERE i.order_id = o.order_id) WHERE o.order_id IN (1001, 1004);
-- @id: U07
-- @note: UPDATE conditioned on another table (Oracle uses EXISTS, PostgreSQL UPDATE ... FROM, MySQL UPDATE ... JOIN)
-- @check: SELECT order_id, note FROM orders ORDER BY order_id
-- @expect-scalardb: ERROR
UPDATE orders o JOIN customers c ON c.customer_id = o.customer_id SET o.note = 'vip' WHERE c.vip = TRUE;
-- @id: U08
-- @note: Sets NULL and filters with IS NULL
-- @check: SELECT customer_id, email, region FROM customers WHERE customer_id = 6
-- @expect-scalardb: WARN
UPDATE customers SET email = NULL, region = 'UNKNOWN' WHERE region IS NULL;
-- @id: U09
-- @note: UPDATE combining a primary-key IN list with BETWEEN
-- @check: SELECT order_id, status FROM orders WHERE order_id IN (1005, 1008) ORDER BY order_id
-- @expect-scalardb: WARN
UPDATE orders SET status = 'PAID' WHERE order_id IN (1005, 1008) AND total BETWEEN 0 AND 100;
-- @id: U10
-- @note: Date arithmetic (Oracle adds days, PostgreSQL uses INTERVAL, MySQL DATE_ADD)
-- @check: SELECT order_id, order_date FROM orders WHERE order_id = 1005
-- @expect-scalardb: ERROR
UPDATE orders SET order_date = DATE_ADD(order_date, INTERVAL 7 DAY) WHERE order_id = 1005;
-- @id: U11
-- @note: UPDATE of only the first row in an order (Oracle uses ROWNUM, PostgreSQL LIMIT in a subquery, MySQL ORDER BY ... LIMIT)
-- @check: SELECT order_id, status FROM orders WHERE status = 'HOLD'
-- @expect-scalardb: ERROR
UPDATE orders SET status = 'HOLD' WHERE status = 'NEW' ORDER BY order_date, order_id LIMIT 1;
-- @id: U12
-- @note: UPDATE filtered by a secondary-index column
-- @check: SELECT order_id, status FROM orders WHERE customer_id = 5
-- @expect-scalardb: OK
UPDATE orders SET status = 'CANCELLED' WHERE customer_id = 5;
-- @id: D01
-- @note: Single-row DELETE by composite primary key
-- @check: SELECT COUNT(*) AS n FROM order_items WHERE order_id = 1003
-- @expect-scalardb: OK
DELETE FROM order_items WHERE order_id = 1003 AND line_no = 1;
-- @id: D02
-- @note: DELETE by partition key and a clustering-key range
-- @check: SELECT line_no FROM order_items WHERE order_id = 1004 ORDER BY line_no
-- @expect-scalardb: OK
DELETE FROM order_items WHERE order_id = 1004 AND line_no >= 2;
-- @id: D03
-- @note: DELETE by an IN list on a non-key column (becomes a cross-partition scan)
-- @check: SELECT warehouse_id, product_id, qty FROM stock ORDER BY warehouse_id, product_id
-- @expect-scalardb: WARN
DELETE FROM stock WHERE qty IN (0, 200);
-- @id: D04
-- @note: DELETE without WHERE (every row)
-- @check: SELECT COUNT(*) AS n FROM audit_log
-- @expect-scalardb: WARN
DELETE FROM audit_log;
-- @id: D05
-- @note: DELETE filtered by an EXISTS subquery (line items of cancelled orders)
-- @check: SELECT order_id, line_no FROM order_items ORDER BY order_id, line_no
-- @expect-scalardb: ERROR
DELETE FROM order_items i WHERE EXISTS (SELECT 1 FROM orders o WHERE o.order_id = i.order_id AND o.status = 'CANCELLED');
-- @id: D06
-- @note: Deletes orders without line items using NOT EXISTS
-- @check: SELECT order_id FROM orders ORDER BY order_id
-- @expect-scalardb: ERROR
DELETE FROM orders WHERE NOT EXISTS (SELECT 1 FROM order_items i WHERE i.order_id = orders.order_id);
-- @id: D07
-- @note: DELETE conditioned on another table (Oracle uses an IN subquery, PostgreSQL USING, MySQL a multi-table DELETE)
-- @check: SELECT COUNT(*) AS n FROM order_items
-- @expect-scalardb: ERROR
DELETE i FROM order_items i JOIN orders o ON o.order_id = i.order_id WHERE o.status = 'CANCELLED';
-- @id: D08
-- @note: DELETE of only the first row in an order (Oracle uses ROWNUM, PostgreSQL LIMIT in a subquery, MySQL ORDER BY ... LIMIT)
-- @check: SELECT log_id FROM audit_log ORDER BY log_id
-- @expect-scalardb: ERROR
DELETE FROM audit_log ORDER BY logged_at, log_id LIMIT 1;
-- @id: D09
-- @note: DELETE that returns the deleted row (PostgreSQL RETURNING; Oracle and MySQL have no equivalent, so they only delete by primary key)
-- @check: SELECT COUNT(*) AS n FROM orders WHERE order_id = 1003
-- @expect-scalardb: OK
DELETE FROM orders WHERE order_id = 1003;
-- @id: S01
-- @note: Partition-key equality with a clustering-key range
-- @expect-scalardb: OK
SELECT line_no, product_id, qty FROM order_items WHERE order_id = 1004 AND line_no BETWEEN 1 AND 2 ORDER BY line_no;
-- @id: S02
-- @note: Keyset pagination (row-value comparison; Oracle writes it with OR)
-- @expect-scalardb: PLANNED
SELECT order_id, line_no, qty FROM order_items WHERE (order_id, line_no) > (1004, 1) ORDER BY order_id, line_no LIMIT 3;
-- @id: S03
-- @note: OFFSET pagination
-- @expect-scalardb: PLANNED
SELECT order_id, order_date FROM orders ORDER BY order_date, order_id LIMIT 3 OFFSET 2;
-- @id: S04
-- @note: Three-table join with aggregation and HAVING
-- @expect-scalardb: PLANNED
SELECT c.region, COUNT(DISTINCT o.order_id) AS orders, SUM(i.qty * i.unit_price) AS amount FROM customers c JOIN orders o ON o.customer_id = c.customer_id JOIN order_items i ON i.order_id = o.order_id WHERE o.status <> 'CANCELLED' GROUP BY c.region HAVING SUM(i.qty * i.unit_price) > 100 ORDER BY c.region;
-- @id: S05
-- @note: Anti-join with LEFT JOIN and IS NULL (orders without line items)
-- @expect-scalardb: PLANNED
SELECT o.order_id FROM orders o LEFT JOIN order_items i ON i.order_id = o.order_id WHERE i.order_id IS NULL ORDER BY o.order_id;
-- @id: S06
-- @note: Correlated scalar subquery in the select list
-- @expect-scalardb: PLANNED
SELECT c.customer_id, c.name, (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.customer_id) AS order_count FROM customers c ORDER BY c.customer_id;
-- @id: S07
-- @note: Top row per group (ROW_NUMBER)
-- @expect-scalardb: PLANNED
SELECT customer_id, order_id, total FROM (SELECT customer_id, order_id, total, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY total DESC, order_id) AS rn FROM orders) t WHERE rn = 1 ORDER BY customer_id;
-- @id: S08
-- @note: Conditional aggregation with CASE
-- @expect-scalardb: PLANNED
SELECT customer_id, SUM(CASE WHEN status = 'NEW' THEN 1 ELSE 0 END) AS new_orders, SUM(CASE WHEN status IN ('PAID', 'SHIPPED') THEN total ELSE 0 END) AS paid_amount FROM orders GROUP BY customer_id ORDER BY customer_id;
-- @id: S09
-- @note: LIKE with ESCAPE (email addresses containing %)
-- @expect-scalardb: WARN
SELECT customer_id, email FROM customers WHERE email LIKE '%!%%' ESCAPE '!' ORDER BY customer_id;
-- @id: S10
-- @note: Case-insensitive search (Oracle uses UPPER, PostgreSQL ILIKE, MySQL its default collation)
-- @expect-scalardb: WARN
SELECT customer_id, name FROM customers WHERE name LIKE 'FRANK%' ORDER BY customer_id;
-- @id: S11
-- @note: Monthly aggregation (Oracle uses TRUNC, PostgreSQL DATE_TRUNC, MySQL DATE_FORMAT)
-- @expect-scalardb: PLANNED
SELECT DATE_FORMAT(order_date, '%Y-%m-01') AS month, COUNT(*) AS n, SUM(total) AS amount FROM orders GROUP BY DATE_FORMAT(order_date, '%Y-%m-01') ORDER BY month;
-- @id: S12
-- @note: Explicit NULL ordering (MySQL has no NULLS LAST, so it sorts by IS NULL)
-- @expect-scalardb: PLANNED
SELECT product_id, price FROM products ORDER BY price IS NULL, price DESC, product_id;
-- @id: S13
-- @note: Rows of two tables combined with UNION ALL
-- @expect-scalardb: PLANNED
SELECT customer_id AS id, 'customer' AS kind FROM customers WHERE region = 'EAST' UNION ALL SELECT product_id, 'product' FROM products WHERE category = 'DISPLAY' ORDER BY id;
-- @id: S14
-- @note: Semi-join with EXISTS (customers with a paid order)
-- @expect-scalardb: PLANNED
SELECT c.customer_id, c.name FROM customers c WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id AND o.status = 'PAID') ORDER BY c.customer_id;
-- @id: S15
-- @note: Reads with a row lock (FOR UPDATE)
-- @expect-scalardb: WARN
SELECT qty FROM stock WHERE warehouse_id = 2 AND product_id = 104 FOR UPDATE;
-- @id: S16
-- @note: Filters on a boolean column (Oracle NUMBER(1), PostgreSQL BOOLEAN, MySQL TINYINT(1))
-- @expect-scalardb: WARN
SELECT customer_id, name FROM customers WHERE vip = TRUE ORDER BY customer_id;
-- @id: S17
-- @note: Aggregation filtered by a secondary index
-- @expect-scalardb: OK
SELECT COUNT(*) AS n, SUM(total) AS amount FROM orders WHERE customer_id = 4;
-- @id: T01
-- @note: SAVEPOINT (ScalarDB has no savepoints)
-- @expect-scalardb: ERROR
SAVEPOINT before_update;
