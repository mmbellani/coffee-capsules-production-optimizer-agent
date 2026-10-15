# Architecture

The solution is **self-contained**: no external database server and no cloud dependency
for the core analytics or the agent's deterministic engine.

```mermaid
flowchart LR
    subgraph Lake["Parquet lake"]
        P1[sensor data]
        P2[machine master]
        P3[products]
        P4[schedule]
    end

    subgraph WH["DuckDB warehouse (coffee_bi.duckdb)"]
        V[Raw views<br/>01_raw_views.sql]
        AGG[Aggregates & fact tables<br/>02_build_aggregates.sql]
        Q[19 analytics queries<br/>sql/analytics/*.sql]
    end

    subgraph App["Applications"]
        DB[app/db.py<br/>access layer]
        UI[Streamlit + Plotly<br/>app/dashboard.py]
        AG[Agent<br/>agent/]
    end

    Lake --> V --> AGG --> Q
    Q --> DB --> UI
    DB --> AG
    AG --> UI
    AG -. optional .-> LLM[(LLM)]
```

## Design principles

| Principle | How it shows up |
|---|---|
| **Query in place** | DuckDB reads Parquet directly through views — no ETL copy. |
| **Pay once for heavy work** | Expensive roll-ups are materialised once into compact tables. |
| **SQL as a library** | Analytics are versioned, self-documenting `.sql` files reused by UI and agent. |
| **Deterministic first** | The agent's analysis and plan don't depend on an LLM. |
| **LLM as narrator** | When available, the LLM explains — it does not compute. |

## Sections

- [Data Flow](data-flow.md)
- [Repository Structure](repository-structure.md)
