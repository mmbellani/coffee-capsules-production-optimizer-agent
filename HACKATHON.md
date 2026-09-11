# Evolve the Stack - Using Darwin to Evolve a Coffee-Capsule Analytics Agent for Speed and Token Efficiency

## Summary

This project applies **Darwin's** automated, evolutionary code-optimization to a real
end-to-end industrial analytics application — a coffee-capsule manufacturing Business
Insight platform that combines a **DuckDB** warehouse of ~27M sensor rows, a library of
**19 complex analytical SQL** queries, and an **agentic layer** that diagnoses production
inefficiencies and generates optimized plans via a **MILP** solver. We want to test
whether Darwin can autonomously improve two distinct, high-value dimensions of the
codebase **without changing behavior**.

First, **SQL latency**: Darwin will iteratively rewrite and tune the warehouse's
analytical queries and aggregate-build statements (join order, predicate pushdown,
window-function structure, materialization strategy) and keep the variants that minimize
execution time, validated against the existing result sets so correctness is preserved.

Second, **agent prompt token usage**: Darwin will evolve the prompts that drive the agent
— the diagnosis, planning, and narrative-generation instructions — compressing and
restructuring them to cut input/output token consumption (and therefore cost and latency)
while holding output quality constant.

Success is measured by a clear fitness function: reduced p50/p95 query latency and lower
tokens-per-run, with automated regression checks guaranteeing that optimized queries
return identical data and the agent produces equivalent findings and plans. The goal is a
demonstrable, benchmarked before/after showing that evolutionary optimization can make an
already-working data-and-AI product materially faster and cheaper to operate.

---

## Concrete Darwin targets & metrics

### Track A — SQL latency optimization
**Targets (files Darwin may mutate):**
- `sql/analytics/*.sql` — the 19 analytical queries (OEE, downtime Pareto, MTBF/MTTR,
  rolling z-score anomalies, predictive-maintenance risk, bottleneck, correlation, …).
- `sql/02_build_aggregates.sql` — the heavy roll-ups and gaps-and-islands fact builds
  (`agg_machine_hour/day`, `agg_line_product_day`, `fact_downtime_episode`,
  `fact_changeover_episode`).
- `sql/01_raw_views.sql` — projection pruning / column selection over the Parquet lake.
- Physical-design knobs: aggregate grain, indexes/sort keys, `PRAGMA threads`,
  partitioning of the `timeseries/*.parquet` scan.

**Mutation ideas Darwin can explore:**
- Join reordering and predicate pushdown; replacing correlated subqueries with window
  functions; narrowing `SELECT` projections; pre-aggregation vs. on-the-fly.
- Window-frame tuning (`ROWS` vs `RANGE`, partition/order minimization).
- Materializing shared CTEs; converting views to tables where it pays off.

**Metrics (fitness = lower is better, subject to correctness):**
- p50 / p95 / max **query execution time** per query (warm and cold cache).
- **Warehouse build time** for `init_db.py` (end-to-end and per statement).
- **Rows scanned / bytes read** and peak memory (from DuckDB `EXPLAIN ANALYZE`).
- **Total dashboard cold-load latency** (sum of first-paint queries).
- **Correctness gate (hard constraint):** optimized query output must be *row-for-row
  identical* (order-insensitive hash) to the baseline result set.

### Track B — Agent prompt token optimization
**Targets (prompts Darwin may mutate):**
- `agent/llm.py` — the `narrate()` **system prompt** and the JSON payload shaping sent
  to the model.
- `agent/agent.py` — the diagnosis/plan payload assembly (`diag_payload`, findings slice
  count) and the deterministic `_template_narrative` (as a token-free fallback baseline).
- `agent/tools.py` — `TOOL_SPECS` descriptions used for LLM function-calling.
- `agent/analyzers.py` / `agent/planner.py` — the `detail`/`recommendation`/`rationale`
  strings that get serialized into the model context.

**Mutation ideas Darwin can explore:**
- Prompt compression and re-templating; trimming redundant instructions; schema-guided
  JSON minification; truncating/summarizing findings before they enter context.
- Reducing the number of findings/rows embedded; switching verbose fields to codes.

**Metrics (fitness = lower is better, subject to quality):**
- **Input tokens**, **output tokens**, **total tokens** per agent run.
- **Estimated $ cost per run** and end-to-end **agent latency**.
- **Prompt character/byte size** of each system/user message.
- **Quality gate (hard constraint):** optimized prompts must produce an executive brief
  and plan that are *semantically equivalent* to baseline — validated by (a) an
  LLM-as-judge rubric score ≥ baseline, and (b) unchanged **structured** outputs
  (findings IDs, €-impact totals, plan schedule, changeovers) from the deterministic
  engine, which stays the source of truth.

### Global success criteria
- **Track A:** ≥ 30% reduction in aggregate p95 query latency **and** ≥ 20% faster
  warehouse build, with **0** correctness regressions.
- **Track B:** ≥ 25% reduction in total tokens-per-run with LLM-judge quality ≥ baseline
  and identical structured findings/plan.
- **Reproducibility:** every Darwin-accepted change is committed with a before/after
  benchmark row and passes the automated regression suite.

---

## Baseline harness (what to benchmark against)
- **SQL:** loop `sql/analytics/*.sql` via `app/db.py`, time each with DuckDB
  `EXPLAIN ANALYZE`; record latency + rows scanned; hash results for the correctness gate.
- **Agent:** run `python -m agent.run_agent --optimize` and capture token counts
  (when an LLM is configured), latency, and the structured `findings.json` /
  `production_plan.json` for the equivalence gate.
- **Report:** emit a `benchmarks/before_after.csv` that Darwin appends to on every
  accepted mutation.
