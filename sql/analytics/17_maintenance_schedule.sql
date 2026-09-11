-- title: Maintenance Schedule & Adherence
-- category: Predictive Maintenance
-- description: Static maintenance calendar per machine with days-since-last,
--   days-until-next and overdue status relative to the dataset clock.
WITH ds AS (SELECT MAX(day) AS asof FROM agg_machine_day)
SELECT
    m.machine_id, m.machine_name, m.line_id, m.stage_category, m.criticality_class,
    m.construction_date, m.installation_date,
    m.last_maintenance_date, m.next_maintenance_date, m.maintenance_interval_days,
    DATE_DIFF('day', CAST(m.last_maintenance_date AS DATE), ds.asof) AS days_since_last,
    DATE_DIFF('day', ds.asof, CAST(m.next_maintenance_date AS DATE)) AS days_until_next,
    CASE WHEN CAST(m.next_maintenance_date AS DATE) < ds.asof
         THEN 'OVERDUE' ELSE 'SCHEDULED' END                        AS maintenance_status
FROM dim_machine m CROSS JOIN ds
ORDER BY days_until_next ASC;
