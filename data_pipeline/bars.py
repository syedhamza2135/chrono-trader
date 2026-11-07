"""Download daily bars for every company that has been an S&P 500 member since 2016, raw and fully adjusted.

The plan comes from the identity table (reference/identity.csv and reference/memberships.csv): for each company's
membership period, and each ticker the company used in it, one fetch of (ticker, asof). `asof` is a date when
Wikipedia showed that ticker for that company (the middle of the run, kept inside the membership period), so Alpaca
resolves the ticker to the right company and returns its history from 2016. A ticker that later passed to another
company (IR, CB, JCI, DLPH) therefore still fetches the right one.

A company listing two classes has one membership period per class, and each period uses only the rows of its own
class. Alpaca's histories follow a symbol rather than a class: as of 2022, UA's history is class A until 2016-12-06
and class C after, because the two classes swapped tickers that day. So a row's member days are only those inside
its own dates, but its file holds the symbol's whole history, and the bars outside the row can be another
security's (see prices.py).

Files: DATA_DIR/bars/<adjustment>/<ticker>__<asof>.parquet. DATA_DIR/bars/plan.csv lists which file covers which
member days of which company (use_from to use_to), so readers never rebuild file names. An existing file is reused
when its asof falls inside the same safe window. Re-running skips files that already exist.

Usage: python -m data_pipeline.bars
"""
import csv
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from . import alpaca
from .settings import DATA_DIR, ROOT

START = "2016-01-01"  # Alpaca's history starts in 2016
ADJUSTMENTS = ("raw", "all")
OUT = DATA_DIR / "bars"
PLAN = OUT / "plan.csv"
REFERENCE = ROOT / "reference"


def last_complete_day():
    """Yesterday in New York. Local dates run ahead of New York (Pakistan is 9 to 10 hours ahead), and the
    free plan refuses any request that reaches into the latest 15 minutes, so never ask for today's bar."""
    new_york_today = (datetime.now(timezone.utc) - timedelta(hours=5)).date()
    return new_york_today - timedelta(days=1)


def _d(value):
    return None if value is None or (isinstance(value, float) and pd.isna(value)) or value == "" else date.fromisoformat(str(value)[:10])


def existing():
    """{symbol: [asof dates with both adjustments on disk]}"""
    have = {}
    for adj in ADJUSTMENTS:
        for p in (OUT / adj).glob("*__*.parquet"):
            sym, asof = p.stem.rsplit("__", 1)
            have.setdefault(adj, set()).add((sym, asof))
    both = have.get("raw", set()) & have.get("all", set())
    out = {}
    for sym, asof in both:
        out.setdefault(sym, []).append(date.fromisoformat(asof))
    return out


def spell_class(rows, ticker, start, end):
    """The share class a membership period is about: the class whose rows carry the period's ticker for most of
    it. The membership file's UA period (from 2016-04-08) is class C, since UA meant class A only until 2016-12-06.
    None if no row carries the ticker."""
    days = Counter()
    for r in rows[rows.symbol == ticker].itertuples():
        a, b = max(start, _d(r.valid_from)), min(end, _d(r.valid_to) or end)
        days[r.share_class] += max((b - a).days + 1, 0)
    return days.most_common(1)[0][0] if days else None


def plan(last_day):
    """Rows of (entity_id, symbol, share_class, asof, use_from, use_to): which file serves which member days."""
    ident = pd.read_csv(REFERENCE / "identity.csv", dtype=str).fillna("")
    members = pd.read_csv(REFERENCE / "memberships.csv", dtype=str)
    have = existing()
    start_all = date.fromisoformat(START)
    rows = []
    for m in members.itertuples():
        a0 = max(_d(m.member_from), start_all)
        b0 = (_d(m.member_to) - timedelta(days=1)) if _d(m.member_to) else last_day
        if b0 < a0:
            continue
        mine = ident[ident.entity_id == m.entity_id]
        if mine.share_class.nunique() > 1:
            k = spell_class(mine, m.source_ticker, _d(m.member_from), _d(m.member_to) or last_day)
            if k is None:
                print(f"plan: no {m.source_ticker} row for {m.entity_id}; its period from {m.member_from} uses every class")
            else:
                mine = mine[mine.share_class == k]
        for r in mine.itertuples():
            vf, vt = _d(r.valid_from), _d(r.valid_to) or last_day
            a, b = max(a0, vf), min(b0, vt)
            if a > b:
                continue
            first, last = _d(r.first_seen), _d(r.last_seen)
            # Near an approximate rename date, stay inside the run Wikipedia saw; an exact end is safe as it is.
            safe_lo = a if r.dated_by != "approximate (first revision showing it)" else max(a, first)
            safe_hi = b if r.dated_to != "approximate" else min(b, last)
            if safe_lo > safe_hi:
                safe_lo = safe_hi = min(max(first + (last - first) / 2, a), b)
            reuse = [x for x in have.get(r.symbol, []) if safe_lo <= x <= safe_hi]
            asof = max(reuse) if reuse else safe_lo + (safe_hi - safe_lo) / 2
            rows.append({"entity_id": m.entity_id, "symbol": r.symbol, "share_class": r.share_class, "asof": asof.isoformat(),
                         "use_from": a.isoformat(), "use_to": b.isoformat(), "reused": bool(reuse)})
    return pd.DataFrame(rows).drop_duplicates()


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


def main():
    last_day = last_complete_day()
    end = last_day.isoformat()
    p = plan(last_day)
    p.to_csv(PLAN, index=False)
    jobs = []
    for sym, asof in sorted(set(zip(p.symbol, p["asof"]))):  # p.asof would be DataFrame.asof
        for adjustment in ADJUSTMENTS:
            path = OUT / adjustment / f"{sym.replace('/', '_')}__{asof}.parquet"
            if not path.exists():
                jobs.append((sym, asof, adjustment, path))
    for adjustment in ADJUSTMENTS:
        (OUT / adjustment).mkdir(parents=True, exist_ok=True)
    print(f"plan: {len(p)} rows for {p.entity_id.nunique()} companies; {int(p.reused.sum())} reuse files on disk; "
          f"{len(jobs)} downloads to do", flush=True)

    manifest = OUT / "manifest.csv"
    new_manifest = not manifest.exists()
    with open(manifest, "a", newline="", encoding="utf-8") as mf, ThreadPoolExecutor(max_workers=3) as pool:
        writer = csv.writer(mf)
        if new_manifest:
            writer.writerow(["ticker", "asof", "adjustment", "spell_start", "spell_end", "bars", "first", "last"])
        futures = {pool.submit(fetch, t, a, adj, end): (t, a, adj, path) for t, a, adj, path in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            ticker, asof, adjustment, path = futures[fut]
            try:
                rows = fut.result()
            except Exception as exc:  # keep going; a re-run retries the missing files
                print(f"FAILED {ticker} {asof} {adjustment}: {exc}", flush=True)
                continue
            save(path, ticker, asof, rows)
            writer.writerow([ticker, asof, adjustment, "", "", len(rows),
                             rows[0]["t"][:10] if rows else "", rows[-1]["t"][:10] if rows else ""])
            mf.flush()
            if i % 100 == 0:
                print(f"{i}/{len(jobs)} done", flush=True)
    print("bars: finished", flush=True)


if __name__ == "__main__":
    main()
