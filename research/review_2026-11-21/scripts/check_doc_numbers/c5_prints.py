"""Probe numbers (Session 1): delayed NYSE opens on 2023-01-24, prints of the 2023 preview picks, bars after the data end,
the 54 overridden opens. Prices are never printed: sizes, times, counts and booleans only."""
import glob, os, datetime as dt
import numpy as np, pandas as pd, pyarrow.parquet as pq
D = "D:/chrono-data/"
plan = pd.read_csv(D + "bars/plan.csv", dtype=str)

def prints_of(sym):
    out = []
    for f in glob.glob(D + f"auctions/prints/{sym}__*.parquet"):
        out.append(pq.read_table(f).to_pandas())
    return pd.concat(out) if out else pd.DataFrame()

# LLY, MA, XOM on 2023-01-24: stated opening print on N: size and time (New York time)
for sym, size, hhmmss in (("LLY", 16693, "09:38:25"), ("MA", 8632, "09:39:56"), ("XOM", 198488, "09:37:03")):
    p = prints_of(sym)
    p = p[(p.date == "2023-01-24") & (p.side == "o") & (p.x == "N")]
    p = p.assign(ny=pd.to_datetime(p.t, utc=True).dt.tz_convert("America/New_York").dt.strftime("%H:%M:%S"))
    hit = p[(p.s == size)]
    print(sym, "2023-01-24 N open prints", len(p), "| a print of the stated size", len(hit) > 0,
          "| at the stated time", bool((hit.ny == hhmmss).any()), "| conditions of the largest:", p.sort_values("s").c.iloc[-1] if len(p) else None)
# NYSE opening print under both O and Q? count N open prints per day whose condition holds O and Q (stock-days in 2023-01-23..25 for LLY, MA, XOM)
for sym in ("LLY", "MA", "XOM"):
    p = prints_of(sym)
    p = p[(p.date >= "2023-01-23") & (p.date <= "2023-01-25") & (p.side == "o") & (p.x == "N")]
    print(sym, "N open prints 23-25 Jan 2023: condition sets", p.c.value_counts().to_dict())
# Nasdaq exchange codes for AAPL opens
a = prints_of("AAPL"); a = a[a.side == "o"]
print("AAPL opening prints, exchange codes seen", a.x.value_counts().head(6).to_dict())

# 2023's 50 preview picks: records and prints over 2023
up = pd.read_csv("research/audit/universe_preview.csv")
picks = up[up.year == 2023]
print("2023 picks", len(picks))
recs = prints = 0
sessions_ok = []
for sym in picks.symbol:
    f = []
    for fp in glob.glob(D + f"auctions/prints/{sym}__*.parquet"):
        t = pq.read_table(fp).to_pandas()
        f.append(t[(t.date >= "2023-01-01") & (t.date <= "2023-12-31")])
    t = pd.concat(f).drop_duplicates() if f else pd.DataFrame(columns=["date"])
    recs += t.drop_duplicates(["date"]).shape[0]
    prints += len(t)
    sessions_ok.append(t.date.nunique())
print("2023 picks: stock-day records", recs, "prints", prints, "symbols with 250 sessions", sum(s == 250 for s in sessions_ok),
      "distribution of sessions per symbol", pd.Series(sessions_ok).value_counts().to_dict())

# bars after the data end
n_after, newest = 0, ""
for r in plan.itertuples():
    t = pq.read_table(D + f"bars/raw/{r.symbol.replace('/', '_')}__{r.asof}.parquet", columns=["t"]).column("t").to_pylist()
    ds = {str(x)[:10] for x in t}
    over = {d for d in ds if d > "2026-10-28" and r.use_from <= d <= r.use_to}
    n_after += len(over)
    if over:
        newest = max(newest, max(over))
print("member stock-days after 2026-10-28 in the plan files", n_after, "latest", newest)

# the 54 override_open rows equal the store's official opens
pe = pd.read_csv("reference/price_events.csv", dtype=str)
ov = pe[pe.action == "override_open"][["symbol", "date", "open"]].assign(open=lambda d: d.open.astype(float))
bars = pd.read_parquet(D + "store/bars.parquet", columns=["entity_id", "share_class", "symbol", "date", "member"])
opens = pd.read_parquet(D + "store/opens.parquet", columns=["entity_id", "share_class", "date", "open"])
bars["date"] = pd.to_datetime(bars.date); ov["date"] = pd.to_datetime(ov.date)
j = ov.merge(bars[bars.member], on=["symbol", "date"], how="left").merge(opens.rename(columns={"open": "o"}), on=["entity_id", "share_class", "date"], how="left")
print("override_open rows", len(ov), "found in store opens", int(j.o.notna().sum()), "equal", int(((j.open - j.o).abs() < 1e-9).sum()))

# which stock-days have no official open: LLY on 2018-01-24 and 2019-08-12
off = pd.read_parquet(D + "auctions/official.parquet")
for d in ("2018-01-24", "2019-08-12"):
    x = off[(off.symbol == "LLY") & (off.date == d)]
    print("LLY", d, "official rows", len(x), "with an open", int(x.open.notna().sum()))
print("2024-07-20 weekday:", dt.date(2024, 7, 20).strftime("%A"))
# download span of the news files
nf = glob.glob(D + "news/*.parquet")
mt = [os.path.getmtime(p) for p in nf]
print("news files", len(nf), "first/last written", dt.datetime.fromtimestamp(min(mt)).strftime("%Y-%m-%d %H:%M"), dt.datetime.fromtimestamp(max(mt)).strftime("%Y-%m-%d %H:%M"))
