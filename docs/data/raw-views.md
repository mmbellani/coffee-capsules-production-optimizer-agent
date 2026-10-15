# Raw Views

Defined in `sql/01_raw_views.sql`. These are **views**, not tables — DuckDB reads the
Parquet files on demand, so nothing is duplicated.

| View | Description |
|---|---|
| `raw_sensor` | Minute-level sensor readings per machine |
| `dim_machine` | Machine master data |
| `dim_product` | Product master data |
| `raw_schedule` | Production schedule |

```sql
-- example: readings for one machine
SELECT *
FROM raw_sensor
WHERE machine_id = '<machine_id>'
LIMIT 100;
```
