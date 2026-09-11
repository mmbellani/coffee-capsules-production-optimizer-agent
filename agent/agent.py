"""EfficiencyAgent: the orchestrator that ties tools, analyzers, planner and the
optional LLM into a single agentic run producing a diagnosis + production plan.

The agent follows an explicit plan-act-observe loop over analysis steps and
records a trace so the reasoning is transparent (and swappable for an LLM-driven
ReAct loop when credentials are configured)."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from agent.tools import Toolbox
from agent import analyzers, planner, llm, optimizer as optimizer_mod


@dataclass
class AgentReport:
    generated_at: str
    diagnosis_summary: dict
    findings: list[dict]
    plan: planner.ProductionPlan
    narrative: str
    trace: list[dict] = field(default_factory=list)
    llm_used: bool = False
    optimization: optimizer_mod.ScenarioResult | None = None


class EfficiencyAgent:
    def __init__(self, tb: Toolbox | None = None):
        self.tb = tb or Toolbox()
        self.trace: list[dict] = []

    def _step(self, action: str, observation: str):
        self.trace.append({"step": len(self.trace) + 1, "action": action,
                           "observation": observation})

    def run(self, params: planner.PlanParams | None = None,
            use_llm: bool | None = None,
            optimize_spec: "optimizer_mod.OptimizerSpec | None" = None) -> AgentReport:
        self.trace = []

        # 1) sense
        self._step("Inspect warehouse & analytics catalog",
                   f"{len(self.tb.list_named_queries())} named queries available.")

        # 2) diagnose inefficiencies
        findings = analyzers.diagnose(self.tb)
        dsum = analyzers.summarise(findings)
        self._step("Diagnose inefficiencies (OEE losses, downtime, quality, energy, "
                   "maintenance, changeovers)",
                   f"{dsum['n_findings']} findings; total quantified impact "
                   f"€{dsum['total_impact_eur']:,}. Top areas: "
                   + ", ".join(f"{k} €{v:,}" for k, v in
                               list(dsum['impact_by_area_eur'].items())[:3]))

        # 3) optimize scenarios (optional) -> selects the plan
        opt = None
        if optimize_spec is not None:
            opt = optimizer_mod.optimize(optimize_spec, self.tb)
            b = opt.best
            self._step(f"Optimize scenarios (objective={optimize_spec.objective}) — MILP solve "
                       f"(PuLP/CBC) + {len(opt.scenarios)}-point Pareto frontier",
                       f"Winner: uplift={b['uplift_pct']}%, overtime_days={b['overtime_line_days']}, "
                       f"offpeak={b['offpeak_capsules']:,} caps -> margin €{b['gross_margin_eur']:,}, "
                       f"fulfilment {b['fulfilment_pct']}%, energy €{b['energy_cost_eur']:,} "
                       f"[{b['solver_status']}]. " + (opt.note or "Constraints satisfied."))
            plan = opt.best_plan
        else:
            plan = planner.build_production_plan(params, self.tb)
        self._step("Build capacity- and demand-grounded production plan with "
                   "changeover minimisation + maintenance insertion",
                   f"Horizon {plan.start_date}→{plan.end_date}; "
                   f"planned {plan.summary['planned_capsules']:,} capsules; "
                   f"{plan.summary['changeovers']} changeovers; "
                   f"{plan.summary['maintenance_events']} maintenance slots.")

        # 4) narrate (LLM optional)
        want_llm = llm.available() if use_llm is None else use_llm
        narrative, llm_used = None, False
        if want_llm:
            diag_payload = dict(dsum)
            diag_payload["findings"] = [f.as_dict() for f in findings[:10]]
            narrative = llm.narrate(diag_payload, plan.as_dict())
            llm_used = narrative is not None and not narrative.startswith("_(LLM")
            self._step("Compose executive narrative via LLM",
                       "LLM narrative generated." if llm_used else "LLM unavailable/failed.")
        if not narrative:
            narrative = self._template_narrative(dsum, findings, plan)
            self._step("Compose executive narrative (deterministic template)",
                       "Narrative generated without LLM.")

        return AgentReport(
            generated_at=datetime.now().isoformat(timespec="seconds"),
            diagnosis_summary=dsum,
            findings=[f.as_dict() for f in findings],
            plan=plan, narrative=narrative, trace=self.trace, llm_used=llm_used,
            optimization=opt)

    # ---- deterministic fallback narrative ----
    @staticmethod
    def _template_narrative(dsum: dict, findings, plan: planner.ProductionPlan) -> str:
        top = findings[:3]
        lines = [
            f"Across the plant, quantified inefficiencies total about "
            f"€{dsum['total_impact_eur']:,} per year "
            f"({dsum['total_impact_capsules']:,} capsules of lost entitlement), "
            f"with {dsum['high_severity']} high-severity issues.",
            "Largest loss areas: " + ", ".join(
                f"{k} (€{v:,})" for k, v in list(dsum['impact_by_area_eur'].items())[:3]) + ".",
            "",
            "Top opportunities:",
        ]
        for i, f in enumerate(top, 1):
            lines.append(f"  {i}. [{f.severity}] {f.title} — €{round(f.impact_eur):,}. {f.recommendation}")
        lines += [
            "",
            f"Production plan ({plan.start_date} → {plan.end_date}): "
            f"schedule {plan.summary['planned_capsules']:,} capsules at "
            f"{plan.summary['planned_utilisation_pct']:.0f}% utilisation with only "
            f"{plan.summary['changeovers']} changeovers and "
            f"{plan.summary['maintenance_events']} preventive-maintenance slots. "
            + ("All product demand is met." if not any(
                v > 0 for v in plan.summary['unmet_capsules_by_product'].values())
               else "A capacity shortfall remains — add Sunday overtime or lift OEE toward "
                    f"{plan.summary['target_oee']*100:.0f}%."),
            "",
            "Prioritised actions: (1) cut downtime on the worst Pareto machines; "
            "(2) execute preventive maintenance on high-risk machines in the planned windows; "
            "(3) lengthen product campaigns to reduce changeover losses.",
        ]
        return "\n".join(lines)
