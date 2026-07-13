"""Official-source adapters with cache-first, fail-safe behavior."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import os
import time
import pandas as pd

DIAMOND_CODES = "710210,710221,710231,710239"
REPORTER_NAMES = {
    "842": "United States", "699": "India", "56": "Belgium",
    "376": "Israel", "784": "United Arab Emirates", "72": "Botswana",
    "710": "South Africa", "124": "Canada",
}


@dataclass
class SourceResult:
    name: str
    status: str
    rows: int
    path: str | None
    message: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    wanted = ["period", "reporterCode", "reporterDesc", "flowCode", "flowDesc",
              "partnerCode", "partnerDesc", "cmdCode", "cmdDesc", "qtyUnitAbbr",
              "qty", "netWgt", "cifvalue", "fobvalue", "primaryValue",
              "isReported", "isAggregate"]
    out = df[[c for c in wanted if c in df.columns]].copy()
    out = out.rename(columns={"period": "year", "primaryValue": "trade_value_usd",
                              "netWgt": "net_weight_kg", "qtyUnitAbbr": "quantity_unit"})
    out["source"] = "UN Comtrade"
    out["retrieved_at_utc"] = _utc_now()
    return out


def _call_preview(year: int, reporter: str) -> pd.DataFrame:
    try:
        import comtradeapicall
    except ImportError as exc:
        raise RuntimeError("Install requirements.txt to enable UN Comtrade") from exc
    return comtradeapicall.previewFinalData(
        typeCode="C", freqCode="A", clCode="HS", period=str(year),
        reporterCode=reporter, cmdCode=DIAMOND_CODES, flowCode="M,X",
        partnerCode="0", partner2Code=None, customsCode=None, motCode=None,
        maxRecords=500, format_output="JSON", aggregateBy=None,
        breakdownMode="classic", countOnly=None, includeDesc=True,
    )


def fetch_comtrade_diamonds(
    root: Path, years: list[int], reporters: list[str], delay: float = 6.0,
    retries: int = 3, caller=None,
) -> tuple[pd.DataFrame, SourceResult]:
    """Fetch reporter-to-world diamond flows with granular caching.

    Each reporter-year call produces at most 8 expected rows (four HS codes by
    two flows), well under the 500-row preview ceiling. Cached calls generate no
    network traffic. HTTP 429 and transient failures use exponential backoff.
    """
    cache = root / "data" / "cache" / "comtrade"; cache.mkdir(parents=True, exist_ok=True)
    caller = caller or _call_preview
    frames, failures, no_data, live_calls, cached_calls = [], [], [], 0, 0
    for year in years:
        for reporter in reporters:
            path = cache / f"hs7102_{reporter}_{year}.csv"
            empty_marker = cache / f"hs7102_{reporter}_{year}.no_data.json"
            if path.exists():
                frames.append(pd.read_csv(path)); cached_calls += 1; continue
            if empty_marker.exists():
                no_data.append(f"{REPORTER_NAMES.get(reporter, reporter)} {year}")
                continue
            last_error = None
            for attempt in range(retries):
                try:
                    raw = caller(year, reporter)
                    if raw is None or raw.empty:
                        empty_marker.write_text(
                            '{"status":"no_data","source":"UN Comtrade preview"}', encoding="utf-8"
                        )
                        no_data.append(f"{REPORTER_NAMES.get(reporter, reporter)} {year}")
                        last_error = None
                        break
                    out = _normalize(raw); out.to_csv(path, index=False)
                    frames.append(out); live_calls += 1; last_error = None
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt < retries - 1:
                        time.sleep(delay * (2 ** attempt))
            if last_error is not None:
                failures.append(f"{REPORTER_NAMES.get(reporter, reporter)} {year}: {last_error}")
            time.sleep(delay)
    if not frames:
        detail = "; ".join(failures[:3]) or "No records returned"
        return pd.DataFrame(), SourceResult("UN Comtrade diamond flows", "unavailable", 0, None, detail)
    combined = pd.concat(frames, ignore_index=True).drop_duplicates()
    combined_path = cache / "diamond_trade_normalized.csv"
    combined.to_csv(combined_path, index=False)
    status = "partial" if failures else "live" if live_calls else "cached"
    message = f"{live_calls} live calls; {cached_calls} cached calls; {len(no_data)} no-data combinations; {len(failures)} failed calls"
    if no_data:
        message += "; no data: " + ", ".join(no_data[:4])
    if failures:
        message += "; " + "; ".join(failures[:2])
    return combined, SourceResult("UN Comtrade diamond flows", status, len(combined), str(combined_path), message)


def build_trade_coverage(root: Path, years: list[int], reporters: list[str]) -> pd.DataFrame:
    """Create an explicit requested reporter-year coverage matrix."""
    cache = root / "data" / "cache" / "comtrade"
    rows = []
    for year in years:
        for reporter in reporters:
            data_path = cache / f"hs7102_{reporter}_{year}.csv"
            marker = cache / f"hs7102_{reporter}_{year}.no_data.json"
            status, count = ("available", len(pd.read_csv(data_path))) if data_path.exists() else (("no_data", 0) if marker.exists() else ("missing", 0))
            rows.append({"year": year, "reporter_code": reporter,
                         "reporter": REPORTER_NAMES.get(reporter, reporter),
                         "coverage_status": status, "rows": count})
    return pd.DataFrame(rows)


def latest_reporter_trade(trade: pd.DataFrame) -> pd.DataFrame:
    """Retain every record from each reporter's latest available period."""
    if trade.empty or "reporterCode" not in trade:
        return pd.DataFrame()
    years = pd.to_numeric(trade["year"], errors="coerce")
    work = trade.assign(year=years).dropna(subset=["year", "reporterCode"])
    latest = work.groupby("reporterCode")["year"].transform("max")
    return work[work.year == latest].copy()


