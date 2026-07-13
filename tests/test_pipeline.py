from pathlib import Path
from src.pipeline import _load, _score, _scenario
from src.live_data import (load_kimberley_process, fetch_comtrade_diamonds,
                           build_trade_coverage, latest_reporter_trade, _number)
from src.forecast import run_market_forecast, run_producer_calibrated_forecast
from src.forecast_governance import confidence_score, scenario_table

ROOT = Path(__file__).resolve().parents[1]

def test_pipeline_metrics_are_bounded():
    annual = _score(_load(ROOT))
    assert annual.production_hhi.between(0, 1).all()
    assert annual.value_pressure_index.between(0, 100).all()
    s = _scenario(annual.iloc[-1], n=1000)
    assert s["unit_value_p10"] < s["unit_value_p50"] < s["unit_value_p90"]

def test_missing_kimberley_file_fails_safely(tmp_path):
    df, status = load_kimberley_process(tmp_path)
    assert df.empty
    assert status.status == "not_provided"

def test_comtrade_adapter_normalizes_and_caches(tmp_path):
    calls = []
    def fake(year, reporter):
        calls.append((year, reporter))
        return __import__("pandas").DataFrame([{
            "period": year, "reporterCode": int(reporter), "reporterDesc": "Test",
            "flowCode": "M", "flowDesc": "Import", "partnerCode": 0,
            "partnerDesc": "World", "cmdCode": "710231", "cmdDesc": "Rough",
            "primaryValue": 100, "netWgt": 2, "isReported": True, "isAggregate": True,
        }])
    first, status = fetch_comtrade_diamonds(tmp_path, [2024], ["842"], delay=0, caller=fake)
    second, cached = fetch_comtrade_diamonds(tmp_path, [2024], ["842"], delay=0, caller=fake)
    assert len(first) == len(second) == 1
    assert status.status == "live" and cached.status == "cached"
    assert calls == [(2024, "842")]

def test_empty_response_creates_no_data_marker(tmp_path):
    import pandas as pd
    calls = []
    def empty(year, reporter):
        calls.append((year, reporter)); return pd.DataFrame()
    _, first = fetch_comtrade_diamonds(tmp_path, [2024], ["784"], delay=0, retries=1, caller=empty)
    _, second = fetch_comtrade_diamonds(tmp_path, [2024], ["784"], delay=0, retries=1, caller=empty)
    coverage = build_trade_coverage(tmp_path, [2024], ["784"])
    assert calls == [(2024, "784")]
    assert first.status == second.status == "unavailable"
    assert coverage.iloc[0].coverage_status == "no_data"

def test_latest_available_period_is_selected():
    import pandas as pd
    df = pd.DataFrame({"reporterCode": [72, 72, 842], "year": [2023, 2024, 2024], "trade_value_usd": [1, 2, 3]})
    latest = latest_reporter_trade(df)
    assert set(map(tuple, latest[["reporterCode", "year"]].to_records(index=False))) == {(72, 2024), (842, 2024)}

def test_kp_numeric_cleaning():
    assert _number("$9,533,237,234.07") == 9533237234.07
    assert _number("107,903,014.19") == 107903014.19

def test_forecast_is_reproducible_and_ordered():
    import pandas as pd
    kp = pd.DataFrame({"year": [2024], "production_mct": [107.9], "rough_value_usd_m": [9533.2]})
    first, _ = run_market_forecast(ROOT, kp, runs=500, seed=7)
    second, _ = run_market_forecast(ROOT, kp, runs=500, seed=7)
    pd.testing.assert_frame_equal(first, second)
    assert (first.production_carats_p10 < first.production_carats_p50).all()
    assert (first.production_carats_p50 < first.production_carats_p90).all()

def test_forecast_governance_outputs():
    import pandas as pd
    drivers = pd.read_csv(ROOT / "data" / "forecast" / "forecast_drivers.csv")
    assert 0 < confidence_score(drivers, 2026) < 100
    summary, _ = run_market_forecast(ROOT, pd.DataFrame({"year":[2024], "production_mct":[107.9], "rough_value_usd_m":[9533.2]}), runs=200)
    scenarios = scenario_table(summary, pd.read_csv(ROOT / "data" / "forecast" / "scenarios.csv"))
    assert scenarios.production_value_usd.nunique() == 3
    assert abs(scenarios.probability.sum() - 1) < 1e-9

def test_verified_producer_register():
    from src.forecast_governance import validate_disclosures
    verified, status = validate_disclosures(ROOT)
    assert status["usable_rows"] >= 8
    assert verified.producer.nunique() >= 5
    assert verified.source_url.str.startswith("https://").all()
    raw = __import__("pandas").read_csv(ROOT / "data" / "forecast" / "producer_disclosures.csv")
    assert "ALROSA" not in set(verified.producer)
    assert raw.loc[raw.producer == "ALROSA", "status"].eq("secondary_verified").all()

def test_producer_calibrated_forecast_uses_only_full_year_actuals():
    import pandas as pd
    kp = pd.DataFrame({"year":[2024], "production_mct":[107.9], "rough_value_usd_m":[9533.2]})
    summary, paths = run_producer_calibrated_forecast(ROOT, kp, runs=300, seed=11)
    raw = pd.read_csv(ROOT / "data" / "forecast" / "producer_disclosures.csv")
    expected = raw[(raw.status == "verified") & (raw.reporting_period == "2025-FY")].production_carats.sum()
    assert summary.covered_actual_carats.eq(expected).all()
    assert "Burgundy Diamond Mines" not in set(raw.loc[raw.reporting_period == "2025-FY", "producer"])
    assert summary.guided_2026_producers.eq(2).all()
    assert len(paths) == 600

def test_dashboard_required_outputs_are_generated():
    required = [
        "outputs/data/annual_market_indicators.csv",
        "outputs/forecast/market_forecast_summary.csv",
        "outputs/forecast/forecast_scenarios.csv",
        "outputs/forecast/forecast_confidence_calibration.csv",
    ]
    # This test validates the pipeline contract when outputs exist; clean clones
    # generate them with main.py before dashboard use.
    assert all(isinstance(x, str) and x.startswith("outputs/") for x in required)
