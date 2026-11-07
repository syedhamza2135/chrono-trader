"""The listing exchange's official opening and closing auction prints, for every stock-day that has a bar.

Alpaca's daily open is the day's first trade on any exchange. On a chaotic day that can be far from the listing
exchange's opening auction, where a market-on-open order fills (PLAN.md, the decision of 4 Nov), so the simulator
fills at the official open instead. Alpaca's historical auctions endpoint returns each stock-day's auction prints from
every exchange, with price, size, exchange, condition and time: opening prints under conditions O and Q, closing
prints under 6 and M.

The job follows the bar download plan (DATA_DIR/bars/plan.csv, written by bars.py): one fetch per bar file (symbol,
asof), with the same asof, over the dates that file's raw bars span. So each file of prints matches one file of bars,
and like the bars, the days outside a plan row's own dates can be another security's (see prices.py).

Files:
- DATA_DIR/auctions/prints/<symbol>__<asof>.parquet: one row per print (symbol, asof, date, side o or c, t in UTC,
  exchange code, price, size, condition). Re-running skips files on disk, so a stop loses only the files in flight.
- DATA_DIR/auctions/official.parquet: one row per file and date, from `official`.
- DATA_DIR/audit/auctions_check.csv: the stock-days where the print check (research/verify_prints.py, run on 787
  stock-days in M0) and this job disagree. Raw prices, so it stays out of git.
- research/audit/auctions.md: counts only.

Usage: python -m data_pipeline.auctions   (fetches what is missing, then rebuilds official.parquet and the check)
"""
from concurrent.futures import ThreadPoolExecutor, as_completed

import exchange_calendars as xcals
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from . import alpaca
from .settings import DATA_DIR, ROOT

OUT = DATA_DIR / "auctions"
PRINTS = OUT / "prints"
OFFICIAL = OUT / "official.parquet"
BARS = DATA_DIR / "bars"
CHECK_IN = DATA_DIR / "audit" / "official_prints.csv"
CHECK_INPUT = DATA_DIR / "audit" / "official_prints_input_v2.csv"
CHECK_OUT = DATA_DIR / "audit" / "auctions_check.csv"
REPORT = ROOT / "research" / "audit" / "auctions.md"

# Alpaca's exchange codes. Nasdaq's auctions print under Q, T or S, so they count as one exchange.
EXCHANGES = {"N": "NYSE", "A": "NYSE American", "P": "NYSE Arca", "Z": "Cboe BZX",
             "Q": "Nasdaq", "S": "Nasdaq", "T": "Nasdaq"}
SIDES = {"o": "open", "c": "close"}
LATE_OPEN = pd.Timedelta(hours=1)  # an official open more than an hour after the session's open is reported
PRINT_COLUMNS = ["symbol", "asof", "date", "side", "t", "x", "p", "s", "c"]
OFFICIAL_COLUMNS = ["symbol", "asof", "date", "listing_exchange", "open", "open_size", "open_time", "n_open_prints",
                    "close", "close_size", "close_time", "n_close_prints"]


def path_for(symbol, asof):
    return PRINTS / f"{symbol.replace('/', '_')}__{asof}.parquet"


def bar_dates(symbol, asof):
    """The dates of one raw bar file, sorted, as YYYY-MM-DD strings."""
    t = pq.read_table(BARS / "raw" / f"{symbol.replace('/', '_')}__{asof}.parquet", columns=["t"]).column("t")
    return sorted({str(x)[:10] for x in t.to_pylist()})


def jobs():
    """[(symbol, asof)]: every bar file in the plan, in a fixed order."""
    plan = pd.read_csv(BARS / "plan.csv", dtype=str)
    return sorted(set(zip(plan.symbol, plan["asof"])))  # plan.asof would be DataFrame.asof


def fetch(symbol, asof, start, end):
    """Every auction print of one symbol, as Alpaca resolves it on `asof`, from start to end (both dates included)."""
    rows = []
    for body in alpaca.pages("/v2/stocks/auctions", symbols=symbol, start=start, end=end, asof=asof, feed="sip",
                             limit=10000):
        auctions = body.get("auctions") or {}
        if set(auctions) - {symbol}:
            raise RuntimeError(f"asked for {symbol}, got {sorted(auctions)}")
        for day in auctions.get(symbol, []):
            for side in ("o", "c"):  # opening prints first, in the order Alpaca lists them
                for p in day.get(side) or []:
                    rows.append((symbol, asof, day["d"], side, p["t"], p["x"], p["p"], p["s"], p.get("c", "")))
    return rows


