-- =====================================================================
-- 01_raw_views.sql
-- Foundation views over the Parquet data lake. No data is copied here;
-- DuckDB reads the parquet files directly. Placeholders like {TS_GLOB}
-- are substituted by scripts/init_db.py from config.py.
-- =====================================================================

-- Raw 1-minute sensor stream for all 51 machines (~26.8M rows).
CREATE OR REPLACE VIEW raw_sensor AS
SELECT
    timestamp,
    machine_id,
    line_id,
    stage_category,
    product_code,
    machine_state,
    rpm,
    temperature_c,
    vibration_mm_s,
    motor_current_a,
    power_kw,
    pressure_bar,
    throughput_units_min,
    good_count,
    reject_count,
    ambient_temp_c,
    humidity_pct,
    energy_kwh_cumulative,
    degradation_index,
    roast_temp_c,
    grind_micron,
    seal_temp_c,
    nitrogen_flow_lpm
FROM read_parquet('{TS_GLOB}');

-- Machine master data (static attributes: location, dates, ratings).
CREATE OR REPLACE VIEW dim_machine AS
SELECT * FROM read_parquet('{META_PARQUET}');

-- Product master data.
CREATE OR REPLACE VIEW dim_product AS
SELECT * FROM read_parquet('{PRODUCT_PARQUET}');

-- Per-line, per-minute production schedule (campaigns + changeovers).
CREATE OR REPLACE VIEW raw_schedule AS
SELECT * FROM read_parquet('{SCHEDULE_PARQUET}');
