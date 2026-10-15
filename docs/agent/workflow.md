# Agent Workflow

```mermaid
flowchart TD
    S([Start]) --> I[Read inputs<br/>horizon · demand · growth]
    I --> Q[Call tools<br/>pull metrics from DuckDB]
    Q --> D[Diagnose<br/>OEE losses, downtime, rejects,<br/>changeovers, energy, maintenance risk]
    D --> E[Quantify impact in €]
    E --> P[Plan production<br/>allocate demand across lines & products]
    P --> SC[Build schedule]
    SC --> R[Write report & reasoning trace]
    R --> L{LLM credentials?}
    L -- yes --> N[Add executive narrative]
    L -- no --> O([Done])
    N --> O
```

## Steps

1. **Inputs** — planning horizon (default 28 days), demand per product family or a growth factor.
2. **Tools** — the agent calls tools (`tools.py`) that query the warehouse.
3. **Diagnosis** — analyzers (`analyzers.py`) identify where capacity and money are lost.
4. **Quantification** — each inefficiency is expressed in **€**, so priorities are comparable.
5. **Planning** — the planner (`planner.py`) and optimizer (`optimizer.py`) produce a plan that meets demand.
6. **Reporting** — `report.py` writes the efficiency report, plan, schedule and trace.
7. **Narrative (optional)** — `llm.py` summarises the result for executives.
