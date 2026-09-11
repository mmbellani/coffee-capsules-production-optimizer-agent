-- title: Bottleneck Analysis (line/day)
-- category: OEE & Performance
-- description: Identifies the rate-limiting machine per line per day by
--   comparing running-time-normalised throughput across unit-producing stages.
WITH r AS (
    SELECT line_id, day, machine_id, stage_category,
           good_units, running_min,
           good_units::DOUBLE / NULLIF(running_min, 0) AS units_per_run_min
    FROM agg_machine_day
    WHERE running_min > 0 AND good_units > 0
)
SELECT
    line_id, day,
    ARG_MIN(machine_id, units_per_run_min)      AS bottleneck_machine,
    ARG_MIN(stage_category, units_per_run_min)  AS bottleneck_stage,
    ROUND(MIN(units_per_run_min), 1)            AS bottleneck_rate,
    ROUND(MAX(units_per_run_min), 1)            AS fastest_rate,
    ROUND(MIN(units_per_run_min)
          / NULLIF(MAX(units_per_run_min), 0), 3) AS balance_ratio
FROM r
GROUP BY line_id, day
ORDER BY day, line_id;
