-- title: Predictive Maintenance - Risk Ranking
-- category: Predictive Maintenance
-- description: Blends current degradation, 14-day degradation slope (linear
--   regression), peak vibration vs alarm and maintenance overdue-ness into a
--   0-100 risk score to prioritise interventions.
WITH ds AS (SELECT MAX(day) AS asof FROM agg_machine_day),
recent AS (
    SELECT machine_id, day, avg_degradation, max_vibration, avg_vibration,
           DATE_DIFF('day', DATE '2025-09-01', day) AS day_idx
    FROM agg_machine_day
),
slope14 AS (
    SELECT r.machine_id,
           REGR_SLOPE(r.avg_degradation, r.day_idx) AS degradation_slope_per_day,
           MAX(r.max_vibration)                     AS peak_vibration_14d
    FROM recent r, ds
    WHERE r.day >= ds.asof - INTERVAL 14 DAY
    GROUP BY r.machine_id
),
latest AS (
    SELECT machine_id,
           ARG_MAX(avg_degradation, day) AS current_degradation,
           ARG_MAX(avg_vibration, day)   AS current_vibration
    FROM agg_machine_day GROUP BY machine_id
)
SELECT
    m.machine_id, m.machine_name, m.line_id, m.stage_category, m.criticality_class,
    m.last_maintenance_date, m.next_maintenance_date,
    DATE_DIFF('day', CAST(m.next_maintenance_date AS DATE), ds.asof) AS days_overdue,
    ROUND(latest.current_degradation, 3)              AS current_degradation,
    ROUND(latest.current_vibration, 2)                AS current_vibration,
    ROUND(slope14.degradation_slope_per_day, 5)       AS degradation_slope_per_day,
    ROUND(slope14.peak_vibration_14d, 2)              AS peak_vibration_14d,
    ROUND(100.0 * (
          0.45 * LEAST(latest.current_degradation / 1.4, 1.0)
        + 0.30 * LEAST(slope14.peak_vibration_14d / {VIB_ALARM}, 1.0)
        + 0.15 * LEAST(GREATEST(slope14.degradation_slope_per_day, 0) * 200, 1.0)
        + 0.10 * LEAST(GREATEST(DATE_DIFF('day', CAST(m.next_maintenance_date AS DATE), ds.asof), 0) / 90.0, 1.0)
    ), 1)                                             AS risk_score
FROM dim_machine m
JOIN latest  USING (machine_id)
JOIN slope14 USING (machine_id)
CROSS JOIN ds
ORDER BY risk_score DESC;
