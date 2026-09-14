"""Deterministic MILP for the line/product/day production allocation used by
``agent.planner.build_production_plan``.

Given a fixed set of lines, products, production days, per-line daily
capacity and per-product horizon demand, decide how many capsules of which
product each line should run on each production day so that:

  1. total demand fulfilment (capped at demand per product) is maximised,
  2. subject to (1), the number of product changeovers per line is minimised,
     and
  3. subject to (1)+(2), each line's mandatory preventive-maintenance day(s)
     are placed on the line-day that costs the least fulfilment.

Formulation (indices l in lines, p in products, k in 0..len(days)-1):

  x[l,p,k] >= 0        capsules of product p made on line l on day k
  y[l,p,k] in {0,1}    campaign indicator: line l runs product p on day k
  chg[l,k] >= 0        changeover indicator entering day k (k >= 1)
  m[l,k] in {0,1}      maintenance indicator: line l is under PM on day k

  sum_p y[l,p,k] + m[l,k] <= 1                 (produce OR do maintenance, not both)
  x[l,p,k] <= capacity[l] * y[l,p,k]           (link production to campaign)
  sum_{l,k} x[l,p,k] <= demand[p]              (never exceed product demand)
  chg[l,k] >= y[l,p,k] - y[l,p,k-1]  for all p (count a switch on any product)
  sum_k m[l,k] == maint_required[l]            (line must take its PM day(s))

  maximise  sum(x) - EPS_CHG * sum(chg) - EPS_MAINT * sum(k * m[l,k])

Maintenance is a *joint* decision variable rather than a pre-reserved,
demand-blind slot: the solver is free to put each line's mandatory PM day(s)
wherever they cost the least fulfilment (e.g. a day where that line's
products are already satisfied elsewhere), while every other calendar day
remains available for production on every line (no artificial blanket
"weekend" that idles lines regardless of whether they actually need
maintenance that day -- see agent.planner for the round-robin baseline this
replaces). EPS_CHG and EPS_MAINT are both far smaller than a single
line-day's capacity so the solver never trades fulfilled demand for fewer
changeovers or "nicer" maintenance timing -- those are only used to break
ties between otherwise-equal-fulfilment solutions (e.g. picking which line
absorbs a mid-horizon product switch, or preferring earlier maintenance when
several days are equally free).

Determinism
-----------
MILP solvers such as CBC can return different (equally optimal) vertices
across runs if variable/constraint order is not fixed or if the search is
multi-threaded. To keep the schedule bit-for-bit reproducible for the same
inputs we:
  * always iterate lines/products/days in explicitly sorted order before
    creating any LP variable or constraint (never rely on dict/set iteration
    order, which is insertion-order-dependent and easy to accidentally
    perturb),
  * pin the CBC thread count to 1 (`threads=1`) so branch-and-bound is not
    subject to multi-threaded race/interleaving effects,
  * pass a fixed CBC random seed (`randomCbcSeed`) so any internal
    tie-breaking/perturbation heuristics behave identically run-to-run,
  * solve with `gapRel=0` (prove true optimality rather than stopping early
    on a heuristic incumbent, which could vary by machine speed/timing), and
  * never use wall-clock time or unseeded randomness anywhere in the model.
"""
from __future__ import annotations

from datetime import date

import pulp

# Deliberately tiny relative to a line-day's capacity (hundreds of thousands
# of capsules) so changeovers/maintenance timing are only tie-breakers, never
# traded against fulfilled demand.
CHANGEOVER_EPS = 1.0
# An order of magnitude smaller than CHANGEOVER_EPS so, among solutions that
# already tie on fulfilment and changeovers, the solver prefers scheduling
# maintenance sooner rather than later -- purely cosmetic determinism, never
# large enough to move a single capsule of production.
MAINT_DAY_EPS = 0.05
SOLVER_TIME_LIMIT = 20
CBC_GAP_REL = 0.0005
CBC_RANDOM_SEED = 1


