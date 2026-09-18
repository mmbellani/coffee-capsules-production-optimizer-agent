# 02 — Architecture

## End-to-end data flow

```mermaid
flowchart LR
    A[Parquet data lake<br/>timeseries/*.parquet<br/>~26.8M rows] --> B
    subgraph DuckDB warehouse
      B[Raw views<br/>01_raw_views.sql] --> C[Aggregate & fact tables<br/>02_build_aggregates.sql]
    end
    C --> D[19 analytics queries<br/>sql/analytics/*.sql]
    D --> E[Streamlit dashboard<br/>app/dashboard.py]
    D --> F[Agent<br/>agent/]
    F --> G[Reports & plan<br/>agent_output/]
    F --> E
```

The build step (`scripts/init_db.py`) runs the two foundation SQL scripts once to
create `coffee_bi.duckdb`. Everything downstream reads from that warehouse.

## Layered design

| Layer | Files | Responsibility |
|-------|-------|----------------|
| **Config** | [config.py](../config.py) | Paths, business assumptions, agent/optimizer parameters, SQL placeholder substitutions |
| **Data lake** | `../coffee_capsule_dataset/` (external) | Raw Parquet sensor data (not in this repo) |
| **Warehouse build** | [sql/01_raw_views.sql](../sql/01_raw_views.sql), [sql/02_build_aggregates.sql](../sql/02_build_aggregates.sql), [scripts/init_db.py](../scripts/init_db.py) | Views over Parquet + materialised aggregates/facts |
| **Analytics** | [sql/analytics/](../sql/analytics/) (19 files) | Self-documenting complex KPI queries |
| **Access layer** | [app/db.py](../app/db.py) | Connect, substitute placeholders, discover & run queries |
| **UI** | [app/dashboard.py](../app/dashboard.py) | Interactive Streamlit + Plotly dashboard |
| **Agent** | [agent/](../agent/) | Tools, diagnosis, planning, optimization, narration, reporting |

## Agent internal architecture

```mermaid
flowchart TD
    RA[run_agent.py<br/>CLI] --> AG[agent.py<br/>EfficiencyAgent]
    AG --> TB[tools.py<br/>Toolbox: read-only warehouse access]
    AG --> AN[analyzers.py<br/>diagnose → Findings]
    AG --> PL[planner.py<br/>build_production_plan]
    AG --> OP[optimizer.py<br/>MILP scenario optimizer]
    PL --> MA[milp_allocator.py<br/>line×product×day MILP]
    AG --> LM[llm.py<br/>optional narrative]
    AG --> RP[report.py<br/>markdown / JSON / parquet]
    TB --> DB[(app/db.py → DuckDB)]
```

The agent follows an explicit **plan → act → observe** loop and records a
transparent trace of every step (visible in the report and the dashboard's
Agent tab). When LLM credentials are present it adds an executive narrative;
otherwise it uses a deterministic template — the numeric results are identical
either way, because the deterministic engine is always the source of truth.

## Determinism guarantees

Both MILP solves ([agent/milp_allocator.py](../agent/milp_allocator.py) and
[agent/optimizer.py](../agent/optimizer.py)) are made bit-for-bit reproducible by:
sorting all lines/products/days before building variables, pinning CBC to a
single thread, fixing the CBC random seed, and solving to a tight optimality gap.
This means the same inputs always produce the same schedule.

Next: [03 — Getting Started](03-Getting-Started.md).
