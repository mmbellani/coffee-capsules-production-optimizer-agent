# Dashboard

A Streamlit + Plotly application (`app/dashboard.py`) backed by the DuckDB access layer
(`app/db.py`).

```bash
streamlit run app/dashboard.py
```

## Tabs

| Tab | What you get |
|---|---|
| **Overview** | Rolling 7-day OEE, state-utilisation stack, hour × weekday heatmap |
| **OEE & Performance** | Line / machine OEE, availability / performance / quality, bottlenecks |
| **Reliability & Downtime** | Downtime Pareto (with cumulative %), MTBF vs MTTR |
| **Quality & Output** | Output by product, yield, worst offenders, changeover matrix |
| **Energy & Cost** | Daily cost, kWh per 1,000 capsules, energy by product |
| **Predictive Maintenance** | Risk ranking, vibration exceedance, degradation ↔ reject correlation, temperature anomalies, maintenance schedule |
| **Machine Explorer** | Full machine master data |
| **SQL Explorer** | Run any saved query or your own SQL, download CSV |
| **:robot: Agent** | Run the agent and view its diagnosis, plan, schedule and reasoning trace |

!!! tip "Screenshots"
    Add screenshots to `docs/assets/` and embed them here, e.g.
    `![Overview](../assets/overview.png)`.
