# 01 — Overview

## The problem

A coffee-capsule plant runs 3 production lines, each a chain of 17 machines
(roasting → grinding → filling → sealing → quality → packaging). Every machine
streams sensor data every minute for a full year. Buried in that data are
millions of euros of avoidable losses: unplanned downtime, slow cycles, rejects,
energy waste, and time lost to product changeovers.

The plant manager needs two things:

1. **Diagnosis** — *Where* are we losing money, *how much*, and *why*?
2. **A plan** — Given demand and capacity, *what* should each line produce, *when*
   should we do maintenance, and *how* do we hit demand at the lowest cost?

This project answers both — first as an interactive BI dashboard, then as an
autonomous agent that produces a written diagnosis and an optimized schedule.

## Key concepts

### OEE (Overall Equipment Effectiveness)
The core manufacturing KPI. It is the product of three factors:

$$\text{OEE} = \text{Availability} \times \text{Performance} \times \text{Quality}$$

- **Availability** = running time ÷ (running + downtime + changeover time). Lost to
  breakdowns and product switches.
- **Performance** = actual output ÷ theoretical output at nominal speed. Lost to
  micro-stops and slow cycles.
- **Quality** = good units ÷ total units. Lost to rejects/scrap.

The whole analysis anchors OEE at the **`doser_filler`** machine on each line —
the station that actually defines how many capsules are produced.

### Capsules and euros
Every inefficiency is quantified twice:
- **Capsules** — the lost production *entitlement* (units you could have made).
- **Euros** — capsules valued at a **gross margin** (`CAPSULE_MARGIN_EUR`), with
  rejects additionally charged the **material/scrap cost** (`MATERIAL_COST...`).

This lets the agent rank findings by real financial impact, not raw counts.

### Predictive maintenance
Machines accumulate a `degradation_index` and vibration; the analytics blend
degradation slope, vibration exceedance and overdue-service days into a
**risk score (0–100)**. High-risk machines are scheduled for preventive
maintenance inside the production plan.

## What "good" looks like

A typical run reports on the order of **€5.5M/yr** of quantified inefficiency
(availability, quality, and changeover losses being the biggest buckets) and
produces a ~28-day plan that meets demand at high utilisation with **zero
changeovers** and preventive-maintenance slots inserted for at-risk machines.

## Two ways to use it

- **Explore** — launch the Streamlit dashboard and browse KPIs, trends, Pareto
  charts, heatmaps and predictive-maintenance rankings interactively.
- **Automate** — run the agent (`python -m agent.run_agent`) to get a written
  executive brief, a ranked findings table, and a machine-readable production
  plan and schedule.

See [02 — Architecture](02-Architecture.md) for how the pieces fit together.
