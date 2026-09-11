-- title: OEE by Line (daily)
-- category: OEE & Performance
-- description: Line-level OEE aggregated across all producing machines using
--   pooled availability, performance and quality numerators/denominators.
WITH base AS (
    SELECT d.line_id, d.day,
           d.running_min, d.down_min, d.changeover_min,
           d.good_units, d.reject_units,
           d.running_min * m.nominal_throughput_units_min AS ideal_units
    FROM agg_machine_day d
    JOIN dim_machine m USING (machine_id)
    WHERE m.nominal_throughput_units_min > 0
),
agg AS (
    SELECT line_id, day,
        SUM(running_min) rmin, SUM(down_min) dmin, SUM(changeover_min) cmin,
        SUM(good_units) g, SUM(reject_units) r, SUM(ideal_units) ideal
    FROM base GROUP BY line_id, day
)
SELECT line_id, day,
    ROUND(rmin::DOUBLE / NULLIF(rmin + dmin + cmin, 0), 4)  AS availability,
    ROUND(LEAST(1.0, (g + r)::DOUBLE / NULLIF(ideal, 0)), 4) AS performance,
    ROUND(g::DOUBLE / NULLIF(g + r, 0), 4)                  AS quality,
    ROUND((rmin::DOUBLE / NULLIF(rmin + dmin + cmin, 0))
        * LEAST(1.0, (g + r)::DOUBLE / NULLIF(ideal, 0))
        * (g::DOUBLE / NULLIF(g + r, 0)), 4)                AS oee
FROM agg
ORDER BY day, line_id;
