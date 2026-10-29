"""Download daily bars for every S&P 500 member since 2016, raw and fully adjusted.

One Parquet file per (ticker, membership spell, adjustment), under DATA_DIR/bars/<adjustment>/.
`asof` is set inside the spell, so Alpaca resolves the ticker to the company that held it then.
Re-running skips files that already exist.

Usage: python -m data_pipeline.bars
"""
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone

import pyarrow as pa
import pyarrow.parquet as pq

from . import alpaca
from .membership import load_snapshots, spells
from .settings import DATA_DIR

START = "2016-01-01"  # Alpaca's history starts in 2016
ADJUSTMENTS = ("raw", "all")
OUT = DATA_DIR / "bars"


def spell_asof(start, end, today):
    """A date when the ticker certainly belonged to that company: the spell's last member day."""
    last = (end - timedelta(days=1)) if end else today
    return max(last, start).isoformat()


def fetch(ticker, asof, adjustment, end):
    rows = []
    for body in alpaca.pages("/v2/stocks/bars", symbols=ticker, timeframe="1Day", start=START, end=end,
                             adjustment=adjustment, asof=asof, feed="sip", limit=10000):
        rows += body.get("bars", {}).get(ticker, [])
    return rows


def save(path, ticker, asof, rows):
    table = pa.table({
        "ticker": [ticker] * len(rows),
        "asof": [asof] * len(rows),
        "t": [r["t"] for r in rows],
        "open": [r["o"] for r in rows],
        "high": [r["h"] for r in rows],
        "low": [r["l"] for r in rows],
        "close": [r["c"] for r in rows],
        "volume": [r["v"] for r in rows],
        "trades": [r.get("n") for r in rows],
        "vwap": [r.get("vw") for r in rows],
    })
    tmp = path.with_suffix(".tmp")
    pq.write_table(table, tmp)
    tmp.replace(path)


def last_complete_day():
    """Yesterday in New York. Local dates run ahead of New York (Pakistan is 9 to 10 hours ahead), and the
    free plan refuses any request that reaches into the latest 15 minutes, so never ask for today's bar."""
    new_york_today = (datetime.now(timezone.utc) - timedelta(hours=5)).date()
    return new_york_today - timedelta(days=1)


def main():
    last_day = last_complete_day()
    end = last_day.isoformat()
    jobs = []
    for ticker, runs in sorted(spells(load_snapshots(), since=date.fromisoformat(START)).items()):
        for start, stop in runs:
            asof = spell_asof(start, stop, last_day)
            for adjustment in ADJUSTMENTS:
                path = OUT / adjustment / f"{ticker.replace('/', '_')}__{asof}.parquet"
                if not path.exists():
                    jobs.append((ticker, asof, adjustment, path, start, stop))
    for adjustment in ADJUSTMENTS:
        (OUT / adjustment).mkdir(parents=True, exist_ok=True)
    print(f"{len(jobs)} downloads to do", flush=True)

    manifest = OUT / "manifest.csv"
    new_manifest = not manifest.exists()
    with open(manifest, "a", newline="", encoding="utf-8") as mf, ThreadPoolExecutor(max_workers=3) as pool:
        writer = csv.writer(mf)
        if new_manifest:
            writer.writerow(["ticker", "asof", "adjustment", "spell_start", "spell_end", "bars", "first", "last"])
        futures = {pool.submit(fetch, t, a, adj, end): (t, a, adj, p, s, e) for t, a, adj, p, s, e in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            ticker, asof, adjustment, path, start, stop = futures[fut]
            try:
                rows = fut.result()
            except Exception as exc:  # keep going; a re-run retries the missing files
                print(f"FAILED {ticker} {asof} {adjustment}: {exc}", flush=True)
                continue
            save(path, ticker, asof, rows)
            writer.writerow([ticker, asof, adjustment, start, stop or "", len(rows),
                             rows[0]["t"][:10] if rows else "", rows[-1]["t"][:10] if rows else ""])
            mf.flush()
            if i % 100 == 0:
                print(f"{i}/{len(jobs)} done", flush=True)
    print("bars: finished", flush=True)


if __name__ == "__main__":
    main()
