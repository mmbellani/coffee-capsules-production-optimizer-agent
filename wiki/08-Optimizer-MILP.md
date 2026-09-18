# 08 — MILP Optimizer

The optimization lives in two files, both built on **PuLP** with the bundled
**CBC** solver:

- [agent/milp_allocator.py](../agent/milp_allocator.py) — the allocation solver
  the **planner** always uses.
- [agent/optimizer.py](../agent/optimizer.py) — the richer **scenario optimizer**
  used when you pass `--optimize`.

## Allocation solver — `solve_allocation()`

Used by [agent/planner.py](../agent/planner.py) to decide, for a fixed set of
lines, products and production days, how many capsules of which product each line
makes each day.

**Decision variables** (indices `l`=line, `p`=product, `k`=day):

| Variable | Type | Meaning |
|----------|------|---------|
| `x[l,p,k]` | ≥ 0 | capsules of product `p` on line `l`, day `k` |
| `y[l,p,k]` | binary | campaign indicator (line runs `p` that day) |
| `chg[l,k]` | ≥ 0 | changeover entering day `k` |
| `m[l,k]` | binary | maintenance on line `l`, day `k` (only if line has due machines) |

**Constraints:**
- Produce **or** do maintenance, not both: `Σ_p y[l,p,k] + m[l,k] ≤ 1`.
- Link production to campaign: `x[l,p,k] ≤ capacity[l] · y[l,p,k]`.
- Never exceed demand: `Σ x[l,p,k] ≤ demand[p]`.
- Count switches: `chg[l,k] ≥ y[l,p,k] − y[l,p,k−1]`.
- Each line takes exactly its required maintenance day(s): `Σ_k m[l,k] = maint_required[l]`.

**Objective** (lexicographic via tiny epsilons):

$$\max \; \sum x \;-\; \varepsilon_{chg}\sum chg \;-\; \varepsilon_{maint}\sum k\cdot m$$

So the solver **first** maximises fulfilled demand, **then** (as a tie-break)
minimises changeovers, **then** prefers earlier maintenance. The epsilons are far
smaller than a single line-day's capacity, so ties are broken without ever
trading away a real capsule of production.

Crucially, maintenance timing is a **joint decision** — the solver puts each
line's maintenance day where it costs the least fulfilment, rather than a
demand-blind round-robin slot. (A `naive_round_robin_maintenance_days()` helper
and a `solve_allocation_fixed_maintenance()` variant exist purely for
comparison/testing to quantify how much the joint placement recovers.)

## Scenario optimizer — `optimize(spec, tb)`

Used by the agent when you pass `--optimize`. A richer MILP over the horizon that
adds real business levers:

| Variable | Meaning |
|----------|---------|
| `x[l,p,d]` | capsules produced |
| `y[l,p,d]` | campaign assignment (≤ 1 product per line-day) |
| `otd[l,d]` | Sunday **overtime** used (binary) |
| `U` | plant **OEE-uplift investment** (continuous, capex per point) |
| `opx[l,p,d]` | **off-peak** production (cheaper night tariff, capacity-limited) |

The `U · otd` product on Sundays is linearised exactly with **McCormick
envelopes** (auxiliary variable `w`). The uplift domain is data-tightened: `U`
only pays off if baseline capacity (including full Sunday overtime) can't already
cover demand, so its upper bound is shrunk to the actual headroom needed plus a
small safety buffer — this tightens the LP relaxation without excluding any
optimal solution.

**Constraints:** per-line daily capacity (with uplift), one product per line-day,
demand caps, off-peak window capacity, and optional **energy-cost cap** and
**min-fulfilment floor**.

**Objectives** (`--objective`):

| Objective | Optimises |
|-----------|-----------|
| `margin` | gross margin = revenue − energy − overtime − uplift capex − changeover − scrap |
| `fulfilment` | total capsules produced |
| `energy_cost` | minimise energy cost (with a fulfilment floor) |
| `balanced` | margin plus a small fulfilment bonus |

### The Pareto frontier

To show the fulfilment-vs-energy trade-off, the optimizer uses the
**ε-constraint** method: it finds the fulfilment-max and energy-min endpoints,
then repeatedly re-solves the fulfilment objective under tightening energy caps
(`np.linspace` between the endpoints). The non-dominated subset (`_pareto()`) is
the frontier shown as a scatter + table in the dashboard's Agent tab.

**Budget split:** the scored metric (`gross_margin_eur`) comes *only* from the
one primary solve of the requested objective, which gets the bulk of the time
budget and a tight 0.05% optimality gap. The auxiliary/frontier solves are purely
informational, so they run with a short time limit and a looser 3% gap.

## Determinism

Both solvers are made bit-for-bit reproducible: sorted iteration order over all
lines/products/days before creating any variable, CBC pinned to a single thread,
a fixed CBC random seed, a tight relative gap, and no wall-clock or unseeded
randomness anywhere. Same inputs → same schedule, every run.

## Output

`optimize()` returns a `ScenarioResult` containing the best metrics, the winning
`ProductionPlan` (which the agent adopts), the full scenario table, the
non-dominated Pareto subset, and the per-cell `x[l,p,d]` solution detail. These
are written to `optimizer_scenarios.csv` and `optimizer_result.json`.

Next: [09 — Configuration](09-Configuration.md).
