"""Agent toolbox: structured, read-only access to the DuckDB warehouse.

Every tool returns plain Python / pandas objects so both the deterministic
engine and an optional LLM (via function-calling) can use them. TOOL_SPECS
exposes JSON-schema definitions for LLM function calling.
"""
from __future__ import annotations
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import config
from app import db


class Toolbox:
    """A thin, safe facade over the warehouse used by the agent."""

    # -- discovery -------------------------------------------------------
    def list_named_queries(self) -> list[dict]:
        return [{"id": v["id"], "title": v["title"], "category": v["category"],
                 "description": v["description"]} for v in db.registry().values()]

    def run_named_query(self, query_id: str) -> pd.DataFrame:
        return db.run_query(query_id)

    def run_sql(self, sql: str) -> pd.DataFrame:
        """Run read-only SQL against the warehouse."""
        lowered = sql.strip().lower()
        if any(lowered.startswith(k) for k in
               ("insert", "update", "delete", "drop", "create", "alter", "attach")):
            raise ValueError("Only read-only SELECT queries are allowed.")
        return db.run_sql(sql)

    def machines(self) -> pd.DataFrame:
        return db.dim_machine()

    # -- derived analytics used by the analyzers/planner -----------------
    def line_efficiency(self) -> pd.DataFrame:
        """OEE loss waterfall per line at the capsule-defining machine
        (doser_filler): entitlement vs actual with availability/performance/
        quality losses in capsules."""
        return self.run_sql(
            """
            WITH f AS (
                SELECT d.line_id, d.machine_id,
                       SUM(d.running_min)                         AS running_min,
                       SUM(d.down_min)                            AS down_min,
                       SUM(d.changeover_min)                      AS changeover_min,
                       SUM(d.good_units)                          AS good,
                       SUM(d.reject_units)                        AS reject,
                       ANY_VALUE(m.nominal_throughput_units_min)  AS ideal_rate
                FROM agg_machine_day d
                JOIN dim_machine m USING (machine_id)
                WHERE m.machine_type = 'doser_filler'
                GROUP BY d.line_id, d.machine_id
            )
            SELECT line_id, machine_id, ideal_rate,
                   running_min, down_min, changeover_min, good, reject,
                   (running_min + down_min + changeover_min) * ideal_rate      AS entitlement,
                   (down_min + changeover_min) * ideal_rate                    AS availability_loss,
                   running_min * ideal_rate - (good + reject)                  AS performance_loss,
                   reject                                                      AS quality_loss,
                   good                                                        AS actual_good,
                   running_min::DOUBLE / NULLIF(running_min+down_min+changeover_min,0) AS availability,
                   LEAST(1.0,(good+reject)::DOUBLE/NULLIF(running_min*ideal_rate,0))    AS performance,
                   good::DOUBLE / NULLIF(good+reject,0)                        AS quality
            FROM f ORDER BY line_id
            """)

    def line_daily_capacity(self) -> pd.DataFrame:
        """Observed effective capsules/day per line (median over real
        production days) plus the maximum achieved - the realistic and
        stretch capacities used for planning."""
        return self.run_sql(
            """
            WITH d AS (
                SELECT d.line_id, d.day, SUM(d.good_units) AS good
                FROM agg_machine_day d JOIN dim_machine m USING (machine_id)
                WHERE m.machine_type='doser_filler' AND d.running_min > 600
                GROUP BY d.line_id, d.day
            )
            SELECT line_id,
                   ROUND(MEDIAN(good))                    AS median_daily_capsules,
                   ROUND(QUANTILE_CONT(good, 0.9))        AS p90_daily_capsules,
                   MAX(good)                              AS max_daily_capsules,
                   COUNT(*)                               AS production_days
            FROM d GROUP BY line_id ORDER BY line_id
            """)

    def product_demand_baseline(self) -> pd.DataFrame:
        """Last-year true capsule output split by product (uses filling-stage
        product shares applied to the real filler capsule totals)."""
        return self.run_sql(
            """
            WITH shares AS (
                SELECT product_code, SUM(good_units) AS g
                FROM agg_line_product_day GROUP BY product_code
            ),
            tot AS (SELECT SUM(g) AS t FROM shares),
            capsules AS (
                SELECT SUM(d.good_units) AS total_true
                FROM agg_machine_day d JOIN dim_machine m USING (machine_id)
                WHERE m.machine_type='doser_filler'
            )
            SELECT s.product_code,
                   ROUND(s.g::DOUBLE / t.t, 4)                       AS share,
                   ROUND(c.total_true * s.g::DOUBLE / t.t)           AS annual_capsules
            FROM shares s, tot t, capsules c
            ORDER BY annual_capsules DESC
            """)

    def maintenance_candidates(self, threshold: float) -> pd.DataFrame:
        pm = db.run_query("13_predictive_maintenance")
        return pm[pm["risk_score"] >= threshold].copy()


# JSON-schema tool specs for optional LLM function-calling.
TOOL_SPECS = [
    {"type": "function", "function": {
        "name": "run_named_query",
        "description": "Run one of the pre-built analytics queries by id and return rows.",
        "parameters": {"type": "object",
                       "properties": {"query_id": {"type": "string"}},
                       "required": ["query_id"]}}},
    {"type": "function", "function": {
        "name": "run_sql",
        "description": "Run a read-only SELECT against the warehouse (views: raw_sensor, "
                       "dim_machine, dim_product, raw_schedule; tables: agg_machine_hour, "
                       "agg_machine_day, agg_line_product_day, fact_downtime_episode, "
                       "fact_changeover_episode).",
        "parameters": {"type": "object",
                       "properties": {"sql": {"type": "string"}},
                       "required": ["sql"]}}},
    {"type": "function", "function": {
        "name": "line_efficiency",
        "description": "OEE loss waterfall per line (availability/performance/quality losses "
                       "in capsules) at the capsule-defining machine.",
        "parameters": {"type": "object", "properties": {}}}},
]
