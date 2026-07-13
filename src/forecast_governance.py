"""Explainability, confidence, scenarios, and disclosure governance."""
from pathlib import Path
import pandas as pd

CONFIDENCE_WEIGHT = {"high": 1.0, "medium": .65, "low": .35}


def confidence_score(drivers: pd.DataFrame, year: int) -> float:
    d = drivers[drivers.year == year].copy()
    if d.empty: return 0.0
    weights = d.confidence.str.lower().map(CONFIDENCE_WEIGHT).fillna(.2)
    uncertainty = (d.standard_deviation.abs() / (d.mean_change.abs() + .02)).clip(0, 3)
    score = 100 * (weights * (1 - uncertainty / 4)).mean()
    return round(float(score.clip(0, 100)), 1)


def driver_sensitivity(drivers: pd.DataFrame, year: int, production: float, unit_value: float) -> pd.DataFrame:
    rows = []
    for r in drivers[drivers.year == year].itertuples():
        scale = 1.0 if r.direction == "production" else production
        impact = r.standard_deviation * scale if r.direction == "production" else r.standard_deviation * production
        rows.append({"year": year, "driver": r.driver, "direction": r.direction,
                     "mean_change": r.mean_change, "standard_deviation": r.standard_deviation,
                     "confidence": r.confidence,
                     "one_sigma_production_carats_effect": impact if r.direction == "production" else 0,
                     "one_sigma_value_usd_effect": impact * unit_value if r.direction == "production" else impact * unit_value})
    return pd.DataFrame(rows).sort_values("one_sigma_value_usd_effect", ascending=False)


def scenario_table(summary: pd.DataFrame, scenarios: pd.DataFrame) -> pd.DataFrame:
    base = summary[summary.year == 2026].iloc[0]
    rows = []
    for s in scenarios.itertuples():
        prod = base.production_carats_p50 * (1 + s.production_adjustment)
        uv = base.unit_value_usd_per_carat_p50 * (1 + s.unit_value_adjustment)
        rows.append({"scenario": s.scenario, "probability": s.probability,
                     "production_carats": prod, "unit_value_usd_per_carat": uv,
                     "production_value_usd": prod * uv, "interpretation": s.interpretation})
    return pd.DataFrame(rows)


def validate_disclosures(root: Path) -> tuple[pd.DataFrame, dict]:
    path = root / "data" / "forecast" / "producer_disclosures.csv"
    if not path.exists(): return pd.DataFrame(), {"status": "not_provided", "usable_rows": 0}
    df = pd.read_csv(path)
    required = {"producer", "reporting_period", "source_url", "published_date", "status"}
    missing = required - set(df.columns)
    if missing: return pd.DataFrame(), {"status": "invalid", "usable_rows": 0, "missing": sorted(missing)}
    usable = df[(df.status == "verified") & df.source_url.notna() & df.published_date.notna()].copy()
    return usable, {"status": "verified" if len(usable) else "no_verified_rows", "usable_rows": len(usable)}


def write_governance_outputs(root: Path, summary: pd.DataFrame, baseline_production: float, baseline_uv: float) -> dict:
    drivers = pd.read_csv(root / "data" / "forecast" / "forecast_drivers.csv")
    scenarios = pd.read_csv(root / "data" / "forecast" / "scenarios.csv")
    out = root / "outputs" / "forecast"; out.mkdir(parents=True, exist_ok=True)
    sens = driver_sensitivity(drivers, 2026, baseline_production, baseline_uv)
    scen = scenario_table(summary, scenarios)
    disclosures, disclosure_status = validate_disclosures(root)
    sens.to_csv(out / "forecast_driver_sensitivity.csv", index=False)
    scen.to_csv(out / "forecast_scenarios.csv", index=False)
    if not disclosures.empty: disclosures.to_csv(out / "verified_producer_disclosures.csv", index=False)
    limitations_path = root / "data" / "forecast" / "disclosure_limitations.csv"
    if limitations_path.exists():
        pd.read_csv(limitations_path).to_csv(out / "disclosure_limitations.csv", index=False)
    base_confidence = confidence_score(drivers, 2026)
    verified_producers = disclosures.producer.nunique() if not disclosures.empty else 0
    disclosure_uplift = min(15.0, verified_producers * 3.0)
    calibrated_confidence = round(min(100.0, base_confidence + disclosure_uplift), 1)
    calibration = pd.DataFrame([{"base_confidence_score": base_confidence,
                                 "verified_producers": verified_producers,
                                 "disclosure_uplift": disclosure_uplift,
                                 "calibrated_confidence_score": calibrated_confidence,
                                 "method": "3 points per verified producer capped at 15; coverage proxy only"}])
    calibration.to_csv(out / "forecast_confidence_calibration.csv", index=False)
    evidence = pd.DataFrame([{
        "official_baseline_carats": baseline_production,
        "verified_full_year_2025_carats": float(disclosures.loc[disclosures.reporting_period.eq("2025-FY"), "production_carats"].sum()) if not disclosures.empty else 0,
        "verified_full_year_producers": int(disclosures.loc[disclosures.reporting_period.eq("2025-FY"), "producer"].nunique()) if not disclosures.empty else 0,
        "verified_2026_guidance_producers": int(disclosures.loc[disclosures.reporting_period.eq("2026-GUIDANCE"), "producer"].nunique()) if not disclosures.empty else 0,
        "residual_method": "Official baseline less fixed 2025 actuals; modeled change applies to uncovered residual"
    }])
    evidence.to_csv(out / "producer_calibration_bridge.csv", index=False)
    return {"forecast_confidence_score": calibrated_confidence,
            "base_confidence_score": base_confidence,
            "disclosures": disclosure_status, "sensitivity": sens, "scenarios": scen}
