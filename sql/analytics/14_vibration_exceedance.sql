-- title: Vibration Exceedance (ISO 10816)
-- category: Predictive Maintenance
-- description: Hours where peak vibration breaches the alarm threshold, per
--   machine, with breach share and peak values.
SELECT
    m.machine_id, m.machine_name, m.line_id, m.stage_category,
    COUNT(*) FILTER (WHERE h.max_vibration > {VIB_ALARM})            AS exceedance_hours,
    COUNT(*)                                                         AS total_hours,
    ROUND(100.0 * COUNT(*) FILTER (WHERE h.max_vibration > {VIB_ALARM})
          / COUNT(*), 2)                                            AS exceedance_pct,
    ROUND(MAX(h.max_vibration), 2)                                  AS peak_vibration,
    ROUND(AVG(h.avg_vibration), 2)                                  AS avg_vibration
FROM agg_machine_hour h
JOIN dim_machine m USING (machine_id)
GROUP BY 1, 2, 3, 4
HAVING COUNT(*) FILTER (WHERE h.max_vibration > {VIB_ALARM}) > 0
ORDER BY exceedance_hours DESC;
