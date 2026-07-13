# Global Diamond Supply and Value Intelligence Model

A reproducible research pipeline for examining natural rough-diamond supply, geographic concentration, aggregate unit value, trade friction, demand conditions, lab-grown substitution pressure, and valuation uncertainty.

The project separates official observations, verified producer disclosures, preliminary estimates, probabilistic forecasts, and conditional scenarios. It is designed as transparent commodity-intelligence research rather than a diamond appraisal or investment tool.

## What it produces

- Annual supply, value, HHI concentration, and value-pressure indicators
- Latest country production exposures
- A seeded 5,000-run Monte Carlo proxy unit-value range
- Production charts and an automated intelligence brief
- Interactive Streamlit intelligence dashboard
- Producer-calibrated 2025 estimate and 2026 forecast
- Automated two-page executive PDF brief
- Explicit methodology limits around diamond heterogeneity

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Launch the interactive dashboard after the pipeline completes:

```bash
streamlit run app.py
```

The dashboard separates official observations, preliminary estimates, and forecasts; displays uncertainty bands, Comtrade coverage, named scenarios, driver sensitivity, verified producer disclosures, and known evidence limitations.

Every pipeline run also generates a two-page executive PDF brief at `output/pdf/diamond_supply_value_intelligence_brief.pdf`. It includes headline metrics, classification-aware forecast ranges, charts, coverage, governance and limitations.

Run the test suite with:

```bash
python -m pytest -q
```

## Current reference results

Using the official 2024 KP Global Summary and the bundled verified disclosure register, the current reference run produces approximately:

- 107.9 million carats of official 2024 production;
- 102.8 million carats for the producer-calibrated 2025 median estimate;
- 105.2 million carats for the 2026 median forecast;
- a 2026 P10-P90 range near 95.2-115.6 million carats; and
- a governed forecast-confidence score of 46.2/100.

Results change as sources, coverage, and assumptions are updated. Reproduce them locally rather than treating README figures as live quotations.

## Official-data mode

Copy `.env.example` to `.env`, then set `DIAMOND_LIVE_DATA=1`. The pipeline uses the official `comtradeapicall.previewFinalData()` function, which does not require an API key. It requests each reporter-year separately, with partner `World`, four diamond subheadings (`710210`, `710221`, `710231`, `710239`), and import/export flows. Each small request remains comfortably below the preview limit.

Successful reporter-year responses are cached under `data/cache/comtrade`; later runs do not request those observations again. `COMTRADE_REQUEST_DELAY` controls pacing, and transient failures receive exponential-backoff retries. A partial response remains labeled `partial` in the source register rather than being presented as complete.

An empty but successful Comtrade response is recorded with a persistent `no_data` marker and is not repeatedly requested. The pipeline writes `comtrade_coverage_matrix.csv`, selects each reporter's latest available period in `latest_reporter_trade.csv`, and generates a segmented trade-value chart. This allows incomplete official reporting to remain visible without treating absence as zero trade or a technical failure.

Kimberley Process production statistics use a controlled manual-import workflow because the public statistics interface does not provide a stable documented API. Download the official table, convert its fields to the schema in `data/external/kimberley_process_production_template.csv`, and save it as:

```text
data/external/kimberley_process_production.csv
```

For the preferred official PDF route, set `KP_GLOBAL_SUMMARY_URL` and `KP_EXPECTED_YEAR` in `.env`, then run:

```bash
python download_kp.py
python main.py
```

The downloader verifies the PDF signature. The parser extracts participant production, import, and export fields, recalculates production value per carat, rejects materially inconsistent tables, and saves a normalized cache file. If the KP changes its PDF layout, the source is marked `invalid`; use the normalized CSV template rather than silently accepting shifted columns.

When the file passes schema validation, it replaces the demonstration production series. `outputs/data/source_status.csv` records whether each layer was live, cached, locally supplied, disabled, invalid, or unavailable.

USGS industrial-diamond and gemstone publications are maintained as contextual sources rather than merged into rough gem-diamond production. Industrial synthetic volumes and prices are economically different series and would distort the natural-diamond value index if combined.

