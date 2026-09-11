-- title: Degradation vs Reject-Rate Correlation
-- category: Predictive Maintenance
-- description: Pearson correlation between daily health degradation and reject
--   rate per machine - evidence that wear drives quality loss.
WITH d AS (
    SELECT machine_id, day, avg_degradation,
           reject_units::DOUBLE / NULLIF(good_units + reject_units, 0) AS reject_rate
    FROM agg_machine_day
    WHERE good_units + reject_units > 0
)
SELECT
    m.machine_id, m.machine_name, m.line_id, m.stage_category,
    ROUND(CORR(d.avg_degradation, d.reject_rate), 3) AS corr_degradation_reject,
    ROUND(AVG(d.reject_rate) * 100, 3)               AS avg_reject_rate_pct,
    COUNT(*)                                         AS observed_days
FROM d
JOIN dim_machine m USING (machine_id)
GROUP BY 1, 2, 3, 4
HAVING COUNT(*) > 20
ORDER BY corr_degradation_reject DESC;
