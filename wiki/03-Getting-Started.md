# 03 — Getting Started

## Prerequisites

- Python 3.10+ (uses `X | Y` type unions and modern dataclasses)
- The Parquet **data lake** produced by the dataset generator. By default the app
  looks for it at the sibling folder `../coffee_capsule_dataset`. Point elsewhere
  with the `COFFEE_DATA_DIR` environment variable.

## 1. Install dependencies

```powershell
pip install -r requirements.txt
```

Key libraries: `duckdb` (warehouse), `streamlit` + `plotly` (UI), `pandas`,
`pulp` (MILP solver, bundles the CBC solver binary), and optionally `openai`
(only used if you enable the LLM narrative).

## 2. Build the warehouse (one-time, a few seconds)

```powershell
# Optional: if the dataset lives elsewhere
# $env:COFFEE_DATA_DIR = "C:\path\to\coffee_capsule_dataset"

python scripts/init_db.py
```

This runs [sql/01_raw_views.sql](../sql/01_raw_views.sql) (views over the Parquet
files) then [sql/02_build_aggregates.sql](../sql/02_build_aggregates.sql) (heavy
one-time roll-ups) and writes `coffee_bi.duckdb`. The file is a **rebuildable
artifact** — delete and regenerate it any time.

## 3. Launch the dashboard

```powershell
streamlit run app/dashboard.py
```

Explore KPIs, OEE, downtime Pareto, heatmaps, energy, predictive maintenance, a
SQL explorer, and the Agent tab. See [06 — Dashboard](06-Dashboard.md).

## 4. Run the agent

```powershell
# 28-day plan, deterministic diagnosis + narrative
python -m agent.run_agent

# Custom horizon and demand growth
python -m agent.run_agent --horizon 42 --growth 1.10

# Explicit per-product demand, no LLM
python -m agent.run_agent --demand STRONG=4e7,MILD=3e7,DECAF=2.5e7 --no-llm
```

Run the **MILP optimizer** to pick the best plan under constraints:

```powershell
# Maximize demand fulfilment under a €50k energy cap
python -m agent.run_agent --optimize --objective fulfilment --max-energy-cost 50000

# Maximize gross margin, no Sunday overtime allowed
python -m agent.run_agent --optimize --objective margin --no-overtime
```

Outputs land in `agent_output/`:
`efficiency_report.md`, `findings.json`, `production_plan.json`,
`production_schedule.csv/.parquet`, and (with `--optimize`)
`optimizer_scenarios.csv` + `optimizer_result.json`.

See [10 — CLI Reference](10-CLI-Reference.md) for every flag.

## 5. (Optional) Enable the LLM narrative

Set **either** Azure OpenAI or OpenAI credentials in your environment. When
present, the agent adds an executive brief; when absent it uses a deterministic
template. Numeric findings and the plan are identical either way.

```powershell
# Azure OpenAI
$env:AZURE_OPENAI_ENDPOINT   = "https://<resource>.openai.azure.com"
$env:AZURE_OPENAI_API_KEY    = "<key>"
$env:AZURE_OPENAI_DEPLOYMENT = "<deployment-name>"

# or OpenAI
$env:OPENAI_API_KEY = "<key>"
# $env:OPENAI_MODEL = "gpt-4o-mini"   # optional
```

See [09 — Configuration](09-Configuration.md) for all environment variables.
