# KPI Definitions

Standard manufacturing definitions used throughout the project. Refer to the SQL files
for the exact implementation.

## OEE

$$
\text{OEE} = \text{Availability} \times \text{Performance} \times \text{Quality}
$$

| Component | Definition |
|---|---|
| Availability | Run time ÷ planned production time |
| Performance | (Ideal cycle time × total count) ÷ run time |
| Quality | Good count ÷ total count |

## Reliability

$$
\text{MTBF} = \frac{\text{Operating time}}{\text{Number of failures}}
\qquad
\text{MTTR} = \frac{\text{Total repair time}}{\text{Number of repairs}}
$$

## Energy intensity

$$
\text{kWh per 1{,}000 capsules} = \frac{\text{kWh}}{\text{capsules produced}} \times 1000
$$

## Yield

$$
\text{Yield} = \frac{\text{Good capsules}}{\text{Total capsules}}
$$
