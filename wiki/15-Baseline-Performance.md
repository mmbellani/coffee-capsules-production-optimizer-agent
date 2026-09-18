# 16 — Baseline Performance (Before Darwin)

This page records the repo's **original, pristine performance** — the unmodified
baseline that every Darwin experiment (pages [11](11-Darwin-Token-Optimization.md)–[14](14-Darwin-Planner-Fulfilment.md))
started from and measured against. These are the "iteration 0" numbers: the code
as written by hand, before any evolutionary optimization.

## At a glance

| Area | Metric | Baseline (before Darwin) | Optimized (after) | Page |
|------|--------|--------------------------|-------------------|------|
| LLM narration prompt | prompt tokens per run | **6,774 tokens** | 806 (−88.1%) | [11](11-Darwin-Token-Optimization.md) |
| Warehouse build | cold build time (`init_db.py`) | **11.108 s** (mean, n=10) | 3.582 s (3.10×) | [12](12-Darwin-Warehouse-Build-Speedup.md) |
| Scenario optimizer | gross margin (EUR) | **≈ €3.588 M** | ≈ €3.595 M (+0.19%) | [13](13-Darwin-Optimizer-Margin-Gain.md) |
| Production planner | demand fulfilment | **98.24%** | 100.00% (+1.76 pp) | [14](14-Darwin-Planner-Fulfilment.md) |

All four baselines are the *same commit* — the four experiments each branched from
the pristine repo independently.

## 1. LLM narration prompt — 6,774 tokens

The agent's `llm.narrate()` call serialised the **full internal data structures**
into the model prompt: the complete per-line/per-day production `schedule` table,
the per-event `maintenance` table, plan `params` and `rationale`, and every
finding's verbose `title` / `detail` / `recommendation` / `evidence` prose.

- **Prompt size:** 6,774 tokens per run.
- **Root cause:** narration reused the same full-fidelity `as_dict()` views meant
  for reports and the canonical hash, sending the model large fields it never needs
  to cite.

## 2. Warehouse build — 11.108 s

Building `coffee_bi.duckdb` from the 1.4 GB Parquet lake via
[scripts/init_db.py](../scripts/init_db.py).

| | value |
|---|---|
| Mean cold build (n=10, interleaved) | **11.108 s** |
| Std. dev. | 0.070 s |
| Coefficient of variation | 0.63 % |

- **Root cause:** the one-shot bulk load used only 4 threads, kept default WAL /
  checkpoint overhead, made multiple full scans of the 26.8 M-row `raw_sensor`
  view, and left the `agg_machine_hour` HASH_GROUP_BY and `fact_downtime_episode`
  window pass unprofiled — untapped parallelism and I/O slack.
- Note: the *current* code already contains the parallelism improvements; the
  11.1 s figure is the pristine pre-Darwin build used as the measurement baseline.

## 3. Scenario optimizer — ≈ €3.588 M margin

The MILP in [agent/optimizer.py](../agent/optimizer.py) already produced a
**near-optimal, feasible** plan — this is a solved MILP, not a heuristic, so the
baseline was strong by construction.

- **Gross margin:** ≈ €3.588 M.
- **Solver settings:** blanket `UPLIFT_MAX = 15%` bound used everywhere the uplift
  lever `U` appears, and a **1% relative optimality gap** on the scored margin
  solve — leaving a sliver of optimality on the table.
- **Feasibility:** Optimal; output ≤ demand, uplift ≤ 15%, output ≤ capacity.

## 4. Production planner — 98.24% fulfilment

The deterministic planner in [agent/planner.py](../agent/planner.py) met almost
all demand but not quite all of it.

| | value |
|---|---|
| Demand fulfilment | **98.236 %** |
| Changeovers | 0 |
| Feasible | yes |

- **Root cause:** the greedy planner pre-reserved a **blanket weekly rest day
  (Sunday)** as non-production for *every* line — regardless of whether that line
  had maintenance due — then round-robined top-risk machines onto those fixed
  slots independently of the demand plan. Lines with no maintenance due wasted a
  full line-day of capacity (≈ 0.8 M capsules of unmet demand).

## Why these baselines matter

Darwin scores every candidate as a ratio against a freshly-sampled baseline, so
these "before" numbers are the reference for all reported deltas. They also
illustrate the two regimes Darwin operated in:

- **Heuristic baselines with obvious slack** (token serialization, planner
  round-robin, unprofiled build) → large, clean wins.
- **An already-optimal baseline** (the margin MILP) → only a fraction of a percent
  of legitimate headroom, which is exactly what Darwin returned.

See [15 — How Darwin Produced These Results](15-How-Darwin-Produced-These-Results.md)
for the method that turned these baselines into the optimized numbers.
