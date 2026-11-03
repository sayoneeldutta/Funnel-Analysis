-- Funnel by device
SELECT
    device,
    SUM(r1) AS visits, SUM(r2) AS product_views, SUM(r3) AS add_to_cart,
    SUM(r4) AS checkout, SUM(r5) AS payment, SUM(r6) AS purchases,
    ROUND(100.0 * SUM(r5) / NULLIF(SUM(r4), 0), 1) AS checkout_to_payment_pct,
    ROUND(100.0 * SUM(r6) / SUM(r1), 2)            AS overall_conv_pct
FROM user_funnel
GROUP BY device
ORDER BY overall_conv_pct DESC;