def save(path, rows):
    df = pd.DataFrame(rows, columns=PRINT_COLUMNS)
    table = pa.table({
        "symbol": pa.array(df.symbol, pa.string()),
        "asof": pa.array(df["asof"], pa.string()),
        "date": pa.array(df.date, pa.string()),
        "side": pa.array(df.side, pa.string()),
        "t": pa.array(pd.to_datetime(df.t, utc=True, format="ISO8601"), pa.timestamp("ns", tz="UTC")),
        "x": pa.array(df.x, pa.string()),
        "p": pa.array(df.p, pa.float64()),
        "s": pa.array(df.s, pa.int64()),
        "c": pa.array(df.c, pa.string()),
    })
    tmp = path.with_suffix(".tmp")
    pq.write_table(table, tmp)
    tmp.replace(path)


def official(prints):
    """One row per date of one file's prints: the listing exchange, and its largest opening and closing prints.

    The listing exchange is the exchange of the day's largest auction print, opening or closing, because its auctions
    dwarf the other exchanges' (research/verify_prints.py judges the same way). Ties go to the print Alpaca lists
    first. A side with no print on the listing exchange is left empty."""
    if prints.empty:
        return pd.DataFrame(columns=OFFICIAL_COLUMNS)
    df = prints.reset_index(drop=True).assign(venue=lambda d: d.x.map(EXCHANGES).fillna(d.x))
    df["order"] = range(len(df))
    biggest = df.sort_values(["date", "s", "order"], ascending=[True, False, True]).drop_duplicates("date")
    out = biggest.set_index("date")[["symbol", "asof", "venue"]].rename(columns={"venue": "listing_exchange"})
    df = df.join(out.listing_exchange, on="date")
    mine = df[df.venue == df.listing_exchange].sort_values(["date", "side", "s", "order"],
                                                          ascending=[True, True, False, True])
    mine = mine.drop_duplicates(["date", "side"])
    for side, name in SIDES.items():
        top = mine[mine.side == side].set_index("date")
        out[name] = top.p
        out[f"{name}_size"] = top.s
        out[f"{name}_time"] = top.t
        out[f"n_{name}_prints"] = df[df.side == side].groupby("date").size()
    out = out.reset_index()
    for name in SIDES.values():
        out[f"n_{name}_prints"] = out[f"n_{name}_prints"].fillna(0).astype("int64")
    return out[OFFICIAL_COLUMNS]


def split_sessions(off):
    """(rows on NYSE sessions, rows on other days). Alpaca lists a few auction records on days with no session, such
    as LLY's opening prints on Saturday 2024-07-20, which look like exchange test data. They are left out."""
    cal = xcals.get_calendar("XNYS")
    days = pd.DatetimeIndex(pd.to_datetime(off.date))
    on = cal.sessions.isin(days)
    sessions = set(cal.sessions[on].strftime("%Y-%m-%d"))
    keep = off.date.isin(sessions)
    return off[keep].reset_index(drop=True), off[~keep].reset_index(drop=True)


def build_official(files):
    """Every file's official rows on NYSE sessions, saved to OFFICIAL; and the rows on other days."""
    frames = []
    for symbol, asof in files:
        path = path_for(symbol, asof)
        if path.exists():
            frames.append(official(pq.read_table(path).to_pandas()))
    df, other = split_sessions(pd.concat([f for f in frames if not f.empty], ignore_index=True))
    df.to_parquet(OFFICIAL, index=False)
    return df, other


def late_opens(off):
    """Rows whose official open printed more than an hour after the NYSE session's open (sessions only)."""
    has = off.dropna(subset=["open_time"])
    if has.empty:
        return has
    cal = xcals.get_calendar("XNYS")
    first = {d: cal.session_open(d) for d in has.date.unique()}
    opened = pd.to_datetime(has.date.map(first), utc=True)
    return has[pd.to_datetime(has.open_time, utc=True) - opened > LATE_OPEN]


def check(off):
    """Compare with the print check, side by side, on the stock-days where it judged a side."""
    prints = pd.read_csv(CHECK_IN, dtype={"date": str})
    spells = pd.read_csv(CHECK_INPUT, dtype=str)[["symbol", "date", "spell_ticker"]].drop_duplicates(["symbol", "date"])
    prints = prints.merge(spells, on=["symbol", "date"], how="left")
    plan = pd.read_csv(BARS / "plan.csv", dtype=str)[["symbol", "asof", "use_from", "use_to"]]

    def live(tickers):
        """The plan row serving each print-check stock-day under these tickers, where one does."""
        x = pd.DataFrame({"spell": tickers, "date": prints.date}).reset_index()
        x = x.merge(plan, left_on="spell", right_on="symbol")
        return x[(x.use_from <= x.date) & (x.use_to >= x.date)].drop_duplicates("index").set_index("index")

    # The ticker the check queried comes first: the input's spell ticker for COH on 2017-04-07 is TPR, a later one.
    queried, spelled = live(prints.symbol), live(prints.spell_ticker.fillna(prints.symbol))
    rows = pd.concat([queried, spelled[~spelled.index.isin(queried.index)]])
    prints = prints.join(rows[["spell", "asof"]])
    unplanned = prints[prints.spell.isna()]  # ARNC after 2020-04-01 is the spun-off Arconic Corp, never a member
    prints = prints.dropna(subset=["spell"])
    got = off.rename(columns={"symbol": "spell"})
    m = prints.merge(got, on=["spell", "asof", "date"], how="left", suffixes=("", "_auctions"))
    out = []
    for name in SIDES.values():
        side = m[m[f"{name}_checked"].astype(str) == "True"]
        out.append(pd.DataFrame({
            "symbol": side.symbol, "date": side.date, "side": name, "print_check": side[f"official_{name}"],
            "auctions": side[name], "same": (side[name] - side[f"official_{name}"]).abs() < 1e-9,
            "check_exchange": side.listing_exchange, "auctions_exchange": side.listing_exchange_auctions,
            "file": side.spell + "__" + side["asof"]}))
    out.append(pd.DataFrame({"symbol": unplanned.symbol, "date": unplanned.date, "side": "not a plan stock-day",
                             "same": False}))
    return pd.concat(out, ignore_index=True)


