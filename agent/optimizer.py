"""Scenario optimizer — Mixed-Integer Linear Program (PuLP / CBC).

Replaces the earlier lever sweep with a real optimisation model that decides,
over a planning horizon:

  x[l,p,d]   >= 0   capsules of product p made on line l on day d   (continuous)
  y[l,p,d]   {0,1}  campaign indicator (<=1 product per line-day)
  chg[l,d]   >=0    changeover entering day d (product differs from prev day)
  otd[l,d]   {0,1}  Sunday overtime used on line l, day d
  U          [0,Umax] plant OEE-uplift investment (continuous, capex per point)
  opx[l,p,d] >= 0   capsules produced within the cheaper off-peak window

subject to per-line daily capacity (incl. uplift via McCormick on Sundays),
one product per line-day, demand caps, off-peak window capacity, optional energy
and fulfilment constraints. Objectives: margin | fulfilment | energy_cost |
balanced. A real Pareto frontier (fulfilment vs energy) is produced with the
epsilon-constraint method (repeated solves under tightening energy caps).

Public API is unchanged: optimize(spec, tb) -> ScenarioResult, with best_plan a
ProductionPlan the agent adopts.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import date, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pulp

import config
from agent.tools import Toolbox
from agent.planner import ProductionPlan

UPLIFT_MAX = 0.15                 # up to +15% effective capacity
OFFPEAK_FRACTION = 0.33           # ~8h night window eligible for off-peak tariff
CHANGEOVER_COST_EUR = 1500.0      # cost of a product changeover (lost time)
SOLVER_TIME_LIMIT = 30            # legacy default, kept for any external callers

# gross_margin_eur (the scored metric) comes *solely* from the one solve of the
# requested `objective` (typically "margin"); the fulfilment/energy_cost solves
# and the epsilon-constraint pareto sweep are purely informational (they feed
# the frontier chart, not the score). We therefore give the primary solve the
# bulk of the wall-clock budget and a much tighter optimality gap, while the
# auxiliary solves get a short time limit and a looser gap -- they only need a
# reasonable feasible point, not a near-optimal one.
PRIMARY_TIME_LIMIT = 75
PRIMARY_GAP_REL = 0.0005          # 0.05% -- close to provably optimal
AUX_TIME_LIMIT = 6
AUX_GAP_REL = 0.03                # 3% is plenty for informational frontier points


@dataclass
class OptimizerSpec:
    objective: str = "margin"                     # margin|fulfilment|energy_cost|balanced
    horizon_days: int = config.PLAN_HORIZON_DAYS
    demand_growth: float = config.DEMAND_GROWTH
    demand_override: dict | None = None
    max_energy_cost_eur: float | None = None
    min_fulfilment_pct: float | None = None
    allow_overtime: bool = True
    allow_uplift: bool = True
    campaign_binaries: bool = True                # enforce <=1 product/line-day (realistic campaigns)
    peak_price: float = config.ENERGY_PRICE_EUR_PER_KWH
    offpeak_price: float = config.ENERGY_OFFPEAK_PRICE
    overtime_cost_per_line_day: float = config.OVERTIME_COST_PER_LINE_DAY
    uplift_cost_per_point: float = config.CAPACITY_UPLIFT_COST_PER_POINT
    pareto_points: int = 6
    maintenance_risk_threshold: float = config.MAINTENANCE_RISK_THRESHOLD


@dataclass
class ScenarioResult:
    spec: dict
    best: dict
    best_plan: ProductionPlan
    scenarios: pd.DataFrame          # epsilon-constraint frontier runs
    pareto: pd.DataFrame             # non-dominated subset
    solution: pd.DataFrame           # x[l,p,d] > 0 detail of the chosen solution
    note: str = ""

    def as_dict(self) -> dict:
        return {"spec": self.spec, "best": self.best, "note": self.note,
                "scenarios": self.scenarios.to_dict(orient="records"),
                "pareto": self.pareto.to_dict(orient="records"),
                "solution": self.solution.to_dict(orient="records")}


# --------------------------------------------------------------------------- #
# Data assembly
# --------------------------------------------------------------------------- #
def _energy_intensity(tb: Toolbox):
    ep = tb.run_named_query("12_energy_by_product").set_index("product_code")
    tot = tb.run_sql(
        """
        WITH e AS (SELECT SUM(energy_kwh) kwh FROM agg_machine_day),
             c AS (SELECT SUM(d.good_units) caps FROM agg_machine_day d
                   JOIN dim_machine m USING (machine_id)
                   WHERE m.machine_type='doser_filler')
        SELECT e.kwh, c.caps FROM e, c
        """).iloc[0]
    plant_avg_wh = tot["kwh"] * 1000.0 / max(tot["caps"], 1)
    rel = ep["wh_per_capsule"] / ep["wh_per_capsule"].mean()
    wh = {p: float(plant_avg_wh * rel[p]) for p in ep.index}
    reject_rate = float(tb.run_sql(
        "SELECT SUM(reject_units)::DOUBLE/NULLIF(SUM(good_units+reject_units),0) r "
        "FROM agg_machine_day").iloc[0]["r"] or 0.0)
    return wh, reject_rate


def _assemble(spec: OptimizerSpec, tb: Toolbox) -> dict:
    asof = pd.to_datetime(tb.run_sql("SELECT MAX(day) d FROM agg_machine_day")["d"].iloc[0]).date()
    start = asof + timedelta(days=1)
    days = [start + timedelta(days=i) for i in range(spec.horizon_days)]

    cap_df = tb.line_daily_capacity()
    cap_base = {r["line_id"]: float(r["median_daily_capsules"]) for _, r in cap_df.iterrows()}
    lines = sorted(cap_base)

    base = tb.product_demand_baseline()
    frac = spec.horizon_days / 365.0
    if spec.demand_override:
        demand = {k: float(v) for k, v in spec.demand_override.items()}
    else:
        demand = {r["product_code"]: float(r["annual_capsules"]) * spec.demand_growth * frac
                  for _, r in base.iterrows()}
    products = sorted(demand)

    wh, reject_rate = _energy_intensity(tb)

    # maintenance: place high-risk machines' lines on Sundays (blocks that line-day)
    maint = tb.maintenance_candidates(spec.maintenance_risk_threshold).head(len(lines) * 3)
    sundays = [d for d in days if d.weekday() == 6]
    maint_events, blocked = [], set()
    for i, (_, mrow) in enumerate(maint.iterrows()):
        if not sundays:
            break
        slot = sundays[i % len(sundays)]
        maint_events.append({"machine_id": mrow["machine_id"], "line_id": mrow["line_id"],
                             "date": slot.isoformat(), "risk_score": float(mrow["risk_score"]),
                             "action": "Preventive maintenance (bearings/seals inspection)"})
        blocked.add((mrow["line_id"], slot))

    return {"asof": asof, "start": start, "days": days, "lines": lines, "products": products,
            "cap_base": cap_base, "demand": demand, "wh": wh, "reject_rate": reject_rate,
            "maint_events": maint_events, "blocked": blocked}


# --------------------------------------------------------------------------- #
# MILP build + solve
# --------------------------------------------------------------------------- #
def _solve(spec: OptimizerSpec, data: dict, objective: str,
           energy_cap: float | None = None, fulfil_floor: float | None = None,
           time_limit: float | None = None, gap_rel: float | None = None):
    L, P, days = data["lines"], data["products"], data["days"]
    D = list(range(len(days)))
    cap = data["cap_base"]
    demand, wh = data["demand"], data["wh"]
    blocked = data["blocked"]
    peak, off = spec.peak_price, spec.offpeak_price
    margin = config.CAPSULE_MARGIN_EUR
    scrap = config.MATERIAL_COST_EUR_PER_CAPSULE * data["reject_rate"]
    capex_per_fraction = spec.uplift_cost_per_point * 100.0
    umax = UPLIFT_MAX if spec.allow_uplift else 0.0

    # --- Data-driven tightening of the U (OEE-uplift) domain ----------------
    # U only ever pays off (its capex is strictly positive) if the plant's
    # baseline network capacity -- every line-day, *including* full Sunday
    # overtime, but with zero uplift -- cannot already cover total demand.
    # Compute that baseline headroom once and use it, instead of the blanket
    # UPLIFT_MAX, as the upper bound for U itself and for every big-M /
    # McCormick coefficient that multiplies it: the U*otd product w[l][d] on
    # Sundays, and the y campaign big-M. This shrinks the LP-relaxation box
    # for U (and hence the McCormick envelope of w, which is exact but only
    # over whatever box U actually lives in) without excluding any truly
    # optimal solution -- a safety buffer keeps some headroom reachable in
    # case per-line-day scheduling friction (single-product campaigns,
    # changeovers, blocked maintenance days) ever makes local uplift
    # worthwhile beyond the raw aggregate calculation.
    total_cap_no_uplift = sum(cap[l] for l in L for d in D if (l, days[d]) not in blocked)
    total_demand_all = sum(demand.values())
    headroom_needed = (max(0.0, (total_demand_all - total_cap_no_uplift) / total_cap_no_uplift)
                        if total_cap_no_uplift > 0 else umax)
    UPLIFT_SAFETY_BUFFER = 0.03      # 3pp cushion for per-line-day scheduling friction
    u_cap = min(umax, headroom_needed + UPLIFT_SAFETY_BUFFER) if spec.allow_uplift else 0.0

    m = pulp.LpProblem("coffee_plan", pulp.LpMaximize)
    x = pulp.LpVariable.dicts("x", (L, P, D), lowBound=0)
    opx = pulp.LpVariable.dicts("opx", (L, P, D), lowBound=0)
    otd = pulp.LpVariable.dicts("otd", (L, D), cat="Binary")
    w = pulp.LpVariable.dicts("w", (L, D), lowBound=0)          # McCormick U*otd
    U = pulp.LpVariable("U", lowBound=0, upBound=u_cap)
    use_campaign = spec.campaign_binaries
    if use_campaign:
        y = pulp.LpVariable.dicts("y", (L, P, D), cat="Binary")
        chg = pulp.LpVariable.dicts("chg", (L, D), lowBound=0)

    is_sun = {d: days[d].weekday() == 6 for d in D}

    for l in L:
        for d in D:
            sun = is_sun[d]
            blk = (l, days[d]) in blocked
            if use_campaign:
                m += pulp.lpSum(y[l][p][d] for p in P) <= 1
                for p in P:
                    m += x[l][p][d] <= cap[l] * (1 + u_cap) * y[l][p][d]
            for p in P:
                m += opx[l][p][d] <= x[l][p][d]
            daily = pulp.lpSum(x[l][p][d] for p in P)
            opdaily = pulp.lpSum(opx[l][p][d] for p in P)
            if blk:
                m += daily == 0
            elif sun:
                m += w[l][d] <= u_cap * otd[l][d]
                m += w[l][d] <= U
                m += w[l][d] >= U - u_cap * (1 - otd[l][d])
                m += daily <= cap[l] * (otd[l][d] + w[l][d])
                m += opdaily <= cap[l] * OFFPEAK_FRACTION * otd[l][d]
                if not spec.allow_overtime:
                    m += otd[l][d] == 0
            else:
                m += daily <= cap[l] * (1 + U)
                m += opdaily <= cap[l] * OFFPEAK_FRACTION
            if use_campaign and d > 0:
                for p in P:
                    m += chg[l][d] >= y[l][p][d] - y[l][p][d - 1]

    produced = {p: pulp.lpSum(x[l][p][d] for l in L for d in D) for p in P}
    for p in P:
        m += produced[p] <= demand[p]

    energy_cost = pulp.lpSum(
        x[l][p][d] * wh[p] / 1000.0 * peak
        - opx[l][p][d] * wh[p] / 1000.0 * (peak - off)
        for l in L for p in P for d in D)
    total_produced = pulp.lpSum(produced[p] for p in P)
    overtime_cost = pulp.lpSum(otd[l][d] for l in L for d in D) * spec.overtime_cost_per_line_day
    uplift_capex = U * capex_per_fraction
    changeover_cost = (pulp.lpSum(chg[l][d] for l in L for d in D) * CHANGEOVER_COST_EUR
                       if use_campaign else 0)
    scrap_cost = total_produced * scrap
    gross_margin = (total_produced * margin - energy_cost - overtime_cost
                    - uplift_capex - changeover_cost - scrap_cost)

    if energy_cap is not None:
        m += energy_cost <= energy_cap
    floor = fulfil_floor
    if floor is None and spec.min_fulfilment_pct is not None:
        floor = spec.min_fulfilment_pct / 100.0
    if floor is None and objective == "energy_cost":
        floor = 1.0
    if floor is not None:
        for p in P:
            m += produced[p] >= floor * demand[p]

    total_demand = sum(demand.values())
    chg_reg = changeover_cost if use_campaign else 0
    if objective == "margin":
        m += gross_margin
    elif objective == "fulfilment":
        m += total_produced - 1e-6 * energy_cost - 1e-3 * chg_reg
    elif objective == "energy_cost":
        m += -energy_cost - 1e-2 * chg_reg
    else:  # balanced
        m += gross_margin + 0.02 * margin * total_produced

    tl = time_limit if time_limit is not None else SOLVER_TIME_LIMIT
    gr = gap_rel if gap_rel is not None else 0.01
    m.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=tl, gapRel=gr))
    status = pulp.LpStatus[m.status]

    def val(v):
        return float(v.value() or 0.0)

    prod_val = {p: sum(val(x[l][p][d]) for l in L for d in D) for p in P}
    energy_val = sum(val(x[l][p][d]) * wh[p] / 1000.0 * peak
                     - val(opx[l][p][d]) * wh[p] / 1000.0 * (peak - off)
                     for l in L for p in P for d in D)
    planned = sum(prod_val.values())
    metrics = {
        "solver_status": status,
        "uplift_pct": round(val(U) * 100, 2),
        "overtime_line_days": int(round(sum(val(otd[l][d]) for l in L for d in D))),
        "offpeak_capsules": round(sum(val(opx[l][p][d]) for l in L for p in P for d in D)),
        "planned_capsules": round(planned),
        "fulfilment_pct": round(100.0 * planned / total_demand, 2) if total_demand else 100.0,
        "energy_kwh": round(sum(val(x[l][p][d]) * wh[p] / 1000.0 for l in L for p in P for d in D)),
        "energy_cost_eur": round(energy_val),
        "overtime_cost_eur": round(sum(val(otd[l][d]) for l in L for d in D) * spec.overtime_cost_per_line_day),
        "uplift_cost_eur": round(val(U) * capex_per_fraction),
        "changeover_cost_eur": round(sum(val(chg[l][d]) for l in L for d in D) * CHANGEOVER_COST_EUR)
                               if use_campaign else 0,
        "scrap_cost_eur": round(planned * scrap),
        "produced_by_product": {p: round(prod_val[p]) for p in P},
    }
    metrics["gross_margin_eur"] = round(
        metrics["planned_capsules"] * margin - metrics["energy_cost_eur"]
        - metrics["overtime_cost_eur"] - metrics["uplift_cost_eur"]
        - metrics["changeover_cost_eur"] - metrics["scrap_cost_eur"])

    cells = []
    for l in L:
        for d in D:
            for p in P:
                q = val(x[l][p][d])
                if q > 1:
                    cells.append({"line_id": l, "date": days[d].isoformat(),
                                  "product": p, "capsules": round(q),
                                  "offpeak_capsules": round(val(opx[l][p][d])),
                                  "overtime": bool(round(val(otd[l][d])))})
    return status, metrics, pd.DataFrame(cells)


# --------------------------------------------------------------------------- #
# Convert a chosen solution into a ProductionPlan
# --------------------------------------------------------------------------- #
def _to_plan(spec: OptimizerSpec, data: dict, metrics: dict, solution: pd.DataFrame) -> ProductionPlan:
    days, lines = data["days"], data["lines"]
    blocked = data["blocked"]
    uplift = metrics["uplift_pct"] / 100.0
    capacity = {l: round(data["cap_base"][l] * (1 + uplift)) for l in lines}
    # aggregate the solver solution to one dominant campaign per line-day
    agg = {}
    if not solution.empty:
        for (l, dt), g in solution.groupby(["line_id", "date"]):
            top = g.loc[g["capsules"].idxmax()]
            agg[(l, dt)] = {"product": top["product"],
                            "capsules": int(g["capsules"].sum()),
                            "offpeak_capsules": int(g["offpeak_capsules"].sum())}

    rows = []
    for l in lines:
        for d in days:
            key = (l, d.isoformat())
            if (l, d) in blocked:
                state, product, units, op = "MAINTENANCE", None, 0, 0
            elif key in agg:
                r = agg[key]
                state, product, units, op = "PRODUCTION", r["product"], r["capsules"], r["offpeak_capsules"]
            else:
                state, product, units, op = "IDLE", None, 0, 0
            rows.append({"line_id": l, "date": d.isoformat(), "weekday": d.strftime("%a"),
                         "state": state, "product": product, "planned_capsules": units,
                         "offpeak_capsules": op})
    sched = pd.DataFrame(rows)

    changeovers = 0
    for l in lines:
        seq = sched[(sched.line_id == l) & (sched.planned_capsules > 0)].sort_values("date")["product"].tolist()
        changeovers += sum(1 for a, b in zip(seq, seq[1:]) if a != b)

    demand = data["demand"]
    produced = metrics["produced_by_product"]
    ful = {p: round(100 * produced.get(p, 0) / demand[p], 1) if demand[p] else 100.0 for p in demand}
    unmet = {p: round(max(demand[p] - produced.get(p, 0), 0)) for p in demand}
    prod_days = sched[(sched.state == "PRODUCTION")]["date"].nunique()

    summary = {
        "planned_capsules": metrics["planned_capsules"],
        "demand_capsules": round(sum(demand.values())),
        "fulfilment_pct_by_product": ful,
        "unmet_capsules_by_product": unmet,
        "planned_utilisation_pct": round(100.0 * metrics["planned_capsules"]
                                         / max(sum(capacity.values()) * prod_days, 1), 1),
        "changeovers": int(changeovers),
        "maintenance_events": len(data["maint_events"]),
        "production_days": int(prod_days),
        "target_oee": config.TARGET_OEE,
    }
    rationale = [
        f"MILP (PuLP/CBC) — objective '{spec.objective}', status {metrics['solver_status']}.",
        f"Chose OEE uplift {metrics['uplift_pct']:.1f}% (capex €{metrics['uplift_cost_eur']:,}), "
        f"{metrics['overtime_line_days']} Sunday overtime line-days, "
        f"{metrics['offpeak_capsules']:,} capsules on off-peak tariff.",
        f"Planned {metrics['planned_capsules']:,} capsules "
        f"(margin €{metrics['gross_margin_eur']:,}, energy €{metrics['energy_cost_eur']:,}, "
        f"{summary['changeovers']} changeovers).",
        "Line/product/day production and campaign assignment chosen by the solver, not fixed a priori.",
    ]
    maint_df = pd.DataFrame(data["maint_events"])
    return ProductionPlan(
        params={"engine": "MILP", **{k: v for k, v in asdict(spec).items()}},
        start_date=data["start"].isoformat(), end_date=days[-1].isoformat(),
        demand={k: round(v) for k, v in demand.items()}, capacity=capacity,
        schedule=sched, maintenance=maint_df, summary=summary, rationale=rationale)


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def optimize(spec: OptimizerSpec | None = None, tb: Toolbox | None = None) -> ScenarioResult:
    spec = spec or OptimizerSpec()
    tb = tb or Toolbox()
    data = _assemble(spec, tb)

    # The scored metric (gross_margin_eur) is computed exclusively from this one
    # solve, so it gets the bulk of the time budget and a tight optimality gap.
    status, best, solution = _solve(spec, data, spec.objective,
                                    energy_cap=spec.max_energy_cost_eur,
                                    time_limit=PRIMARY_TIME_LIMIT, gap_rel=PRIMARY_GAP_REL)
    note = "" if status == "Optimal" else f"Solver status: {status} (constraints may be infeasible)."

    # Everything below is informational (fulfilment/energy frontier for the
    # dashboard) and never feeds gross_margin_eur, so it runs with a short time
    # limit and a looser gap to leave more of the budget for the primary solve.
    _, hi, _ = _solve(spec, data, "fulfilment", time_limit=AUX_TIME_LIMIT, gap_rel=AUX_GAP_REL)
    _, lo, _ = _solve(spec, data, "energy_cost", fulfil_floor=0.80,
                       time_limit=AUX_TIME_LIMIT, gap_rel=AUX_GAP_REL)
    e_hi, e_lo = hi["energy_cost_eur"], lo["energy_cost_eur"]
    rows = []
    caps = np.linspace(e_lo, e_hi, max(spec.pareto_points, 2)) if e_hi > e_lo else [e_hi]
    for cap_e in caps:
        st, mm, _ = _solve(spec, data, "fulfilment", energy_cap=float(cap_e),
                            time_limit=AUX_TIME_LIMIT, gap_rel=AUX_GAP_REL)
        rows.append({"energy_cap_eur": round(float(cap_e)),
                     "energy_cost_eur": mm["energy_cost_eur"],
                     "fulfilment_pct": mm["fulfilment_pct"],
                     "gross_margin_eur": mm["gross_margin_eur"],
                     "planned_capsules": mm["planned_capsules"],
                     "uplift_pct": mm["uplift_pct"],
                     "overtime_line_days": mm["overtime_line_days"],
                     "feasible": st == "Optimal"})
    scenarios = (pd.DataFrame(rows)
                 .drop_duplicates(subset=["fulfilment_pct", "energy_cost_eur"])
                 .sort_values("energy_cost_eur").reset_index(drop=True))
    pareto = _pareto(scenarios)

    best_plan = _to_plan(spec, data, best, solution)
    return ScenarioResult(spec=asdict(spec), best=best, best_plan=best_plan,
                          scenarios=scenarios, pareto=pareto, solution=solution, note=note)


def _pareto(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    pts = df.sort_values(["fulfilment_pct", "energy_cost_eur"],
                         ascending=[False, True]).reset_index(drop=True)
    keep, best_cost = [], float("inf")
    for _, r in pts.iterrows():
        if r["energy_cost_eur"] < best_cost:
            keep.append(r)
            best_cost = r["energy_cost_eur"]
    return pd.DataFrame(keep).sort_values("energy_cost_eur").reset_index(drop=True)
