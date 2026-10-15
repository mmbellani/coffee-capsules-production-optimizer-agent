# Analytics Library

`sql/analytics/` contains **19 self-documenting analytical queries**. They are the single
source of truth for metrics shown in the dashboard and used by the agent.

## Coverage

| Area | Examples of questions answered |
|---|---|
| **OEE & performance** | Line / machine OEE; availability, performance, quality; bottlenecks; rolling 7-day OEE |
| **Reliability & downtime** | Downtime Pareto with cumulative %; MTBF vs MTTR |
| **Quality & output** | Output by product; yield; worst offenders; changeover matrix |
| **Energy & cost** | Daily cost; kWh per 1,000 capsules; energy by product |
| **Predictive maintenance** | Risk ranking; vibration exceedance; degradation ↔ reject correlation; temperature anomalies; maintenance schedule |
| **Utilisation** | State-utilisation stack; hour × weekday heatmap |

## Running a query

From the dashboard, open **SQL Explorer**, pick a saved query or write your own, and
download results as CSV.

!!! note "Self-documenting"
    Each `.sql` file carries a header comment describing what it computes —
    open the file for the exact logic.

See [KPI Definitions](kpis.md).
