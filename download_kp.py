"""Download the official Kimberley Process annual global-summary PDF."""
from pathlib import Path
import os
from urllib.request import Request, urlopen
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
url = os.getenv("KP_GLOBAL_SUMMARY_URL", "").strip()
if not url:
    raise SystemExit("Set KP_GLOBAL_SUMMARY_URL in .env")
target = ROOT / "data" / "external" / "kimberley_process_global_summary.pdf"
target.parent.mkdir(parents=True, exist_ok=True)
request = Request(url, headers={"User-Agent": "diamond-supply-research/1.0"})
with urlopen(request, timeout=60) as response:
    content = response.read()
if not content.startswith(b"%PDF"):
    raise SystemExit("The downloaded response is not a PDF")
target.write_bytes(content)
print(f"Saved official KP summary: {target}")

