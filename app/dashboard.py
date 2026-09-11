"""Coffee Capsule Business Insight - interactive Streamlit dashboard."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import plotly.express as px
import streamlit as st

import config
from app import db

st.set_page_config(page_title="Coffee Capsule BI", page_icon="☕", layout="wide")


@st.cache_data(show_spinner=False)
def q(query_id: str) -> pd.DataFrame:
    return db.run_query(query_id)


@st.cache_data(show_spinner=False)
def machines() -> pd.DataFrame:
    return db.dim_machine()


def apply_filters(df: pd.DataFrame, lines, date_range, products=None) -> pd.DataFrame:
    out = df
    if "line_id" in out.columns and lines:
        out = out[out["line_id"].isin(lines)]
    if products is not None and "product_code" in out.columns and products:
        out = out[out["product_code"].isin(products)]
    date_col = next((c for c in ("day", "hour_ts", "start_ts") if c in out.columns), None)
    if date_col and date_range:
        d = pd.to_datetime(out[date_col])
        lo, hi = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]) + pd.Timedelta(days=1)
        out = out[(d >= lo) & (d < hi)]
    return out


# --------------------------------------------------------------------------- #
# Guard: warehouse must exist
# --------------------------------------------------------------------------- #
if not config.DB_PATH.exists():
    st.error(f"Warehouse not found at {config.DB_PATH}.\n\n"
             "Build it first:  `python scripts/init_db.py`")
    st.stop()

reg = db.registry()
dim = machines()
all_lines = sorted(dim["line_id"].unique().tolist())
oee_line = q("03_oee_line_day")
min_day, max_day = oee_line["day"].min(), oee_line["day"].max()

# --------------------------------------------------------------------------- #
# Sidebar filters
# --------------------------------------------------------------------------- #
st.sidebar.title("☕ Coffee Capsule BI")
st.sidebar.caption("Synthetic plant · 3 lines · 51 machines · 1-min sensors")
sel_lines = st.sidebar.multiselect("Production line", all_lines, default=all_lines)
sel_range = st.sidebar.date_input("Date range", value=(min_day, max_day),
                                  min_value=min_day, max_value=max_day)
if isinstance(sel_range, (list, tuple)) and len(sel_range) == 2:
    date_range = sel_range
else:
    date_range = (min_day, max_day)
sel_products = st.sidebar.multiselect("Product", ["STRONG", "MILD", "DECAF"],
                                      default=["STRONG", "MILD", "DECAF"])
st.sidebar.markdown("---")
st.sidebar.caption(f"Energy price: €{config.ENERGY_PRICE_EUR_PER_KWH}/kWh · "
                   f"Vibration alarm: {config.VIBRATION_ALARM_MM_S} mm/s")

# --------------------------------------------------------------------------- #
# Header KPIs
# --------------------------------------------------------------------------- #
st.title("Coffee Capsule — Business Insight")
kpi = q("01_kpi_summary").iloc[0]
c = st.columns(6)
c[0].metric("OEE", f"{kpi['oee_pct']:.1f}%")
c[1].metric("Availability", f"{kpi['availability_pct']:.1f}%")
c[2].metric("Performance", f"{kpi['performance_pct']:.1f}%")
c[3].metric("Quality", f"{kpi['quality_pct']:.1f}%")
c[4].metric("Capsules produced", f"{kpi['total_capsules']/1e6:.1f} M")
c[5].metric("Energy cost", f"€{kpi['total_energy_cost_eur']/1000:,.0f} k")
c2 = st.columns(6)
c2[0].metric("Downtime", f"{kpi['total_downtime_hours']:,.0f} h")
c2[1].metric("Downtime events", f"{int(kpi['downtime_events']):,}")
c2[2].metric("Energy", f"{kpi['total_energy_kwh']/1000:,.0f} MWh")

tabs = st.tabs(["📈 Overview", "⚙️ OEE & Performance", "🔧 Reliability & Downtime",
                "✅ Quality & Output", "⚡ Energy & Cost", "🩺 Predictive Maintenance",
                "🗂 Machine Explorer", "🧮 SQL Explorer", "🤖 Agent"])

# ---- Overview ----
with tabs[0]:
    st.subheader("Rolling 7-day OEE trend")
    roll = apply_filters(q("04_rolling_oee_trend"), sel_lines, date_range)
    fig = px.line(roll, x="day", y="oee_7d_avg", color="line_id",
                  labels={"oee_7d_avg": "OEE (7d avg)"})
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("State utilization by machine")
        util = apply_filters(q("07_state_utilization"), sel_lines, None)
        melt = util.melt(id_vars=["machine_id"],
                         value_vars=["running_pct", "idle_pct", "down_pct",
                                     "maintenance_pct", "changeover_pct"],
                         var_name="state", value_name="pct")
        fig = px.bar(melt, x="machine_id", y="pct", color="state", barmode="stack")
        fig.update_xaxes(tickangle=-60)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Utilization heatmap (hour × weekday)")
        hm = apply_filters(q("08_utilization_heatmap"), sel_lines, None)
        pivot = hm.groupby(["weekday", "hour_of_day"])["running_pct"].mean().reset_index()
        fig = px.density_heatmap(pivot, x="hour_of_day", y="weekday", z="running_pct",
                                 color_continuous_scale="Viridis", nbinsx=24)
        st.plotly_chart(fig, use_container_width=True)

# ---- OEE & Performance ----
with tabs[1]:
    st.subheader("OEE by line (daily)")
    ol = apply_filters(oee_line, sel_lines, date_range)
    fig = px.line(ol, x="day", y="oee", color="line_id")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Average OEE components by machine")
    om = apply_filters(q("02_oee_machine_day"), sel_lines, date_range)
    agg = om.groupby(["machine_id", "line_id"], as_index=False)[
        ["availability", "performance", "quality", "oee"]].mean()
    fig = px.bar(agg.sort_values("oee"), x="oee", y="machine_id", color="line_id",
                 orientation="h", height=700)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Bottleneck frequency by machine")
    bn = apply_filters(q("18_bottleneck_analysis"), sel_lines, date_range)
    freq = bn["bottleneck_machine"].value_counts().reset_index()
    freq.columns = ["machine_id", "days_as_bottleneck"]
    st.plotly_chart(px.bar(freq, x="machine_id", y="days_as_bottleneck"),
                    use_container_width=True)

# ---- Reliability & Downtime ----
with tabs[2]:
    st.subheader("Downtime Pareto")
    par = apply_filters(q("05_downtime_pareto"), sel_lines, None).head(20)
    fig = px.bar(par, x="machine_name", y="down_min", color="stage_category")
    fig.add_scatter(x=par["machine_name"], y=par["cumulative_pct"], name="cumulative %",
                    yaxis="y2", mode="lines+markers")
    fig.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0, 100],
                                  title="cumulative %"))
    fig.update_xaxes(tickangle=-60)
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("MTBF vs MTTR")
        rel = apply_filters(q("06_reliability_mtbf_mttr"), sel_lines, None)
        st.plotly_chart(px.scatter(rel, x="mttr_min", y="mtbf_min", color="line_id",
                                   size="failures", hover_name="machine_name"),
                        use_container_width=True)
    with col2:
        st.subheader("Reliability table")
        st.dataframe(rel, use_container_width=True, height=380)

# ---- Quality & Output ----
with tabs[3]:
    ty = apply_filters(q("09_throughput_yield"), sel_lines, date_range, sel_products)
    st.subheader("Daily good output by product")
    daily = ty.groupby(["day", "product_code"], as_index=False)["good_units"].sum()
    st.plotly_chart(px.area(daily, x="day", y="good_units", color="product_code"),
                    use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Yield % by product")
        yld = ty.groupby("product_code", as_index=False).apply(
            lambda g: pd.Series({"yield_pct": 100 * g["good_units"].sum()
                                 / max(g["good_units"].sum() + g["reject_units"].sum(), 1)}),
            include_groups=False)
        yld["product_code"] = ty.groupby("product_code").size().index
        st.plotly_chart(px.bar(yld, x="product_code", y="yield_pct", color="product_code"),
                        use_container_width=True)
    with col2:
        st.subheader("Worst reject offenders")
        wo = apply_filters(q("10_quality_worst_offenders"), sel_lines, None).head(15)
        st.plotly_chart(px.bar(wo, x="reject_rate_pct", y="machine_name",
                               orientation="h", color="stage_category"),
                        use_container_width=True)

    st.subheader("Changeover lost-time matrix")
    co = apply_filters(q("16_changeover_analysis"), sel_lines, None)
    st.dataframe(co, use_container_width=True)

# ---- Energy & Cost ----
with tabs[4]:
    en = apply_filters(q("11_energy_line_day"), sel_lines, date_range)
    st.subheader("Daily energy cost by line")
    st.plotly_chart(px.area(en, x="day", y="energy_cost_eur", color="line_id"),
                    use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Energy intensity (kWh / 1000 capsules)")
        st.plotly_chart(px.line(en, x="day", y="kwh_per_1000_capsules", color="line_id"),
                        use_container_width=True)
    with col2:
        st.subheader("Energy intensity by product")
        ep = q("12_energy_by_product")
        st.plotly_chart(px.bar(ep, x="product_code", y="wh_per_capsule",
                               color="product_code"), use_container_width=True)
        st.dataframe(ep, use_container_width=True)

# ---- Predictive Maintenance ----
with tabs[5]:
    st.subheader("Machine risk ranking")
    pm = apply_filters(q("13_predictive_maintenance"), sel_lines, None)
    st.plotly_chart(px.bar(pm.sort_values("risk_score", ascending=False).head(20),
                           x="risk_score", y="machine_name", orientation="h",
                           color="risk_score", color_continuous_scale="Reds"),
                    use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Vibration exceedance hours")
        ve = apply_filters(q("14_vibration_exceedance"), sel_lines, None)
        st.dataframe(ve, use_container_width=True, height=360)
    with col2:
        st.subheader("Degradation ↔ reject-rate correlation")
        corr = apply_filters(q("19_degradation_reject_corr"), sel_lines, None)
        st.plotly_chart(px.bar(corr.sort_values("corr_degradation_reject"),
                               x="corr_degradation_reject", y="machine_name",
                               orientation="h"), use_container_width=True)

    st.subheader("Temperature anomalies (rolling z-score > 3σ)")
    an = apply_filters(q("15_anomaly_zscore"), sel_lines, date_range)
    st.plotly_chart(px.scatter(an, x="hour_ts", y="zscore", color="machine_id",
                               hover_data=["avg_temp_c", "roll_mean"]),
                    use_container_width=True)

    st.subheader("Maintenance schedule")
    ms = apply_filters(q("17_maintenance_schedule"), sel_lines, None)
    st.dataframe(ms, use_container_width=True)

# ---- Machine Explorer ----
with tabs[6]:
    st.subheader("Machine master data")
    md = dim[dim["line_id"].isin(sel_lines)] if sel_lines else dim
    st.dataframe(md, use_container_width=True, height=500)

# ---- SQL Explorer ----
with tabs[7]:
    st.subheader("Run analytical SQL")
    st.caption("Pick a saved query or write your own against the warehouse "
               "(views: raw_sensor, dim_machine, dim_product, raw_schedule; "
               "tables: agg_machine_hour/day, agg_line_product_day, "
               "fact_downtime_episode, fact_changeover_episode).")
    options = {f"[{v['category']}] {v['title']}": k for k, v in reg.items()}
    pick = st.selectbox("Saved query", ["(custom)"] + list(options.keys()))
    default_sql = reg[options[pick]]["sql"] if pick != "(custom)" else \
        "SELECT machine_id, COUNT(*) rows FROM raw_sensor GROUP BY 1 LIMIT 20;"
    sql = st.text_area("SQL", value=default_sql, height=260)
    if st.button("Run", type="primary"):
        try:
            res = db.run_sql(sql)
            st.success(f"{len(res):,} rows")
            st.dataframe(res, use_container_width=True, height=400)
            st.download_button("Download CSV", res.to_csv(index=False),
                               "query_result.csv", "text/csv")
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

# ---- Agent ----
with tabs[8]:
    st.subheader("🤖 Efficiency & Production-Planning Agent")
    st.caption("The agent inspects the warehouse, diagnoses inefficiencies with € impact, "
               "and generates an optimized production plan (campaigns + maintenance).")
    ac1, ac2, ac3, ac4 = st.columns(4)
    horizon = ac1.number_input("Horizon (days)", 7, 120, config.PLAN_HORIZON_DAYS, step=7)
    growth = ac2.number_input("Demand growth ×", 0.5, 2.0, config.DEMAND_GROWTH, step=0.05)
    risk_thr = ac3.number_input("Maint. risk ≥", 0, 100, int(config.MAINTENANCE_RISK_THRESHOLD))
    run_llm = ac4.checkbox("Use LLM narrative", value=False)

    if st.button("Run agent", type="primary"):
        from agent.agent import EfficiencyAgent
        from agent.planner import PlanParams
        with st.spinner("Agent analysing sensor data and planning production..."):
            params = PlanParams(horizon_days=int(horizon), demand_growth=float(growth),
                                maintenance_risk_threshold=float(risk_thr))
            rep = EfficiencyAgent().run(params, use_llm=(None if run_llm else False))
        st.session_state["agent_report"] = rep

    rep = st.session_state.get("agent_report")
    if rep is None:
        st.info("Configure parameters and click **Run agent**.")
    else:
        d = rep.diagnosis_summary
        m = st.columns(4)
        m[0].metric("Quantified impact", f"€{d['total_impact_eur']/1e6:.2f} M/yr")
        m[1].metric("Lost capsules", f"{d['total_impact_capsules']/1e6:.1f} M")
        m[2].metric("High-severity", d["high_severity"])
        m[3].metric("Plan output", f"{rep.plan.summary['planned_capsules']/1e6:.1f} M")

        st.markdown("#### Executive summary")
        st.markdown(rep.narrative)

        cA, cB = st.columns(2)
        with cA:
            st.markdown("#### Impact by area (€/yr)")
            area = pd.DataFrame(list(d["impact_by_area_eur"].items()),
                                columns=["area", "impact_eur"])
            st.plotly_chart(px.bar(area, x="impact_eur", y="area", orientation="h"),
                            use_container_width=True)
        with cB:
            st.markdown("#### Demand fulfilment")
            ful = pd.DataFrame(list(rep.plan.summary["fulfilment_pct_by_product"].items()),
                               columns=["product", "fulfilment_pct"])
            st.plotly_chart(px.bar(ful, x="product", y="fulfilment_pct", color="product",
                                   range_y=[0, 110]), use_container_width=True)

        st.markdown("#### Findings")
        st.dataframe(pd.DataFrame(rep.findings), use_container_width=True, height=320)

        st.markdown("#### Production schedule")
        sched = rep.plan.schedule.copy()
        sched["cell"] = sched.apply(
            lambda r: r["product"] if r["state"] == "PRODUCTION" else r["state"], axis=1)
        fig = px.scatter(sched, x="date", y="line_id", color="cell",
                         symbol="state", height=280)
        fig.update_traces(marker=dict(size=12))
        fig.update_xaxes(tickangle=-60)
        st.plotly_chart(fig, use_container_width=True)

        if not rep.plan.maintenance.empty:
            st.markdown("#### Scheduled maintenance")
            st.dataframe(rep.plan.maintenance, use_container_width=True)

        with st.expander("Agent trace (plan → act → observe)"):
            for t in rep.trace:
                st.markdown(f"**{t['step']}. {t['action']}** — {t['observation']}")

        from agent import report as report_mod
        st.download_button("Download report (Markdown)",
                           report_mod.render_markdown(rep), "efficiency_report.md", "text/markdown")
        st.download_button("Download schedule (CSV)",
                           rep.plan.schedule.to_csv(index=False),
                           "production_schedule.csv", "text/csv")

    # ---- Scenario optimizer (MILP) ----
    st.divider()
    st.subheader("🎯 Scenario optimizer (MILP)")
    st.caption("A PuLP/CBC mixed-integer program decides production per line/product/day, "
               "campaign assignment, Sunday overtime, an OEE-uplift investment and off-peak "
               "energy scheduling — for your objective under constraints. The Pareto frontier "
               "is built by ε-constraint solves.")
    o1, o2, o3, o4 = st.columns(4)
    objective = o1.selectbox("Objective", ["margin", "fulfilment", "energy_cost", "balanced"])
    max_energy = o2.number_input("Max energy cost € (0=none)", 0, 500000, 0, step=5000)
    min_ful = o3.number_input("Min fulfilment %", 0, 100, 0, step=1)
    allow_ot = o4.checkbox("Allow overtime", value=True)

    if st.button("Solve MILP", type="primary"):
        from agent.optimizer import optimize, OptimizerSpec
        with st.spinner("Solving mixed-integer program + Pareto frontier..."):
            spec = OptimizerSpec(
                objective=objective, horizon_days=int(horizon), demand_growth=float(growth),
                max_energy_cost_eur=(max_energy or None),
                min_fulfilment_pct=(min_ful or None), allow_overtime=allow_ot)
            st.session_state["opt_result"] = optimize(spec)

    opt = st.session_state.get("opt_result")
    if opt is not None:
        if opt.note:
            st.warning(opt.note)
        b = opt.best
        mo = st.columns(4)
        mo[0].metric("Gross margin", f"€{b['gross_margin_eur']/1e6:.2f} M")
        mo[1].metric("Fulfilment", f"{b['fulfilment_pct']:.1f}%")
        mo[2].metric("Energy cost", f"€{b['energy_cost_eur']:,.0f}")
        mo[3].metric("Solution",
                     f"uplift {b['uplift_pct']:.0f}% · OT {b['overtime_line_days']}d · "
                     f"OP {b['offpeak_capsules']/1e6:.1f}M")

        st.markdown("#### Pareto frontier (ε-constraint MILP solves)")
        sc = opt.scenarios.copy()
        fig = px.scatter(sc, x="energy_cost_eur", y="fulfilment_pct",
                         color="gross_margin_eur", symbol="feasible",
                         color_continuous_scale="Viridis",
                         labels={"energy_cost_eur": "Energy cost €", "fulfilment_pct": "Fulfilment %"})
        par = opt.pareto
        fig.add_scatter(x=par["energy_cost_eur"], y=par["fulfilment_pct"],
                        mode="lines+markers", name="Pareto frontier",
                        line=dict(color="red", dash="dash"))
        st.plotly_chart(fig, use_container_width=True)

        cc1, cc2 = st.columns(2)
        with cc1:
            st.markdown("#### Frontier runs")
            st.dataframe(sc, use_container_width=True, height=300)
        with cc2:
            st.markdown("#### Optimal production (line × product)")
            if not opt.solution.empty:
                agg = opt.solution.groupby(["line_id", "product"], as_index=False)["capsules"].sum()
                st.plotly_chart(px.bar(agg, x="line_id", y="capsules", color="product",
                                       barmode="group"), use_container_width=True)
        st.download_button("Download frontier (CSV)", opt.scenarios.to_csv(index=False),
                           "optimizer_frontier.csv", "text/csv")