def load_kimberley_process(root: Path) -> tuple[pd.DataFrame, SourceResult]:
    pdf = root / "data" / "external" / "kimberley_process_global_summary.pdf"
    path = root / "data" / "external" / "kimberley_process_production.csv"
    if pdf.exists():
        try:
            df = parse_kimberley_pdf(pdf, int(os.getenv("KP_EXPECTED_YEAR", "2024")))
            normalized = root / "data" / "cache" / "kimberley_process_production_normalized.csv"
            normalized.parent.mkdir(parents=True, exist_ok=True); df.to_csv(normalized, index=False)
            return df, SourceResult("Kimberley Process", "local_official_pdf", len(df), str(pdf), "Official global-summary PDF parsed and reconciled")
        except Exception as exc:
            if not path.exists():
                return pd.DataFrame(), SourceResult("Kimberley Process", "invalid", 0, str(pdf), f"PDF parsing failed: {exc}")
    if not path.exists():
        return pd.DataFrame(), SourceResult("Kimberley Process", "not_provided", 0, None,
            "Download official production statistics and map them to the provided template")
    df = pd.read_csv(path)
    required = {"year", "country", "production_carats", "production_value_usd"}
    missing = required - set(df.columns)
    if missing:
        return pd.DataFrame(), SourceResult("Kimberley Process", "invalid", 0, str(path), f"Missing columns: {sorted(missing)}")
    df["production_mct"] = pd.to_numeric(df.production_carats, errors="coerce") / 1_000_000
    df["rough_value_usd_m"] = pd.to_numeric(df.production_value_usd, errors="coerce") / 1_000_000
    df = df.dropna(subset=["year", "country", "production_mct", "rough_value_usd_m"])
    return df, SourceResult("Kimberley Process", "local_official", len(df), str(path), "Official downloaded table loaded")


def _number(value) -> float:
    text = str(value or "").replace("$", "").replace(",", "").replace(" ", "")
    text = re.sub(r"[^0-9.()\-]", "", text)
    if not text or text in {"-", "."}:
        return 0.0
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    return float(text)


def parse_kimberley_pdf(path: Path, year: int) -> pd.DataFrame:
    """Parse the official Annual Global Summary table and reconcile its total."""
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError("Install pdfplumber to parse the KP global-summary PDF") from exc
    rows = []
    with pdfplumber.open(path) as doc:
        for page in doc.pages:
            for table in page.extract_tables() or []:
                for row in table or []:
                    if not row or not row[0]:
                        continue
                    cells = [str(x or "").replace("\n", " ").strip() for x in row]
                    name = cells[0]
                    if name.lower().startswith(("participant", "annual global", "production")):
                        continue
                    # Expected layout: participant + production(3), import(3), export(3), KPC(2).
                    if len(cells) < 10 or name.lower() == "totals":
                        continue
                    try:
                        nums = [_number(x) for x in cells[1:]]
                    except ValueError:
                        continue
                    if len(nums) < 9:
                        continue
                    rows.append({"year": year, "country": name,
                                 "production_carats": nums[0], "production_value_usd": nums[1],
                                 "production_usd_per_carat": nums[2],
                                 "import_carats": nums[3], "import_value_usd": nums[4],
                                 "export_carats": nums[6], "export_value_usd": nums[7],
                                 "source_url": os.getenv("KP_GLOBAL_SUMMARY_URL", ""),
                                 "source_file": path.name})
    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("No participant rows detected; use the normalized CSV template")
    df = df.drop_duplicates(["year", "country"])
    df["production_mct"] = df.production_carats / 1_000_000
    df["rough_value_usd_m"] = df.production_value_usd / 1_000_000
    positive = df[(df.production_carats > 0) | (df.production_value_usd > 0)].copy()
    if positive.empty:
        raise ValueError("No positive production observations detected")
    implied = positive.production_value_usd / positive.production_carats.replace(0, pd.NA)
    bad = (implied.notna()) & ((implied - positive.production_usd_per_carat).abs() > implied.abs().clip(lower=1) * .03)
    if bad.mean() > .10:
        raise ValueError("More than 10% of production unit values fail reconciliation")
    return positive


def write_source_register(root: Path, results: list[SourceResult]) -> None:
    out = root / "outputs" / "data"; out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{**r.__dict__, "checked_at_utc": _utc_now()} for r in results]).to_csv(out / "source_status.csv", index=False)


def live_enabled() -> bool:
    return os.getenv("DIAMOND_LIVE_DATA", "0").strip().lower() in {"1", "true", "yes"}
