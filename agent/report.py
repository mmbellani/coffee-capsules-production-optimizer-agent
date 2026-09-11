"""Render an AgentReport to markdown and persist artifacts."""
from __future__ import annotations
import json
from pathlib import Path

import pandas as pd


def render_markdown(report) -> str:
    d = report.diagnosis_summary
    plan = report.plan
    md = []
    md.append("# Coffee Capsule — Efficiency & Production-Plan Report")
    md.append(f"_Generated {report.generated_at} · "
              f"{'LLM-assisted' if report.llm_used else 'deterministic engine'}_\n")

    md.append("## Executive summary\n")
    md.append(report.narrative + "\n")

    md.append("## Quantified inefficiencies\n")
    md.append(f"- Total quantified impact: **€{d['total_impact_eur']:,}/yr** "
              f"({d['total_impact_capsules']:,} capsules of lost entitlement)")
    md.append(f"- High-severity findings: **{d['high_severity']}** of {d['n_findings']}")
    md.append("- Impact by area: " + ", ".join(
        f"{k} €{v:,}" for k, v in d["impact_by_area_eur"].items()) + "\n")

    md.append("| Sev | Area | Scope | Finding | €/yr | Recommendation |")
    md.append("|-----|------|-------|---------|------|----------------|")
    for f in report.findings[:15]:
        md.append(f"| {f['severity']} | {f['area']} | {f['scope']} | {f['title']} | "
                  f"{f['impact_eur']:,} | {f['recommendation']} |")
    md.append("")

    md.append("## Production plan\n")
    md.append(f"- Horizon: **{plan.start_date} → {plan.end_date}**")
    md.append(f"- Planned output: **{plan.summary['planned_capsules']:,} capsules** "
              f"at {plan.summary['planned_utilisation_pct']:.0f}% utilisation")
    md.append(f"- Changeovers: {plan.summary['changeovers']} · "
              f"Maintenance slots: {plan.summary['maintenance_events']}")
    md.append("- Demand fulfilment: " + ", ".join(
        f"{k} {v}%" for k, v in plan.summary["fulfilment_pct_by_product"].items()))
    md.append(f"- Line capacity (capsules/day): " + ", ".join(
        f"{k}={v:,}" for k, v in plan.capacity.items()) + "\n")

    md.append("### Planning rationale\n")
    for r in plan.rationale:
        md.append(f"- {r}")
    md.append("")

    if not plan.maintenance.empty:
        md.append("### Scheduled maintenance\n")
        md.append("| Date | Line | Machine | Risk | Action |")
        md.append("|------|------|---------|------|--------|")
        for _, m in plan.maintenance.iterrows():
            md.append(f"| {m['date']} | {m['line_id']} | {m['machine_id']} | "
                      f"{m['risk_score']:.0f} | {m['action']} |")
        md.append("")

    md.append("### Schedule (first 14 days)\n")
    piv = (plan.schedule.assign(cell=plan.schedule.apply(
        lambda r: (r["product"] or r["state"][:4]) if r["state"] != "PRODUCTION"
        else f"{r['product']}", axis=1))
        .pivot_table(index="date", columns="line_id", values="cell", aggfunc="first"))
    piv = piv.head(14)
    md.append("| Date | " + " | ".join(piv.columns) + " |")
    md.append("|------|" + "|".join(["------"] * len(piv.columns)) + "|")
    for day, row in piv.iterrows():
        md.append(f"| {day} | " + " | ".join(str(row[c]) for c in piv.columns) + " |")
    md.append("")

    if getattr(report, "optimization", None) is not None:
        md.append(render_optimizer_markdown(report.optimization))

    md.append("## Agent trace\n")
    for t in report.trace:
        md.append(f"{t['step']}. **{t['action']}** — {t['observation']}")
    md.append("")
    return "\n".join(md)


def render_optimizer_markdown(opt) -> str:
    md = ["## Scenario optimizer (MILP)\n"]
    md.append(f"- Engine: **PuLP / CBC mixed-integer program** · Objective: **{opt.spec['objective']}**"
              + (f" · energy cap €{opt.spec['max_energy_cost_eur']:,.0f}"
                 if opt.spec.get("max_energy_cost_eur") else "")
              + (f" · min fulfilment {opt.spec['min_fulfilment_pct']}%"
                 if opt.spec.get("min_fulfilment_pct") else ""))
    if opt.note:
        md.append(f"- ⚠️ {opt.note}")
    b = opt.best
    md.append(f"- **Optimal solution** [{b['solver_status']}]: OEE uplift {b['uplift_pct']}%, "
              f"{b['overtime_line_days']} overtime line-days, {b['offpeak_capsules']:,} off-peak capsules")
    md.append(f"  - Margin €{b['gross_margin_eur']:,} · Fulfilment {b['fulfilment_pct']}% · "
              f"Energy €{b['energy_cost_eur']:,} (uplift capex €{b['uplift_cost_eur']:,}, "
              f"overtime €{b['overtime_cost_eur']:,})\n")
    md.append("### Pareto frontier — ε-constraint (fulfilment ↑ vs energy cost ↓)\n")
    pcols = ["energy_cap_eur", "energy_cost_eur", "fulfilment_pct", "gross_margin_eur",
             "uplift_pct", "overtime_line_days", "feasible"]
    md.append("| " + " | ".join(pcols) + " |")
    md.append("|" + "|".join(["---"] * len(pcols)) + "|")
    for _, r in opt.scenarios[pcols].iterrows():
        md.append("| " + " | ".join(str(r[c]) for c in pcols) + " |")
    md.append("")
    return "\n".join(md)


def save(report, out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {}

    md = render_markdown(report)
    (out_dir / "efficiency_report.md").write_text(md, encoding="utf-8")
    paths["report_md"] = str(out_dir / "efficiency_report.md")

    (out_dir / "findings.json").write_text(
        json.dumps({"diagnosis_summary": report.diagnosis_summary,
                    "findings": report.findings}, indent=2), encoding="utf-8")
    paths["findings_json"] = str(out_dir / "findings.json")

    (out_dir / "production_plan.json").write_text(
        json.dumps(report.plan.as_dict(), indent=2, default=str), encoding="utf-8")
    paths["plan_json"] = str(out_dir / "production_plan.json")

    report.plan.schedule.to_csv(out_dir / "production_schedule.csv", index=False)
    report.plan.schedule.to_parquet(out_dir / "production_schedule.parquet", index=False)
    paths["schedule_csv"] = str(out_dir / "production_schedule.csv")
    paths["schedule_parquet"] = str(out_dir / "production_schedule.parquet")

    if getattr(report, "optimization", None) is not None:
        opt = report.optimization
        opt.scenarios.to_csv(out_dir / "optimizer_scenarios.csv", index=False)
        (out_dir / "optimizer_result.json").write_text(
            json.dumps(opt.as_dict(), indent=2, default=str), encoding="utf-8")
        paths["optimizer_scenarios_csv"] = str(out_dir / "optimizer_scenarios.csv")
        paths["optimizer_result_json"] = str(out_dir / "optimizer_result.json")
    return paths
