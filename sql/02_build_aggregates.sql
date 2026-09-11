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
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE fact_downtime_episode AS
WITH flagged AS (
    SELECT
        machine_id, line_id, stage_category, timestamp, machine_state,
        ROW_NUMBER() OVER (PARTITION BY machine_id ORDER BY timestamp)
          - ROW_NUMBER() OVER (PARTITION BY machine_id, machine_state ORDER BY timestamp)
          AS island
    FROM raw_sensor
)
SELECT
    machine_id,
    ANY_VALUE(line_id)          AS line_id,
    ANY_VALUE(stage_category)   AS stage_category,
    MIN(timestamp)              AS start_ts,
    MAX(timestamp)              AS end_ts,
    COUNT(*)                    AS duration_min
FROM flagged
WHERE machine_state = 'DOWN'
GROUP BY machine_id, island;

-- ---------------------------------------------------------------------
-- Changeover episodes per line (gaps-and-islands over the schedule),
-- capturing the product transition (from_product -> to_product).
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE fact_changeover_episode AS
WITH s AS (
    SELECT
        line_id, timestamp, changeover, scheduled_product,
        ROW_NUMBER() OVER (PARTITION BY line_id ORDER BY timestamp)
          - ROW_NUMBER() OVER (PARTITION BY line_id, changeover ORDER BY timestamp)
          AS island,
        LAG(scheduled_product)  OVER (PARTITION BY line_id ORDER BY timestamp) AS prev_prod,
        LEAD(scheduled_product) OVER (PARTITION BY line_id ORDER BY timestamp) AS next_prod
    FROM raw_schedule
)
SELECT
    line_id,
    MIN(timestamp)                       AS start_ts,
    MAX(timestamp)                       AS end_ts,
    COUNT(*)                             AS duration_min,
    ARG_MIN(prev_prod, timestamp)        AS from_product,
    ARG_MAX(next_prod, timestamp)        AS to_product
FROM s
WHERE changeover
GROUP BY line_id, island;
