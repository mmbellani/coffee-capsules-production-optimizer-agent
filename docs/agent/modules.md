# Agent Modules

| Module | Role |
|---|---|
| `agent/agent.py` | Orchestrates the run: tools → analysis → planning → reporting |
| `agent/tools.py` | Tools the agent calls to retrieve metrics from DuckDB |
| `agent/analyzers.py` | Detects inefficiencies and quantifies them in € |
| `agent/planner.py` | Builds the production plan from demand and capacity |
| `agent/optimizer.py` | Optimisation model used by the planner |
| `agent/report.py` | Generates markdown outputs |
| `agent/llm.py` | Optional LLM client for the executive narrative |
| `agent/run_agent.py` | Command-line entry point |

!!! info "Extending the agent"
    To add a new capability: write the SQL in `sql/analytics/`, expose it as a tool in
    `tools.py`, consume it in `analyzers.py`, and surface it in `report.py`.
