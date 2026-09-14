-- =====================================================================
-- 02_build_aggregates.sql
-- Heavy one-time roll-ups that turn 26.8M raw minutes into compact,
-- query-friendly fact/aggregate tables. Run by scripts/init_db.py.
-- Uses window functions, FILTER aggregates and gaps-and-islands.
-- =====================================================================

-- ---------------------------------------------------------------------
-- Hourly aggregate per machine (446k rows). Core grain for most charts.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE agg_machine_hour AS
SELECT
    machine_id,
    ANY_VALUE(line_id)                                              AS line_id,
    ANY_VALUE(stage_category)                                       AS stage_category,
    date_trunc('hour', timestamp)                                   AS hour_ts,
    COUNT(*)                                                        AS total_min,
    COUNT(*) FILTER (WHERE machine_state = 'RUNNING')               AS running_min,
    COUNT(*) FILTER (WHERE machine_state = 'IDLE')                  AS idle_min,
    COUNT(*) FILTER (WHERE machine_state = 'DOWN')                  AS down_min,
    COUNT(*) FILTER (WHERE machine_state = 'MAINTENANCE')           AS maintenance_min,
    COUNT(*) FILTER (WHERE machine_state = 'CHANGEOVER')            AS changeover_min,
    SUM(good_count)                                                 AS good_units,
    SUM(reject_count)                                               AS reject_units,
    AVG(rpm)            FILTER (WHERE machine_state = 'RUNNING')     AS avg_rpm,
    AVG(temperature_c)                                              AS avg_temp_c,
    MAX(temperature_c)                                              AS max_temp_c,
    AVG(vibration_mm_s) FILTER (WHERE machine_state = 'RUNNING')     AS avg_vibration,
    MAX(vibration_mm_s)                                             AS max_vibration,
    AVG(power_kw)                                                   AS avg_power_kw,
    MAX(energy_kwh_cumulative) - MIN(energy_kwh_cumulative)         AS energy_kwh,
    AVG(degradation_index)                                          AS avg_degradation,
    MODE(product_code) FILTER (WHERE machine_state = 'RUNNING')      AS dominant_product
FROM raw_sensor
GROUP BY machine_id, date_trunc('hour', timestamp);

-- ---------------------------------------------------------------------
-- Daily aggregate per machine, rolled up from the hourly table.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE agg_machine_day AS
SELECT
    machine_id,
    ANY_VALUE(line_id)              AS line_id,
    ANY_VALUE(stage_category)       AS stage_category,
    CAST(hour_ts AS DATE)           AS day,
    SUM(total_min)                  AS total_min,
    SUM(running_min)                AS running_min,
    SUM(idle_min)                   AS idle_min,
    SUM(down_min)                   AS down_min,
    SUM(maintenance_min)            AS maintenance_min,
    SUM(changeover_min)             AS changeover_min,
    SUM(good_units)                 AS good_units,
    SUM(reject_units)               AS reject_units,
    SUM(energy_kwh)                 AS energy_kwh,
    -- running-time weighted rpm/vibration
    SUM(avg_rpm * running_min)       / NULLIF(SUM(running_min), 0) AS avg_rpm,
    SUM(avg_vibration * running_min) / NULLIF(SUM(running_min), 0) AS avg_vibration,
    MAX(max_vibration)              AS max_vibration,
    SUM(avg_temp_c * total_min)      / NULLIF(SUM(total_min), 0)   AS avg_temp_c,
    MAX(max_temp_c)                 AS max_temp_c,
    AVG(avg_degradation)            AS avg_degradation
FROM agg_machine_hour
GROUP BY machine_id, CAST(hour_ts AS DATE);

-- ---------------------------------------------------------------------
-- Line x Product x Day aggregate (production mix / yield / energy).
-- Only counts producing minutes (excludes NONE / idle labels).
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE agg_line_product_day AS
SELECT
    line_id,
    product_code,
    CAST(timestamp AS DATE)                          AS day,
    COUNT(*) FILTER (WHERE machine_state = 'RUNNING') AS running_min,
    SUM(good_count)                                  AS good_units,
    SUM(reject_count)                                AS reject_units,
    SUM(energy_kwh_per_min)                          AS energy_kwh
