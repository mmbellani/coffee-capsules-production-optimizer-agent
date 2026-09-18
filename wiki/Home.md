# ☕ Coffee Capsule Production Optimizer — Wiki

Welcome to the project wiki. This is a self-contained **Business Intelligence +
agentic optimization** platform for a synthetic coffee-capsule manufacturing
plant. It turns ~27 million raw sensor rows into decision-ready insight and an
optimized production plan.

## What this project does (in one paragraph)

A synthetic factory (3 lines, 51 machines, 1-minute sensors over a full year)
emits ~26.8M rows of Parquet sensor data. **DuckDB** builds a compact analytical
warehouse over that lake, a library of **19 complex SQL queries** computes
manufacturing KPIs (OEE, downtime, quality, energy, predictive maintenance), a
**Streamlit + Plotly** dashboard makes it explorable, and an **agentic layer**
diagnoses euro-quantified inefficiencies and generates an optimized production
plan using a real **Mixed-Integer Linear Program (MILP)**.

## Wiki index

| Page | What it covers |
|------|----------------|
| [01 — Overview](01-Overview.md) | The problem, the goals, key concepts (OEE, capsules, euros) |
| [02 — Architecture](02-Architecture.md) | End-to-end data flow and module map |
| [03 — Getting Started](03-Getting-Started.md) | Install, build the warehouse, run the dashboard & agent |
| [04 — Data & Warehouse](04-Data-And-Warehouse.md) | The Parquet lake, DuckDB views, aggregate/fact tables |
| [05 — Analytics Query Library](05-Analytics-Queries.md) | The 19 self-documenting SQL queries |
| [06 — Dashboard](06-Dashboard.md) | The Streamlit UI and its tabs |
| [07 — The Agent](07-Agent.md) | Tools, analyzers, planner, orchestrator, LLM, reports |
| [08 — MILP Optimizer](08-Optimizer-MILP.md) | The scenario optimizer and allocation solver |
| [09 — Configuration](09-Configuration.md) | Every config knob and environment variable |
| [10 — CLI Reference](10-CLI-Reference.md) | `run_agent` command-line options |
| [11 — Darwin Token Optimization](11-Darwin-Token-Optimization.md) | How the LLM narration prompt was cut 88.1% with identical outputs |
| [12 — Darwin Warehouse Build Speedup](12-Darwin-Warehouse-Build-Speedup.md) | Track A: 3.10× faster DuckDB warehouse build with byte-identical tables |
| [13 — Darwin Optimizer Margin Gain](13-Darwin-Optimizer-Margin-Gain.md) | Track B: +0.19% provably-feasible margin gain on the already-optimal MILP |
| [14 — Darwin Planner Fulfilment to 100%](14-Darwin-Planner-Fulfilment.md) | Track C: planner lifted to 100% demand fulfilment, feasible and changeover-free |
| [15 — Baseline Performance (Before Darwin)](15-Baseline-Performance.md) | The repo's original pre-Darwin numbers that every experiment measured against |
| [16 — How Darwin Produced These Results](16-How-Darwin-Produced-These-Results.md) | The method behind pages 11–14: evolutionary search, evaluators, gates, and why the numbers are trustworthy |
| [17 — SQL Result Equality: Literature Review](17-SQL-Result-Equality-Literature-Review.md) | Background theory on verifying two SQL results are exactly equal (the basis of the build-speedup gate) |
| [18 — ROI of Running Darwin](18-ROI-Of-Running-Darwin.md) | Quantified return on investment for the SQL build speedup and the token optimization |

## Quick links to the code

- Warehouse builder: [scripts/init_db.py](../scripts/init_db.py)
- DuckDB access layer: [app/db.py](../app/db.py)
- Dashboard: [app/dashboard.py](../app/dashboard.py)
- Agent orchestrator: [agent/agent.py](../agent/agent.py)
- Diagnosis engine: [agent/analyzers.py](../agent/analyzers.py)
- Production planner: [agent/planner.py](../agent/planner.py)
- MILP optimizer: [agent/optimizer.py](../agent/optimizer.py)
- Central config: [config.py](../config.py)