def solve_allocation(lines: list[str], products: list[str], days: list[date],
                      capacity: dict[str, float], demand: dict[str, float],
                      maint_required: dict[str, int] | None = None):
    """Solve the line/product/day allocation MILP, jointly with placement of
    each line's mandatory preventive-maintenance day(s).

    ``maint_required`` maps line_id -> number of maintenance days that line
    must take somewhere in the horizon (0 if the line has no due machines).
    The solver chooses which day(s) to use for each line so as to minimise
    the fulfilment lost to maintenance, instead of a demand-blind
    round-robin placement.

    Returns (alloc, changeovers, maint_days, note) where alloc maps
    (line_id, iso_date) -> (product, capsules) for every line-day that is
    assigned production, changeovers is the solver's realised changeover
    count, maint_days maps line_id -> list of iso-date strings chosen for
    that line's maintenance, and note is a short human-readable rationale
    string.
    """
    # Explicit, sorted iteration order everywhere below -- never rely on
    # dict/set insertion order for anything that touches the model.
    L = sorted(lines)
    P = sorted(products)
    D = sorted(range(len(days)), key=lambda k: days[k].isoformat())
    n_days = len(D)
    maint_required = {l: int(maint_required.get(l, 0)) if maint_required else 0
                       for l in L}

    if not L or not P or n_days == 0:
        return {}, 0, {}, "MILP allocator: nothing to schedule (no lines/products/days)."

    prob = pulp.LpProblem("line_product_day_allocation", pulp.LpMaximize)

    x = {(l, p, k): pulp.LpVariable(f"x_{l}_{p}_{k}", lowBound=0)
         for l in L for p in P for k in D}
    y = {(l, p, k): pulp.LpVariable(f"y_{l}_{p}_{k}", cat="Binary")
         for l in L for p in P for k in D}
    chg = {(l, k): pulp.LpVariable(f"chg_{l}_{k}", lowBound=0)
           for l in L for k in D[1:]}
    # Maintenance indicator only needs to exist (and only costs binary
    # variables) for lines that actually have a maintenance requirement.
    m = {(l, k): pulp.LpVariable(f"m_{l}_{k}", cat="Binary")
         for l in L for k in D if maint_required[l] > 0}

    for l in L:
        for k in D:
            campaign = pulp.lpSum(y[(l, p, k)] for p in P)
            if maint_required[l] > 0:
                prob += campaign + m[(l, k)] <= 1   # produce OR do maintenance
            else:
                prob += campaign <= 1
            for p in P:
                prob += x[(l, p, k)] <= capacity[l] * y[(l, p, k)]
        for k in D[1:]:
            for p in P:
                prob += chg[(l, k)] >= y[(l, p, k)] - y[(l, p, k - 1)]
        if maint_required[l] > 0:
            prob += pulp.lpSum(m[(l, k)] for k in D) == maint_required[l]

    for p in P:
        prob += pulp.lpSum(x[(l, p, k)] for l in L for k in D) <= demand[p]

    total_produced = pulp.lpSum(x[(l, p, k)] for l in L for p in P for k in D)
    total_changeovers = pulp.lpSum(chg[(l, k)] for l in L for k in D[1:])
    total_maint_day_index = pulp.lpSum(k * m[(l, k)] for (l, k) in m)
    prob += (total_produced - CHANGEOVER_EPS * total_changeovers
             - MAINT_DAY_EPS * total_maint_day_index)

    solver = pulp.PULP_CBC_CMD(
        msg=0, threads=1, timeLimit=SOLVER_TIME_LIMIT, gapRel=CBC_GAP_REL,
        options=["randomCbcSeed", str(CBC_RANDOM_SEED),
                 "randomSeed", str(CBC_RANDOM_SEED)],
    )
    prob.solve(solver)
    status = pulp.LpStatus[prob.status]

    alloc: dict[tuple[str, str], tuple[str, float]] = {}
    maint_days: dict[str, list[str]] = {l: [] for l in L}
    realised_changeovers = 0
    for l in L:
        for k in D:
            if maint_required[l] > 0 and (m[(l, k)].value() or 0) > 0.5:
                maint_days[l].append(days[k].isoformat())
                continue
            best_p, best_q = None, 0.0
            for p in P:
                q = x[(l, p, k)].value() or 0.0
                if q > best_q:
                    best_p, best_q = p, q
            if best_p is not None and best_q > 1e-6:
                alloc[(l, days[k].isoformat())] = (best_p, round(best_q))
        seq = [alloc[(l, days[k].isoformat())][0] for k in D
               if (l, days[k].isoformat()) in alloc]
        realised_changeovers += sum(1 for a, b in zip(seq, seq[1:]) if a != b)

    planned = sum(q for _, q in alloc.values())
    total_demand = sum(demand.values())
    n_maint_days = sum(len(v) for v in maint_days.values())
    note = (f"MILP allocator (PuLP/CBC, single-threaded, seed={CBC_RANDOM_SEED}) — "
            f"status={status}, planned {planned:,.0f} of {total_demand:,.0f} capsules "
            f"demand ({100 * planned / total_demand:.1f}% fulfilment) with "
            f"{realised_changeovers} changeovers across {len(L)} lines x {n_days} "
            f"calendar days, jointly placing {n_maint_days} maintenance day(s) on the "
            "line-day combinations that cost the least fulfilment.")
    return alloc, realised_changeovers, maint_days, note