FROM (
    SELECT *,
           energy_kwh_cumulative
             - LAG(energy_kwh_cumulative) OVER (PARTITION BY machine_id ORDER BY timestamp)
             AS energy_kwh_per_min
    FROM raw_sensor
    WHERE stage_category = 'filling'          -- the capsule-producing stage
)
WHERE product_code <> 'NONE'
GROUP BY line_id, product_code, CAST(timestamp AS DATE);

-- ---------------------------------------------------------------------
-- Downtime episodes (gaps-and-islands over the DOWN state).
-- Each row = one contiguous unplanned-stop event.
--
-- Rewritten from the classic "two ROW_NUMBER() windows, then filter"
-- pattern to a single-pass version: (1) push the machine_state = 'DOWN'
-- filter down BEFORE windowing, shrinking the input from 26.8M rows to
-- only the ~205k DOWN-state rows, and (2) replace the two window passes
-- (each needing its own full sort -- one PARTITION BY machine_id, one
-- PARTITION BY machine_id, machine_state) with a single ROW_NUMBER()
-- pass plus one-minute date arithmetic. Since raw_sensor is a strictly
-- regular 1-row-per-minute stream (verified: every consecutive reading
-- per machine is exactly 60s apart), `timestamp - row_number() * 1 min`
-- is constant within a contiguous run of DOWN minutes and jumps whenever
-- there's a gap -- the standard "gaps and islands via arithmetic" trick.
-- EXPLAIN ANALYZE showed the original two WINDOW operators cumulatively
-- costing ~19.7s + ~16.4s of thread-time (the single largest cost in the
-- whole build); profiling the rewrite shows a single ~0.1s window pass
-- over the pre-filtered rows -- verified byte-identical output.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE fact_downtime_episode AS
WITH down_rows AS (
    SELECT
        machine_id, line_id, stage_category, timestamp,
        timestamp - (ROW_NUMBER() OVER (PARTITION BY machine_id ORDER BY timestamp) * INTERVAL 1 MINUTE)
          AS island
    FROM raw_sensor
    WHERE machine_state = 'DOWN'
)
SELECT
    machine_id,
    ANY_VALUE(line_id)          AS line_id,
    ANY_VALUE(stage_category)   AS stage_category,
    MIN(timestamp)              AS start_ts,
    MAX(timestamp)              AS end_ts,
    COUNT(*)                    AS duration_min
FROM down_rows
GROUP BY machine_id, island;

-- ---------------------------------------------------------------------
-- Changeover episodes per line (gaps-and-islands over the schedule),
-- capturing the product transition (from_product -> to_product).
--
-- prev_prod/next_prod need LAG/LEAD over the FULL (unfiltered) schedule
-- (a changeover row's neighbours may not themselves be changeover rows),
-- so that pass can't be pushed past a filter. But the island id used
-- purely for grouping contiguous changeover minutes together no longer
-- needs a second ROW_NUMBER() pass over the full table partitioned by
-- (line_id, changeover): raw_schedule is a strictly regular 1-row-per-
-- minute stream per line, so once we filter down to just the changeover
-- rows we can derive the island with a single ROW_NUMBER() + one-minute
-- date-arithmetic trick (see fact_downtime_episode above for the same
-- pattern) instead of a second full-table windowed pass. Verified
-- byte-identical output against the original double-ROW_NUMBER version.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE fact_changeover_episode AS
WITH s AS (
    SELECT
        line_id, timestamp, changeover, scheduled_product,
        LAG(scheduled_product)  OVER (PARTITION BY line_id ORDER BY timestamp) AS prev_prod,
        LEAD(scheduled_product) OVER (PARTITION BY line_id ORDER BY timestamp) AS next_prod
    FROM raw_schedule
),
filtered AS (
    SELECT
        line_id, timestamp, prev_prod, next_prod,
        timestamp - (ROW_NUMBER() OVER (PARTITION BY line_id ORDER BY timestamp) * INTERVAL 1 MINUTE)
          AS island
    FROM s
    WHERE changeover
)
SELECT
    line_id,
    MIN(timestamp)                       AS start_ts,
    MAX(timestamp)                       AS end_ts,
    COUNT(*)                             AS duration_min,
    ARG_MIN(prev_prod, timestamp)        AS from_product,
    ARG_MAX(next_prod, timestamp)        AS to_product
FROM filtered
GROUP BY line_id, island;
