-- sql-migration-shop: the existing PostgreSQL schema the SQL migration skills read.
CREATE TABLE customers (
  customer_id BIGINT PRIMARY KEY,
  name VARCHAR(40) NOT NULL,
  region VARCHAR(10),
  vip BOOLEAN
);

CREATE TABLE orders (
  customer_id BIGINT,
  order_no BIGINT,
  status VARCHAR(10),
  total BIGINT,
  ordered_at DATE,
  PRIMARY KEY (customer_id, order_no)
);

CREATE INDEX idx_orders_status ON orders (status);

CREATE TABLE order_items (
  order_no BIGINT,
  line_no INT,
  product_id BIGINT,
  qty INT,
  unit_price BIGINT,
  PRIMARY KEY (order_no, line_no)
);

CREATE TABLE stock (
  product_id BIGINT PRIMARY KEY,
  qty INT
);

CREATE SEQUENCE order_no_seq START 1000;
