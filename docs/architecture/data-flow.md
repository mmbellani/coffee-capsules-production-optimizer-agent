# Data Flow

```mermaid
sequenceDiagram
    participant L as Parquet lake
    participant I as scripts/init_db.py
    participant D as DuckDB
    participant U as Dashboard
    participant A as Agent

    I->>D: create raw views over Parquet
    I->>D: build aggregates & fact tables
    U->>D: run analytics queries
    D-->>U: KPIs, trends, Pareto, heatmaps
    A->>D: call analysis tools
    D-->>A: metrics
    A->>A: diagnose → quantify € → plan
    A-->>U: report, plan, schedule, trace
```

## Stages

1. **Ingest (virtual)** — `sql/01_raw_views.sql` exposes `raw_sensor`, `dim_machine`, `dim_product`, `raw_schedule`.
2. **Aggregate** — `sql/02_build_aggregates.sql` produces hourly/daily roll-ups and episode-level fact tables.
3. **Analyse** — `sql/analytics/*.sql` compute OEE, downtime, quality, energy and maintenance metrics.
4. **Consume** — the dashboard visualises; the agent reasons and plans.
