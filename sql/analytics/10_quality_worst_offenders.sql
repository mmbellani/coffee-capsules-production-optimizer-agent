-- title: Quality - Worst Offenders
-- category: Quality & Output
-- description: Machines ranked by overall reject rate, including the estimated
--   cost of poor quality (rejected capsules x material cost).
WITH q AS (
    SELECT machine_id,
           SUM(good_units)   AS good_units,
           SUM(reject_units) AS reject_units
    FROM agg_machine_day
    GROUP BY machine_id
    HAVING SUM(good_units + reject_units) > 0
)
SELECT
    m.machine_id, m.machine_name, m.line_id, m.stage_category,
    q.good_units, q.reject_units,
    ROUND(100.0 * q.reject_units / NULLIF(q.good_units + q.reject_units, 0), 3) AS reject_rate_pct,
    ROUND(q.reject_units * {CAPSULE_COST}, 0)                                   AS cost_of_poor_quality_eur,
    RANK() OVER (ORDER BY q.reject_units::DOUBLE
                          / NULLIF(q.good_units + q.reject_units, 0) DESC)      AS reject_rank
FROM q
JOIN dim_machine m USING (machine_id)
ORDER BY reject_rate_pct DESC;
