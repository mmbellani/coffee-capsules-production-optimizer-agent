# Data

The synthetic plant dataset models **3 production lines** and **51 machines**,
with **1-minute sensor readings** over **a full year** (~26.8 M rows in Parquet).

The warehouse is built in two layers:

| Layer | File | Purpose |
|---|---|---|
| Raw views | `sql/01_raw_views.sql` | Zero-copy views over Parquet |
| Aggregates & facts | `sql/02_build_aggregates.sql` | One-time heavy roll-ups into compact tables |

- [Raw Views](raw-views.md)
- [Aggregates & Fact Tables](aggregates.md)
