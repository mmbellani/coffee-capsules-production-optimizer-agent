# Repository Structure

```text
coffee-capsules-production-optimizer-agent/
├── agent/                 # Agentic layer
│   ├── agent.py           # Orchestration
│   ├── analyzers.py       # Inefficiency analysis
│   ├── tools.py           # Tools the agent can call
│   ├── planner.py         # Production planning
│   ├── optimizer.py       # Optimisation model
│   ├── report.py          # Report generation
│   ├── llm.py             # Optional LLM narrative
│   └── run_agent.py       # CLI entry point
├── app/
│   ├── db.py              # DuckDB access layer
│   └── dashboard.py       # Streamlit dashboard
├── data/
├── scripts/
│   └── init_db.py         # Builds the DuckDB warehouse
├── sql/
│   ├── 01_raw_views.sql
│   ├── 02_build_aggregates.sql
│   └── analytics/         # 19 analytical queries
├── docs/                  # This documentation
├── config.py
├── requirements.txt
├── README.md
└── HACKATHON.md
```
