# Methodology

## Analytical boundary

The model examines natural rough-diamond production, aggregate production value, selected HS 7102 trade flows, producer disclosures, and forward scenarios. Industrial synthetic diamonds and retail polished-diamond valuations are not merged into the natural rough-diamond production series.

## Evidence classes

1. **Official actual:** Kimberley Process or official UN Comtrade observation.
2. **Verified producer actual:** primary company disclosure with a reporting period, publication date, and direct source URL.
3. **Preliminary estimate:** fixed verified actuals plus a modeled residual market.
4. **Forecast:** producer-guidance sampling plus probabilistic residual-market drivers.
5. **Scenario:** conditional downside, base, or upside case; not a probability forecast by itself.

## Production baseline

The preferred baseline is the Kimberley Process Annual Global Summary PDF. The parser extracts participant production, imports, exports, values, and unit values. It recalculates production dollars per carat and rejects a table if more than 10% of positive-production rows fail a 3% reconciliation tolerance.

## Trade layer

The pipeline queries annual UN Comtrade final-data previews for selected reporters, partner World, import/export flows, and HS subheadings 710210, 710221, 710231, and 710239. Successful reporter-year responses are cached. Empty successful responses receive `no_data` markers and are not interpreted as zero trade.

Reporter totals are retained separately. Bilateral flows and World totals must not be summed together.

## Value Pressure Index

The illustrative composite is:

```text
0.30 * supply tightness
+ 0.30 * demand strength
+ 0.25 * trade friction
- 0.15 * lab-grown pressure
```

The weights are transparent analytical assumptions, not statistically estimated causal coefficients.

## Producer-calibrated forecast

Verified full-year 2025 producer production is fixed. Quarterly records and secondary evidence are excluded from annual calibration. The remaining portion of the official baseline is treated as the residual market and receives modeled production shocks.

For 2026, verified producer guidance ranges are sampled directly with a uniform distribution. General production shocks apply only to producers and residual supply not represented by guidance. Unit-value drivers are simulated separately. The seeded model returns P10, P50, and P90 production, unit-value, and production-value estimates.

## Confidence score

Driver confidence and relative uncertainty determine the base score. Each distinct primary-source verified producer adds three coverage points, capped at 15. The score measures evidence coverage and assumption quality; it is not the probability that the forecast is correct.

## Known limitations

- Diamonds are heterogeneous by size, quality, color, clarity, shape, and provenance.
- Aggregate dollars per carat are mix-sensitive proxies.
- Producer fiscal years may differ from calendar years.
- Sanctions and disclosure restrictions create asymmetric evidence quality.
- Customs values can contain re-exports and reporting differences.
- The residual-market bridge assumes uncovered supply can be modeled collectively.
- The model is not an appraisal, price quotation, sanctions determination, or investment recommendation.

