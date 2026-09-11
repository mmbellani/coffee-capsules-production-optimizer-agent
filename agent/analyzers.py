"""Inefficiency analyzers: turn warehouse data into ranked, quantified findings."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from agent.tools import Toolbox


@dataclass
class Finding:
    id: str
    area: str                    # Availability | Performance | Quality | Energy | Maintenance | Changeover | Bottleneck
    severity: str                # HIGH | MEDIUM | LOW
    scope: str                   # line / machine id or 'plant'
    title: str
    detail: str
    impact_capsules: float = 0.0
    impact_eur: float = 0.0
    recommendation: str = ""
    evidence: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["impact_capsules"] = round(self.impact_capsules)
        d["impact_eur"] = round(self.impact_eur)
        return d


def _sev(eur: float) -> str:
    if eur >= 150_000:
        return "HIGH"
    if eur >= 40_000:
        return "MEDIUM"
    return "LOW"


def diagnose(tb: Toolbox | None = None) -> list[Finding]:
    """Run the full inefficiency diagnosis and return ranked findings."""
    tb = tb or Toolbox()
    findings: list[Finding] = []
    margin = config.CAPSULE_MARGIN_EUR
    scrap = config.MATERIAL_COST_EUR_PER_CAPSULE

    # ---- 1) OEE loss waterfall per line (availability/performance/quality) ----
    eff = tb.line_efficiency()
    for _, r in eff.iterrows():
        line = r["line_id"]
        findings.append(Finding(
            id=f"avail-{line}", area="Availability", severity=_sev(r["availability_loss"] * margin),
            scope=line,
            title=f"{line}: {r['availability_loss']/1e6:.1f}M capsules lost to downtime & changeovers",
            detail=(f"Availability {r['availability']*100:.1f}% at the filler. "
                    f"{r['down_min']:,} down min + {r['changeover_min']:,} changeover min "
                    f"cost {r['availability_loss']/1e6:.1f}M capsules of entitlement."),
            impact_capsules=r["availability_loss"], impact_eur=r["availability_loss"] * margin,
            recommendation="Attack top downtime drivers (see Pareto) and cut changeover time via "
                           "product sequencing; target availability >= 95%.",
            evidence={"availability": round(r["availability"], 4),
                      "down_min": int(r["down_min"]), "changeover_min": int(r["changeover_min"])}))
        if r["performance"] < 0.98:
            findings.append(Finding(
                id=f"perf-{line}", area="Performance", severity=_sev(r["performance_loss"] * margin),
                scope=line,
                title=f"{line}: {r['performance_loss']/1e6:.1f}M capsules lost to speed losses",
                detail=(f"Performance {r['performance']*100:.1f}% - minor stops / slow cycles "
                        f"below nominal {r['ideal_rate']:.0f} cps/min."),
                impact_capsules=r["performance_loss"], impact_eur=max(r["performance_loss"], 0) * margin,
                recommendation="Investigate micro-stops and rate throttling on the filler; "
                               "tune infeed buffering.",
                evidence={"performance": round(r["performance"], 4)}))
        findings.append(Finding(
            id=f"qual-{line}", area="Quality", severity=_sev(r["quality_loss"] * (margin + scrap)),
            scope=line,
            title=f"{line}: {r['quality_loss']/1e6:.2f}M rejected capsules",
            detail=f"Quality {r['quality']*100:.2f}% - rejects scrap material and lose margin.",
            impact_capsules=r["quality_loss"], impact_eur=r["quality_loss"] * (margin + scrap),
            recommendation="Correlate rejects with degradation (wear-driven); tighten seal/fill control.",
            evidence={"quality": round(r["quality"], 4), "reject": int(r["reject"])}))

    # ---- 2) Downtime Pareto (top unplanned-stop machines) ----
    par = tb.run_named_query("05_downtime_pareto").head(5)
    for _, r in par.iterrows():
        lost = r["down_min"]
        findings.append(Finding(
            id=f"downtime-{r['machine_id']}", area="Availability", severity=_sev(lost * 20),
            scope=r["machine_id"],
            title=f"{r['machine_name']} drives {r['pct_of_total']:.0f}% of plant downtime",
            detail=(f"{int(r['episodes'])} stops, {int(r['down_min']):,} min "
                    f"(avg {r['avg_episode_min']:.0f} min, worst {int(r['longest_episode_min'])} min)."),
            impact_capsules=0.0, impact_eur=lost * 20,
            recommendation="Root-cause the recurring failure mode; add condition monitoring / spares.",
            evidence={"episodes": int(r["episodes"]), "down_min": int(r["down_min"]),
                      "cumulative_pct": float(r["cumulative_pct"])}))

    # ---- 3) Bottleneck stations ----
    bn = tb.run_named_query("18_bottleneck_analysis")
    freq = bn["bottleneck_machine"].value_counts()
    for machine_id, days in freq.head(3).items():
        findings.append(Finding(
            id=f"bottleneck-{machine_id}", area="Bottleneck",
            severity="MEDIUM" if days > 60 else "LOW", scope=machine_id,
            title=f"{machine_id} is the line constraint on {int(days)} days",
            detail="Lowest running-time-normalised throughput in its line on these days.",
            recommendation="Rebalance the line: increase this station's rate or buffer around it "
                           "so it stops starving downstream machines.",
            evidence={"days_as_bottleneck": int(days)}))

    # ---- 4) Energy intensity outliers ----
    ep = tb.run_named_query("12_energy_by_product")
    worst = ep.iloc[0]
    findings.append(Finding(
        id="energy-product", area="Energy", severity="MEDIUM",
        scope="plant",
        title=f"{worst['product_code']} is the most energy-intensive product "
              f"({worst['wh_per_capsule']:.1f} Wh/capsule)",
        detail="Energy per capsule varies by product; the highest is a decarbonisation & cost target.",
        impact_eur=float(ep["energy_cost_eur"].sum() * 0.05),
        recommendation="Batch energy-intensive products during off-peak tariff windows and review "
                       "roaster/grinder setpoints for that blend.",
        evidence=ep.set_index("product_code")["wh_per_capsule"].round(2).to_dict()))

    # ---- 5) Predictive maintenance (high-risk machines) ----
    pm = tb.maintenance_candidates(config.MAINTENANCE_RISK_THRESHOLD)
    for _, r in pm.head(6).iterrows():
        findings.append(Finding(
            id=f"maint-{r['machine_id']}", area="Maintenance",
            severity="HIGH" if r["risk_score"] >= 70 else "MEDIUM", scope=r["machine_id"],
            title=f"{r['machine_name']} at maintenance risk {r['risk_score']:.0f}/100",
            detail=(f"Current degradation {r['current_degradation']:.2f}, "
                    f"peak vibration {r['peak_vibration_14d']:.1f} mm/s, "
                    f"{int(r['days_overdue'])} days past scheduled service."),
            recommendation="Schedule preventive maintenance in the plan's next low-demand window "
                           "before failure; verify bearings/seals.",
            evidence={"risk_score": float(r["risk_score"]),
                      "degradation_slope_per_day": float(r["degradation_slope_per_day"]),
                      "days_overdue": int(r["days_overdue"])}))

    # ---- 6) Changeover waste ----
    co = tb.run_named_query("16_changeover_analysis")
    if not co.empty:
        by_line = co.groupby("line_id")["total_lost_min"].sum()
        for line, mins in by_line.items():
            findings.append(Finding(
                id=f"changeover-{line}", area="Changeover",
                severity="MEDIUM" if mins > 3000 else "LOW", scope=line,
                title=f"{line}: {mins/60:.0f} h lost to product changeovers",
                detail="Frequent product switching erodes available production time.",
                impact_eur=float(mins * 20),
                recommendation="Run longer campaigns per product and sequence transitions to "
                               "minimise cumulative changeover time.",
                evidence={"total_lost_min": int(mins)}))

    findings.sort(key=lambda f: f.impact_eur, reverse=True)
    return findings


def summarise(findings: list[Finding]) -> dict:
    by_area: dict[str, float] = {}
    for f in findings:
        by_area[f.area] = by_area.get(f.area, 0.0) + f.impact_eur
    return {
        "total_impact_eur": round(sum(f.impact_eur for f in findings)),
        "total_impact_capsules": round(sum(f.impact_capsules for f in findings)),
        "impact_by_area_eur": {k: round(v) for k, v in
                               sorted(by_area.items(), key=lambda x: -x[1])},
        "high_severity": sum(1 for f in findings if f.severity == "HIGH"),
        "n_findings": len(findings),
    }
