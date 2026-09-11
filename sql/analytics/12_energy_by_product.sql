-- title: Energy Intensity by Product
-- category: Energy & Cost
-- description: Compares filling-stage energy per product with output and yield
--   to reveal which capsule type is most energy-intensive to produce.
SELECT
    product_code,
    SUM(good_units)                                              AS good_units,
    SUM(reject_units)                                            AS reject_units,
    ROUND(SUM(energy_kwh), 0)                                    AS energy_kwh,
    ROUND(SUM(energy_kwh) * {ENERGY_PRICE}, 0)                   AS energy_cost_eur,
    ROUND(100.0 * SUM(good_units)
          / NULLIF(SUM(good_units + reject_units), 0), 3)        AS yield_pct,
    ROUND(1e6 * SUM(energy_kwh)
          / NULLIF(SUM(good_units), 0), 2)                       AS wh_per_capsule
FROM agg_line_product_day
GROUP BY product_code
ORDER BY wh_per_capsule DESC;
