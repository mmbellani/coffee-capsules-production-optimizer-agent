"""Central configuration for the Coffee Capsule Business Insight app."""
import os
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent

# Location of the parquet data lake produced by generate_coffee_dataset.py.
# Defaults to the sibling folder created in phase 1; override with COFFEE_DATA_DIR.
DATA_DIR = Path(os.environ.get(
    "COFFEE_DATA_DIR", REPO_DIR.parent / "coffee_capsule_dataset")).resolve()

# Persistent DuckDB warehouse built by scripts/init_db.py.
DB_PATH = Path(os.environ.get("COFFEE_DB", REPO_DIR / "coffee_bi.duckdb")).resolve()

SQL_DIR = REPO_DIR / "sql"
ANALYTICS_DIR = SQL_DIR / "analytics"

# Parquet paths (forward slashes work on all platforms inside DuckDB).
TS_GLOB = (DATA_DIR / "timeseries" / "*.parquet").as_posix()
META_PARQUET = (DATA_DIR / "machine_metadata.parquet").as_posix()
PRODUCT_PARQUET = (DATA_DIR / "product_reference.parquet").as_posix()
SCHEDULE_PARQUET = (DATA_DIR / "line_schedule.parquet").as_posix()

# Business assumptions used by the analytical queries.
ENERGY_PRICE_EUR_PER_KWH = float(os.environ.get("ENERGY_PRICE", "0.24"))
MATERIAL_COST_EUR_PER_CAPSULE = float(os.environ.get("CAPSULE_COST", "0.045"))
# Gross margin per good capsule - used to value availability/performance losses.
CAPSULE_MARGIN_EUR = float(os.environ.get("CAPSULE_MARGIN", "0.08"))
# ISO 10816 style vibration alarm threshold (mm/s RMS) used for exceedance flags.
VIBRATION_ALARM_MM_S = float(os.environ.get("VIB_ALARM", "4.5"))

# ---- Agent / production-planning parameters ----
PLAN_HORIZON_DAYS = int(os.environ.get("PLAN_HORIZON_DAYS", "28"))
DEMAND_GROWTH = float(os.environ.get("DEMAND_GROWTH", "1.05"))   # +5% vs last year
TARGET_OEE = float(os.environ.get("TARGET_OEE", "0.90"))
# Risk score (0-100) above which a machine is scheduled for maintenance in the plan.
MAINTENANCE_RISK_THRESHOLD = float(os.environ.get("MAINT_RISK_THRESHOLD", "55"))

# ---- Scenario-optimizer parameters ----
ENERGY_OFFPEAK_PRICE = float(os.environ.get("ENERGY_OFFPEAK_PRICE", "0.15"))
OVERTIME_COST_PER_LINE_DAY = float(os.environ.get("OVERTIME_COST_PER_LINE_DAY", "9000"))
CAPACITY_UPLIFT_COST_PER_POINT = float(os.environ.get("UPLIFT_COST_PER_POINT", "60000"))

SQL_SUBSTITUTIONS = {
    "TS_GLOB": TS_GLOB,
    "META_PARQUET": META_PARQUET,
    "PRODUCT_PARQUET": PRODUCT_PARQUET,
    "SCHEDULE_PARQUET": SCHEDULE_PARQUET,
    "ENERGY_PRICE": ENERGY_PRICE_EUR_PER_KWH,
    "CAPSULE_COST": MATERIAL_COST_EUR_PER_CAPSULE,
    "VIB_ALARM": VIBRATION_ALARM_MM_S,
}
