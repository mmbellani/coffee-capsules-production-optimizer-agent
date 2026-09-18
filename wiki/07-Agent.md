# 07 — The Agent

The `agent/` package is a **tool-using agent** that analyzes the sensor data,
quantifies inefficiencies in euros, and generates a production plan. It runs
fully offline on a deterministic engine; if LLM credentials are present it adds an
executive narrative on top (the numbers never change).

## Module map

| File | Role |
|------|------|
| [tools.py](../agent/tools.py) | `Toolbox` — read-only, safe access to the warehouse |
| [analyzers.py](../agent/analyzers.py) | `diagnose()` — turns data into ranked, euro-quantified `Finding`s |
| [planner.py](../agent/planner.py) | `build_production_plan()` — capacity/demand-grounded schedule |
| [milp_allocator.py](../agent/milp_allocator.py) | MILP that assigns product × line × day and places maintenance |
| [optimizer.py](../agent/optimizer.py) | Full scenario MILP with objectives, constraints and Pareto frontier |
| [agent.py](../agent/agent.py) | `EfficiencyAgent` — orchestrates plan → act → observe |
| [llm.py](../agent/llm.py) | Optional Azure OpenAI / OpenAI narrative |
| [report.py](../agent/report.py) | Renders markdown / JSON / parquet artifacts |
| [run_agent.py](../agent/run_agent.py) | CLI entry point |

## 1. Toolbox — [tools.py](../agent/tools.py)

A thin, **safe** facade over the warehouse. Every method returns plain
pandas/Python objects so both the deterministic engine and an LLM (via
function-calling) can use them.

- `list_named_queries()` / `run_named_query(id)` — the 19 analytics queries.
- `run_sql(sql)` — ad-hoc SQL, but **rejects** anything that isn't a read-only
  SELECT (blocks `insert/update/delete/drop/create/alter/attach`).
- `machines()` — machine master data.
- Derived analytics used by the planner/analyzers:
  - `line_efficiency()` — the OEE loss **waterfall** per line at the filler
    (entitlement vs actual, split into availability/performance/quality losses).
  - `line_daily_capacity()` — observed median / p90 / max capsules per day per line.
  - `product_demand_baseline()` — last-year output split by product.
  - `maintenance_candidates(threshold)` — machines above a risk score.
- `TOOL_SPECS` — JSON-schema definitions exposing these tools for LLM
  function-calling.

## 2. Diagnosis — [analyzers.py](../agent/analyzers.py)

`diagnose()` produces a ranked list of `Finding` objects. A `Finding` records its
area, severity (HIGH/MEDIUM/LOW by euro impact), scope, a human title/detail, the
impact in **capsules** and **euros**, a recommendation, and supporting evidence.

It examines six areas:

1. **OEE loss waterfall** per line — availability, performance and quality losses.
2. **Downtime Pareto** — the top unplanned-stop machines.
3. **Bottleneck stations** — the most frequent line constraints.
4. **Energy intensity outliers** — the most energy-hungry product.
5. **Predictive maintenance** — high-risk machines.
6. **Changeover waste** — hours lost to product switching per line.

Findings are sorted by euro impact. `summarise()` rolls them up into totals,
impact-by-area, and a high-severity count.

Severity thresholds: HIGH ≥ €150k, MEDIUM ≥ €40k, else LOW.

## 3. Planner — [planner.py](../agent/planner.py)

`build_production_plan()` builds a horizon schedule grounded entirely in observed
data:

1. **Clock** — plan starts the day after the dataset's last day.
2. **Capacity** — per-line capsules/day from the observed median of real
   production days (optionally scaled by an OEE `capacity_uplift`).
3. **Demand** — either a user override, or last-year output × growth × horizon
   fraction.
4. **Maintenance** — every high-risk machine on a line is batched into a single
   mandatory "line-down" day; *where* that day falls is decided jointly with
   production (not a demand-blind rotating slot).
5. **Allocation** — hands lines, products, days, capacity, demand and the
   maintenance requirement to `solve_allocation()` (see
   [08 — MILP Optimizer](08-Optimizer-MILP.md)), which returns the product each
   line runs each day, the changeover count, and the chosen maintenance days.
6. **Summary** — planned capsules, per-product fulfilment %, unmet capsules,
   utilisation, changeovers, maintenance slots, plus a plain-English `rationale`
   list explaining every decision.

The result is a `ProductionPlan` dataclass with the schedule and maintenance as
DataFrames, serialisable via `as_dict()`.

## 4. Orchestrator — [agent.py](../agent/agent.py)

`EfficiencyAgent.run()` executes an explicit **plan → act → observe** loop and
records a `trace` of every step:

1. **Sense** — inspect the warehouse & analytics catalog.
2. **Diagnose** — run `analyzers.diagnose()` and summarise.
3. **Optimize or plan** — if an `OptimizerSpec` is given, run the MILP scenario
   optimizer and adopt its winning plan; otherwise build the deterministic plan.
4. **Narrate** — call the LLM if available, else fall back to
   `_template_narrative()` (a fully deterministic executive brief).

It returns an `AgentReport` (diagnosis, findings, plan, narrative, trace, whether
the LLM was used, and any optimization result).

## 5. LLM layer — [llm.py](../agent/llm.py)

Optional and side-effect-free when unconfigured. `available()` checks for Azure
OpenAI or OpenAI credentials; `narrate()` sends a compact JSON of the diagnosis +
plan and asks for a ~250-word executive brief ending in 3 prioritised actions.
To save tokens, the payload uses **compact** views (`as_narration_dict()`) that
keep only the fields needed to cite/prioritise and drop prose already captured by
the deterministic engine.

## 6. Reporting — [report.py](../agent/report.py)

`render_markdown()` produces the executive report (summary, quantified
inefficiencies table, production plan, rationale, maintenance, a 14-day schedule
pivot, optional optimizer section, and the agent trace). `save()` writes all
artifacts to `agent_output/`:

- `efficiency_report.md` — the human-readable report
- `findings.json` — diagnosis summary + all findings
- `production_plan.json` — full plan
- `production_schedule.csv` / `.parquet` — the per-line/day schedule
- `optimizer_scenarios.csv` / `optimizer_result.json` — when `--optimize` is used

Next: [08 — MILP Optimizer](08-Optimizer-MILP.md).
