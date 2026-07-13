# Data Dictionary

## Core production outputs

| Field | Unit | Meaning |
|---|---:|---|
| `production_mct` | million carats | Aggregate rough-diamond production |
| `rough_value_usd_m` | USD millions | Aggregate reported production value |
| `unit_value_usd_per_carat` | USD/carat | Aggregate value divided by carats; mix-sensitive proxy |
| `production_hhi` | 0-1 | Sum of squared producer-country shares |
| `value_pressure_index` | 0-100 | Transparent composite analytical signal |

## Forecast summary

| Field | Meaning |
|---|---|
| `classification` | Estimate/forecast evidence label |
| `production_carats_p10/p50/p90` | Production percentiles from simulated paths |
| `unit_value_usd_per_carat_p10/p50/p90` | Aggregate unit-value percentiles |
| `production_value_usd_p10/p50/p90` | Production times unit-value percentiles |
| `covered_actual_carats` | Fixed verified full-year 2025 producer production |
| `actual_coverage_share` | Covered actuals divided by official baseline production |
| `guided_2026_producers` | Count of verified producers with sampled guidance |

## Comtrade fields

| Field | Meaning |
|---|---|
| `reporterCode`, `reporterDesc` | Reporting economy |
| `partnerCode`, `partnerDesc` | Trade partner; World is used in the default workflow |
| `cmdCode`, `cmdDesc` | HS diamond subheading and description |
| `flowCode`, `flowDesc` | Import or export |
| `trade_value_usd` | Comtrade primary value |
| `net_weight_kg` | Reported net weight where available |
| `isReported`, `isAggregate` | Comtrade record-quality flags |

## Source status

| Status | Meaning |
|---|---|
| `live` | Retrieved during the current run |
| `cached` | Reused from a prior successful retrieval |
| `partial` | Some requests succeeded and technical failures remain |
| `no_data` | Successful request returned no observations |
| `local_official_pdf` | Parsed official KP PDF |
| `invalid` | Source exists but failed validation |
| `not_provided` | Optional source was not supplied |

