-- title: OEE by Machine (daily)
-- category: OEE & Performance
-- description: Overall Equipment Effectiveness = Availability x Performance x
--   Quality, computed per producing machine per day. Availability excludes
--   idle/maintenance; performance benchmarks output against nominal rate.
WITH base AS (
    SELECT
        d.machine_id, m.machine_name, m.machine_type, d.line_id, d.stage_category, d.day,
        d.running_min, d.down_min, d.changeover_min, d.good_units, d.reject_units,
        m.nominal_throughput_units_min AS ideal_rate
    FROM agg_machine_day d
    JOIN dim_machine m USING (machine_id)
    WHERE m.nominal_throughput_units_min > 0
),
calc AS (
    SELECT *,
        running_min::DOUBLE / NULLIF(running_min + down_min + changeover_min, 0) AS availability,
        LEAST(1.0, (good_units + reject_units)::DOUBLE
                   / NULLIF(running_min * ideal_rate, 0))                        AS performance,
        good_units::DOUBLE / NULLIF(good_units + reject_units, 0)                AS quality
    FROM base
)
SELECT
    machine_id, machine_name, machine_type, line_id, stage_category, day,
    running_min, down_min, changeover_min, good_units, reject_units,
    ROUND(availability, 4)                       AS availability,
    ROUND(performance, 4)                         AS performance,
    ROUND(quality, 4)                             AS quality,
    ROUND(availability * performance * quality, 4) AS oee
FROM calc
ORDER BY day, line_id, machine_id;
