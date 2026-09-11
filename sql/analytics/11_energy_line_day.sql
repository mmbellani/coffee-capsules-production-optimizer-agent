-- title: Energy Consumption by Line/Day
-- category: Energy & Cost
-- description: Daily electrical energy and cost per line, plus energy intensity
--   (kWh per 1,000 good capsules) using true capsule count from the filler.
WITH e AS (
    SELECT line_id, day, SUM(energy_kwh) AS energy_kwh
    FROM agg_machine_day GROUP BY line_id, day
),
g AS (
    SELECT d.line_id, d.day, SUM(d.good_units) AS good_capsules
    FROM agg_machine_day d JOIN dim_machine m USING (machine_id)
    WHERE m.machine_type = 'doser_filler'
    GROUP BY d.line_id, d.day
)
SELECT
    e.line_id, e.day,
    ROUND(e.energy_kwh, 1)                                         AS energy_kwh,
    ROUND(e.energy_kwh * {ENERGY_PRICE}, 2)                        AS energy_cost_eur,
    g.good_capsules,
    ROUND(1000.0 * e.energy_kwh / NULLIF(g.good_capsules, 0), 3)   AS kwh_per_1000_capsules
FROM e JOIN g USING (line_id, day)
ORDER BY e.day, e.line_id;
