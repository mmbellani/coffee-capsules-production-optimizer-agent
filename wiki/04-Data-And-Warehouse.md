# 04 — Data & Warehouse

## The Parquet data lake (input)

The raw dataset is **external** to this repo (default location
`../coffee_capsule_dataset`). It models a plant with **3 lines × 17 machines =
51 machine IDs** streaming sensor data every minute for a full year.

| File | Rows | Description |
|------|------|-------------|
| `machine_metadata.parquet` | 51 | One row per machine — static attributes (type, location, ratings, maintenance dates) |
| `product_reference.parquet` | 3 | Product master (STRONG / MILD / DECAF: intensity, roast, grind, fill weight) |
| `line_schedule.parquet` | 1,576,800 | Per-line, per-minute scheduled product / running / changeover |
| `timeseries/<machine_id>.parquet` | 525,600 each | One sensor time series per machine (51 files) |

Total ≈ **26.8M** time-series rows (~1.4 GB). Machines are typed by role; the
most important is **`doser_filler`** — the capsule-defining station used to
anchor OEE and output.

## Layer 1 — Raw views ([sql/01_raw_views.sql](../sql/01_raw_views.sql))

These create DuckDB **views** directly over the Parquet files — *no data is
copied*. Placeholders like `{TS_GLOB}` are substituted from `config.py` at build
time.

| View | Source | Purpose |
|------|--------|---------|
| `raw_sensor` | `timeseries/*.parquet` | The full 1-minute sensor stream (rpm, temperature, vibration, power, throughput, good/reject counts, degradation index, …) |
| `dim_machine` | `machine_metadata.parquet` | Machine master data |
| `dim_product` | `product_reference.parquet` | Product master data |
| `raw_schedule` | `line_schedule.parquet` | Planned campaigns & changeovers |

## Layer 2 — Aggregates & facts ([sql/02_build_aggregates.sql](../sql/02_build_aggregates.sql))

Heavy one-time roll-ups materialised into compact **tables** so every downstream
query is fast:

| Table | Grain | Notes |
|-------|-------|-------|
| `agg_machine_hour` | machine × hour | Hourly sensor/production roll-up |
| `agg_machine_day` | machine × day | Daily running/down/changeover minutes, good/reject units, energy |
| `agg_line_product_day` | line × product × day | Output split by product |
| `fact_downtime_episode` | one row per stop | Built with a **gaps-and-islands** window pass |
| `fact_changeover_episode` | one row per switch | Product-transition episodes |

The downtime/changeover facts use the classic *gaps-and-islands* SQL pattern to
collapse consecutive same-state minutes into discrete episodes with start/end and
duration.

## The build script ([scripts/init_db.py](../scripts/init_db.py))

Runs the two SQL scripts in order and prints per-table row counts. Notable
details:

- **Parallelism** — sets `PRAGMA threads` to all available cores and
  `preserve_insertion_order=false`, because the two heaviest statements
  (`agg_machine_hour`'s grouped scan and `fact_downtime_episode`'s window pass)
  are CPU-bound sort/hash work. This is the single highest-leverage build speedup.
- **Profiling** — set `COFFEE_PROFILE_SQL=1` to print a per-statement timing
  breakdown when tuning the build.
- **Idempotent** — safe to re-run; it rebuilds the tables.

## The access layer ([app/db.py](../app/db.py))

The one place that talks to DuckDB. Responsibilities:

- `connect()` — open the warehouse (read-only for queries) and set `PRAGMA threads=4`.
- `substitute()` — replace `{TOKEN}` placeholders using `config.SQL_SUBSTITUTIONS`.
- `registry()` — discover every file in `sql/analytics/`, parse its header
  comments (`-- title:`, `-- category:`, `-- description:`) into metadata, and
  cache the result. This is how new queries auto-appear in the dashboard and to
  the agent — just drop a `.sql` file in the folder.
- `run_query(id)` / `run_sql(sql)` — execute a named query or ad-hoc read-only SQL.

Next: [05 — Analytics Query Library](05-Analytics-Queries.md).
