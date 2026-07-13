from pathlib import Path
import json
import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
try:
    from dotenv import load_dotenv
except ImportError:  # Keeps fallback mode runnable before optional dependency install.
    def load_dotenv(*args, **kwargs):
        return False
from .live_data import (fetch_comtrade_diamonds, load_kimberley_process,
                        write_source_register, live_enabled, build_trade_coverage,
                        latest_reporter_trade)
from .forecast import write_forecast_outputs
from .forecast_governance import write_governance_outputs
from .pdf_report import generate_pdf_report


def _load(root: Path) -> pd.DataFrame:
    df = pd.read_csv(root / "data" / "sample" / "diamond_market.csv")
    required = {"year", "country", "production_mct", "rough_value_usd_m", "trade_friction", "lab_pressure", "demand_index"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if (df[["production_mct", "rough_value_usd_m"]] < 0).any().any():
        raise ValueError("Production and value cannot be negative")
    return df


def _score(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for year, g in df.groupby("year"):
        total_p = g.production_mct.sum()
        total_v = g.rough_value_usd_m.sum()
        shares = g.production_mct / total_p
        hhi = float((shares ** 2).sum())
        avg_unit = total_v * 1_000_000 / (total_p * 1_000_000)
        friction = np.average(g.trade_friction, weights=g.production_mct)
        lab = np.average(g.lab_pressure, weights=g.production_mct)
        demand = np.average(g.demand_index, weights=g.production_mct)
        supply_tightness = np.clip((1 - total_p / df.groupby("year").production_mct.sum().max()) * 100, 0, 100)
        value_pressure = np.clip(0.30*supply_tightness + 0.30*demand + 0.25*friction - 0.15*lab, 0, 100)
        out.append({"year": year, "production_mct": total_p, "rough_value_usd_m": total_v,
                    "unit_value_usd_per_carat": avg_unit, "production_hhi": hhi,
                    "supply_tightness": supply_tightness, "demand_index": demand,
                    "trade_friction": friction, "lab_pressure": lab,
                    "value_pressure_index": value_pressure})
    return pd.DataFrame(out).sort_values("year")


def _scenario(latest: pd.Series, n: int = 5000, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    supply = rng.normal(0, 0.08, n)
    demand = rng.normal(0, 0.10, n)
    friction = rng.normal(0, 0.05, n)
    lab = rng.normal(0.03, 0.04, n)
    change = -0.55*supply + 0.65*demand + 0.25*friction - 0.45*lab
    values = latest.unit_value_usd_per_carat * (1 + change)
    p10, p50, p90 = np.percentile(values, [10, 50, 90])
    return {"runs": n, "seed": seed, "unit_value_p10": round(float(p10), 2),
            "unit_value_p50": round(float(p50), 2), "unit_value_p90": round(float(p90), 2),
            "probability_below_baseline": round(float(np.mean(values < latest.unit_value_usd_per_carat)), 4)}


def _charts(root: Path, annual: pd.DataFrame, raw: pd.DataFrame, trade: pd.DataFrame | None = None, forecast: pd.DataFrame | None = None) -> None:
    out = root / "outputs" / "charts"; out.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(9, 5)); ax.plot(annual.year, annual.production_mct, marker="o", color="#174a7e")
    ax.set(title="Global Sample Rough-Diamond Production", xlabel="Year", ylabel="Million carats")
    fig.tight_layout(); fig.savefig(out / "production_trend.png", dpi=160); plt.close(fig)
    latest = raw[raw.year == raw.year.max()].sort_values("production_mct")
    fig, ax = plt.subplots(figsize=(9, 5)); ax.barh(latest.country, latest.production_mct, color="#2f8f83")
    ax.set(title=f"Production by Country ({raw.year.max()})", xlabel="Million carats")
    fig.tight_layout(); fig.savefig(out / "country_production.png", dpi=160); plt.close(fig)
    if trade is not None and not trade.empty:
        latest = latest_reporter_trade(trade)
        latest["segment"] = latest.get("cmdCode", pd.Series(index=latest.index, dtype=str)).astype(str).map({
            "710210": "Unsorted", "710221": "Industrial rough",
            "710231": "Nonindustrial rough", "710239": "Nonindustrial worked",
        }).fillna("Other")
        latest["trade_value_usd"] = pd.to_numeric(latest.trade_value_usd, errors="coerce").fillna(0)
        reporter_col = "reporterDesc" if "reporterDesc" in latest else "reporterCode"
        pivot = latest.pivot_table(index=reporter_col, columns="segment", values="trade_value_usd", aggfunc="sum") / 1_000_000
        if not pivot.empty:
            ax = pivot.plot(kind="barh", stacked=True, figsize=(10, 6), colormap="viridis")
            ax.set(title="Latest Available Diamond Trade by Reporter and Segment", xlabel="Trade value (USD millions)", ylabel="")
            ax.legend(title="Segment", fontsize=8); ax.figure.tight_layout()
            ax.figure.savefig(out / "diamond_trade_segments.png", dpi=160); plt.close(ax.figure)
    if forecast is not None and not forecast.empty:
        actual_year = int(raw.year.max()); actual_carats = raw[raw.year == actual_year].production_mct.sum() * 1_000_000
        years = [actual_year] + forecast.year.astype(int).tolist()
        med = [actual_carats] + forecast.production_carats_p50.tolist()
        low = [actual_carats] + forecast.production_carats_p10.tolist()
        high = [actual_carats] + forecast.production_carats_p90.tolist()
        fig, ax = plt.subplots(figsize=(9, 5)); ax.plot(years, np.array(med)/1e6, marker="o", color="#7b2cbf", label="Median")
        ax.fill_between(years, np.array(low)/1e6, np.array(high)/1e6, alpha=.2, color="#7b2cbf", label="P10–P90")
        ax.set(title="Global Rough-Diamond Production: Actual, Estimate and Forecast", xlabel="Year", ylabel="Million carats")
        ax.legend(); fig.tight_layout(); fig.savefig(out / "production_forecast.png", dpi=160); plt.close(fig)


def _report(root: Path, annual: pd.DataFrame, scenario: dict, trade: pd.DataFrame | None = None, coverage: pd.DataFrame | None = None, forecast: pd.DataFrame | None = None) -> None:
    x = annual.iloc[-1]
    concentration = "high" if x.production_hhi >= .25 else "moderate" if x.production_hhi >= .15 else "low"
    trade_section = "## Official trade layer\n\nNo official UN Comtrade records were available in this run."
    if trade is not None and not trade.empty:
        latest = latest_reporter_trade(trade)
        latest["trade_value_usd"] = pd.to_numeric(latest.trade_value_usd, errors="coerce").fillna(0)
        reporter_col = "reporterDesc" if "reporterDesc" in latest else "reporterCode"
        ranked = latest.groupby(reporter_col).trade_value_usd.sum().sort_values(ascending=False)
        leader = ranked.index[0]; leader_value = ranked.iloc[0] / 1_000_000
        periods = latest.groupby(reporter_col).year.max()
        available = int((coverage.coverage_status == "available").sum()) if coverage is not None else 0
        requested = len(coverage) if coverage is not None else 0
        trade_section = f"""## Official trade layer

UN Comtrade supplied **{len(trade):,} records** across the configured reporter-year requests. Using each reporter's latest available period, **{leader}** has the largest combined monitored flow at **${leader_value:,.1f} million**. Coverage is **{available}/{requested} requested reporter-year combinations**; reporter years differ where the latest period is unavailable, so comparisons are explicitly latest-available rather than falsely synchronized.

Latest periods by reporter: {', '.join(f'{k}: {int(v)}' for k, v in periods.items())}."""
    forecast_section = ""
    if forecast is not None and not forecast.empty:
        e25 = forecast[forecast.year == 2025].iloc[0]; f26 = forecast[forecast.year == 2026].iloc[0]
        forecast_section = f"""## Preliminary estimate and forecast

The model estimates 2025 production at **{e25.production_carats_p50/1e6:.1f} million carats** (P10–P90: **{e25.production_carats_p10/1e6:.1f}–{e25.production_carats_p90/1e6:.1f} million**). This is a preliminary estimate, not an official KP actual.

The 2026 median forecast is **{f26.production_carats_p50/1e6:.1f} million carats**, with a P10–P90 range of **{f26.production_carats_p10/1e6:.1f}–{f26.production_carats_p90/1e6:.1f} million**. Median modeled unit value is **${f26.unit_value_usd_per_carat_p50:.2f}/ct** (P10–P90: **${f26.unit_value_usd_per_carat_p10:.2f}–${f26.unit_value_usd_per_carat_p90:.2f}**). Driver assumptions are transparent and should be recalibrated as producer reports arrive."""
    text = f"""# Diamond Supply and Value Intelligence Brief

## Executive assessment

The sample market produced **{x.production_mct:.1f} million carats** in {int(x.year)}, with an estimated rough value of **${x.rough_value_usd_m:,.0f} million**. Production concentration is **{concentration}** (HHI {x.production_hhi:.3f}). The model's Natural Diamond Value Pressure Index is **{x.value_pressure_index:.1f}/100**.

## Scenario range

The Monte Carlo layer produces a proxy unit-value range of **${scenario['unit_value_p10']:.2f}–${scenario['unit_value_p90']:.2f} per carat** (P10–P90), with a median of **${scenario['unit_value_p50']:.2f}**. This is a scenario estimate, not a quoted market price.

{trade_section}

{forecast_section}

## Interpretation

- Higher supply tightness, consumer demand, and trade friction increase modeled value pressure.
- Lab-grown substitution pressure reduces natural-diamond value pressure.
- Carat-level unit values are aggregate customs/production proxies; they do not control for cut, color, clarity, size, shape, or provenance.
- Results support strategic monitoring and research, not investment, sanctions-compliance, or valuation decisions.

## Data status

This release uses a clearly labeled demonstration dataset so the pipeline runs without credentials. Replace it with Kimberley Process, USGS, UN Comtrade, and producer-report observations before operational use.
"""
    (root / "outputs" / "reports").mkdir(parents=True, exist_ok=True)
    (root / "outputs" / "reports" / "diamond_intelligence_brief.md").write_text(text, encoding="utf-8")


def run_pipeline(root: Path) -> None:
    load_dotenv(root / ".env")
    demo = _load(root)
    kp, kp_status = load_kimberley_process(root)
    raw = kp.assign(
        trade_friction=25.0, lab_pressure=60.0, demand_index=50.0
    ) if not kp.empty else demo
    coverage = pd.DataFrame()
    if live_enabled():
        years = [int(x.strip()) for x in os.getenv("COMTRADE_YEARS", "2022,2023,2024").split(",") if x.strip()]
        reporters = [x.strip() for x in os.getenv("COMTRADE_REPORTERS", "842,699,56,376,784,72,710,124").split(",") if x.strip()]
        delay = float(os.getenv("COMTRADE_REQUEST_DELAY", "6"))
        trade, trade_status = fetch_comtrade_diamonds(root, years, reporters, delay=delay)
        coverage = build_trade_coverage(root, years, reporters)
    else:
        trade = pd.DataFrame()
        from .live_data import SourceResult
        trade_status = SourceResult("UN Comtrade diamond flows", "disabled", 0, None, "Set DIAMOND_LIVE_DATA=1 to enable")
    write_source_register(root, [kp_status, trade_status])
    annual = _score(raw); scenario = _scenario(annual.iloc[-1])
    forecast = write_forecast_outputs(root, kp) if not kp.empty else pd.DataFrame()
    governance = None
    if not forecast.empty:
        base_prod = kp[kp.year == kp.year.max()].production_mct.sum() * 1_000_000
        base_uv = kp[kp.year == kp.year.max()].rough_value_usd_m.sum() * 1_000_000 / base_prod
        governance = write_governance_outputs(root, forecast, base_prod, base_uv)
    (root / "outputs" / "data").mkdir(parents=True, exist_ok=True)
    annual.to_csv(root / "outputs" / "data" / "annual_market_indicators.csv", index=False)
    latest = raw[raw.year == raw.year.max()].copy()
    latest["production_share"] = latest.production_mct / latest.production_mct.sum()
    latest.to_csv(root / "outputs" / "data" / "latest_country_exposure.csv", index=False)
    if not trade.empty:
        trade.to_csv(root / "outputs" / "data" / "comtrade_hs7102_trade.csv", index=False)
        latest_reporter_trade(trade).to_csv(root / "outputs" / "data" / "latest_reporter_trade.csv", index=False)
    if not coverage.empty:
        coverage.to_csv(root / "outputs" / "data" / "comtrade_coverage_matrix.csv", index=False)
    (root / "outputs" / "data" / "monte_carlo_summary.json").write_text(json.dumps(scenario, indent=2), encoding="utf-8")
    _charts(root, annual, raw, trade, forecast); _report(root, annual, scenario, trade, coverage, forecast)
    pdf_path = generate_pdf_report(root, annual, forecast, trade, coverage, governance)
    if not forecast.empty:
        f26 = forecast[forecast.year == 2026].iloc[0]
        print(f"2026 production forecast P10/P50/P90: {f26.production_carats_p10/1e6:.1f} / {f26.production_carats_p50/1e6:.1f} / {f26.production_carats_p90/1e6:.1f} million carats")
        print(f"2026 forecast confidence score: {governance['forecast_confidence_score']:.1f}/100")
    print(f"PDF brief: {pdf_path}")
    print("Diamond intelligence pipeline completed successfully.")
    print(f"Latest value pressure index: {annual.iloc[-1].value_pressure_index:.1f}/100")
    print(f"Scenario unit-value P10/P50/P90: ${scenario['unit_value_p10']:.2f} / ${scenario['unit_value_p50']:.2f} / ${scenario['unit_value_p90']:.2f}")
    print(f"Production data: {'Kimberley Process local official file' if not kp.empty else 'demonstration fallback'}")
    print(f"UN Comtrade: {trade_status.status}")
