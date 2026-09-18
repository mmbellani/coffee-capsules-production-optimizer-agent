# 09 — Configuration

All configuration lives in [config.py](../config.py). Every value can be
overridden with an environment variable, so you never have to edit the file.

## Paths

| Setting | Env var | Default | Purpose |
|---------|---------|---------|---------|
| `DATA_DIR` | `COFFEE_DATA_DIR` | `../coffee_capsule_dataset` | The Parquet data lake |
| `DB_PATH` | `COFFEE_DB` | `coffee_bi.duckdb` | The DuckDB warehouse |

Derived Parquet paths (`TS_GLOB`, `META_PARQUET`, `PRODUCT_PARQUET`,
`SCHEDULE_PARQUET`) are computed from `DATA_DIR` and exposed to SQL as
`{TOKEN}` placeholders via `SQL_SUBSTITUTIONS`.

## Business assumptions

| Setting | Env var | Default | Purpose |
|---------|---------|---------|---------|
| `ENERGY_PRICE_EUR_PER_KWH` | `ENERGY_PRICE` | `0.24` | Peak electricity price |
| `MATERIAL_COST_EUR_PER_CAPSULE` | `CAPSULE_COST` | `0.045` | Scrap/material cost per rejected capsule |
| `CAPSULE_MARGIN_EUR` | `CAPSULE_MARGIN` | `0.08` | Gross margin per good capsule — used to value losses |
| `VIBRATION_ALARM_MM_S` | `VIB_ALARM` | `4.5` | ISO 10816-style vibration alarm threshold |

These drive how inefficiencies are converted to euros and how vibration
exceedances are flagged.

## Agent / planner parameters

| Setting | Env var | Default | Purpose |
|---------|---------|---------|---------|
| `PLAN_HORIZON_DAYS` | `PLAN_HORIZON_DAYS` | `28` | Planning horizon |
| `DEMAND_GROWTH` | `DEMAND_GROWTH` | `1.05` | Demand vs last year (+5%) |
| `TARGET_OEE` | `TARGET_OEE` | `0.90` | OEE target referenced in narratives |
| `MAINTENANCE_RISK_THRESHOLD` | `MAINT_RISK_THRESHOLD` | `55` | Risk score above which a machine gets scheduled maintenance |

## Scenario-optimizer parameters

| Setting | Env var | Default | Purpose |
|---------|---------|---------|---------|
| `ENERGY_OFFPEAK_PRICE` | `ENERGY_OFFPEAK_PRICE` | `0.15` | Cheaper night tariff for off-peak production |
| `OVERTIME_COST_PER_LINE_DAY` | `OVERTIME_COST_PER_LINE_DAY` | `9000` | Cost of a Sunday overtime line-day |
| `CAPACITY_UPLIFT_COST_PER_POINT` | `UPLIFT_COST_PER_POINT` | `60000` | Capex per OEE-uplift point |

## LLM credentials (optional)

Set **either** provider; if neither is present the agent runs fully
deterministically (see [llm.py](../agent/llm.py)).

**Azure OpenAI:**
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_API_VERSION` (optional, defaults to `2024-08-01-preview`)

**OpenAI:**
- `OPENAI_API_KEY`
- `OPENAI_MODEL` (optional, defaults to `gpt-4o-mini`)

## Build-time flags

| Env var | Purpose |
|---------|---------|
| `COFFEE_PROFILE_SQL=1` | Print a per-statement timing breakdown during `init_db.py` |

## Example (PowerShell)

```powershell
$env:COFFEE_DATA_DIR = "D:\data\coffee_capsule_dataset"
$env:ENERGY_PRICE    = "0.28"
$env:PLAN_HORIZON_DAYS = "42"
python scripts/init_db.py
python -m agent.run_agent --optimize --objective margin
```

Next: [10 — CLI Reference](10-CLI-Reference.md).
