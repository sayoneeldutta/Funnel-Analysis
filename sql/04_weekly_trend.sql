-- Weekly cohorts (by first-visit week, Monday start) x device
SELECT
    date(t1, 'weekday 0', '-6 days') AS week_start,
    device,
    SUM(r1) AS visits,
    SUM(r6) AS purchases,
    ROUND(100.0 * SUM(r6) / SUM(r1), 2)            AS overall_conv_pct,
    ROUND(100.0 * SUM(r6) / NULLIF(SUM(r5), 0), 1) AS payment_to_purchase_pct
FROM user_funnel
GROUP BY week_start, device
ORDER BY week_start, device;
