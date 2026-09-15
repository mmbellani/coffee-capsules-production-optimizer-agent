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


@dataclass
class PlanParams:
    horizon_days: int = config.PLAN_HORIZON_DAYS
    start_date: date | None = None                 # defaults to day after dataset end
    demand_growth: float = config.DEMAND_GROWTH
    target_oee: float = config.TARGET_OEE
    maintenance_risk_threshold: float = config.MAINTENANCE_RISK_THRESHOLD
    demand_override: dict | None = None            # {product: capsules} for the horizon
    workdays_per_week: int = 6                     # Mon-Sat production, Sun maintenance/idle
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
    prod_days_per_line = sum(1 for d in days if d.weekday() < params.workdays_per_week)
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

    # --- capacity check ---
    total_capacity = sum(capacity[l] for l in lines) * prod_days_per_line
    util = total_demand / total_capacity if total_capacity else 0
    rationale.append(f"Total demand {total_demand/1e6:.1f}M vs capacity {total_capacity/1e6:.1f}M "
                     f"→ planned utilisation {util*100:.0f}%.")

    # --- maintenance scheduling: high-risk machines get a non-production day ---
    maint = tb.maintenance_candidates(params.maintenance_risk_threshold).copy()
    maint_events = []
    non_prod_days = [d for d in days if d.weekday() >= params.workdays_per_week] or [days[6]]
    for i, (_, m) in enumerate(maint.head(len(lines) * 3).iterrows()):
        slot = non_prod_days[i % len(non_prod_days)]
        maint_events.append({"machine_id": m["machine_id"], "line_id": m["line_id"],
                             "date": slot.isoformat(), "risk_score": float(m["risk_score"]),
                             "action": "Preventive maintenance (bearings/seals inspection)"})
    maint_df = pd.DataFrame(maint_events)
    maint_by_line_day = {(e["line_id"], e["date"]) for e in maint_events}
    if maint_events:
        rationale.append(f"Scheduled {len(maint_events)} preventive-maintenance slots on "
                         f"non-production days for machines above risk {params.maintenance_risk_threshold:.0f}.")

    # --- allocate products to lines to minimise changeovers ---
    # Assign each line a "home" product (largest demand first, round-robin) so it
    # runs long single-product campaigns; overflow demand fills spare line-days.
    remaining = dict(sorted(demand.items(), key=lambda x: -x[1]))
    line_product = {l: p for l, p in zip(lines, list(remaining.keys()) + list(remaining.keys()))}
    rationale.append("Assigned each line a home product for long campaigns: "
                     + ", ".join(f"{l}->{line_product[l]}" for l in lines))

    rows = []
    for l in lines:
        home = line_product[l]
        for d in days:
            is_prod_day = d.weekday() < params.workdays_per_week
            is_maint = (l, d.isoformat()) in maint_by_line_day
            if not is_prod_day:
                rows.append(_row(l, d, "MAINTENANCE" if is_maint else "IDLE", None, 0))
                continue
            # pick product: home product while its demand remains, else the
            # product with the most outstanding demand (keeps campaigns long).
            prod = home if remaining.get(home, 0) > 0 else _most_needed(remaining)
            if prod is None:
                rows.append(_row(l, d, "IDLE", None, 0))
                continue
            planned = min(capacity[l], remaining[prod])
            remaining[prod] -= planned
            state = "MAINTENANCE" if is_maint else "PRODUCTION"
            plan_units = 0 if is_maint else planned
            if is_maint:
                remaining[prod] += planned  # give back, machine is down
            rows.append(_row(l, d, state, None if is_maint else prod, plan_units))

    sched = pd.DataFrame(rows)

    # --- changeover count (product switches per line) ---
    changeovers = 0
    for l in lines:
        seq = sched[(sched.line_id == l) & (sched.product == sched.product) &
                    (sched.planned_capsules > 0)].sort_values("date")["product"].tolist()
        changeovers += sum(1 for a, b in zip(seq, seq[1:]) if a != b)

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
        rationale.append("Capacity shortfall detected → recommend overtime (Sunday shifts) or "
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


def _most_needed(remaining: dict):
    pos = {p: v for p, v in remaining.items() if v > 0}
    return max(pos, key=pos.get) if pos else None


def _params_dict(p: PlanParams) -> dict:
    d = asdict(p)
    d["start_date"] = p.start_date.isoformat() if p.start_date else None
    return d
