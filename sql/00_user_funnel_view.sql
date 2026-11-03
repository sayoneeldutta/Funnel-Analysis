-- One row per user with ordered-funnel flags r1..r6.
-- Rules:
--   * unique users, using each user's FIRST occurrence of every event (this de-duplicates double-fired events)
--   * each step must happen at/after the previous step
--   * every step must fall within 7 days of the user's first visit (conversion window)
--   * a user counts at a step only if they counted at all earlier steps (strict funnel)
DROP VIEW IF EXISTS user_funnel;
CREATE VIEW user_funnel AS
WITH first_events AS (
    SELECT
        user_id,
        MIN(CASE WHEN event_name = 'session_start'  THEN event_ts END) AS t1,
        MIN(CASE WHEN event_name = 'product_view'   THEN event_ts END) AS t2,
        MIN(CASE WHEN event_name = 'add_to_cart'    THEN event_ts END) AS t3,
        MIN(CASE WHEN event_name = 'checkout_start' THEN event_ts END) AS t4,
        MIN(CASE WHEN event_name = 'payment_info'   THEN event_ts END) AS t5,
        MIN(CASE WHEN event_name = 'purchase'       THEN event_ts END) AS t6
    FROM events
    GROUP BY user_id
),
a2 AS (
    SELECT *, CASE WHEN t2 IS NOT NULL AND t2 >= t1
                   AND t2 <= datetime(t1, '+7 days') THEN 1 ELSE 0 END AS r2
    FROM first_events WHERE t1 IS NOT NULL
),
a3 AS (
    SELECT *, CASE WHEN r2 = 1 AND t3 IS NOT NULL AND t3 >= t2
                   AND t3 <= datetime(t1, '+7 days') THEN 1 ELSE 0 END AS r3
    FROM a2
),
a4 AS (
    SELECT *, CASE WHEN r3 = 1 AND t4 IS NOT NULL AND t4 >= t3
                   AND t4 <= datetime(t1, '+7 days') THEN 1 ELSE 0 END AS r4
    FROM a3
),
a5 AS (
    SELECT *, CASE WHEN r4 = 1 AND t5 IS NOT NULL AND t5 >= t4
                   AND t5 <= datetime(t1, '+7 days') THEN 1 ELSE 0 END AS r5
    FROM a4
),
a6 AS (
    SELECT *, CASE WHEN r5 = 1 AND t6 IS NOT NULL AND t6 >= t5
                   AND t6 <= datetime(t1, '+7 days') THEN 1 ELSE 0 END AS r6
    FROM a5
)
SELECT
    a6.user_id, u.channel, u.device,
    a6.t1, a6.t2, a6.t3, a6.t4, a6.t5, a6.t6,
    1 AS r1, a6.r2, a6.r3, a6.r4, a6.r5, a6.r6
FROM a6
JOIN users u ON u.user_id = a6.user_id;
