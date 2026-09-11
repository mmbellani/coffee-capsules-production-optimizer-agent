-- title: 7-Day Rolling OEE Trend (line)
-- category: OEE & Performance
-- description: Line OEE with a trailing 7-day moving average using a window
--   frame, to smooth daily noise and reveal drift.
WITH base AS (
    SELECT d.line_id, d.day,
           d.running_min, d.down_min, d.changeover_min,
           d.good_units, d.reject_units,
           d.running_min * m.nominal_throughput_units_min AS ideal_units
    FROM agg_machine_day d
    JOIN dim_machine m USING (machine_id)
    WHERE m.nominal_throughput_units_min > 0
),
line_day AS (
    SELECT line_id, day,
        (SUM(running_min)::DOUBLE / NULLIF(SUM(running_min + down_min + changeover_min), 0))
      * LEAST(1.0, SUM(good_units + reject_units)::DOUBLE / NULLIF(SUM(ideal_units), 0))
      * (SUM(good_units)::DOUBLE / NULLIF(SUM(good_units + reject_units), 0)) AS oee
    FROM base GROUP BY line_id, day
)
SELECT line_id, day,
    ROUND(oee, 4) AS oee,
    ROUND(AVG(oee) OVER (
        PARTITION BY line_id ORDER BY day
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 4) AS oee_7d_avg
FROM line_day
ORDER BY line_id, day;
