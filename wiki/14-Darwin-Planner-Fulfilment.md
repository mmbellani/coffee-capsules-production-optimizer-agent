# 14 — Darwin Planner Fulfilment to 100% (Track C)

## Summary

Darwin (an evolutionary coding agent) evolved the deterministic production
planner to lift demand fulfilment from **98.24% to 100.00%** — every capsule of
demand met — while keeping the schedule **feasible** (no overproduction, nothing
on maintenance days, all preventive‑maintenance slots intact) and **changeover‑free**
(0 product changeovers). The combined score reaches **1.0**, the mathematical
ceiling of the objective (fulfilment − changeover penalty).

## The insight

The baseline greedy planner pre‑reserved a **blanket weekly rest day (Sunday) as
non‑production for _every_ line** — regardless of whether that line actually had a
maintenance event due — then round‑robined top‑risk machines onto those fixed
slots independently of the demand plan. That wastes a full line‑day of capacity on
lines with no maintenance due, which is essentially the ~0.8M capsules of unmet
demand.

The evolved planner **folds maintenance‑day placement into the same MILP as
production allocation**: it batches every high‑risk machine on a line into **one
jointly‑optimised line‑down day** chosen by the solver, so a line only loses
capacity when it genuinely needs maintenance — and the freed rest‑day capacity is
redirected to the still‑unmet products. That closes fulfilment to 100%.

## What changed

- **New `agent/milp_allocator.py` (270 lines)** — a MILP that jointly decides
  production allocation and maintenance‑day placement across lines / products /
  days, maximising demand fulfilment subject to per‑line daily capacity, per‑product
  demand caps, and the maintenance requirement. Uses **PuLP** (already a repo
  dependency — no new requirement).
- **`agent/planner.py`** — `build_production_plan()` now calls the MILP allocator
  and maps its solution back into the deterministic `ProductionPlan` (schedule,
  changeovers, maintenance events), replacing the demand‑blind round‑robin rest‑day
  reservation.

## Verification (anti‑cheat)

Capacity and demand are ground truth from the **pristine baseline planner** run in
the same environment; the evaluator re‑derives produced / fulfilment / changeovers
from the candidate's own schedule and checks feasibility against those numbers.
This candidate records:

- `fulfilment_pct = 100.0` (baseline 98.236)
- `feasible = 1.0` — no production beyond a line's daily capacity, none on
  maintenance/idle days, no dropped maintenance slots
- `changeovers = 0`

So the +1.76 pp is real, constraint‑respecting fulfilment — not a relaxed gate.

## Darwin lineage (matcher + refiner island search)

| iter | combined | fulfilment | changeovers | note |
|---:|---:|---:|---:|---|
| 0 | 0.9824 | 98.24% | 0 | baseline greedy planner |
| 4 | 0.9933 | 99.43% | 2 | strong plateau (re‑found many times) |
| 12 | 0.9880 | 100% | 24 | 100% but changeover‑penalised _below_ the plateau |
| **15** | **1.0000** | **100%** | **0** | **MILP maintenance co‑optimisation (this PR)** |

The breakthrough was reaching 100% fulfilment **with zero changeovers** — the top
of the objective. The matcher/refiner ideator plus a "use a real solver" prompt
are what steered the search from greedy tweaks to building an actual MILP.
