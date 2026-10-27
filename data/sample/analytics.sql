-- Developer verification examples only. UTC months; USD; no tax/shipping/discount columns.

-- Completed-order revenue: excludes pending, cancelled, and fully refunded orders.
SELECT date_trunc('month', order_date AT TIME ZONE 'UTC') AS month,
       sum(total_amount) AS revenue_usd
FROM orders WHERE status = 'completed' GROUP BY 1 ORDER BY 1;

-- Top five products by completed-order line revenue.
SELECT p.product_id, p.name, sum(i.quantity * i.unit_price) AS revenue_usd
FROM products p JOIN order_items i USING(product_id) JOIN orders o USING(order_id)
WHERE o.status = 'completed'
GROUP BY p.product_id, p.name ORDER BY revenue_usd DESC, p.product_id LIMIT 5;

-- Allocate payment-level refunds by each category's original line value.
-- Fixture refunds are full-order, so allocation reconciles exactly before final rounding.
SELECT p.category,
       round(sum(r.amount * i.quantity * i.unit_price / o.total_amount), 2) AS refunds_usd
FROM refunds r JOIN payments pay USING(payment_id) JOIN orders o USING(order_id)
JOIN order_items i USING(order_id) JOIN products p USING(product_id)
GROUP BY p.category ORDER BY p.category;

-- All order statuses included; customers with zero orders are retained.
SELECT c.customer_id, c.name, count(o.order_id) AS order_count
FROM customers c LEFT JOIN orders o USING(customer_id)
GROUP BY c.customer_id, c.name ORDER BY order_count DESC, c.customer_id;

-- Count payment attempts, not distinct customers or orders.
SELECT payment_method, count(*) AS failed_attempts
FROM payments WHERE payment_status = 'failed' GROUP BY payment_method ORDER BY payment_method;
