-- title: Reliability - MTBF / MTTR
-- category: Reliability & Downtime
-- description: Mean Time Between Failures and Mean Time To Repair per machine,
--   derived from downtime episodes and total running time, with availability.
WITH up AS (
    SELECT machine_id, SUM(running_min) AS running_min
    FROM agg_machine_day GROUP BY machine_id
),
dt AS (
    SELECT machine_id,
           COUNT(*)              AS failures,
           SUM(duration_min)     AS down_min,
           AVG(duration_min)     AS mttr_min
    FROM fact_downtime_episode GROUP BY machine_id
)
SELECT
    m.machine_id, m.machine_name, m.line_id, m.stage_category, m.criticality_class,
    COALESCE(dt.failures, 0)                                   AS failures,
    up.running_min,
    ROUND(up.running_min / NULLIF(dt.failures, 0), 0)          AS mtbf_min,
    ROUND(dt.mttr_min, 1)                                      AS mttr_min,
    ROUND(up.running_min
          / NULLIF(up.running_min + dt.down_min, 0), 4)        AS inherent_availability
FROM dim_machine m
LEFT JOIN up USING (machine_id)
LEFT JOIN dt USING (machine_id)
ORDER BY failures DESC, mtbf_min ASC;
