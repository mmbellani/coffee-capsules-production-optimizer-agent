# Running the App

## 1. Build the warehouse

```bash
python scripts/init_db.py
```

This creates `coffee_bi.duckdb` by:

1. Creating views over the Parquet files (`sql/01_raw_views.sql`) — no data copy.
2. Materialising compact aggregates and fact tables (`sql/02_build_aggregates.sql`).

It is a one-time step and takes seconds.

## 2. Launch the dashboard

```bash
streamlit run app/dashboard.py
```

Streamlit opens the UI in your browser. See [Dashboard](../dashboard/index.md) for a tour.

## 3. Run the agent

```bash
python -m agent.run_agent
```

Outputs are written to `agent_output/`. See [CLI Reference](../agent/cli.md) and [Outputs](../agent/outputs.md).