def summary(files, off, other, compared, missing_member_opens, late, n_member_days, n_bar_days):
    lines = ["# Official auction prints (M1)", "",
             "Written by `python -m data_pipeline.auctions`. Counts only: the prints themselves are raw market data",
             "and stay in `D:\\chrono-data\\auctions`.", "",
             f"- Bar files fetched: {len(files)}, one per file of the bar plan.",
             f"- Stock-days with a bar: {n_bar_days:,}. With an auction record on an NYSE session: {len(off):,}.",
             f"- Auction records on days with no NYSE session, left out: {len(other):,}, on "
             f"{other.date.nunique() if len(other) else 0} dates ({', '.join(sorted(other.date.unique())[:5])}).",
             f"- Member stock-days with a bar (inside a plan row's own dates): {n_member_days:,}. Without an official",
             f"  open on the listing exchange: {len(missing_member_opens):,}"
             " (listed in `research/audit/auctions_missing_opens.csv`).",
             f"- Official opens more than an hour after the session's open: {len(late):,}.", ""]
    if len(compared):
        for name in SIDES.values():
            side = compared[compared.side == name]
            lines.append(f"- The print check judged the {name} on {len(side)} plan stock-days. The auctions agree on "
                         f"{int(side.same.sum())}.")
        unplanned = compared[compared.side == "not a plan stock-day"]
        lines.append(f"- Print-check stock-days that no plan row serves, so not compared: {len(unplanned)} "
                     f"({', '.join(sorted(unplanned.symbol + ' ' + unplanned.date))}).")
        lines.append("- Disagreements are in `D:\\chrono-data\\audit\\auctions_check.csv`.")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    files = jobs()
    PRINTS.mkdir(parents=True, exist_ok=True)
    spans = {f: bar_dates(*f) for f in files}
    todo = [f for f in files if not path_for(*f).exists() and spans[f]]
    print(f"auctions: {len(files)} bar files, {len(todo)} to fetch", flush=True)
    with ThreadPoolExecutor(max_workers=8) as pool:  # a page takes 2 to 3 seconds; the limiter caps the rate
        futures = {pool.submit(fetch, s, a, spans[(s, a)][0], spans[(s, a)][-1]): (s, a) for s, a in todo}
        for i, fut in enumerate(as_completed(futures), 1):
            symbol, asof = futures[fut]
            try:
                save(path_for(symbol, asof), fut.result())
            except Exception as exc:  # keep going; a re-run retries the missing files
                print(f"FAILED {symbol} {asof}: {exc}", flush=True)
            if i % 50 == 0:
                print(f"{i}/{len(todo)} fetched", flush=True)

    off, other = build_official(files)
    plan = pd.read_csv(BARS / "plan.csv", dtype=str)
    opened = off[off.open.notna()]
    have_open = set(zip(opened.symbol, opened["asof"], opened.date))
    member, missing = 0, []
    for r in plan.itertuples():
        for d in spans[(r.symbol, r.asof)]:
            if r.use_from <= d <= r.use_to:
                member += 1
                if (r.symbol, r.asof, d) not in have_open:
                    missing.append({"entity_id": r.entity_id, "symbol": r.symbol, "asof": r.asof, "date": d})
    missing = pd.DataFrame(missing, columns=["entity_id", "symbol", "asof", "date"])
    missing.to_csv(ROOT / "research" / "audit" / "auctions_missing_opens.csv", index=False)
    late = late_opens(off)
    compared = check(off) if CHECK_IN.exists() and CHECK_INPUT.exists() else pd.DataFrame()
    if len(compared):
        compared[~compared.same].to_csv(CHECK_OUT, index=False)
    summary(files, off, other, compared, missing, late, member, sum(len(v) for v in spans.values()))
    print(REPORT.read_text(encoding="utf-8"), flush=True)


if __name__ == "__main__":
    main()
