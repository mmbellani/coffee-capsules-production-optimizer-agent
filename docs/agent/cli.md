# CLI Reference

```bash
python -m agent.run_agent [options]
```

## Examples

```bash
# 28-day plan, automatic narrative (if LLM available)
python -m agent.run_agent

# Custom horizon and demand growth
python -m agent.run_agent --horizon 42 --growth 1.10

# Explicit demand per product family, no LLM
python -m agent.run_agent --demand STRONG=4e7,MILD=3e7,DECAF=2.5e7 --no-llm
```

## Options

| Option | Description |
|---|---|
| `--horizon N` | Planning horizon in days (default 28) |
| `--growth F` | Demand growth multiplier, e.g. `1.10` = +10% |
| `--demand K=V,...` | Explicit demand per product family |
| `--no-llm` | Skip the LLM narrative |

Run `python -m agent.run_agent --help` for the full list.
