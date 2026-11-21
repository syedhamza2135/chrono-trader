"""Doc numbers about the official auction prints (m1_kickoff Session 1 to 3, README). Counts, dates and symbols only."""
import os, glob, datetime as dt
import pandas as pd, pyarrow.parquet as pq, exchange_calendars as xc

D = "D:/chrono-data/"
plan = pd.read_csv(D + "bars/plan.csv", dtype=str)
print("plan rows", len(plan), "unique (symbol, asof) files", len(set(zip(plan.symbol, plan["asof"]))))
pf = sorted(glob.glob(D + "auctions/prints/*.parquet"))
print("print files", len(pf))
mt = [os.path.getmtime(p) for p in pf]
print("print files written from", dt.datetime.fromtimestamp(min(mt)).strftime("%Y-%m-%d %H:%M:%S"), "to",
      dt.datetime.fromtimestamp(max(mt)).strftime("%Y-%m-%d %H:%M:%S"),
      "span minutes", round((max(mt) - min(mt)) / 60, 1))
off = pd.read_parquet(D + "auctions/official.parquet")
print("official.parquet rows", len(off))

# stock-days with a bar, from the raw bar files of the plan
spans = {}
for s, a in sorted(set(zip(plan.symbol, plan["asof"]))):
    t = pq.read_table(D + f"bars/raw/{s.replace('/', '_')}__{a}.parquet", columns=["t"]).column("t")
    spans[(s, a)] = sorted({str(x)[:10] for x in t.to_pylist()})
print("stock-days with a bar", sum(len(v) for v in spans.values()))

# records on days with no NYSE session (from the raw prints)
cal = xc.get_calendar("XNYS")
sess = set(cal.sessions.strftime("%Y-%m-%d"))
other = set()
for p in pf:
    d = pq.read_table(p, columns=["symbol", "asof", "date"]).to_pandas().drop_duplicates()
    for r in d.itertuples():
        if r.date not in sess:
            other.add((r.symbol, r.asof, r.date))
print("auction records on non-session days", len(other), "dates", sorted({x[2] for x in other}))

# member stock-days with a bar, and those with no official open
have = set(zip(off.loc[off.open.notna(), "symbol"], off.loc[off.open.notna(), "asof"], off.loc[off.open.notna(), "date"]))
member, miss = 0, []
for r in plan.itertuples():
    for d in spans[(r.symbol, r.asof)]:
        if r.use_from <= d <= r.use_to:
            member += 1
            if (r.symbol, r.asof, d) not in have:
                miss.append(d)
print("member stock-days with a bar (plan dates)", member)
print("member stock-days without an official open", len(miss))
print("by date (top 4):", pd.Series(miss).value_counts().head(4).to_dict())

# late opens
has = off.dropna(subset=["open_time"]).copy()
first = {d: cal.session_open(d) for d in has.date.unique()}
opened = pd.to_datetime(has.date.map(first), utc=True)
late = has[pd.to_datetime(has.open_time, utc=True) - opened > pd.Timedelta(hours=1)]
print("official opens more than an hour late (all stock-days)", len(late))
member_keys = set()
for r in plan.itertuples():
    for d in spans[(r.symbol, r.asof)]:
        if r.use_from <= d <= r.use_to:
            member_keys.add((r.symbol, r.asof, d))
print("  of which on member stock-days", sum((a, b, c) in member_keys for a, b, c in zip(late.symbol, late["asof"], late.date)))

# COF 2016-10-13 and CXO 2017-10-09 have an official open
for sym, d in (("COF", "2016-10-13"), ("CXO", "2017-10-09")):
    x = off[(off.symbol == sym) & (off.date == d)]
    print(sym, d, "rows", len(x), "has open", bool(x.open.notna().any()))
# 2026-08-20 NYSE Arca opens: listing exchange of rows that day
x = off[off.date == "2026-08-20"]
print("2026-08-20 rows", len(x), "listing exchange counts", x.listing_exchange.value_counts().to_dict())

# print check
pc = pd.read_csv(D + "audit/official_prints.csv")
print("official_prints.csv rows", len(pc), "open_checked", int((pc.open_checked.astype(str) == "True").sum()),
      "close_checked", int((pc.close_checked.astype(str) == "True").sum()))
ck = pd.read_csv(D + "audit/auctions_check.csv") if os.path.exists(D + "audit/auctions_check.csv") else None
print("auctions_check.csv (disagreements) exists:", ck is not None, "rows", None if ck is None else len(ck))
# independent agreement count: join the print check to official.parquet by symbol and date
j = pc.merge(off, on=["symbol", "date"], how="left", suffixes=("", "_a"))
plan_ok = set()
for r in plan.itertuples():
    pass
o = j[j.open_checked.astype(str) == "True"]
c = j[j.close_checked.astype(str) == "True"]
print("opens checked", len(o), "joined with an auctions row", int(o.open.notna().sum()),
      "equal", int(((o.open - o.official_open).abs() < 1e-9).sum()))
print("closes checked", len(c), "joined with an auctions row", int(c.close.notna().sum()),
      "equal", int(((c.close - c.official_close).abs() < 1e-9).sum()))
nj = pc.merge(off[["symbol", "date"]].drop_duplicates(), on=["symbol", "date"], how="left", indicator=True)
print("print-check stock-days with no auctions row:", sorted((nj[nj._merge == "left_only"].symbol + " " + nj[nj._merge == "left_only"].date).tolist()))
