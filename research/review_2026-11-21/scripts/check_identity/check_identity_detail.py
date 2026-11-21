"""Follow-up detail for check_identity.py: who the overlapping membership rows are, the sessions below 500 members,
and symbols for the no-bar list. Counts, ids, symbols and dates only.
Run from the repo root:
  D:\\venvs\\chrono-trader\\Scripts\\python.exe -W ignore research\\review_2026-11-21\\scripts\\check_identity\\check_identity_detail.py
"""
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

S = "D:/chrono-data/store/"
mem = pq.read_table(S + "membership.parquet").to_pandas()
ide = pq.read_table(S + "identity.parquet").to_pandas()
bars = pq.read_table(S + "bars.parquet", columns=["entity_id", "date", "member"]).to_pandas()
ref = pd.read_csv("reference/memberships.csv", dtype=str)
FAR = pd.Timestamp("2262-01-01")
OVER = ["0001166691", "0001308161", "0001336917", "0001437107", "0001564708", "0001652044", "0001754301"]

print("== overlapping entities: rows of reference/memberships.csv (entity, from, to, source_ticker, how)")
for e in OVER:
    for r in ref[ref.entity_id == e].itertuples():
        print("  ", r.entity_id, r.member_from, r.member_to if isinstance(r.member_to, str) else None, r.source_ticker, "|", r.how)
    print("   identity share classes:", sorted(set(zip(ide[ide.entity_id == e].symbol, ide[ide.entity_id == e].share_class))))

print("\n== sessions below 500 distinct members (2016 to 2018)")
sessions = pd.DatetimeIndex(sorted(bars.date.unique()))
sessions = sessions[sessions >= pd.Timestamp("2016-01-04")]
start = mem.member_from.to_numpy().astype("datetime64[ns]")
end = mem.member_to.fillna(FAR).to_numpy().astype("datetime64[ns]")
codes = pd.factorize(mem.entity_id)[0]
low = []
for d in sessions:
    x = np.datetime64(d, "ns")
    n = len(np.unique(codes[(start <= x) & (end > x)]))
    if n < 500:
        low.append((d, n))
print("low sessions:", len(low))
print([(d.date().isoformat(), n) for d, n in low])
# which exits and joins sit next to each low session
snap = pd.read_csv("D:/chrono-data/membership/components_extended.csv", parse_dates=["date"])
snap["n"] = snap.tickers.str.split(",").map(len)
print("index file snapshot sizes on or just before each low session (date, tickers):")
seen = set()
for d, n in low:
    s = snap[snap.date <= d].iloc[-1]
    if s.date not in seen:
        seen.add(s.date)
        print("  ", d.date().isoformat(), "snapshot", s.date.date().isoformat(), int(s.n))
ev = mem[mem.member_to.notna() & (mem.member_to >= pd.Timestamp("2016-01-01")) & (mem.member_to <= pd.Timestamp("2018-12-31"))]
low_days = {d for d, _ in low}
ends_gap = [(r.entity_id, r.member_to.date().isoformat()) for r in ev.itertuples() if r.member_to in low_days or (r.member_to + pd.Timedelta(days=1)) in low_days]
print("membership rows ending (member_to) on a low session or the day before:", len(ends_gap))
starts = mem[(mem.member_from >= pd.Timestamp("2016-01-01")) & (mem.member_from <= pd.Timestamp("2018-12-31"))]
print("rows with member_from on a low session:", int(starts.member_from.isin(low_days).sum()))
print("low sessions that are the first session of a run (previous session not low):",
      sum(1 for i, (d, _) in enumerate(low) if i == 0 or low[i - 1][0] != sessions[sessions.get_loc(d) - 1]))
print("count of distinct member entities per session that day vs previous, around low sessions (date, n_prev, n, n_next):")
cn = {}
for d in sessions:
    x = np.datetime64(d, "ns")
    cn[d] = len(np.unique(codes[(start <= x) & (end > x)]))
sl = list(sessions)
for d, n in low[:12]:
    i = sl.index(d)
    print("  ", d.date().isoformat(), cn[sl[i - 1]] if i else None, n, cn[sl[i + 1]] if i + 1 < len(sl) else None)

print("\n== symbols for the first 20 no-bar entity-days")
sess = sessions
md = []
for r in mem.itertuples():
    a = np.datetime64(r.member_from, "ns")
    b = np.datetime64(r.member_to if pd.notna(r.member_to) else pd.Timestamp("2026-10-29"), "ns")
    s = sess.to_numpy().astype("datetime64[ns]")
    md.append(pd.DataFrame({"entity_id": r.entity_id, "date": s[(s >= a) & (s < b) & (s <= np.datetime64("2026-10-28"))]}))
md = pd.concat(md).drop_duplicates()
have = bars.groupby(["entity_id", "date"]).size().rename("n").reset_index()
nb = md.merge(have, how="left", on=["entity_id", "date"])
nb = nb[nb.n.isna()].sort_values(["entity_id", "date"])
ide["vf"] = pd.to_datetime(ide.valid_from)
ide["vt"] = pd.to_datetime(ide.valid_to.replace("", None)).fillna(FAR)


def sym(e, d):
    g = ide[(ide.entity_id == e) & (ide.vf <= d) & (ide.vt >= d)]
    return "/".join(sorted(set(g.symbol)))


for e, d in list(zip(nb.entity_id, nb.date))[:20]:
    print("  ", e, d.date().isoformat(), sym(e, d))
runs = []
for e, g in nb.groupby("entity_id"):
    ds = list(g.date)
    runs.append((e, sym(e, ds[0]), ds[0].date().isoformat(), ds[-1].date().isoformat(), len(ds)))
print("no-bar runs per entity (entity, symbol, first, last, days): ", len(runs), "entities")
for r in runs:
    print("  ", r)
