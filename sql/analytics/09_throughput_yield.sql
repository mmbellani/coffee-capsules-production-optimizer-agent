-- title: Throughput & Yield by Line/Product/Day
-- category: Quality & Output
-- description: Daily good/reject output, first-pass yield and reject rate per
--   line and product, from the filling (capsule-producing) stage.
SELECT
    line_id, product_code, day,
    running_min,
    good_units, reject_units,
    good_units + reject_units                                              AS total_units,
    ROUND(100.0 * good_units   / NULLIF(good_units + reject_units, 0), 3)  AS yield_pct,
    ROUND(100.0 * reject_units / NULLIF(good_units + reject_units, 0), 3)  AS reject_rate_pct,
    ROUND(energy_kwh, 1)                                                   AS energy_kwh
FROM agg_line_product_day
ORDER BY day, line_id, product_code;
