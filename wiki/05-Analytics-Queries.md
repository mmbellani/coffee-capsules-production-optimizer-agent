# 05 — Analytics Query Library

The [sql/analytics/](../sql/analytics/) folder holds **19 self-documenting**
analytical queries. Each file starts with header comments that
[app/db.py](../app/db.py) parses into a registry:

```sql
-- title: Plant KPI Summary
-- category: Overview
-- description: Single-row headline KPIs for the whole plant...
```

Because discovery is automatic, **adding a query is just dropping a `.sql` file**
in the folder — it immediately appears in the dashboard's SQL Explorer and
becomes callable by the agent via `run_named_query("<file-stem>")`.

Business assumptions (`{ENERGY_PRICE}`, `{CAPSULE_COST}`, `{VIB_ALARM}`) are
injected as placeholders from [config.py](../config.py) at run time.

## The 19 queries

| # | Query | Category | Techniques |
|---|-------|----------|------------|
| 01 | Plant KPI Summary | Overview | multi-CTE, cross join, OEE math |
| 02 | OEE by Machine (daily) | OEE | joins, `NULLIF` guards, `LEAST` cap |
| 03 | OEE by Line (daily) | OEE | pooled A×P×Q aggregation |
| 04 | 7-Day Rolling OEE Trend | OEE | moving-average window frame |
| 05 | Downtime Pareto | Reliability | window cumulative %, ranking |
| 06 | Reliability MTBF / MTTR | Reliability | episode + uptime joins |
| 07 | State Utilization | Reliability | `FILTER` aggregates |
| 08 | Utilization Heatmap | Reliability | `EXTRACT` hour/weekday |
| 09 | Throughput & Yield | Quality | line×product×day grain |
| 10 | Quality Worst Offenders | Quality | `RANK` window, cost of poor quality |
| 11 | Energy by Line/Day | Energy | multi-CTE, energy intensity |
| 12 | Energy Intensity by Product | Energy | Wh per capsule |
| 13 | Predictive Maintenance Risk | Pred. Maint. | `REGR_SLOPE`, `ARG_MAX`, risk blend |
| 14 | Vibration Exceedance | Pred. Maint. | conditional counts vs alarm |
| 15 | Temperature Anomaly (z-score) | Pred. Maint. | 24h rolling mean/std window |
| 16 | Changeover Analysis | Quality | transition matrix, partition % |
| 17 | Maintenance Schedule | Pred. Maint. | `DATE_DIFF`, overdue status |
| 18 | Bottleneck Analysis | OEE | `ARG_MIN`, balance ratio |
| 19 | Degradation↔Reject Correlation | Pred. Maint. | `CORR()` per machine |

## How the key ones work

- **01 — Plant KPI Summary** ([01_kpi_summary.sql](../sql/analytics/01_kpi_summary.sql)):
  computes availability, performance and quality across all machines, multiplies
  them into OEE, and reports total capsules (from the fillers only), energy kWh,
  energy cost and downtime — a single headline row.

- **05 — Downtime Pareto**: ranks machines by total downtime minutes and adds a
  cumulative-percentage window so you can see which few machines drive most of the
  plant's lost time (the classic 80/20 Pareto view).

- **13 — Predictive Maintenance Risk**: blends degradation slope (`REGR_SLOPE`
  over time), peak recent vibration, and days overdue for service into a single
  0–100 **risk score**. This feeds both the dashboard ranking and the agent's
  maintenance scheduling.

- **15 — Temperature Anomaly (z-score)**: uses a 24-hour rolling mean and standard
  deviation window to flag statistically unusual temperature readings.

- **16 — Changeover Analysis**: builds a from→to product transition matrix and
  measures the time lost to each switch, driving the "run longer campaigns"
  recommendation.

- **18 — Bottleneck Analysis**: for each line-day, finds the station with the
  lowest running-time-normalised throughput (`ARG_MIN`) — the constraint that
  starves everything downstream.

## Running them

- **Dashboard** — the SQL Explorer tab lets you run any saved query or your own
  SQL and download the result as CSV.
- **Code** — `db.run_query("05_downtime_pareto")` returns a pandas DataFrame.
- **Agent** — `Toolbox.run_named_query("05_downtime_pareto")` (see
  [07 — The Agent](07-Agent.md)).

Next: [06 — Dashboard](06-Dashboard.md).
