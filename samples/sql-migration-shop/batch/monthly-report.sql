-- Nightly batch: revenue by region, then the stock correction the warehouse job applies.
SELECT c.region, SUM(i.qty * i.unit_price) AS amount
FROM customers c
JOIN orders o ON o.customer_id = c.customer_id
JOIN order_items i ON i.order_no = o.order_no
WHERE o.status <> 'CANCELLED'
GROUP BY c.region
ORDER BY c.region;

UPDATE stock SET qty = qty - 1 WHERE product_id = 10;
