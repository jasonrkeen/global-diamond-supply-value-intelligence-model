"""Preliminary 2025 estimate and probabilistic 2026 diamond-market forecast."""
from pathlib import Path
import json
import numpy as np
import pandas as pd


def _baseline(kp: pd.DataFrame) -> tuple[int, float, float]:
    year = int(pd.to_numeric(kp.year).max())
    latest = kp[pd.to_numeric(kp.year) == year]
    carats = float(latest.production_mct.sum() * 1_000_000)
    value = float(latest.rough_value_usd_m.sum() * 1_000_000)
    if carats <= 0 or value <= 0:
        raise ValueError("Official baseline production and value must be positive")
    return year, carats, value / carats


def run_market_forecast(root: Path, kp: pd.DataFrame, runs: int = 10000, seed: int = 2026) -> tuple[pd.DataFrame, pd.DataFrame]:
    drivers = pd.read_csv(root / "data" / "forecast" / "forecast_drivers.csv")
    base_year, carats, unit_value = _baseline(kp)
    rng = np.random.default_rng(seed)
    paths = []
    current_carats = np.full(runs, carats); current_uv = np.full(runs, unit_value)
    for year in [2025, 2026]:
        subset = drivers[drivers.year == year]
        prod_change = np.zeros(runs); value_change = np.zeros(runs)
        for row in subset.itertuples():
            shock = rng.normal(row.mean_change, row.standard_deviation, runs)
            if row.direction == "production": prod_change += shock
            else: value_change += shock
        current_carats = np.maximum(current_carats * (1 + prod_change), 1)
        current_uv = np.maximum(current_uv * (1 + value_change), 1)
        total_value = current_carats * current_uv
        for i in range(runs):
            paths.append((i, year, current_carats[i], current_uv[i], total_value[i]))
    paths = pd.DataFrame(paths, columns=["run", "year", "production_carats", "unit_value_usd_per_carat", "production_value_usd"])
    summaries = []
    for year, g in paths.groupby("year"):
        row = {"year": year, "classification": "preliminary_estimate" if year == 2025 else "forecast",
               "baseline_year": base_year, "runs": runs, "seed": seed}
        for field in ["production_carats", "unit_value_usd_per_carat", "production_value_usd"]:
            p10, p50, p90 = np.percentile(g[field], [10, 50, 90])
            row.update({f"{field}_p10": p10, f"{field}_p50": p50, f"{field}_p90": p90})
        summaries.append(row)
    return pd.DataFrame(summaries), paths


def write_forecast_outputs(root: Path, kp: pd.DataFrame) -> pd.DataFrame:
    summary, paths = run_producer_calibrated_forecast(root, kp)
    out = root / "outputs" / "forecast"; out.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out / "market_forecast_summary.csv", index=False)
    paths.to_csv(out / "market_forecast_simulations.csv.gz", index=False, compression="gzip")
    metadata = {"observed_through": int(pd.to_numeric(kp.year).max()), "forecast_version": "1.0",
                "replacement_rule": "Replace 2025 estimate when official KP 2025 actual is available",
                "warning": "Forecasts are model outputs, not observed prices, appraisals, or investment advice"}
    (out / "forecast_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return summary


def run_producer_calibrated_forecast(root: Path, kp: pd.DataFrame, runs: int = 10000, seed: int = 2026) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Forecast with fixed full-year actuals and sampled verified guidance.

    The remaining market is a residual bridge, not a claim that uncovered
    producers behaved uniformly. Interim and secondary-verified rows are excluded.
    """
    drivers = pd.read_csv(root / "data" / "forecast" / "forecast_drivers.csv")
    disclosures = pd.read_csv(root / "data" / "forecast" / "producer_disclosures.csv")
    base_year, global_carats, base_uv = _baseline(kp)
    actuals = disclosures[(disclosures.status == "verified") &
                          (disclosures.reporting_period == "2025-FY") &
                          disclosures.production_carats.notna()].copy()
    guidance = disclosures[(disclosures.status == "verified") &
                            (disclosures.reporting_period == "2026-GUIDANCE") &
                            disclosures.production_guidance_low.notna() &
                            disclosures.production_guidance_high.notna()].copy()
    covered_2025 = float(actuals.production_carats.sum())
    if covered_2025 <= 0 or covered_2025 >= global_carats:
        return run_market_forecast(root, kp, runs, seed)
    rng = np.random.default_rng(seed)
    d25 = drivers[drivers.year == 2025]
    residual_change = np.zeros(runs)
    for r in d25[d25.direction == "production"].itertuples():
        residual_change += rng.normal(r.mean_change, r.standard_deviation, runs)
    # Conservative bridge: covered actuals are fixed; uncertainty applies to the
    # portion of the official baseline not represented by those disclosures.
    residual_base = max(global_carats - covered_2025, 1)
    production_2025 = covered_2025 + np.maximum(residual_base * (1 + residual_change), 1)
    uv_change_25 = np.zeros(runs)
    for r in d25[d25.direction == "unit_value"].itertuples():
        uv_change_25 += rng.normal(r.mean_change, r.standard_deviation, runs)
    uv_2025 = np.maximum(base_uv * (1 + uv_change_25), 1)
    guided_2026 = np.zeros(runs)
    for r in guidance.itertuples():
        guided_2026 += rng.uniform(r.production_guidance_low, r.production_guidance_high, runs)
    guided_producers = set(guidance.producer)
    guided_actual_2025 = float(actuals[actuals.producer.isin(guided_producers)].production_carats.sum())
    nonguided_2025 = np.maximum(production_2025 - guided_actual_2025, 1)
    d26 = drivers[drivers.year == 2026]
    other_change = np.zeros(runs)
    for r in d26[d26.direction == "production"].itertuples():
        other_change += rng.normal(r.mean_change, r.standard_deviation, runs)
    production_2026 = guided_2026 + np.maximum(nonguided_2025 * (1 + other_change), 1)
    uv_change_26 = np.zeros(runs)
    for r in d26[d26.direction == "unit_value"].itertuples():
        uv_change_26 += rng.normal(r.mean_change, r.standard_deviation, runs)
    uv_2026 = np.maximum(uv_2025 * (1 + uv_change_26), 1)
    frames = []
    for year, prod, uv in [(2025, production_2025, uv_2025), (2026, production_2026, uv_2026)]:
        frames.append(pd.DataFrame({"run": np.arange(runs), "year": year,
            "production_carats": prod, "unit_value_usd_per_carat": uv,
            "production_value_usd": prod * uv, "covered_2025_actual_carats": covered_2025,
            "guided_2026_producer_count": len(guidance)}))
    paths = pd.concat(frames, ignore_index=True)
    summaries = []
    for year, g in paths.groupby("year"):
        row = {"year": year, "classification": "producer_calibrated_estimate" if year == 2025 else "producer_calibrated_forecast",
               "baseline_year": base_year, "runs": runs, "seed": seed,
               "covered_actual_carats": covered_2025, "actual_coverage_share": covered_2025/global_carats,
               "guided_2026_producers": len(guidance)}
        for field in ["production_carats", "unit_value_usd_per_carat", "production_value_usd"]:
            p10, p50, p90 = np.percentile(g[field], [10, 50, 90]); row.update({f"{field}_p10":p10,f"{field}_p50":p50,f"{field}_p90":p90})
        summaries.append(row)
    return pd.DataFrame(summaries), paths
