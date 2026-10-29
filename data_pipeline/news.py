"""Download every Alpaca (Benzinga) news story since 2015, headlines and metadata only.

One Parquet file per calendar month, under DATA_DIR/news/. Months are fetched oldest first,
three at a time. A finished month is never fetched again; the current month is always refreshed.
Timing comes from each story's own created_at/updated_at, never from the query window. A story
can appear in two months' files (Alpaca may filter by update time), so readers de-duplicate by id.

Usage: python -m data_pipeline.news [first_month YYYY-MM]
"""
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

import pyarrow as pa
import pyarrow.parquet as pq

from . import alpaca
from .settings import DATA_DIR

OUT = DATA_DIR / "news"
FIRST_MONTH = "2015-01"


def months(first, last):
    y, m = map(int, first.split("-"))
    while (y, m) <= (last.year, last.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def fetch_month(y, m):
    start = f"{y:04d}-{m:02d}-01T00:00:00Z"
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    # The free plan refuses the latest 15 minutes, so the current month stops 20 minutes ago.
    month_end = datetime(ny, nm, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
    end = min(month_end, datetime.now(timezone.utc) - timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for body in alpaca.pages("/v1beta1/news", start=start, end=end, limit=50, sort="asc", include_content="false"):
        rows += body.get("news", [])
    return rows


def save(path, rows):
    table = pa.table({
        "id": [r["id"] for r in rows],
        "created_at": [r["created_at"] for r in rows],
        "updated_at": [r["updated_at"] for r in rows],
        "headline": [r.get("headline", "") for r in rows],
        "author": [r.get("author", "") for r in rows],
        "source": [r.get("source", "") for r in rows],
        "url": [r.get("url") or "" for r in rows],
        "symbols": [r.get("symbols", []) for r in rows],
    })
    tmp = path.with_suffix(".tmp")
    pq.write_table(table, tmp)
    tmp.replace(path)


def run_month(y, m, is_current):
    path = OUT / f"{y:04d}-{m:02d}.parquet"
    if path.exists() and not is_current:
        return f"{y:04d}-{m:02d}: already done"
    started = datetime.now()
    rows = fetch_month(y, m)
    save(path, rows)
    return f"{y:04d}-{m:02d}: {len(rows)} stories in {(datetime.now() - started).seconds}s"


def main():
    first = sys.argv[1] if len(sys.argv) > 1 else FIRST_MONTH
    OUT.mkdir(parents=True, exist_ok=True)
    today = date.today()
    todo = list(months(first, today))
    print(f"{len(todo)} months from {first} to {today:%Y-%m}", flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(run_month, y, m, (y, m) == (today.year, today.month)) for y, m in todo]
        for fut in futures:  # report in month order
            try:
                print(fut.result(), flush=True)
            except Exception as exc:  # a re-run retries the missing months
                print(f"FAILED: {exc}", flush=True)
    print("news: finished", flush=True)


if __name__ == "__main__":
    main()
