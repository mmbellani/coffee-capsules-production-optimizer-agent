# 10 — CLI Reference

The agent's command-line entry point is
[agent/run_agent.py](../agent/run_agent.py), run as a module:

```powershell
python -m agent.run_agent [options]
```

It requires the warehouse to exist first (`python scripts/init_db.py`).

## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--horizon` | int | `28` | Planning horizon in days |
| `--growth` | float | `1.05` | Demand growth factor vs last year |
| `--target-oee` | float | `0.90` | OEE target used in narrative |
| `--maint-risk` | float | `55` | Maintenance risk-score threshold |
| `--demand` | str | — | Override horizon demand, e.g. `STRONG=4e7,MILD=3e7,DECAF=2.5e7` |
| `--out` | str | `agent_output/` | Output directory for artifacts |
| `--no-llm` | flag | off | Force the deterministic narrative (skip LLM) |
| `--optimize` | flag | off | Run the MILP scenario optimizer to select the plan |
| `--objective` | choice | `margin` | `margin` \| `fulfilment` \| `energy_cost` \| `balanced` |
| `--max-energy-cost` | float | — | Constraint: max horizon energy cost (EUR) |
| `--min-fulfilment` | float | — | Constraint: min demand fulfilment (%) |
| `--no-overtime` | flag | off | Disallow Sunday overtime in the optimizer |

## Examples

```powershell
# Default 28-day plan (auto LLM narrative if configured)
python -m agent.run_agent

# 42-day horizon, +10% demand
python -m agent.run_agent --horizon 42 --growth 1.10

# Explicit demand, deterministic narrative only
python -m agent.run_agent --demand STRONG=4e7,MILD=3e7,DECAF=2.5e7 --no-llm

# Maximise fulfilment under a €50k energy cap
python -m agent.run_agent --optimize --objective fulfilment --max-energy-cost 50000

# Maximise margin with no Sunday overtime
python -m agent.run_agent --optimize --objective margin --no-overtime

# Minimise energy cost while meeting a fulfilment floor
python -m agent.run_agent --optimize --objective energy_cost --min-fulfilment 95
```

## What it prints and writes

On completion it prints the full markdown report to stdout and lists the written
artifacts. Files land in the `--out` directory (default `agent_output/`):

- `efficiency_report.md` — executive report
- `findings.json` — diagnosis summary + all findings
- `production_plan.json` — full production plan
- `production_schedule.csv` / `.parquet` — per-line/day schedule
- `optimizer_scenarios.csv` / `optimizer_result.json` — only with `--optimize`

See [07 — The Agent](07-Agent.md) and [08 — MILP Optimizer](08-Optimizer-MILP.md)
for what happens under the hood.
