> This file mirrors `.github/copilot-instructions.md`; keep both in sync when either changes.

# CLAUDE.md — Global Diamond Supply and Value Intelligence Model

## Purpose
Python-based commodity intelligence model combining Kimberley Process production, UN Comtrade flows, producer disclosures, Monte Carlo forecasting, scenario analysis, and risk governance.

## Tech stack
- Python; dependencies in `requirements.txt`
- Key libraries: `pandas`, `numpy`, `matplotlib`, `pytest`, `python-dotenv`, `comtradeapicall`, `requests`, `urllib3`, `pdfplumber`, `streamlit`, `plotly`, `reportlab`

## Folder structure
- `data/` (7 files)
- `docs/` (3 files)
- `outputs/` (20 files)
- `src/` (6 files)
- `tests/` (1 files)
- `.env.example`
- `README.md`
- `app.py`
- `download_kp.py`
- `main.py`
- `requirements.txt`

## Setup, run, test
Commands documented in README.md (referenced files exist):
```bash
python -m venv .venv
pip install -r requirements.txt
python main.py
streamlit run app.py
python -m pytest -q
python download_kp.py
```
- Tests: 1 Python test file(s) under `tests/`; framework appears to be pytest. Add/update tests with any logic change.

## Conventions observed
- Functions use type hints; keep annotating new code.
- Uses `dataclasses` for structured config/results.
- Random seeds are set for reproducibility (Monte Carlo/simulation); keep seeded, deterministic runs.
- Credentials/API keys come from environment variables (see `.env.example`); never hardcode them.
- Public data sources referenced: World Bank, UN Comtrade, Kimberley.
- Write paths relative to the repo root (no absolute local paths).

## Output artifacts
- Generated outputs go to: `outputs/charts/`, `outputs/data/`, `outputs/forecast/`, `outputs/reports/`
- A PDF report is produced with `reportlab`; keep it in sync with model changes.
- Streamlit dashboard: `app.py` (run with `streamlit run <file>`).
- Charts are generated with matplotlib / plotly.

## Guardrails
- Never commit secrets, API keys, tokens, or `.env` files.
- Do not commit large raw datasets or binaries; keep data fetched or documented with its source.
- Keep analysis source-backed: cite data sources and assumptions; label scenario/forecast outputs as model estimates, not facts.
- Synthetic data must stay synthetic; never introduce real personal or sensitive records.
- Preserve reproducibility: no unseeded randomness, no hidden manual steps.
