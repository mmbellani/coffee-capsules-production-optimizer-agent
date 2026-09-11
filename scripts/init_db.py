"""Build the DuckDB warehouse from the parquet data lake.

Runs 01_raw_views.sql (views over parquet) then 02_build_aggregates.sql
(materialised aggregate/fact tables). Safe to re-run; it rebuilds tables.

Usage:  python scripts/init_db.py
"""
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
    for stmt in statements:
        con.execute(stmt)


def main():
    print(f"Data lake : {config.DATA_DIR}")
    print(f"Warehouse : {config.DB_PATH}")
    if not config.DATA_DIR.exists():
        raise SystemExit(f"ERROR: data dir not found: {config.DATA_DIR}")

    con = duckdb.connect(str(config.DB_PATH))
    con.execute("PRAGMA threads=4")

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
