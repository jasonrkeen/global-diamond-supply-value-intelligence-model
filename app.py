from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent


def read_csv(relative: str) -> pd.DataFrame:
    path = ROOT / relative
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


st.set_page_config(page_title="Diamond Supply Intelligence", page_icon="💎", layout="wide")
st.title("Global Diamond Supply & Value Intelligence")
st.caption("Official actuals → preliminary estimate → producer-calibrated forecast")

annual = read_csv("outputs/data/annual_market_indicators.csv")
forecast = read_csv("outputs/forecast/market_forecast_summary.csv")
coverage = read_csv("outputs/data/comtrade_coverage_matrix.csv")
trade = read_csv("outputs/data/latest_reporter_trade.csv")
scenarios = read_csv("outputs/forecast/forecast_scenarios.csv")
sensitivity = read_csv("outputs/forecast/forecast_driver_sensitivity.csv")
disclosures = read_csv("outputs/forecast/verified_producer_disclosures.csv")
limitations = read_csv("outputs/forecast/disclosure_limitations.csv")
calibration = read_csv("outputs/forecast/forecast_confidence_calibration.csv")

if annual.empty:
    st.error("Run `python main.py` before launching the dashboard.")
    st.stop()

latest = annual.sort_values("year").iloc[-1]
f26 = forecast.loc[forecast.year == 2026].iloc[0] if not forecast.empty else None
confidence = float(calibration.iloc[-1].calibrated_confidence_score) if not calibration.empty else 0
c1, c2, c3, c4 = st.columns(4)
c1.metric("Official production", f"{latest.production_mct:.1f}M ct", f"{int(latest.year)} KP actual")
c2.metric("Value pressure", f"{latest.value_pressure_index:.1f}/100")
c3.metric("2026 median production", f"{f26.production_carats_p50/1e6:.1f}M ct" if f26 is not None else "N/A")
c4.metric("Forecast confidence", f"{confidence:.1f}/100")

tab1, tab2, tab3, tab4 = st.tabs(["Supply & Forecast", "Trade", "Scenarios", "Governance"])

with tab1:
    st.subheader("Production path")
    if f26 is not None:
        fy = forecast.year.astype(int).tolist(); actual_year = int(latest.year)
        years = [actual_year] + fy
        median = [latest.production_mct] + (forecast.production_carats_p50/1e6).tolist()
        low = [latest.production_mct] + (forecast.production_carats_p10/1e6).tolist()
        high = [latest.production_mct] + (forecast.production_carats_p90/1e6).tolist()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=years, y=high, mode="lines", line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=years, y=low, mode="lines", fill="tonexty", name="P10–P90", line=dict(width=0)))
        fig.add_trace(go.Scatter(x=years, y=median, mode="lines+markers", name="Actual / median"))
        fig.update_layout(yaxis_title="Million carats", xaxis_title="Year")
        st.plotly_chart(fig, width="stretch")
        display = forecast.copy()
        display["P10 (Mct)"] = display.production_carats_p10/1e6
        display["Median (Mct)"] = display.production_carats_p50/1e6
        display["P90 (Mct)"] = display.production_carats_p90/1e6
        st.dataframe(display[["year","classification","P10 (Mct)","Median (Mct)","P90 (Mct)","actual_coverage_share"]], hide_index=True, width="stretch")

with tab2:
    st.subheader("UN Comtrade coverage and latest available flows")
    if not coverage.empty:
        counts = coverage.groupby(["year","coverage_status"]).size().reset_index(name="combinations")
        st.plotly_chart(px.bar(counts, x="year", y="combinations", color="coverage_status", barmode="stack"), width="stretch")
    if not trade.empty:
        trade["trade_value_usd"] = pd.to_numeric(trade.trade_value_usd, errors="coerce").fillna(0)
        reporter = "reporterDesc" if "reporterDesc" in trade else "reporterCode"
        flows = trade.groupby([reporter,"flowDesc"], dropna=False).trade_value_usd.sum().reset_index()
        flows["trade_value_usd_m"] = flows.trade_value_usd/1e6
        st.plotly_chart(px.bar(flows, x="trade_value_usd_m", y=reporter, color="flowDesc", orientation="h", barmode="group"), width="stretch")

with tab3:
    st.subheader("Named 2026 scenarios")
    if not scenarios.empty:
        view = scenarios.copy(); view["Production (Mct)"] = view.production_carats/1e6
        view["Value (USD bn)"] = view.production_value_usd/1e9
        st.plotly_chart(px.scatter(view, x="Production (Mct)", y="unit_value_usd_per_carat", size="probability", color="scenario", hover_data=["interpretation"]), width="stretch")
        st.dataframe(view[["scenario","probability","Production (Mct)","unit_value_usd_per_carat","Value (USD bn)","interpretation"]], hide_index=True, width="stretch")

with tab4:
    st.subheader("Forecast explainability")
    st.progress(min(confidence/100, 1.0), text=f"Calibrated confidence: {confidence:.1f}/100")
    if not sensitivity.empty:
        sens = sensitivity.sort_values("one_sigma_value_usd_effect")
        st.plotly_chart(px.bar(sens, x="one_sigma_value_usd_effect", y="driver", color="confidence", orientation="h", title="One-sigma modeled value impact"), width="stretch")
    st.subheader("Verified producer disclosures")
    st.dataframe(disclosures, hide_index=True, width="stretch") if not disclosures.empty else st.info("No verified disclosures loaded.")
    st.subheader("Known disclosure limitations")
    st.dataframe(limitations, hide_index=True, width="stretch") if not limitations.empty else st.info("No limitations register found.")

st.divider()
st.caption("Research and scenario-analysis tool. Aggregate unit values are not gemological appraisals or directly tradable spot prices.")