## Model logic

The value-pressure index combines supply tightness (30%), demand strength (30%), trade friction (25%), and lab-grown pressure (-15%). HHI measures country-level production concentration. Monte Carlo scenarios shock supply, demand, trade friction, and lab-grown substitution around the latest aggregate unit value.

These weights are transparent analytical assumptions, not fitted causal estimates. Sensitivity testing and expert calibration should precede decision use.

## 2025 preliminary estimate and 2026 forecast

When an official KP production baseline is available, the pipeline runs a seeded 10,000-path forecast. The 2025 layer is labeled `preliminary_estimate`; 2026 is labeled `forecast`. Production and unit-value drivers are stored in `data/forecast/forecast_drivers.csv` with source class, confidence, mean effect, volatility, and notes. Outputs include P10/P50/P90 ranges, compressed simulations, metadata, and a forecast chart.

The 2025 estimate is automatically designated for replacement when an official KP 2025 actual becomes available. Forecast assumptions are scenario inputs rather than causal estimates and must not be represented as quoted diamond prices or investment guidance.

The production path is producer-calibrated when verified disclosures are present. Full-year 2025 actuals are fixed; quarterly observations and secondary evidence are excluded. Modeled 2025 change applies only to the uncovered residual of the official 2024 baseline. Verified 2026 producer guidance is sampled directly, while generic production shocks apply to the remaining market. `producer_calibration_bridge.csv` records the covered actuals, guidance count, and residual method.

Forecast governance outputs include named downside/base/upside scenarios, a driver-sensitivity register, a confidence score, and an optional verified producer-disclosure register. Copy `producer_disclosures_template.csv` to `producer_disclosures.csv`, retain direct source URLs and publication dates, and mark a row `verified` only after checking the underlying company or government disclosure.

The bundled initial register uses primary company disclosures for De Beers, Petra Diamonds, and Lucara Diamond. Reporting periods and basis differences are preserved in notes. Each distinct verified producer adds a conservative three-point confidence uplift, capped at 15 points; this is a coverage proxy, not a statistical accuracy claim. The calibration calculation is written to `forecast_confidence_calibration.csv`.

Rio Tinto/Diavik and Burgundy/Ekati are also included where primary disclosures support the observation. Interim periods are never annualized automatically. ALROSA's 2025 target is labeled `secondary_verified` and excluded from the confidence uplift because an equivalent current primary production disclosure was not established. `disclosure_limitations.csv` makes these asymmetries explicit.

## Documentation

- [Methodology](docs/METHODOLOGY.md)
- [Data dictionary](docs/DATA_DICTIONARY.md)
- [Source register](docs/SOURCES.md)

## Data roadmap

The included CSV is a demonstration dataset assembled from rounded, illustrative market observations. It is not represented as an authoritative historical series. A production release should add source-specific adapters and provenance fields for:

- Kimberley Process production and rough-diamond trade statistics
- USGS mineral commodity summaries
- UN Comtrade HS 7102 trade flows
- Company production and inventory disclosures
- World Bank/IMF macroeconomic indicators
- Official sanctions and import-restriction notices

## Important limitation

Diamonds are not a homogeneous commodity. Aggregate dollars-per-carat can change because the mix of stones changes. It is a proxy and not a gemological appraisal or a directly tradable spot price. The project separates analytical signals from quoted prices and should not be used as investment advice.

## Repository layout

```text
app.py              Streamlit intelligence dashboard
data/external/      User-supplied official KP source
data/forecast/      Drivers, scenarios, disclosures, limitations
data/sample/        Demonstration fallback input
docs/               Methodology, dictionary, source register
src/                Ingestion, scoring, forecasts, governance, reports
tests/              Reproducibility and validation tests
output/pdf/         Generated executive PDF
outputs/            Generated charts, data, reports, forecast artifacts
download_kp.py      Controlled official KP PDF downloader
main.py             End-to-end pipeline entry point
```

## License

MIT. Verify licensing and redistribution terms for every live data source added later.
