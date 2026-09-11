-- title: State Utilization (machine)
-- category: Reliability & Downtime
-- description: Share of time each machine spends RUNNING / IDLE / DOWN /
--   MAINTENANCE / CHANGEOVER across the whole horizon.
SELECT
    machine_id, line_id, stage_category,
    SUM(running_min)     AS running_min,
    SUM(idle_min)        AS idle_min,
    SUM(down_min)        AS down_min,
    SUM(maintenance_min) AS maintenance_min,
    SUM(changeover_min)  AS changeover_min,
    SUM(total_min)       AS total_min,
    ROUND(100.0 * SUM(running_min)     / SUM(total_min), 2) AS running_pct,
    ROUND(100.0 * SUM(idle_min)        / SUM(total_min), 2) AS idle_pct,
    ROUND(100.0 * SUM(down_min)        / SUM(total_min), 2) AS down_pct,
    ROUND(100.0 * SUM(maintenance_min) / SUM(total_min), 2) AS maintenance_pct,
    ROUND(100.0 * SUM(changeover_min)  / SUM(total_min), 2) AS changeover_pct
FROM agg_machine_hour
GROUP BY machine_id, line_id, stage_category
ORDER BY running_pct DESC;
