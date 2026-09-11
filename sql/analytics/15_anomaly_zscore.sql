-- title: Temperature Anomaly Detection (rolling z-score)
-- category: Predictive Maintenance
-- description: Flags hourly temperatures that deviate > 3 sigma from a trailing
--   24-hour rolling mean/std per machine (leakage-free window frame).
WITH r AS (
    SELECT machine_id, line_id, stage_category, hour_ts, avg_temp_c, max_vibration,
        AVG(avg_temp_c)        OVER w AS roll_mean,
        STDDEV_SAMP(avg_temp_c) OVER w AS roll_std
    FROM agg_machine_hour
    WINDOW w AS (PARTITION BY machine_id ORDER BY hour_ts
                 ROWS BETWEEN 24 PRECEDING AND 1 PRECEDING)
)
SELECT
    machine_id, line_id, stage_category, hour_ts,
    ROUND(avg_temp_c, 2)  AS avg_temp_c,
    ROUND(roll_mean, 2)   AS roll_mean,
    ROUND(roll_std, 3)    AS roll_std,
    ROUND((avg_temp_c - roll_mean) / NULLIF(roll_std, 0), 2) AS zscore
FROM r
WHERE roll_std > 0.05
  AND ABS((avg_temp_c - roll_mean) / NULLIF(roll_std, 0)) > 3
ORDER BY ABS((avg_temp_c - roll_mean) / NULLIF(roll_std, 0)) DESC
LIMIT 1000;
