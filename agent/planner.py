"""Production planner: builds a horizon schedule grounded in observed capacity
and demand, minimising changeovers and inserting preventive maintenance for
high-risk machines. Deterministic and fully explainable."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import date, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import config
from agent.tools import Toolbox
from agent.milp_allocator import solve_allocation


@dataclass
class PlanParams:
    horizon_days: int = config.PLAN_HORIZON_DAYS
    start_date: date | None = None                 # defaults to day after dataset end
    demand_growth: float = config.DEMAND_GROWTH
    target_oee: float = config.TARGET_OEE
    maintenance_risk_threshold: float = config.MAINTENANCE_RISK_THRESHOLD
    demand_override: dict | None = None            # {product: capsules} for the horizon
    workdays_per_week: int = 6                     # retained for API compat; no longer used
                                                    # to blanket-idle a rest day (see note in
                                                    # build_production_plan) -- every calendar
                                                    # day is now a production candidate for
                                                    # every line, and only each line's own
                                                    # jointly-optimised maintenance day(s) are
                                                    # excluded from production.
    capacity_uplift: float = 0.0                   # fractional capacity gain from OEE programs


@dataclass
class ProductionPlan:
    params: dict
    start_date: str
    end_date: str
    demand: dict                     # product -> capsules to produce in horizon
    capacity: dict                   # line -> capsules/day used
    schedule: pd.DataFrame           # per line/day assignments
    maintenance: pd.DataFrame        # scheduled maintenance events
    summary: dict
    rationale: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "params": self.params,
            "start_date": self.start_date, "end_date": self.end_date,
            "demand": self.demand, "capacity": self.capacity,
            "summary": self.summary, "rationale": self.rationale,
            "schedule": self.schedule.to_dict(orient="records"),
            "maintenance": self.maintenance.to_dict(orient="records"),
        }

    def as_narration_dict(self) -> dict:
        """Compact plan view for LLM narration: KPIs already fully capture the
        schedule/maintenance outcome (totals, fulfilment, changeovers, risk
        counts), so the per-day schedule rows and per-event maintenance table
        are redundant here and are omitted to save tokens. Full detail remains
        available via as_dict() for reports/hashing."""
        return {
            "start_date": self.start_date, "end_date": self.end_date,
            "demand": self.demand, "capacity": self.capacity,
            "summary": self.summary,
        }


def build_production_plan(params: PlanParams | None = None,
                          tb: Toolbox | None = None) -> ProductionPlan:
    params = params or PlanParams()
    tb = tb or Toolbox()
    rationale: list[str] = []

    # --- dataset clock -> plan start ---
    asof = pd.to_datetime(tb.run_sql("SELECT MAX(day) d FROM agg_machine_day")["d"].iloc[0]).date()
    start = params.start_date or (asof + timedelta(days=1))
    days = [start + timedelta(days=i) for i in range(params.horizon_days)]
    end = days[-1]
    rationale.append(f"Planning {params.horizon_days} days ({start} → {end}); dataset clock at {asof}.")

    # --- capacity (observed effective capsules/day per line) ---
    cap_df = tb.line_daily_capacity()
    uplift = 1.0 + params.capacity_uplift
    capacity = {r["line_id"]: float(r["median_daily_capsules"]) * uplift for _, r in cap_df.iterrows()}
    lines = sorted(capacity)
    cap_note = "" if params.capacity_uplift == 0 else f" (+{params.capacity_uplift*100:.0f}% OEE uplift)"
    rationale.append("Line capacity from observed median of real production days" + cap_note + ": "
                     + ", ".join(f"{l}={capacity[l]:,.0f}/day" for l in lines))

    # --- demand (override or last-year actual scaled by growth & horizon) ---
    base = tb.product_demand_baseline()
    horizon_fraction = params.horizon_days / 365.0
    if params.demand_override:
        demand = {k: float(v) for k, v in params.demand_override.items()}
        rationale.append("Demand taken from user override.")
    else:
        demand = {r["product_code"]: float(r["annual_capsules"]) * params.demand_growth * horizon_fraction
                  for _, r in base.iterrows()}
        rationale.append(f"Demand = last-year output × {params.demand_growth:g} growth × "
                         f"{horizon_fraction:.3f} horizon fraction.")
    total_demand = sum(demand.values())

    # --- maintenance requirement: every high-risk machine must get its line
    # taken down for preventive maintenance somewhere in the horizon. All
    # overdue machines *on the same line* are batched into a single line-down
    # day (one maintenance shutdown services everything due on that line),
    # so each line needs at most one mandatory maintenance day. WHERE that
    # day falls is decided jointly with the production allocation below
    # (agent.milp_allocator.solve_allocation) instead of being pinned in
    # advance to a demand-blind rotating slot -- this is what lets the
    # solver put maintenance on the line-day that costs the least fulfilment
    # rather than a round-robin day that might collide with scarce demand.
    maint = tb.maintenance_candidates(params.maintenance_risk_threshold).copy()
    maint_by_line = {l: g for l, g in maint.groupby("line_id")} if not maint.empty else {}
    maint_required = {l: (1 if l in maint_by_line else 0) for l in lines}
    if maint_by_line:
        rationale.append(f"{sum(len(g) for g in maint_by_line.values())} machines above risk "
                         f"{params.maintenance_risk_threshold:.0f} need preventive maintenance, "
                         f"batched into {len(maint_by_line)} mandatory line-down day(s) "
                         "(one per affected line) placed jointly with the production plan.")

    # --- allocate products to lines, and place maintenance day(s), via a
    # single deterministic MILP (was: greedy "home product" heuristic that
    # left spare line-days idle whenever its home product ran out of demand,
    # plus a demand-blind round-robin maintenance slot that blanket-idled
    # every line on a fixed weekly rest day regardless of whether that line
    # actually needed maintenance that day). The MILP jointly assigns, for
    # every line and every calendar day, whether the line is in maintenance,
    # and if not, which product (if any) is campaigned and how many capsules
    # are made -- so total demand fulfilment is maximised first, changeovers
    # are minimised as a tie-break, and each line's maintenance day is placed
    # on the day that costs the least fulfilment. See
    # agent.milp_allocator.solve_allocation for the formulation and the
    # determinism controls (sorted keys, single-threaded CBC, fixed seed).
    alloc, changeovers, maint_days, solver_note = solve_allocation(
        lines=lines, products=sorted(demand), days=days,
        capacity=capacity, demand=demand, maint_required=maint_required)
    rationale.append(solver_note)

    maint_events = []
    for l, chosen_dates in maint_days.items():
        for d_iso in chosen_dates:
            for _, m in maint_by_line[l].iterrows():
                maint_events.append({"machine_id": m["machine_id"], "line_id": l,
                                     "date": d_iso, "risk_score": float(m["risk_score"]),
                                     "action": "Preventive maintenance (bearings/seals inspection)"})
    maint_df = pd.DataFrame(maint_events)
    maint_by_line_day = {(e["line_id"], e["date"]) for e in maint_events}

    # --- capacity check: every calendar day is a production candidate for
    # every line except that line's own maintenance day(s), so a line's
    # available production days = horizon_days - maint_required[line].
    prod_days_per_line = {l: params.horizon_days - maint_required[l] for l in lines}
    total_capacity = sum(capacity[l] * prod_days_per_line[l] for l in lines)
    util = total_demand / total_capacity if total_capacity else 0
    rationale.append(f"Total demand {total_demand/1e6:.1f}M vs capacity {total_capacity/1e6:.1f}M "
                     f"→ planned utilisation {util*100:.0f}%.")

    rows = []
    for l in lines:
        for d in days:
            if (l, d.isoformat()) in maint_by_line_day:
                rows.append(_row(l, d, "MAINTENANCE", None, 0))
                continue
            prod, units = alloc.get((l, d.isoformat()), (None, 0.0))
            if prod is None or units <= 0:
                rows.append(_row(l, d, "IDLE", None, 0))
                continue
            rows.append(_row(l, d, "PRODUCTION", prod, units))

    sched = pd.DataFrame(rows)

    # changeovers already computed by the solver (see solve_allocation); we
    # recompute from the realised schedule too, purely as a cross-check that
    # the post-processed rows agree with what the MILP reported.
    _check_changeovers = 0
    for l in lines:
        seq = sched[(sched.line_id == l) & (sched.planned_capsules > 0)].sort_values("date")["product"].tolist()
        _check_changeovers += sum(1 for a, b in zip(seq, seq[1:]) if a != b)
    if _check_changeovers != changeovers:
        changeovers = _check_changeovers  # trust the realised schedule if they ever diverge

    produced = sched.groupby("product")["planned_capsules"].sum().to_dict()
    fulfil = {p: round(100 * produced.get(p, 0) / demand[p], 1) if demand[p] else 100.0
              for p in demand}
    unmet = {p: round(max(demand[p] - produced.get(p, 0), 0)) for p in demand}

    summary = {
        "planned_capsules": round(sched["planned_capsules"].sum()),
        "demand_capsules": round(total_demand),
        "fulfilment_pct_by_product": fulfil,
        "unmet_capsules_by_product": unmet,
        "planned_utilisation_pct": round(util * 100, 1),
        "changeovers": int(changeovers),
        "maintenance_events": len(maint_events),
        "production_days": prod_days_per_line,
        "target_oee": params.target_oee,
    }
    if any(v > 0 for v in unmet.values()):
        rationale.append("Capacity shortfall detected → recommend overtime shifts or "
                         "OEE improvement to close the gap (see summary.unmet_capsules_by_product).")
    else:
        rationale.append("All demand met within available production days.")

    return ProductionPlan(
        params=_params_dict(params), start_date=start.isoformat(), end_date=end.isoformat(),
        demand={k: round(v) for k, v in demand.items()},
        capacity={k: round(v) for k, v in capacity.items()},
        schedule=sched, maintenance=maint_df, summary=summary, rationale=rationale)


def _row(line, d, state, product, units):
    return {"line_id": line, "date": d.isoformat(), "weekday": d.strftime("%a"),
            "state": state, "product": product, "planned_capsules": round(units)}


def _params_dict(p: PlanParams) -> dict:
    d = asdict(p)
    d["start_date"] = p.start_date.isoformat() if p.start_date else None
    return d
