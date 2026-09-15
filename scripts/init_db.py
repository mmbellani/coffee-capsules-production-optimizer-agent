"""Build the DuckDB warehouse from the parquet data lake.

Runs 01_raw_views.sql (views over parquet) then 02_build_aggregates.sql
(materialised aggregate/fact tables). Safe to re-run; it rebuilds tables.

Usage:  python scripts/init_db.py
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import duckdb
import config
from app.db import substitute


def run_script(con, path: Path):
    sql = substitute(path.read_text(encoding="utf-8"))
    # Split on semicolons at statement boundaries (naive but fine for our SQL).
    statements = [s.strip() for s in sql.split(";\n") if s.strip()]
    # Set COFFEE_PROFILE_SQL=1 to print a per-statement timing breakdown (used
    # to identify which table build dominates build time -- e.g. this is how
    # we found that fact_downtime_episode's gaps-and-islands window pass and
    # agg_machine_hour's grouped scan were the two heaviest statements, well
    # ahead of agg_machine_day/agg_line_product_day/fact_changeover_episode).
    # Left off by default so it never perturbs timed/cold builds.
    profile = os.environ.get("COFFEE_PROFILE_SQL") == "1"
    for stmt in statements:
        if profile:
            t0 = time.time()
            con.execute(stmt)
            first_line = stmt.splitlines()[0][:70]
            print(f"      [{time.time() - t0:6.3f}s] {first_line}")
        else:
            con.execute(stmt)


def main():
    print(f"Data lake : {config.DATA_DIR}")
    print(f"Warehouse : {config.DB_PATH}")
    if not config.DATA_DIR.exists():
        raise SystemExit(f"ERROR: data dir not found: {config.DATA_DIR}")

    con = duckdb.connect(str(config.DB_PATH))
    # Profiling (PRAGMA enable_profiling='json' per statement, see notes below)
    # showed the two heaviest statements -- agg_machine_hour's grouped scan and
    # fact_downtime_episode's gaps-and-islands window pass -- were both CPU
    # (sort/hash) bound rather than I/O bound, yet the build only used 4 of the
    # available cores. Scaling threads to all available cores (with insertion
    # order preservation relaxed, since these are unordered aggregate/fact
    # tables) lets DuckDB parallelize the parquet scan, window sorts, and hash
    # aggregates across all cores -- the single highest-leverage change found.
    n_threads = os.cpu_count() or 4
    con.execute(f"PRAGMA threads={n_threads}")
    con.execute("PRAGMA preserve_insertion_order=false")

    for name in ["01_raw_views.sql", "02_build_aggregates.sql"]:
        path = config.SQL_DIR / name
        t0 = time.time()
        print(f"-> running {name} ...")
        run_script(con, path)
        print(f"   done in {time.time() - t0:5.1f}s")

    print("\nTables built:")
    rows = con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='main' AND table_type='BASE TABLE' ORDER BY table_name"
    ).fetchall()
    for (t,) in rows:
        cnt = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"   {t:28s} {cnt:>12,} rows")

    con.close()
    print("\nWarehouse ready. Launch UI with:  streamlit run app/dashboard.py")


if __name__ == "__main__":
    main()
