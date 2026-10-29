"""Check that Alpaca market data (news and daily bars) works with the keys in .env.

Answers the first M0 questions:
- Is news included on this plan?
- How far back does it go?
- Do stories have summaries and content?
- Do delisted companies have bars?
- How are daily bars timestamped?

Prints counts and field coverage only. It never prints the keys.

Usage: python research/alpaca_check.py   (from anywhere; it finds .env in the repo root)
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_env(path):
    if not path.exists():
        sys.exit(f"No {path.name} in {path.parent}. Copy .env.example to .env and fill in your keys.")
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


ENV = load_env(ROOT / ".env")
KEY = ENV.get("APCA_API_KEY_ID", "")
SECRET = ENV.get("APCA_API_SECRET_KEY", "")
DATA = ENV.get("APCA_DATA_URL", "https://data.alpaca.markets").rstrip("/")
if not KEY or not SECRET:
    sys.exit("APCA_API_KEY_ID or APCA_API_SECRET_KEY is empty in .env.")


def get(path, **params):
    url = f"{DATA}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"APCA-API-KEY-ID": KEY, "APCA-API-SECRET-KEY": SECRET})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.load(resp), resp.headers.get("X-RateLimit-Limit")
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode("utf-8", errors="replace")[:200], None


def news(label, **params):
    status, body, limit = get("/v1beta1/news", limit=50, include_content="true", **params)
    if status != 200:
        print(f"news   {label}: HTTP {status} {body}")
        return
    items = body.get("news", [])
    created = sorted(n["created_at"] for n in items)
    print(f"news   {label}: {len(items)} stories on the first page"
          f" | created {created[0] if created else '-'} .. {created[-1] if created else '-'}"
          f" | summary {sum(bool(n.get('summary')) for n in items)}"
          f" | content {sum(bool(n.get('content')) for n in items)}"
          f" | edited after publishing {sum(n['updated_at'] != n['created_at'] for n in items)}"
          f" | max symbols on one story {max((len(n['symbols']) for n in items), default=0)}"
          f" | rate limit {limit}/min")


def bars(symbol, asof):
    status, body, _ = get("/v2/stocks/bars", symbols=symbol, timeframe="1Day", start="2016-01-04",
                          end="2016-01-08", adjustment="raw", asof=asof, feed="sip")
    if status != 200:
        print(f"bars   {symbol}: HTTP {status} {body}")
        return
    rows = body.get("bars", {}).get(symbol, [])
    first = rows[0] if rows else {}
    print(f"bars   {symbol} (asof {asof}): {len(rows)} daily bars for 4 to 8 Jan 2016"
          f" | first bar stamped {first.get('t', '-')} close {first.get('c', '-')}")


def main():
    print(f"data endpoint: {DATA}\n")
    news("AAPL, Jan 2015", symbols="AAPL", start="2015-01-01", end="2015-01-31", sort="asc")
    news("AAPL, Jan 2016", symbols="AAPL", start="2016-01-01", end="2016-01-31", sort="asc")
    news("JPM, Jun 2016", symbols="JPM", start="2016-06-01", end="2016-06-30", sort="asc")
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    news("AAPL, last 7 days", symbols="AAPL", start=week_ago)
    print()
    # A company still trading, then three that left the market after 2016
    for symbol in ("AAPL", "CELG", "MON", "TWX"):
        bars(symbol, "2016-01-04")


if __name__ == "__main__":
    main()
