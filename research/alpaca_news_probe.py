"""Probe Alpaca news in depth: how the date filter works, how late stories get edited,
how many symbols a story carries, how often content exists, and whether time-of-day
headlines land where they should in New York time.

Prints aggregates and a few headlines only. It never prints the keys.

Usage: python research/alpaca_news_probe.py
"""
import statistics
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alpaca_check import get  # noqa: E402  (loads .env the same way)


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def nth_sunday(year, month, n):
    d = datetime(year, month, 1, tzinfo=timezone.utc)
    d += timedelta(days=(6 - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def to_new_york(t):
    """UTC -> New York wall time (US rules since 2007), without needing tzdata on Windows."""
    start = nth_sunday(t.year, 3, 2) + timedelta(hours=7)   # 2:00 EST
    end = nth_sunday(t.year, 11, 1) + timedelta(hours=6)    # 2:00 EDT
    return t + timedelta(hours=-4 if start <= t < end else -5)


def fetch_all(symbol, start, end, max_pages=40):
    items, token = [], None
    for _ in range(max_pages):
        params = dict(symbols=symbol, start=start, end=end, limit=50, include_content="true", sort="asc")
        if token:
            params["page_token"] = token
        status, body, _ = get("/v1beta1/news", **params)
        if status != 200:
            print(f"HTTP {status}: {body}")
            break
        items += body.get("news", [])
        token = body.get("next_page_token")
        if not token:
            break
    return items


def describe(label, symbol, start, end):
    items = fetch_all(symbol, start, end)
    s, e = parse(start), parse(end)
    print(f"\n== {label}: {len(items)} stories for {symbol}, window {start} .. {end}")
    if not items:
        return items
    created = [parse(n["created_at"]) for n in items]
    updated = [parse(n["updated_at"]) for n in items]
    print(f"   created inside window {sum(s <= c <= e for c in created)}, before it {sum(c < s for c in created)}"
          f" | updated inside window {sum(s <= u <= e for u in updated)}")
    lags = [(u - c).total_seconds() / 3600 for c, u in zip(created, updated)]
    q = statistics.quantiles(lags, n=100) if len(lags) > 1 else lags
    print(f"   edit lag (hours): median {statistics.median(lags):.2f}, p90 {q[89]:.1f}, p99 {q[98]:.1f}, max {max(lags):.1f}"
          f" | edited at all {sum(x > 0 for x in lags)}, >15 min {sum(x > 0.25 for x in lags)},"
          f" >1 day {sum(x > 24 for x in lags)}, >30 days {sum(x > 720 for x in lags)}")
    nsym = Counter(min(len(n["symbols"]), 6) for n in items)
    print(f"   symbols per story: 1={nsym[1]}, 2={nsym[2]}, 3-5={nsym[3] + nsym[4] + nsym[5]}, 6+={nsym[6]}")
    with_content = [n for n in items if n.get("content")]
    lengths = [len(n["content"]) for n in with_content]
    print(f"   content on {len(with_content)} of {len(items)}; median length {statistics.median(lengths) if lengths else 0:.0f} chars"
          f" | summary on {sum(bool(n.get('summary')) for n in items)}"
          f" | sources {Counter(n.get('source', '') for n in items).most_common(3)}")
    late = sorted(zip(lags, items), key=lambda p: -p[0])[:3]
    for lag, n in late:
        print(f"   latest edit: +{lag:.0f}h  created {n['created_at']}  updated {n['updated_at']}  {n['headline'][:70]}")
    return items


def anchors(items):
    windows = {"pre-market": (4, 9.5), "mid-day": (11, 14), "after-hours": (16, 20)}
    hits = {k: [] for k in windows}
    for n in items:
        h = n["headline"].lower()
        for key in windows:
            if key in h or key.replace("-", " ") in h:
                ny = to_new_york(parse(n["created_at"]))
                hits[key].append((ny, n["headline"]))
    print("\n== timestamp anchors (created_at in New York time)")
    for key, (lo, hi) in windows.items():
        rows = hits[key]
        inside = sum(lo <= ny.hour + ny.minute / 60 <= hi for ny, _ in rows)
        print(f"   {key}: {inside} of {len(rows)} inside {lo}:00-{int(hi)}:{'30' if hi % 1 else '00'}")
        for ny, head in rows[:3]:
            print(f"      {ny:%Y-%m-%d %H:%M}  {head[:70]}")


def main():
    all_items = []
    all_items += describe("Narrow window, 1 day", "AAPL", "2016-01-05T00:00:00Z", "2016-01-05T23:59:59Z")
    all_items += describe("Jan 2015", "AAPL", "2015-01-01T00:00:00Z", "2015-01-31T23:59:59Z")
    all_items += describe("Jun 2018", "AAPL", "2018-06-01T00:00:00Z", "2018-06-30T23:59:59Z")
    all_items += describe("Mar 2020", "JPM", "2020-03-01T00:00:00Z", "2020-03-31T23:59:59Z")
    all_items += describe("Sep 2026", "MSFT", "2026-09-01T00:00:00Z", "2026-09-30T23:59:59Z")
    anchors(all_items)


if __name__ == "__main__":
    main()
