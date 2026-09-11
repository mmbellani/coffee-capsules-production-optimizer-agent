-- title: Plant KPI Summary
-- category: Overview
-- description: Single-row headline KPIs for the whole plant: OEE and its three
--   components, total capsules produced, energy, cost and downtime.
WITH base AS (
    SELECT d.running_min, d.down_min, d.changeover_min,
           d.good_units, d.reject_units, d.energy_kwh,
           d.running_min * m.nominal_throughput_units_min AS ideal_units
    FROM agg_machine_day d
    JOIN dim_machine m USING (machine_id)
    WHERE m.nominal_throughput_units_min > 0
),
agg AS (
    SELECT SUM(running_min) rmin, SUM(down_min) dmin, SUM(changeover_min) cmin,
           SUM(good_units) g, SUM(reject_units) r, SUM(ideal_units) ideal
    FROM base
),
caps AS (
    SELECT SUM(d.good_units) capsules
    FROM agg_machine_day d JOIN dim_machine m USING (machine_id)
    WHERE m.machine_type = 'doser_filler'
),
en AS (SELECT SUM(energy_kwh) kwh FROM agg_machine_day),
dt AS (SELECT SUM(duration_min) down_min, COUNT(*) episodes FROM fact_downtime_episode)
SELECT
    ROUND(100.0 * rmin / NULLIF(rmin + dmin + cmin, 0), 2)                       AS availability_pct,
    ROUND(100.0 * LEAST(1.0, (g + r) / NULLIF(ideal, 0)), 2)                     AS performance_pct,
    ROUND(100.0 * g / NULLIF(g + r, 0), 2)                                       AS quality_pct,
    ROUND(100.0 * (rmin / NULLIF(rmin + dmin + cmin, 0))
                * LEAST(1.0, (g + r) / NULLIF(ideal, 0))
                * (g / NULLIF(g + r, 0)), 2)                                     AS oee_pct,
    caps.capsules                                                               AS total_capsules,
    ROUND(en.kwh, 0)                                                            AS total_energy_kwh,
    ROUND(en.kwh * {ENERGY_PRICE}, 0)                                           AS total_energy_cost_eur,
    ROUND(dt.down_min / 60.0, 1)                                                AS total_downtime_hours,
    dt.episodes                                                                 AS downtime_events
FROM agg, caps, en, dt;
