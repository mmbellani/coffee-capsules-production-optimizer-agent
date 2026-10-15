# LLM Narrative

The LLM is **optional**. All numbers, diagnoses and plans come from the deterministic
engine; the LLM only writes an **executive narrative** on top.

| Mode | Behaviour |
|---|---|
| No credentials / `--no-llm` | Deterministic outputs only |
| Credentials present | Deterministic outputs **+** executive narrative |

## Why this design

- **Reproducible** — same inputs, same plan.
- **Trustworthy** — the LLM cannot alter computed figures.
- **Runs anywhere** — works offline for demos and testing.

Configure credentials via environment variables (see `agent/llm.py` for the exact names).
