-- title: Utilization Heatmap (hour x weekday)
-- category: Reliability & Downtime
-- description: Average running share per line by hour-of-day and day-of-week,
--   exposing shift patterns and weekend/maintenance windows.
SELECT
    line_id,
    CAST(EXTRACT(dow  FROM hour_ts) AS INTEGER) AS weekday,   -- 0=Sun .. 6=Sat
    CAST(EXTRACT(hour FROM hour_ts) AS INTEGER) AS hour_of_day,
    ROUND(100.0 * SUM(running_min) / SUM(total_min), 1)       AS running_pct,
    ROUND(AVG(avg_temp_c), 1)                                 AS avg_temp_c
FROM agg_machine_hour
GROUP BY line_id, weekday, hour_of_day
ORDER BY line_id, weekday, hour_of_day;
