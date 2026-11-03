-- Overall funnel: users, step conversion, overall conversion, drop-off
WITH steps AS (
    SELECT 1 AS step_no, 'visit'          AS step, SUM(r1) AS users FROM user_funnel
    UNION ALL SELECT 2, 'product_view',   SUM(r2) FROM user_funnel
    UNION ALL SELECT 3, 'add_to_cart',    SUM(r3) FROM user_funnel
    UNION ALL SELECT 4, 'checkout_start', SUM(r4) FROM user_funnel
    UNION ALL SELECT 5, 'payment_info',   SUM(r5) FROM user_funnel
    UNION ALL SELECT 6, 'purchase',       SUM(r6) FROM user_funnel
)
SELECT
    step_no, step, users,
    ROUND(100.0 * users / LAG(users) OVER (ORDER BY step_no), 1)               AS step_conv_pct,
    ROUND(100.0 * (1 - 1.0 * users / LAG(users) OVER (ORDER BY step_no)), 1)   AS dropoff_pct,
    ROUND(100.0 * users / FIRST_VALUE(users) OVER (ORDER BY step_no), 2)       AS overall_pct
FROM steps
ORDER BY step_no;
