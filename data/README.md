# Synthetic Coffee-Capsule Plant Sensor Dataset

Synthetic industrial IoT dataset for a coffee-capsule factory producing three
products — **STRONG**, **MILD**, **DECAF** — at **1-minute** granularity over a
**full year** (2025-09-01 → 2026-08-31, 525,600 rows per machine).

## Plant model
3 production lines (L1, L2, L3). Each line is a chain of **17 machines** that
mirrors a real single-serve capsule line, so **51 unique machine IDs** total.

| Stage | Machines (in process order) |
|-------|------------------------------|
| Roasting/grinding (upstream) | green-bean silo & destoner → drum roaster → cooler → degassing silo → roller grinder |
| Filling & sealing | capsule denester → dosing/filling → tamping → nitrogen flushing → heat sealing/lidding |
| Quality | checkweigher → vision & seal inspector → metal detector |
| Packaging (downstream) | cartoner → case packer → palletizer → stretch wrapper |

Lines run any of the 3 products via multi-hour campaigns separated by changeovers.
Operating pattern: weekday-heavy 2–3 shifts, reduced Saturdays, Sunday planned
maintenance windows, plus random unplanned downtime.

## Tables (Parquet)

| File | Rows | Description |
|------|------|-------------|
| `machine_metadata.parquet` | 51 | One row per machine — **static** info |
| `product_reference.parquet` | 3 | Product master data (intensity, roast, grind, fill weight) |
| `line_schedule.parquet` | 1,576,800 | Per-line, per-minute scheduled product / running / changeover |
| `timeseries/<machine_id>.parquet` | 525,600 each | One sensor time series per machine (51 files) |
| `dataset_manifest.parquet` | 51 | Row/size manifest of every time-series file |

Total: **~26.8M** time-series rows, **~1.4 GB**.

## `machine_metadata.parquet` columns
`machine_id`, `machine_type`, `machine_name`, `stage_category`, `line_id`,
`manufacturer`, `model`, `serial_number`, `plant_name`, `plant_hall`,
`location_zone`, `floor_x_m`, `floor_y_m`, `construction_date`,
`installation_date`, `commission_date`, `last_maintenance_date`,
`next_maintenance_date`, `maintenance_interval_days`, `criticality_class`,
`nominal_rpm`, `max_rpm`, `nominal_temperature_c`, `power_rating_kw`,
`weight_kg`, `nominal_throughput_units_min`, `firmware_version`,
`plc_ip_address`, `energy_meter_id`, `commissioning_engineer`,
`expected_life_years`.

## Time-series columns (per machine, 1-minute)
| Column | Unit / values |
|--------|---------------|
| `timestamp` | minute-resolution datetime |
| `machine_id`, `line_id`, `stage_category` | identifiers |
| `product_code` | STRONG / MILD / DECAF / NONE |
| `machine_state` | RUNNING / IDLE / CHANGEOVER / DOWN / MAINTENANCE |
| `rpm` | machine speed |
| `temperature_c` | body/process temperature |
| `vibration_mm_s` | ISO-10816 style vibration velocity |
| `motor_current_a`, `power_kw` | electrical load (3-phase 400 V) |
| `pressure_bar` | pneumatic pressure |
| `throughput_units_min` | capsules (or cartons/cases) per minute |
| `good_count`, `reject_count` | per-minute quality counts |
| `ambient_temp_c`, `humidity_pct` | environment (seasonal + diel) |
| `energy_kwh_cumulative` | running energy meter |
| `degradation_index` | 0→~1.4 health drift, resets at maintenance |
| `roast_temp_c` | roaster only (else null) |
| `grind_micron` | grinder only |
| `seal_temp_c` | heat sealer only |
| `nitrogen_flow_lpm` | nitrogen flusher only |

## Built-in realism
- Product-dependent setpoints (rpm, roast/grind, temperature offsets).
- Health **degradation** trends that raise vibration/temperature and reject rate,
  resetting after each maintenance cycle (`maintenance_interval_days`).
- Correlated line behaviour (machines on a line share campaign & running state).
- Seasonal and daily ambient temperature/humidity cycles.

Regenerate with `python generate_coffee_dataset.py` (set `QUICK=1` for a 1-day test).