def naive_round_robin_maintenance_days(lines: list[str], days: list[date],
                                        maint_required: dict[str, int]) -> dict[str, list[str]]:
    """Reference/comparison-only placement: the demand-blind round-robin
    strategy the previous planner used (cycle maintenance across a fixed
    slot list irrespective of the production plan). Used solely to quantify,
    in evaluation/tests, how much the joint MILP placement in
    ``solve_allocation`` recovers versus a naive scheduler -- NOT used by
    ``agent.planner.build_production_plan`` itself.
    """
    L = sorted(lines)
    n_days = len(days)
    slots = [days[i].isoformat() for i in range(0, n_days, max(1, n_days // 4 or 1))] or \
            [days[0].isoformat()]
    out: dict[str, list[str]] = {l: [] for l in L}
    counters: dict[str, int] = {l: 0 for l in L}
    for l in L:
        need = int(maint_required.get(l, 0))
        for _ in range(need):
            slot = slots[counters[l] % len(slots)]
            out[l].append(slot)
            counters[l] += 1
    return out


def solve_allocation_fixed_maintenance(lines: list[str], products: list[str],
                                        days: list[date], capacity: dict[str, float],
                                        demand: dict[str, float],
                                        maint_days_fixed: dict[str, list[str]]):
    """Same production MILP as ``solve_allocation`` but with maintenance
    day(s) pinned in advance (e.g. by ``naive_round_robin_maintenance_days``)
    instead of jointly optimised. Comparison-only helper for measuring the
    value of joint placement; not used by the production planner.
    """
    L = sorted(lines)
    P = sorted(products)
    D = sorted(range(len(days)), key=lambda k: days[k].isoformat())
    blocked = {(l, days[k].isoformat()) for l in L for k in D
               if days[k].isoformat() in maint_days_fixed.get(l, [])}

    prob = pulp.LpProblem("line_product_day_allocation_fixed_maint", pulp.LpMaximize)
    x = {(l, p, k): pulp.LpVariable(f"x_{l}_{p}_{k}", lowBound=0)
         for l in L for p in P for k in D}
    y = {(l, p, k): pulp.LpVariable(f"y_{l}_{p}_{k}", cat="Binary")
         for l in L for p in P for k in D}
    chg = {(l, k): pulp.LpVariable(f"chg_{l}_{k}", lowBound=0)
           for l in L for k in D[1:]}

    for l in L:
        for k in D:
            is_blocked = (l, days[k].isoformat()) in blocked
            prob += pulp.lpSum(y[(l, p, k)] for p in P) <= (0 if is_blocked else 1)
            for p in P:
                prob += x[(l, p, k)] <= capacity[l] * y[(l, p, k)]
        for k in D[1:]:
            for p in P:
                prob += chg[(l, k)] >= y[(l, p, k)] - y[(l, p, k - 1)]

    for p in P:
        prob += pulp.lpSum(x[(l, p, k)] for l in L for k in D) <= demand[p]

    total_produced = pulp.lpSum(x[(l, p, k)] for l in L for p in P for k in D)
    total_changeovers = pulp.lpSum(chg[(l, k)] for l in L for k in D[1:])
    prob += total_produced - CHANGEOVER_EPS * total_changeovers

    solver = pulp.PULP_CBC_CMD(
        msg=0, threads=1, timeLimit=SOLVER_TIME_LIMIT, gapRel=CBC_GAP_REL,
        options=["randomCbcSeed", str(CBC_RANDOM_SEED),
                 "randomSeed", str(CBC_RANDOM_SEED)],
    )
    prob.solve(solver)

    alloc: dict[tuple[str, str], tuple[str, float]] = {}
    for l in L:
        for k in D:
            best_p, best_q = None, 0.0
            for p in P:
                q = x[(l, p, k)].value() or 0.0
                if q > best_q:
                    best_p, best_q = p, q
            if best_p is not None and best_q > 1e-6:
                alloc[(l, days[k].isoformat())] = (best_p, round(best_q))
    planned = sum(q for _, q in alloc.values())
    return alloc, planned
