"""CLI entry point for the efficiency & production-planning agent.

Examples:
  python -m agent.run_agent
  python -m agent.run_agent --horizon 42 --growth 1.10 --out agent_output
  python -m agent.run_agent --demand STRONG=40000000,MILD=30000000,DECAF=25000000
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from agent.agent import EfficiencyAgent
from agent.planner import PlanParams
from agent import report as report_mod


def _parse_demand(s: str | None):
    if not s:
        return None
    out = {}
    for part in s.split(","):
        k, v = part.split("=")
        out[k.strip().upper()] = float(v)
    return out


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Coffee-capsule efficiency & production-plan agent")
    ap.add_argument("--horizon", type=int, default=config.PLAN_HORIZON_DAYS,
                    help="planning horizon in days")
    ap.add_argument("--growth", type=float, default=config.DEMAND_GROWTH,
                    help="demand growth factor vs last year")
    ap.add_argument("--target-oee", type=float, default=config.TARGET_OEE)
    ap.add_argument("--maint-risk", type=float, default=config.MAINTENANCE_RISK_THRESHOLD)
    ap.add_argument("--demand", type=str, default=None,
                    help="override horizon demand, e.g. STRONG=4e7,MILD=3e7,DECAF=2.5e7")
    ap.add_argument("--out", type=str, default=str(config.REPO_DIR / "agent_output"))
    ap.add_argument("--no-llm", action="store_true", help="force deterministic narrative")
    # scenario optimizer
    ap.add_argument("--optimize", action="store_true",
                    help="run the scenario optimizer to select the best plan")
    ap.add_argument("--objective", choices=["margin", "fulfilment", "energy_cost", "balanced"],
                    default="margin")
    ap.add_argument("--max-energy-cost", type=float, default=None,
                    help="constraint: max horizon energy cost (EUR)")
    ap.add_argument("--min-fulfilment", type=float, default=None,
                    help="constraint: min demand fulfilment (%%)")
    ap.add_argument("--no-overtime", action="store_true",
                    help="disallow Sunday overtime in the optimizer")
    args = ap.parse_args(argv)

    if not config.DB_PATH.exists():
        raise SystemExit(f"Warehouse not found: {config.DB_PATH}. Run scripts/init_db.py first.")

    params = PlanParams(horizon_days=args.horizon, demand_growth=args.growth,
                        target_oee=args.target_oee,
                        maintenance_risk_threshold=args.maint_risk,
                        demand_override=_parse_demand(args.demand))

    opt_spec = None
    if args.optimize:
        from agent.optimizer import OptimizerSpec
        opt_spec = OptimizerSpec(objective=args.objective, horizon_days=args.horizon,
                                 demand_growth=args.growth,
                                 demand_override=_parse_demand(args.demand),
                                 max_energy_cost_eur=args.max_energy_cost,
                                 min_fulfilment_pct=args.min_fulfilment,
                                 allow_overtime=not args.no_overtime)

    agent = EfficiencyAgent()
    rep = agent.run(params, use_llm=False if args.no_llm else None, optimize_spec=opt_spec)
    paths = report_mod.save(rep, Path(args.out))

    print(report_mod.render_markdown(rep))
    print("\nArtifacts written:")
    for k, v in paths.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
