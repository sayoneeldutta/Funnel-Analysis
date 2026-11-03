-- Funnel by acquisition channel
SELECT
    channel,
    SUM(r1) AS visits, SUM(r2) AS product_views, SUM(r3) AS add_to_cart,
    SUM(r4) AS checkout, SUM(r5) AS payment, SUM(r6) AS purchases,
    ROUND(100.0 * SUM(r2) / SUM(r1), 1)             AS visit_to_view_pct,
    ROUND(100.0 * SUM(r3) / NULLIF(SUM(r2), 0), 1)  AS view_to_cart_pct,
    ROUND(100.0 * SUM(r6) / SUM(r1), 2)             AS overall_conv_pct
FROM user_funnel
GROUP BY channel
ORDER BY overall_conv_pct DESC;
