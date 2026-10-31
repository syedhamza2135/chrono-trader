"""Evidence for identity questions, from local data only (no API calls). Used to hand-check the identity table.

Usage: python research/identity_evidence.py <command> [args]
  wiki SYMBOL                  months Wikipedia's list showed SYMBOL, with CIK and company name
  cik CIK                      months and tickers Wikipedia showed for a CIK (10 digits, or without leading zeros)
  changes TEXT                 change-log rows whose tickers, names or reason contain TEXT (case-insensitive)
  members SYMBOL               membership spells for SYMBOL
  renames SYMBOL               Alpaca name changes (since 2020) with SYMBOL as old or new ticker
  tags SYMBOL [SYMBOL ...] START END
                               stories per day tagged with each symbol (Benzinga only), dates YYYY-MM-DD
  news SYMBOL START END [N]    first N (default 40) stories tagged SYMBOL in the window, New York time
  grep REGEX START END [N]     headlines matching REGEX (case-insensitive) in the window
  bars SYMBOL                  local bar files for SYMBOL: asof, first and last bar, rows, last traded day
  prices FILESTEM START END    raw and adjusted daily bars from a local file (e.g. WRK__2024-07-07), with adj/raw
  alpaca SYMBOL START END [ASOF]
                               daily bars straight from Alpaca (raw and fully adjusted); one or two API calls.
                               Use sparingly: the plan allows 200 calls a minute for everyone together.
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import pyarrow.parquet as pq

from data_pipeline import wikipedia as wp
from data_pipeline.membership import load_snapshots, spells
from data_pipeline.settings import DATA_DIR

NEWS = DATA_DIR / "news"
BENZINGA = {"", "benzinga"}


def _wiki():
    rows = []
    for path in sorted((wp.CACHE / "revisions").glob(f"{wp.LIST}@*.json")):
        rev = json.loads(path.read_text(encoding="utf-8"))["query"]["pages"][0]["revisions"][0]
        month = path.stem.split("@")[1]
        rows += [{"month": month, "stamp": rev["timestamp"][:10], **r} for r in wp.constituents(rev["slots"]["main"]["content"])]
    return pd.DataFrame(rows)


def _news(start, end, columns=("created_at", "headline", "symbols", "source")):
    months = pd.period_range(start[:7], end[:7], freq="M").strftime("%Y-%m")
    frames = [pq.read_table(NEWS / f"{m}.parquet", columns=list(columns)).to_pandas() for m in months if (NEWS / f"{m}.parquet").exists()]
    df = pd.concat(frames, ignore_index=True)
    df = df[df.source.isin(BENZINGA)]
    df["ny"] = pd.to_datetime(df.created_at, utc=True).dt.tz_convert("America/New_York")
    day = df.ny.dt.strftime("%Y-%m-%d")
    return df[(day >= start) & (day <= end)].sort_values("ny")


def main(cmd, *args):
    if cmd == "wiki":
        w = _wiki()
        g = w[w.symbol == args[0].upper()].groupby(["cik", "security"]).month.agg(["min", "max", "count"])
        print(g.to_string() if len(g) else "never shown")
    elif cmd == "cik":
        w = _wiki()
        g = w[w.cik == args[0].zfill(10)].groupby(["symbol", "security"]).month.agg(["min", "max", "count"])
        print(g.sort_values("min").to_string() if len(g) else "never shown")
    elif cmd == "changes":
        text = args[0].lower()
        for r in wp.changes(wp.current(wp.HISTORY, max(p.stem.split("@")[1] for p in wp.CACHE.glob(f"{wp.HISTORY}@*.json")))):
            if text in " ".join(str(v) for v in r.values()).lower():
                print(r["date"], "| added", r["added"], r["added_name"], "| removed", r["removed"], r["removed_name"], "|", r["reason"])
    elif cmd == "members":
        for s, e in spells(load_snapshots(), since=date(1990, 1, 1)).get(args[0].upper(), []):
            print(s, "to", e or "today")
    elif cmd == "renames":
        items = json.loads((DATA_DIR / "corporate_actions" / "name_changes.json").read_text(encoding="utf-8"))
        for it in sorted(items, key=lambda i: i["process_date"]):
            if args[0].upper() in (it["old_symbol"], it["new_symbol"]):
                print(it["process_date"], it["old_symbol"], "->", it["new_symbol"], "| cusip", it["old_cusip"], "->", it["new_cusip"])
    elif cmd == "tags":
        *symbols, start, end = args
        df = _news(start, end)
        day = df.ny.dt.strftime("%Y-%m-%d")
        table = pd.DataFrame({s: df.symbols.apply(lambda x, s=s: s.upper() in x).groupby(day).sum() for s in symbols}).fillna(0).astype(int)
        print(table[(table > 0).any(axis=1)].to_string())
    elif cmd == "news":
        symbol, start, end, *n = args
        df = _news(start, end)
        hit = df[df.symbols.apply(lambda x: symbol.upper() in x)]
        for r in hit.head(int(n[0]) if n else 40).itertuples():
            print(f"{r.ny:%Y-%m-%d %H:%M} | {','.join(list(r.symbols)[:6])} | {r.headline[:150]}")
    elif cmd == "grep":
        regex, start, end, *n = args
        df = _news(start, end)
        hit = df[df.headline.str.contains(regex, case=False, regex=True)]
        for r in hit.head(int(n[0]) if n else 40).itertuples():
            print(f"{r.ny:%Y-%m-%d %H:%M} | {','.join(list(r.symbols)[:6])} | {r.headline[:150]}")
    elif cmd == "bars":
        for path in sorted((DATA_DIR / "bars" / "raw").glob(f"{args[0].upper()}__*.parquet")):
            t = pq.read_table(path, columns=["t", "close", "volume"]).to_pandas()
            traded = t[t.volume > 0]
            print(path.stem, "| rows", len(t), "| first", t.t.min()[:10] if len(t) else "-", "| last", t.t.max()[:10] if len(t) else "-",
                  "| last traded", traded.t.max()[:10] if len(traded) else "-")
    elif cmd == "prices":
        stem, start, end = args
        frames = {}
        for adj in ("raw", "all"):
            t = pq.read_table(DATA_DIR / "bars" / adj / f"{stem}.parquet").to_pandas()
            t["d"] = t.t.str[:10]
            frames[adj] = t[(t.d >= start) & (t.d <= end)].set_index("d")
        r, a = frames["raw"], frames["all"]
        out = r[["open", "high", "low", "close", "volume", "vwap"]].assign(adj_close=a.close, adj_over_raw=a.close / r.close)
        print(out.round(4).to_string())
    elif cmd == "alpaca":
        from data_pipeline import alpaca
        symbol, start, end, *asof = args
        for adj in ("raw", "all"):
            params = {"symbols": symbol, "timeframe": "1Day", "start": start, "end": end, "adjustment": adj, "feed": "sip", "limit": 1000}
            if asof:
                params["asof"] = asof[0]
            bars = alpaca.get("/v2/stocks/bars", **params).get("bars", {}).get(symbol, [])
            print(f"-- {symbol} {adj} ({len(bars)} bars)")
            for b in bars:
                print(f"{b['t'][:10]} o{b['o']} h{b['h']} l{b['l']} c{b['c']} v{b['v']} vw{b.get('vw')}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main(*sys.argv[1:]) if len(sys.argv) > 1 else print(__doc__)
