-- title: Downtime Pareto (machine)
-- category: Reliability & Downtime
-- description: Ranks machines by total unplanned-downtime minutes with running
--   (cumulative) share to support 80/20 Pareto analysis.
WITH agg AS (
    SELECT e.machine_id, m.machine_name, m.line_id, m.stage_category, m.criticality_class,
           COUNT(*)            AS episodes,
           SUM(e.duration_min) AS down_min,
           ROUND(AVG(e.duration_min), 1) AS avg_episode_min,
           MAX(e.duration_min) AS longest_episode_min
    FROM fact_downtime_episode e
    JOIN dim_machine m USING (machine_id)
    GROUP BY 1, 2, 3, 4, 5
)
SELECT *,
    ROW_NUMBER() OVER (ORDER BY down_min DESC)                                   AS pareto_rank,
    ROUND(100.0 * down_min / SUM(down_min) OVER (), 2)                           AS pct_of_total,
    ROUND(100.0 * SUM(down_min) OVER (ORDER BY down_min DESC
              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
          / SUM(down_min) OVER (), 2)                                            AS cumulative_pct
FROM agg
ORDER BY down_min DESC;
